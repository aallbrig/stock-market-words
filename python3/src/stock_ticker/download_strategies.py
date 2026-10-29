"""
Download strategies for Yahoo Finance data extraction.

DownloadStrategy  — abstract base, defines the interface
BatchDownloadStrategy  — original behavior: yf.download() batches, exponential backoff, VPN on limit
PiaVpnDownloadStrategy — adaptive pacing: slows on 429, cycles PIA VPN after 30 s of rate limiting
"""

import abc
import time
from typing import Optional
import yfinance as yf
import pandas as pd
from yfinance import shared as yf_shared

from .logging_setup import setup_logging
from .retry import RetryTracker, BackoffLimitExceeded, get_retry_tracker, get_request_metrics
from .vpn_rotator import PiaVpnRotator, get_vpn_rotator

logger = setup_logging()


def _is_rate_limit_text(text: str) -> bool:
    msg = text.lower()
    return '429' in msg or 'rate limit' in msg or 'too many requests' in msg


def _is_no_data_text(text: str) -> bool:
    """Yahoo's answer for a symbol it no longer serves (delisted, merged, never listed)."""
    msg = text.lower()
    return 'no price data' in msg or 'delisted' in msg or 'no data found' in msg


def _is_rate_limit(exc: Exception) -> bool:
    return _is_rate_limit_text(str(exc))


def _symbol_frame(data: Optional[pd.DataFrame], symbol: str) -> pd.DataFrame:
    """One ticker's bars out of a yf.download(group_by='ticker') frame; empty when absent."""
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if symbol not in data.columns.get_level_values(0):
            return pd.DataFrame()
        frame = data[symbol]
    else:
        frame = data
    if 'Close' not in frame.columns:
        return pd.DataFrame()
    return frame.dropna(subset=['Close'])


class DownloadAborted(Exception):
    """Raised by a strategy when it can no longer make progress (exhausted retries/VPN)."""


class DownloadStrategy(abc.ABC):
    """
    Encapsulates how Yahoo Finance data is fetched: batching, rate limiting, retry.

    The extractors call these methods and only handle DB persistence; all
    network-level concerns (delays, backoff, VPN cycling) live here.
    """

    @abc.abstractmethod
    def fetch_price_batch(self, symbols: list) -> pd.DataFrame:
        """
        Download close price + volume for a batch of symbols.
        Blocks as needed to handle rate limiting.
        Raises DownloadAborted when unable to continue.
        """

    @abc.abstractmethod
    def fetch_ticker_info(self, symbol: str) -> dict:
        """
        Download yfinance Ticker.info dict for one symbol.
        Blocks as needed to handle rate limiting.
        Raises DownloadAborted when unable to continue.
        """

    @abc.abstractmethod
    def fetch_ticker_history(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """Download yfinance Ticker.history() for one symbol."""

    @abc.abstractmethod
    def inter_batch_pause(self):
        """Called between batches for polite pacing."""

    def _on_history_rate_limited(self, symbol_count: int):
        """Back off (sleep, rotate VPN) after a throttled history download; raise DownloadAborted to give up."""
        raise NotImplementedError

    def _on_history_ok(self):
        raise NotImplementedError

    def fetch_price_history(self, symbols: list, start: str, end: str) -> dict:
        """
        Raw (unadjusted) daily bars for `symbols` over [start, end) in ONE
        yf.download call, as {symbol: DataFrame(Open/High/Low/Close/Volume)}.
        A symbol Yahoo has no data for maps to an empty frame. A symbol whose
        request failed for any other reason (timeout, connection reset) maps to
        None so the caller can tell "no data" from "try again later".

        yf.download() swallows per-ticker failures, including HTTP 429, into
        yfinance.shared._ERRORS and just omits the column. Throttled tickers are
        picked out of that dict, the strategy's own backoff is applied, and only
        those tickers are requested again.
        """
        metrics = get_request_metrics()
        frames = {}
        remaining = list(symbols)
        while remaining:
            try:
                data = yf.download(
                    ' '.join(remaining), start=start, end=end, auto_adjust=False,
                    group_by='ticker', progress=False, threads=True
                )
                errors = dict(yf_shared._ERRORS)
            except Exception as e:
                if not _is_rate_limit(e):
                    raise
                data, errors = None, {s.upper(): repr(e) for s in remaining}
            # yfinance issues one chart request per ticker inside a download() call
            metrics.record_request('yahoo_finance', 'history_download')
            for _ in remaining:
                metrics.record_request('yahoo_finance', 'history_chart_request')
            limited = [s for s in remaining if _is_rate_limit_text(errors.get(s.upper(), ''))]
            for symbol in remaining:
                if symbol in limited:
                    continue
                error = errors.get(symbol.upper())
                frames[symbol] = None if error and not _is_no_data_text(error) else _symbol_frame(data, symbol)
            remaining = limited
            if remaining:
                logger.warning(f"Rate limit on {len(remaining)} of {len(symbols)} history symbols")
                self._on_history_rate_limited(len(remaining))
            else:
                self._on_history_ok()
        return frames


class BatchDownloadStrategy(DownloadStrategy):
    """
    Original batch-download behavior.

    - Prices: yf.download() in batches, 1 s inter-batch pause.
    - Metadata: yf.Ticker per symbol, 1 s inter-batch pause, exponential backoff on 429.
    - On BackoffLimitExceeded: tries PIA VPN rotation; raises DownloadAborted if that fails too.
    """

    _INTER_BATCH_SLEEP = 1.0

    def __init__(self, retry_tracker: Optional[RetryTracker] = None, vpn_rotator: Optional[PiaVpnRotator] = None):
        self._retry = retry_tracker or get_retry_tracker()
        self._vpn = vpn_rotator or get_vpn_rotator()

    def fetch_price_batch(self, symbols: list) -> pd.DataFrame:
        topic = 'yahoo_finance_batch'
        while True:
            try:
                data = yf.download(
                    ' '.join(symbols), period='1d', group_by='ticker',
                    progress=False, threads=True
                )
                self._retry.record_success(topic)
                return data
            except BackoffLimitExceeded:
                raise
            except Exception as e:
                if _is_rate_limit(e):
                    logger.warning(f"Rate limit on price batch ({len(symbols)} symbols)")
                    try:
                        self._retry.record_failure(topic)
                    except BackoffLimitExceeded:
                        self._try_vpn_or_abort(topic)
                else:
                    raise

    def fetch_ticker_info(self, symbol: str) -> dict:
        topic = f'yahoo_finance_metadata:{symbol}'
        while True:
            try:
                info = yf.Ticker(symbol).info
                self._retry.record_success(topic)
                return info
            except BackoffLimitExceeded:
                raise
            except Exception as e:
                if _is_rate_limit(e):
                    try:
                        self._retry.record_failure(topic)
                    except BackoffLimitExceeded:
                        self._try_vpn_or_abort(topic)
                else:
                    raise

    def fetch_ticker_history(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        return yf.Ticker(symbol).history(period=period)

    def inter_batch_pause(self):
        time.sleep(self._INTER_BATCH_SLEEP)

    def _on_history_rate_limited(self, symbol_count: int):
        topic = 'yahoo_finance_history'
        try:
            self._retry.record_failure(topic)
        except BackoffLimitExceeded:
            self._try_vpn_or_abort(topic)

    def _on_history_ok(self):
        self._retry.record_success('yahoo_finance_history')

    def _try_vpn_or_abort(self, topic: str):
        if self._vpn.should_rotate():
            logger.info("Backoff limit hit — attempting PIA VPN rotation...")
            if self._vpn.rotate_ip():
                logger.info("VPN rotated. Resetting backoff.")
                self._retry.reset(topic)
                time.sleep(3)
                return
            logger.error("VPN rotation failed.")
        else:
            logger.error("VPN rotation unavailable.")
        raise DownloadAborted(f"Cannot continue after backoff limit for {topic}")


class PiaVpnDownloadStrategy(DownloadStrategy):
    """
    Adaptive rate-limit strategy with PIA VPN IP cycling.

    Algorithm:
    - Start at initial_delay between requests (default 0.2 s).
    - On 429: double the current delay (up to max_delay), note when rate limiting started.
    - If 429 persists for > vpn_cycle_after_secs (default 30 s): cycle PIA VPN for a fresh IP.
    - After a successful request: halve the current delay (floor at initial_delay).
    - Degrades gracefully when piactl is unavailable (delay-only backoff, no abort).

    This strategy lets the pipeline run faster on good days (adaptive pacing),
    and recover from sustained throttling faster than exponential backoff alone.
    """

    _DEFAULT_INITIAL_DELAY = 0.2   # seconds between requests when healthy
    _DEFAULT_MAX_DELAY = 30.0      # maximum delay before VPN cycle takes over
    _DEFAULT_VPN_CYCLE_SECS = 30.0 # seconds of continuous 429 before VPN cycle

    def __init__(
        self,
        vpn_rotator: Optional[PiaVpnRotator] = None,
        initial_delay: float = _DEFAULT_INITIAL_DELAY,
        max_delay: float = _DEFAULT_MAX_DELAY,
        vpn_cycle_after_secs: float = _DEFAULT_VPN_CYCLE_SECS,
    ):
        self._vpn = vpn_rotator or get_vpn_rotator()
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._vpn_cycle_after_secs = vpn_cycle_after_secs
        self._current_delay = initial_delay
        self._rate_limit_start: float | None = None

    def _on_rate_limit(self, context: str):
        now = time.time()
        if self._rate_limit_start is None:
            self._rate_limit_start = now
            logger.warning(f"Rate limit detected ({context}). Slowing down.")

        elapsed = now - self._rate_limit_start
        self._current_delay = min(self._current_delay * 2, self._max_delay)

        if elapsed >= self._vpn_cycle_after_secs:
            if self._vpn.should_rotate():
                logger.info(
                    f"Rate limit sustained {elapsed:.0f}s >= {self._vpn_cycle_after_secs:.0f}s "
                    "— cycling PIA VPN for a fresh IP..."
                )
                if self._vpn.rotate_ip():
                    logger.info("VPN cycled. Resuming with reset delay.")
                    self._rate_limit_start = None
                    self._current_delay = self._initial_delay
                    time.sleep(3)
                    return
                logger.error("VPN cycle failed. Continuing with delay-only backoff.")
            else:
                logger.warning(
                    f"Rate limit sustained {elapsed:.0f}s but VPN unavailable. "
                    "Continuing with delay-only backoff."
                )

        logger.info(f"Waiting {self._current_delay:.1f}s before retry ({context})...")
        time.sleep(self._current_delay)

    def _on_success(self):
        if self._rate_limit_start is not None:
            logger.info("Rate limit cleared. Reducing inter-request delay.")
            self._rate_limit_start = None
        self._current_delay = max(self._current_delay / 2, self._initial_delay)

    def fetch_price_batch(self, symbols: list) -> pd.DataFrame:
        while True:
            try:
                data = yf.download(
                    ' '.join(symbols), period='1d', group_by='ticker',
                    progress=False, threads=True
                )
                self._on_success()
                return data
            except Exception as e:
                if _is_rate_limit(e):
                    self._on_rate_limit(f"price batch ({len(symbols)} symbols)")
                else:
                    raise

    def fetch_ticker_info(self, symbol: str) -> dict:
        while True:
            try:
                info = yf.Ticker(symbol).info
                self._on_success()
                return info
            except Exception as e:
                if _is_rate_limit(e):
                    self._on_rate_limit(f"ticker info {symbol}")
                else:
                    raise

    def fetch_ticker_history(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        try:
            hist = yf.Ticker(symbol).history(period=period)
            self._on_success()
            return hist
        except Exception as e:
            if _is_rate_limit(e):
                self._on_rate_limit(f"ticker history {symbol}")
                return pd.DataFrame()
            raise

    def inter_batch_pause(self):
        time.sleep(self._current_delay)

    def _on_history_rate_limited(self, symbol_count: int):
        self._on_rate_limit(f"history ({symbol_count} symbols)")

    def _on_history_ok(self):
        self._on_success()


def get_strategy(name: str) -> DownloadStrategy:
    """
    Factory function: resolve a strategy name from the CLI to a strategy instance.

    Names:
        'batch'   — BatchDownloadStrategy (default, original behavior)
        'pia-vpn' — PiaVpnDownloadStrategy (adaptive + VPN cycling)
    """
    if name == 'pia-vpn':
        logger.info("Download strategy: PIA VPN (adaptive rate limiting + VPN cycling)")
        return PiaVpnDownloadStrategy()
    if name == 'batch':
        logger.info("Download strategy: Batch (original behavior)")
        return BatchDownloadStrategy()
    raise ValueError(f"Unknown download strategy: {name!r}. Valid: 'batch', 'pia-vpn'")
