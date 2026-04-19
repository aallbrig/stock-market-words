# ADR: Event-Driven Sparkline ↔ Delta Chip Interaction

**Date:** 2026-04-19
**Status:** Accepted
**Author:** Copilot (requested by Andrew Allbright)

## Context

Ticker detail pages render two independent, feature-flagged UI components
per strategy row:

| Component | Flag | Renders |
|-----------|------|---------|
| **Sparkline** (Chart.js) | `enableStrategyHistoryChart` | 10-day score trend line |
| **Delta chip** | `enableStrategyDeltaChip` | Badge showing score change vs prior day |

Both are gated independently — a site operator may enable either, both, or
neither. Today they share no runtime state: the delta chip is
server-rendered HTML; the sparkline is client-rendered Chart.js.

Users have requested that hovering or clicking a sparkline data point
should update the neighbouring delta chip to show the delta between the
**latest** score and the **hovered** score, then revert on mouse-leave or
deselect. This creates a runtime coupling between two independently-flagged
components.

## Decision

Use a **DOM CustomEvent bus** scoped to each strategy row container. The
sparkline JS dispatches events; the delta chip JS listens for them. Neither
component imports or references the other.

### Event contracts

| Event name | `detail` shape | Emitted by | Consumed by |
|---|---|---|---|
| `strategy-spark:hover` | `{ strategy: string, score: number, date: string }` | `strategy-sparklines.js` | `strategy-delta-live.js` |
| `strategy-spark:leave` | `{ strategy: string }` | `strategy-sparklines.js` | `strategy-delta-live.js` |

Events are dispatched on the closest `.strategy-row` ancestor of the
canvas. The delta chip listener is also attached to `.strategy-row`. If
the row element doesn't exist (broken markup), the event simply doesn't
propagate — no errors.

### Why CustomEvents on an ancestor element

- **Decoupled:** The sparkline JS doesn't need to know whether a delta
  chip exists. If the chip flag is off, no listener is attached and the
  event is a no-op.
- **Scoped:** Events don't pollute `document`; each strategy row is
  independent. A hover on the Dividend Daddy sparkline cannot accidentally
  update the Moon Shot delta chip.
- **Testable:** Tests can dispatch synthetic events on a `.strategy-row`
  and assert the delta chip updated, without instantiating Chart.js.
- **Extensible:** Future components (e.g., a score annotation, a
  comparison overlay) can subscribe to the same events without modifying
  existing code.

### Why not direct DOM manipulation from sparklines

The sparkline JS could find the delta chip by selector and mutate it
directly. This was rejected because:

1. It couples two feature-flagged components — the sparkline script would
   break or need guards when the delta flag is off.
2. It violates single-responsibility: the chart script shouldn't know the
   DOM structure of the delta badge.
3. Testing becomes harder — you can't test the delta update logic without
   a real Chart.js instance.

### Why not a global event bus / pub-sub library

A global bus (e.g., on `window` or `document`) would work but loses the
natural DOM scoping. With row-level events, there's zero risk of
cross-strategy contamination and no need for strategy-key matching in
listeners.

### Delta chip update logic

The delta chip is server-rendered with the default (vs prior day) delta.
The new `strategy-delta-live.js` script:

1. On load, reads `data-latest-score` from each `.strategy-delta` badge
   and stores the original `innerHTML` for restoration.
2. On `strategy-spark:hover`, computes `latestScore - hoveredScore` and
   rewrites the badge's text, arrow, and colour class.
3. On `strategy-spark:leave`, restores the original server-rendered HTML.

This means the page works without JS (server-rendered delta is the
fallback) and degrades gracefully if only one feature flag is enabled.

## Consequences

- **Two new JS files** are conditionally loaded (one per feature). Both
  are small (<2 KB unminified).
- **Hugo template changes** are minimal: add `data-*` attributes to the
  delta chip `<span>` and wrap each strategy in a `.strategy-row` `<div>`.
- **No new feature flag.** The interaction activates automatically when
  both existing flags are on. No additional config surface.
- **No new external dependencies.** Uses the browser's native
  `CustomEvent` API (IE 11+ / all modern browsers).
