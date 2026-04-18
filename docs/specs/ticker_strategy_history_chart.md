# Ticker Page: 10-Day Strategy Ratings History Chart

**Status:** Draft
**Author:** Andrew Allbright
**Created:** 2026-04-17
**Supersedes:** —
**Superseded by:** —
**ADR:** [`docs/design/20260418_023906_UTC_adr_strategy_history_chart.md`](../design/20260418_023906_UTC_adr_strategy_history_chart.md)

## Context

Individual ticker pages (`/tickers/<symbol>/`) currently show today's
strategy scores as progress bars — one snapshot, no trajectory. We already
record a full daily history in the `strategy_scores` table (see
[`database_schema.md`](../design/20260408_013203_UTC_database_schema.md)),
but nothing on the site surfaces it. A reader who wants to know whether a
ticker's *Moon Shot* score is rising or falling has to take our word that
the latest number matters.

The companion ADR explains the data-shape and feature-flag decisions. This
spec is the implementation contract: what pages change, what files get
touched, what "done" looks like.

## Goal

On every ticker detail page, a reader sees a small sparkline next to each
strategy's progress bar showing that strategy's score over the last 10
trading days. Hovering a sparkline reveals a tooltip with the exact date
and score. Rendered only when the site-level Hugo flag is on (default on).

## Non-goals

- Historical price/volume charts. This is about *strategy scores* only;
  OHLC candlesticks belong to a later spec.
- Configurable window length (30-day, 90-day toggles). v1 is a fixed
  10-trading-day window.
- Downloadable history (CSV export). Out of scope.
- Any pipeline change beyond enriching `all_tickers.json`. No new CLI
  command, no new schema column.
- A Python-side feature flag. Only the render is gated.
- A shared multi-line chart with a legend. v1 is one sparkline per
  strategy.
- Per-ticker lazy-fetched history JSON. Inline in `all_tickers.json` for
  v1.
- Self-hosting Chart.js. v1 uses a pinned CDN URL with SRI.

## User stories

- **As a casual reader** browsing `/tickers/crm/`, I want to see how CRM's
  strategy scores have moved over the last two weeks of trading so I can
  tell at a glance whether today's score is an outlier or a trend.

- **As an analytically-minded reader**, I want to hover a specific point
  on the chart and see the exact date and score so I can cite a concrete
  number when sharing the page.

- **As a user interested in one strategy**, I want each strategy's
  trend to sit next to its own progress bar so I can focus on a single
  strategy without the visual noise of other lines crossing it.

- **As the site operator**, I want a single config flag I can flip off
  without redeploying data if the chart ever regresses page performance.

## Design

See the ADR for the *why*. This section is the concrete *what*.

### Data pipeline

**File:** `python3/src/stock_ticker/hugo_generators.py`

Modify `generate_all_tickers_json()` (existing, ~line 656) to attach a
`scoresHistory` array to each ticker row.

1. Before the per-ticker loop, fetch the last 10 distinct dates from
   `strategy_scores`:

   ```python
   cursor.execute("""
       SELECT DISTINCT date FROM strategy_scores
       ORDER BY date DESC LIMIT 10
   """)
   history_dates = sorted(r[0] for r in cursor.fetchall())  # ascending
   ```

2. Batch-fetch all history rows for those dates in a single query:

   ```python
   placeholders = ','.join('?' * len(history_dates))
   cursor.execute(f"""
       SELECT symbol, date,
              dividend_daddy_score, moon_shot_score, falling_knife_score,
              over_hyped_score, inst_whale_score, reit_radar_score
       FROM strategy_scores
       WHERE date IN ({placeholders})
   """, history_dates)
   history_by_symbol = defaultdict(list)
   for row in cursor.fetchall():
       history_by_symbol[row[0]].append(row[1:])
   ```

3. In the existing ticker loop, attach:

   ```python
   raw = sorted(history_by_symbol.get(row[0], []), key=lambda r: r[0])
   ticker['scoresHistory'] = [
       {
           'date': d,
           'dividendDaddy': _int_or_none(dd),
           'moonShot':      _int_or_none(ms),
           'fallingKnife':  _int_or_none(fk),
           'overHyped':     _int_or_none(oh),
           'instWhale':     _int_or_none(iw),
           'reitRadar':     _int_or_none(rr),
       }
       for (d, dd, ms, fk, oh, iw, rr) in raw
   ]
   ```

   where `_int_or_none` is a tiny helper (or inline the conditional, matching
   the existing `safe_float` style in the same function).

No changes to `ticker-cli run-all`, `build`, or any other CLI command.
The enrichment runs inside the already-scheduled
`ticker-cli hugo all-tickers` substep.

### Hugo content adapter

**File:** `hugo/site/content/tickers/_content.gotmpl`

Add `scoresHistory` to the params dict passed to `$.AddPage`:

```go-html
"scoresHistory" .scoresHistory
```

### Hugo feature flag

**File:** `hugo/site/hugo.toml`

Under `[params]`:

```toml
enableStrategyHistoryChart = true
```

### Template changes

**File:** `hugo/site/layouts/tickers/single.html`

Modify each strategy row inside the existing strategy-scores card (lines
~122–199). For each `{{ with index $scores "<strategyKey>" }}` block, add
a sparkline canvas beside the existing `<div class="progress">`. Example
for Dividend Daddy:

```go-html
{{ with index $scores "dividendDaddy" }}
<div>
  <div class="d-flex justify-content-between mb-1">
    <a href="{{ "/strategy/dividend-daddy/" | relLangURL }}" class="text-decoration-none">{{ i18n "strategy_dividend_daddy" }}</a>
    <strong>{{ . }}/100</strong>
  </div>
  <div class="d-flex align-items-center gap-2">
    <div class="progress flex-grow-1" style="height:10px">
      <div class="progress-bar bg-success" style="width:{{ . }}%"></div>
    </div>
    {{ if and site.Params.enableStrategyHistoryChart $.Params.scoresHistory }}
      <canvas class="strategy-sparkline" width="60" height="20"
              data-strategy="dividendDaddy"
              data-color="#198754"
              data-history='{{ $.Params.scoresHistory | jsonify }}'></canvas>
    {{ end }}
  </div>
  <small class="text-muted">{{ i18n "strategy_dividend_daddy_long" }}</small>
</div>
{{ end }}
```

Repeat the sparkline canvas insertion inside each of the other strategy
blocks (`moonShot`, `fallingKnife`, `overHyped`, `instWhale`, `reitRadar`),
with `data-strategy` and `data-color` matching that strategy's existing
Bootstrap color:

| Strategy | `data-color` | Matches |
|---|---|---|
| `dividendDaddy` | `#198754` | `bg-success` |
| `moonShot`      | `#ffc107` | `bg-warning` |
| `fallingKnife`  | `#dc3545` | `bg-danger`  |
| `overHyped`     | `#0dcaf0` | `bg-info`    |
| `instWhale`     | `#0d6efd` | `bg-primary` |
| `reitRadar`     | `#20c997` | existing REIT teal |

At the bottom of the template, emit a script block — gated by the same
flag — that loads Chart.js from jsDelivr and then runs
`strategy-sparklines.js`:

```go-html
{{ if site.Params.enableStrategyHistoryChart }}
<script
  src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"
  integrity="sha384-<pin-at-implementation-time>"
  crossorigin="anonymous"
  defer></script>
<script src="{{ "js/strategy-sparklines.js" | relURL }}" defer></script>
{{ end }}
```

The `defer` attribute on both ensures Chart.js runs before the
sparklines script, and both run after HTML parse.

### Client JS

**File (new):** `hugo/site/static/js/strategy-sparklines.js`

```js
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('canvas.strategy-sparkline').forEach((el) => {
    const strategy = el.dataset.strategy;
    const color    = el.dataset.color || '#0d6efd';
    const history  = JSON.parse(el.dataset.history || '[]');
    const labels   = history.map((row) => row.date);
    const scores   = history.map((row) => row[strategy]);

    if (!scores.some((v) => v !== null && v !== undefined)) return;

    new Chart(el, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: scores,
          borderColor: color,
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.3,
          fill: false,
          spanGaps: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            displayColors: false,
            callbacks: {
              title: (items) => items[0].label,
              label: (item) => `${item.parsed.y}/100`,
            },
          },
        },
        scales: {
          x: { display: false },
          y: { display: false, min: 0, max: 100 },
        },
        interaction: { mode: 'nearest', intersect: false },
      },
    });
  });
});
```

No vendored Chart.js file. Version is pinned in `single.html` via the
`@4.4.7` tag (or whichever 4.x is current at implementation time) and
locked with an SRI hash captured from jsDelivr at implementation time.

### Client JS

**File (new):** `hugo/site/static/js/strategy-history-chart.js`

Responsibilities:

1. Read `data-history` and `data-labels` from the canvas.
2. Build a Chart.js `line` chart with one dataset per non-empty strategy
   (skip a strategy entirely if every value is null — keeps REIT lines
   off non-REIT pages).
3. Enable point hover + tooltip showing `date, strategy, score`.
4. Default `hidden: false` on each dataset; rely on Chart.js's
   built-in legend click handler for per-series isolation.
5. Y-axis: fixed 0–100 range (scores are percentiles).
6. X-axis: dates formatted `MMM D` (e.g., `Apr 4`).

**Vendored library:** `hugo/site/static/js/vendor/chart.umd.min.js`
(pin the version; document the version and source URL in a header
comment at the top of `strategy-history-chart.js`).

### i18n keys (new)

Sparklines need no chart title or description — they sit inside the
existing strategy-scores card which is already titled. No new i18n keys
are required for v1. Tooltip content (`"{date}: {score}/100"`) is
format-only and reuses Chart.js's built-in locale handling for the date
label.

If we later want a small helper line like "Last 10 trading days — hover
to see exact scores" above the card, that becomes one key,
`ticker_strategy_history_hint`, added to both `en.toml` and
`zh-cn.toml`. Not in v1.

## Affected files

| File | Change |
|------|--------|
| `python3/src/stock_ticker/hugo_generators.py` | `generate_all_tickers_json()` emits `scoresHistory` |
| `hugo/site/content/tickers/_content.gotmpl` | Pass `scoresHistory` into page params |
| `hugo/site/layouts/tickers/single.html` | Inline sparkline canvas per strategy row; flag-gated Chart.js + init script tags |
| `hugo/site/hugo.toml` | `enableStrategyHistoryChart = true` under `[params]` |
| `hugo/site/static/js/strategy-sparklines.js` (new) | Instantiates one Chart.js sparkline per `canvas.strategy-sparkline` |
| `tests/puppeteer/website-pages.e2e.test.js` | (optional) assert six `canvas.strategy-sparkline` elements are present on a REIT page and five on a non-REIT page |

## Verification

- **Pipeline:** Run `ticker-cli hugo all-tickers`. Confirm
  `hugo/site/data/all_tickers.json` contains a `scoresHistory` array of
  length ≤10 on a known ticker (e.g., `jq '.tickers[] | select(.symbol=="AAPL") | .scoresHistory | length' hugo/site/data/all_tickers.json`).
- **Pipeline:** Confirm dates in `scoresHistory` are ascending.
- **Pipeline:** Confirm `reitRadar` is null on a non-REIT (e.g., AAPL)
  and non-null on a REIT (e.g., O) for at least one date.
- **Hugo (flag on):** `hugo server` → open `/tickers/aapl/` → confirm
  five sparklines render (one per strategy row, no REIT Radar), each
  ~60×20 px, hovering any sparkline reveals a tooltip with the expected
  date and score.
- **Hugo (flag on):** Open `/tickers/o/` → confirm six sparklines
  including REIT Radar.
- **Hugo (flag on):** Open `/zh-cn/tickers/aapl/` → confirm sparklines
  still render; existing strategy row labels remain in Chinese; tooltip
  date/score format is unaffected.
- **Hugo (flag off):** Set `enableStrategyHistoryChart = false`,
  rebuild, confirm no `canvas.strategy-sparkline` elements exist and the
  jsDelivr Chart.js script tag is not emitted (verify with View Source).
- **Network:** Confirm Chart.js loads from
  `cdn.jsdelivr.net/npm/chart.js@<version>/...` with a valid SRI hash —
  browser blocks execution on hash mismatch; none should fire.
- **New ticker:** Find a ticker with <10 days of history in
  `strategy_scores`. Confirm its sparklines render with the available
  points (Chart.js `spanGaps`) and no console errors.

## Open questions

1. **Chart.js version pin.** Default: pin the latest 4.x release at
   implementation time (e.g., `4.4.7`) and record the jsDelivr SRI hash
   in a header comment at the top of `strategy-sparklines.js` and in the
   `<script>` tag in `single.html`.
2. **Trading-day gaps.** If one of the 10 most recent dates is missing
   for a symbol, the sparkline has a gap. Default: render with
   `spanGaps: true` so the line connects across null points. Tooltip is
   suppressed on the missing date.
3. **Mobile layout.** Sparklines at 60×20 px fit comfortably on narrow
   screens even next to the progress bar + score text. Default: accept
   current sizing; revisit if mobile QA surfaces cramping.
4. **Color palette.** Default: reuse each strategy's existing
   progress-bar color (hex values mapped from Bootstrap classes — see
   Design § Template changes).
5. **Data retention dependency.** The retention question in
   `database_schema.md` is now slightly more load-bearing — the
   sparklines give `strategy_scores` history its first read surface.
   Default: doesn't block v1; flag for a future retention spec.
6. **CDN reliability.** jsDelivr is used by Bootstrap itself and is
   reliable in Singapore. If we later observe load failures or adopt a
   stricter third-party policy, swap to `hugo/site/static/js/vendor/chart.umd.min.js`
   and update the `<script src>` — no other code changes.

## Alternatives considered

See the ADR. Short version: a separate per-ticker JSON, a no-JS SVG
sparkline, and uPlot were all considered and rejected for v1 in favor of
inlining history into `all_tickers.json` and rendering with Chart.js.
