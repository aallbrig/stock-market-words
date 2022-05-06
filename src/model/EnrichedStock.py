from src.model.StockSymbol import StockSymbol


class EnrichedStock:
    stock_symbol: StockSymbol

    def __str__(self):
        return f'{self.stock_symbol}'
