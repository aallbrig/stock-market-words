from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy


class StockEnricher:
    _strategy: StockSymbolEnrichStrategy

    def __init__(self, strategy: StockSymbolEnrichStrategy):
        self._strategy = strategy

    def enrich_stock_symbols(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        return [self._strategy.enrich(stock_symbol) for stock_symbol in stock_symbols]
