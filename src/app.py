#!/usr/bin/env python3
import logging
import os
import time
from logging import debug, info

from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy
from src.pkg.StockEnricher import StockEnricher
from src.pkg.enrich_strategy.TimedEnrichStrategyDecorator import TimedEnrichStrategyDecorator
from src.pkg.enrich_strategy.YahooFinanceSequentialStrategy import YahooFinanceSequentialStrategy
from src.pkg.enrich_strategy.YahooFinanceParallelStrategy import YahooFinanceParallelStrategy
from src.pkg.stock_symbol_repository.FileStockSymbolRepository import FileStockSymbolRepository


def YahooStrategyFactory(use_parallel: bool = True) -> StockSymbolEnrichStrategy:
    if use_parallel:
        return YahooFinanceParallelStrategy(pool_size=35)
    else:
        return YahooFinanceSequentialStrategy()


if __name__ == '__main__':
    start_time = time.time()
    logging.basicConfig(level=logging.DEBUG)
    all_exchanges_symbol_repository = FileStockSymbolRepository(os.path.join("static", "api", "all-exchanges.txt"))
    strategy = TimedEnrichStrategyDecorator(YahooStrategyFactory(False))
    app = StockEnricher(strategy)
    enriched = app.enrich_stock_symbols(all_exchanges_symbol_repository.get_all())
    [info(e) for e in enriched]
    debug("--- program execution time %s seconds ---" % (time.time() - start_time))
