# Stock Market Ticker CLI

Python CLI tool for extracting and processing stock market data from NASDAQ FTP servers.

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the full pipeline
python3 -m src.stock_ticker.cli run-all

# Check status
python3 -m src.stock_ticker.cli status
```

## Commands

### `status`
Check database health and pipeline progress.

### `init`
Initialize SQLite database schema.

### `sync-ftp`
Download ticker lists from NASDAQ FTP (filters out ETFs, warrants, test tickers).

### `extract-prices`
Fetch price/volume data for all tickers (Pass 1, batched API calls).

### `extract-metadata`
Fetch detailed metrics (market cap, beta, RSI, MA200) for filtered tickers (Pass 2).

### `build-assets`
Generate optimized JSON assets (trie.json, metadata.json) with 5 strategy scores:
- **Dividend Daddy**: High yield + low volatility
- **Moon Shot**: High beta + oversold
- **Falling Knife**: Oversold + below MA200
- **Over-Hyped**: Overbought (high RSI)
- **Institutional Whale**: Large market cap

### `run-all`
Execute the complete pipeline: sync-ftp → extract-prices → extract-metadata → build-assets.

### `hugo` (subcommands)
Generate Hugo data files:
- `hugo raw-ftp` - Export raw FTP data
- `hugo filtered` - Export filtered ticker list
- `hugo all` - Generate all Hugo data files

## Data Flow

```
NASDAQ FTP → SQLite (tickers table)
           ↓
Yahoo Finance API → SQLite (daily_metrics table)
                  ↓
Strategy Scoring → SQLite (strategy_scores table)
                 ↓
Build Assets → JSON files (api/*.json)
             ↓
Hugo Generators → Hugo data files
```

## Database Schema

- **tickers**: symbol, name, exchange, etf_flag, first_seen
- **daily_metrics**: symbol, date, price, volume, market_cap, dividend_yield, beta, rsi_14, ma_200
- **strategy_scores**: symbol, date, [5 strategy scores]
- **pipeline_steps**: Tracks execution history
- **sync_history**: Tracks FTP sync runs

## Configuration

Edit `src/stock_ticker/config.py` for API directory and other settings.
