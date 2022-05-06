from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol


class StockSymbolEnrichStrategy:
    def enrich(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        raise NotImplementedError("Please Implement this method")
