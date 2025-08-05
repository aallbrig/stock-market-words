const assert = require("assert");
const puppeteer = require("puppeteer");
const { assertNavigationBar } = require("./nav.spec.helper.js");
const { assertBootstrapCDNVersion } = require("./bootstrap.spec.helper.js");

const HEADLESS_MODE = process.env.HEADLESS_MODE || true;
const LANDING_PAGE = process.env.LANDING_PAGE || "http://localhost:8668";

describe("The landing page for English Dictionary Stocks website", () => {
  let browser;

  before(async () => {
    browser = await puppeteer.launch({
      headless: HEADLESS_MODE,
      args: ['--disable-dev-shm-usage']
    });
  });

  after(async () => {
    await browser.close();
  });

  it("Should have a 🔥 page title", async () => {
    const page = await browser.newPage();
    await page.goto(LANDING_PAGE);
    let title = await page.title();
    assert.equal(title, "English Dictionary Stocks");
  });

  it("Should summarize what the website is", async () => {
    const page = await browser.newPage();
    await page.goto(LANDING_PAGE);

    const projectSummarySection = await page.$('#project-summary-section');

    // If no HTML element is found, page.$ returns null
    assert.notEqual(projectSummarySection, null);
  });

  it("Have link to 'all' exchanges data", async () => {
    const page = await browser.newPage();
    await page.goto(LANDING_PAGE);

    const link = await page.$('#all-exchanges-data');

    // If no HTML element is found, page.$ returns null
    assert.notEqual(link, null);
  });

  it("should display the navigation bar with Home and About links", async () => {
    const page = await browser.newPage();
    await page.goto(LANDING_PAGE);
    await assertNavigationBar(page);
  });

  it("should submit the ticker form and show the result section", async () => {
    const page = await browser.newPage();
    await page.goto(LANDING_PAGE);
    await page.type('#user-input', 'AAPL TSLA are popular tickers');
    await page.click('button[type="submit"]');
    await page.waitForSelector('#result-section', { visible: true });
    const resultText = await page.$eval('#user-output', el => el.innerHTML);
    assert(resultText.includes('AAPL'));
    assert(resultText.includes('TSLA'));
  });

  it("should use the correct Bootstrap CDN version for CSS and JS", async () => {
    const page = await browser.newPage();
    await page.goto(LANDING_PAGE);
    await assertBootstrapCDNVersion(page, '5.3.0');
  });
});
