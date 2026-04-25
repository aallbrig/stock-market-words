/**
 * E2E tests for the Navigation Bar Ticker Lookup Widget
 *
 * Covers the compact nav widget added to every page via navigation.html.
 * The widget shares logic with the home-page widget but displays errors
 * and recent lookups inside the autocomplete dropdown rather than as
 * persistent DOM elements below the form.
 *
 * Depends on: ticker_lookup_enhancements spec (ticker-lookup.js, ticker-lookup.json)
 */

import { test, expect } from '@playwright/test';

const NAV_INPUT  = '#nav-ticker-lookup-input';
const NAV_FORM   = '#nav-ticker-lookup-form';
const NAV_DROPDOWN = '#nav-ticker-lookup-dropdown';

test.describe('Nav Bar Ticker Lookup Widget', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator(NAV_INPUT)).toBeVisible({ timeout: 10000 });
  });

  test('nav widget is present and visible on the home page', async ({ page }) => {
    await expect(page.locator(NAV_INPUT)).toBeVisible();
    await expect(page.locator(NAV_FORM).locator('button[type="submit"]')).toBeVisible();
  });

  test('nav widget is present on a non-home page (ticker detail page)', async ({ page }) => {
    await page.goto('/tickers/aapl/');
    await expect(page.locator(NAV_INPUT)).toBeVisible({ timeout: 10000 });
  });

  test('nav autocomplete dropdown appears when typing a symbol prefix', async ({ page }) => {
    const input = page.locator(NAV_INPUT);
    await input.fill('AAPL');

    const dropdown = page.locator(NAV_DROPDOWN);
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    await expect(dropdown).toContainText('AAPL');
  });

  test('nav autocomplete dropdown appears when typing a company name', async ({ page }) => {
    const input = page.locator(NAV_INPUT);
    await input.fill('microsoft');

    const dropdown = page.locator(NAV_DROPDOWN);
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    const items = dropdown.locator('.dropdown-item');
    expect(await items.count()).toBeGreaterThan(0);
  });

  test('nav invalid ticker shows error in dropdown and does not navigate', async ({ page }) => {
    const input = page.locator(NAV_INPUT);

    // Wait for the data file to load by focusing first.
    await input.focus();
    await page.waitForTimeout(3000);

    const initialUrl = page.url();

    await input.fill('ZZZZZZ');
    await page.locator(NAV_FORM).locator('button[type="submit"]').click();

    // Error message should appear inside the dropdown.
    const dropdown = page.locator(NAV_DROPDOWN);
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    await expect(dropdown).toContainText('ZZZZZZ');
    await expect(dropdown).toContainText('was not found');

    // URL should be unchanged.
    expect(page.url()).toBe(initialUrl);
  });

  test('nav recent lookups appear in dropdown on empty focus', async ({ page }) => {
    // Pre-populate localStorage with recent lookups.
    await page.evaluate(function () {
      localStorage.setItem('smw-recent-tickers', JSON.stringify(['NVDA', 'TSLA']));
    });

    await page.reload();
    await expect(page.locator(NAV_INPUT)).toBeVisible({ timeout: 10000 });

    // Focus the input without typing — should show recent dropdown.
    await page.locator(NAV_INPUT).focus();

    const dropdown = page.locator(NAV_DROPDOWN);
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    await expect(dropdown).toContainText('Recent');
    await expect(dropdown).toContainText('NVDA');
    await expect(dropdown).toContainText('TSLA');
  });

  test('nav search bar is always visible on mobile (below the navbar)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // The search bar lives in a persistent strip below the navbar, so it is
    // always visible on mobile — no hamburger interaction needed.
    const input = page.locator(NAV_INPUT);
    await expect(input).toBeVisible({ timeout: 5000 });

    // The nav links are still hidden behind the hamburger toggler.
    const toggler = page.locator('.navbar-toggler');
    await expect(toggler).toBeVisible({ timeout: 5000 });
  });
});
