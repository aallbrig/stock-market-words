# ADR: Strategy Ratings History Chart on Ticker Pages

**Status:** Accepted
**Type:** Architecture Decision Record
**Created:** 2026-04-17 (UTC 2026-04-18)
**Related spec:** [`docs/specs/ticker_strategy_history_chart.md`](../specs/ticker_strategy_history_chart.md)

---

## Context

`strategy_scores` already stores a full daily history (one row per ticker
per trading day, five–six 1–100 scores per row — see
[`database_schema.md`](./20260408_013203_UTC_database_schema.md)). The ticker
detail page at `/tickers/<symbol>/` shows only the **latest** snapshot as
five/six horizontal progress bars.

Users reading an individual ticker page have no way to see whether a score
is rising, falling, or volatile. "O scored 82 on Dividend Daddy today" is
less informative than "O has been 78 → 80 → 82 over ten sessions."

The data exists. The gap is purely presentation.

## Decision

Add a 10-trading-day **strategy ratings history** to the ticker detail
page as a **sparkline per strategy**, rendered inline alongside each
existing progress bar in the strategy-scores card. The sparklines are:

- **One per strategy** — each strategy row gets its own ~60×20 px
  sparkline next to its 0–100 progress bar. No shared legend, no series
  isolation UI — each sparkline is self-labeled by the row it sits in.
- **Interactive** — hovering a sparkline reveals a dot at the nearest
  point plus a tooltip showing date + score for that strategy.
- **Hugo-gated** — rendered only when a site-level feature flag is on.
  Flag defaults to **on**.

**Why sparklines over a single multi-line chart.** Five or six
percentile-rank series in one ~120 px chart with only 10 x-points
tangles visually; percentile scores jitter day-to-day and lines cross.
A Singapore-leaning mobile audience would get a cluttered legend and
awkward per-series toggles. Sparklines sidestep all of that: the reader
compares today's bar to the last 10 days' *shape* at a glance, no
legend, no isolation, no cross-series color decoding.

### Feature flag

A single Hugo site param controls visibility:

```toml
# hugo/site/hugo.toml
[params]
  enableStrategyHistoryChart = true
```

Template check:

```go-html
{{ if site.Params.enableStrategyHistoryChart }}
  {{/* render chart card */}}
{{ end }}
```

**Why a Hugo flag and not a Python pipeline flag:** the data is cheap to
compute (≤10 rows × ≤6 columns per ticker, read from an existing indexed
table). Always computing the history and gating only the **render** keeps
the pipeline simple and lets us roll the UI forward/back without
regenerating data. The JSON payload with `scoresHistory` present but the
flag off is ~5–10% larger than today's `all_tickers.json`; acceptable.

### Data shape

The history ships inline with the existing `all_tickers.json` under a new
`scoresHistory` field on each ticker row:

```json
{
  "symbol": "CRM",
  "scores": { "dividendDaddy": 42, "moonShot": 18, ... },
  "scoresHistory": [
    { "date": "2026-04-04", "dividendDaddy": 40, "moonShot": 20, "fallingKnife": 55, "overHyped": 30, "instWhale": 88, "reitRadar": null },
    { "date": "2026-04-07", "dividendDaddy": 41, ... },
    ...
    { "date": "2026-04-17", "dividendDaddy": 42, ... }
  ]
}
```

- Ascending date order (oldest → newest). The latest entry's scores
  duplicate the existing `scores` block; that duplication is intentional —
  the chart should not need a separate "current" lookup.
- Up to 10 most-recent **trading** days for this symbol (not calendar
  days). Fewer if the ticker is young.
- `null` for a strategy on a day where the score is unset (new tickers,
  non-REIT for `reitRadar`).

Sizing estimate: ~8,000 tickers × 10 days × 6 ints ≈ 480k ints plus
dates. Adds ≈1 MB to `all_tickers.json` (before minification). `all_tickers.json`
is consumed by Hugo at build time — it is *not* fetched by the browser —
so the payload cost is borne by the build, not the user.

### Pipeline integration

Add a single new helper in `hugo_generators.py` that the existing
`generate_all_tickers_json()` calls:

```python
def fetch_scores_history(cursor, symbol, limit=10):
    cursor.execute("""
        SELECT date, dividend_daddy_score, moon_shot_score,
               falling_knife_score, over_hyped_score,
               inst_whale_score, reit_radar_score
        FROM strategy_scores
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
    """, (symbol, limit))
    return list(reversed(cursor.fetchall()))
```

No new CLI command. No new `run-all` step. The work slots into the
existing `ticker-cli hugo all-tickers` substep (itself part of
`ticker-cli hugo all`, itself part of `ticker-cli run-all`). Because the
strategy-scores history is already populated by `ticker-cli build`, the
ordering in `run-all` (sync-ftp → extract-prices → extract-metadata →
**build** → **hugo all**) is already correct.

To keep the single-ticker query off the hot path, prefer a single batched
query:

```sql
SELECT symbol, date, dividend_daddy_score, ... , reit_radar_score
FROM strategy_scores
WHERE (symbol, date) IN (
  SELECT symbol, date FROM strategy_scores
  WHERE symbol IN (...)
  GROUP BY symbol
  ORDER BY date DESC
  LIMIT 10 PER symbol  -- emulated in Python
)
```

Pragmatically: pull the last 10 distinct dates from `strategy_scores`,
then one batched `SELECT ... WHERE date IN (...)` scoped to the ticker
set. This avoids 8,000 per-symbol round-trips.

### Client rendering

- Library: **Chart.js 4** (UMD build), loaded from the **jsDelivr CDN**
  with a pinned version and Subresource Integrity (SRI) hash:

  ```html
  <script
    src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"
    integrity="sha384-<pin-at-implementation-time>"
    crossorigin="anonymous"
    defer></script>
  ```

  Pin the exact version; do not use `@4` floating tags. Confirm the SRI
  hash from jsDelivr at implementation time and record it in the spec.
- Chosen because it is well-documented, handles tooltips out of the box,
  and supports many small instances on one page cheaply. Six tiny
  sparklines × one `new Chart()` each is negligible overhead at this
  data volume.
- Per-sparkline config: `type: 'line'`, `pointRadius: 0`,
  `pointHoverRadius: 4`, both axes hidden, y-axis fixed `min: 0, max: 100`,
  legend hidden, `spanGaps: true`. Border color matches the strategy's
  existing progress-bar Bootstrap color.
- Load only on ticker pages. The `<script>` tag and the sparkline
  initializer are both emitted inside the `{{ if site.Params.enableStrategyHistoryChart }}`
  block so flag-off pages don't fetch Chart.js at all.
- No new Web Worker. The dataset per canvas is ≤10 numbers; render
  synchronously after DOMContentLoaded.
- Graceful degradation: a `<noscript>` inside each sparkline cell says
  "Enable JavaScript to view the 10-day trend."

### i18n

Very minimal with sparklines — no chart title, no axis labels, no
legend. Only the tooltip needs a localized phrasing: `"{date}: {score}/100"`.
The score unit ("/100") is culture-neutral; the date format is handled
by Chart.js using the page locale. Net: one or two new i18n keys, not a
full chart-copy set.

## Consequences

**Positive**

- Adds meaningful temporal context to every ticker page without a schema
  change or a new CLI command.
- Feature-flagged so the chart can be disabled site-wide with a one-line
  config edit if it regresses Core Web Vitals or confuses users.
- Historical score rows are currently write-only; this gives them a first
  read surface, making the data's long-term retention question more
  concrete (see the open retention question in `database_schema.md`).

**Negative**

- `all_tickers.json` grows ~1 MB. Build-time only; no browser cost. If
  the file ever becomes the build bottleneck, split history into
  `all_tickers_history.json` (separate read in `_content.gotmpl`).
- Adds a client-side JS dependency (Chart.js, ~70 KB gzipped) loaded
  from jsDelivr. Mitigated by pinning the version with SRI, loading it
  only on ticker pages, and deferring execution. Trade-off accepted:
  CDN fetch introduces a third-party runtime dependency but gives the
  site free edge caching and a smaller repo than a vendored bundle.
- For brand-new tickers with <10 days of scores, the chart is sparse.
  Acceptable: the legend still renders; the line is short.

## Alternatives considered

1. **Single multi-line chart with legend-click isolation.** Rejected.
   5–6 percentile lines in a small chart tangle visually; legend
   interaction is awkward on mobile; a Singapore mobile audience would
   feel the pain first. Sparklines deliver the "is it trending?"
   question more directly and need no legend UI.
2. **Per-ticker JSON files** (`/static/data/ticker_history/<sym>.json`,
   fetched lazily). Rejected for v1: introduces ~8k files per build and a
   runtime fetch per page view, for a dataset small enough to inline.
   Revisit if `all_tickers.json` exceeds a few MB.
3. **Hand-rolled SVG polylines (~2 KB, zero deps).** Rejected for v1 only
   because Chart.js gives us battle-tested tooltips and hover-dot behavior
   for free. Strong candidate for v2 if we decide the 70 KB Chart.js
   payload isn't earning its keep.
4. **Server-rendered sparkline (SVG, no JS)**. Rejected: no tooltip —
   the hover-to-reveal-exact-score is half the value.
5. **Lightweight library (uPlot, 45 KB)**. Rejected for v1 on
   documentation and tooling grounds; uPlot is faster but you have to
   write the tooltip and DOM glue yourself. Swap later if perf matters.
6. **Self-hosted Chart.js** (`static/js/vendor/chart.umd.min.js`).
   Rejected for v1 to keep the repo slim. CDN fetch with SRI is
   acceptable; revisit if we move to a stricter third-party policy.
7. **Python feature flag gating the JSON field itself**. Rejected:
   two flags (Python + Hugo) is more operational surface than the feature
   warrants. Data is cheap to generate.

## Rollout

1. Migration: none.
2. Land pipeline change (`generate_all_tickers_json` emits
   `scoresHistory`). Verify in `all_tickers.json`.
3. Land Hugo template change behind the flag with flag **on**.
4. Visual QA on three tickers: a REIT (e.g., `/tickers/o/`), a brand-new
   ticker with <10 days of data, and a mega-cap (e.g., `/tickers/aapl/`).
5. If regressions surface, flip `enableStrategyHistoryChart = false` in
   `hugo.toml` and redeploy. Data keeps flowing; UI hides.
