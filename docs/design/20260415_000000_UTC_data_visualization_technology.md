# ADR: Data Visualization Technology Stack

**Date:** 2026-04-15
**Status:** Accepted

## Context

The project creates editorial content (articles) about stock market topics with a goal of delighting users with data. Articles about shipping lanes, geographic regions, and financial trends benefit from visual representations of data. We need a consistent, documented approach to what visualization libraries we use so contributors and AI agents can make consistent decisions.

Multiple visualization needs exist:
- Geographic maps (shipping lanes, chokepoints, regional market coverage)
- Time-series charts (price data, trade volumes, historical trends)
- Comparison charts (stock performance, market metrics)

## Decision

### Charts: Chart.js 4.4.1

Use **Chart.js 4.4.1** loaded from jsDelivr CDN for all data charts:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```

Chart.js is already in use in the project (see `grab-price-chart.html`, `grab-vs-spy.html`). It supports bar, line, scatter, pie/doughnut, and mixed chart types. It is lightweight, has no runtime dependencies, and works well inside Hugo shortcodes.

**Pattern:** Each chart lives in its own Hugo shortcode (`layouts/shortcodes/*.html`) or inline in the article markdown via a dedicated shortcode. Charts are wrapped in an IIFE to avoid global scope pollution. Always guard with `if (typeof Chart === 'undefined') return;`.

### Maps: Leaflet.js 1.9.4 with OpenStreetMap tiles

Use **Leaflet.js 1.9.4** loaded from jsDelivr CDN for all geographic maps:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.css"
      integrity="sha256-QZFpF9DkpabUBLoCc7fQJVCmtag/LaVAfAkUJSfuNyY=" crossorigin="" />
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.js"
        integrity="sha256-MgH13bFTTNqsnuEoqNPBLDaqxjGH+lCpqrukmXc8Ppg=" crossorigin=""></script>
```

**IMPORTANT:** The SRI hashes above are correct. Many published sources list incorrect hashes for Leaflet 1.9.4. Use these exact values. See `layouts/shortcodes/strait-map.html` as the canonical example.

Leaflet is used in `strait-map.html` for the interactive Strait of Malacca map. Use OpenStreetMap tile layer with proper attribution.

### No other visualization libraries

Do not introduce D3.js, Highcharts, ECharts, or other libraries without a superseding ADR. Keep the dependency footprint small.

## Consequences

- Any contributor building a chart uses Chart.js 4.4.1 from this CDN URL — do not use another version or source without updating this ADR.
- Any contributor building a map uses Leaflet.js 1.9.4 with the SRI hashes above — do not use another version or source without updating this ADR.
- AI agents working on this codebase can answer "what graphing library do we use?" by reading this ADR.
- When Chart.js or Leaflet is upgraded, this ADR must be updated with new version numbers and SRI hashes.
