# REIT Radar Strategy

**Status:** Implemented  
**Author:** Copilot  
**Created:** 2026-04-12  
**Supersedes:** —  
**Superseded by:** —

## Context

Singapore has the **largest REIT market in Asia ex-Japan**, with 42 S-REITs
and property trusts listed on SGX representing ~S$80 billion in market cap.
REITs are arguably Singapore's most popular asset class among retail
investors — "REIT hunter" is practically a national identity.

stockmarketwords.com currently has 5 investment strategies, none of which are
purpose-built for REIT analysis. The closest is **Dividend Daddy** (high
yield + low beta), but it doesn't account for REIT-specific metrics like
price-to-NAV ratio, gearing (leverage) ratio, or distribution frequency.

Adding a 6th strategy — **REIT Radar** 📡 — would directly serve the Wei Lin,
Ah Huat, and Mei Ling personas. Combined with SGX Ticker Support (separate
spec), it would make stockmarketwords.com the only free tool that scores both
US and Singapore REITs on a unified scale with ticker extraction capability.

## Goal

A new "REIT Radar" investment strategy that scores REITs (both US-listed and
SGX-listed, when available) on REIT-specific fundamentals, with its own
strategy page, scoring in the extraction tool, and a dedicated filtered view.

## Non-goals

- Replacing Dividend Daddy. REIT Radar is complementary — Dividend Daddy
  scores all high-yield stocks, REIT Radar is REIT-specific.
- Property trust analysis (e.g., business trusts, stapled securities).
  V1 includes only securities classified as REITs by Yahoo Finance sector
  data.
- NAV calculation from financial statements. V1 uses Yahoo Finance's
  `priceToBook` as a proxy for price-to-NAV.
- Distribution schedule tracking (monthly, quarterly, semi-annual).
- REIT-specific risk modeling (interest rate sensitivity, occupancy rates).

## User stories

- As a REIT-focused Singaporean investor (Wei Lin), I want to see REITs
  ranked by a REIT-specific score so that I can compare distribution yield,
  valuation, and leverage in one view without noise from non-REIT stocks.

- As a conservative investor (Ah Huat), I want to understand which REITs
  offer the best yield relative to their risk (gearing) so that I can pick
  REITs that complement my CPF-invested blue chips.

- As a user of the ticker extraction tool (any persona), I want to see a
  "REIT Radar" tab alongside the existing 5 strategy tabs so that when I
  paste an article mentioning REITs, I get REIT-specific scoring.

## Design

### 1. REIT Identification

Yahoo Finance classifies REITs under `sector = "Real Estate"` with
`industry` values like:
- "REIT—Diversified"
- "REIT—Industrial"
- "REIT—Retail"
- "REIT—Residential"
- "REIT—Office"
- "REIT—Healthcare Facilities"
- "REIT—Hotel & Motel"
- "REIT—Specialty"
- "REIT—Mortgage"

**Filter rule:** A ticker is a REIT if `industry LIKE 'REIT%'`. This
catches all Yahoo Finance REIT classifications. Store a derived boolean
`is_reit` flag in the `tickers` table (populated during `extract-metadata`).

### 2. Scoring Formula

The REIT Radar raw score combines three dimensions:

```python
def reit_radar_raw(row):
    """Score for REIT-focused investors. Only computed for is_reit=True tickers."""
    
    # Distribution Yield (40% weight)
    # Higher dividend yield = better for income investors
    yield_score = row['dividend_yield'] * 100 if pd.notna(row['dividend_yield']) else 0
    
    # Valuation: Price-to-Book as proxy for Price-to-NAV (30% weight)
    # Lower P/B = trading closer to or below NAV = better value
    # Invert: score = 100 - min(P/B * 20, 100) so that P/B < 1 scores high
    if pd.notna(row['price_to_book']) and row['price_to_book'] > 0:
        valuation_score = max(0, 100 - row['price_to_book'] * 20)
    else:
        valuation_score = 50  # neutral if unknown
    
    # Leverage: Debt-to-Equity as proxy for gearing (30% weight)
    # Lower D/E = less leveraged = safer
    # MAS regulatory limit for S-REITs: 50% gearing
    # Invert: score = 100 - min(D/E * 25, 100) so that low leverage scores high
    if pd.notna(row['debt_to_equity']) and row['debt_to_equity'] > 0:
        leverage_score = max(0, 100 - row['debt_to_equity'] * 25)
    else:
        leverage_score = 50  # neutral if unknown
    
    return (yield_score * 0.40) + (valuation_score * 0.30) + (leverage_score * 0.30)
```

**Why these weights:**
- **40% yield** — Distribution yield is the primary reason Singaporeans buy
  REITs. It must dominate the score.
- **30% valuation** — Price-to-NAV tells you if you're paying fair value
  for the underlying real estate. A REIT trading below NAV (P/B < 1) is a
  potential bargain.
- **30% leverage** — Gearing determines risk. MAS caps S-REIT gearing at
  50%; lower is safer. This rewards conservative balance sheets.

**Percentile ranking:** Like all strategies, the raw score is converted to a
1–100 percentile rank. But since only REITs are scored, the percentile pool
is ~200–300 US REITs (+ ~42 S-REITs once SGX is added), not the full ~8k
universe.

### 3. Pipeline Changes

#### a. `tickers` table — add `is_reit` column

```sql
ALTER TABLE tickers ADD COLUMN is_reit BOOLEAN DEFAULT 0;
```

Populated during `extract-metadata` when sector/industry data is fetched
from Yahoo Finance:

```python
# In extractors.py, after fetching metadata:
is_reit = 1 if (industry or '').startswith('REIT') else 0
# UPDATE tickers SET is_reit = ? WHERE symbol = ?
```

#### b. `strategy_scores` table — add `reit_radar_score` column

```sql
ALTER TABLE strategy_scores ADD COLUMN reit_radar_score INTEGER;
```

This column is NULL for non-REIT tickers (they aren't scored).

#### c. `builders.py` — add REIT Radar strategy

Add `reit_radar_raw()` function and integrate into the existing scoring
pipeline. Key difference from other strategies: **only score rows where
`is_reit = True`**. Non-REITs get NULL.

```python
# Filter to REITs only for this strategy
reit_df = df[df['is_reit'] == True].copy()
reit_df['reit_radar_raw'] = reit_df.apply(reit_radar_raw, axis=1)
reit_df['reit_radar_score'] = pd.qcut(
    reit_df['reit_radar_raw'], 100, labels=False, duplicates='drop'
) + 1
# Merge back: non-REITs keep reit_radar_score = NULL
```

#### d. `hugo_generators.py` — new strategy JSON

Generate `hugo/site/static/data/strategy_reit_radar.json` containing only
REIT tickers with their scores. Same format as existing strategy files.

Also add `reitRadar` to the scores dict in `all_tickers.json` (null for
non-REITs).

### 4. Hugo Site Changes

#### a. New strategy page

Create `hugo/site/content/strategy-reit-radar.md` and
`strategy-reit-radar.zh-cn.md`:

```yaml
---
title: "REIT Radar 📡"
layout: strategy-filter
strategy: reit_radar
description: "Score REITs by distribution yield, valuation (price-to-NAV), and leverage."
---
```

Content explains the strategy's methodology:
- What REITs are (Real Estate Investment Trusts)
- Why yield, valuation, and leverage matter
- How the score is calculated
- Singapore context: MAS gearing limits, S-REITs vs US REITs

#### b. Strategy filter page

The existing `strategy-filter.html` layout can be reused. It reads from
`strategy_reit_radar.json`. Add the REIT Radar to the DataTable config.

#### c. Ticker detail page

In `single.html`, add the REIT Radar score to the strategies card — but
only when the ticker is a REIT (when `reitRadar` score is non-null):

```html
{{- with index $scores "reitRadar" -}}
  {{- $scoresList = $scoresList | append (dict 
      "label" (i18n "strategy_reit_radar") 
      "url" "/strategy-reit-radar/" 
      "score" . 
      "desc" (i18n "strategy_reit_radar_long")
  ) -}}
{{- end -}}
```

#### d. Home page extraction tool

Add a 6th strategy tab "REIT Radar 📡" to the extraction tool. When
selected, the Web Worker loads `strategy_reit_radar.json`.

Changes to `portfolio-extractor.js`:
- Add tab HTML
- Add tab click handler
- Load `strategy_reit_radar.json` on tab select

#### e. Navigation

Add "REIT Radar" to the strategy dropdown in the site navigation (defined
in `hugo.toml` under `[menu]`).

### 5. i18n Keys (new)

| Key | English | Chinese |
|-----|---------|---------|
| `strategy_reit_radar` | REIT Radar 📡 | REIT雷达 📡 |
| `strategy_reit_radar_long` | Score REITs by distribution yield, valuation, and leverage | 按分配收益率、估值和杠杆对REIT评分 |
| `strategy_reit_radar_desc` | Find the best-value REITs with strong yields and conservative leverage | 寻找收益率高、杠杆保守的优质REIT |
| `reit_yield_weight` | Distribution Yield (40%) | 分配收益率（40%） |
| `reit_valuation_weight` | Price-to-NAV (30%) | 价格/净资产价值（30%） |
| `reit_leverage_weight` | Gearing / Leverage (30%) | 杠杆比率（30%） |
| `reit_only_note` | This strategy scores only REITs (Real Estate Investment Trusts) | 此策略仅对REIT（房地产投资信托）评分 |
| `nav_strategy_reit_radar` | REIT Radar | REIT雷达 |

### 6. Data Flow Summary

```
daily_metrics (dividend_yield, price_to_book, debt_to_equity)
    + tickers (is_reit flag)
    ↓ builders.py: reit_radar_raw() → percentile rank
strategy_scores.reit_radar_score (NULL for non-REITs)
    ↓ hugo_generators.py
strategy_reit_radar.json (REITs only, ~200-300 tickers)
all_tickers.json (reitRadar field, null for non-REITs)
    ↓ Hugo build
/strategy-reit-radar/ page (DataTable of REITs)
/tickers/<symbol>/ pages (6th strategy bar if REIT)
Home page extraction tool (6th tab)
```

## Affected files

| File | Change |
|------|--------|
| `python3/src/stock_ticker/migrations.py` | Add `is_reit` to tickers, `reit_radar_score` to strategy_scores |
| `python3/src/stock_ticker/extractors.py` | Set `is_reit` flag during metadata extraction |
| `python3/src/stock_ticker/builders.py` | Add `reit_radar_raw()` and REIT-only percentile scoring |
| `python3/src/stock_ticker/hugo_generators.py` | Generate `strategy_reit_radar.json`, add `reitRadar` to all_tickers |
| `hugo/site/content/strategy-reit-radar.md` (new) | English strategy page |
| `hugo/site/content/strategy-reit-radar.zh-cn.md` (new) | Chinese strategy page |
| `hugo/site/hugo.toml` | Add REIT Radar to menu |
| `hugo/site/layouts/tickers/single.html` | Show REIT Radar score when available |
| `hugo/site/static/js/portfolio-extractor.js` | Add 6th strategy tab |
| `hugo/site/i18n/en.toml` | New i18n keys |
| `hugo/site/i18n/zh-cn.toml` | New i18n keys |
| `tests/puppeteer/website-pages.e2e.test.js` | Add `/strategy-reit-radar/` to PAGES |

## Verification

- **Pipeline:** Run `ticker-cli extract-metadata --limit 50` → confirm
  `is_reit` flag set for Real Estate sector tickers.
- **Pipeline:** Run `ticker-cli build` → confirm `reit_radar_score` column
  populated for REIT tickers, NULL for others.
- **Pipeline:** Verify `strategy_reit_radar.json` contains only REIT tickers
  with scores.
- **Hugo:** Confirm `/strategy-reit-radar/` renders with a DataTable of
  REITs.
- **Hugo:** Open a known REIT ticker page (e.g., `/tickers/o/` for Realty
  Income). Confirm 6 strategy bars including REIT Radar.
- **Hugo:** Open a non-REIT ticker page (e.g., `/tickers/aapl/`). Confirm
  only 5 strategy bars (no REIT Radar).
- **Extraction:** Paste "I'm considering O, VNQ, and AAPL" into the
  extraction tool. Select REIT Radar tab. Confirm only O and VNQ (REITs)
  appear in results.
- **Automated:** Add `/strategy-reit-radar/` to the PAGES array in
  `tests/puppeteer/website-pages.e2e.test.js`.

## Open questions

1. **Mortgage REITs:** Yahoo classifies mortgage REITs as "REIT—Mortgage".
   These are financially very different from equity REITs (more like banks).
   Default: Include all REIT types in v1. Add a sub-filter later if needed.

2. **Price-to-Book vs actual NAV:** Using P/B as a NAV proxy is imperfect —
   book value ≠ NAV for all REITs. Default: Accept P/B as "good enough" for
   v1. Explore REIT-specific data providers for v2.

3. **S-REIT gearing data:** MAS requires gearing ratio disclosure, but
   Yahoo Finance may not expose it directly. Default: Use `debt_to_equity`
   as a proxy. Investigate alternative data sources for v2.

4. **Should REIT Radar appear in extraction results when no REITs are
   found?** Default: Show the tab but display "No REITs found in this text"
   message. This educates users about the strategy's existence.

5. **Score normalization with SGX REITs:** When SGX tickers are added
   (separate spec), the REIT universe grows. Should the percentile pool
   combine US + SGX REITs? Default: Yes — unified scoring. The REIT's
   exchange badge (NASDAQ/NYSE/SGX) will indicate origin.

## Alternatives considered

1. **Modify Dividend Daddy instead of new strategy** — Rejected. Dividend
   Daddy serves all high-yield stocks (utilities, telecoms, MLPs). A
   REIT-specific strategy needs REIT-specific inputs (leverage, NAV) and a
   REIT-only percentile pool.

2. **Use a REIT-specific data API (e.g., Nareit)** — Rejected for v1.
   Yahoo Finance provides sufficient data (yield, P/B, D/E) and is
   consistent with the existing pipeline. Consider for v2 if more granular
   REIT data is needed.

3. **Score all stocks on REIT Radar dimensions** — Rejected. Non-REIT
   stocks don't have meaningful P/B-as-NAV or REIT-style leverage
   constraints. Scoring them would be misleading. The NULL-for-non-REITs
   approach is honest.
