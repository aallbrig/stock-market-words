# Strategy URL Migration

**Status:** Draft  
**Author:** Copilot  
**Created:** 2026-04-13  
**Supersedes:** —  
**Superseded by:** —

## Context

Strategy pages currently live at flat URLs like `/strategy-dividend-daddy/`.
The user wants a cleaner hierarchical URL scheme: `/strategy/dividend-daddy/`.

| Strategy | Current URL | New URL |
|----------|-------------|---------|
| Dividend Daddy | `/strategy-dividend-daddy/` | `/strategy/dividend-daddy/` |
| Moon Shot | `/strategy-moon-shot/` | `/strategy/moon-shot/` |
| Falling Knife | `/strategy-falling-knife/` | `/strategy/falling-knife/` |
| Over-Hyped | `/strategy-over-hyped/` | `/strategy/over-hyped/` |
| Institutional Whale | `/strategy-institutional-whale/` | `/strategy/institutional-whale/` |
| REIT Radar | `/strategy-reit-radar/` | `/strategy/reit-radar/` |

The overview page `/strategies/` is **unchanged**.

## Design Decision: Frontmatter `url` vs Directory Move

**Two options:**

1. **Directory move** — move `.md` files into `content/strategy/` directory.
   Creates a Hugo "section" at `/strategy/`, which auto-generates a list
   page that competes with the existing `/strategies/` overview. Requires
   an `_index.md` and possibly suppressing the auto-list. More structural.

2. **Frontmatter `url` override** — keep files where they are, add
   `url: /strategy/dividend-daddy/` to frontmatter. Hugo routes to the
   new URL. Add `aliases: ["/strategy-dividend-daddy/"]` for SEO redirects.
   No directory restructure.

**Chosen: Option 2 (frontmatter override).** Reasons:
- Minimal structural change — files stay as `strategy-*.md`
- Hugo `aliases` auto-generates redirect pages at old URLs (HTML meta-refresh)
- No risk of Hugo section auto-list conflicting with `/strategies/`
- zh-CN variants get the same treatment (`url: /zh-cn/strategy/...`)
- Easier to review and revert if needed

## Inventory of Changes

### Phase 1 — Content files (frontmatter updates)

12 files. Add `url` and `aliases` to frontmatter of each strategy page
(6 EN + 6 zh-CN).

| File | Add to frontmatter |
|------|--------------------|
| `content/strategy-dividend-daddy.md` | `url: "/strategy/dividend-daddy/"` + `aliases: ["/strategy-dividend-daddy/"]` |
| `content/strategy-dividend-daddy.zh-cn.md` | `url: "/zh-cn/strategy/dividend-daddy/"` + `aliases: ["/zh-cn/strategy-dividend-daddy/"]` |
| `content/strategy-moon-shot.md` | `url: "/strategy/moon-shot/"` + `aliases: ["/strategy-moon-shot/"]` |
| `content/strategy-moon-shot.zh-cn.md` | `url: "/zh-cn/strategy/moon-shot/"` + `aliases: ["/zh-cn/strategy-moon-shot/"]` |
| `content/strategy-falling-knife.md` | `url: "/strategy/falling-knife/"` + `aliases: ["/strategy-falling-knife/"]` |
| `content/strategy-falling-knife.zh-cn.md` | `url: "/zh-cn/strategy/falling-knife/"` + `aliases: ["/zh-cn/strategy-falling-knife/"]` |
| `content/strategy-over-hyped.md` | `url: "/strategy/over-hyped/"` + `aliases: ["/strategy-over-hyped/"]` |
| `content/strategy-over-hyped.zh-cn.md` | `url: "/zh-cn/strategy/over-hyped/"` + `aliases: ["/zh-cn/strategy-over-hyped/"]` |
| `content/strategy-institutional-whale.md` | `url: "/strategy/institutional-whale/"` + `aliases: ["/strategy-institutional-whale/"]` |
| `content/strategy-institutional-whale.zh-cn.md` | `url: "/zh-cn/strategy/institutional-whale/"` + `aliases: ["/zh-cn/strategy-institutional-whale/"]` |
| `content/strategy-reit-radar.md` | `url: "/strategy/reit-radar/"` + `aliases: ["/strategy-reit-radar/"]` |
| `content/strategy-reit-radar.zh-cn.md` | `url: "/zh-cn/strategy/reit-radar/"` + `aliases: ["/zh-cn/strategy-reit-radar/"]` |

### Phase 2 — Internal link updates (content files)

18 content files with hardcoded `/strategy-*` links. All instances of
`/strategy-X/` become `/strategy/X/` and `/zh-cn/strategy-X/` becomes
`/zh-cn/strategy/X/`.

| File | Refs | Description |
|------|------|-------------|
| `content/strategies.md` | 6 | Strategy overview page |
| `content/strategies.zh-cn.md` | 5 | zh-CN overview |
| `content/data.md` | 5 | Data overview page |
| `content/data.zh-cn.md` | 5 | zh-CN data page |
| `content/articles/top-stocks-by-strategy-march-2026.md` | 5 | Monthly roundup |
| `content/articles/practical-guide-to-stock-indicators.md` | 5 | Indicators article |
| `content/articles/southeast-asia-unicorn-tickerengine-grab.md` | 3 | GRAB article |
| `content/articles/hidden-tickers-in-earnings-transcripts.md` | 2 | Transcripts article |
| `content/glossary/52-week-high.md` | 2 | |
| `content/glossary/52-week-low.md` | 2 | |
| `content/glossary/beta.md` | 5 | |
| `content/glossary/dividend-yield.md` | 2 | |
| `content/glossary/market-cap.md` | 2 | |
| `content/glossary/moving-average-200.md` | 2 | |
| `content/glossary/moving-average-50.md` | 2 | |
| `content/glossary/pe-ratio.md` | 2 | |
| `content/glossary/rsi.md` | 6 | |
| `content/glossary/volume.md` | 2 | |

### Phase 3 — Layout/template updates

4 layout files with hardcoded strategy URL references.

| File | Refs | Notes |
|------|------|-------|
| `layouts/partials/navigation.html` | 6 | Dropdown hrefs |
| `layouts/tickers/single.html` | 12 | Links to strategy pages from ticker detail |
| `layouts/tickers/list.html` | 5 | Ticker browse page links |
| `layouts/page/strategy-filter.html` | 5 | Self-referencing cross-links |

### Phase 4 — Test updates

4 test files with hardcoded strategy URL paths.

| File | Refs |
|------|------|
| `tests/playwright/website-pages.spec.js` | 7 |
| `tests/playwright/i18n.spec.js` | 8 |
| `tests/playwright/datatables.spec.js` | 6 |
| `tests/playwright/pagination.spec.js` | 4 |

### Phase 5 — Docs/specs (non-critical, for accuracy)

4 docs files. These don't affect the live site but should be updated for
accuracy.

| File | Refs |
|------|------|
| `docs/specs/reit_radar_strategy.md` | 9 |
| `docs/specs/zhcn_content_backfill.md` | 6 |
| `docs/specs/cli_translate.md` | 2 |
| `docs/design/20260408_013203_UTC_i18n_architecture.md` | 1 |

### Phase 6 — Python pipeline (comments only)

`hugo_generators.py` has 5 comment references to `strategy-*.md`. These are
informational comments, not functional code. Update for accuracy.

### Not changed

- **JSON data files** (`strategy_*.json`) — filenames use underscores, not
  hyphens, and are loaded by `strategy_key` in templates. No URL dependency.
- **`temp/` directory** — scratch docs, not deployed. Ignore.
- **`hugo.toml`** — no strategy URL references.
- **`portfolio-extractor.js`** — references strategies by key, not URL.
- **`i18n-js.html`** — no URL references.

## SEO Redirect Strategy

Hugo `aliases` in frontmatter auto-generate an HTML file at the old URL path
containing a `<meta http-equiv="refresh">` redirect to the new URL. This
ensures:

- Existing bookmarks continue working
- Search engine crawlers follow the redirect and update their index
- No server-side redirect configuration needed (static site)

The redirect HTML also includes a `<link rel="canonical">` pointing to the
new URL, which tells search engines the new URL is authoritative.

## Verification Plan

### Pre-migration baseline

1. Build the site before changes
2. Capture list of all generated URLs: `find public/ -name index.html`
3. Save as `pre-migration-urls.txt`

### Post-migration checks

1. **Hugo build succeeds** — zero errors/warnings
2. **New URLs exist** — `public/strategy/dividend-daddy/index.html` etc.
3. **Redirects exist** — `public/strategy-dividend-daddy/index.html` contains
   `<meta http-equiv="refresh">`
4. **Zero broken links** — grep built HTML for any remaining
   `/strategy-dividend-daddy` links (should find zero, only redirects)
5. **URL inventory complete** — every old URL has a corresponding redirect
6. **Playwright tests pass** — updated paths resolve correctly
7. **zh-CN pages verified** — both `/zh-cn/strategy/X/` pages and
   `/zh-cn/strategy-X/` redirects exist

### Post-migration grep audit

```bash
# Should return ZERO results (no stale references in source)
grep -rn '/strategy-\(dividend\|moon\|falling\|over\|institutional\|reit\)' \
  hugo/site/content/ hugo/site/layouts/ hugo/site/static/js/ tests/ \
  --include='*.md' --include='*.html' --include='*.js' \
  | grep -v 'aliases:'
```

## Summary

- **38 source files** to update (12 content + 18 link updates + 4 layouts +
  4 tests = 38 functional; plus 5 docs for accuracy)
- **~134 individual references** to change
- **12 redirect pages** auto-generated by Hugo aliases
- **Approach**: frontmatter `url` override + `aliases` for redirects
- **Risk**: low — Hugo aliases are a first-class feature, links are
  mechanical find-replace, tests verify correctness
