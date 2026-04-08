# Extract Tickers — GA4 Event Tracking

**Status:** Draft
**Author:** unassigned
**Created:** 2026-04-08

## Context

The home-page **Extract Tickers** tool is the marquee feature of
stockmarketwords.com. It's instrumented with **zero** product analytics
today: GA4 is configured at the page-view level
(`hugo/site/layouts/partials/google-analytics.html`, `gtag.js` loads when
`googleAnalyticsId` is set), but `hugo/site/static/js/portfolio-extractor.js`
emits no custom events. We have no idea what people paste, how often, or
which tickers come out the other side. We need to start measuring so we can
make data-driven product decisions.

The audience skews Singaporean, so any data collection has to respect
Singapore's PDPA. The strict rule: **never send raw user input to GA**.

Background reading:

- [`docs/design/architecture_overview.md`](../design/20260408_013203_UTC_architecture_overview.md)
- `hugo/site/static/js/portfolio-extractor.js` (the file being instrumented)
- `hugo/site/layouts/partials/google-analytics.html` (existing GA4 wiring)

## Goal

When a user clicks **Extract Tickers**, we record a small set of GA4 custom
events that let us answer: how many people use the tool, how big are typical
inputs, what tickers come out, which strategy is most popular, and how long
extraction takes — without ever capturing the raw text the user pasted.

## Non-goals

- Storing data anywhere other than GA4. No new backend, no DB columns.
- A/B testing infrastructure. (Could be a follow-up.)
- Tracking page views (already handled by `gtag.js`).
- Capturing the user's IP, browser fingerprint, or any identifier beyond
  what GA4 collects by default.

## User stories

- As the site owner, I want to see in GA4 DebugView which examples users
  click on most often, so I can prioritize tutorial content.
- As the site owner, I want to know which tickers get extracted most
  frequently across all users, so I can write articles about them.
- As a privacy-conscious Singaporean user, I want assurance that my pasted
  text never leaves my browser unhashed.

## Design

### Events to emit

All events go through `gtag('event', name, params)`. Three custom events:

#### 1. `extract_tickers_submitted`

Fired in `portfolio-extractor.js` immediately when the form's submit handler
runs (before extraction kicks off).

| Param | Type | Source |
|---|---|---|
| `input_chars` | int | `inputText.length` |
| `input_words` | int | `inputText.trim().split(/\s+/).length` |
| `input_hash` | string | First 16 hex chars of `SHA-256` of the normalized input (lowercased, whitespace-collapsed). Computed via `crypto.subtle.digest`. |
| `paste_source` | string | `"manual"` if the user typed/pasted, `"example_button"` if the input came from `fillExample(n)`, `"unknown"` otherwise. Tracked via a module-level flag set by `fillExample`. |
| `language` | string | `document.documentElement.lang` (`"en"` or `"zh-cn"`) |

#### 2. `extract_tickers_completed`

Fired after the Web Worker (or fallback synchronous path) returns results.

| Param | Type | Source |
|---|---|---|
| `tickers_found` | int | result array length |
| `tickers_list` | string | comma-joined symbols, capped at 100 chars (truncate with "...") |
| `top_strategy` | string | name of the highest-scoring strategy across the result set, or `""` if none |
| `duration_ms` | int | `performance.now()` delta from submit to result render |
| `language` | string | `document.documentElement.lang` |

Ticker symbols are public data (NASDAQ listings), so transmitting them is
not a PDPA concern.

#### 3. `example_clicked`

Fired in `fillExample(n)` before the input is filled.

| Param | Type | Source |
|---|---|---|
| `example_index` | int | the `n` argument |
| `language` | string | `document.documentElement.lang` |

### Hashing implementation

```javascript
async function sha256Hex16(input) {
  const normalized = input.toLowerCase().replace(/\s+/g, ' ').trim();
  const bytes = new TextEncoder().encode(normalized);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest))
    .slice(0, 8)                              // 8 bytes = 16 hex chars
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}
```

16 hex chars (64 bits) is enough to distinguish ~4 billion unique inputs
without much collision risk for our scale, while being short enough to
group nicely in GA4 reports. If the user's browser doesn't support
`crypto.subtle.digest` (very old / insecure context), set `input_hash` to
`""` and proceed.

### gtag safety wrapper

`gtag` may not exist in local dev or if the user has an ad blocker. Wrap
every call:

```javascript
function safeGtag(event, params) {
  if (typeof window.gtag === 'function') {
    try { window.gtag('event', event, params); } catch (_) {}
  }
}
```

This matches the existing pattern in
`hugo/site/layouts/partials/google-analytics.html` where the partial is
conditionally rendered only if `googleAnalyticsId` is non-empty.

### Privacy policy update

`hugo/site/content/privacy-policy.md` and `privacy-policy.zh-cn.md` need a
new paragraph (in the same PR as the JS changes):

> When you use the Extract Tickers tool on our home page, we record an
> anonymized usage event that includes the size of your input (character
> and word count), a one-way cryptographic hash of the input that cannot
> be reversed to recover the original text, the list of stock ticker
> symbols extracted, and how long the extraction took. We do **not**
> record the raw text you paste. These metrics are sent to Google
> Analytics 4 and used to improve the tool.

Provide the equivalent text in Chinese for the `.zh-cn.md` version.

## Affected files

**Modified:**

- `hugo/site/static/js/portfolio-extractor.js` — add the three event emitters and the `safeGtag` / `sha256Hex16` helpers.
- `hugo/site/layouts/index.html` — confirm `fillExample(n)` calls flow through the new analytics path. May need a small refactor if `fillExample` lives inline.
- `hugo/site/content/privacy-policy.md` — add the new paragraph.
- `hugo/site/content/privacy-policy.zh-cn.md` — add the same paragraph in Chinese.
- `tests/puppeteer/ticker-ui.e2e.test.js` (or its Playwright successor) — add an assertion that `window.gtag` is called with `extract_tickers_submitted` on form submit.

**Not modified:**

- `hugo/site/layouts/partials/google-analytics.html` — existing wiring is fine.
- `hugo.toml` — no new params needed.
- Python CLI — none of this is server-side.

## Verification

1. Set `HUGO_PARAMS_GOOGLEANALYTICSID=G-XXXXXXX` (use a debug GA4 property)
   and run `cd hugo/site && hugo server`.
2. Open `http://localhost:1313/` with the Chrome GA4 DebugView extension
   pointed at the same property.
3. Click the example buttons → `example_clicked` events appear in DebugView
   with the right `example_index`.
4. Paste a news article and click **Extract Tickers** → both
   `extract_tickers_submitted` and `extract_tickers_completed` events
   appear, with sane param values.
5. Verify in DebugView that `input_hash` is a 16-char hex string and **does
   not contain any words from the pasted text** (a quick eyeball test).
6. Repeat the same paste a second time → `input_hash` is identical (proving
   the normalization works) but `extract_tickers_submitted` is a fresh event.
7. Repeat in `/zh-cn/` → events fire with `language: "zh-cn"`.
8. Test with `googleAnalyticsId` empty (local dev default) → no console
   errors, the tool still works, no events attempted.
9. Run Playwright E2E: the new test asserts `window.gtag` was called with
   the expected event name and an `input_hash` matching `/^[0-9a-f]{16}$/`.

## Open questions

- **Q1:** Should `tickers_list` be truncated by character count or by ticker
  count? **Default: character count (100 chars), simpler.** Revisit if power
  users routinely have >20 tickers per paste.
- **Q2:** Should we also fire an `extract_tickers_failed` event on errors?
  **Default: yes, with `error_type` param.** Cheap and useful for catching
  regressions.
- **Q3:** Does the privacy policy update need legal review? **Default: ask
  before deploying.** This is the first time the site collects per-event
  user data, even hashed.

## Alternatives considered

- **Send the first 200 chars of raw input.** More insight per event, but
  PDPA-fragile and would absolutely require legal sign-off. Rejected.
- **Roll our own analytics endpoint instead of using GA4.** More control,
  but a new backend to maintain. GA4 is already paid for and configured.
  Rejected.
- **Don't hash, just send sizes.** Simpler, but loses the ability to
  detect repeat pastes (useful for understanding power users vs one-off
  visits). The hash is cheap insurance.
