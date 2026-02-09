/**
 * End-to-end performance test for TickerEngine UI
 * Tests the extraction tool on the main page with all three sample texts
 * 
 * TIMEOUT CONFIGURATION:
 * - Local development: 60 seconds (default)
 * - CI/CD: 10 seconds (set via TIMEOUT_SECONDS=10)
 * 
 * Migrated from Puppeteer to Playwright
 */

import { test, expect } from '@playwright/test';

// CI uses 10 seconds, local dev uses 60 seconds
const MAX_PROCESSING_TIME_MS = process.env.TIMEOUT_SECONDS 
  ? parseInt(process.env.TIMEOUT_SECONDS) * 1000 
  : 60000;

console.log(`TickerEngine E2E Tests - Max processing time: ${MAX_PROCESSING_TIME_MS / 1000}s`);

test.describe('TickerEngine E2E Performance Tests', () => {
  /**
   * Helper function to test a sample text
   */
  async function testSampleText(page, sampleIndex, sampleName) {
    // Navigate to home page
    await page.goto('/');
    
    // Wait for the form to be visible
    await expect(page.locator('#ticker-form')).toBeVisible({ timeout: 10000 });
    
    // Click the sample text button (0-indexed)
    const sampleButtons = page.locator('.btn-outline-secondary');
    await expect(sampleButtons).toHaveCount(3, { timeout: 5000 });
    
    await sampleButtons.nth(sampleIndex).click();
    
    // Wait a bit for text to populate
    await page.waitForTimeout(500);
    
    // Verify text area has content
    const textareaValue = await page.locator('#user-input').inputValue();
    expect(textareaValue.length).toBeGreaterThan(0);
    
    console.log(`${sampleName}: Text populated (${textareaValue.length} chars)`);
    
    // Record start time
    const startTime = Date.now();
    
    // Click the Extract Portfolios button
    await page.locator('#ticker-form button[type="submit"]').click();
    
    // Wait for loading indicator to appear
    await expect(page.locator('#loading-indicator')).toBeVisible({ timeout: 5000 });
    console.log(`${sampleName}: Processing started...`);
    
    // Wait for result card to appear (this means processing is complete)
    await expect(page.locator('#result-card')).toBeVisible({ 
      timeout: MAX_PROCESSING_TIME_MS 
    });
    
    // Calculate processing time
    const processingTime = Date.now() - startTime;
    console.log(`${sampleName}: Processing completed in ${processingTime}ms`);
    
    // Verify loading indicator is hidden
    await expect(page.locator('#loading-indicator')).toBeHidden();
    
    // Verify results are displayed
    await expect(page.locator('#result-card')).toBeVisible();
    
    // Verify portfolio strategies are rendered
    const portfolioStrategies = page.locator('#portfolio-strategies');
    await expect(portfolioStrategies).toBeVisible();
    
    const strategiesContent = await portfolioStrategies.innerHTML();
    expect(strategiesContent.length).toBeGreaterThan(0);
    
    // Assert processing time is under timeout
    expect(processingTime).toBeLessThan(MAX_PROCESSING_TIME_MS);
    
    return processingTime;
  }

  test('Sample 1: SHORT text completes within timeout', async ({ page }) => {
    const time = await testSampleText(page, 0, 'SHORT');
    console.log(`✓ SHORT sample completed in ${time}ms`);
  });

  test('Sample 2: MEDIUM text completes within timeout', async ({ page }) => {
    const time = await testSampleText(page, 1, 'MEDIUM');
    console.log(`✓ MEDIUM sample completed in ${time}ms`);
  });

  test('Sample 3: LONG text completes within timeout', async ({ page }) => {
    const time = await testSampleText(page, 2, 'LONG');
    console.log(`✓ LONG sample completed in ${time}ms`);
  });

  test.describe('UI Validation', () => {
    test('Page loads with all required elements', async ({ page }) => {
      await page.goto('/');
      
      // Check for ticker form
      await expect(page.locator('#ticker-form')).toBeVisible();
      
      // Check for text area
      await expect(page.locator('#user-input')).toBeVisible();
      
      // Check for submit button
      await expect(page.locator('#ticker-form button[type="submit"]')).toBeVisible();
      
      // Check for all three sample buttons
      await expect(page.locator('.btn-outline-secondary')).toHaveCount(3);
      
      console.log('✓ All UI elements present');
    });

    test('Sample buttons populate text area', async ({ page }) => {
      await page.goto('/');
      
      // Test first sample button
      const sampleButtons = page.locator('.btn-outline-secondary');
      await sampleButtons.nth(0).click();
      
      await page.waitForTimeout(500);
      
      const textareaValue = await page.locator('#user-input').inputValue();
      expect(textareaValue.length).toBeGreaterThan(0);
      expect(textareaValue).toContain('cat');
      
      console.log('✓ Sample button populates text area');
    });

    test('Loading indicator shows during processing', async ({ page }) => {
      await page.goto('/');
      
      // Fill in text
      await page.locator('#user-input').fill('Apple Microsoft Google');
      
      // Submit form
      await page.locator('#ticker-form button[type="submit"]').click();
      
      // Loading indicator should appear
      await expect(page.locator('#loading-indicator')).toBeVisible();
      
      console.log('✓ Loading indicator appears');
    });
  });
});

// Set test timeout based on processing time
test.setTimeout(MAX_PROCESSING_TIME_MS + 15000);
