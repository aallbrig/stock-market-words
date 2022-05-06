from src.model.EnrichedStock import EnrichedStock
from src.model.StockSymbol import StockSymbol
from src.model.StockSymbolEnrichStrategy import StockSymbolEnrichStrategy
import yfinance as yf


def enrich_single(stock_symbol: StockSymbol, yf_ticker: yf.Ticker) -> EnrichedStock:
    enriched = EnrichedStock()
    enriched.stock_symbol = stock_symbol

    info = yf_ticker.info
    if 'sector' in info.keys():
        enriched.sector = info['sector']
    if 'industry' in info.keys():
        enriched.industry = info['industry']
    if 'ebitda' in info.keys():
        enriched.ebitda = info['ebitda']
    if 'website' in info.keys():
        enriched.website = info['website']
    if 'open' in info.keys():
        enriched.open = info['open']
    if 'previousClose' in info.keys():
        enriched.previous_close = info['previousClose']
    if 'currentPrice' in info.keys():
        enriched.current_price = info['currentPrice']
    if 'fiftyTwoWeekLow' in info.keys():
        enriched.fifty_two_week_low = info['fiftyTwoWeekLow']
    if 'fiftyTwoWeekHigh' in info.keys():
        enriched.fifty_two_week_high = info['fiftyTwoWeekHigh']

    return enriched


class YahooFinanceStrategy(StockSymbolEnrichStrategy):
    def enrich(self, stock_symbols: list[StockSymbol]) -> list[EnrichedStock]:
        symbols_str = " ".join(str(stock_symbol) for stock_symbol in stock_symbols)
        tickers = yf.Tickers(symbols_str)
        return [enrich_single(stock_symbol, tickers.tickers[str(stock_symbol)]) for stock_symbol in stock_symbols]
