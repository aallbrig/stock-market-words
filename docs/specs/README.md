# Feature Specs

This directory holds **per-feature specs** for stockmarketwords.com. Specs
are written *before* the implementation and serve as the contract between
whoever scoped the work and whoever implements it.

A spec is the right tool when:

- The work touches more than one file or subsystem.
- There are multiple plausible approaches and you need to pick one explicitly.
- A future agent (human or LLM) might need to pick up the work mid-stream.
- Acceptance criteria need to be unambiguous before coding starts.

A spec is **not** the right tool for typo fixes, single-line changes, or
trivial refactors. Just do those.

## How specs are organized

- One spec per feature, in its own file.
- Filename convention: `<slug>.md` (simple slug, no timestamp). Keep names
  short and descriptive (e.g., `zhcn_content_backfill.md`).
- Specs are immutable once "Accepted" — substantive changes go in a new spec
  that supersedes the old one (link them in the frontmatter via the "Supersedes" 
  and "Superseded by" fields).

## Spec template

Copy this when starting a new spec.

```markdown
# <Feature title>

**Status:** Draft | Accepted | In progress | Done | Superseded
**Author:** <name>
**Created:** YYYY-MM-DD
**Supersedes:** (optional link to previous spec)
**Superseded by:** (optional link)

## Context

Why is this work being done? What is the user-visible problem or the
internal pain point? Link to any prior research notes, bugs, or related
specs. One or two paragraphs — assume the reader has read
`docs/design/architecture_overview.md` but nothing else about this feature.

## Goal

One sentence: what does "done" look like from a user's perspective?

## Non-goals

Bullet list of things this spec is explicitly *not* doing. Drawing this
boundary is often the most useful part of the spec.

## User stories

- As a <user type>, I want to <action> so that <outcome>.
- (Add as many as needed; usually 1–3.)

## Design

The recommended approach. Pick one — alternatives go in an "Alternatives
considered" section, not here. Be specific about:

- New files to create (with full paths)
- Existing files to modify (with full paths and the relevant function or
  section names)
- Existing utilities to reuse (with paths)
- Data shapes (JSON schemas, DB columns, function signatures)
- External dependencies (new packages, CDNs, services)

## Affected files

A short, scannable list of every file the implementation will touch.
Useful as a sanity-check at PR review time.

## Verification

How will we know it works? List the concrete checks:

- Manual: "Open `http://localhost:1313/zh-cn/tickers/crm/` and confirm 200 + Chinese labels"
- Automated: which test file gets a new test, and what does it assert
- Data: any DB query or JSON inspection that should pass

## Open questions

Anything still ambiguous when the spec was written. Each question should
have a default answer so the implementer is unblocked, with a note that
the default can be revisited.

## Alternatives considered

(Optional) The other paths you considered and why you rejected them.
Helps the next person understand the decision.
```

## Lifecycle

1. **Draft** — being written, not ready for implementation. Anyone can edit.
2. **Accepted** — author + at least one reviewer have signed off. Implementation can start.
3. **In progress** — someone is actively building it. Add a link to the PR.
4. **Done** — merged and verified per the spec's verification section.
5. **Superseded** — replaced by a newer spec. Keep the file for history; add a `Superseded by:` link in the frontmatter.

## Existing specs

- [zh-CN content backfill](./zhcn_content_backfill.md)
- [zh-CN ticker pages](./zhcn_ticker_pages.md)
- [Extract Tickers analytics](./extract_tickers_analytics.md)
- [CLI: ticker-cli translate](./cli_translate.md) — parallel translation job system with SQLite heuristics
- [Dividend Withholding Tax Calculator](./dividend_withholding_tax.md) — Tax-Smart Yield card for non-US investors
- [SGX Ticker Support](./sgx_ticker_support.md) — Singapore Exchange tickers in pipeline and extraction engine
- [REIT Radar Strategy](./reit_radar_strategy.md) — 6th investment strategy purpose-built for REIT investors
- [Strait of Malacca Article](./strait_of_malacca_article.md) — editorial article linking 53 tickers to Malacca Strait trade flows
- [Articles Index Redesign](./articles_index_redesign.md) — auto-generated articles page from frontmatter, replacing hand-curated listing
- [Daily Automation](./daily_automation.md) — systemd timer, bot commits, install/verify scripts, S3 backup
- [VPN IP Rotation](./vpn_ip_rotation.md) — PIA VPN rotation for Yahoo Finance rate-limit mitigation
- [Ticker Strategy History Chart](./ticker_strategy_history_chart.md) — 10-day strategy score line chart on ticker pages, Hugo-flag gated
- [Sparkline ↔ Delta Chip Sync](./sparkline_delta_sync.md) — hover a sparkline point to update the delta chip dynamically, event-driven and decoupled
- [Ticker Lookup Enhancements](./ticker_lookup_enhancements.md) — autocomplete by symbol/name, not-found feedback, recent lookups chips
- [Ticker Lookup in Navigation Bar](./ticker_lookup_nav.md) — compact nav-bar widget on all pages, multi-instance refactor of ticker-lookup.js
