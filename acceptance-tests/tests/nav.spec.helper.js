const assert = require("assert");

/**
 * Checks that the navigation bar is present and contains Home and About links.
 * @param {import('puppeteer').Page} page - Puppeteer page object
 */
async function assertNavigationBar(page) {
  const nav = await page.$('nav.navbar');
  assert.notEqual(nav, null, 'Navigation bar should exist');
  const homeLink = await page.$x("//a[contains(@class, 'nav-link') and text()='Home']");
  const aboutLink = await page.$x("//a[contains(@class, 'nav-link') and text()='About']");
  assert(homeLink.length > 0, 'Home link should exist');
  assert(aboutLink.length > 0, 'About link should exist');
}

module.exports = { assertNavigationBar };
