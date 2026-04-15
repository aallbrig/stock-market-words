# ADR: Articles Should Include Data Visualizations

**Date:** 2026-04-15
**Status:** Accepted

## Context

Articles on stockmarketwords.com serve multiple audiences: retail investors looking for insights, enthusiasts curious about market structure, and potential customers for the analysis tools this site provides. Raw text, while informative, misses an opportunity to create memorable, shareable, and high-impact content.

Data visualization — charts and maps — materially increases:
- Time-on-page (readers explore interactive elements)
- Shareability (charts are easy to screenshot and share)
- Search relevance (unique data visualizations attract backlinks)
- Trust (data-backed claims feel more credible than prose assertions)

## Decision

**Every article should include at least one data visualization** — either a chart or a map (ideally both if the topic warrants).

### Guidelines

**Maps are GOLD.** If an article covers a geographic topic (a country, a region, a shipping route, a market area), include an interactive Leaflet.js map. Maps orient readers, create engagement, and differentiate the article from generic financial content.

**Charts are GOLD.** If an article covers a trend, comparison, or volume over time, include a Chart.js chart. Even a simple 5-year bar chart of a key metric adds significant value over a table.

**Data quality trumps chart quantity.** A single well-sourced chart with clear attribution is better than multiple speculative visualizations. Always cite the source of data (EIA, UNCTAD, SEC filings, etc.) in a caption below the chart.

**Placement:** Place visualizations at the point in the article where they are most useful — typically right before or after the section that discusses what the chart shows. For geographic orientation, a map near the top of the article is appropriate. For trend data, position the chart at the start of the relevant section.

**Ad placement and visualizations:** Both ads and visualizations are high-engagement elements. Do not place them adjacent to each other. The article ad should appear at approximately the midpoint of the prose, surrounded by text on both sides. See ADR `20260414_230800_UTC_article_ad_placement.md`.

### Reference implementations

- **Map:** `layouts/shortcodes/strait-map.html` — Interactive Leaflet.js map with port markers, shipping lane, and trade flow labels.
- **Chart:** `layouts/shortcodes/malacca-trade-chart.html` — Chart.js bar chart with year-over-year data and source citation.

### Technology

See ADR `20260415_000000_UTC_data_visualization_technology.md` for the canonical library choices (Chart.js 4.4.1 for charts, Leaflet.js 1.9.4 for maps).

## Consequences

- Article authors (human or AI) are expected to include at least one visualization per article.
- If time or data availability prevents a visualization, note it in the article spec and revisit when data becomes available.
- Reusable shortcodes should be created where a visualization pattern repeats across articles (e.g., `strait-map.html`, `grab-price-chart.html`). One-off charts for a specific article can be article-specific shortcodes or inline.
