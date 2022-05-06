#!/usr/bin/env python3
import os

from src.pkg.StockEnricher import StockEnricher
from src.pkg.enrich_strategy.VanillaStrategy import VanillaStrategy
from src.pkg.stock_symbol_repository.FileStockSymbolRepository import FileStockSymbolRepository

if __name__ == '__main__':
    all_exchanges_symbol_repository = FileStockSymbolRepository(os.path.join("static", "api", "all-exchanges.txt"))
    app = StockEnricher(VanillaStrategy())
    enriched = app.enrich_stock_symbols(all_exchanges_symbol_repository.get_all())
    [print(e) for e in enriched]
