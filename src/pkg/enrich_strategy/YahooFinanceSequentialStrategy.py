from logging import debug

from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy
import yfinance as yf

from src.pkg.enrich_strategy.yahoo_finance_common.enrich_single import enrich_single


class YahooFinanceSequentialStrategy(StockSymbolEnrichStrategy):
    _enrich_start_time: float
    _enrich_complete_time: float

    def enrich(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        symbols_str = " ".join(str(stock_symbol) for stock_symbol in stock_symbols)
        debug(f'obtaining yahoo finance tickers for {len(stock_symbols)} stock symbols')
        tickers = yf.Tickers(symbols_str)
        debug(f'yahoo finance tickers obtained')
        enriched_stocks = [enrich_single(stock_symbol, tickers.tickers[str(stock_symbol)]) for stock_symbol in stock_symbols]
        debug(f'complete enrichment processing (time: {self._enrich_start_time - self._enrich_complete_time})')
        return enriched_stocks
