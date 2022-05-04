const assert = require("assert");
const puppeteer = require("puppeteer");

const HEADLESS_MODE = process.env.HEADLESS_MODE || true;
const EXCHANGE_DATA_PAGE = process.env.EXCHANGE_DATA_PAGE_BASE || "http://localhost:8668/exchange-data-display.html";

describe("The exchange data display page for English Dictionary Stocks website", () => {
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
    await page.goto(EXCHANGE_DATA_PAGE);
    let title = await page.title();
    assert.equal(title, "Exchange Data Display");
  });
});