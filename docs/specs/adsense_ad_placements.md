# AdSense Ad Placements

**Status:** In Progress
**Author:** Copilot
**Created:** 2026-04-14

## Problem

The site loads the AdSense library script (`adsbygoogle.js`) on every page, but:

1. There is no `ads.txt` file — Google requires this for authorized-seller verification.
2. There are zero `<ins class="adsbygoogle">` ad-unit placements in any template — so no ads actually render.
3. Ad-slot IDs from the AdSense console have not yet been generated.

## Scope

- **In scope:** `ads.txt`, one ad placement on ticker detail pages, Hugo config for ad-slot IDs, reusable partial.
- **Out of scope:** Auto-ads (full-page AdSense auto-placement), ad placements on non-ticker pages, A/B testing, consent management / GDPR banner.

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

### 4. Hugo Config

Add `adSlotTicker = ""` to `hugo.toml` params, injectable at build time via `HUGO_PARAMS_ADSLOTTICKER`.

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
| `hugo/site/hugo.toml` | Edit — add `adSlotTicker` param |
| `.github/workflows/website-qa-deploy.yml` | Edit — add env var placeholder |
| `tests/playwright/analytics.spec.js` | Edit — add `ads.txt` test |

## Testing

- Local: `hugo server` — no ads render (params empty), no errors.
- Production: after slot ID is set, Playwright test confirms `adsbygoogle` element exists on a ticker page.
- `ads.txt` is fetchable at root.
