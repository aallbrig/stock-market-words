const assert = require("assert");
const puppeteer = require("puppeteer");

const HEADLESS_MODE = process.env.HEADLESS_MODE || false;
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
});