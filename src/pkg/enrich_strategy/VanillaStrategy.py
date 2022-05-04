from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy


class VanillaStrategy(StockSymbolEnrichStrategy):
    def enrich(self, stock_symbol: StockSymbol) -> EnrichedStock:
        enriched = EnrichedStock()
        enriched.stock_symbol = stock_symbol
        return enriched
