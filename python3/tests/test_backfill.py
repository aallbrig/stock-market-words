"""Gap detection, fetching, idempotency, resume and throttling for `ticker-cli backfill`."""
import json
from datetime import date, datetime, timezone
from unittest import mock

import click
import pytest
from click.testing import CliRunner
from yfinance import shared as yf_shared

from stock_ticker import backfill
from stock_ticker.cli import cli
from stock_ticker.download_strategies import BatchDownloadStrategy, DownloadAborted, PiaVpnDownloadStrategy
from stock_ticker.retry import RetryTracker
from tests.conftest import fake_bars, fake_close

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)  # 08:00 ET: last completed session is 2026-10-28
SYMBOLS = ["AAA", "BBB", "CCC", "DDD", "EEE"]
LEVELS = {s: 100.0 + n for n, s in enumerate(SYMBOLS)}


def seed_tickers(conn, symbols=SYMBOLS):
    conn.executemany("INSERT OR IGNORE INTO tickers (symbol, name, exchange, is_etf) VALUES (?, ?, 'NASDAQ', 0)",
                     [(s, s) for s in symbols])
    conn.commit()


def seed_rows(conn, symbols, days, price=1.0, market_cap=None):
    conn.executemany(
        "INSERT INTO daily_metrics (symbol, date, price, volume, market_cap) VALUES (?, ?, ?, 1000, ?)",
        [(s, d, price, market_cap) for s in symbols for d in days],
    )
    conn.commit()


def dump(conn):
    return conn.execute("SELECT * FROM daily_metrics ORDER BY symbol, date").fetchall()


class FakeYahoo:
    """Stands in for yf.download; `plan(call_number, symbols)` may raise or return {SYMBOL: error text}."""

    def __init__(self, monkeypatch, plan=None):
        self.calls = []
        self.plan = plan
        monkeypatch.setattr("stock_ticker.download_strategies.yf.download", self)

    def __call__(self, tickers, start=None, end=None, **kwargs):
        symbols = tickers.split()
        self.calls.append({"symbols": symbols, "start": start, "end": end, **kwargs})
        errors = (self.plan(len(self.calls), symbols) if self.plan else None) or {}
        yf_shared._ERRORS = dict(errors)
        ok = [s for s in symbols if s.upper() not in errors]
        return fake_bars(ok, start, end, base=LEVELS)


@pytest.fixture
def strategy(monkeypatch):
    monkeypatch.setattr("stock_ticker.retry.time.sleep", lambda s: None)
    monkeypatch.setattr("stock_ticker.download_strategies.time.sleep", lambda s: None)
    vpn = mock.Mock()
    vpn.should_rotate.return_value = False
    return BatchDownloadStrategy(retry_tracker=RetryTracker(), vpn_rotator=vpn)


@pytest.fixture
def small_batches(monkeypatch):
    monkeypatch.setattr(backfill, "PRICE_BATCH_SIZE", 2)


def run(conn, strategy, start="2026-10-19", end="2026-10-23", **kwargs):
    lines = []
    summary = backfill.run_backfill(
        conn, date.fromisoformat(start), date.fromisoformat(end), strategy=strategy, now=NOW,
        echo=lines.append, **kwargs
    )
    summary["output"] = "\n".join(lines)
    return summary


class TestGapDetection:
    def test_missing_incomplete_and_complete_sessions(self, market_db):
        seed_tickers(market_db, [f"T{i}" for i in range(10)])
        tickers = [f"T{i}" for i in range(10)]
        seed_rows(market_db, tickers, ["2026-10-19", "2026-10-23"])
        seed_rows(market_db, tickers[:7], ["2026-10-21"])       # 70% of its neighbours: incomplete
        seed_rows(market_db, tickers[:9], ["2026-10-22"])       # 90%: fine
        seed_rows(market_db, tickers[:3], ["2026-10-24"])       # Saturday: not a session
        report = backfill.analyze_gaps(market_db, date(2026, 10, 19), date(2026, 10, 25), now=NOW)
        assert {p.day.isoformat(): (p.reason, p.mode) for p in report.targets} == {
            "2026-10-20": ("missing", "fill"),
            "2026-10-21": ("incomplete", "fill"),
        }
        assert report.non_trading_rows == {date(2026, 10, 24): 3}
        assert len(report.sessions) == 5

    def test_threshold_boundary(self, market_db):
        tickers = [f"T{i}" for i in range(20)]
        seed_tickers(market_db, tickers)
        seed_rows(market_db, tickers, ["2026-10-19", "2026-10-21"])
        seed_rows(market_db, tickers[:17], ["2026-10-20"])       # 17/20 = exactly 85%: complete
        assert backfill.analyze_gaps(market_db, date(2026, 10, 20), date(2026, 10, 20), now=NOW).targets == []
        market_db.execute("DELETE FROM daily_metrics WHERE symbol = 'T16' AND date = '2026-10-20'")
        report = backfill.analyze_gaps(market_db, date(2026, 10, 20), date(2026, 10, 20), now=NOW)
        assert [p.reason for p in report.targets] == ["incomplete"]

    def test_session_captured_before_close_is_replaced_not_filled(self, market_db):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-21", "2026-10-22", "2026-10-23"])
        market_db.execute("INSERT INTO pipeline_steps VALUES ('extract-prices', '2026-10-22', "
                          "'2026-10-22 15:07:12', 5, 'completed')")
        report = backfill.analyze_gaps(market_db, date(2026, 10, 21), date(2026, 10, 23), now=NOW)
        assert [(p.day.isoformat(), p.reason, p.mode) for p in report.targets] == [
            ("2026-10-22", "preclose", "replace")]

    def test_stretch_of_equally_partial_sessions_is_caught_by_the_universe_floor(self, market_db):
        tickers = [f"T{i}" for i in range(20)]
        seed_tickers(market_db, tickers)
        seed_rows(market_db, tickers[:5], ["2026-10-19", "2026-10-20", "2026-10-21"])  # 25% each, same as neighbours
        report = backfill.analyze_gaps(market_db, date(2026, 10, 19), date(2026, 10, 21), now=NOW)
        assert [p.reason for p in report.targets] == ["incomplete"] * 3

    def test_holiday_is_not_a_gap(self, market_db):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-07-02", "2026-07-06"])
        report = backfill.analyze_gaps(market_db, date(2026, 7, 2), date(2026, 7, 6), now=NOW)
        assert report.targets == []  # 07-03 (observed holiday) and the weekend are not sessions


class TestDryRun:
    def test_reports_gaps_and_request_estimate_without_writing(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-19", "2026-10-23"])
        monkeypatch.setattr("stock_ticker.download_strategies.yf.download",
                            mock.Mock(side_effect=AssertionError("dry run must not download")))
        before = dump(market_db)
        result = run(market_db, strategy, dry_run=True)
        assert list(result["targets"]) == ["2026-10-20", "2026-10-21", "2026-10-22"]
        assert result["estimate"] == {"download_calls": 1, "chart_requests": 5,
                                      "per_day_download_calls": 3, "per_day_chart_requests": 15}
        assert "DRY RUN" in result["output"] and "2026-10-20" in result["output"]
        assert dump(market_db) == before
        assert market_db.execute("SELECT COUNT(*) FROM backfill_runs").fetchone()[0] == 0

    def test_cli_dry_run(self, market_db, monkeypatch):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-19", "2026-10-23"])
        monkeypatch.setattr("stock_ticker.backfill.utc_now", lambda: NOW)
        monkeypatch.setattr("stock_ticker.market_calendar.utc_now", lambda: NOW)
        result = CliRunner().invoke(cli, ["backfill", "--from", "2026-10-19", "--to", "2026-10-23", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "3 need work" in result.output and "yf.download calls" in result.output


class TestFill:
    def test_one_download_per_batch_not_per_day(self, market_db, monkeypatch, strategy, small_batches):
        seed_tickers(market_db)
        yahoo = FakeYahoo(monkeypatch)
        result = run(market_db, strategy)  # five missing sessions, five tickers, batch size 2
        assert len(yahoo.calls) == 3
        assert [c["symbols"] for c in yahoo.calls] == [["AAA", "BBB"], ["CCC", "DDD"], ["EEE"]]
        assert result["download_calls"] == 3
        assert all(c["auto_adjust"] is False for c in yahoo.calls)
        rows = market_db.execute("SELECT COUNT(*), COUNT(DISTINCT date) FROM daily_metrics").fetchone()
        assert rows == (25, 5)

    def test_rows_match_the_daily_run_schema(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        row = market_db.execute(
            "SELECT price, volume, open_price, high_price, low_price, adj_close, market_cap "
            "FROM daily_metrics WHERE symbol = 'BBB' AND date = '2026-10-20'").fetchone()
        close = fake_close(LEVELS["BBB"], "2026-10-20")
        assert row == (pytest.approx(close), 1_000_010, pytest.approx(close - 0.5),
                       pytest.approx(close + 1), pytest.approx(close - 1), None, None)

    def test_existing_rows_and_fundamentals_are_left_alone(self, market_db, monkeypatch, strategy):
        tickers = [f"T{i}" for i in range(10)]
        seed_tickers(market_db, tickers)
        seed_rows(market_db, tickers, ["2026-10-20", "2026-10-22"], market_cap=7e9)
        seed_rows(market_db, tickers[:7], ["2026-10-21"], price=1.0, market_cap=7e9)
        FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-21", end="2026-10-21")
        kept = market_db.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = '2026-10-21' "
                                 "AND price = 1.0 AND market_cap = 7e9").fetchone()[0]
        added = market_db.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = '2026-10-21' "
                                  "AND price > 1.0 AND market_cap IS NULL").fetchone()[0]
        assert (kept, added) == (7, 3)

    def test_writes_technicals_for_new_rows(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db, ["AAA"])
        FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-20", end="2026-10-23")
        rsi, ma50, ma200, vol, atr = market_db.execute(
            "SELECT rsi_14, ma_50, ma_200, hist_volatility, atr_14 FROM daily_metrics "
            "WHERE symbol = 'AAA' AND date = '2026-10-23'").fetchone()
        assert rsi == pytest.approx(100.0)          # the feed rises every day
        assert ma50 is not None and ma200 is not None  # 320 days of lookback were requested
        assert atr == pytest.approx(2.0) and vol is not None

    def test_limit_runs_are_not_remembered_as_complete(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        yahoo = FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-20", end="2026-10-20", limit=2)
        assert yahoo.calls[0]["symbols"] == ["AAA", "BBB"]
        assert backfill._settled_dates(market_db) == set()
        row = market_db.execute("SELECT status, symbol_limit FROM backfill_runs").fetchone()
        assert row == ("completed", 2)


class TestIdempotency:
    def test_second_plain_run_finds_nothing_to_do(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        yahoo = FakeYahoo(monkeypatch)
        run(market_db, strategy)
        after_first = dump(market_db)
        calls = len(yahoo.calls)
        again = run(market_db, strategy)
        assert again["targets"] == {} and len(yahoo.calls) == calls
        assert dump(market_db) == after_first

    def test_refetch_twice_changes_nothing_and_never_duplicates(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        FakeYahoo(monkeypatch)
        run(market_db, strategy)
        run(market_db, strategy, refetch=True)
        first = dump(market_db)
        run(market_db, strategy, refetch=True)
        assert dump(market_db) == first
        assert len(first) == 25

    def test_refetch_preserves_fundamentals(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-20"], price=1.0, market_cap=3e9)
        FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-20", end="2026-10-20", refetch=True)
        price, cap = market_db.execute("SELECT price, market_cap FROM daily_metrics "
                                       "WHERE symbol = 'AAA' AND date = '2026-10-20'").fetchone()
        assert price == pytest.approx(fake_close(LEVELS["AAA"], "2026-10-20")) and cap == 3e9


class TestPartialDayReplacement:
    def test_preclose_session_is_overwritten_and_rescored(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-20", "2026-10-22"], price=1.0, market_cap=5e9)
        market_db.execute("INSERT INTO pipeline_steps VALUES ('extract-prices', '2026-10-22', "
                          "'2026-10-22 15:07:12', 5, 'completed')")
        market_db.execute("INSERT INTO pipeline_steps VALUES ('extract-prices', '2026-10-20', "
                          "'2026-10-21 00:30:00', 5, 'completed')")
        market_db.commit()
        FakeYahoo(monkeypatch)
        result = run(market_db, strategy, start="2026-10-20", end="2026-10-22")
        assert result["targets"]["2026-10-22"] == "replace" and "2026-10-20" not in result["targets"]
        price, cap = market_db.execute("SELECT price, market_cap FROM daily_metrics "
                                       "WHERE symbol = 'CCC' AND date = '2026-10-22'").fetchone()
        assert price == pytest.approx(fake_close(LEVELS["CCC"], "2026-10-22")) and cap == 5e9
        untouched = market_db.execute("SELECT DISTINCT price FROM daily_metrics WHERE date = '2026-10-20'").fetchall()
        assert untouched == [(1.0,)]
        scored = market_db.execute("SELECT COUNT(*) FROM strategy_scores WHERE date = '2026-10-22'").fetchone()[0]
        assert scored == 5

    def test_second_run_does_not_replace_again(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-22"], price=1.0)
        market_db.execute("INSERT INTO pipeline_steps VALUES ('extract-prices', '2026-10-22', "
                          "'2026-10-22 15:07:12', 5, 'completed')")
        market_db.commit()
        yahoo = FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-22", end="2026-10-22")
        assert len(yahoo.calls) == 1
        # the replaced session is now stamped as post-close, so nothing is left to do
        again = run(market_db, strategy, start="2026-10-22", end="2026-10-22")
        assert again["targets"] == {} and len(yahoo.calls) == 1
        stamp = market_db.execute("SELECT completed_at FROM pipeline_steps WHERE run_date = '2026-10-22'").fetchone()[0]
        assert stamp > "2026-10-22 20:00:00"

    def test_limit_run_does_not_stamp_the_session_as_refreshed(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db)
        seed_rows(market_db, SYMBOLS, ["2026-10-22"], price=1.0)
        market_db.execute("INSERT INTO pipeline_steps VALUES ('extract-prices', '2026-10-22', "
                          "'2026-10-22 15:07:12', 5, 'completed')")
        market_db.commit()
        FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-22", end="2026-10-22", limit=2)  # 2 of 5 tickers only
        stamp = market_db.execute("SELECT completed_at FROM pipeline_steps WHERE run_date = '2026-10-22'").fetchone()[0]
        assert stamp == "2026-10-22 15:07:12"


class TestResume:
    def test_crash_mid_run_resumes_with_remaining_tickers_only(self, market_db, monkeypatch, strategy, small_batches):
        seed_tickers(market_db)

        def explode_on_second_batch(call, symbols):
            if call == 2:
                raise RuntimeError("network down")

        FakeYahoo(monkeypatch, plan=explode_on_second_batch)
        with pytest.raises(RuntimeError):
            run(market_db, strategy)
        status, written = market_db.execute("SELECT status, rows_written FROM backfill_runs").fetchone()
        done = [r[0] for r in market_db.execute("SELECT symbol FROM backfill_symbols ORDER BY symbol")]
        assert (status, written, done) == ("failed", 10, ["AAA", "BBB"])
        assert market_db.execute("SELECT COUNT(DISTINCT symbol) FROM daily_metrics").fetchone()[0] == 2

        yahoo = FakeYahoo(monkeypatch)
        result = run(market_db, strategy)
        assert "Resuming backfill run #1" in result["output"] and result["report"] is None
        assert [c["symbols"] for c in yahoo.calls] == [["CCC", "DDD"], ["EEE"]]
        assert market_db.execute("SELECT COUNT(*) FROM daily_metrics").fetchone()[0] == 25
        assert market_db.execute("SELECT status, download_calls FROM backfill_runs").fetchall() == [("completed", 3)]

    def test_resume_keeps_the_original_plan_after_dates_look_complete(self, market_db, monkeypatch, strategy, small_batches):
        # 4 of 5 tickers are written before the crash: every session is 80% populated, above both
        # completeness thresholds, so a fresh gap scan sees nothing to do. The journal's frozen
        # plan must still finish the last ticker.
        seed_tickers(market_db)
        FakeYahoo(monkeypatch, plan=lambda call, symbols: (_ for _ in ()).throw(RuntimeError("x")) if call == 3 else None)
        with pytest.raises(RuntimeError):
            run(market_db, strategy)
        assert backfill.analyze_gaps(market_db, date(2026, 10, 19), date(2026, 10, 23), now=NOW).targets == []
        FakeYahoo(monkeypatch)
        run(market_db, strategy)
        assert market_db.execute("SELECT COUNT(*) FROM daily_metrics WHERE symbol = 'EEE'").fetchone()[0] == 5

    def test_restart_discards_the_interrupted_run(self, market_db, monkeypatch, strategy, small_batches):
        seed_tickers(market_db)
        FakeYahoo(monkeypatch, plan=lambda call, symbols: (_ for _ in ()).throw(RuntimeError("x")) if call == 2 else None)
        with pytest.raises(RuntimeError):
            run(market_db, strategy)
        yahoo = FakeYahoo(monkeypatch)
        result = run(market_db, strategy, restart=True)
        assert "Resuming" not in result["output"]
        assert [c["symbols"] for c in yahoo.calls] == [["AAA", "BBB"], ["CCC", "DDD"], ["EEE"]]
        statuses = [r[0] for r in market_db.execute("SELECT status FROM backfill_runs ORDER BY run_id")]
        assert statuses == ["abandoned", "completed"]


class TestThrottling:
    def test_only_throttled_tickers_are_requested_again(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db, SYMBOLS[:3])
        limited = "YFRateLimitError('Too Many Requests. Rate limited. Try after a while.')"
        yahoo = FakeYahoo(monkeypatch, plan=lambda call, symbols: {"BBB": limited} if call == 1 else None)
        sleeps = []
        monkeypatch.setattr("stock_ticker.retry.time.sleep", sleeps.append)
        run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        assert [c["symbols"] for c in yahoo.calls] == [["AAA", "BBB", "CCC"], ["BBB"]]
        assert len(sleeps) == 1  # retry.py's backoff ran once
        assert market_db.execute("SELECT COUNT(*) FROM daily_metrics WHERE symbol = 'BBB'").fetchone()[0] == 1

    def test_persistent_throttling_aborts_and_is_resumable(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db, SYMBOLS[:2])
        limited = "429 Too Many Requests"
        FakeYahoo(monkeypatch, plan=lambda call, symbols: {s.upper(): limited for s in symbols})
        with pytest.raises(DownloadAborted):
            run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        assert market_db.execute("SELECT status FROM backfill_runs").fetchone() == ("failed",)
        assert market_db.execute("SELECT COUNT(*) FROM backfill_symbols").fetchone()[0] == 0
        strategy._retry.reset()
        yahoo = FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        assert yahoo.calls and market_db.execute("SELECT COUNT(*) FROM daily_metrics").fetchone()[0] == 2

    def test_pia_vpn_strategy_slows_down_and_retries_only_throttled_tickers(self, market_db, monkeypatch):
        seed_tickers(market_db, SYMBOLS[:3])
        limited = "YFRateLimitError('Too Many Requests. Rate limited. Try after a while.')"
        yahoo = FakeYahoo(monkeypatch, plan=lambda call, symbols: {"CCC": limited} if call == 1 else None)
        sleeps = []
        monkeypatch.setattr("stock_ticker.download_strategies.time.sleep", sleeps.append)
        vpn = mock.Mock()
        vpn.should_rotate.return_value = False
        pia = PiaVpnDownloadStrategy(vpn_rotator=vpn, initial_delay=0.2)
        run(market_db, pia, start="2026-10-20", end="2026-10-20")
        assert [c["symbols"] for c in yahoo.calls] == [["AAA", "BBB", "CCC"], ["CCC"]]
        assert sleeps == [0.4]  # the adaptive delay doubled once
        assert market_db.execute("SELECT COUNT(*) FROM daily_metrics").fetchone()[0] == 3

    def test_transient_errors_are_retried_not_recorded_as_no_data(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db, SYMBOLS[:3])
        FakeYahoo(monkeypatch, plan=lambda call, symbols: {"BBB": "ReadTimeout('timed out')"})
        with pytest.raises(click.ClickException, match="BBB"):
            run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        assert market_db.execute("SELECT status FROM backfill_runs").fetchone() == ("failed",)
        assert [r[0] for r in market_db.execute("SELECT symbol FROM backfill_symbols ORDER BY symbol")] == ["AAA", "CCC"]
        yahoo = FakeYahoo(monkeypatch)
        run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        assert [c["symbols"] for c in yahoo.calls] == [["BBB"]]
        assert market_db.execute("SELECT COUNT(*) FROM daily_metrics").fetchone()[0] == 3
        assert market_db.execute("SELECT status FROM backfill_runs").fetchone() == ("completed",)

    def test_symbols_without_data_are_recorded_as_done(self, market_db, monkeypatch, strategy):
        seed_tickers(market_db, SYMBOLS[:2])
        FakeYahoo(monkeypatch, plan=lambda call, symbols: {"BBB": "possibly delisted; no price data found"})
        run(market_db, strategy, start="2026-10-20", end="2026-10-20")
        done = dict(market_db.execute("SELECT symbol, rows_written FROM backfill_symbols").fetchall())
        assert done == {"AAA": 1, "BBB": 0}


def test_final_report_judges_completeness_only_for_full_runs(market_db, monkeypatch, strategy):
    seed_tickers(market_db)
    FakeYahoo(monkeypatch)
    result = run(market_db, strategy, start="2026-10-20", end="2026-10-20", limit=2)
    lines = []
    assert backfill.final_report(market_db, result["targets"], lines.append, limit=2) == []
    assert "SHORT" not in "\n".join(lines) and "not judged" in "\n".join(lines)
    lines.clear()
    assert [row[0] for row in backfill.final_report(market_db, result["targets"], lines.append)] == ["2026-10-20"]
    assert "SHORT" in "\n".join(lines)


def test_target_plan_is_frozen_as_json(market_db, monkeypatch, strategy):
    seed_tickers(market_db, SYMBOLS[:1])
    FakeYahoo(monkeypatch)
    run(market_db, strategy, start="2026-10-20", end="2026-10-21")
    plan = market_db.execute("SELECT target_dates FROM backfill_runs").fetchone()[0]
    assert json.loads(plan) == {"2026-10-20": "fill", "2026-10-21": "fill"}


def test_to_after_last_completed_session_is_clamped(market_db, monkeypatch, strategy):
    seed_tickers(market_db, SYMBOLS[:1])
    FakeYahoo(monkeypatch)
    result = run(market_db, strategy, start="2026-10-27", end="2026-10-30")
    assert list(result["targets"]) == ["2026-10-27", "2026-10-28"] and "using 2026-10-28" in result["output"]
