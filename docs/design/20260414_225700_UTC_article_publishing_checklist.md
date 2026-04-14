# ADR: Article Publishing Checklist

**Status:** Accepted
**Author:** Andrew Allbright
**Created:** 2026-04-14

## Context

stockmarketwords.com has an article announcement banner system
(`hugo/site/static/js/article-banner.js`) that notifies visitors about the
latest published article. The banner is configured via `[params.latestArticle]`
in `hugo/site/hugo.toml` and is dismissable per-user via localStorage.

Currently, the requirement to update the banner when publishing a new article
is implicit — there is no documented process. This has led to a situation where
the banner could be stale (pointing to an old article) or simply forgotten when
new content is published.

## Decision

**Every time a new article is published, the author MUST update the article
announcement banner configuration in `hugo/site/hugo.toml`.**

### Required steps when publishing a new article

1. **Create the article** markdown file in `hugo/site/content/articles/`.

2. **Update the banner** in `hugo/site/hugo.toml`:
   ```toml
   [params.latestArticle]
   title = "Your New Article Title Here"
   url = "/articles/your-new-article-slug/"
   expirationDays = 7
   ```

3. **Add the article** to the E2E test page list in
   `tests/puppeteer/website-pages.e2e.test.js` (add to the `PAGES` array).

4. **Verify locally** that the banner appears:
   - Run `cd hugo/site && hugo server`
   - Open `http://localhost:1313/` in a private/incognito window
   - Confirm the banner shows with the correct title and link
   - Confirm clicking the link navigates to the new article
   - Confirm the dismiss button works

5. **Clear stale dismissals** (if testing after a previous banner):
   - Open browser console and run `clearAllArticleBannerDismissals()`

### Banner behavior reference

- Banner is hidden by default (CSS class `hidden`) and shown by JS when config
  is present and not dismissed.
- Dismissal is stored in localStorage with keys:
  - `articleBannerDismissed_{url}` — boolean flag
  - `articleBannerExpiration_{url}` — expiration timestamp
- Banner auto-expires after `expirationDays` (default: 7).
- Clicking the article link also dismisses the banner.

## Consequences

- New articles will always be surfaced to visitors via the banner.
- The banner config serves as a single source of truth for "what's the latest
  article" — useful for both the UI and for auditing.
- Authors must remember this step; PR reviewers should check for it when an
  article is added.

## Status

Accepted — this process applies to all articles published after this date.
