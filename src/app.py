#!/usr/bin/env python3
from src.model.StockSymbol import StockSymbol
from src.pkg.StockEnricher import StockEnricher
from src.pkg.enrich_strategy.VanillaStrategy import VanillaStrategy

if __name__ == '__main__':
    app = StockEnricher(VanillaStrategy())
    enriched = app.enrich_stock_symbols([StockSymbol("TSLA")])
    [print(e) for e in enriched]
