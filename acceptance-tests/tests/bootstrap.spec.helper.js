const assert = require("assert");

/**
 * Checks that the page is using the expected Bootstrap CDN version for CSS and JS.
 * @param {import('puppeteer').Page} page - Puppeteer page object
 * @param {string} expectedVersion - The expected Bootstrap version (e.g., '5.3.0')
 */
async function assertBootstrapCDNVersion(page, expectedVersion = '5.3.0') {
  // Check CSS
  const cssLinks = await page.$$eval('link[rel="stylesheet"]', links => links.map(l => l.href));
  const cssMatch = cssLinks.some(href => href.includes(`bootstrap@${expectedVersion}`));
  assert(cssMatch, `Bootstrap CSS version ${expectedVersion} not found in page links: ${cssLinks}`);

  // Check JS
  const jsScripts = await page.$$eval('script[src]', scripts => scripts.map(s => s.src));
  const jsMatch = jsScripts.some(src => src.includes(`bootstrap@${expectedVersion}`));
  assert(jsMatch, `Bootstrap JS version ${expectedVersion} not found in page scripts: ${jsScripts}`);
}

module.exports = { assertBootstrapCDNVersion };
