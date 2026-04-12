# SGX Ticker Support

**Status:** Draft  
**Author:** Copilot  
**Created:** 2026-04-12  
**Supersedes:** —  
**Superseded by:** —

## Context

stockmarketwords.com currently indexes only US-listed securities from NASDAQ,
NYSE, and AMEX. For Singaporean investors — the site's emerging target market
— the **Singapore Exchange (SGX)** is their home market. SGX lists ~700
equities including blue chips (DBS `D05.SI`, OCBC `O39.SI`, Singtel
`Z74.SI`), the world's largest concentration of Asia-Pacific REITs, and
numerous mid-cap/small-cap names.

The existing data pipeline already uses Yahoo Finance as its primary data
source for prices and fundamentals. **Yahoo Finance fully supports SGX
tickers** using the `.SI` suffix (e.g., `D05.SI`). This means the heaviest
infrastructure — price extraction, metadata extraction, strategy scoring — can
be reused with minimal changes.

The main challenge is the **ticker extraction engine**: SGX tickers are
alphanumeric codes (e.g., `D05`, `O39`, `Z74`, `BS6`, `9CI`) rather than
English words/abbreviations like US tickers (`AAPL`, `MSFT`). The
TickerEngine's current algorithm is tuned for US-style ticker patterns.

## Goal

Singaporean investors can paste text containing SGX ticker codes or company
names and have the extraction engine identify them alongside US tickers, with
full strategy scoring and detail pages for all ~700 SGX-listed securities.

## Non-goals

- Supporting other Asian exchanges (HKEX, TSE, ASX) in this spec. The
  architecture should not preclude them, but implementation is out of scope.
- Real-time or intraday SGX data. The daily end-of-day pipeline cadence
  remains unchanged.
- SGX-specific strategies (that's the REIT Radar spec). This spec provides
  the data foundation.
- Dual-listed stock arbitrage detection.
- SGX derivatives, structured warrants, or ETFs — equity-only for v1.

## User stories

- As a Singaporean investor reading The Business Times, I want to paste an
  article and have SGX tickers like "D05" and "Z74" extracted alongside any US
  tickers mentioned, so that I get a complete picture of all stocks discussed.

- As Uncle Tan browsing SGX forums, I want to paste a forum thread mentioning
  SGX codes and see strategy scores for each, so that I can quickly evaluate
  which mentioned stocks align with my investment style.

- As a financial planner, I want ticker detail pages for SGX stocks (e.g.,
  `/tickers/D05.SI/`) with the same market data and strategy scores as US
  stocks, so that I can use one tool for both markets.

## Design

### 1. SGX Ticker List Source

SGX does not offer a public FTP like NASDAQ. Options:

| Source | Freshness | Format | License |
|--------|-----------|--------|---------|
| **Yahoo Finance screener** | Daily | JSON API | Fair use (same as current US data) |
| **SGX website screener** | Daily | HTML/JSON | Public data, scraping required |
| **Static seed list + Yahoo validation** | Weekly | CSV → SQLite | No external dependency for list |

**Recommended: Static seed list + Yahoo Finance validation.**

Maintain a curated CSV file `data/sgx_tickers.csv` with columns:
`symbol,name,sector,industry`. The pipeline validates each symbol against
Yahoo Finance during `extract-prices` (if Yahoo returns data, the ticker is
active). This avoids fragile scraping and keeps the pipeline deterministic.

The seed list can be refreshed periodically from SGX's public company
directory or open-source repositories (e.g.,
`github.com/Singapore-Fintech/sgx-tickers`).

### 2. Pipeline Changes

#### a. New command: `ticker-cli sync-sgx`

Similar to `sync-ftp` but reads from `data/sgx_tickers.csv`:

```python
@cli.command()
def sync_sgx(ctx):
    """Import SGX tickers from seed CSV into the tickers table."""
    # Read data/sgx_tickers.csv
    # For each row, upsert into tickers table with exchange='SGX'
    # Symbol stored WITH .SI suffix: "D05.SI"
    # Apply same MIN_PRICE / MIN_VOLUME filters after price extraction
```

#### b. Modify `extract-prices` and `extract-metadata`

These already batch Yahoo Finance requests. Changes needed:

- Include `exchange='SGX'` tickers in the query set.
- Yahoo Finance ticker format: `D05.SI` — the `.SI` suffix is already in
  the symbol column, so no transformation needed.
- SGX trades in SGD; Yahoo Finance returns prices in the local currency.
  Store as-is (SGD for SGX, USD for US). Add a `currency` column to
  `daily_metrics` or infer from exchange.

#### c. Modify `builders.py`

Strategy scoring operates on percentiles across all tickers. With SGX
tickers added (~700), the universe grows from ~8k to ~8.7k. Decisions:

- **Option A: Combined scoring** — SGX and US tickers scored in the same
  percentile pool. A Singaporean REIT with 5% yield competes against US
  stocks for Dividend Daddy ranking.
- **Option B: Separate scoring** — Per-exchange percentiles. SGX tickers
  scored against each other.
- **Recommended: Option A** for v1. Users see a unified ranking. The REIT
  Radar spec can add exchange-filtered views later.

#### d. Modify `hugo_generators.py`

- `hugo all-tickers`: Include SGX tickers in `all_tickers.json`.
- `hugo strategies`: Include SGX tickers in all `strategy_*.json` files.
- `hugo filtered`: Include in `filtered_tickers.json`.
- Add `exchange` field to JSON if not already present (it is — confirmed in
  `builders.py` line ~195).

#### e. `run-all` orchestration

Add `sync-sgx` as a step after `sync-ftp` and before `extract-prices`.
Pipeline state tracking (`pipeline_steps`) already supports arbitrary step
names.

### 3. Database Changes

#### a. `tickers` table

No schema change needed. The `exchange` column already accepts free text.
SGX tickers will have `exchange = 'SGX'`.

#### b. `daily_metrics` table

Add a `currency` column (default `'USD'` for backward compatibility):

```sql
ALTER TABLE daily_metrics ADD COLUMN currency TEXT DEFAULT 'USD';
```

SGX rows will have `currency = 'SGD'`. This enables the future "SGD View"
feature to convert US prices correctly.

New migration in `migrations.py`.

### 4. TickerEngine Changes

The browser-side TickerEngine needs to recognize SGX ticker patterns:

| Pattern | Examples | Challenge |
|---------|----------|-----------|
| Alphanumeric 2–4 chars | `D05`, `O39`, `Z74`, `9CI`, `BS6` | Short codes overlap with common English (e.g., "A17" could be a list marker) |
| Suffix notation | `D05.SI` | Unambiguous but rarely written in articles |

**Approach:** Add SGX tickers to the ticker dictionary that the Web Worker
loads. The TickerEngine's existing dictionary-lookup approach (check if a
word matches a known ticker) already handles this — no algorithm change
needed. The extracted text "D05" will match the dictionary entry `D05.SI`.

**Key implementation detail:** When the user's text contains `D05`, the
engine looks it up in the dictionary. If `D05.SI` is a known ticker, it
matches. The `.SI` suffix is added to the result, not expected in the input
text.

Changes to `TickerEngine.js`:
- The dictionary already maps `symbol → data`. SGX entries keyed by the
  short code (`D05`) pointing to full data (`D05.SI`, "DBS Group Holdings",
  exchange: "SGX").
- No algorithm change needed — dictionary lookup already works.

Changes to `portfolio-worker.js`:
- Load SGX tickers from the same strategy JSON files (they'll be included
  by the pipeline).

### 5. Hugo Site Changes

#### a. Ticker detail pages

The content adapter (`hugo/site/content/tickers/_content.gotmpl`) iterates
`all_tickers.json`. SGX tickers will automatically get pages at
`/tickers/d05.si/` (Hugo lowercases).

Add an exchange badge color: SGX = orange (vs. NASDAQ = blue, NYSE = green,
AMEX = purple) in `single.html`.

#### b. Filtered data page

Add an exchange filter dropdown to the filtered data DataTable, allowing
users to filter by NASDAQ / NYSE / AMEX / SGX.

#### c. Strategy pages

No changes needed — SGX tickers naturally appear in strategy rankings.

#### d. Home page extraction tool

No changes needed — the Web Worker loads the combined dictionary.

### 6. Data Files

| File | Change |
|------|--------|
| `data/sgx_tickers.csv` (new) | Seed list of ~700 SGX equities |
| `hugo/site/data/all_tickers.json` | Now includes SGX tickers |
| `hugo/site/static/data/strategy_*.json` | Now includes SGX tickers |
| `hugo/site/static/data/filtered_tickers.json` | Now includes SGX tickers |

### 7. Currency handling

SGX prices are in SGD. For v1, display prices as-is with a currency
indicator. The ticker detail page should show `S$X.XX` for SGX stocks and
`$X.XX` for US stocks. The "SGD View" feature (a separate future spec) will
handle cross-currency conversion.

## Affected files

| File | Change |
|------|--------|
| `data/sgx_tickers.csv` (new) | SGX ticker seed list |
| `python3/src/stock_ticker/cli.py` | New `sync-sgx` command, update `run-all` |
| `python3/src/stock_ticker/sgx_sync.py` (new) | SGX CSV reader + ticker upsert |
| `python3/src/stock_ticker/extractors.py` | Include SGX tickers in extraction queries |
| `python3/src/stock_ticker/builders.py` | No change (SGX tickers scored with US) |
| `python3/src/stock_ticker/hugo_generators.py` | No change (queries all tickers) |
| `python3/src/stock_ticker/migrations.py` | Add `currency` column migration |
| `python3/src/stock_ticker/config.py` | Add `SGX_SEED_FILE` path constant |
| `hugo/site/layouts/tickers/single.html` | Currency-aware price display, SGX badge color |
| `hugo/site/layouts/page/strategy-filter.html` | Exchange filter dropdown |
| `hugo/site/static/js/filtered-data.js` | Exchange filter JS logic |
| `hugo/site/i18n/en.toml` | New keys: exchange_sgx, currency_sgd |
| `hugo/site/i18n/zh-cn.toml` | New keys: exchange_sgx, currency_sgd |
| `tests/puppeteer/website-pages.e2e.test.js` | Verify SGX ticker page renders |

## Verification

- **Pipeline:** Run `ticker-cli sync-sgx` → confirm ~700 rows in `tickers`
  table with `exchange='SGX'`.
- **Pipeline:** Run `ticker-cli extract-prices --limit 10` → confirm SGX
  tickers get prices in SGD.
- **Pipeline:** Run `ticker-cli build` → confirm SGX tickers appear in
  `strategy_scores`.
- **Hugo:** Run `hugo` → confirm `/tickers/d05.si/` renders with DBS data
  and SGD price.
- **Extraction:** Paste "I bought D05 and AAPL today" into the home page
  tool → confirm both DBS (SGX) and Apple (NASDAQ) are extracted.
- **Filtered data:** Confirm exchange filter dropdown works to show only SGX
  tickers.
- **Manual:** Open `/tickers/d05.si/` → confirm orange SGX badge, S$ price
  format.

## Open questions

1. **SGX ticker seed list maintenance:** How often should
   `data/sgx_tickers.csv` be refreshed? Default: manually, quarterly.
   Automate later if needed.
2. **Ambiguous short codes:** SGX codes like `A17` or `M44` might appear in
   text as list markers or addresses. Default: Accept some false positives —
   the dictionary-lookup approach keeps precision high because only known
   SGX tickers match.
3. **Combined vs. separate strategy scoring:** Default: Combined (Option A).
   Revisit if users complain about SGX stocks being drowned by US volume.
4. **SGX ETFs:** Default: Exclude for v1 (same as US ETFs). The `is_etf`
   flag in the seed CSV handles this.
5. **Currency in JSON:** Should `all_tickers.json` include a `currency`
   field? Default: Yes, add it.

## Alternatives considered

1. **Scrape SGX website directly** — Rejected. Fragile, may violate ToS,
   requires ongoing maintenance.
2. **Use a paid data provider (e.g., Alpha Vantage, Polygon.io)** —
   Rejected for v1. Yahoo Finance covers SGX adequately and is consistent
   with the existing US data source.
3. **Separate site section for SGX** (`/sgx/tickers/...`) — Rejected.
   Unified experience is better. One ticker page template, one strategy
   framework, one extraction tool. Exchange is just a filter dimension.
