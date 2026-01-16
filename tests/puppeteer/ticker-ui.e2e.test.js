/**
 * End-to-end performance test for TickerEngine UI
 * Tests the extraction tool on the main page with all three sample texts
 * 
 * TIMEOUT CONFIGURATION:
 * - Local development: 60 seconds (default)
 * - CI/CD: 10 seconds (set via TIMEOUT_SECONDS=10)
 * 
 * Environment variables:
 * - TEST_URL: Override base URL (e.g., https://aallbrig.github.io/stock-market-words/)
 * - START_SERVER: Set to 'false' to skip server startup (default: true)
 * - SERVER_PORT: Port for local server (default: 8668)
 * - TIMEOUT_SECONDS: Max processing time in seconds (default: 60)
 * 
 * Usage:
 *   npm run test:e2e:ticker          # Local: 60s timeout
 *   TIMEOUT_SECONDS=10 npm run ...   # CI: 10s timeout
 *   TEST_URL=https://... npm run ... # Test against remote
 */

const puppeteer = require('puppeteer');
const { setupTestServer, teardownTestServer } = require('../test-server');

let BASE_URL;
// CI uses 10 seconds, local dev uses 60 seconds
const MAX_PROCESSING_TIME_MS = process.env.TIMEOUT_SECONDS 
  ? parseInt(process.env.TIMEOUT_SECONDS) * 1000 
  : 60000;

console.log(`TickerEngine E2E Tests - Max processing time: ${MAX_PROCESSING_TIME_MS / 1000}s`);

describe('TickerEngine E2E Performance Tests', () => {
  let browser;
  let page;

  beforeAll(async () => {
    // Start test server (or verify external server)
    BASE_URL = await setupTestServer();
    console.log(`Running tests against: ${BASE_URL}`);
    
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
    
    // Stop test server
    await teardownTestServer();
  });

  beforeEach(async () => {
    page = await browser.newPage();
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
  });

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  /**
   * Helper function to test a sample text
   */
  async function testSampleText(sampleIndex, sampleName) {
    // Wait for the form to be visible
    await page.waitForSelector('#ticker-form', { timeout: 10000 });
    
    // Click the sample text button (0-indexed)
    const sampleButtons = await page.$$('.btn-outline-secondary');
    expect(sampleButtons.length).toBeGreaterThanOrEqual(3);
    
    await sampleButtons[sampleIndex].click();
    
    // Wait a bit for text to populate using a promise-based timeout
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Verify text area has content
    const textareaValue = await page.$eval('#user-input', el => el.value);
    expect(textareaValue.length).toBeGreaterThan(0);
    
    console.log(`${sampleName}: Text populated (${textareaValue.length} chars)`);
    
    // Record start time
    const startTime = Date.now();
    
    // Click the Extract Portfolios button
    await page.click('#ticker-form button[type="submit"]');
    
    // Wait for loading indicator to appear
    await page.waitForSelector('#loading-indicator', { visible: true, timeout: 5000 });
    console.log(`${sampleName}: Processing started...`);
    
    // Wait for result card to appear (this means processing is complete)
    await page.waitForSelector('#result-card', { 
      visible: true, 
      timeout: MAX_PROCESSING_TIME_MS 
    });
    
    // Calculate processing time
    const processingTime = Date.now() - startTime;
    console.log(`${sampleName}: Processing completed in ${processingTime}ms`);
    
    // Verify loading indicator is hidden
    const loadingHidden = await page.$eval('#loading-indicator', 
      el => el.style.display === 'none'
    );
    expect(loadingHidden).toBe(true);
    
    // Verify results are displayed
    const resultsVisible = await page.$eval('#result-card', 
      el => el.style.display !== 'none'
    );
    expect(resultsVisible).toBe(true);
    
    // Verify portfolio strategies are rendered
    const portfolioStrategies = await page.$('#portfolio-strategies');
    expect(portfolioStrategies).toBeTruthy();
    
    const strategiesContent = await page.$eval('#portfolio-strategies', 
      el => el.innerHTML
    );
    expect(strategiesContent.length).toBeGreaterThan(0);
    
    // Assert processing time is under 60 seconds
    expect(processingTime).toBeLessThan(MAX_PROCESSING_TIME_MS);
    
    return processingTime;
  }

  test('Sample 1: SHORT text completes within 60 seconds', async () => {
    const time = await testSampleText(0, 'SHORT');
    console.log(`✓ SHORT sample completed in ${time}ms`);
  }, MAX_PROCESSING_TIME_MS + 15000); // Extra time for page load

  test('Sample 2: MEDIUM text completes within 60 seconds', async () => {
    const time = await testSampleText(1, 'MEDIUM');
    console.log(`✓ MEDIUM sample completed in ${time}ms`);
  }, MAX_PROCESSING_TIME_MS + 15000);

  test('Sample 3: LONG text completes within 60 seconds', async () => {
    const time = await testSampleText(2, 'LONG');
    console.log(`✓ LONG sample completed in ${time}ms`);
  }, MAX_PROCESSING_TIME_MS + 15000);

  describe('UI Validation', () => {
    test('Page loads with all required elements', async () => {
      // Check for ticker form
      const form = await page.$('#ticker-form');
      expect(form).toBeTruthy();
      
      // Check for text area
      const textarea = await page.$('#user-input');
      expect(textarea).toBeTruthy();
      
      // Check for submit button
      const submitButton = await page.$('#ticker-form button[type="submit"]');
      expect(submitButton).toBeTruthy();
      
      // Check for all three sample buttons
      const sampleButtons = await page.$$('.btn-outline-secondary');
      expect(sampleButtons.length).toBeGreaterThanOrEqual(3);
      
      console.log('✓ All UI elements present');
    });

    test('Sample buttons populate text area', async () => {
      // Test first sample button
      const sampleButtons = await page.$$('.btn-outline-secondary');
      await sampleButtons[0].click();
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const textareaValue = await page.$eval('#user-input', el => el.value);
      expect(textareaValue.length).toBeGreaterThan(0);
      expect(textareaValue).toContain('cat');
      
      console.log('✓ Sample buttons work correctly');
    });
  });

  describe('Performance Monitoring', () => {
    test('Benchmark all three samples and report statistics', async () => {
      const results = [];
      
      for (let i = 0; i < 3; i++) {
        const sampleNames = ['SHORT', 'MEDIUM', 'LONG'];
        
        // Reload page for fresh state
        await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
        
        const time = await testSampleText(i, sampleNames[i]);
        results.push({ name: sampleNames[i], time });
      }
      
      console.log('\n=== E2E Performance Summary ===');
      results.forEach(r => {
        console.log(`  ${r.name.padEnd(8)}: ${r.time}ms`);
      });
      
      const totalTime = results.reduce((sum, r) => sum + r.time, 0);
      const avgTime = totalTime / results.length;
      const maxTime = Math.max(...results.map(r => r.time));
      
      console.log(`  Average  : ${avgTime.toFixed(2)}ms`);
      console.log(`  Max      : ${maxTime}ms`);
      console.log('================================\n');
      
      // All should be under 60 seconds
      results.forEach(r => {
        expect(r.time).toBeLessThan(MAX_PROCESSING_TIME_MS);
      });
    }, (MAX_PROCESSING_TIME_MS + 15000) * 3); // Time for all 3 samples
  });

  describe('Error Handling', () => {
    test('Empty text area shows appropriate message', async () => {
      // Listen for alert dialog
      let dialogMessage = '';
      page.on('dialog', async dialog => {
        dialogMessage = dialog.message();
        await dialog.accept();
      });
      
      // Submit without selecting a sample
      await page.click('#ticker-form button[type="submit"]');
      
      // Wait for dialog to be handled
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Check if alert was shown
      expect(dialogMessage.toLowerCase()).toContain('text');
      
      console.log('✓ Empty input validation works');
    }, 15000);
  });
});
