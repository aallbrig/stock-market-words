/**
 * Test for portfolio table pagination and strategy links
 * 
 * Issues to fix:
 * 1. Tables with >10 tickers should show only 10 rows initially (not require clicking "Next")
 * 2. Each portfolio card should have a link to the strategy page
 */

const puppeteer = require('puppeteer');
const { setupTestServer, teardownTestServer } = require('../test-server');

let BASE_URL;

const LONG_TEXT = `The tech industry saw major changes this year. Companies like Apple and Dell released new products while Oracle expanded their cloud services. Meanwhile analysts noted how British American Tobacco continued its dominance in Asian markets.

In the automotive sector Ford announced electric vehicle plans and General Motors followed suit. Uber and Doordash both reported strong quarterly earnings. The ride sharing wars continue with Grab making moves in Southeast Asia.

Retail giants Costco and Target adapted to changing consumer habits. Lowes improved their home improvement offerings while Home Depot focused on professional contractors. The fast food industry saw consolidation with Jack in the Box and Sonic exploring merger possibilities.`;

describe('Portfolio Table Pagination and Strategy Links', () => {
  let browser;
  let page;

  beforeAll(async () => {
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
    await teardownTestServer();
  });

  beforeEach(async () => {
    page = await browser.newPage();
    
    // Capture console messages for debugging
    page.on('console', msg => {
      const type = msg.type();
      if (type === 'error' || type === 'warning') {
        console.log(`Browser ${type}:`, msg.text());
      }
    });
    
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
  });

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  test('Tables with >10 tickers should show only first 10 rows initially', async () => {
    // Fill in the long text using the fill example function (like the UI does)
    await page.evaluate((text) => {
      document.getElementById('user-input').value = text;
    }, LONG_TEXT);
    
    // Submit the form
    await page.click('#ticker-form button[type="submit"]');
    
    // Wait for result card to appear (data loads on first submit)
    await page.waitForSelector('#result-card', { visible: true, timeout: 60000 });

    // Debug: Check what's in the result card
    const portfolioContent = await page.$eval('#portfolio-strategies', el => el.innerHTML);
    if (portfolioContent.includes('alert-danger') || portfolioContent.includes('alert-warning')) {
      console.log('ERROR/WARNING in result:', portfolioContent.substring(0, 500));
    }

    // Wait for tables to render
    await page.waitForFunction(() => {
      const tables = document.querySelectorAll('table[id^="table-"]');
      return tables.length > 0;
    }, { timeout: 10000 });

    // Check each table
    const tables = await page.$$('table[id^="table-"]');
    
    let foundTableWithPagination = false;
    
    for (const table of tables) {
      const tableId = await table.evaluate(el => el.id);
      console.log(`Checking table: ${tableId}`);
      
      // Count total rows
      const totalRows = await table.$$eval('tbody tr', rows => rows.length);
      
      if (totalRows > 10) {
        foundTableWithPagination = true;
        console.log(`  Table has ${totalRows} rows (>10), checking pagination...`);
        
        // Count visible rows INITIALLY (before any interaction)
        const visibleRows = await table.$$eval('tbody tr', rows => 
          rows.filter(row => row.style.display !== 'none').length
        );
        
        console.log(`  Visible rows initially: ${visibleRows}`);
        
        // EXPECTATION: Should show exactly 10 rows initially
        expect(visibleRows).toBe(10);
        
        // Verify pagination controls exist
        const hasPagination = await page.$(`div.pagination-controls[data-table="${tableId}"]`);
        expect(hasPagination).not.toBeNull();
      }
    }
    
    // Ensure we actually tested pagination
    if (!foundTableWithPagination) {
      console.warn('Warning: No tables with >10 rows found. Test may need different input text.');
    }
  }, 90000);

  test('Each portfolio card should have a link to the strategy page', async () => {
    // Fill in the long text
    await page.evaluate((text) => {
      document.getElementById('user-input').value = text;
    }, LONG_TEXT);
    
    // Submit the form
    await page.click('#ticker-form button[type="submit"]');
    
    // Wait for result card to appear
    await page.waitForSelector('#result-card', { visible: true, timeout: 60000 });

    // Wait for portfolio cards to render
    await page.waitForSelector('.card.mb-4', { timeout: 10000 });

    // Get all portfolio cards
    const cards = await page.$$('.card.mb-4');
    
    expect(cards.length).toBeGreaterThan(0);
    console.log(`Found ${cards.length} portfolio cards`);

    // Check each card has a strategy link in the header
    for (const card of cards) {
      const strategyLink = await card.$('.card-header a[href^="/strategy-"]');
      
      if (!strategyLink) {
        const cardHtml = await card.evaluate(el => el.outerHTML);
        console.log('Card without strategy link:', cardHtml.substring(0, 500));
      }
      
      // EXPECTATION: Each card should have a link to the strategy page
      expect(strategyLink).not.toBeNull();
      
      if (strategyLink) {
        const href = await strategyLink.evaluate(el => el.getAttribute('href'));
        console.log(`Found strategy link: ${href}`);
        
        // Verify it matches the pattern /strategy-{name}/
        expect(href).toMatch(/^\/strategy-[a-z-]+\/$/);
      }
    }
  }, 90000);

  test('Pagination buttons work correctly', async () => {
    // Fill in the long text
    await page.evaluate((text) => {
      document.getElementById('user-input').value = text;
    }, LONG_TEXT);
    
    // Submit the form
    await page.click('#ticker-form button[type="submit"]');
    
    // Wait for results
    await page.waitForSelector('#result-card', { visible: true, timeout: 60000 });

    // Find a table with pagination
    const paginationControl = await page.$('div.pagination-controls');
    
    if (paginationControl) {
      const tableId = await paginationControl.evaluate(el => el.getAttribute('data-table'));
      const table = await page.$(`#${tableId}`);
      
      // Get initial visible rows
      const initialVisible = await table.$$eval('tbody tr', rows => 
        rows.filter(row => row.style.display !== 'none').length
      );
      
      console.log(`Initial visible rows: ${initialVisible}`);
      expect(initialVisible).toBe(10);
      
      // Click "Next" button
      const nextButton = await paginationControl.$('button:last-child');
      await nextButton.click();
      
      // Wait a bit for the display to update
      await page.waitForTimeout(500);
      
      // Check that different rows are visible
      const afterNextVisible = await table.$$eval('tbody tr', rows => 
        rows.filter(row => row.style.display !== 'none').length
      );
      
      console.log(`After clicking Next, visible rows: ${afterNextVisible}`);
      expect(afterNextVisible).toBeGreaterThan(0);
      expect(afterNextVisible).toBeLessThanOrEqual(10);
    } else {
      console.log('No pagination controls found (all tables have <=10 rows)');
    }
  }, 90000);
});
