# Simplified Chinese (zh-CN) i18n Evaluation

**Date:** 2026-04-03  
**Status:** Research / Evaluation  
**Scope:** What it takes to add zh-CN support to Stock Market Words

---

## Executive Summary

The site has **zero i18n infrastructure** today. All ~200+ user-facing strings are hardcoded in English across 22 Hugo templates and 4 JavaScript files. Hugo has excellent built-in multilingual support, so **no external i18n library or CDN is needed** for the core site. The only CDN addition would be DataTables' own language plugin (~1 file).

This is a **medium-to-large effort** — not because the tooling is hard, but because of the sheer surface area of hardcoded strings and translatable content pages.

---

## Current State

| Area | Status |
|------|--------|
| Hugo i18n functions (`{{ i18n }}` / `{{ T }}`) | ❌ Not used anywhere |
| `hugo/site/i18n/` directory | Exists but **empty** |
| `[languages]` config in hugo.toml | ❌ Not configured |
| `<html lang="">` attribute | Hardcoded to `"en"` |
| Content directory structure | Flat (no language prefixes) |
| JavaScript string externalization | ❌ None — all inline |
| DataTables localization | ❌ Using English defaults |
| External i18n library | ❌ None loaded |

---

## What Needs Translation

### Hugo Templates (~200+ strings across 22 files)

| File | Example Strings | Count (approx) |
|------|----------------|-----------------|
| `layouts/index.html` | "Paste any text. Find every hidden stock ticker.", "Extract Tickers →", "Try an example:", strategy labels | ~30 |
| `layouts/page/tool.html` | "Stock Ticker Extractor", "Find Hidden Tickers →", "What you can paste" | ~25 |
| `layouts/page/strategy-filter.html` | Table headers (Symbol, Name, Sector…), "No Matching Stocks", strategy names | ~30 |
| `layouts/page/filtered-data.html` | "✅ Total Tickers", "Filtered Ticker List", stat labels | ~25 |
| `layouts/page/raw-data.html` | "📊 NASDAQ Data", "Total Rows:", column headers | ~15 |
| `layouts/tickers/single.html` | "📊 Market Data", all metric labels, strategy interpretation text | ~40 |
| `layouts/tickers/list.html` | "Browse All Tickers", section labels | ~10 |
| `layouts/partials/navigation.html` | "Home", "Tool", "Data", "Articles", "Strategies", "Glossary", "About" | ~20 |
| `layouts/partials/footer.html` | "Source:", "Privacy Policy", copyright | ~10 |
| `layouts/articles/single.html` | "By", "Published", "Updated", author bio | ~5 |
| `layouts/shortcodes/ticker-portfolio-extraction-tool.html` | Duplicate of tool page strings | ~15 |

### JavaScript (~50+ strings across 4 files)

| File | What Needs Translation |
|------|----------------------|
| `static/js/portfolio-extractor.js` (850 lines) | Strategy names & descriptions, help text, error/alert messages, UI labels ("Previous", "Next", "Page N of M"), demo example texts |
| `static/js/filtered-data.js` (93 lines) | "Failed to load…", "Pass 1 Results Summary", column headers, search placeholder |
| `static/js/raw-ftp-data.js` (59 lines) | "Failed to load…", "Source:", "File:", "Downloaded:", "Total Rows:" |
| `static/js/TickerEngine.js` (319 lines) | ✅ No user-facing strings (pure algorithm) |
| `static/js/portfolio-worker.js` (144 lines) | ✅ No user-facing strings (Web Worker) |

### Content Pages (~30+ Markdown files)

| Directory | Files | Notes |
|-----------|-------|-------|
| `content/` (root) | ~15 pages (about, methodology, privacy, strategies, tool, etc.) | Full prose translation needed |
| `content/articles/` | 7 articles + index | Long-form educational content |
| `content/glossary/` | 17+ financial term definitions | Domain-specific translations |
| `content/tickers/` | 3,000+ auto-generated pages | **Skip** — these are data-driven, not prose |

### Third-Party Libraries

| Library | Version | CDN Used | i18n Needed? |
|---------|---------|----------|-------------|
| jQuery 3.7.1 | 3.7.1 | code.jquery.com | ❌ No UI strings |
| Bootstrap 5.3.0 | 5.3.0 | cdn.jsdelivr.net | ❌ CSS framework |
| Bootswatch 5.3.0 | 5.3.0 | cdn.jsdelivr.net | ❌ CSS theme |
| **DataTables 1.13.7** | 1.13.7 | cdn.datatables.net | **✅ Yes** — "Search:", "Showing X to Y of Z", pagination |
| Chart.js 4.4.1 | 4.4.1 | cdn.jsdelivr.net | ❌ Labels come from templates |

---

## Should We Add an i18n Library?

**No.** Hugo's built-in multilingual system is the right tool here. Adding a runtime i18n library (like i18next) would be unnecessary complexity.

### Hugo's Built-in i18n Covers:

- **Template strings** → `{{ i18n "key" }}` function with TOML/YAML translation files
- **Content translation** → Language-prefixed content directories (`content/en/`, `content/zh-cn/`)
- **URL routing** → Automatic `/zh-cn/` prefix for Chinese pages
- **Language switcher** → Built-in `.Translations` variable for linking between languages
- **Date/number formatting** → `lang.FormatNumber` already in use

### For JavaScript Strings:

Hugo can generate a JSON translations file at build time via a data template or output format. The JS files would fetch `/data/i18n-{lang}.json` and use it for strategy names, error messages, etc. No external library needed — a small wrapper function suffices.

### For DataTables:

DataTables has its own language plugin system. Use their CDN directly:

```html
<!-- Load zh-CN language for DataTables -->
<script>
$.extend(true, $.fn.dataTable.defaults, {
    language: {
        url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/zh-HANS.json'
    }
});
</script>
```

This is the **only CDN addition needed**.

---

## What CDN to Use?

**No new CDN is needed.** The project already uses:

| CDN | Currently Loads | Would Also Load |
|-----|----------------|-----------------|
| `cdn.datatables.net` | DataTables core | DataTables zh-HANS language plugin |
| `cdn.jsdelivr.net` | Bootstrap, Bootswatch, Chart.js | Nothing new |
| `code.jquery.com` | jQuery | Nothing new |

The DataTables i18n file (`zh-HANS.json`) is hosted on the same `cdn.datatables.net` CDN already in use. No new CDN dependencies.

---

## Implementation Approach

### Phase 1: Hugo Multilingual Setup
1. Add `[languages]` config to `hugo.toml`
2. Create `i18n/en.toml` with all English string keys
3. Create `i18n/zh-cn.toml` with Chinese translations
4. Update `<html lang="">` to use `{{ .Site.Language.Lang }}`

### Phase 2: Template String Extraction (~200 strings)
1. Replace every hardcoded string in layouts with `{{ i18n "key" }}`
2. Priority order: navigation → footer → home page → tool → strategies → data pages → ticker pages

### Phase 3: JavaScript i18n (~50 strings)
1. Create Hugo-generated JSON translation files per language
2. Add a thin JS translation loader (no library needed, ~20 lines)
3. Update `portfolio-extractor.js` strategy definitions to pull from translations
4. Update error messages, UI labels, pagination text

### Phase 4: DataTables Localization
1. Conditionally load DataTables language plugin based on site language
2. Single `<script>` tag addition — uses existing `cdn.datatables.net`

### Phase 5: Content Translation
1. Restructure content dirs: `content/en/` and `content/zh-cn/`
2. Translate ~30 prose pages (articles, glossary, methodology, about, etc.)
3. Auto-generated ticker pages: add translated labels to the template, data stays in English

### Phase 6: Language Switcher UI
1. Add language toggle to navigation (e.g., "EN | 中文")
2. Use Hugo's `.Translations` to link equivalent pages

---

## Effort Estimate

| Phase | Scope | Complexity |
|-------|-------|------------|
| Phase 1: Hugo config | 1 file | Low |
| Phase 2: Template extraction | 22 layout files, ~200 strings | **High** (tedious but straightforward) |
| Phase 3: JS i18n | 3 JS files, ~50 strings | Medium |
| Phase 4: DataTables | 1 script tag | Low |
| Phase 5: Content translation | ~30 pages of prose | **High** (requires Chinese translator) |
| Phase 6: Language switcher | Navigation partial | Low |

**Biggest bottleneck:** Phase 5 — translating ~30 pages of financial/educational content into accurate Simplified Chinese. This requires domain knowledge in both finance and Chinese.

---

## Risks & Considerations

1. **URL structure change** — Adding `/zh-cn/` prefix changes all Chinese page URLs. English pages can stay at root or move to `/en/`.
2. **SEO impact** — Need `hreflang` tags, separate sitemaps per language, and proper canonical URLs.
3. **Ticker pages (3,000+)** — Template labels translate, but ticker symbols and financial data are universal. No need to duplicate 3,000 content files.
4. **Strategy names** — "Dividend Daddy", "Moon Shot", etc. are brand-like names. Decide: translate them or keep English with Chinese descriptions?
5. **Financial terminology** — Glossary terms need accurate Chinese financial translations (e.g., RSI = 相对强弱指标, P/E = 市盈率, Market Cap = 市值).
6. **RTL not needed** — Simplified Chinese is LTR, so no layout changes needed.
7. **Test updates** — E2E tests check for English strings; need language-aware test variants or skip string checks for zh-CN.

---

## Recommendation

**Use Hugo's built-in i18n. No external i18n library. No new CDN.** The only addition is DataTables' zh-HANS language file from their existing CDN.

Start with Phase 1–2 (config + template extraction) as a prerequisite PR — this lays the foundation without needing any Chinese translations yet. Phase 5 (content) can follow incrementally.
