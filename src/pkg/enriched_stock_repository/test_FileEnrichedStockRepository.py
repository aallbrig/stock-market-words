import tempfile
import unittest

from src.model.EnrichedStock import EnrichedStock
from src.model.File import File
from src.model.StockSymbol import StockSymbol
from src.pkg.enriched_stock_repository.FileEnrichedStockRepository import FileEnrichedStockRepository


class TestFileEnrichedStockRepository(unittest.TestCase):
    def test_FileRepository_CanLocateExistingEnrichedStockByStockSymbol(self):
        fp = tempfile.NamedTemporaryFile()
        file = File()
        file.filepath = fp.name
        sut = FileEnrichedStockRepository(file)
        enriched_stock = EnrichedStock()
        symbol = StockSymbol("TSLA")
        sut.put(symbol, enriched_stock)

        maybe_enriched = sut.get(symbol)

        self.assertIsNotNone(maybe_enriched)
        fp.close()


if __name__ == '__main__':
    unittest.main()
