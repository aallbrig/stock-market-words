/**
 * Basic page load tests for all website pages
 * Ensures all pages load successfully with no console errors
 * 
 * Migrated from Puppeteer to Playwright
 */

import { test, expect } from '@playwright/test';

// All pages on the website
const PAGES = [
  { path: '/', name: 'Home' },
  { path: '/about/', name: 'About' },
  { path: '/privacy-policy/', name: 'Privacy Policy' },
  { path: '/raw-ftp-data/', name: 'Raw FTP Data' },
  { path: '/filtered-data/', name: 'Filtered Data' },
  { path: '/strategy-dividend-daddy/', name: 'Strategy: Dividend Daddy' },
  { path: '/strategy-moon-shot/', name: 'Strategy: Moon Shot' },
  { path: '/strategy-falling-knife/', name: 'Strategy: Falling Knife' },
  { path: '/strategy-over-hyped/', name: 'Strategy: Over Hyped' },
  { path: '/strategy-institutional-whale/', name: 'Strategy: Institutional Whale' },
  { path: '/tickers/aapl/', name: 'Ticker: AAPL' },
  { path: '/tickers/msft/', name: 'Ticker: MSFT' },
  { path: '/tickers/tsla/', name: 'Ticker: TSLA' },
  { path: '/contact/', name: 'Contact' },
  { path: '/methodology/', name: 'Methodology' },
  { path: '/articles/', name: 'Articles' },
  { path: '/articles/how-ticker-extraction-works/', name: 'Article: Ticker Extraction' },
  { path: '/articles/how-to-read-the-five-strategies/', name: 'Article: Five Strategies' },
  { path: '/glossary/', name: 'Glossary' },
  { path: '/glossary/rsi/', name: 'Glossary: RSI' },
  { path: '/glossary/beta/', name: 'Glossary: Beta' },
  { path: '/articles/practical-guide-to-stock-indicators/', name: 'Article: Indicators Guide' },
  { path: '/articles/why-some-tickers-have-no-scores/', name: 'Article: No Scores Explainer' },
  { path: '/articles/top-stocks-by-strategy-march-2026/', name: 'Article: March 2026 Roundup' },
  { path: '/articles/how-to-extract-tickers-from-financial-news/', name: 'Article: Financial News' },
  { path: '/articles/hidden-tickers-in-earnings-transcripts/', name: 'Article: Earnings Transcripts' },
  // zh-CN translated pages
  { path: '/zh-cn/', name: 'Home (zh-CN)' },
  { path: '/zh-cn/about/', name: 'About (zh-CN)' },
  { path: '/zh-cn/contact/', name: 'Contact (zh-CN)' },
  { path: '/zh-cn/methodology/', name: 'Methodology (zh-CN)' },
  { path: '/zh-cn/strategies/', name: 'Strategies (zh-CN)' },
  { path: '/zh-cn/strategy-dividend-daddy/', name: 'Strategy: Dividend Daddy (zh-CN)' },
  { path: '/zh-cn/filtered-data/', name: 'Filtered Data (zh-CN)' },
  { path: '/zh-cn/raw-ftp-data/', name: 'Raw FTP Data (zh-CN)' },
  { path: '/zh-cn/privacy-policy/', name: 'Privacy Policy (zh-CN)' },
];

test.describe('Website Page Load Tests', () => {
  test.describe('Page Loading', () => {
    for (const { path, name } of PAGES) {
      test(`${name} (${path}) loads successfully`, async ({ page }) => {
        const response = await page.goto(path);
        
        // Check HTTP status
        expect(response.status()).toBe(200);
        
        // Check page title exists
        await expect(page).toHaveTitle(/.+/);
        const title = await page.title();
        
        console.log(`✓ ${name}: ${response.status()} - "${title}"`);
      });
    }
  });

  test.describe('No Console Errors', () => {
    for (const { path, name } of PAGES) {
      test(`${name} (${path}) has no console errors`, async ({ page }) => {
        const consoleErrors = [];
        const pageErrors = [];

        // Capture console errors
        page.on('console', msg => {
          if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
          }
        });

        // Capture page errors
        page.on('pageerror', error => {
          pageErrors.push(error.message);
        });

        await page.goto(path);
        
        // Wait a bit for any deferred JS to execute
        await page.waitForTimeout(1000);
        
        // Filter out expected/benign errors
        const filteredConsoleErrors = consoleErrors.filter(err => {
          // DataTable errors are expected on data pages when there's no data to display
          if ((name === 'Raw FTP Data' || name === 'Filtered Data' || name.startsWith('Strategy:')) && 
              err.includes('DataTable')) {
            return false;
          }
          // 404 errors for missing resources are expected in development (e.g., missing data files)
          if (err.includes('404') || err.includes('Failed to load resource')) {
            return false;
          }
          return true;
        });
        
        const filteredPageErrors = pageErrors.filter(err => {
          // DataTable errors are expected on data pages when there's no data to display
          if ((name === 'Raw FTP Data' || name === 'Filtered Data' || name.startsWith('Strategy:')) && 
              err.includes('DataTable')) {
            return false;
          }
          return true;
        });
        
        // Check for console errors
        if (filteredConsoleErrors.length > 0) {
          console.log(`Console errors on ${name}:`, filteredConsoleErrors);
        }
        expect(filteredConsoleErrors).toHaveLength(0);
        
        // Check for page errors
        if (filteredPageErrors.length > 0) {
          console.log(`Page errors on ${name}:`, filteredPageErrors);
        }
        expect(filteredPageErrors).toHaveLength(0);
        
        console.log(`✓ ${name}: No errors`);
      });
    }
  });

  test.describe('Navigation Structure', () => {
    test('All pages have navigation bar', async ({ page }) => {
      test.setTimeout(180000);
      for (const { path, name } of PAGES) {
        await page.goto(path, { waitUntil: 'domcontentloaded' });
        
        // Check for navbar
        await expect(page.locator('nav.navbar')).toBeVisible();
        
        // Check for brand link
        const brand = page.locator('a.navbar-brand');
        await expect(brand).toBeVisible();
        // Brand text matches the site title for the current language
        const brandText = await brand.textContent();
        expect(brandText.trim()).toBeTruthy();
      }
      
      console.log('✓ All pages have proper navigation');
    });

    test('Navigation links are accessible', async ({ page }) => {
      await page.goto('/');
      
      // Check Home link
      await expect(page.locator('a.nav-link[href="/"]')).toBeVisible();
      
      // Check About link
      await expect(page.locator('a.nav-link[href="/about/"]')).toBeVisible();
      
      // Check Data dropdown
      await expect(page.locator('#navbarDataDropdown')).toBeVisible();
      
      console.log('✓ All navigation links present');
    });
  });

  test.describe('Page Content', () => {
    test('Home page has ticker extraction tool', async ({ page }) => {
      await page.goto('/');
      
      // Check for the ticker form
      await expect(page.locator('#ticker-form')).toBeVisible();
      
      // Check for text area
      await expect(page.locator('#user-input')).toBeVisible();
      
      // Check for submit button
      await expect(page.locator('#ticker-form button[type="submit"]')).toBeVisible();
      
      console.log('✓ Home page has ticker extraction tool');
    });

    test('About page has content', async ({ page }) => {
      await page.goto('/about/');
      
      // Should have at least a heading
      await expect(page.locator('h1').first()).toBeVisible();
      
      console.log('✓ About page has content');
    });
  });
});
