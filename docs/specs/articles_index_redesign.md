# Articles Index Page Redesign

**Status:** Draft
**Author:** Andrew Allbright
**Created:** 2026-04-14
**Supersedes:** —
**Superseded by:** —

## Context

The `/articles/` page is built from a hand-curated `_index.md` plus the
default `section.html` template. This creates several problems:

1. **Every article appears twice** — once in the hand-curated markdown, once
   in the auto-generated `{{ range .Pages }}` list at the bottom.
2. **Hand-curated listings are a maintenance burden** — adding a new article
   requires editing `_index.md` in addition to creating the article file.
   Categories and descriptions in the listing can drift from actual frontmatter.
3. **Article descriptions are wasted** — most articles have good `description`
   frontmatter that never shows on the index page.
4. **No real dates** — just parenthetical "April 2026" text on some items.
5. **No visual hierarchy** — everything is bullet points. The latest article
   looks the same as the oldest.
6. **"Last updated: April 14, 2026"** in a blockquote is manual and fragile.
7. **zh-CN `_index.zh-cn.md` is stale** — generic intro paragraph with no
   article links.

Additionally, no article currently uses `tags` in its frontmatter, so there
is no machine-readable categorization.

## Goal

The articles index page auto-generates from article frontmatter so that
publishing a new article requires only creating the `.md` file (no edits to
`_index.md`). The page features the newest article prominently, shows titles
with dates and descriptions, and groups articles by tag.

## Non-goals

- Pagination (only 9 articles; not needed yet)
- Search/filter functionality
- RSS feed changes (Hugo generates this automatically)
- Changing individual article layouts (`articles/single.html`)
- Adding images/thumbnails to article cards (no article has a `cover` image)

## User stories

- As a visitor, I want to see what articles exist at a glance — with titles,
  dates, and one-sentence descriptions — so I can decide what to read.
- As a site author, I want adding a new article to automatically update the
  index page, so I don't have to maintain a separate listing.
- As a zh-CN visitor, I want the articles index to show article titles and
  descriptions (even if in English) rather than a stale generic paragraph.

## Design

### 1. Add `tags` frontmatter to all articles

Each article gets a `tags` list that maps to the categories currently in
`_index.md`. The tag taxonomy is:

| Tag                    | Articles                                              |
|------------------------|-------------------------------------------------------|
| `global-trade`         | strait-of-malacca-trade-and-tickers                   |
| `regional-analysis`    | southeast-asia-unicorn-tickerengine-grab               |
| `extraction-engine`    | how-ticker-extraction-works                            |
| `using-the-tool`       | how-to-extract-tickers-from-financial-news, hidden-tickers-in-earnings-transcripts |
| `strategy`             | how-to-read-the-five-strategies, top-stocks-by-strategy-march-2026 |
| `indicators`           | practical-guide-to-stock-indicators, why-some-tickers-have-no-scores |

An article can have multiple tags. Tags are defined in frontmatter as:
```yaml
tags: ["global-trade", "regional-analysis"]
```

### 2. Add missing `description` frontmatter

Two articles lack descriptions:
- `how-ticker-extraction-works.md`
- `how-to-read-the-five-strategies.md`

These need descriptions added so the index page can display them.

### 3. Create `layouts/articles/list.html`

A dedicated list template for the articles section, replacing the generic
`_default/section.html`. Uses Bootstrap 5 cards and Hugo's page collection.

**Layout structure:**

```
┌─────────────────────────────────────────────┐
│ <h1> Articles </h1>                         │
│ <p> One-line intro from _index.md .Content  │
├─────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐ │
│ │  ★ FEATURED (latest article)            │ │
│ │  Title (large)                          │ │
│ │  Date · Author                          │ │
│ │  Full description                       │ │
│ │  [Read →] button                        │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ <h2> Tag Group: Global Trade & Shipping     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│ │ Card     │ │ Card     │ │ Card     │     │
│ │ Title    │ │ Title    │ │ Title    │     │
│ │ Date     │ │ Date     │ │ Date     │     │
│ │ Desc     │ │ Desc     │ │ Desc     │     │
│ └──────────┘ └──────────┘ └──────────┘     │
│                                             │
│ <h2> Tag Group: Strategy & Scoring          │
│ ┌──────────┐ ┌──────────┐                   │
│ │ Card     │ │ Card     │                   │
│ └──────────┘ └──────────┘                   │
│ ...                                         │
└─────────────────────────────────────────────┘
```

**Key behaviors:**
- Featured card = `.Pages.ByDate.Reverse` first item (newest by `date`)
- Remaining articles grouped by their first tag
- Tag display names are defined in a lookup map in the template
- Each card shows: title (linked), date (formatted), description
- Cards use `col-md-6` grid (2 per row on desktop, 1 on mobile)
- Featured card is full-width with a distinct background (`bg-light`)
- The latest article appears **only** in the featured section, not again
  in its tag group, to avoid duplication

### 4. Simplify `_index.md`

Replace the current hand-curated listing with a minimal intro:

```markdown
---
title: "Articles"
description: "Original articles about stock tickers, investment strategies, and global trade."
---

Original articles about the extraction engine, strategy logic, global trade,
and how to use the site's data.
```

Everything else is auto-generated by the template.

### 5. Update `_index.zh-cn.md`

```markdown
---
title: "专栏文章"
description: "关于股票代码、投资策略和全球贸易的原创文章。"
---

深入了解 Stock Market Words 的工作原理、策略解读和实用指南。
```

The template renders the same auto-generated cards for both languages.
Article titles/descriptions will be in English (since individual articles
aren't translated yet), which is expected per the i18n fallback ADR.

### 6. Tag display name map

In the template, a dict maps tag slugs to display names:

| Slug                | English display         | zh-CN display (future) |
|---------------------|------------------------|------------------------|
| `global-trade`      | Global Trade & Shipping | 全球贸易与航运          |
| `regional-analysis` | Regional Analysis       | 区域分析               |
| `extraction-engine` | The Extraction Engine   | 提取引擎               |
| `using-the-tool`    | Using the Tool          | 工具使用               |
| `strategy`          | Strategy & Scoring      | 策略与评分             |
| `indicators`        | Understanding Indicators| 理解指标               |

For now, only English names are needed. zh-CN names can be added to Hugo's
i18n files when the content backfill spec is implemented.

### 7. Tag group ordering

Tag groups appear in a fixed order defined in the template (not alphabetical),
so we control editorial flow:

1. Global Trade & Shipping
2. Regional Analysis
3. Using the Tool
4. The Extraction Engine
5. Strategy & Scoring
6. Understanding Indicators

## Affected files

| Action  | File                                                   |
|---------|--------------------------------------------------------|
| Create  | `hugo/site/layouts/articles/list.html`                 |
| Modify  | `hugo/site/content/articles/_index.md`                 |
| Modify  | `hugo/site/content/articles/_index.zh-cn.md`           |
| Modify  | `hugo/site/content/articles/strait-of-malacca-trade-and-tickers.md` (add tags) |
| Modify  | `hugo/site/content/articles/southeast-asia-unicorn-tickerengine-grab.md` (add tags) |
| Modify  | `hugo/site/content/articles/how-ticker-extraction-works.md` (add tags, description) |
| Modify  | `hugo/site/content/articles/how-to-extract-tickers-from-financial-news.md` (add tags) |
| Modify  | `hugo/site/content/articles/hidden-tickers-in-earnings-transcripts.md` (add tags) |
| Modify  | `hugo/site/content/articles/how-to-read-the-five-strategies.md` (add tags, description) |
| Modify  | `hugo/site/content/articles/top-stocks-by-strategy-march-2026.md` (add tags) |
| Modify  | `hugo/site/content/articles/practical-guide-to-stock-indicators.md` (add tags) |
| Modify  | `hugo/site/content/articles/why-some-tickers-have-no-scores.md` (add tags) |

## Verification

- **Manual — no duplication:** Open `http://localhost:1313/articles/` and
  confirm every article title appears exactly once (plus the featured card).
- **Manual — auto-generation:** Remove `_index.md` content below the
  frontmatter. Confirm all articles still appear (template drives the listing).
- **Manual — featured article:** Confirm the newest article by `date` appears
  in the featured card at the top.
- **Manual — tag groups:** Confirm articles are grouped under their correct
  tag headings.
- **Manual — card content:** Each card shows title (linked), date, and
  description.
- **Manual — zh-CN:** Open `http://localhost:1313/zh-cn/articles/` and
  confirm the same layout renders (with Chinese section title).
- **Manual — mobile:** Resize to mobile width. Cards should stack to single
  column.
- **Hugo build:** `hugo -s hugo/site` completes with no errors or warnings.
- **Existing E2E tests:** `npm run test:e2e:pages` still passes (the
  `/articles/` page is in the PAGES array).

## Open questions

1. **Should tags generate their own taxonomy pages (e.g., `/tags/global-trade/`)?**
   Default: No. Hugo generates these automatically when `tags` taxonomy is
   enabled (which it is by default), but we won't link to them from the
   articles index. We can revisit if we want tag-based browsing later.

2. **Should the featured card have a distinct color or just `bg-light`?**
   Default: `bg-light` with a subtle border. Keep it simple.

## Alternatives considered

**Alternative A: Keep hand-curated `_index.md`, just fix the duplication.**
Rejected because it doesn't solve the maintenance burden. Every new article
still requires editing two files.

**Alternative B: Flat chronological list (no tag groups).**
Simpler template, but with 9 articles spanning different topics, grouping
helps scanability. As the article count grows, this becomes more important.

**Alternative C: Use Hugo's built-in taxonomy list pages.**
Hugo can generate `/tags/<tag>/` pages automatically, but we want a single
curated index, not scattered tag pages. The taxonomy system is overkill for
a flat index with visual grouping.
