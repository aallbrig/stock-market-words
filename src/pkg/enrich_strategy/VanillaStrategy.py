from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy


class VanillaStrategy(StockSymbolEnrichStrategy):
    def enrich(self, stock_symbol: StockSymbol) -> EnrichedStock:
        enriched = EnrichedStock()

        enriched.stock_symbol = stock_symbol
        enriched.sector = "Example sector"
        enriched.industry = "Example industry"
        enriched.ebitda = 0
        enriched.website = "www.example.com"
        enriched.open = 10
        enriched.previous_close = 10
        enriched.current_price = 10
        enriched.fifty_two_week_low = 10
        enriched.fifty_two_week_high = 10

        return enriched
