# ADR: Ad Placement in Articles

**Status:** Accepted
**Author:** Andrew Allbright
**Created:** 2026-04-14

## Context

stockmarketwords.com uses Google AdSense for monetization. The article layout
template (`hugo/site/layouts/articles/single.html`) currently places a single
ad unit **after** article content, before the author footer. This is the
`adSlotArticle` slot.

For longer articles (3,000+ words), a single bottom-of-article ad has poor
viewability — many readers never scroll to the end. Industry best practice for
long-form content is to place one ad mid-article (after 40-60% of content) in
addition to the end-of-article placement.

## Decision

**Every article MUST include at least one ad placement. Long articles (2,000+
words) SHOULD include a mid-article ad in addition to the automatic
end-of-article ad.**

### Implementation

1. **End-of-article ad (automatic):** The article layout template already
   renders `ad-unit.html` with `adSlotArticle` after `{{ .Content }}`. This
   requires no author action — it is always present.

2. **Mid-article ad (manual via shortcode):** Authors place the `article-ad`
   shortcode at a natural section break roughly 40-60% through the article:

   ```markdown
   ## Previous Section

   Content here...

   {{</* article-ad */>}}

   ## Next Section

   More content...
   ```

3. **Ad slot reuse:** Both placements use the same `adSlotArticle` slot ID.
   AdSense handles deduplication and fill rate automatically. If a separate
   mid-article slot is needed in the future, add a new `adSlotArticleMid`
   parameter to `hugo.toml`.

4. **Local development:** Ads only render when both `googleAdSenseId` and
   `adSlotArticle` are set (via environment variables in production). Local
   development sees no ads — this is by design.

### Optimal placement guidelines

| Article length | Ad placements |
|---|---|
| < 1,000 words | End-of-article only (automatic) |
| 1,000 – 2,000 words | End-of-article only (automatic) |
| 2,000+ words | Mid-article shortcode + end-of-article (automatic) |

### Where to place the mid-article ad

- After a major section break (between `##` headings)
- After the reader has received substantial value (not in the first 30%)
- Before the article's "payoff" section (ticker table, conclusions)
- Never inside a table, code block, or chart

## Affected files

- `hugo/site/layouts/shortcodes/article-ad.html` — **new** shortcode
- `hugo/site/layouts/partials/ad-unit.html` — existing (no changes)
- `hugo/site/layouts/articles/single.html` — existing (no changes)
- Article markdown files — authors add `{{</* article-ad */>}}` as needed

## Consequences

- Long articles get better ad viewability without degrading reading experience.
- Authors have explicit control over mid-article placement.
- The shortcode is a no-op in local development (no visual clutter).
- PR reviewers should verify ad placement in new articles follows the
  guidelines above.

## Status

Accepted — applies to all articles published after this date.
