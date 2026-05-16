/**
 * Shared Playwright fixtures.
 *
 * Extends the built-in `page` fixture with a base-path-aware `goto()` so that
 * tests written with leading-slash paths (e.g. `/strategy/dividend-daddy/`)
 * work correctly against both:
 *   - Local Hugo dev server (no base path)
 *   - GitHub Pages subpath deployment (e.g. /stock-market-words)
 *
 * Set the PLAYWRIGHT_BASE_PATH env var to the subpath prefix when running
 * against a subpath-deployed site (e.g. PLAYWRIGHT_BASE_PATH=/stock-market-words).
 * When unset, behavior is identical to the standard @playwright/test page.
 */
import { test as base, expect } from '@playwright/test';

const BASE_PATH = (process.env.PLAYWRIGHT_BASE_PATH || '').replace(/\/$/, '');

export const test = base.extend({
  page: async ({ page }, use) => {
    if (!BASE_PATH) {
      await use(page);
      return;
    }

    const originalGoto = page.goto.bind(page);
    page.goto = (url, options) => {
      if (typeof url === 'string' && url.startsWith('/')) {
        url = BASE_PATH + url;
      }
      return originalGoto(url, options);
    };

    await use(page);
  },
});

export { expect };
