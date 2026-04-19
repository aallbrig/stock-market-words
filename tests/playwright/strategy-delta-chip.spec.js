/**
 * Strategy delta chip — small "▲+3" / "▼-2" badge next to each
 * strategy score on ticker detail pages, comparing today's score to
 * the earliest score in the 10-day history window.
 *
 * Business rules under test:
 *  1. When enableStrategyDeltaChip is on, a chip appears next to each
 *     rendered strategy score (non-REITs: 5 chips; REITs: up to 6).
 *  2. The chip's arrow matches the sign of the delta (▲ positive,
 *     ▼ negative, — zero).
 *  3. Chip carries a `title` attribute of the form "vs YYYY-MM-DD"
 *     pointing at the comparison date.
 *  4. With enableStrategyDeltaChip=false (simulated by stripping chips
 *     from the HTML), the page renders without any chip badges — the
 *     flag-off contract.
 */

import { test, expect } from '@playwright/test';

test.describe('Strategy delta chip — ticker page', () => {
  test('AAPL: a chip renders next to each strategy score (5 chips)', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    const chips = page.locator('.card-body .badge.rounded-pill');
    await expect(chips).toHaveCount(5);
  });

  test('chip arrow matches the sign of the delta', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    const chipData = await page
      .locator('.card-body .badge.rounded-pill')
      .evaluateAll((els) =>
        els.map((el) => ({
          text: el.textContent.trim(),
          title: el.getAttribute('title'),
        }))
      );

    for (const { text, title } of chipData) {
      expect(title, `chip title format`).toMatch(/^vs \d{4}-\d{2}-\d{2}$/);
      // "▲ +3", "▼ -2", "— 0"
      const m = text.match(/^([▲▼—])\s*(-?\+?\d+)$/);
      expect(m, `chip text "${text}" parses`).not.toBeNull();
      const [, arrow, numStr] = m;
      const n = parseInt(numStr, 10);
      if (arrow === '▲') expect(n, `▲ should be >0`).toBeGreaterThan(0);
      else if (arrow === '▼') expect(n, `▼ should be <0`).toBeLessThan(0);
      else expect(n, `— should be 0`).toBe(0);
    }
  });

  test('flag-off contract: stripping chips from HTML leaves the page coherent', async ({
    page,
  }) => {
    // Simulate enableStrategyDeltaChip=false by removing every chip badge
    // from the HTML before the browser sees it. The page should still
    // render the 5 strategy rows (sparklines stay) with no chips.
    await page.route('**/tickers/aapl/', async (route) => {
      const response = await route.fetch();
      let body = await response.text();
      body = body.replace(
        /<span class="strategy-delta badge rounded-pill[\s\S]*?<\/span>/g,
        ''
      );
      await route.fulfill({ response, body, headers: response.headers() });
    });

    await page.goto('/tickers/aapl/');
    await expect(page.locator('.card-body .badge.rounded-pill')).toHaveCount(0);
    await expect(page.locator('canvas.strategy-sparkline')).toHaveCount(5);
  });
});
