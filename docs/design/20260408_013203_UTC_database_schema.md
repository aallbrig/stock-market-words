# Database Schema

**Status:** Design / Foundation
**Last updated:** 2026-04-08

The SQLite database at `data/market_data.db` is the durable store behind
stockmarketwords.com. Authoritative DDL: `python3/schema.sql`. Migrations:
`python3/src/stock_ticker/migrations.py`. This doc explains *why* the tables
exist and how they relate.

---

## Six tables, three concerns

### Identity (1 table)

**`tickers`** — the phonebook. One row per active US ticker. Updated only
when the NASDAQ FTP listings change.

| Column | Type | Notes |
|---|---|---|
| `symbol` | TEXT PK | e.g. `CRM` |
| `name` | TEXT | Company name |
| `exchange` | TEXT | NASDAQ / NYSE / AMEX |
| `is_etf` | INTEGER | Filter flag (ETFs are excluded by default) |
| `first_seen` | TEXT (date) | When this symbol first appeared in our pipeline |
| `sector` | TEXT | Yahoo classification |
| `industry` | TEXT | Yahoo sub-classification |

### Daily snapshots (2 tables)

**`daily_metrics`** — the heartbeat. One row per ticker per trading day.
This is the table that grows. PK: `(symbol, date)`. Index:
`idx_date_filter` on `(date, price, volume)`.

Key columns (full list in `schema.sql`):

- Pass 1 (`extract-prices`): `price`, `volume`
- Pass 2 (`extract-metadata`): `market_cap`, `dividend_yield`, `beta`,
  `rsi_14`, `ma_50`, `ma_200`, `pe_ratio`, `forward_pe`, `price_to_book`,
  `peg_ratio`, `enterprise_value`, `week_52_high`, `week_52_low`,
  `avg_volume_10day`, `short_ratio`, `short_percent_float`,
  `debt_to_equity`, `current_ratio`, `quick_ratio`, `profit_margin`,
  `operating_margin`, `return_on_equity`, `return_on_assets`,
  `revenue_growth`, `earnings_growth`, `target_mean_price`,
  `recommendation_mean`, `num_analyst_opinions`, `shares_outstanding`,
  `float_shares`

**`strategy_scores`** — the brain. One row per ticker per day, with five
1–100 percentile-ranked scores. PK: `(symbol, date)`.

| Column | Meaning |
|---|---|
| `dividend_daddy_score` | Higher = more dividend-and-stable |
| `moon_shot_score` | Higher = more volatile + oversold |
| `falling_knife_score` | Higher = more oversold + below MA200 |
| `over_hyped_score` | Higher = more overbought |
| `inst_whale_score` | Higher = more large-cap |

Computed by `python3/src/stock_ticker/builders.py` during `ticker-cli build`.
Percentile ranking means scores are *relative* to that day's universe — a
score of 90 means "top 10% on this dimension among today's tickers."

### Pipeline observability (3 tables)

**`pipeline_steps`** — per-day step completion. PK: `(step_name, run_date)`.
Lets `ticker-cli run-all` resume after a crash. Steps tracked: `sync-ftp`,
`extract-prices`, `extract-metadata`, `build`, `generate-hugo`.

**`pipeline_runs`** — full-run history. One row per `run-all` invocation.
Columns include `run_id` (PK), `started_at`, `completed_at`, `status`,
`failed_step`, network reachability flags, request counts, byte counts, and
per-step timings (`timing_sync_ftp`, `timing_extract_prices`, ..., `timing_total`).

**`ticker_sync_history`** — per-ticker fetch log. Foreign keys to `pipeline_runs`
and `tickers`. Lets you ask "why did AAPL fail to refresh on April 3?" by
joining on `(run_id, symbol)`. Indexes: `idx_ticker_sync_run`,
`idx_ticker_sync_symbol`.

---

## Data lifecycle

- `tickers` — slow-moving, only changes on FTP delta.
- `daily_metrics` and `strategy_scores` — append one row per ticker per
  trading day. **No retention policy is currently enforced** — see open
  question below.
- `pipeline_steps` — per-day; `reset` clears today's row.
- `pipeline_runs` and `ticker_sync_history` — append-only history.

## Migrations

Schema changes go through `ticker-cli migrate up` / `migrate down`. Add new
migration files via `python3/src/stock_ticker/migrations.py`. Never edit
`schema.sql` to change an existing table on a populated DB — write a
migration.

## Common queries

```sql
-- Today's top 10 dividend daddies
SELECT t.symbol, t.name, s.dividend_daddy_score
FROM strategy_scores s JOIN tickers t USING (symbol)
WHERE s.date = (SELECT MAX(date) FROM strategy_scores)
ORDER BY s.dividend_daddy_score DESC LIMIT 10;

-- Yesterday's full row for one ticker
SELECT * FROM daily_metrics
WHERE symbol = 'CRM' AND date = (SELECT MAX(date) FROM daily_metrics);

-- Pipeline failures in the last week
SELECT run_date, failed_step, total_failures
FROM pipeline_runs
WHERE status != 'success' AND run_date >= date('now', '-7 days');
```

## Open questions

- **Retention.** `daily_metrics` and `strategy_scores` grow ~8k rows/day with
  no archival. At ~10 KB/row that's ~30 MB/year of new data, manageable, but
  no policy is documented. Worth a follow-up spec if the DB becomes the
  bottleneck.
- **Backups.** `data/market_data.db` is currently 53 MB. There is no documented
  backup process; the file is the only source of historical scores.
