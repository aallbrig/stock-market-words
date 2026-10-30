"""
NYSE trading-calendar helpers shared by the daily close guard and the backfill.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from .logging_setup import setup_logging

logger = setup_logging()

NEW_YORK = ZoneInfo("America/New_York")
REGULAR_CLOSE = dtime(16, 0)


def utc_now() -> datetime:
    """Current time as an aware UTC datetime (patched in tests)."""
    return datetime.now(timezone.utc)


@lru_cache(maxsize=1)
def _nyse():
    import pandas_market_calendars as mcal
    return mcal.get_calendar("NYSE")


def trading_days(start: date, end: date) -> list[date]:
    """NYSE sessions in [start, end], inclusive."""
    if end < start:
        return []
    schedule = _nyse().schedule(start_date=start, end_date=end)
    return [ts.date() for ts in schedule.index]


def market_close_utc(day: date) -> datetime | None:
    """
    Aware UTC close time of the NYSE session on `day` (13:00 ET on early-close
    days, otherwise 16:00 ET), or None when the market is closed that day.

    Falls back to weekday 16:00 America/New_York when the calendar library is
    not installed, so the daily run never depends on it to start.
    """
    try:
        schedule = _nyse().schedule(start_date=day, end_date=day)
    except ImportError:
        logger.warning("pandas_market_calendars not installed; assuming a 16:00 ET close on weekdays")
        if day.weekday() >= 5:
            return None
        return datetime.combine(day, REGULAR_CLOSE, tzinfo=NEW_YORK).astimezone(timezone.utc)
    if schedule.empty:
        return None
    return schedule["market_close"].iloc[0].to_pydatetime().astimezone(timezone.utc)


def last_completed_trading_day(now: datetime | None = None) -> date:
    """Most recent NYSE session whose close is at or before `now`."""
    now = now or utc_now()
    today = now.astimezone(NEW_YORK).date()
    schedule = _nyse().schedule(start_date=today - timedelta(days=14), end_date=today)
    for session, row in reversed(list(schedule.iterrows())):
        if row["market_close"].to_pydatetime() <= now:
            return session.date()
    raise RuntimeError(f"No completed NYSE session found in the 14 days before {today}")


def _parse_utc(timestamp: str) -> datetime:
    """pipeline_steps.completed_at is SQLite CURRENT_TIMESTAMP: naive UTC text."""
    return datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def capture_predates_close(conn, day: date, now: datetime | None = None) -> bool:
    """
    True when `day`'s prices were last written before that session's close and
    the close has since passed, i.e. the stored rows are an intraday snapshot
    that a later run should replace.

    Uses pipeline_steps.completed_at for 'extract-prices' as the last-write time
    (record_pipeline_step refreshes it every 5 batches and on completion). A run
    that straddles the close counts as post-close; the nightly timer (23:00)
    cannot straddle it.
    """
    now = now or utc_now()
    close = market_close_utc(day)
    if close is None or now < close:
        return False
    row = conn.execute(
        "SELECT completed_at FROM pipeline_steps WHERE step_name = 'extract-prices' AND run_date = ?",
        (day.isoformat(),),
    ).fetchone()
    if not row or not row[0]:
        return False
    return _parse_utc(row[0]) < close
