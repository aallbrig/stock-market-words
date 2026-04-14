# Welcome Banner

**Status:** Done
**Supersedes:** [`localization_banner.md`](localization_banner.md)
**Author:** Copilot
**Created:** 2026-04-14
**Completed:** 2026-04-14

## Context

The site previously displayed a localization-progress banner ("🌍 Working toward full Chinese support — some pages may still appear in English.") on every page. As the site matures and targets a broader audience beyond zh-CN localization, this messaging no longer reflects the site's primary value proposition. The banner real estate is better used for a GTM-oriented welcome message that communicates what the site does and builds trust with first-time visitors.

## Goal

Repurpose the existing sitewide dismissable banner from a localization notice to a social-proof welcome message that:

1. Communicates the site's scale and value proposition in one line.
2. Resets the dismiss state so all existing users see the new message.
3. Preserves all existing banner infrastructure (CSS, dismiss UX, localStorage persistence).

## Non-goals

- Renaming CSS classes or HTML IDs (reuse existing `.localization-banner` structure to minimize churn).
- Adding a CTA link or button to the banner.
- Per-locale banner text (same message globally).
- Changing banner styling or positioning.

## Design

### New banner text

```
📈 Analyzing 3,000+ tickers daily — free strategy scores, market data, and a ticker extraction tool. No account required.
```

**Rationale:** Option 2 (Social Proof) was chosen from four candidates:

| Option | Message | Tone |
|--------|---------|------|
| 1 — Value Prop | "Free stock ticker extraction — paste any text, instantly find every ticker…" | Informative |
| **2 — Social Proof** ✓ | "Analyzing 3,000+ tickers daily — free strategy scores… No account required." | Authoritative |
| 3 — CTA-Driven | "Try it now — paste a news article and we'll extract every stock ticker…" | Action-oriented |
| 4 — Tagline | "Stock Market Words — find the tickers hidden in any text." | Minimal |

Social proof was selected because it leads with scale ("3,000+ tickers"), reduces friction ("no account required"), and builds trust for first-time visitors arriving from search or referral.

### Versioned localStorage key

The old banner used `localizationBannerDismissed`. Users who dismissed the old banner would never see the new message. The fix is a versioned key:

- **Old key:** `localizationBannerDismissed`
- **New key:** `bannerDismissed_v2-welcome`

When the banner message changes in the future, bump the version string (e.g., `v3-promo`) so all users see the new message. Old keys are harmlessly orphaned in localStorage.

## Files Changed

| File | Action |
|------|--------|
| `hugo/site/layouts/_default/baseof.html` | Edit — update banner text |
| `hugo/site/static/js/localization-banner.js` | Edit — versioned localStorage key |

## Verification

1. `cd hugo/site && hugo server` — banner appears with new text on all pages.
2. Users who previously dismissed the old banner will see the new one (different localStorage key).
3. Clicking ✕ dismisses the banner; it stays dismissed across page loads.
4. Mobile responsive behavior unchanged (inherits existing CSS).
