const assert = require("assert");
const puppeteer = require("puppeteer");

const HEADLESS_MODE = process.env.HEADLESS_MODE || true;
const API_BASE = process.env.EXCHANGE_DATA_PAGE_BASE || "http://localhost:1313/api";

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

  describe("All exchange data", () => {
    describe("TXT format", () => {
      it("endpoint exists", async () => {
        const page = await browser.newPage();

        const response = await page.goto(`${API_BASE}/all-exchanges.txt`);

        assert.equal(response._status, 200);
      });
      it.skip("endpoint contains data", async () => {
        const page = await browser.newPage();

        const body = await page.$('body');
        const bodyChildren = await page.evaluateHandle(el => el.children, body);

        assert.equal(bodyChildren.length > 0, true);
      });
    });
  });
});