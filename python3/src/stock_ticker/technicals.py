"""
Price-derived indicators stored in daily_metrics (RSI-14, MA-50, MA-200,
20-day historical volatility, ATR-14).

`compute_technicals` is the formula `extract_metadata` has always used, moved
here unchanged. `technicals_series` evaluates the same formulas at every bar so
a backfill can fill many dates from one download; tests assert the two agree.
"""
import math

import numpy as np
import pandas as pd

TECHNICAL_COLUMNS = ("rsi_14", "ma_50", "ma_200", "hist_volatility", "atr_14")


def compute_technicals(hist: pd.DataFrame) -> dict:
    """Indicators as of the last bar of `hist` (columns Close/High/Low)."""
    ma_200 = hist['Close'].tail(200).mean() if not hist.empty and len(hist) >= 200 else None
    ma_50 = hist['Close'].tail(50).mean() if not hist.empty and len(hist) >= 50 else None

    rsi_14 = None
    if not hist.empty and len(hist) >= 14:
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        last_rs = rs.iloc[-1]
        rsi_14 = float(100 - (100 / (1 + last_rs))) if not pd.isna(last_rs) else None

    hist_volatility = None
    if not hist.empty and len(hist) >= 21:
        closes = hist['Close'].values.astype(float)
        log_ret = np.log(closes[1:] / closes[:-1])
        if len(log_ret) >= 20:
            vol = float(np.std(log_ret[-20:], ddof=1) * math.sqrt(252) * 100)
            hist_volatility = vol if not math.isnan(vol) else None

    atr_14 = None
    if not hist.empty and len(hist) >= 15:
        high = pd.Series(hist['High'].values)
        low = pd.Series(hist['Low'].values)
        close = pd.Series(hist['Close'].values)
        prev_close = close.shift(1)
        true_range = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        last_atr = true_range.rolling(14).mean().iloc[-1]
        atr_14 = float(last_atr) if not pd.isna(last_atr) else None

    return {
        'rsi_14': rsi_14,
        'ma_50': ma_50,
        'ma_200': ma_200,
        'hist_volatility': hist_volatility,
        'atr_14': atr_14,
    }


def technicals_series(hist: pd.DataFrame) -> pd.DataFrame:
    """
    `compute_technicals(hist.iloc[:i + 1])` for every row i, computed once.
    `hist` must be NaN-free on Close and ordered by date.
    """
    close = hist['Close'].astype(float)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    log_ret = np.log(close / close.shift(1))
    volatility = log_ret.rolling(20).std(ddof=1) * math.sqrt(252) * 100

    prev_close = close.shift(1)
    true_range = pd.concat(
        [hist['High'] - hist['Low'], (hist['High'] - prev_close).abs(), (hist['Low'] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(14).mean()
    atr.iloc[:14] = np.nan  # the scalar form needs 15 bars

    out = pd.DataFrame({
        'rsi_14': rsi,
        'ma_50': close.rolling(50).mean(),
        'ma_200': close.rolling(200).mean(),
        'hist_volatility': volatility,
        'atr_14': atr,
    }, index=hist.index)
    return out.replace([np.inf, -np.inf], np.nan)
