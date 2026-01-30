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

Options:
- `--clean`: Clean today's data before running

### `extract-prices`
Fetch price/volume data for all tickers (Pass 1, batched API calls).

Options:
- `--limit N`: Limit processing to N tickers (for testing)
- `--clean`: Clean today's data before running

### `extract-metadata`
Fetch detailed metrics (market cap, beta, RSI, MA200) for filtered tickers (Pass 2).

Options:
- `--limit N`: Limit processing to N tickers (for testing)
- `--clean`: Clean today's data before running

### `build`
Generate optimized JSON assets (trie.json, metadata.json) with 5 strategy scores:
- **Dividend Daddy**: High yield + low volatility
- **Moon Shot**: High beta + oversold
- **Falling Knife**: Oversold + below MA200
- **Over-Hyped**: Overbought (high RSI)
- **Institutional Whale**: Large market cap

Options:
- `--clean`: Clean today's data before running

### `run-all`
Execute the complete pipeline: sync-ftp → extract-prices → extract-metadata → build-assets.

Options:
- `--limit N`: Limit processing to N tickers (for testing)
- `--force`: Force re-run even if already completed today
- `--clean`: Clean today's data before running (resets all pipeline state)

**Note:** The `--clean` flag removes **only today's data** and never affects previous days. This allows for a fresh run without duplication. It deletes:
- Today's daily_metrics records
- Today's strategy_scores records
- Today's pipeline_steps records
- Today's pipeline_runs records
- Today's ticker_sync_history records

### `hugo` (subcommands)
Generate Hugo data files:
- `hugo raw-ftp` - Export raw FTP data
- `hugo filtered` - Export filtered ticker list
- `hugo all` - Generate all Hugo data files
  - Options: `--clean` - Clean today's data before running

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
- **pipeline_steps**: Tracks when each pipeline step completes (replaces sync_history)
- **pipeline_runs**: Tracks complete pipeline runs with metrics and timing
- **ticker_sync_history**: Tracks individual ticker fetch success/failure for each run

## Configuration

Edit `src/stock_ticker/config.py` for API directory and other settings.
