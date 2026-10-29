"""technicals_series must equal compute_technicals evaluated at every prefix."""
import numpy as np
import pandas as pd
import pytest

from stock_ticker.technicals import TECHNICAL_COLUMNS, compute_technicals, technicals_series


def random_walk(n, seed):
    rng = np.random.default_rng(seed)
    close = 50 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    spread = rng.uniform(0.2, 1.5, n)
    index = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame({"High": close + spread, "Low": close - spread, "Close": close}, index=index)


def assert_matches(frame):
    series = technicals_series(frame)
    for i in range(len(frame)):
        scalar = compute_technicals(frame.iloc[: i + 1])
        for column in TECHNICAL_COLUMNS:
            got = series[column].iloc[i]
            if scalar[column] is None:
                assert pd.isna(got), f"{column}@{i}: expected None, got {got}"
            else:
                assert got == pytest.approx(scalar[column], rel=1e-9, abs=1e-9), f"{column}@{i}"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_series_matches_scalar_at_every_bar(seed):
    assert_matches(random_walk(260, seed))


def test_flat_prices_have_no_rsi():
    frame = random_walk(60, 4)
    frame["Close"] = 10.0
    frame["High"] = 10.5
    frame["Low"] = 9.5
    assert_matches(frame)
    assert pd.isna(technicals_series(frame)["rsi_14"].iloc[-1])


def test_monotonic_rise_has_rsi_100():
    frame = random_walk(60, 5)
    frame["Close"] = np.arange(1.0, 61.0)
    frame["High"] = frame["Close"] + 1
    frame["Low"] = frame["Close"] - 1
    assert_matches(frame)
    assert technicals_series(frame)["rsi_14"].iloc[-1] == pytest.approx(100.0)


def test_short_history_leaves_long_windows_empty():
    out = technicals_series(random_walk(30, 6))
    assert out["ma_200"].isna().all() and out["ma_50"].isna().all()
    assert out["atr_14"].iloc[:14].isna().all() and out["atr_14"].iloc[14:].notna().all()
