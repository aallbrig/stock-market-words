from src.model.EnrichedStockCache import EnrichedStockCache
from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy


class CachedStockSymbolEnrichStrategy(StockSymbolEnrichStrategy):
    _cache: EnrichedStockCache
    _strategy: StockSymbolEnrichStrategy

    def __init__(self, cache: EnrichedStockCache, strategy: StockSymbolEnrichStrategy):
        self._cache = cache
        self._strategy = strategy

    def enrich(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        return [self.cached_enriched(stock_symbol) for stock_symbol in stock_symbols]

    def cached_enriched(self, stock_symbol: StockSymbol) -> EnrichedStock:
        maybe_cached = self._cache.get(stock_symbol)
        if maybe_cached is not None:
            return maybe_cached
        else:
            self._strategy.enrich([stock_symbol])
