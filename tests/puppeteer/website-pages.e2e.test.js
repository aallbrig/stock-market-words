/**
 * Basic page load tests for all website pages
 * Ensures all pages load successfully with no console errors
 * 
 * Environment variables:
 * - TEST_URL: Override base URL (e.g., https://stockmarketwords.com/)
 * - START_SERVER: Set to 'false' to skip server startup (default: true)
 * - SERVER_PORT: Port for local server (default: 8668)
 */

const puppeteer = require('puppeteer');
const { setupTestServer, teardownTestServer } = require('../test-server');

let BASE_URL;

// All pages on the website
const PAGES = [
  { path: '/', name: 'Home' },
  { path: '/about/', name: 'About' },
  { path: '/raw-ftp-data/', name: 'Raw FTP Data' },
  { path: '/filtered-data/', name: 'Filtered Data' },
  { path: '/strategy-dividend-daddy/', name: 'Strategy: Dividend Daddy' },
  { path: '/strategy-moon-shot/', name: 'Strategy: Moon Shot' },
  { path: '/strategy-falling-knife/', name: 'Strategy: Falling Knife' },
  { path: '/strategy-over-hyped/', name: 'Strategy: Over Hyped' },
  { path: '/strategy-institutional-whale/', name: 'Strategy: Institutional Whale' }
];

describe('Website Page Load Tests', () => {
  let browser;
  let page;
  let consoleErrors = [];
  let pageErrors = [];

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
    consoleErrors = [];
    pageErrors = [];

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
  });

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  describe('Page Loading', () => {
    PAGES.forEach(({ path, name }) => {
      test(`${name} (${path}) loads successfully`, async () => {
        const response = await page.goto(BASE_URL + path, { 
          waitUntil: 'networkidle2',
          timeout: 30000 
        });
        
        // Check HTTP status
        expect(response.status()).toBe(200);
        
        // Check page title exists
        const title = await page.title();
        expect(title).toBeTruthy();
        expect(title.length).toBeGreaterThan(0);
        
        console.log(`✓ ${name}: ${response.status()} - "${title}"`);
      });
    });
  });

  describe('No Console Errors', () => {
    PAGES.forEach(({ path, name }) => {
      test(`${name} (${path}) has no console errors`, async () => {
        await page.goto(BASE_URL + path, { 
          waitUntil: 'networkidle2',
          timeout: 30000 
        });
        
        // Wait a bit for any deferred JS to execute
        await new Promise(resolve => setTimeout(resolve, 1000));
        
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
    });
  });

  describe('Navigation Structure', () => {
    test('All pages have navigation bar', async () => {
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        const navbar = await page.$('nav.navbar');
        expect(navbar).toBeTruthy();
        
        // Check for brand link
        const brand = await page.$('a.navbar-brand');
        expect(brand).toBeTruthy();
        
        const brandText = await page.$eval('a.navbar-brand', el => el.textContent);
        expect(brandText).toBe('Stock Market Words');
      }
      
      console.log('✓ All pages have proper navigation');
    });

    test('Navigation links are accessible', async () => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
      
      // Check Home link
      const homeLink = await page.$('a.nav-link[href="/"]');
      expect(homeLink).toBeTruthy();
      
      // Check About link
      const aboutLink = await page.$('a.nav-link[href="/about/"]');
      expect(aboutLink).toBeTruthy();
      
      // Check Data dropdown
      const dataDropdown = await page.$('#navbarDataDropdown');
      expect(dataDropdown).toBeTruthy();
      
      console.log('✓ All navigation links present');
    });
  });

  describe('Page Content', () => {
    test('Home page has ticker extraction tool', async () => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
      
      // Check for the ticker form
      const tickerForm = await page.$('#ticker-form');
      expect(tickerForm).toBeTruthy();
      
      // Check for text area
      const textarea = await page.$('#user-input');
      expect(textarea).toBeTruthy();
      
      // Check for sample buttons
      const sampleButtons = await page.$$('.btn-outline-secondary');
      expect(sampleButtons.length).toBeGreaterThanOrEqual(3);
      
      console.log('✓ Home page has ticker extraction tool');
    });

    test('About page has content', async () => {
      await page.goto(BASE_URL + '/about/', { waitUntil: 'networkidle2' });
      
      // Check that main content exists
      const mainContent = await page.$('main');
      expect(mainContent).toBeTruthy();
      
      const contentText = await page.$eval('main', el => el.textContent);
      expect(contentText.length).toBeGreaterThan(50);
      
      console.log('✓ About page has content');
    });

    test('Raw FTP Data page loads', async () => {
      await page.goto(BASE_URL + '/raw-ftp-data/', { waitUntil: 'networkidle2' });
      
      const mainContent = await page.$('main');
      expect(mainContent).toBeTruthy();
      
      console.log('✓ Raw FTP Data page loads');
    });

    test('Filtered Data page loads', async () => {
      await page.goto(BASE_URL + '/filtered-data/', { waitUntil: 'networkidle2' });
      
      const mainContent = await page.$('main');
      expect(mainContent).toBeTruthy();
      
      console.log('✓ Filtered Data page loads');
    });
  });

  describe('Asset Loading', () => {
    test('All pages load CSS successfully', async () => {
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        // Check if Bootstrap CSS is loaded
        const stylesheets = await page.$$eval('link[rel="stylesheet"]', links => 
          links.map(link => link.href)
        );
        
        expect(stylesheets.length).toBeGreaterThan(0);
        
        // Check if at least one stylesheet is Bootstrap
        const hasBootstrap = stylesheets.some(href => 
          href.includes('bootstrap') || href.includes('bootswatch')
        );
        expect(hasBootstrap).toBe(true);
      }
      
      console.log('✓ All pages load CSS successfully');
    });

    test('Home page loads JavaScript files', async () => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
      
      // Check if scripts are loaded
      const scripts = await page.$$eval('script[src]', scripts => 
        scripts.map(script => script.src)
      );
      
      expect(scripts.length).toBeGreaterThan(0);
      
      // Check for Bootstrap JS
      const hasBootstrapJS = scripts.some(src => src.includes('bootstrap'));
      expect(hasBootstrapJS).toBe(true);
      
      console.log('✓ Home page loads JavaScript files');
    });
  });

  describe('Responsive Design', () => {
    test('Pages render correctly on mobile viewport', async () => {
      await page.setViewport({ width: 375, height: 667 }); // iPhone SE
      
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        // Check that navbar exists
        const navbar = await page.$('nav.navbar');
        expect(navbar).toBeTruthy();
        
        // Check for hamburger menu button
        const hamburger = await page.$('.navbar-toggler');
        expect(hamburger).toBeTruthy();
      }
      
      console.log('✓ All pages render on mobile viewport');
    });

    test('Pages render correctly on desktop viewport', async () => {
      await page.setViewport({ width: 1920, height: 1080 });
      
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        const navbar = await page.$('nav.navbar');
        expect(navbar).toBeTruthy();
      }
      
      console.log('✓ All pages render on desktop viewport');
    });
  });

  describe('SEO and Meta Tags', () => {
    test('All pages have proper meta tags', async () => {
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        // Check viewport meta tag
        const viewport = await page.$('meta[name="viewport"]');
        expect(viewport).toBeTruthy();
        
        // Check charset
        const charset = await page.$('meta[charset]');
        expect(charset).toBeTruthy();
      }
      
      console.log('✓ All pages have proper meta tags');
    });

    test('All pages have titles', async () => {
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        const title = await page.title();
        expect(title).toBeTruthy();
        expect(title.length).toBeGreaterThan(0);
        expect(title).not.toBe('');
        
        console.log(`  ${name}: "${title}"`);
      }
    });
  });

  describe('Accessibility', () => {
    test('Pages have proper heading structure', async () => {
      for (const { path, name } of PAGES) {
        await page.goto(BASE_URL + path, { waitUntil: 'networkidle2' });
        
        // Check for headings
        const headings = await page.$$('h1, h2, h3, h4, h5, h6');
        expect(headings.length).toBeGreaterThan(0);
      }
      
      console.log('✓ All pages have heading structure');
    });

    test('Navigation links have accessible text', async () => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
      
      const navLinks = await page.$$eval('nav a', links => 
        links.map(link => ({
          text: link.textContent.trim(),
          href: link.href
        }))
      );
      
      // All nav links should have text
      navLinks.forEach(link => {
        expect(link.text.length).toBeGreaterThan(0);
      });
      
      console.log('✓ Navigation links have accessible text');
    });
  });

  describe('Performance', () => {
    test('Pages load within reasonable time', async () => {
      for (const { path, name } of PAGES) {
        const startTime = Date.now();
        
        await page.goto(BASE_URL + path, { 
          waitUntil: 'networkidle2',
          timeout: 30000 
        });
        
        const loadTime = Date.now() - startTime;
        
        // Page should load within 10 seconds
        expect(loadTime).toBeLessThan(10000);
        
        console.log(`  ${name}: ${loadTime}ms`);
      }
    });
  });
});
