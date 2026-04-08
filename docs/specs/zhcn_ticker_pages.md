# zh-CN Ticker Pages

**Status:** Draft (investigation pending)
**Author:** unassigned
**Created:** 2026-04-08

## Context

`stockmarketwords.com/tickers/<symbol>/` resolves for ~8,000 tickers (CRM,
AAPL, NVDA, ...). The corresponding `/zh-cn/tickers/<symbol>/` URLs all 404.
This means our Chinese audience cannot land on any individual ticker page
from search engines or our own internal links.

The ticker detail pages are not hand-authored markdown — they're materialized
at Hugo build time by a content adapter:
`hugo/site/content/tickers/_content.gotmpl` (~30 lines). It iterates over
`Site.Data.all_tickers.tickers` (a JSON file written by
`ticker-cli hugo all-tickers`) and calls `$.AddPage` for each ticker. The
template `hugo/site/layouts/tickers/single.html` already uses `{{ i18n }}`
for every label, so once the routes exist, the labels render in Chinese
automatically.

The ticker detail page is one of the highest-traffic page types on the site
(via long-tail organic search). Fixing this is high-leverage.

Background reading:

- [`docs/design/architecture_overview.md`](../design/20260408_013203_UTC_architecture_overview.md)
- [`docs/design/data_pipeline.md`](../design/20260408_013203_UTC_data_pipeline.md)
- [`docs/design/i18n_architecture.md`](../design/20260408_013203_UTC_i18n_architecture.md)

## Goal

Every URL of the form `/tickers/<symbol>/` has a working
`/zh-cn/tickers/<symbol>/` mirror that returns HTTP 200 and renders all
labels in Simplified Chinese.

## Non-goals

- Translating sector / industry strings to Chinese (they pass through as
  English in v1; revisit if it matters).
- Translating company names (proper nouns, stay in English).
- Changing the source of ticker data — `all_tickers.json` remains the
  pipeline output.
- Adding per-language metadata to the SQLite schema.

## User stories

- As a Singaporean user who Googles "CRM 股票", I want
  `stockmarketwords.com/zh-cn/tickers/crm/` to be a valid landing page
  showing CRM's metrics in Chinese instead of a 404.
- As an internal contributor, I want the language switcher on `/tickers/crm/`
  to send users to the working `/zh-cn/tickers/crm/` instead of an empty page.

## Design

### Investigation step (must run before locking the design)

The current behavior needs to be reproduced and root-caused. Allocate
~15-30 minutes to this *before* writing code.

1. From a clean checkout: `cd hugo/site && hugo server`.
2. `curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:1313/tickers/crm/`
   → expect `200`.
3. `curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:1313/zh-cn/tickers/crm/`
   → expect `404` (the bug).
4. Build to disk: `hugo --minify` and inspect:
   - `ls hugo/site/public/tickers/ | head` (should have many entries)
   - `ls hugo/site/public/zh-cn/tickers/ 2>/dev/null` (the question — empty? missing?)
5. Read Hugo's official docs on content adapters
   (`_content.gotmpl`) to confirm whether the adapter iterates per language
   automatically or whether it must explicitly set the `lang` key on each
   `$page` dict it adds.
6. Try the minimal patch: in `hugo/site/content/tickers/_content.gotmpl`,
   wrap the existing loop in `{{ range site.Languages }}` and set
   `"lang" .Lang` in the `$page` dict; rebuild and re-test step 3.

Record the findings in this spec under "Root cause" before proceeding.

### Root cause

**TODO** — fill in after the investigation. One of:

- (A) The content adapter does not auto-iterate languages and must be
  rewritten to call `$.AddPage` once per language.
- (B) The data file path or template path resolves only for the default
  language and needs a `_content.zh-cn.gotmpl` sibling.
- (C) Something subtler — the gotmpl runs but the resulting pages are
  filtered out by a `disableKinds` or section config.

### Recommended fix — Option A (Hugo-only)

Default recommendation pending the investigation. Modify
`hugo/site/content/tickers/_content.gotmpl` to explicitly add the page for
each configured language:

```gotmpl
{{- range $lang := site.Languages }}
  {{- range $.Site.Data.all_tickers.tickers }}
    {{- $page := dict
      "kind"  "page"
      "path"  .symbol
      "lang"  $lang.Lang
      "title" (printf "%s Stock — %s" .symbol .name)
      "params" (dict
        "symbol" .symbol
        ...
      )
    }}
    {{- $.AddPage $page }}
  {{- end }}
{{- end }}
```

(The exact form depends on Hugo's content-adapter API surface — confirm
during the investigation. The shape above is illustrative.)

This requires **no Python CLI changes** and **no template changes** —
`layouts/tickers/single.html` already uses `{{ i18n }}` everywhere.

### Fallback fix — Option B (Python CLI)

If Option A turns out not to be possible with content adapters, fall back to
generating per-language data files in `python3/src/stock_ticker/hugo_generators.py`:

1. Have `ticker-cli hugo all-tickers` write both `all_tickers.json` (English
   default) and `all_tickers.zh-cn.json`.
2. Add a `_content.zh-cn.gotmpl` sibling that reads the zh-cn data file.
3. Optionally translate `sector` / `industry` strings via a static lookup
   table in `hugo_generators.py`.

This is more code and more maintenance, so prefer Option A unless forced
into B.

### What stays unchanged

- `python3/src/stock_ticker/hugo_generators.py:generate_all_tickers_data` —
  the JSON shape is fine.
- `hugo/site/layouts/tickers/single.html` — already i18n-ready.
- `hugo/site/i18n/zh-cn.toml` — all `ticker_*` and `th_*` keys already exist.

## Affected files

**Modified (Option A):**

- `hugo/site/content/tickers/_content.gotmpl`
- `tests/puppeteer/website-pages.e2e.test.js` (add a `/zh-cn/tickers/crm/` smoke check)

**Modified (Option B, fallback only):**

- `python3/src/stock_ticker/hugo_generators.py`
- `python3/src/stock_ticker/cli.py` (if a new flag is needed)
- `hugo/site/content/tickers/_content.gotmpl` (or a new `.zh-cn.gotmpl`)
- `tests/puppeteer/website-pages.e2e.test.js`

## Verification

1. `cd hugo/site && hugo server` starts cleanly.
2. `curl -sf http://localhost:1313/zh-cn/tickers/crm/` returns 200.
3. The HTML contains the Chinese label string for "Market Data" (which is
   `市场数据` per `hugo/site/i18n/zh-cn.toml`'s `ticker_market_data` key).
4. `curl -sf http://localhost:1313/zh-cn/tickers/aapl/` and
   `http://localhost:1313/zh-cn/tickers/nvda/` also return 200.
5. The English ticker pages still work (`/tickers/crm/` returns 200).
6. A new Playwright test in `tests/puppeteer/` (or its successor) asserts
   that `/zh-cn/tickers/crm/` returns 200 and contains the expected Chinese
   label.
7. Production build (`hugo --minify`) finishes in roughly the same wall-clock
   time as before (we've ~doubled the page count for tickers; it should still
   be acceptable, but record the before/after numbers).

## Open questions

- **Q1:** Does doubling the ticker page count (`~8k → ~16k`) cause an
  unacceptable build-time hit? **Default: assume no, measure during
  implementation.** If it's a problem, consider lazy generation or a smaller
  ticker universe for zh-CN.
- **Q2:** Should `sector` and `industry` strings be translated? **Default:
  no in v1.** They're displayed but not searched on; English is acceptable
  for a launch.
- **Q3:** Does the zh-CN ticker page need its own canonical / hreflang
  treatment for SEO? **Default: yes, but the existing
  `hugo/site/layouts/partials/head.html` should already emit hreflang for
  any page that has a translation — confirm it works for content-adapter
  pages.**

## Alternatives considered

- **Hand-author 8,000 markdown files per language.** Absurd. Not done.
- **Use a Hugo shortcode instead of a content adapter.** Would still 404 at
  the URL level; shortcodes don't create routes.
- **Skip zh-CN ticker pages entirely and redirect to English.** Bad for SEO
  and bad for the user. Only acceptable as a temporary stopgap.
