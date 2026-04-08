# Data Pipeline

**Status:** Design / Foundation
**Last updated:** 2026-04-08

How raw market data becomes published web pages. This is the canonical
trading-day loop.

---

## End-to-end flow

```
NASDAQ FTP (ftp.nasdaqtrader.com/SymbolDirectory/)
        |
        |  ticker-cli sync-ftp
        v
data/tmp/nasdaqlisted.txt + otherlisted.txt
        |
        |  parse + filter (drop ETFs, warrants, derivatives, test issues)
        v
SQLite: tickers table  (~8,000 active rows)
        |
        |  ticker-cli extract-prices  [Pass 1, batch=100, Yahoo Finance]
        v
SQLite: daily_metrics  (price, volume)
        |
        |  ticker-cli extract-metadata  [Pass 2, batch=50, Yahoo Finance]
        v
SQLite: daily_metrics  (extended: market_cap, beta, RSI-14, MA200, PE, ...)
        |
        |  ticker-cli build  (percentile-rank scoring across 5 strategies)
        v
SQLite: strategy_scores
        |
        |  ticker-cli hugo all
        v
hugo/site/data/*.json           (raw_nasdaq.json, raw_otherlisted.json, ...)
hugo/site/static/data/*.json    (all_tickers.json, strategy_*.json, ...)
hugo/site/content/raw-ftp-data.md, filtered-data.md
        |
        |  hugo --minify  (or `hugo server` in dev)
        v
hugo/site/public/**             Static HTML/CSS/JS — deployable
```

## CLI commands

Entry point: `ticker-cli` (defined in `python3/pyproject.toml`,
implemented in `python3/src/stock_ticker/cli.py`).

| Command | What it does | Writes |
|---|---|---|
| `ticker-cli status` | Health check: FTP + Yahoo reachability, DB tables, today's progress | nothing |
| `ticker-cli init` | Apply `python3/schema.sql` to `data/market_data.db` | DB tables |
| `ticker-cli migrate {status,up,down}` | Schema migrations | DB |
| `ticker-cli sync-ftp [--clean]` | Pull NASDAQ FTP listings, filter, upsert | `tickers` table |
| `ticker-cli extract-prices [--limit N] [--clean]` | Pass 1: price + volume from Yahoo | `daily_metrics` (price, volume) |
| `ticker-cli extract-metadata [--limit N] [--clean]` | Pass 2: extended fundamentals | `daily_metrics` (full row) |
| `ticker-cli build [--clean]` | Compute percentile-ranked strategy scores | `strategy_scores` table |
| `ticker-cli hugo raw-ftp` | Emit raw FTP JSON (pre-filtering view) | `hugo/site/data/raw_*.json`, `hugo/site/static/data/raw_*.json` |
| `ticker-cli hugo filtered` | Emit filtered ticker JSON | `hugo/site/static/data/filtered_tickers.json` |
| `ticker-cli hugo strategies` | Emit per-strategy ticker lists for the home-page tool | `hugo/site/static/data/strategy_*.json` |
| `ticker-cli hugo all-tickers` | Emit the universal ticker dataset | `hugo/site/data/all_tickers.json` |
| `ticker-cli hugo pages` | Generate the two CLI-managed markdown pages | `hugo/site/content/raw-ftp-data.md`, `filtered-data.md` |
| `ticker-cli hugo all` | All `hugo *` subcommands in sequence | (everything above) |
| `ticker-cli run-all [--limit N] [--force] [--clean]` | Full pipeline: sync-ftp → extract-prices → extract-metadata → build → hugo all | (everything) |
| `ticker-cli reset [--force]` | Delete today's `daily_metrics`, `strategy_scores`, `pipeline_steps` rows | DB |

## Pipeline state and resumability

`ticker-cli run-all` is resumable within a trading day. The `pipeline_steps`
table tracks per-day completion of each step (`sync-ftp`, `extract-prices`,
`extract-metadata`, `build`, `generate-hugo`). If extract-metadata dies
halfway, re-running `run-all` skips finished steps unless `--force` is set.
`pipeline_runs` retains per-run timing and failure history; per-ticker
fetches are logged in `ticker_sync_history`.

## Filtering rules (in `ftp_sync.py`)

Tickers are dropped at sync time if they are:

- Units, Warrants, Preferred Stock, Series A/B, Depositary Shares, Rights, Trust Preferred (string match on ticker name)
- Marked as Test Issue
- Below the price floor (`config.py`: `MIN_PRICE = 5.0`)
- Below the volume floor (`config.py`: `MIN_VOLUME = 100_000`)

These thresholds and filtering choices live in
`python3/src/stock_ticker/config.py` and `ftp_sync.py`.

## Strategy scoring

`ticker-cli build` percentile-ranks every ticker against five strategies and
writes a 1–100 score per ticker per strategy into `strategy_scores`:

| Strategy | Heuristic |
|---|---|
| Dividend Daddy | High dividend yield + low volatility |
| Moon Shot | High beta + oversold (low RSI) |
| Falling Knife | Oversold + below 200-day MA |
| Over-Hyped | Overbought (high RSI) |
| Institutional Whale | Large market cap |

The scoring math lives in `python3/src/stock_ticker/builders.py`.

## What the browser actually consumes

`portfolio-extractor.js` loads strategy-specific JSON files from
`/static/data/strategy_*.json` lazily, depending on which strategy the user
has selected. `all_tickers.json` is consumed by Hugo at build time (not by
the browser) via `hugo/site/content/tickers/_content.gotmpl` to materialize
the per-ticker detail pages.

## i18n note

The pipeline currently has **zero language awareness**. All JSON output is
language-agnostic (numbers, symbols), and the markdown pages it writes
(`raw-ftp-data.md`, `filtered-data.md`) are English-only — no `.zh-cn.md`
sibling is generated. See
[`i18n_architecture.md`](./20260408_013203_UTC_i18n_architecture.md) for the
gap analysis and the open spec(s) addressing this.
