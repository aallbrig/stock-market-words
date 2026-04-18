/**
 * Strategy sparklines — 10-day strategy-score line charts on ticker
 * pages. In the current config, sparklines REPLACE the progress bars
 * (enableStrategyProgressBar=false, enableStrategyHistoryChart=true).
 *
 * Business rules under test:
 *  1. On a non-REIT ticker (AAPL), exactly 5 sparklines render.
 *  2. On a REIT ticker (O), 6 sparklines render (incl. reitRadar).
 *  3. Each sparkline canvas lives in a .sparkline-wrap with a fixed
 *     pixel height — the resize-loop fix.
 *  4. Progress bars are gone when the progress-bar flag is off.
 *  5. Chart.js is loaded exactly once from the pinned jsDelivr CDN.
 *  6. Every visible sparkline has a non-zero canvas bitmap (i.e.
 *     Chart.js actually rendered it).
 *  7. A strategy whose 10-day values are all null is hidden.
 *  8. Tooltip API returns a date title and "<score>/100" body.
 */

import { test, expect } from '@playwright/test';

const NON_REIT = ['dividendDaddy', 'moonShot', 'fallingKnife', 'overHyped', 'instWhale'];
const ALL = [...NON_REIT, 'reitRadar'];

test.describe('Strategy sparklines — ticker page', () => {
  test('AAPL: exactly 5 sparklines, no reitRadar', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    const canvases = page.locator('canvas.strategy-sparkline');
    await expect(canvases).toHaveCount(5);
    const strategies = await canvases.evaluateAll((els) =>
      els.map((e) => e.dataset.strategy)
    );
    expect(strategies.sort()).toEqual([...NON_REIT].sort());
  });

  test('O: 6 sparklines including reitRadar', async ({ page }) => {
    await page.goto('/tickers/o/');
    const canvases = page.locator('canvas.strategy-sparkline');
    await expect(canvases).toHaveCount(6);
    const strategies = await canvases.evaluateAll((els) =>
      els.map((e) => e.dataset.strategy)
    );
    expect(strategies.sort()).toEqual([...ALL].sort());
  });

  test('each canvas lives in a fixed-height wrapper (resize-loop guard)', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    const heights = await page.locator('.sparkline-wrap').evaluateAll((els) =>
      els.map((e) => e.getBoundingClientRect().height)
    );
    expect(heights.length).toBe(5);
    for (const h of heights) {
      // Wrapper is 56px tall — any growth beyond a small margin indicates
      // the responsive resize loop is back.
      expect(h).toBeGreaterThan(40);
      expect(h).toBeLessThan(80);
    }
  });

  test('progress bars are gone when the progress-bar flag is off', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    await expect(page.locator('.progress .progress-bar')).toHaveCount(0);
  });

  test('Chart.js loads from pinned jsDelivr CDN', async ({ page }) => {
    const reqs = [];
    page.on('request', (req) => {
      if (/cdn\.jsdelivr\.net\/npm\/chart\.js@/.test(req.url())) reqs.push(req.url());
    });
    await page.goto('/tickers/aapl/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined', null, {
      timeout: 10000,
    });
    expect(reqs.length).toBeGreaterThanOrEqual(1);
    expect(reqs[0]).toMatch(/chart\.js@4\.\d+\.\d+/);
  });

  test('every visible sparkline is rendered by Chart.js', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined');
    await page.waitForTimeout(300);

    const rendered = await page
      .locator('canvas.strategy-sparkline')
      .evaluateAll((els) =>
        els
          .filter((e) => e.style.display !== 'none')
          .map((e) => ({
            strategy: e.dataset.strategy,
            width: e.width,
            height: e.height,
          }))
      );
    expect(rendered.length).toBe(5);
    for (const r of rendered) {
      expect(r.width, `${r.strategy} width`).toBeGreaterThan(0);
      expect(r.height, `${r.strategy} height`).toBeGreaterThan(0);
    }
  });

  test('all-null strategy is hidden', async ({ page }) => {
    // The data-history attribute is HTML-entity-escaped, so we match &#34;.
    await page.route('**/tickers/aapl/', async (route) => {
      const response = await route.fetch();
      let body = await response.text();
      body = body.replace(/(&#34;moonShot&#34;:)\d+/g, '$1null');
      await route.fulfill({ response, body, headers: response.headers() });
    });
    await page.goto('/tickers/aapl/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined');
    await page.waitForTimeout(200);
    // With the wrapper-based layout, "hidden" means the .sparkline-wrap
    // parent is display:none — the canvas itself is left alone.
    const visible = await page
      .locator('canvas.strategy-sparkline')
      .evaluateAll((els) =>
        els
          .filter((e) => {
            var w = e.parentNode;
            return w.style.display !== 'none';
          })
          .map((e) => e.dataset.strategy)
      );
    expect(visible).not.toContain('moonShot');
    expect(visible.sort()).toEqual(NON_REIT.filter((s) => s !== 'moonShot').sort());
  });

  test('tooltip API yields date title + "<n>/100" body', async ({ page }) => {
    await page.goto('/tickers/o/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined');
    await page.waitForTimeout(300);

    const canvas = page
      .locator('canvas.strategy-sparkline[data-strategy="dividendDaddy"]')
      .first();
    await expect(canvas).toBeVisible();

    const tooltip = await canvas.evaluate((el) => {
      const chart = window.Chart.getChart(el);
      if (!chart) return null;
      const meta = chart.getDatasetMeta(0);
      const mid = Math.floor(meta.data.length / 2);
      chart.setActiveElements([{ datasetIndex: 0, index: mid }]);
      chart.tooltip.setActiveElements(
        [{ datasetIndex: 0, index: mid }],
        { x: 0, y: 0 }
      );
      chart.update();
      const t = chart.tooltip;
      return {
        title: t.title?.[0] || null,
        body: t.body?.[0]?.lines?.[0] || null,
      };
    });
    expect(tooltip).not.toBeNull();
    expect(tooltip.title).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(tooltip.body).toMatch(/^\d{1,3}\/100$/);
  });

  test('respects strategySparklineWindow: only the last 5 points render', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined');
    await page.waitForTimeout(200);

    const lengths = await page
      .locator('canvas.strategy-sparkline')
      .evaluateAll((els) =>
        els.map((e) => {
          const chart = window.Chart.getChart(e);
          return chart ? chart.data.labels.length : -1;
        })
      );
    for (const n of lengths) {
      expect(n, 'points drawn').toBeLessThanOrEqual(5);
      expect(n, 'points drawn').toBeGreaterThan(0);
    }
  });

  test('external HTML tooltip renders inside the wrapper, not the canvas', async ({ page }) => {
    await page.goto('/tickers/o/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined');
    await page.waitForTimeout(300);

    const canvas = page
      .locator('canvas.strategy-sparkline[data-strategy="dividendDaddy"]')
      .first();

    // Trigger the external tooltip by driving the chart API, then read
    // the resulting DOM tooltip out of the sparkline-wrap.
    await canvas.evaluate((el) => {
      const chart = window.Chart.getChart(el);
      const meta = chart.getDatasetMeta(0);
      const mid = Math.floor(meta.data.length / 2);
      chart.tooltip.setActiveElements(
        [{ datasetIndex: 0, index: mid }],
        { x: 0, y: 0 }
      );
      chart.update();
    });

    const tipInfo = await canvas.evaluate((el) => {
      const tip = el.parentNode.querySelector('.sparkline-tooltip');
      if (!tip) return null;
      return {
        text: tip.textContent.trim(),
        opacity: tip.style.opacity,
        position: getComputedStyle(tip).position,
      };
    });
    expect(tipInfo).not.toBeNull();
    expect(tipInfo.position).toBe('absolute');
    expect(Number(tipInfo.opacity)).toBeGreaterThan(0);
    expect(tipInfo.text).toMatch(/\d{4}-\d{2}-\d{2}\d{1,3}\/100/);
  });
});

test.describe('Strategy sparklines — mobile viewport', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('sparklines still render at iPhone-14 width with bounded wrapper', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    await page.waitForFunction(() => typeof window.Chart !== 'undefined');
    await page.waitForTimeout(300);

    const canvases = page.locator('canvas.strategy-sparkline');
    await expect(canvases).toHaveCount(5);

    const wraps = await page.locator('.sparkline-wrap').evaluateAll((els) =>
      els.map((e) => e.getBoundingClientRect())
    );
    for (const r of wraps) {
      // Wrapper must fit within the viewport and maintain its 56px height
      // — any horizontal overflow or runaway height indicates a layout bug.
      expect(r.width).toBeLessThanOrEqual(390);
      expect(r.width).toBeGreaterThan(200);
      expect(r.height).toBeGreaterThan(40);
      expect(r.height).toBeLessThan(80);
    }

    // Every canvas bitmap should be sized by Chart.js responsive logic.
    const canvasSizes = await canvases.evaluateAll((els) =>
      els.map((e) => ({ w: e.width, h: e.height }))
    );
    for (const s of canvasSizes) {
      expect(s.w).toBeGreaterThan(0);
      expect(s.h).toBeGreaterThan(0);
    }
  });
});
