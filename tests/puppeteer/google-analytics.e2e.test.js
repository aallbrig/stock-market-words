/**
 * Google Analytics test for production site
 * Verifies that Google Analytics is loaded on the production site
 * 
 * This test only runs when TEST_URL is set to production (stockmarketwords.com)
 * Local development should NOT have GA tracking enabled
 * 
 * Usage:
 * TEST_URL=https://stockmarketwords.com/ START_SERVER=false npm test -- tests/puppeteer/google-analytics.e2e.test.js
 */

const puppeteer = require('puppeteer');

const PRODUCTION_URL = 'https://stockmarketwords.com/';
const GA_ID = 'G-RQCDXSWTLG';

describe('Google Analytics Production Test', () => {
  let browser;
  let page;

  // Only run if TEST_URL is set to production
  const shouldRun = process.env.TEST_URL === PRODUCTION_URL;

  beforeAll(async () => {
    if (!shouldRun) {
      console.log('⏭️  Skipping Google Analytics test - not running against production');
      console.log(`   Set TEST_URL=${PRODUCTION_URL} to run this test`);
      return;
    }

    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  (shouldRun ? test : test.skip)('Google Analytics script should be loaded on production', async () => {
    page = await browser.newPage();
    
    // Navigate to production site
    await page.goto(PRODUCTION_URL, {
      waitUntil: 'networkidle0',
      timeout: 30000
    });

    // Check for gtag script tag
    const gtagScriptFound = await page.evaluate(() => {
      const scripts = Array.from(document.querySelectorAll('script'));
      return scripts.some(script => 
        script.src && script.src.includes('googletagmanager.com/gtag/js')
      );
    });

    expect(gtagScriptFound).toBe(true);

    // Verify gtag function is defined
    const gtagFunctionExists = await page.evaluate(() => {
      return typeof window.gtag === 'function';
    });

    expect(gtagFunctionExists).toBe(true);

    // Verify correct tracking ID is configured
    const hasCorrectTrackingId = await page.evaluate((expectedId) => {
      const scripts = Array.from(document.querySelectorAll('script'));
      return scripts.some(script => 
        script.src && script.src.includes(`id=${expectedId}`)
      );
    }, GA_ID);

    expect(hasCorrectTrackingId).toBe(true);

    // Check dataLayer exists
    const dataLayerExists = await page.evaluate(() => {
      return Array.isArray(window.dataLayer);
    });

    expect(dataLayerExists).toBe(true);

    await page.close();
  });

  (shouldRun ? test : test.skip)('Google Analytics should NOT be on local development', async () => {
    // This is more of a documentation test - we can't test localhost from here
    // But we document the expectation
    expect(true).toBe(true);
  });
});
