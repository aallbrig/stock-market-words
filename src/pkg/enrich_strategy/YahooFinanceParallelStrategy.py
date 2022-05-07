import time
from logging import debug

from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
import yfinance as yf
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy
from multiprocessing import Pool

from src.pkg.enrich_strategy.YahooFinanceSequentialStrategy import enrich_single

_DEFAULT_POOL_SIZE: int = 10


class YahooFinanceParallelStrategy(StockSymbolEnrichStrategy):
    _pool_size: int
    _enrich_start_time: float
    _enrich_complete_time: float

    def __init__(self, pool_size=_DEFAULT_POOL_SIZE):
        self._pool_size = pool_size

    def enrich(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        symbols_str = " ".join(str(stock_symbol) for stock_symbol in stock_symbols)
        debug(f'obtaining yahoo finance tickers for {len(stock_symbols)} stock symbols')
        tickers = yf.Tickers(symbols_str)
        debug(f'yahoo finance tickers obtained')
        debug(f'starting enrichment pool processing (size: {self._pool_size})')
        self._enrich_start_time = time.time()
        with Pool(self._pool_size) as p:
            enriched = p.starmap(
                enrich_single,
                [(stock_symbol, tickers.tickers[f'{stock_symbol}']) for stock_symbol in stock_symbols]
            )
        self._enrich_complete_time = time.time()
        debug(f'complete enrichment pool processing (time: {self._enrich_start_time - self._enrich_complete_time})')
        return enriched
