from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol


class StockSymbolEnrichStrategy:
    def enrich(self, stock_symbol: StockSymbol) -> EnrichedStock:
        raise NotImplementedError("Please Implement this method")
