/**
 * Google Analytics tests
 * Tests that GA is present on production site
 * Migrated from Puppeteer to Playwright
 */

import { test, expect } from '@playwright/test';

test.describe('Google Analytics', () => {
  test.skip(({ baseURL }) => !baseURL?.includes('stockmarketwords.com'), 
    'Google Analytics tests only run against production');

  test('production site has Google Analytics', async ({ page }) => {
    const requests = [];
    
    // Capture network requests
    page.on('request', request => {
      requests.push(request.url());
    });

    await page.goto('/');
    
    // Wait for page to fully load
    await page.waitForTimeout(2000);
    
    // Check for GA request
    const hasGA = requests.some(url => 
      url.includes('google-analytics.com') || 
      url.includes('googletagmanager.com')
    );
    
    expect(hasGA).toBe(true);
    console.log('✓ Google Analytics detected on production');
  });

  test('production site has Google AdSense', async ({ page }) => {
    const requests = [];
    
    page.on('request', request => {
      requests.push(request.url());
    });

    await page.goto('/');
    await page.waitForTimeout(2000);
    
    // Check for AdSense request
    const hasAdSense = requests.some(url => 
      url.includes('googlesyndication.com') || 
      url.includes('adsbygoogle')
    );
    
    expect(hasAdSense).toBe(true);
    console.log('✓ Google AdSense detected on production');
  });
});
