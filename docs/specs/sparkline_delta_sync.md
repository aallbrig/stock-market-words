# Sparkline ↔ Delta Chip Interactive Sync

**Status:** Draft
**Author:** Andrew Allbright
**Created:** 2026-04-19
**Supersedes:** —
**Superseded by:** —
**ADR:** [`docs/design/20260419_010536_UTC_adr_sparkline_delta_interaction.md`](../design/20260419_010536_UTC_adr_sparkline_delta_interaction.md)

## Context

Ticker detail pages now show two per-strategy visual indicators:

1. **Sparkline** — a Chart.js line chart plotting the last N trading days
   of a strategy's score (gated by `enableStrategyHistoryChart`).
2. **Delta chip** — a coloured badge showing score change vs the prior
   day, e.g. `▲ +3` (gated by `enableStrategyDeltaChip`).

These components are independently feature-flagged and share no runtime
state. When a user hovers a point on the sparkline, the tooltip shows the
date and score — but the delta chip still reflects the static "vs
yesterday" comparison. There's no way to see how today's score compares
to an arbitrary historical point without mental arithmetic.

See also: [Ticker Strategy History Chart spec](./ticker_strategy_history_chart.md).

## Goal

When a user hovers or clicks a sparkline data point, the delta chip next
to that strategy's score dynamically updates to show the delta between
**today's score** and the **hovered point's score**. On mouse-leave or
deselect, the chip reverts to its default (vs prior day) state. The
interaction is event-driven and fully decoupled — either component may be
absent due to feature flags.

## Non-goals

- **Click-to-pin behaviour.** v1 is hover-only. Click support is a future
  enhancement (clicking a point could pin the delta until a second click
  dismisses it).
- **Cross-strategy interaction.** Hovering one strategy's sparkline does
  not affect other strategies' delta chips.
- **Persisting the selected comparison.** When the user navigates away
  and returns, the chip resets to the default.
- **New feature flag.** The interaction auto-activates when both existing
  flags are on; no third flag.
- **Tooltip changes.** The sparkline tooltip remains unchanged.

## User stories

- **As a casual reader** viewing `/tickers/aapl/`, I want to hover over a
  historical point on the Moon Shot sparkline and see the delta chip update
  to show how today's score compares to that day, so I can quickly assess
  whether a recent score change is significant relative to last week.

- **As a returning reader**, I want the delta chip to revert to its
  default state when I stop hovering, so I always know the baseline
  comparison is "vs yesterday."

- **As the site operator**, I want the feature to degrade gracefully: if I
  disable sparklines but keep delta chips on (or vice versa), nothing
  breaks — each component works in isolation.

## Design

### Event-driven architecture (see ADR)

The sparkline JS **dispatches** DOM `CustomEvent`s on the `.strategy-row`
container. The delta chip JS **listens** on the same container. Neither
imports the other. If one component is absent, events are either never
dispatched or never consumed — no errors, no guards.

### Event contracts

```
strategy-spark:hover
  Dispatched when the user hovers a data point on a sparkline.
  detail: { strategy: string, score: number, date: string }

strategy-spark:leave
  Dispatched when the tooltip hides (mouse leaves the chart area).
  detail: { strategy: string }
```

Events bubble from the `<canvas>` but are dispatched on the nearest
`.strategy-row` ancestor to keep them scoped.

### Template changes

**File:** `hugo/site/layouts/tickers/single.html`

1. Wrap each strategy block in a `<div class="strategy-row"
   data-strategy="dividendDaddy">` (or equivalent key). This provides
   the event scope for both emitter and listener.

2. Add data attributes to the delta chip `<span>` rendered by
   `strategy-delta.html`:
   - `data-strategy="dividendDaddy"` — identifies which strategy.
   - `data-latest-score="48"` — today's score, used by JS for delta math.
   - `class="strategy-delta"` — selector for the live-update script.

**File:** `hugo/site/layouts/partials/strategy-delta.html`

Add `class="strategy-delta"`, `data-strategy="{{ .key }}"`, and
`data-latest-score="{{ .current }}"` to the rendered `<span>` badge.

### Sparkline changes (emitter)

**File:** `hugo/site/static/js/strategy-sparklines.js`

In `renderOne()`, add a Chart.js `onHover` plugin callback (or use the
existing `interaction` + tooltip hooks):

```js
// Inside the Chart options:
onHover: function (event, elements) {
  var row = el.closest('.strategy-row');
  if (!row) return;
  if (elements.length > 0) {
    var idx = elements[0].index;
    var score = scores[idx];
    var date = labels[idx];
    if (score !== null && score !== undefined) {
      row.dispatchEvent(new CustomEvent('strategy-spark:hover', {
        bubbles: false,
        detail: { strategy: strategy, score: score, date: date }
      }));
    }
  } else {
    row.dispatchEvent(new CustomEvent('strategy-spark:leave', {
      bubbles: false,
      detail: { strategy: strategy }
    }));
  }
}
```

Also add a `mouseleave` listener on the canvas itself to ensure
`strategy-spark:leave` fires when the cursor exits the chart entirely
(Chart.js `onHover` with no elements can be unreliable on fast exits).

### Delta chip live-update (listener)

**File (new):** `hugo/site/static/js/strategy-delta-live.js`

```js
(function () {
  function init() {
    var rows = document.querySelectorAll('.strategy-row');
    rows.forEach(function (row) {
      var chip = row.querySelector('.strategy-delta');
      if (!chip) return;

      var latestScore = parseInt(chip.dataset.latestScore, 10);
      var originalHTML = chip.innerHTML;
      var originalClass = chip.className;

      row.addEventListener('strategy-spark:hover', function (e) {
        var d = e.detail;
        var delta = latestScore - d.score;
        // Update chip text, arrow, and colour
        chip.innerHTML = formatDelta(delta, d.date);
        chip.className = deltaClass(delta);
      });

      row.addEventListener('strategy-spark:leave', function () {
        chip.innerHTML = originalHTML;
        chip.className = originalClass;
      });
    });
  }

  function formatDelta(delta, date) {
    if (delta > 0) return '▲ +' + delta;
    if (delta < 0) return '▼ ' + delta;
    return '— 0';
  }

  function deltaClass(delta) {
    var base = 'badge rounded-pill ms-2 align-middle';
    var style = 'font-size:0.7em;font-weight:500';
    if (delta > 0) return base + ' bg-success-subtle text-success-emphasis';
    if (delta < 0) return base + ' bg-danger-subtle text-danger-emphasis';
    return base + ' bg-secondary-subtle text-muted';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

### Script loading

**File:** `hugo/site/layouts/tickers/single.html` (bottom)

The new script is conditionally loaded when **both** flags are on:

```go-html
{{ if and site.Params.enableStrategyDeltaChip .Params.scoresHistory }}
<script src="{{ "js/strategy-delta-live.js" | relURL }}" defer></script>
{{ end }}
```

Alternatively, if we want the listener script to load whenever the delta
flag is on (even without sparklines — for future event sources), gate it
only on the delta flag and let the listener silently wait for events that
never arrive.

## Affected files

| File | Change |
|------|--------|
| `hugo/site/layouts/tickers/single.html` | Wrap strategy blocks in `.strategy-row`; load new script |
| `hugo/site/layouts/partials/strategy-delta.html` | Add `class`, `data-strategy`, `data-latest-score` attrs |
| `hugo/site/static/js/strategy-sparklines.js` | Dispatch `strategy-spark:hover` / `leave` events |
| `hugo/site/static/js/strategy-delta-live.js` (new) | Listen for events, update delta chip DOM |
| `tests/playwright/sparkline-delta-sync.spec.js` (new) | E2E tests for hover interaction |
| `tests/playwright/strategy-delta-chip.spec.js` | Verify existing tests still pass with new attrs |
| `tests/playwright/strategy-sparklines.spec.js` | Verify existing tests still pass with new events |

## Verification

### Manual

1. `hugo server` → open `/tickers/aapl/` → hover a point on any
   sparkline → the delta chip next to that strategy's score should update
   to reflect `today − hovered_score`.
2. Move the mouse off the sparkline → chip reverts to the default "vs
   yesterday" text.
3. Repeat on `/tickers/o/` (REIT) — REIT Radar row should also work.
4. Set `enableStrategyDeltaChip = false`, rebuild — sparklines render
   normally, no JS errors, no delta chip DOM.
5. Set `enableStrategyHistoryChart = false`, rebuild — delta chips render
   with their static server values, no JS errors, no sparklines.
6. Both flags off — only progress bars (if that flag is on), no errors.

### Automated

- **New file:** `tests/playwright/sparkline-delta-sync.spec.js`
  - Test 1: Simulate Chart.js hover by dispatching a synthetic
    `strategy-spark:hover` event on a `.strategy-row` element. Assert the
    `.strategy-delta` badge text updated.
  - Test 2: Dispatch `strategy-spark:leave`. Assert the badge reverted.
  - Test 3: On a page with delta chips but no sparklines (flag off),
    assert no JS errors in the console.
  - Test 4: On a page with sparklines but no delta chips, assert hover
    works without errors (event dispatches to no listener).

### Regression

- Run `npm run test:e2e` — existing sparkline and delta chip tests pass.

## Open questions

1. **Click-to-pin.** Should clicking a data point pin the delta until a
   second click dismisses? **Default:** no, hover-only for v1. Add in a
   follow-up spec if users request it.

2. **Transition animation.** Should the delta chip text fade or slide when
   updating? **Default:** instant swap for v1. CSS transitions can be
   added later without JS changes.

3. **Title attribute.** The current delta chip has `title="vs 2026-04-15"`
   for the comparison date. Should the hover-updated chip also update the
   title? **Default:** yes, update title to `"vs {hovered_date}"` and
   revert on leave.

4. **Debounce.** Rapid mouse movement across multiple points will fire
   many events. **Default:** no debounce — Chart.js already throttles
   `onHover` to ~60 fps, and the DOM update is trivial (one badge text
   swap). Add debounce only if profiling shows jank.

## Alternatives considered

See the [ADR](../design/20260419_010536_UTC_adr_sparkline_delta_interaction.md)
for the full decision record. Summary:

- **Direct DOM manipulation from sparklines JS** — rejected for coupling
  two feature-flagged components.
- **Global event bus on `document`** — rejected because row-scoped events
  are naturally isolated and need no strategy-key matching.
