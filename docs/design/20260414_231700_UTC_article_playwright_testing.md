# ADR: Playwright Tests for Articles

**Status:** Accepted
**Author:** Andrew Allbright
**Created:** 2026-04-14

## Context

Articles on stockmarketwords.com increasingly include interactive elements
beyond plain markdown: Chart.js charts (GRAB article), Leaflet.js maps (Strait
of Malacca article), and inline ad shortcodes. These integrations can break
silently — a wrong SRI hash, a CDN outage, or a shortcode rendering error
produces a page that *looks* published but has broken functionality.

The existing E2E test suite (`tests/puppeteer/website-pages.e2e.test.js`)
checks that pages return 200 and have basic content, but does not verify that
interactive elements actually load and function.

## Decision

**Every article that includes interactive elements (maps, charts, embedded
tools) MUST have a Playwright test verifying those elements load correctly.**

### What to test

At minimum, each article's test should verify:

1. **Page loads** — HTTP 200, title present
2. **CDN resources load** — no console errors related to SRI hash mismatches
   or failed resource loads
3. **Interactive elements render** — the DOM element exists and has child
   content (e.g., `#strait-map` has children, meaning Leaflet initialized)
4. **Ticker links work** — spot-check that a sample of ticker links
   (e.g., `/tickers/zim/`, `/tickers/xom/`) are present in the page

### Test file location

Article-specific tests go in `tests/puppeteer/` following the existing naming
convention:

- `tests/puppeteer/article-malacca.e2e.test.js` — Strait of Malacca article
- `tests/puppeteer/article-grab.e2e.test.js` — GRAB analysis article
- Or consolidated into `tests/puppeteer/website-pages.e2e.test.js` with
  article-specific assertions

### Example test structure (Playwright with Firefox)

```javascript
const { test, expect } = require('@playwright/test');

test('Strait of Malacca article - map loads', async ({ page }) => {
  // Collect console errors
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  await page.goto('/articles/strait-of-malacca-trade-and-tickers/');

  // Map container exists and has content (Leaflet initialized)
  const map = page.locator('#strait-map');
  await expect(map).toBeVisible();
  const childCount = await map.evaluate(el => el.children.length);
  expect(childCount).toBeGreaterThan(0);

  // No SRI or resource loading errors
  const sriErrors = errors.filter(e => e.includes('integrity') || e.includes('hash'));
  expect(sriErrors).toHaveLength(0);

  // Spot-check ticker links exist
  await expect(page.locator('a[href="/tickers/zim/"]')).toHaveCount(2); // body + summary table
  await expect(page.locator('a[href="/tickers/xom/"]')).toHaveCount(2);
});
```

### When to write tests

| Article type | Required tests |
|---|---|
| Plain markdown (text + tables + links) | Page loads, ticker links present |
| Chart.js integration | Above + chart canvas renders |
| Leaflet/map integration | Above + map container has children, no SRI errors |
| Custom shortcode with JS | Above + shortcode DOM element renders |

### Checklist for new articles

- [ ] Add article URL to `website-pages.e2e.test.js` PAGES array
- [ ] If article has interactive elements, add element-specific assertions
- [ ] Run tests locally before committing: `npm run test:e2e:pages`

## Consequences

- Broken CDN integrations (like the SRI hash mismatch caught today) will be
  caught before deployment.
- Tests serve as living documentation of what each article's interactive
  features are.
- Test maintenance cost is low — most articles need only 5-10 lines of
  assertions beyond the standard page-load check.

## Status

Accepted — applies to all articles published after this date. Existing articles
should be backfilled with tests as capacity allows.
