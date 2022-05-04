import unittest

from src.app import StockEnricher
from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.pkg.enrich_strategy.VanillaStrategy import VanillaStrategy


class TestApp(unittest.TestCase):
    def test_CanEnrichStockSymbolWithFinancialInfo(self):
        sut = StockEnricher(VanillaStrategy())

        enriched = sut.enrich_stock_symbols([StockSymbol("TSLA")])

        self.assertEqual(len(enriched), 1)
        self.assertEqual(isinstance(enriched[0], EnrichedStock), True)


if __name__ == '__main__':
    unittest.main()
