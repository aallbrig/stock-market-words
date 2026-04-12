# REIT Radar UI Polish

**Status:** Draft  
**Author:** Copilot  
**Created:** 2026-04-12  
**Supersedes:** —  
**Superseded by:** —

## Context

After deploying the REIT Radar strategy (6th strategy), three UI issues were
identified during local testing:

1. **Stale "5 Strategy Portfolios" label** — The home page extraction tool
   heading still reads "🎯 5 Strategy Portfolios". The i18n key
   `home_strategy_portfolios` was missed during the five→six sweep.

2. **Double emoji on Portfolio Visualizer button** — The `js_view_portfolio`
   i18n string contains `📊` *and* the JS template literal in
   `portfolio-extractor.js` line 631 also prepends `📊`, resulting in
   `📊 📊 View in Portfolio Visualizer`.

3. **Redundant Sector Distribution chart on REIT Radar page** — Because REIT
   Radar only scores REITs, the sector pie chart is a single-color circle
   showing "Real Estate: 150 (100.0%)". This adds no analytical value and
   wastes vertical space.

## Proposed Changes

### Fix 1 — Update strategy count in i18n

| File | Key | Old | New |
|------|-----|-----|-----|
| `hugo/site/i18n/en.toml` | `home_strategy_portfolios` | `🎯 5 Strategy Portfolios` | `🎯 6 Strategy Portfolios` |
| `hugo/site/i18n/zh-cn.toml` | `home_strategy_portfolios` | `🎯 5种策略投资组合` | `🎯 6种策略投资组合` |

### Fix 2 — Remove duplicate emoji from Portfolio Visualizer button

**Option chosen:** Remove the emoji from the i18n strings (keep it in JS)
since the JS already prepends `📊`. This keeps the i18n string as pure text,
consistent with how other JS-rendered strings work (strategy names already
carry their own emojis in the i18n key, but `view_portfolio` is used inline
with a hardcoded emoji prefix).

Actually — the cleaner fix is the opposite: **remove the emoji from the JS
template** and keep it in the i18n string, since all other JS strings use
`T('key')` without prepending anything. The emoji belongs in the translation.

| File | Change |
|------|--------|
| `hugo/site/static/js/portfolio-extractor.js` line 631 | Remove `📊 ` prefix before `${T('view_portfolio')}` |

### Fix 3 — Hide sector chart for REIT Radar

The strategy-filter template already has access to `$strategyKey` (from
`.Params.strategy_key`). Add a conditional to skip the sector distribution
block when `$strategyKey == "reit_radar"`.

| File | Change |
|------|--------|
| `hugo/site/layouts/page/strategy-filter.html` line 40 | Wrap sector chart block with `{{ if ne $strategyKey "reit_radar" }}` |

An alternative would be a generic "hide when ≤1 sector" check in JS, but that
requires runtime logic. The Hugo template conditional is simpler and
deterministic.

## Files Changed

1. `hugo/site/i18n/en.toml` — Fix 1
2. `hugo/site/i18n/zh-cn.toml` — Fix 1
3. `hugo/site/static/js/portfolio-extractor.js` — Fix 2
4. `hugo/site/layouts/page/strategy-filter.html` — Fix 3

## Verification

- Hugo build succeeds
- Home page shows "6 Strategy Portfolios"
- Portfolio Visualizer button shows single emoji
- REIT Radar strategy page has no sector chart section
- Other strategy pages still show sector charts normally
