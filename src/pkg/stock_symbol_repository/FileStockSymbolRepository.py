from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolRepository import StockSymbolRepository


class FileStockSymbolRepository(StockSymbolRepository):
    _filepath: str

    def __init__(self, filepath: str):
        self._filepath = filepath

    def read_symbols_from_file(self) -> list[StockSymbol]:
        file = open(self._filepath, 'r')
        stock_symbols: list[StockSymbol] = [StockSymbol(line.strip()) for line in file.readlines()]
        file.close()
        return stock_symbols

    def get_all(self) -> list[StockSymbol]:
        return self.read_symbols_from_file()
