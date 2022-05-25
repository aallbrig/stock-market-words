from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol


class EnrichedStockCache:
    _cache: dict[StockSymbol, EnrichedStock] = {}

    def get(self, stock: StockSymbol) -> EnrichedStock:
        raise NotImplementedError("Please Implement this method")
