# AdSense Ad Placements

**Status:** Done
**Author:** Copilot
**Created:** 2026-04-14
**Completed:** 2026-04-14

## Problem

The site loads the AdSense library script (`adsbygoogle.js`) on every page, but:

1. There is no `ads.txt` file — Google requires this for authorized-seller verification.
2. There are zero `<ins class="adsbygoogle">` ad-unit placements in any template — so no ads actually render.
3. Ad-slot IDs from the AdSense console have not yet been generated.

## Scope

- **In scope:** `ads.txt`, ad placements on ticker detail pages, homepage, and article pages, Hugo config for ad-slot IDs, reusable partial.
- **Out of scope:** Auto-ads (full-page AdSense auto-placement), A/B testing, consent management / GDPR banner.

## Design

### 1. `ads.txt`

Create `hugo/site/static/ads.txt` so it deploys to `stockmarketwords.com/ads.txt`:

```
google.com, pub-2847616693333026, DIRECT, f08c47fec0942fa0
```

Fields: ad network domain, publisher ID (without `ca-` prefix), relationship, TAG-ID (Google's public certification authority ID).

### 2. Reusable Ad-Unit Partial

Create `hugo/site/layouts/partials/ad-unit.html` that:

- Only renders when `googleAdSenseId` is set (no ads in local dev).
- Accepts a slot ID via a Hugo param (e.g., `.Site.Params.adSlotTicker`).
- Renders the standard `<ins class="adsbygoogle">` block with responsive format.
- Pushes `adsbygoogle` after the element.

### 3. Ticker Detail Page Placement

Place the ad unit in `hugo/site/layouts/tickers/single.html` after the two-column data cards row (Market Data + Strategy Scores) and before the Strategy Interpretation card — Option A positioning for highest viewability (~85%) and estimated $8–15 RPM in the finance niche.

### 3b. Homepage Placement

Place the ad unit in `hugo/site/layouts/index.html` after the tool area (extractor + results + ticker lookup) and before the "Why this site exists" section — Option A for ~70% viewability. Wrapped in `col-lg-8` to match the page's content column width.

### 3c. Article Page Placement

Place the ad unit in `hugo/site/layouts/articles/single.html` after the `.article-content` div and before the `<footer>` — "Post-Content" position. Articles are 1,200–3,400 words of editorial content in a `col-md-8` single column. A horizontal/responsive ad format was chosen because:

- Horizontal fills the content column width cleanly, matching reading flow.
- Square ads are better suited to sidebars (this layout has none).
- Vertical ads disrupt reading flow in single-column layouts.
- Responsive lets Google auto-optimize between formats for best RPM.

Estimated RPM: $10–20 (finance editorial, indexed, organic traffic potential).

### 3d. Strategy Filter Page Placement

Place the ad unit in `hugo/site/layouts/page/strategy-filter.html` after the matching stocks table and before the "Explore other strategies" navigation card — "Post-Table" position (Option B). Key layout consideration: the pie chart and table are interactively linked (clicking a sector filters the table), so placing an ad between them (Option A) would break that interaction. A horizontal/responsive ad format was chosen to match the full-width column layout.

Estimated RPM: $8–15 (6 strategy pages, high-intent finance users, indexed).

### 4. Hugo Config

Add `adSlotTicker = ""`, `adSlotHome = ""`, `adSlotArticle = ""`, and `adSlotStrategy = ""` to `hugo.toml` params, injectable at build time via `HUGO_PARAMS_ADSLOTTICKER`, `HUGO_PARAMS_ADSLOTHOME`, `HUGO_PARAMS_ADSLOTARTICLE`, and `HUGO_PARAMS_ADSLOTSTRATEGY`.

### 5. Ad-Slot ID Provisioning (Manual Step)

The site owner must create an ad unit in the AdSense console:

1. Go to https://www.google.com/adsense → **Ads** → **By ad unit** → **Display ads**
2. Name it something like "Ticker Detail - In-Content"
3. Choose **Responsive** format
4. Click **Create** → copy the `data-ad-slot` value (a numeric string like `1234567890`)
5. Add it to the GitHub Actions workflow as an env var:
   `HUGO_PARAMS_ADSLOTTICKER: <slot-id>`

Until this step is completed, the partial will gracefully no-op (no ad rendered).

## Files Changed

| File | Action |
|------|--------|
| `hugo/site/static/ads.txt` | Create |
| `hugo/site/layouts/partials/ad-unit.html` | Create |
| `hugo/site/layouts/tickers/single.html` | Edit — insert partial call |
| `hugo/site/layouts/articles/single.html` | Edit — insert article ad partial call |
| `hugo/site/layouts/page/strategy-filter.html` | Edit — insert strategy ad partial call |
| `hugo/site/layouts/index.html` | Edit — insert homepage ad partial call |
| `hugo/site/hugo.toml` | Edit — add `adSlotTicker`, `adSlotHome`, `adSlotArticle`, and `adSlotStrategy` params |
| `.github/workflows/website-qa-deploy.yml` | Edit — add env var placeholder |
| `tests/playwright/analytics.spec.js` | Edit — add `ads.txt` test |

## Ad Unit Inventory

| AdSense Name | Slot ID | Hugo Param | Page Type | Position | Format | Est. RPM |
|---|---|---|---|---|---|---|
| Ticker Detail - In-Content | `4937671520` | `adSlotTicker` | `/tickers/*` | After data cards, before interpretation | Responsive | $8–15 |
| Homepage - Mid-Content | `5479550822` | `adSlotHome` | `/` | After tool area, before "Why this site exists" | Responsive | $5–10 |
| Article - Post-Content | `7424234063` | `adSlotArticle` | `/articles/*` | After article body, before footer | Horizontal/Responsive | $10–20 |
| Strategy - Post-Table | `2853387485` | `adSlotStrategy` | `/strategy/*` | After stocks table, before strategy nav | Horizontal/Responsive | $8–15 |

### Pages intentionally without ads

| Page Type | Reason |
|---|---|
| Glossary entries | Too short — ad would dominate the page, AdSense policy risk |
| Data tables (filtered, raw) | Utility pages — low dwell time, poor ad performance |
| Static pages (about, contact, privacy, methodology) | Informational/trust pages — ads undermine credibility |

## Testing

- Local: `hugo server` — no ads render (params empty), no errors.
- Production: after slot ID is set, Playwright test confirms `adsbygoogle` element exists on a ticker page.
- `ads.txt` is fetchable at root.

## Open Questions

- **Additional placements:** The current 4-unit inventory covers the primary page types. Monitor AdSense RPM data for 30 days before considering additional placements. Diminishing returns set in quickly beyond 4 well-placed units.
