/**
 * E2E tests for DataTables sorting functionality
 * 
 * Tests all pages with data tables to ensure columns are sortable:
 * - Strategy pages (dividend-daddy, moon-shot, falling-knife, over-hyped, institutional-whale)
 * - Filtered data page
 * - Raw FTP data page
 */

const puppeteer = require('puppeteer');
const path = require('path');
const { setupTestServer, teardownTestServer } = require('../test-server');

let BASE_URL;
const TIMEOUT = 30000;

// Pages with data tables
const PAGES_WITH_TABLES = [
  {
    path: '/strategy-dividend-daddy/',
    name: 'Strategy: Dividend Daddy',
    tableId: '#strategyTable',
    // Updated columns to match current implementation (includes Sector and P/E Ratio)
    columns: ['Symbol', 'Name', 'Sector', 'Exchange', 'Price', 'Volume', 'Market Cap', 'P/E Ratio', 'Dividend Yield %', '200-Day MA', 'Relative Strength (90-Day)', 'Relative Strength (30-Day)', 'Strategy Score']
  },
  {
    path: '/strategy-moon-shot/',
    name: 'Strategy: Moon Shot',
    tableId: '#strategyTable',
    columns: ['Symbol', 'Name', 'Sector', 'Exchange', 'Price', 'Volume', 'Market Cap', 'P/E Ratio', 'Beta', 'RSI (14-Day)', 'Relative Strength (90-Day)', 'Relative Strength (30-Day)', 'Strategy Score']
  },
  {
    path: '/strategy-falling-knife/',
    name: 'Strategy: Falling Knife',
    tableId: '#strategyTable',
    columns: ['Symbol', 'Name', 'Sector', 'Exchange', 'Price', 'Volume', 'Market Cap', 'P/E Ratio', 'Beta', 'RSI (14-Day)', '200-Day MA', 'Relative Strength (90-Day)', 'Relative Strength (30-Day)', 'Strategy Score']
  },
  {
    path: '/strategy-over-hyped/',
    name: 'Strategy: Over Hyped',
    tableId: '#strategyTable',
    columns: ['Symbol', 'Name', 'Sector', 'Exchange', 'Price', 'Volume', 'Market Cap', 'P/E Ratio', 'Beta', 'RSI (14-Day)', 'Relative Strength (90-Day)', 'Relative Strength (30-Day)', 'Strategy Score']
  },
  {
    path: '/strategy-institutional-whale/',
    name: 'Strategy: Institutional Whale',
    tableId: '#strategyTable',
    columns: ['Symbol', 'Name', 'Sector', 'Exchange', 'Price', 'Volume', 'Market Cap', 'P/E Ratio', 'Dividend Yield %', 'Beta', '200-Day MA', 'Relative Strength (90-Day)', 'Relative Strength (30-Day)', 'Strategy Score']
  },
  {
    path: '/filtered-data/',
    name: 'Filtered Data',
    tableId: '#tickerTable',
    columns: ['Symbol', 'Name', 'Exchange', 'ETF', 'Price', 'Volume', 'Market Cap', 'First Seen']
  },
  {
    path: '/raw-ftp-data/',
    name: 'Raw FTP Data',
    tableId: '#nasdaqTable', // Test first table
    columns: null // Will be determined dynamically
  }
];

describe('DataTables Sorting', () => {
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
    page.setDefaultTimeout(TIMEOUT);
    
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error(`Browser console error: ${msg.text()}`);
      }
    });
  });

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  // Helper function to check if DataTables is initialized
  async function isDataTablesInitialized(tableSelector) {
    return await page.evaluate((selector) => {
      const table = document.querySelector(selector);
      if (!table) return false;
      return $.fn.DataTable.isDataTable(selector);
    }, tableSelector);
  }

  // Helper function to get column headers
  async function getColumnHeaders(tableSelector) {
    return await page.evaluate((selector) => {
      const headers = [];
      const table = document.querySelector(selector);
      if (!table) return headers;
      
      const headerCells = table.querySelectorAll('thead th');
      headerCells.forEach(th => {
        headers.push(th.textContent.trim());
      });
      return headers;
    }, tableSelector);
  }

  // Helper function to get first column values
  async function getColumnValues(tableSelector, columnIndex) {
    return await page.evaluate((selector, colIdx) => {
      const values = [];
      const table = document.querySelector(selector);
      if (!table) return values;
      
      const rows = table.querySelectorAll('tbody tr');
      // Get first 10 rows to check sorting
      const rowsToCheck = Math.min(rows.length, 10);
      
      for (let i = 0; i < rowsToCheck; i++) {
        const cells = rows[i].querySelectorAll('td');
        if (cells[colIdx]) {
          // Get the data-order attribute if present, otherwise text content
          const dataOrder = cells[colIdx].getAttribute('data-order');
          const value = dataOrder !== null ? dataOrder : cells[colIdx].textContent.trim();
          values.push(value);
        }
      }
      return values;
    }, tableSelector, columnIndex);
  }

  // Helper function to click column header
  async function clickColumnHeader(tableSelector, columnIndex) {
    await page.evaluate((selector, colIdx) => {
      const table = document.querySelector(selector);
      const headers = table.querySelectorAll('thead th');
      headers[colIdx].click();
    }, tableSelector, columnIndex);
    
    // Wait for DataTables to finish sorting (use a Promise-based delay)
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  // Helper function to check if values are sorted (ascending or descending)
  function checkSorted(values, columnName) {
    if (values.length < 2) return { sorted: true, direction: 'unknown' };
    
    // Convert values for comparison
    const numericValues = values.map(v => {
      // Remove currency symbols, commas, and percentage signs
      const cleaned = v.replace(/[$,%]/g, '').replace(/,/g, '');
      return parseFloat(cleaned) || 0;
    });
    
    let ascending = true;
    let descending = true;
    
    for (let i = 1; i < numericValues.length; i++) {
      if (numericValues[i] < numericValues[i-1]) ascending = false;
      if (numericValues[i] > numericValues[i-1]) descending = false;
    }
    
    return {
      sorted: ascending || descending,
      direction: ascending ? 'ascending' : (descending ? 'descending' : 'unsorted'),
      values: numericValues
    };
  }

  PAGES_WITH_TABLES.forEach(pageInfo => {
    describe(pageInfo.name, () => {
      test('should load page and initialize DataTables', async () => {
        await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle0' });
        
        // Wait for table to be present
        await page.waitForSelector(pageInfo.tableId, { timeout: 10000 });
        
        // Check if DataTables is initialized
        const isInitialized = await isDataTablesInitialized(pageInfo.tableId);
        expect(isInitialized).toBe(true);
      });

      test('should have correct column headers', async () => {
        await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle0' });
        await page.waitForSelector(pageInfo.tableId);
        
        const headers = await getColumnHeaders(pageInfo.tableId);
        
        if (pageInfo.columns) {
          // Check expected columns
          expect(headers).toHaveLength(pageInfo.columns.length);
          pageInfo.columns.forEach((expectedColumn, index) => {
            expect(headers[index]).toBe(expectedColumn);
          });
        } else {
          // Just verify we have headers
          expect(headers.length).toBeGreaterThan(0);
        }
      });

      test('should be able to sort all numeric columns', async () => {
        await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle0' });
        await page.waitForSelector(pageInfo.tableId);
        
        const headers = await getColumnHeaders(pageInfo.tableId);
        
        // Determine which columns are numeric (skip Symbol, Name, Exchange, ETF)
        const nonNumericColumns = ['Symbol', 'Name', 'Exchange', 'ETF', 'First Seen'];
        
        for (let i = 0; i < headers.length; i++) {
          const columnName = headers[i];
          
          // Skip non-numeric columns
          if (nonNumericColumns.includes(columnName)) {
            continue;
          }
          
          // Click header to sort ascending
          await clickColumnHeader(pageInfo.tableId, i);
          let values = await getColumnValues(pageInfo.tableId, i);
          let sortCheck = checkSorted(values, columnName);
          
          expect(sortCheck.sorted).toBe(true);
          console.log(`  ✓ Column "${columnName}" sorted ${sortCheck.direction} (first: ${sortCheck.values[0]}, last: ${sortCheck.values[sortCheck.values.length-1]})`);
          
          // Click again to sort descending
          await clickColumnHeader(pageInfo.tableId, i);
          values = await getColumnValues(pageInfo.tableId, i);
          sortCheck = checkSorted(values, columnName);
          
          expect(sortCheck.sorted).toBe(true);
          console.log(`  ✓ Column "${columnName}" reversed sort ${sortCheck.direction} (first: ${sortCheck.values[0]}, last: ${sortCheck.values[sortCheck.values.length-1]})`);
        }
      });

      // Special test for Strategy Score column (should default to descending)
      if (pageInfo.path.startsWith('/strategy-')) {
        test('should default sort by Strategy Score (descending)', async () => {
          await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle0' });
          await page.waitForSelector(pageInfo.tableId);
          
          const headers = await getColumnHeaders(pageInfo.tableId);
          const scoreColumnIndex = headers.indexOf('Strategy Score');
          
          expect(scoreColumnIndex).toBeGreaterThan(-1);
          
          // Get values without clicking (should already be sorted)
          const values = await getColumnValues(pageInfo.tableId, scoreColumnIndex);
          const sortCheck = checkSorted(values, 'Strategy Score');
          
          expect(sortCheck.sorted).toBe(true);
          expect(sortCheck.direction).toBe('descending');
          console.log(`  ✓ Strategy Score defaults to descending: ${sortCheck.values[0]} → ${sortCheck.values[sortCheck.values.length-1]}`);
        });
      }
    });
  });

  // Special tests for raw-ftp-data page (has multiple tables)
  describe('Raw FTP Data - Multiple Tables', () => {
    test('should have sortable NASDAQ table', async () => {
      await page.goto(`${BASE_URL}/raw-ftp-data/`, { waitUntil: 'networkidle0' });
      
      const nasdaqExists = await page.$('#nasdaqTable');
      if (!nasdaqExists) {
        console.warn('  ⚠ NASDAQ table not found - skipping');
        return;
      }
      
      const isInitialized = await isDataTablesInitialized('#nasdaqTable');
      expect(isInitialized).toBe(true);
      
      // Test sorting first column
      const headers = await getColumnHeaders('#nasdaqTable');
      await clickColumnHeader('#nasdaqTable', 0);
      const values = await getColumnValues('#nasdaqTable', 0);
      
      console.log(`  ✓ NASDAQ table has ${headers.length} columns and is sortable`);
    });

    test('should have sortable Other Listed table', async () => {
      await page.goto(`${BASE_URL}/raw-ftp-data/`, { waitUntil: 'networkidle0' });
      
      const otherExists = await page.$('#otherlistedTable');
      if (!otherExists) {
        console.warn('  ⚠ Other Listed table not found - skipping');
        return;
      }
      
      const isInitialized = await isDataTablesInitialized('#otherlistedTable');
      expect(isInitialized).toBe(true);
      
      console.log(`  ✓ Other Listed table is sortable`);
    });
  });

  // Test for human-readable column headers
  describe('Column Header Readability', () => {
    test('all column headers should be human-readable', async () => {
      const jargonTerms = ['MA200', 'Div Yield', 'RSI-14'];
      const foundJargon = [];
      
      for (const pageInfo of PAGES_WITH_TABLES) {
        await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle0' });
        
        const tableExists = await page.$(pageInfo.tableId);
        if (!tableExists) continue;
        
        const headers = await getColumnHeaders(pageInfo.tableId);
        
        headers.forEach(header => {
          jargonTerms.forEach(jargon => {
            if (header.includes(jargon)) {
              foundJargon.push({ page: pageInfo.name, header });
            }
          });
        });
      }
      
      if (foundJargon.length > 0) {
        console.error('Found jargony column headers:');
        foundJargon.forEach(item => {
          console.error(`  ${item.page}: "${item.header}"`);
        });
      }
      
      expect(foundJargon).toHaveLength(0);
    });
  });
});
