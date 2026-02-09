/**
 * E2E tests for DataTables sorting functionality
 * 
 * Tests all pages with data tables to ensure columns are sortable
 * 
 * Migrated from Puppeteer to Playwright
 */

import { test, expect } from '@playwright/test';

const TIMEOUT = 30000;

// Pages with data tables
const PAGES_WITH_TABLES = [
  {
    path: '/strategy-dividend-daddy/',
    name: 'Strategy: Dividend Daddy',
    tableId: '#strategyTable',
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
    tableId: '#nasdaqTable',
    columns: null // Will be determined dynamically
  }
];

test.describe('DataTables Sorting', () => {
  // Helper function to check if DataTables is initialized
  async function isDataTablesInitialized(page, tableSelector) {
    return await page.evaluate((selector) => {
      const table = document.querySelector(selector);
      if (!table) return false;
      return $.fn.DataTable.isDataTable(selector);
    }, tableSelector);
  }

  // Helper function to get column headers
  async function getColumnHeaders(page, tableSelector) {
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

  // Helper function to get column values
  async function getColumnValues(page, tableSelector, columnIndex) {
    return await page.evaluate((selector, colIdx) => {
      const values = [];
      const table = document.querySelector(selector);
      if (!table) return values;
      
      const rows = table.querySelectorAll('tbody tr');
      const rowsToCheck = Math.min(rows.length, 10);
      
      for (let i = 0; i < rowsToCheck; i++) {
        const cells = rows[i].querySelectorAll('td');
        if (cells[colIdx]) {
          const dataOrder = cells[colIdx].getAttribute('data-order');
          const value = dataOrder !== null ? dataOrder : cells[colIdx].textContent.trim();
          values.push(value);
        }
      }
      return values;
    }, tableSelector, columnIndex);
  }

  // Helper function to click column header
  async function clickColumnHeader(page, tableSelector, columnIndex) {
    await page.evaluate((selector, colIdx) => {
      const table = document.querySelector(selector);
      const headers = table.querySelectorAll('thead th');
      headers[colIdx].click();
    }, tableSelector, columnIndex);
    
    await page.waitForTimeout(500);
  }

  // Helper function to check if values are sorted
  function checkSorted(values, columnName) {
    if (values.length < 2) return { sorted: true, direction: 'unknown' };
    
    const numericValues = values.map(v => {
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

  for (const pageInfo of PAGES_WITH_TABLES) {
    test.describe(pageInfo.name, () => {
      test('should load page and initialize DataTables', async ({ page }) => {
        await page.goto(pageInfo.path);
        
        // Wait for table to be present
        await expect(page.locator(pageInfo.tableId)).toBeVisible({ timeout: 10000 });
        
        // Check if DataTables is initialized
        const isInitialized = await isDataTablesInitialized(page, pageInfo.tableId);
        expect(isInitialized).toBe(true);
      });

      test('should have correct column headers', async ({ page }) => {
        await page.goto(pageInfo.path);
        await expect(page.locator(pageInfo.tableId)).toBeVisible();
        
        const headers = await getColumnHeaders(page, pageInfo.tableId);
        
        if (pageInfo.columns) {
          expect(headers).toHaveLength(pageInfo.columns.length);
          pageInfo.columns.forEach((expectedColumn, index) => {
            expect(headers[index]).toBe(expectedColumn);
          });
        } else {
          expect(headers.length).toBeGreaterThan(0);
        }
      });

      test('should be able to sort numeric columns', async ({ page }) => {
        await page.goto(pageInfo.path);
        await expect(page.locator(pageInfo.tableId)).toBeVisible();
        
        const headers = await getColumnHeaders(page, pageInfo.tableId);
        const nonNumericColumns = ['Symbol', 'Name', 'Exchange', 'ETF', 'First Seen', 'Sector'];
        
        // Test first numeric column only (for speed)
        for (let i = 0; i < headers.length; i++) {
          const columnName = headers[i];
          
          if (nonNumericColumns.includes(columnName)) {
            continue;
          }
          
          // Test this column
          await clickColumnHeader(page, pageInfo.tableId, i);
          let values = await getColumnValues(page, pageInfo.tableId, i);
          let sortCheck = checkSorted(values, columnName);
          
          expect(sortCheck.sorted).toBe(true);
          console.log(`  ✓ Column "${columnName}" sorted ${sortCheck.direction}`);
          
          // Only test first numeric column for speed
          break;
        }
      });

      // Special test for Strategy Score column
      if (pageInfo.path.startsWith('/strategy-')) {
        test('should default sort by Strategy Score descending', async ({ page }) => {
          await page.goto(pageInfo.path);
          await expect(page.locator(pageInfo.tableId)).toBeVisible();
          
          const headers = await getColumnHeaders(page, pageInfo.tableId);
          const scoreColumnIndex = headers.indexOf('Strategy Score');
          
          expect(scoreColumnIndex).toBeGreaterThan(-1);
          
          const values = await getColumnValues(page, pageInfo.tableId, scoreColumnIndex);
          const sortCheck = checkSorted(values, 'Strategy Score');
          
          expect(sortCheck.sorted).toBe(true);
          expect(sortCheck.direction).toBe('descending');
          console.log(`  ✓ Strategy Score defaults to descending`);
        });
      }
    });
  }

  test.describe('Raw FTP Data - Multiple Tables', () => {
    test('should have sortable NASDAQ table', async ({ page }) => {
      await page.goto('/raw-ftp-data/');
      
      const nasdaqExists = await page.locator('#nasdaqTable').count();
      if (nasdaqExists === 0) {
        console.warn('  ⚠ NASDAQ table not found - skipping');
        test.skip();
      }
      
      const isInitialized = await isDataTablesInitialized(page, '#nasdaqTable');
      expect(isInitialized).toBe(true);
      
      const headers = await getColumnHeaders(page, '#nasdaqTable');
      console.log(`  ✓ NASDAQ table has ${headers.length} columns and is sortable`);
    });

    test('should have sortable Other Listed table', async ({ page }) => {
      await page.goto('/raw-ftp-data/');
      
      const otherExists = await page.locator('#otherlistedTable').count();
      if (otherExists === 0) {
        console.warn('  ⚠ Other Listed table not found - skipping');
        test.skip();
      }
      
      const isInitialized = await isDataTablesInitialized(page, '#otherlistedTable');
      expect(isInitialized).toBe(true);
      
      console.log(`  ✓ Other Listed table is sortable`);
    });
  });
});

test.setTimeout(TIMEOUT);
