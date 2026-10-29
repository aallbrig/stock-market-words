"""
The daily run: unchanged when the capture is fresh, and a later run replaces
rows that were captured before the 4pm ET close.
"""
from datetime import datetime, timezone
from unittest import mock

import pytest
from click.testing import CliRunner

from stock_ticker import extractors
from stock_ticker.cli import cli
from stock_ticker.download_strategies import DownloadStrategy
from tests.conftest import fake_bars, fake_close

TODAY = "2026-10-28"
AFTER_CLOSE = datetime(2026, 10, 28, 23, 0, tzinfo=timezone.utc)
BEFORE_CLOSE = datetime(2026, 10, 28, 18, 0, tzinfo=timezone.utc)
SYMBOLS = ["AAA", "BBB", "CCC"]


class DailyStrategy(DownloadStrategy):
    """fetch_price_batch takes only `symbols`, exactly as the daily path has always called it."""

    def __init__(self, level=100.0):
        self.level = level
        self.calls = []

    def fetch_price_batch(self, symbols):
        self.calls.append(list(symbols))
        bars = fake_bars(symbols, TODAY, "2026-10-29", base={s: self.level + n for n, s in enumerate(SYMBOLS)})
        return bars.drop(columns="Adj Close", level=1)  # a period='1d' download has no Adj Close column

    def fetch_ticker_info(self, symbol):
        raise NotImplementedError

    def fetch_ticker_history(self, symbol, period="1y"):
        raise NotImplementedError

    def inter_batch_pause(self):
        pass


@pytest.fixture
def daily_db(market_db, monkeypatch):
    market_db.executemany("INSERT INTO tickers (symbol, name, exchange, is_etf) VALUES (?, ?, 'NASDAQ', 0)",
                          [(s, s) for s in SYMBOLS])
    market_db.execute("INSERT INTO tickers (symbol, name, exchange, is_etf) VALUES ('SPY', 'SPY', 'NYSE', 1)")
    market_db.commit()
    for module in ("stock_ticker.extractors", "stock_ticker.database", "stock_ticker.cli"):
        monkeypatch.setattr(f"{module}.get_today", lambda: TODAY)
    return market_db


def set_clock(monkeypatch, now):
    monkeypatch.setattr("stock_ticker.market_calendar.utc_now", lambda: now)


def seed_today(conn, price=1.0, market_cap=None, captured_at=None):
    conn.executemany("INSERT INTO daily_metrics (symbol, date, price, volume, market_cap) VALUES (?, ?, ?, 10, ?)",
                     [(s, TODAY, price, market_cap) for s in SYMBOLS])
    if captured_at:
        conn.execute("INSERT OR REPLACE INTO pipeline_steps VALUES ('extract-prices', ?, ?, 3, 'completed')",
                     (TODAY, captured_at))
    conn.commit()


def prices(conn):
    return dict(conn.execute("SELECT symbol, price FROM daily_metrics WHERE date = ?", (TODAY,)).fetchall())


class TestExtractPricesUnchangedWhenFresh:
    """Regression: the normal daily path behaves exactly as before the guard existed."""

    def test_fetches_every_non_etf_ticker_once_and_stores_the_bars(self, daily_db, monkeypatch):
        set_clock(monkeypatch, AFTER_CLOSE)
        strategy = DailyStrategy()
        extractors.extract_prices(strategy=strategy)
        assert strategy.calls == [SYMBOLS]  # ETF excluded, a single batch, called with symbols only
        rows = daily_db.execute(
            "SELECT symbol, price, volume, open_price, high_price, low_price, adj_close, market_cap "
            "FROM daily_metrics WHERE date = ? ORDER BY symbol", (TODAY,)).fetchall()
        assert len(rows) == 3
        symbol, price, volume, open_, high, low, adj, cap = rows[1]
        assert (symbol, volume, adj, cap) == ("BBB", 1_000_010, None, None)
        assert (open_, high, low) == (pytest.approx(price - 0.5), pytest.approx(price + 1), pytest.approx(price - 1))
        step = daily_db.execute("SELECT status, tickers_processed FROM pipeline_steps "
                                "WHERE step_name = 'extract-prices'").fetchone()
        assert step == ("completed", 3)

    def test_only_tickers_without_a_price_today_are_fetched(self, daily_db, monkeypatch):
        set_clock(monkeypatch, AFTER_CLOSE)
        daily_db.execute("INSERT INTO daily_metrics (symbol, date, price, volume) VALUES ('AAA', ?, 1.0, 10)", (TODAY,))
        daily_db.commit()
        strategy = DailyStrategy()
        extractors.extract_prices(strategy=strategy)
        assert strategy.calls == [["BBB", "CCC"]]
        assert prices(daily_db)["AAA"] == 1.0

    def test_capture_after_the_close_is_not_refetched(self, daily_db, monkeypatch):
        set_clock(monkeypatch, AFTER_CLOSE)
        seed_today(daily_db, captured_at="2026-10-28 21:30:00")  # 17:30 ET
        strategy = DailyStrategy()
        extractors.extract_prices(strategy=strategy)
        assert strategy.calls == [] and set(prices(daily_db).values()) == {1.0}

    def test_before_the_close_nothing_better_exists_so_nothing_is_refetched(self, daily_db, monkeypatch):
        set_clock(monkeypatch, BEFORE_CLOSE)
        seed_today(daily_db, captured_at="2026-10-28 15:07:12")
        strategy = DailyStrategy()
        extractors.extract_prices(strategy=strategy)
        assert strategy.calls == []


class TestPreCloseCaptureIsReplaced:
    def test_later_run_replaces_rows_written_before_the_close(self, daily_db, monkeypatch):
        set_clock(monkeypatch, AFTER_CLOSE)
        seed_today(daily_db, price=1.0, market_cap=9e9, captured_at="2026-10-28 15:07:12")  # 11:07 ET
        strategy = DailyStrategy(level=200.0)
        extractors.extract_prices(strategy=strategy)
        assert strategy.calls == [SYMBOLS]
        assert prices(daily_db) == {s: pytest.approx(fake_close(200.0 + n, TODAY)) for n, s in enumerate(SYMBOLS)}
        # same replace semantics as the daily path: metadata is cleared so extract-metadata refreshes it
        assert daily_db.execute("SELECT COUNT(market_cap) FROM daily_metrics WHERE date = ?", (TODAY,)).fetchone()[0] == 0

    def test_replacement_happens_once(self, daily_db, monkeypatch):
        set_clock(monkeypatch, AFTER_CLOSE)
        seed_today(daily_db, captured_at="2026-10-28 15:07:12")
        strategy = DailyStrategy()
        extractors.extract_prices(strategy=strategy)
        extractors.extract_prices(strategy=strategy)
        assert len(strategy.calls) == 1  # the refreshed capture is stamped after the close

    def test_interrupted_pre_close_run_is_refreshed_not_resumed(self, daily_db, monkeypatch):
        set_clock(monkeypatch, AFTER_CLOSE)
        seed_today(daily_db, captured_at="2026-10-28 15:07:12")
        daily_db.execute("UPDATE pipeline_steps SET status = 'in_progress'")
        daily_db.commit()
        strategy = DailyStrategy()
        extractors.extract_prices(strategy=strategy)
        assert strategy.calls == [SYMBOLS]


@pytest.fixture
def pipeline(daily_db, monkeypatch):
    """run-all with every step stubbed so only the orchestration is exercised."""
    order = []
    sentinel = object()

    def step(name):
        return mock.Mock(side_effect=lambda *a, **k: order.append(name))

    mocks = {name: step(name) for name in ("sync-ftp", "extract-prices", "extract-metadata", "build", "generate-hugo")}
    patches = {
        "sync_ftp": mocks["sync-ftp"], "extract_prices": mocks["extract-prices"],
        "extract_metadata": mocks["extract-metadata"], "build_assets": mocks["build"],
        "generate_all_hugo_content": mocks["generate-hugo"],
        "check_ftp_server": lambda host: True, "check_yahoo_finance": lambda host: True,
        "get_strategy": lambda name: sentinel, "print_pipeline_summary": lambda: None,
    }
    for attr, value in patches.items():
        monkeypatch.setattr(f"stock_ticker.cli.{attr}", value)
    monkeypatch.setattr("stock_ticker.utils.check_ftp_server", lambda host: True)
    monkeypatch.setattr("stock_ticker.utils.check_yahoo_finance", lambda host: True)
    return order, mocks, sentinel


def complete_all_steps(conn, completed_at):
    conn.executemany("INSERT INTO pipeline_steps VALUES (?, ?, ?, 3, 'completed')",
                     [(name, TODAY, completed_at) for name in
                      ("sync-ftp", "extract-prices", "extract-metadata", "build", "generate-hugo")])
    conn.commit()


class TestRunAll:
    def test_ordinary_day_runs_all_five_steps_once_in_order(self, daily_db, pipeline, monkeypatch):
        order, mocks, sentinel = pipeline
        set_clock(monkeypatch, AFTER_CLOSE)
        result = CliRunner().invoke(cli, ["run-all", "--limit", "7"])
        assert result.exit_code == 0, result.output
        assert order == ["sync-ftp", "extract-prices", "extract-metadata", "build", "generate-hugo"]
        kwargs = mocks["extract-prices"].call_args.kwargs
        assert (kwargs["limit"], kwargs["strategy"], isinstance(kwargs["run_id"], int)) == (7, sentinel, True)
        assert mocks["extract-metadata"].call_args.kwargs["limit"] == 7

    def test_already_completed_fresh_day_does_nothing(self, daily_db, pipeline, monkeypatch, caplog):
        order, _, _ = pipeline
        set_clock(monkeypatch, AFTER_CLOSE)
        complete_all_steps(daily_db, "2026-10-28 22:00:00")
        result = CliRunner().invoke(cli, ["run-all"])
        assert result.exit_code == 0 and order == []
        assert "already completed" in caplog.text

    def test_completed_pre_close_day_is_rebuilt_after_the_close(self, daily_db, pipeline, monkeypatch):
        order, _, _ = pipeline
        set_clock(monkeypatch, AFTER_CLOSE)
        complete_all_steps(daily_db, "2026-10-28 15:07:12")
        result = CliRunner().invoke(cli, ["run-all"])
        assert result.exit_code == 0, result.output
        # the ticker list is not price-derived, so sync-ftp is kept; everything downstream reruns
        assert order == ["extract-prices", "extract-metadata", "build", "generate-hugo"]

    def test_completed_pre_close_day_is_left_alone_while_the_market_is_open(self, daily_db, pipeline, monkeypatch):
        order, _, _ = pipeline
        set_clock(monkeypatch, BEFORE_CLOSE)
        complete_all_steps(daily_db, "2026-10-28 15:07:12")
        assert CliRunner().invoke(cli, ["run-all"]).exit_code == 0
        assert order == []

    def test_dry_run_is_untouched(self, daily_db, pipeline, monkeypatch):
        order, _, _ = pipeline
        set_clock(monkeypatch, AFTER_CLOSE)
        complete_all_steps(daily_db, "2026-10-28 15:07:12")
        result = CliRunner().invoke(cli, ["--dry-run", "run-all"])
        assert result.exit_code == 0 and order == []
