from typing import Optional

from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol


class EnrichedStockRepository:
    def get(self, stock_symbol: StockSymbol) -> Optional[EnrichedStock]:
        raise NotImplementedError("Please Implement this method")

    def put(self, stock_symbol: StockSymbol, enriched_stock: EnrichedStock):
        raise NotImplementedError("Please Implement this method")
