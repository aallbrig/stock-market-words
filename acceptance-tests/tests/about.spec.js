const assert = require("assert");
const puppeteer = require("puppeteer");
const { assertNavigationBar } = require("./nav.spec.helper.js");
const { assertBootstrapCDNVersion } = require("./bootstrap.spec.helper.js");

const HEADLESS_MODE = process.env.HEADLESS_MODE || true;
const ABOUT_PAGE = process.env.ABOUT_PAGE || "http://localhost:8668/about/";

describe("The about page for Stock Market Words website", () => {
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

  it("should display the navigation bar with Home and About links", async () => {
    const page = await browser.newPage();
    await page.goto(ABOUT_PAGE);
    await assertNavigationBar(page);
  });

  it("should display the About card and Stock Data section", async () => {
    const page = await browser.newPage();
    await page.goto(ABOUT_PAGE);
    const aboutCard = await page.$('.card .card-title');
    assert.notEqual(aboutCard, null);
    const stockDataSection = await page.$('#stock-data');
    assert.notEqual(stockDataSection, null);
  });

  it("should use the correct Bootstrap CDN version for CSS and JS", async () => {
    const page = await browser.newPage();
    await page.goto(ABOUT_PAGE);
    await assertBootstrapCDNVersion(page, '5.3.0');
  });
});
