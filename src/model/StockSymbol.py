class StockSymbol:
    _symbol: str

    def __init__(self, symbol: str):
        # TODO: validate symbol
        self._symbol = symbol

    def __str__(self):
        return self._symbol
