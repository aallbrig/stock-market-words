/**
 * Internationalization (i18n) tests for zh-CN Chinese language support
 *
 * Essential coverage:
 *  1. zh-CN pages exist and return 200
 *  2. zh-CN pages render Chinese text (not English fallbacks)
 *  3. Language switcher appears and links correctly (EN↔ZH)
 *  4. English pages are unchanged at root URLs
 *  5. hreflang SEO tags are present on both language versions
 *  6. Navigation links on zh-CN pages stay within /zh-cn/ prefix
 *  7. window.I18N JS object is injected with translated strings
 *  8. No console errors on zh-CN pages
 */

import { test, expect } from '@playwright/test';

// Key zh-CN pages that must exist (mirrors EN pages created with .zh-cn.md content)
const ZH_PAGES = [
  { path: '/zh-cn/', name: 'Home (ZH)' },
  { path: '/zh-cn/about/', name: 'About (ZH)' },
  { path: '/zh-cn/contact/', name: 'Contact (ZH)' },
  { path: '/zh-cn/methodology/', name: 'Methodology (ZH)' },
  { path: '/zh-cn/strategies/', name: 'Strategies (ZH)' },
  { path: '/zh-cn/strategy-dividend-daddy/', name: 'Strategy: Dividend Daddy (ZH)' },
  { path: '/zh-cn/strategy-moon-shot/', name: 'Strategy: Moon Shot (ZH)' },
  { path: '/zh-cn/strategy-falling-knife/', name: 'Strategy: Falling Knife (ZH)' },
  { path: '/zh-cn/strategy-over-hyped/', name: 'Strategy: Over Hyped (ZH)' },
  { path: '/zh-cn/strategy-institutional-whale/', name: 'Strategy: Institutional Whale (ZH)' },
  { path: '/zh-cn/strategy-reit-radar/', name: 'Strategy: REIT Radar (ZH)' },
  { path: '/zh-cn/filtered-data/', name: 'Filtered Data (ZH)' },
  { path: '/zh-cn/raw-ftp-data/', name: 'Raw FTP Data (ZH)' },
  { path: '/zh-cn/privacy-policy/', name: 'Privacy Policy (ZH)' },
  { path: '/zh-cn/data/', name: 'Data (ZH)' },
];

// Matching EN pages to verify they still work at root
const EN_PAGES = [
  { path: '/', name: 'Home' },
  { path: '/about/', name: 'About' },
  { path: '/strategy-dividend-daddy/', name: 'Strategy: Dividend Daddy' },
  { path: '/filtered-data/', name: 'Filtered Data' },
];

// ─── 1. zh-CN pages load with HTTP 200 ───────────────────────────────────────

test.describe('zh-CN Page Availability', () => {
  for (const { path, name } of ZH_PAGES) {
    test(`${name} (${path}) returns 200`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response.status()).toBe(200);
    });
  }
});

// ─── 2. zh-CN pages render Chinese text ──────────────────────────────────────

test.describe('zh-CN Content Rendering', () => {
  test('Home page renders Chinese heading', async ({ page }) => {
    await page.goto('/zh-cn/');
    // The hero heading should contain Chinese characters
    const heading = page.locator('h1').first();
    await expect(heading).toBeVisible();
    const text = await heading.textContent();
    // Must contain at least one CJK character
    expect(text).toMatch(/[\u4e00-\u9fff]/);
  });

  test('About page renders Chinese content', async ({ page }) => {
    await page.goto('/zh-cn/about/');
    const body = await page.locator('.container').first().textContent();
    expect(body).toMatch(/[\u4e00-\u9fff]/);
  });

  test('Navigation labels are in Chinese on zh-CN pages', async ({ page }) => {
    await page.goto('/zh-cn/');
    // The nav should contain Chinese text like 数据, 工具, 关于
    const nav = page.locator('nav.navbar');
    const navText = await nav.textContent();
    expect(navText).toMatch(/[\u4e00-\u9fff]/);
  });

  test('Footer is in Chinese on zh-CN pages', async ({ page }) => {
    await page.goto('/zh-cn/');
    const footer = page.locator('footer');
    const footerText = await footer.textContent();
    expect(footerText).toMatch(/[\u4e00-\u9fff]/);
  });

  test('html lang attribute is zh-cn', async ({ page }) => {
    await page.goto('/zh-cn/');
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('zh-cn');
  });
});

// ─── 3. Language switcher ────────────────────────────────────────────────────

test.describe('Language Switcher', () => {
  test('English page shows Chinese switcher link', async ({ page }) => {
    await page.goto('/about/');
    // Should have a link with 中文 text pointing to /zh-cn/about/
    const zhLink = page.locator('a.nav-link', { hasText: '中文' });
    await expect(zhLink).toBeVisible();
    const href = await zhLink.getAttribute('href');
    expect(href).toBe('/zh-cn/about/');
  });

  test('Chinese page shows English switcher link', async ({ page }) => {
    await page.goto('/zh-cn/about/');
    const enLink = page.locator('a.nav-link', { hasText: 'English' });
    await expect(enLink).toBeVisible();
    const href = await enLink.getAttribute('href');
    expect(href).toBe('/about/');
  });

  test('Language switcher navigates to correct page', async ({ page }) => {
    await page.goto('/about/');
    const zhLink = page.locator('a.nav-link', { hasText: '中文' });
    await zhLink.click();
    await expect(page).toHaveURL(/\/zh-cn\/about\//);
    // Verify we landed on a Chinese page
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('zh-cn');
  });
});

// ─── 4. English pages unchanged ──────────────────────────────────────────────

test.describe('English Pages Unchanged', () => {
  for (const { path, name } of EN_PAGES) {
    test(`${name} (${path}) still loads at root URL`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response.status()).toBe(200);
      const lang = await page.locator('html').getAttribute('lang');
      expect(lang).toBe('en');
    });
  }

  test('English home page still has English content', async ({ page }) => {
    await page.goto('/');
    const brand = page.locator('a.navbar-brand');
    await expect(brand).toHaveText('Stock Market Words');
  });
});

// ─── 5. hreflang SEO tags ────────────────────────────────────────────────────

test.describe('hreflang SEO Tags', () => {
  test('English page has hreflang for both languages', async ({ page }) => {
    await page.goto('/about/');
    const enTag = page.locator('link[hreflang="en"]');
    const zhTag = page.locator('link[hreflang="zh-cn"]');
    const defaultTag = page.locator('link[hreflang="x-default"]');
    await expect(enTag).toHaveCount(1);
    await expect(zhTag).toHaveCount(1);
    await expect(defaultTag).toHaveCount(1);
  });

  test('Chinese page has hreflang for both languages', async ({ page }) => {
    await page.goto('/zh-cn/about/');
    const enTag = page.locator('link[hreflang="en"]');
    const zhTag = page.locator('link[hreflang="zh-cn"]');
    await expect(enTag).toHaveCount(1);
    await expect(zhTag).toHaveCount(1);
  });
});

// ─── 6. zh-CN navigation links stay within /zh-cn/ ──────────────────────────

test.describe('zh-CN Internal Links', () => {
  test('Navigation links on zh-CN page use /zh-cn/ prefix', async ({ page }) => {
    await page.goto('/zh-cn/');
    // Get all nav links (excluding external links and the language switcher)
    const navLinks = page.locator('nav.navbar a[href^="/"]');
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const href = await navLinks.nth(i).getAttribute('href');
      const text = await navLinks.nth(i).textContent();
      // Skip the language switcher itself (links to English)
      if (text.trim() === 'English') continue;
      // All other internal links should be under /zh-cn/
      expect(href, `Nav link "${text.trim()}" should use /zh-cn/ prefix`).toMatch(/^\/zh-cn\//);
    }
  });

  test('Footer links on zh-CN page use /zh-cn/ prefix', async ({ page }) => {
    await page.goto('/zh-cn/');
    const footerLinks = page.locator('footer a[href^="/"]');
    const count = await footerLinks.count();

    for (let i = 0; i < count; i++) {
      const href = await footerLinks.nth(i).getAttribute('href');
      expect(href, `Footer link should use /zh-cn/ prefix`).toMatch(/^\/zh-cn\//);
    }
  });
});

// ─── 7. JavaScript i18n injection ────────────────────────────────────────────

test.describe('JavaScript i18n', () => {
  test('zh-CN home page has window.I18N with Chinese strings', async ({ page }) => {
    await page.goto('/zh-cn/');
    const i18n = await page.evaluate(() => window.I18N);
    expect(i18n).toBeTruthy();
    // The error_processing key should contain Chinese characters
    expect(i18n.error_processing).toMatch(/[\u4e00-\u9fff]/);
    // Strategy names should be in English (user requirement)
    expect(i18n.strategies.DIVIDEND_DADDY.name).toContain('Dividend Daddy');
    // Strategy descriptions should be in Chinese
    expect(i18n.strategies.DIVIDEND_DADDY.description).toMatch(/[\u4e00-\u9fff]/);
  });

  test('English home page has window.I18N with English strings', async ({ page }) => {
    await page.goto('/');
    const i18n = await page.evaluate(() => window.I18N);
    expect(i18n).toBeTruthy();
    expect(i18n.error_processing).toMatch(/[a-zA-Z]/);
  });

  test('zh-CN page sets SITE_LANG to zh-cn', async ({ page }) => {
    await page.goto('/zh-cn/');
    const lang = await page.evaluate(() => window.SITE_LANG);
    expect(lang).toBe('zh-cn');
  });
});

// ─── 8. No console errors on zh-CN pages ────────────────────────────────────

test.describe('zh-CN No Console Errors', () => {
  const KEY_ZH_PAGES = [
    { path: '/zh-cn/', name: 'Home (ZH)' },
    { path: '/zh-cn/about/', name: 'About (ZH)' },
    { path: '/zh-cn/strategy-dividend-daddy/', name: 'Strategy: Dividend Daddy (ZH)' },
  ];

  for (const { path, name } of KEY_ZH_PAGES) {
    test(`${name} has no console errors`, async ({ page }) => {
      const consoleErrors = [];
      const pageErrors = [];

      page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });
      page.on('pageerror', error => {
        pageErrors.push(error.message);
      });

      await page.goto(path);
      await page.waitForTimeout(1000);

      // Filter benign errors (missing data files, DataTable init on empty data)
      const critical = consoleErrors.filter(err =>
        !err.includes('404') &&
        !err.includes('Failed to load resource') &&
        !err.includes('DataTable')
      );

      if (critical.length > 0) {
        console.log(`Console errors on ${name}:`, critical);
      }
      expect(critical).toHaveLength(0);
      expect(pageErrors).toHaveLength(0);
    });
  }
});
