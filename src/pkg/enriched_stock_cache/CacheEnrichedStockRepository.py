from typing import Optional

from src.model.EnrichedStock import EnrichedStock
from src.model.EnrichedStockCache import EnrichedStockCache
from src.model.EnrichedStockRepository import EnrichedStockRepository
from src.model.StockSymbol import StockSymbol


class CacheFromEnrichedStockRepository(EnrichedStockCache):
    _repository: EnrichedStockRepository

    def __init__(self, repository: EnrichedStockRepository):
        self._repository = repository

    def get(self, stock: StockSymbol) -> Optional[EnrichedStock]:
        return self.cached_get(stock)

    def cached_get(self, stock) -> Optional[EnrichedStock]:
        if stock in self._cache.keys():
            return self._cache[stock]
        else:
            maybe_enriched_stock = self._repository.get(stock)
            if maybe_enriched_stock is not None:
                self._cache[stock] = maybe_enriched_stock
                return maybe_enriched_stock
            else:
                return None

