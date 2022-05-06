from src.model.StockSymbol import StockSymbol


class EnrichedStock:
    stock_symbol: StockSymbol
    open: float
    previous_close: float
    fifty_two_week_low: float
    fifty_two_week_high: float
    sector: str
    industry: str
    website: str
    ebitda: int

    def __str__(self):
        return f'{self.stock_symbol} {self.ebitda} {self.open} {self.previous_close} {self.industry} {self.website}'
