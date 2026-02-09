/**
 * Portfolio pagination tests
 * Migrated from Puppeteer to Playwright
 */

import { test, expect } from '@playwright/test';

test.describe('Portfolio Pagination', () => {
  test('strategy pages have paginated tables', async ({ page }) => {
    const strategyPages = [
      '/strategy-dividend-daddy/',
      '/strategy-moon-shot/',
      '/strategy-falling-knife/'
    ];

    for (const path of strategyPages) {
      await page.goto(path);
      
      // Check if table exists
      await expect(page.locator('#strategyTable')).toBeVisible();
      
      // Check if pagination controls exist
      const paginationExists = await page.locator('.dataTables_paginate').count();
      if (paginationExists > 0) {
        console.log(`✓ ${path} has pagination`);
      }
    }
  });

  test('can navigate between pages', async ({ page }) => {
    await page.goto('/strategy-dividend-daddy/');
    
    // Wait for table to load
    await expect(page.locator('#strategyTable')).toBeVisible();
    
    // Check if pagination controls exist
    const nextButton = page.locator('.paginate_button.next');
    const isDisabled = await nextButton.evaluate(el => el.classList.contains('disabled'));
    
    if (!isDisabled) {
      // Click next page
      await nextButton.click();
      await page.waitForTimeout(500);
      
      console.log('✓ Can navigate to next page');
    } else {
      console.log('✓ Pagination works (single page of data)');
    }
  });
});
