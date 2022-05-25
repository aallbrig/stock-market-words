from logging import debug
from typing import Optional

from src.model.EnrichedStock import EnrichedStock
from src.model.EnrichedStockRepository import EnrichedStockRepository
from src.model.File import File
from src.model.StockSymbol import StockSymbol


class LineData:
    symbol: StockSymbol
    enriched_stock: EnrichedStock


class LineParser:
    _separator = "\t|\t"

    def encode(self, data: LineData) -> str:
        return f'{data.symbol}{self._separator}{data.enriched_stock}'

    def decode(self, line) -> LineData:
        maybe_symbol, maybe_enriched_stock = line.split(self._separator)
        data = LineData()
        return data


class FileEnrichedStockRepository(EnrichedStockRepository):
    _file: File
    _cache: dict[StockSymbol, EnrichedStock] = {}
    _parser: LineParser = LineParser()

    def __init__(self, file: File):
        self._file = file

    def get(self, stock: StockSymbol) -> EnrichedStock:
        if stock in self._cache.keys():
            return self._cache[stock]
        return self.get_from_file(stock)

    def put(self, stock_symbol: StockSymbol, enriched_stock: EnrichedStock):
        file = open(self._file.filepath, 'a')
        data = LineData()
        data.symbol = stock_symbol
        data.enriched_stock = enriched_stock
        encoded_data = self._parser.encode(data)
        file.write(encoded_data)
        file.close()

    def get_from_file(self, stock: StockSymbol) -> Optional[EnrichedStock]:
        file = open(self._file.filepath, 'r')

        for line in file:
            maybe_enriched = self._parser.decode(line)
            if maybe_enriched.symbol is stock:
                file.close()
                return maybe_enriched.enriched_stock

        file.close()
        return None
