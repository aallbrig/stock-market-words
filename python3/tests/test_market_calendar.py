"""NYSE calendar helpers and the pre-close capture check."""
import sqlite3
from datetime import date, datetime, timezone

import pytest

from stock_ticker import market_calendar as mc


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


class TestTradingDays:
    def test_skips_weekends_and_exchange_holidays(self):
        days = mc.trading_days(date(2026, 7, 1), date(2026, 7, 8))
        # 2026-07-03 is the observed Independence Day closure (July 4 is a Saturday)
        assert days == [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8)]

    def test_good_friday_is_closed(self):
        assert date(2026, 4, 3) not in mc.trading_days(date(2026, 4, 1), date(2026, 4, 7))

    def test_empty_when_end_before_start(self):
        assert mc.trading_days(date(2026, 3, 2), date(2026, 3, 1)) == []


class TestMarketClose:
    def test_regular_day_is_4pm_eastern(self):
        assert mc.market_close_utc(date(2026, 10, 28)) == utc(2026, 10, 28, 20, 0)   # EDT
        assert mc.market_close_utc(date(2026, 1, 5)) == utc(2026, 1, 5, 21, 0)       # EST

    def test_early_close_day_after_thanksgiving(self):
        assert mc.market_close_utc(date(2026, 11, 27)) == utc(2026, 11, 27, 18, 0)

    def test_none_when_closed(self):
        assert mc.market_close_utc(date(2026, 10, 31)) is None  # Saturday


class TestLastCompletedTradingDay:
    def test_before_close_is_previous_session(self):
        assert mc.last_completed_trading_day(utc(2026, 10, 29, 19, 59)) == date(2026, 10, 28)

    def test_after_close_is_same_day(self):
        assert mc.last_completed_trading_day(utc(2026, 10, 29, 20, 0)) == date(2026, 10, 29)

    def test_weekend_is_friday(self):
        assert mc.last_completed_trading_day(utc(2026, 10, 31, 15, 0)) == date(2026, 10, 30)


@pytest.fixture
def steps_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE pipeline_steps (step_name TEXT, run_date DATE, completed_at TIMESTAMP, "
                 "tickers_processed INTEGER, status TEXT, PRIMARY KEY (step_name, run_date))")
    return conn


def record(conn, completed_at, day="2026-10-28", status="completed"):
    conn.execute("INSERT INTO pipeline_steps VALUES ('extract-prices', ?, ?, 10, ?)", (day, completed_at, status))


class TestCapturePredatesClose:
    DAY = date(2026, 10, 28)
    AFTER = utc(2026, 10, 28, 23, 0)

    def test_captured_mid_session_is_stale_after_close(self, steps_db):
        record(steps_db, "2026-10-28 15:07:12")  # 11:07 ET
        assert mc.capture_predates_close(steps_db, self.DAY, self.AFTER)

    def test_captured_after_close_is_fresh(self, steps_db):
        record(steps_db, "2026-10-28 20:00:01")
        assert not mc.capture_predates_close(steps_db, self.DAY, self.AFTER)

    def test_not_stale_while_market_still_open(self, steps_db):
        record(steps_db, "2026-10-28 15:07:12")
        assert not mc.capture_predates_close(steps_db, self.DAY, utc(2026, 10, 28, 19, 0))

    def test_in_progress_step_still_counts(self, steps_db):
        record(steps_db, "2026-10-28 15:07:12", status="in_progress")
        assert mc.capture_predates_close(steps_db, self.DAY, self.AFTER)

    def test_no_capture_nothing_to_replace(self, steps_db):
        assert not mc.capture_predates_close(steps_db, self.DAY, self.AFTER)

    def test_non_trading_day_never_stale(self, steps_db):
        record(steps_db, "2026-10-31 15:00:00", day="2026-10-31")
        assert not mc.capture_predates_close(steps_db, date(2026, 10, 31), utc(2026, 11, 1, 12, 0))

    def test_early_close_uses_actual_close(self, steps_db):
        record(steps_db, "2026-11-27 17:30:00", day="2026-11-27")  # 12:30 ET: before the 13:00 early close
        assert mc.capture_predates_close(steps_db, date(2026, 11, 27), utc(2026, 11, 27, 19, 0))
        steps_db.execute("UPDATE pipeline_steps SET completed_at = '2026-11-27 18:05:00'")
        assert not mc.capture_predates_close(steps_db, date(2026, 11, 27), utc(2026, 11, 27, 19, 0))
