# Ticker Lookup in Navigation Bar

**Status:** Done
**Author:** Andrew Allbright
**Created:** 2026-04-24
**Supersedes:** —
**Superseded by:** —
**Depends on:** [`ticker_lookup_enhancements.md`](./ticker_lookup_enhancements.md) — must be
merged first (provides `ticker-lookup.js` and `ticker-lookup.json`)

## Context

The ticker lookup tool (autocomplete, not-found feedback, recent lookups)
currently only appears on the home page. Every other page — ticker detail
pages, strategy pages, article pages — offers no quick way to jump to a
different ticker without returning to the home page first. This is especially
frustrating on ticker detail pages where a user has finished reading about
one stock and wants to look up another.

The home-page implementation is self-contained in `ticker-lookup.js`, which
is hardcoded to `#ticker-lookup-form` / `#ticker-lookup-input`. This spec
adds a second, navigation-bar instance of the same widget while refactoring
the shared code so zero logic is duplicated.

## Goal

A fully-featured ticker lookup widget lives in the site-wide navigation bar.
On desktop (≥lg breakpoint) it renders as a compact inline form in the
expanded navbar. On mobile it renders as a full-width input block inside the
hamburger menu. Both share identical search, validation, and recent-lookups
logic with the home-page widget.

## Non-goals

- Adding the lookup to any other location (footer, sidebar, etc.).
- Showing ticker preview cards in the nav dropdown (autocomplete shows
  symbol + name; a full preview card is too large for a nav context).
- A "search results page" — the widget always navigates directly to
  `/tickers/{symbol}/`.
- Separate HTML nodes for desktop and mobile — one form node, CSS
  handles both breakpoints.
- Fuzzy search (same non-goal as the home-page spec).
- Changing the home-page widget's UX (persistent chips below the form,
  below-form error div) — it stays as-is.

## User stories

- As a user reading a ticker page for `AAPL`, I want to type "NVDA" in
  the nav and jump straight to NVDA's page without navigating back to
  the home page.
- As a mobile user, I want to find the search input inside the hamburger
  menu so I can look up a ticker even on a small screen.
- As a returning user, I want to see my recent lookups as chips in the
  nav dropdown when I focus the input without typing, so I can re-visit
  tickers with one tap.

## Design

### Code sharing: multi-instance `ticker-lookup.js`

The `initTickerLookup(config)` function (a new named export from the
IIFE) is the single entry point for both widgets:

```js
initTickerLookup({
  formId:    'ticker-lookup-form',         // home page (existing IDs)
  inputId:   'ticker-lookup-input',
  errorId:   'ticker-lookup-error',
  recentId:  'ticker-recent-lookups',
  compact:   false,                        // home page: full-feature mode
});

initTickerLookup({
  formId:    'nav-ticker-lookup-form',     // nav bar
  inputId:   'nav-ticker-lookup-input',
  compact:   true,                         // nav: compact mode (see below)
});
```

The `loadData()` / `filterTickers()` / `saveRecent()` / `getRecents()`
functions are called by both instances from a single shared closure.
The fetch fires at most once regardless of how many instances are
initialised.

### Compact mode (nav widget behaviour)

When `compact: true` the widget differs from the home-page version in
two ways:

| Behaviour | Home page (full) | Nav bar (compact) |
|---|---|---|
| **Error display** | `alert-warning` div below the form | "Not found" row at top of autocomplete dropdown |
| **Recent lookups** | Persistent chips below the form, always visible after first lookup | Chips shown *inside* the dropdown when input is focused with an empty query |

Everything else — filtering, keyboard nav, validation, localStorage key,
max-recent count — is identical.

#### Compact dropdown layout

When focused with an empty query (and recents exist):

```
┌──────────────────────────────────┐
│ 🕐  Recent                       │
│   AAPL                           │
│   NVDA                           │
│   MSFT                           │
└──────────────────────────────────┘
```

When typing (any query):

```
┌──────────────────────────────────┐
│  AAPL   Apple Inc.               │
│  AAPLX  (name match)             │
│  ...                             │
└──────────────────────────────────┘
```

When submitting an unknown symbol:

```
┌──────────────────────────────────┐
│ ⚠  "XYZ" was not found          │
└──────────────────────────────────┘
```

The dropdown auto-closes after ~3 seconds for the "not found" case.

### Navigation template changes

**File:** `hugo/site/layouts/partials/navigation.html`

Add the compact lookup form inside `#navbarNav`, before the language
switcher `<li>`:

```html
<!-- Ticker lookup (compact, nav-bar widget) -->
<li class="nav-item d-flex align-items-center ms-lg-2">
  <form id="nav-ticker-lookup-form" class="d-flex gap-1"
        role="search" aria-label="Look up a ticker">
    <div style="position:relative;">
      <input type="text"
             id="nav-ticker-lookup-input"
             class="form-control form-control-sm"
             placeholder="{{ i18n "nav_lookup_placeholder" }}"
             autocomplete="off"
             autocapitalize="characters"
             style="width:7rem;">
    </div>
    <button type="submit" class="btn btn-outline-light btn-sm">
      {{ i18n "nav_lookup_btn" }}
    </button>
  </form>
</li>
```

Notes:
- `ms-lg-2` adds left margin only on desktop so it sits a bit apart from
  the nav links.
- The input is `7rem` wide on desktop (fits ~8 chars comfortably). On
  mobile it fills the full collapsed-menu width automatically because
  the `<li>` becomes a block.
- `btn-outline-light` matches the `navbar-dark` palette (white border,
  white text on dark background).
- On mobile (<lg) the `<li>` and its form are block-level inside the
  hamburger; padding comes from Bootstrap's `navbar-nav` context.

### Dropdown positioning

On **desktop**: the dropdown must appear below the input, which is
inside the fixed top navbar. The dropdown wrapper (`position:relative`
already on the inner `<div>`) and `z-index:1050` (same as home page)
are sufficient.

On **mobile**: the navbar collapse sits in normal document flow; the
dropdown will appear inline below the input, which is the correct
behaviour.

### i18n additions

**File:** `hugo/site/i18n/en.toml`

```toml
[nav_lookup_placeholder]
other = "Ticker symbol…"

[nav_lookup_btn]
other = "Go"
```

**File:** `hugo/site/i18n/zh-cn.toml`

```toml
[nav_lookup_placeholder]
other = "股票代码…"

[nav_lookup_btn]
other = "查找"
```

### Script loading

`ticker-lookup.js` is already loaded on the home page by `index.html`
and the shortcode. For every other page it must be loaded via the base
layout.

**File:** `hugo/site/layouts/baseof.html` (or whichever file renders
`<head>` / end-of-body for all pages)

```go-html
{{/* Ticker lookup — loaded on all pages for the nav widget */}}
<script>
  window.SITE_BASE_URL = window.SITE_BASE_URL || '{{ .Site.BaseURL }}';
  window.SITE_LANG    = window.SITE_LANG    || '{{ .Site.Language.Lang }}';
</script>
<script src="{{ .Site.BaseURL }}js/ticker-lookup.js" defer></script>
```

The `||` guards prevent double-assignment on the home page where the
variables are already set by `index.html`.

## Affected files

| File | Change |
|------|--------|
| `hugo/site/static/js/ticker-lookup.js` | Refactor to multi-instance via `initTickerLookup(config)`; add compact mode |
| `hugo/site/layouts/partials/navigation.html` | Add compact lookup form `<li>` |
| `hugo/site/layouts/baseof.html` | Load `ticker-lookup.js` on all pages |
| `hugo/site/i18n/en.toml` | Add `nav_lookup_placeholder`, `nav_lookup_btn` |
| `hugo/site/i18n/zh-cn.toml` | Add same keys in Chinese |
| `hugo/site/layouts/index.html` | Guard against double script load |
| `hugo/site/layouts/shortcodes/ticker-portfolio-extraction-tool.html` | Guard against double script load |
| `tests/playwright/ticker-lookup-nav.spec.js` | New E2E tests for nav widget |
| `tests/playwright/ticker-lookup.spec.js` | Verify home-page widget unaffected by refactor |

## Verification

### Manual

1. `hugo server` → any non-home page (e.g. `/tickers/aapl/`) → type
   "NVDA" in the nav input → autocomplete dropdown appears → press Enter
   → navigates to `/tickers/nvda/`.
2. Same page → type "ZZZZZ" → submit → "not found" row appears in
   dropdown → auto-closes after ~3s, no navigation.
3. Look up "AAPL" via nav → reload → focus nav input without typing →
   dropdown shows "Recent" section with AAPL chip.
4. Resize to mobile → open hamburger → lookup input appears full-width
   as a block item → same features work.
5. Home page → both the nav widget and the home-page card widget work
   independently (separate form IDs, shared data).
6. zh-CN home page (`/zh-cn/`) → nav placeholder shows "股票代码…".

### Automated

New file: `tests/playwright/ticker-lookup-nav.spec.js`

- **Test 1** — Nav autocomplete by symbol: type "AAPL" in
  `#nav-ticker-lookup-input` → dropdown appears, contains "AAPL".
- **Test 2** — Nav autocomplete by name: type "microsoft" →
  dropdown contains at least one result.
- **Test 3** — Nav invalid ticker: type "ZZZZZZ" → submit → "not
  found" message visible in dropdown; URL unchanged.
- **Test 4** — Nav recent lookups on focus: pre-populate localStorage
  `smw-recent-tickers` via `page.evaluate`, reload, focus
  `#nav-ticker-lookup-input` without typing → recent section visible.
- **Test 5** — Nav present on non-home page: navigate to
  `/tickers/aapl/` → `#nav-ticker-lookup-input` is visible.
- **Test 6** — Mobile hamburger: set viewport to 375×667 → hamburger
  button visible → click it → `#nav-ticker-lookup-input` becomes
  visible.

### Regression

- Run `npm run test:e2e` — all existing tests (including
  `ticker-lookup.spec.js` home-page tests) pass.

## Open questions

1. **Nav input width on desktop.** `7rem` fits ~8 characters which is
   sufficient for all symbols (max 5 chars) and short company-name
   searches. Should the input expand on focus? **Default:** no — keep it
   fixed to avoid layout shift. Revisit if users complain.

2. **Nav widget on home page.** The home page will now have two lookup
   widgets (nav + card). Is this confusing? **Default:** acceptable —
   the card widget has additional context (subtitle, browse link, recent
   chips) that makes it feel distinct from the small nav input.

3. **Script load on home page guard.** Both `index.html` and `baseof.html`
   will attempt to load `ticker-lookup.js`. The `||` guard on the globals
   prevents double-initialisation, but a second `<script>` tag will still
   be emitted. **Default:** use Hugo's `Scratch` / page-level flag to
   suppress the baseof load when `index.html` already loaded it — same
   pattern already used for `portfolio-extractor.js`.

## Alternatives considered

- **Two separate DOM nodes (one hidden per breakpoint)** — common
  pattern but doubles the HTML, doubles the event listeners, and requires
  keeping two input values in sync. Rejected in favour of one node +
  Bootstrap responsive utilities.
- **Search icon that opens a full-width overlay panel** — polished UX
  (used by many e-commerce sites) but significantly more JS complexity
  for diminishing benefit on a site with ≤6 nav items. Deferred as a
  future enhancement.
- **Dedicated `/search/` page** — would support richer results (showing
  metrics inline) but breaks the "one-click jump" flow. Not aligned with
  the site's single-page-per-ticker information architecture.
