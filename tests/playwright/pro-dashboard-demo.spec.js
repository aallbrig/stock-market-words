/**
 * Pro dashboard — demo account smoke tests (localhost dev stack only).
 *
 * Authenticates as demo@stockmarketwords.com using the magic link flow,
 * then asserts the dashboard renders the Strait of Malacca watchlists with
 * working ticker links.
 *
 * Requires the full local dev stack (task dev):
 *   - Hugo  on http://localhost:1313
 *   - SAM   on http://localhost:3000
 *   - LocalStack on http://localhost:4566
 *
 * Skips automatically when the stack isn't running.
 */

import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

const HUGO_URL  = 'http://localhost:1313';
const SAM_URL   = 'http://localhost:3000';
const DYNAMO_EP = 'http://localhost:4566';
const DEMO_EMAIL = 'demo@stockmarketwords.com';

// Override the shared baseURL — these tests always run against the local dev server.
test.use({ baseURL: HUGO_URL });

// ── Helpers ──────────────────────────────────────────────────────────────────

function devStackRunning() {
  try {
    execSync(`curl -sf --max-time 2 ${HUGO_URL}/ -o /dev/null`, { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

function requestMagicLink() {
  execSync(
    `curl -sf -X POST ${SAM_URL}/auth/magic-link \
       -H "Content-Type: application/json" \
       -d '{"email": "${DEMO_EMAIL}"}' -o /dev/null`,
    { stdio: 'pipe' }
  );
}

function getUnusedMagicToken() {
  const raw = execSync(
    `aws dynamodb query \
       --endpoint-url ${DYNAMO_EP} \
       --region us-east-1 \
       --table-name smw-pro-magic-tokens \
       --index-name email-index \
       --key-condition-expression "email = :e" \
       --filter-expression "used = :f" \
       --expression-attribute-values '{":e":{"S":"${DEMO_EMAIL}"},":f":{"BOOL":false}}' \
       --output json`,
    { stdio: 'pipe' }
  ).toString();

  const items = JSON.parse(raw).Items || [];
  if (items.length === 0) throw new Error('No unused magic token in DynamoDB for demo account');

  // Most recently issued token has the highest TTL
  items.sort((a, b) => Number(b.ttl.N) - Number(a.ttl.N));
  return items[0].token.S;
}

async function authenticateDemo(page) {
  requestMagicLink();
  // Give SAM a moment to write the token to DynamoDB
  await page.waitForTimeout(1000);
  const token = getUnusedMagicToken();

  // The callback page JS exchanges the token for a JWT and stores it in
  // localStorage, then redirects to /pro/dashboard/
  await page.goto(`/pro/callback?token=${token}`);
  await page.waitForURL(`${HUGO_URL}/pro/dashboard/`, { timeout: 15000 });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

// Serial: tests share the demo account — parallel workers would race on magic tokens.
test.describe.serial('Pro Dashboard — Demo Account', () => {
  test.beforeEach(async () => {
    if (!devStackRunning()) {
      test.skip(true, 'Dev stack not running (Hugo on :1313) — skipping localhost tests');
    }
  });

  test('demo account signs in and sees Strait of Malacca watchlists', async ({ page }) => {
    await authenticateDemo(page);

    // The sidebar should show watchlist buttons
    const sidebar = page.locator('#wl-list');
    await expect(sidebar).toBeVisible({ timeout: 10000 });

    // Wait for at least one watchlist button to appear
    const firstBtn = sidebar.locator('button').first();
    await expect(firstBtn).toBeVisible({ timeout: 10000 });

    // There should be 10 watchlists from the Strait of Malacca article
    const buttons = sidebar.locator('button');
    await expect(buttons).toHaveCount(10, { timeout: 10000 });
  });

  test('watchlist ticker links use /tickers/ path — not /stocks/', async ({ page }) => {
    await authenticateDemo(page);

    // Click the first watchlist to render the detail view
    const sidebar = page.locator('#wl-list');
    await sidebar.locator('button').first().waitFor({ timeout: 10000 });
    await sidebar.locator('button').first().click();

    // Wait for the table to populate
    const tableBody = page.locator('#wl-table-body');
    await tableBody.locator('tr a').first().waitFor({ timeout: 10000 });

    const links = await tableBody.locator('tr a').all();
    expect(links.length).toBeGreaterThan(0);

    for (const link of links) {
      const href = await link.getAttribute('href');
      expect(href, `Ticker link must use /tickers/ — got: ${href}`).toMatch(/^\/tickers\//);
    }
  });

  test('no demo watchlist ticker link leads to a 404', async ({ page, request }) => {
    await authenticateDemo(page);

    const sidebar = page.locator('#wl-list');
    await sidebar.locator('button').first().waitFor({ timeout: 10000 });

    const wlButtons = await sidebar.locator('button').all();
    const hrefs = new Set();

    // Walk every watchlist and collect all ticker hrefs
    for (const btn of wlButtons) {
      await btn.click();
      const tableBody = page.locator('#wl-table-body');
      // Some watchlists have 1 ticker, some have 11 — wait for any row
      await tableBody.locator('tr').first().waitFor({ timeout: 5000 }).catch(() => {});
      const links = await tableBody.locator('tr a').all();
      for (const link of links) {
        const href = await link.getAttribute('href');
        if (href) hrefs.add(href);
      }
    }

    expect(hrefs.size).toBeGreaterThan(0);

    // Verify each ticker page returns 200
    const failures = [];
    for (const href of hrefs) {
      const resp = await request.get(HUGO_URL + href);
      if (resp.status() !== 200) {
        failures.push(`${href} → ${resp.status()}`);
      }
    }

    if (failures.length > 0) {
      console.error('Ticker pages that did not return 200:\n' + failures.join('\n'));
    }
    expect(failures).toHaveLength(0);
  });
});
