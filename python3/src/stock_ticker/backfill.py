"""
Historical price backfill.

Finds NYSE sessions that are missing from, or only partly present in,
daily_metrics, downloads each ticker's bars for the whole span in one yfinance
call per batch, and upserts them through the same row builder `extract_prices`
uses. Progress is journaled in backfill_runs / backfill_symbols (migration 008)
so a crash or rate-limit abort resumes where it stopped.
"""
from __future__ import annotations

import json
import math
import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import click
import pandas as pd

from .builders import recompute_strategy_scores
from .config import PRICE_BATCH_SIZE
from .download_strategies import DownloadStrategy
from .extractors import price_row_from_bar
from .logging_setup import setup_logging
from .market_calendar import capture_predates_close, last_completed_trading_day, trading_days, utc_now
from .migrations import MIGRATIONS_DIR
from .retry import get_request_metrics
from .technicals import TECHNICAL_COLUMNS, technicals_series

logger = setup_logging()

# A session is "incomplete" when it holds fewer price rows than GAP_RATIO times
# the median of the BASELINE_NEIGHBORS nearest populated dates on each side
# (healthy days in the local database sit at 0.92-1.05 of that median), or fewer
# than UNIVERSE_FLOOR times the ticker universe. The floor catches stretches of
# equally partial sessions, whose neighbours are no better than they are.
GAP_RATIO = 0.85
BASELINE_NEIGHBORS = 5
UNIVERSE_FLOOR = 0.75

# Trading bars needed before the first target date for MA-200 (200 bars is
# ~290 calendar days; the slack covers holidays).
LOOKBACK_DAYS = 320

FILL = "fill"        # insert rows that are absent, leave existing rows alone
REPLACE = "replace"  # overwrite price columns (intraday snapshot, or --refetch)

_PRICE_SET = (
    "price = excluded.price, volume = excluded.volume, open_price = excluded.open_price, "
    "high_price = excluded.high_price, low_price = excluded.low_price, adj_close = excluded.adj_close"
)
_TECH_SET = ", ".join(f"{c} = excluded.{c}" for c in TECHNICAL_COLUMNS)
_PRICE_COLS = "symbol, date, price, volume, open_price, high_price, low_price, adj_close"


def _upsert_sql(with_technicals: bool) -> str:
    cols = _PRICE_COLS + (", " + ", ".join(TECHNICAL_COLUMNS) if with_technicals else "")
    marks = ", ".join("?" * (8 + (len(TECHNICAL_COLUMNS) if with_technicals else 0)))
    sets = _PRICE_SET + (", " + _TECH_SET if with_technicals else "")
    return (
        f"INSERT INTO daily_metrics ({cols}) VALUES ({marks}) "
        f"ON CONFLICT(symbol, date) DO UPDATE SET {sets}"
    )


@dataclass
class DatePlan:
    day: date
    rows: int
    baseline: Optional[float]
    reason: str          # missing | incomplete | preclose | refetch (<one of those, or complete>)
    mode: str            # FILL | REPLACE


@dataclass
class GapReport:
    start: date
    end: date
    sessions: list[date]
    targets: list[DatePlan] = field(default_factory=list)
    settled_short: list[DatePlan] = field(default_factory=list)  # still short after an earlier backfill
    non_trading_rows: dict[date, int] = field(default_factory=dict)
    counts: dict[date, int] = field(default_factory=dict)
    baselines: dict[date, Optional[float]] = field(default_factory=dict)

    @property
    def target_modes(self) -> dict[str, str]:
        return {p.day.isoformat(): p.mode for p in self.targets}


# ── ledger ──────────────────────────────────────────────────────────────────

def _has_ledger(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'backfill_runs'"
    ).fetchone() is not None


def ensure_progress_tables(conn: sqlite3.Connection) -> None:
    """Create the ledger tables from migration 008 (idempotent; also applied by `migrate up`)."""
    conn.executescript(Path(MIGRATIONS_DIR, "008_backfill_progress.sql").read_text())


def _settled_dates(conn: sqlite3.Connection) -> set[date]:
    """Dates a completed full-universe backfill already tried; not retried unless --refetch."""
    if not _has_ledger(conn):
        return set()
    settled: set[date] = set()
    for (blob,) in conn.execute(
        "SELECT target_dates FROM backfill_runs WHERE status = 'completed' AND symbol_limit IS NULL"
    ):
        settled.update(date.fromisoformat(d) for d in json.loads(blob))
    return settled


# ── gap detection ───────────────────────────────────────────────────────────

def _price_row_counts(conn: sqlite3.Connection) -> dict[date, int]:
    return {
        date.fromisoformat(d): n
        for d, n in conn.execute(
            "SELECT date, COUNT(*) FROM daily_metrics WHERE price IS NOT NULL GROUP BY date"
        )
    }


def _baseline(day: date, counts: dict[date, int], universe: int) -> Optional[float]:
    """Median row count of the nearest populated dates on either side of `day`."""
    dates = sorted(d for d, n in counts.items() if n > 0 and d != day)
    before = [counts[d] for d in dates if d < day][-BASELINE_NEIGHBORS:]
    after = [counts[d] for d in dates if d > day][:BASELINE_NEIGHBORS]
    neighbours = before + after
    if neighbours:
        return float(statistics.median(neighbours))
    return float(universe) if universe else None


def _is_short(rows: int, baseline: Optional[float], universe: int) -> bool:
    return (
        rows == 0
        or (baseline is not None and rows < GAP_RATIO * baseline)
        or rows < UNIVERSE_FLOOR * universe
    )


def analyze_gaps(
    conn: sqlite3.Connection, start: date, end: date, *, refetch: bool = False, now: Optional[datetime] = None
) -> GapReport:
    """Classify every NYSE session in [start, end]; see module constants for the thresholds."""
    now = now or utc_now()
    sessions = trading_days(start, end)
    counts = _price_row_counts(conn)
    universe = conn.execute("SELECT COUNT(*) FROM tickers WHERE is_etf = 0").fetchone()[0]
    settled = _settled_dates(conn)
    report = GapReport(start=start, end=end, sessions=sessions, counts=counts)

    for day in sessions:
        rows = counts.get(day, 0)
        baseline = _baseline(day, counts, universe)
        report.baselines[day] = baseline
        short = _is_short(rows, baseline, universe)
        if rows == 0:
            reason, mode = "missing", FILL
        elif capture_predates_close(conn, day, now):
            reason, mode = "preclose", REPLACE
        elif short:
            reason, mode = "incomplete", FILL
        elif refetch:
            reason, mode = "complete", FILL
        else:
            continue
        if refetch:
            reason, mode = f"refetch ({reason})", REPLACE
        plan = DatePlan(day, rows, baseline, reason, mode)
        if day in settled and not refetch and plan.reason != "preclose":
            report.settled_short.append(plan)
        else:
            report.targets.append(plan)

    session_set = set(sessions)
    report.non_trading_rows = {d: n for d, n in counts.items() if start <= d <= end and d not in session_set}
    return report


def estimate_requests(symbols: int, target_days: int) -> dict[str, int]:
    """Yahoo traffic for one backfill versus fetching a day at a time."""
    calls = math.ceil(symbols / PRICE_BATCH_SIZE)
    return {
        "download_calls": calls,                    # yf.download() invocations
        "chart_requests": symbols,                  # yfinance sends one chart request per ticker
        "per_day_download_calls": calls * target_days,
        "per_day_chart_requests": symbols * target_days,
    }


def print_gap_report(report: GapReport, echo: Callable[[str], None] = click.echo) -> None:
    echo(f"Range {report.start} .. {report.end}: {len(report.sessions)} NYSE sessions, "
         f"{len(report.targets)} need work")
    echo(f"Incomplete threshold: rows < {GAP_RATIO:.0%} of the median of the "
         f"{BASELINE_NEIGHBORS} nearest populated dates on each side, or < {UNIVERSE_FLOOR:.0%} of the ticker universe")
    for plan in report.targets:
        base = f"{plan.baseline:,.0f}" if plan.baseline is not None else "n/a"
        echo(f"  {plan.day}  rows={plan.rows:>6,}  baseline={base:>6}  {plan.reason:<22} -> {plan.mode}")
    for plan in report.settled_short:
        echo(f"  {plan.day}  rows={plan.rows:>6,}  still short after an earlier backfill "
             "(skipped; --refetch to retry)")
    if report.non_trading_rows:
        echo("Rows stamped on non-trading days (left untouched):")
        for day, n in sorted(report.non_trading_rows.items()):
            echo(f"  {day} ({day:%a})  rows={n:,}")


# ── run ─────────────────────────────────────────────────────────────────────

def _find_unfinished(conn, start: date, refetch: bool, limit: Optional[int]):
    return conn.execute(
        "SELECT run_id, range_from, range_to, target_dates FROM backfill_runs "
        "WHERE status IN ('running', 'failed') AND range_from = ? AND refetch = ? "
        "AND IFNULL(symbol_limit, -1) = IFNULL(?, -1) ORDER BY run_id DESC LIMIT 1",
        (start.isoformat(), int(refetch), limit),
    ).fetchone()


def _universe(conn, limit: Optional[int]) -> list[str]:
    symbols = [r[0] for r in conn.execute("SELECT symbol FROM tickers WHERE is_etf = 0 ORDER BY symbol")]
    return symbols[:limit] if limit else symbols


def _rows_for_symbol(symbol: str, frame: pd.DataFrame, targets: dict[str, str], existing: set,
                     derived: bool) -> list[tuple]:
    """Upsert tuples for the target sessions found in `frame`."""
    if frame.empty:
        return []
    frame = frame.drop(columns=["Adj Close"], errors="ignore")  # the daily run stores adj_close NULL
    tech = technicals_series(frame) if derived else None
    out = []
    for ts, bar in frame.iterrows():
        iso = pd.Timestamp(ts).date().isoformat()
        mode = targets.get(iso)
        if mode is None or (mode == FILL and (symbol, iso) in existing):
            continue
        try:
            row, _ = price_row_from_bar(symbol, iso, bar)
        except Exception as exc:
            logger.debug(f"Skipping {symbol} {iso}: {exc}")
            continue
        if row is None:
            continue
        if tech is not None:
            values = tech.loc[ts]
            row = row + tuple(None if pd.isna(values[c]) else float(values[c]) for c in TECHNICAL_COLUMNS)
        out.append(row)
    return out


def _existing_keys(conn, symbols: list[str], target_days: list[str]) -> set:
    marks_s, marks_d = ",".join("?" * len(symbols)), ",".join("?" * len(target_days))
    cur = conn.execute(
        f"SELECT symbol, date FROM daily_metrics WHERE price IS NOT NULL "
        f"AND symbol IN ({marks_s}) AND date IN ({marks_d})",
        [*symbols, *target_days],
    )
    return set(cur.fetchall())


def run_backfill(
    conn: sqlite3.Connection,
    start: date,
    end: Optional[date] = None,
    *,
    strategy: Optional[DownloadStrategy] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    refetch: bool = False,
    restart: bool = False,
    derived: bool = True,
    now: Optional[datetime] = None,
    echo: Callable[[str], None] = click.echo,
) -> dict:
    """Detect gaps and fill them. Returns a summary dict (also used by tests)."""
    now = now or utc_now()
    last_session = last_completed_trading_day(now)
    if end is None or end > last_session:
        if end is not None:
            echo(f"--to {end} is after the last completed session; using {last_session}")
        end = last_session
    if start > end:
        raise click.UsageError(f"--from {start} is after the end of the range ({end})")

    ledger = _has_ledger(conn)
    if not dry_run:
        ensure_progress_tables(conn)
        ledger = True

    resumed = None
    run_id = None
    if ledger:
        if restart:
            if not dry_run:
                conn.execute(
                    "UPDATE backfill_runs SET status = 'abandoned' WHERE status IN ('running', 'failed') "
                    "AND range_from = ? AND refetch = ? AND IFNULL(symbol_limit, -1) = IFNULL(?, -1)",
                    (start.isoformat(), int(refetch), limit),
                )
                conn.commit()
        else:
            resumed = _find_unfinished(conn, start, refetch, limit)

    if resumed:
        run_id, r_from, r_to, blob = resumed
        targets = json.loads(blob)
        echo(f"Resuming backfill run #{run_id} ({r_from} .. {r_to}) with its original "
             f"{len(targets)} target sessions; --restart discards it")
        report = None
    else:
        report = analyze_gaps(conn, start, end, refetch=refetch, now=now)
        print_gap_report(report, echo)
        targets = report.target_modes

    symbols = _universe(conn, limit)
    done: set[str] = set()
    if resumed:
        done = {r[0] for r in conn.execute("SELECT symbol FROM backfill_symbols WHERE run_id = ?", (run_id,))}
    todo = [s for s in symbols if s not in done]
    estimate = estimate_requests(len(todo) if targets else 0, len(targets))

    summary = {"targets": targets, "symbols": len(symbols), "todo": len(todo), "estimate": estimate,
               "report": report, "run_id": None, "rows_written": 0, "download_calls": 0}
    echo(f"Estimated Yahoo traffic: {estimate['download_calls']} yf.download calls "
         f"(~{estimate['chart_requests']:,} chart requests, one per ticker) for {len(todo):,} tickers; "
         f"fetching one session at a time would need {estimate['per_day_download_calls']:,} calls "
         f"(~{estimate['per_day_chart_requests']:,} chart requests)")
    if dry_run:
        echo("DRY RUN: no data fetched, no rows written")
        return summary
    if not targets:
        echo("Nothing to backfill")
        return summary

    if not resumed:
        cur = conn.execute(
            "INSERT INTO backfill_runs (range_from, range_to, refetch, symbol_limit, target_dates, status, "
            "symbols_total) VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (start.isoformat(), end.isoformat(), int(refetch), limit, json.dumps(targets), len(symbols)),
        )
        run_id = cur.lastrowid
        conn.commit()
    summary["run_id"] = run_id

    if strategy is None:
        from .download_strategies import BatchDownloadStrategy
        strategy = BatchDownloadStrategy()

    target_days = sorted(targets)
    first = date.fromisoformat(target_days[0])
    fetch_start = (first - timedelta(days=LOOKBACK_DAYS if derived else 0)).isoformat()
    fetch_end = (date.fromisoformat(target_days[-1]) + timedelta(days=1)).isoformat()  # end is exclusive
    sql = _upsert_sql(derived)
    metrics = get_request_metrics()
    calls_before = metrics.get_counts().get("yahoo_finance", {}).get("history_download", 0)
    calls_prior = conn.execute("SELECT download_calls FROM backfill_runs WHERE run_id = ?", (run_id,)).fetchone()[0]

    errored: list[str] = []
    try:
        batches = [todo[i:i + PRICE_BATCH_SIZE] for i in range(0, len(todo), PRICE_BATCH_SIZE)]
        for number, batch in enumerate(batches, 1):
            echo(f"Batch {number}/{len(batches)} ({len(batch)} tickers) {fetch_start} .. {fetch_end}")
            frames = strategy.fetch_price_history(batch, fetch_start, fetch_end)
            existing = _existing_keys(conn, batch, target_days)
            rows, per_symbol = [], []
            for symbol in batch:
                frame = frames.get(symbol, pd.DataFrame())
                if frame is None:  # failed for a reason other than "no data": leave it unjournaled to retry
                    errored.append(symbol)
                    continue
                symbol_rows = _rows_for_symbol(symbol, frame, targets, existing, derived)
                rows.extend(symbol_rows)
                per_symbol.append((run_id, symbol, len(symbol_rows)))
            calls = metrics.get_counts().get("yahoo_finance", {}).get("history_download", 0) - calls_before
            conn.executemany(sql, rows)
            conn.executemany("INSERT OR REPLACE INTO backfill_symbols (run_id, symbol, rows_written) VALUES (?, ?, ?)",
                             per_symbol)
            conn.execute("UPDATE backfill_runs SET rows_written = rows_written + ?, download_calls = ? "
                         "WHERE run_id = ?", (len(rows), calls_prior + calls, run_id))
            conn.commit()
            summary["rows_written"] += len(rows)
            echo(f"  wrote {len(rows):,} rows")
            if number < len(batches):
                strategy.inter_batch_pause()

        if derived:
            for iso, mode in sorted(targets.items()):
                if mode == REPLACE:
                    scored = recompute_strategy_scores(conn, iso)
                    if scored:
                        echo(f"Recomputed strategy_scores for {iso} ({scored:,} tickers)")
        if errored:
            raise click.ClickException(
                f"{len(errored)} ticker(s) failed with errors other than 'no data' "
                f"(e.g. {', '.join(errored[:5])}); re-run the same command to retry them"
            )
        if not limit:
            # The replaced sessions now hold post-close data; stamp the step like extract_prices
            # would, or capture_predates_close keeps flagging them and every run refetches them.
            conn.executemany(
                "UPDATE pipeline_steps SET completed_at = CURRENT_TIMESTAMP "
                "WHERE step_name = 'extract-prices' AND run_date = ?",
                [(iso,) for iso, mode in targets.items() if mode == REPLACE],
            )
            conn.commit()
    except BaseException as exc:
        conn.rollback()
        conn.execute("UPDATE backfill_runs SET status = 'failed', error_message = ?, finished_at = CURRENT_TIMESTAMP "
                     "WHERE run_id = ?", (f"{type(exc).__name__}: {exc}"[:500], run_id))
        conn.commit()
        echo(f"Backfill run #{run_id} stopped: {exc}. Re-run the same command to resume.")
        raise

    summary["download_calls"] = metrics.get_counts().get("yahoo_finance", {}).get("history_download", 0) - calls_before
    conn.execute("UPDATE backfill_runs SET status = 'completed', finished_at = CURRENT_TIMESTAMP WHERE run_id = ?",
                 (run_id,))
    conn.commit()
    return summary


def final_report(conn: sqlite3.Connection, targets: dict[str, str], echo: Callable[[str], None] = click.echo,
                 limit: Optional[int] = None) -> list:
    """
    Row counts for each target session after the run; returns the sessions still below threshold.
    A --limit run only fetched N tickers, so completeness is not judged.
    """
    counts = _price_row_counts(conn)
    universe = conn.execute("SELECT COUNT(*) FROM tickers WHERE is_etf = 0").fetchone()[0]
    still_short = []
    echo("Rows per backfilled session (price NOT NULL):")
    if limit:
        echo(f"  (--limit {limit}: only the first {limit} tickers were fetched, completeness is not judged)")
    for iso in sorted(targets):
        day = date.fromisoformat(iso)
        rows, baseline = counts.get(day, 0), _baseline(day, counts, universe)
        base = f"{baseline:,.0f}" if baseline is not None else "n/a"
        if limit:
            echo(f"  {iso}  rows={rows:>6,}")
            continue
        short = _is_short(rows, baseline, universe)
        echo(f"  {iso}  rows={rows:>6,}  baseline={base:>6}  {'SHORT' if short else 'ok'}")
        if short:
            still_short.append((iso, rows, baseline))
    return still_short
