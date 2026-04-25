/**
 * E2E tests for Ticker Lookup Enhancements
 *
 * Covers three features added by ticker-lookup.js:
 *   1. Autocomplete — dropdown with symbol/name matches
 *   2. Not-found feedback — inline error instead of 404
 *   3. Recent lookups — localStorage chips rendered on page load
 *
 * These tests run against the Hugo dev server (same as other specs).
 */

import { test, expect } from '@playwright/test';

test.describe('Ticker Lookup Enhancements', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#ticker-lookup-input')).toBeVisible({ timeout: 10000 });
  });

  test('autocomplete dropdown appears when typing a symbol prefix', async ({ page }) => {
    const input = page.locator('#ticker-lookup-input');

    await input.fill('AAPL');

    // Wait for the dropdown to appear (data loads async on first focus/input)
    const dropdown = page.locator('#ticker-lookup-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 10000 });

    // Dropdown should contain an item for AAPL
    await expect(dropdown).toContainText('AAPL');
  });

  test('autocomplete dropdown appears when typing a company name', async ({ page }) => {
    const input = page.locator('#ticker-lookup-input');

    await input.fill('apple');

    const dropdown = page.locator('#ticker-lookup-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 10000 });

    // Should find at least one result with "Apple" in the company name
    const items = dropdown.locator('.dropdown-item');
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
  });

  test('dropdown closes on Escape key', async ({ page }) => {
    const input = page.locator('#ticker-lookup-input');
    await input.fill('MSFT');

    const dropdown = page.locator('#ticker-lookup-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 10000 });

    await input.press('Escape');
    await expect(dropdown).not.toBeVisible();
  });

  test('ArrowDown highlights the first dropdown item', async ({ page }) => {
    const input = page.locator('#ticker-lookup-input');
    await input.fill('A');

    const dropdown = page.locator('#ticker-lookup-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 10000 });

    await input.press('ArrowDown');

    // The first item should now have the .active class
    const firstItem = dropdown.locator('.dropdown-item').first();
    await expect(firstItem).toHaveClass(/active/);
  });

  test('invalid ticker shows inline error and does not navigate', async ({ page }) => {
    const input = page.locator('#ticker-lookup-input');
    const form = page.locator('#ticker-lookup-form');
    const errorDiv = page.locator('#ticker-lookup-error');

    // Wait for data to load first by focusing
    await input.focus();
    // Give the data file time to load (it's lazy on focus)
    await page.waitForTimeout(3000);

    const initialUrl = page.url();

    await input.fill('ZZZZZZ');
    await form.locator('button[type="submit"]').click();

    // Error message should be visible
    await expect(errorDiv).toBeVisible({ timeout: 5000 });
    await expect(errorDiv).toContainText('ZZZZZZ');
    await expect(errorDiv).toContainText('was not found');

    // URL should not have changed
    expect(page.url()).toBe(initialUrl);
  });

  test('recent lookups chips render from localStorage', async ({ page }) => {
    // Pre-populate localStorage with recent lookups
    await page.evaluate(function () {
      localStorage.setItem('smw-recent-tickers', JSON.stringify(['MSFT', 'AAPL']));
    });

    // Reload so the init() function picks up the stored recents
    await page.reload();
    await expect(page.locator('#ticker-lookup-input')).toBeVisible({ timeout: 10000 });

    const recentContainer = page.locator('#ticker-recent-lookups');
    await expect(recentContainer).toBeVisible({ timeout: 5000 });
    await expect(recentContainer).toContainText('MSFT');
    await expect(recentContainer).toContainText('AAPL');
  });

  test('recent chips are links to the correct ticker pages', async ({ page }) => {
    await page.evaluate(function () {
      localStorage.setItem('smw-recent-tickers', JSON.stringify(['TSLA']));
    });
    await page.reload();
    await expect(page.locator('#ticker-lookup-input')).toBeVisible({ timeout: 10000 });

    const chip = page.locator('#ticker-recent-lookups a').first();
    await expect(chip).toContainText('TSLA');

    const href = await chip.getAttribute('href');
    expect(href).toContain('tickers/tsla');
  });
});
