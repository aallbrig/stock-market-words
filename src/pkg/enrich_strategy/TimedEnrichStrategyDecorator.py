import time
from logging import debug

from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy


class TimedEnrichStrategyDecorator(StockSymbolEnrichStrategy):
    _strategy: StockSymbolEnrichStrategy
    _enrich_start_time: float
    _enrich_complete_time: float

    def __init__(self, strategy: StockSymbolEnrichStrategy):
        self._strategy = strategy

    def enrich(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        self._enrich_start_time = time.time()
        enriched_stock = self._strategy.enrich(stock_symbols)
        self._enrich_complete_time = time.time()
        debug(f'enrichment processing complete (time: {self._enrich_start_time - self._enrich_complete_time})')
        return enriched_stock
