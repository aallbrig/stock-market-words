from src.model.StockSymbol import StockSymbol


def _safe_str(maybe_stringable):
    return str(maybe_stringable) if maybe_stringable is not None else ""


class EnrichedStock:
    stock_symbol: StockSymbol
    open: float = None
    previous_close: float = None
    fifty_two_week_low: float = None
    fifty_two_week_high: float = None
    sector: str = None
    industry: str = None
    website: str = None
    ebitda: int = None

    def __str__(self):
        stock_symbol = f'{self.stock_symbol}'
        ebitda = _safe_str(self.ebitda)
        open_price = _safe_str(self.open)
        previous_close_price = _safe_str(self.previous_close)
        industry = _safe_str(self.industry)
        website = _safe_str(self.website)
        return f'{stock_symbol} {ebitda} {open_price} {previous_close_price} {industry} {website}'
