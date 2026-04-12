# Dividend Withholding Tax Calculator

**Status:** Draft  
**Author:** Copilot  
**Created:** 2026-04-12  
**Supersedes:** —  
**Superseded by:** —

## Context

Singaporean investors buying US-listed dividend stocks face a **30% US
withholding tax (WHT)** on dividends — the single biggest "surprise cost" for
non-US investors. Filing IRS Form W-8BEN (available through all major SG
brokers) reduces this to **15%** under the US-Singapore tax treaty.

stockmarketwords.com already displays `dividendYield` on every ticker detail
page, but this is the **gross** yield — the number a US investor receives. A
Singaporean investor's effective yield is 15–30% lower, which can turn a
seemingly attractive 4% yield into a mediocre 2.8% after tax.

No calculation, no education, no toggle exists today. This is the
lowest-hanging fruit to make the site immediately valuable for non-US
investors.

## Goal

Every ticker detail page shows **effective dividend yield after withholding
tax**, with a toggle for W-8BEN status, so that Singaporean (and other
non-US) investors see the yield they will actually receive.

## Non-goals

- Tax advice or legal disclaimers beyond a simple informational note.
- Supporting every country's tax treaty rate (v1: only US default 30% and
  Singapore treaty rate 15%).
- Calculating total return including capital gains tax (Singapore has none).
- Integration with tax filing software.
- Server-side calculation — this is purely a frontend feature.

## User stories

- As a Singaporean investor viewing a US dividend stock, I want to see my
  effective dividend yield after US withholding tax so that I can compare it
  accurately against SGX REITs and Singapore savings bonds.

- As a new investor who hasn't filed W-8BEN yet, I want to see the difference
  between the 30% and 15% rate so that I'm motivated to file the form with my
  broker.

- As a financial planner (Mei Ling persona), I want to show clients the
  tax-adjusted yield so that I can give honest comparisons across markets.

## Design

### UI Component: "Tax-Smart Yield" card

Add a new card below the existing "Market Data" card on the ticker detail
page. It appears **only** when `dividendYield > 0`.

```
┌─────────────────────────────────────────────────┐
│  🧮 Tax-Smart Yield (Non-US Investors)          │
├─────────────────────────────────────────────────┤
│                                                 │
│  Gross Dividend Yield:           4.20%          │
│                                                 │
│  ┌─ Without W-8BEN (30% WHT) ─┐                │
│  │  Tax withheld:      1.26%   │                │
│  │  Effective yield:   2.94%   │                │
│  └─────────────────────────────┘                │
│                                                 │
│  ┌─ With W-8BEN (15% WHT) ────┐                │
│  │  Tax withheld:      0.63%   │                │
│  │  Effective yield:   3.57%   │  ← highlight   │
│  └─────────────────────────────┘                │
│                                                 │
│  [ ] I have filed W-8BEN  (toggle)              │
│                                                 │
│  ℹ️ W-8BEN reduces US dividend withholding tax  │
│  from 30% to 15% for Singapore tax residents.   │
│  File it through your broker (free).            │
│  Learn more → /glossary/w-8ben/                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Behavior

1. **Default state:** Show both rates side by side. The W-8BEN rate is
   visually highlighted (green badge or bold) as the "recommended" path.

2. **Toggle:** A checkbox "I have filed W-8BEN" (persisted in
   `localStorage` key `smw_w8ben_filed`). When checked:
   - The "without W-8BEN" row is visually de-emphasized (muted/collapsed).
   - The "with W-8BEN" effective yield is shown prominently.
   - State persists across page visits.

3. **Zero-yield stocks:** If `dividendYield` is 0 or null, the entire card
   is hidden. No point showing tax on zero dividends.

4. **Calculation:** Pure arithmetic, no API calls:
   - `effectiveYield = grossYield × (1 - whtRate)`
   - `taxWithheld = grossYield × whtRate`

5. **i18n:** All labels use Hugo i18n keys (new keys in `en.toml` and
   `zh-cn.toml`).

### Implementation

#### Hugo template changes

**`hugo/site/layouts/tickers/single.html`** — Add the Tax-Smart Yield card
after the Market Data card, inside the left column `col-lg-6`. The card
uses Hugo template logic (no JS needed for the calculation since
`dividendYield` is available at build time).

```html
{{ if and .Params.dividendYield (gt .Params.dividendYield 0) }}
<div class="card mt-3" id="tax-smart-yield">
  <div class="card-header bg-success text-white">
    <h5 class="mb-0">🧮 {{ i18n "wht_card_title" }}</h5>
  </div>
  <div class="card-body">
    {{- $gross := div .Params.dividendYield 100.0 -}}
    {{- $wht30 := mul $gross 0.30 -}}
    {{- $wht15 := mul $gross 0.15 -}}
    {{- $net30 := sub $gross $wht30 -}}
    {{- $net15 := sub $gross $wht15 -}}
    <!-- ... render table with these values ... -->
  </div>
</div>
{{ end }}
```

#### i18n keys (new)

Add to both `hugo/site/i18n/en.toml` and `hugo/site/i18n/zh-cn.toml`:

| Key | English | Chinese |
|-----|---------|---------|
| `wht_card_title` | Tax-Smart Yield (Non-US Investors) | 税后收益率（非美国投资者） |
| `wht_gross_yield` | Gross Dividend Yield | 股息总收益率 |
| `wht_without_w8ben` | Without W-8BEN (30% WHT) | 未提交W-8BEN（30%预扣税） |
| `wht_with_w8ben` | With W-8BEN (15% WHT) | 已提交W-8BEN（15%预扣税） |
| `wht_tax_withheld` | Tax withheld | 预扣税额 |
| `wht_effective_yield` | Effective yield | 实际收益率 |
| `wht_toggle_label` | I have filed W-8BEN | 我已提交W-8BEN |
| `wht_info_text` | W-8BEN reduces US dividend withholding tax from 30% to 15% for Singapore tax residents. File it through your broker (free). | W-8BEN可将美国股息预扣税从30%降至15%（适用于新加坡税务居民）。通过您的券商免费提交。 |
| `wht_learn_more` | Learn more | 了解更多 |

#### localStorage for toggle persistence

A small inline `<script>` at the bottom of the card (or in a new
`wht-toggle.js` file) that:
1. On page load: reads `localStorage.getItem('smw_w8ben_filed')` and sets
   checkbox state.
2. On toggle: writes to `localStorage` and toggles CSS class on the card to
   de-emphasize the 30% row.

#### Glossary entry

Create `hugo/site/content/glossary/w-8ben.md` (and `.zh-cn.md`) explaining:
- What W-8BEN is
- Why Singaporean investors should file it
- How to file through Tiger Brokers, moomoo, IBKR
- Link back to ticker pages

### Data flow

No pipeline changes. The `dividendYield` field is already present in
`all_tickers.json` and available as `.Params.dividendYield` on every ticker
page. The calculation is purely template-side (Hugo build time) + a small
localStorage toggle (client-side).

## Affected files

| File | Change |
|------|--------|
| `hugo/site/layouts/tickers/single.html` | Add Tax-Smart Yield card |
| `hugo/site/i18n/en.toml` | Add ~10 new i18n keys |
| `hugo/site/i18n/zh-cn.toml` | Add ~10 new i18n keys |
| `hugo/site/static/js/wht-toggle.js` (new) | localStorage toggle logic |
| `hugo/site/content/glossary/w-8ben.md` (new) | Glossary entry |
| `hugo/site/content/glossary/w-8ben.zh-cn.md` (new) | zh-CN glossary entry |
| `tests/puppeteer/website-pages.e2e.test.js` | Add w-8ben glossary to PAGES array |

## Verification

- **Manual:** Open `http://localhost:1313/tickers/ko/` (Coca-Cola, has
  dividends). Confirm Tax-Smart Yield card appears with correct math. Toggle
  W-8BEN checkbox, reload page, confirm state persists.
- **Manual:** Open a ticker with no dividends (e.g., a growth stock). Confirm
  the card is hidden.
- **Manual:** Open `/zh-cn/tickers/ko/`. Confirm Chinese labels render.
- **Manual:** Open `/glossary/w-8ben/`. Confirm page renders.
- **Automated:** Add `/glossary/w-8ben/` to PAGES array in
  `tests/puppeteer/website-pages.e2e.test.js`.
- **Math check:** For a 4.20% gross yield: 30% WHT → 2.94% effective;
  15% WHT → 3.57% effective.

## Open questions

1. **Should we support other treaty rates?** Default: No. V1 is 30% (default)
   and 15% (Singapore treaty). A future version could add a country dropdown.
2. **Should the toggle affect the main "Dividend Yield" row in the Market Data
   card?** Default: No — keep the original display as gross yield for
   consistency with other financial sites. The Tax-Smart card is additive.
3. **Legal disclaimer?** Default: Add a small "This is for informational
   purposes only and does not constitute tax advice" footer on the card.

## Alternatives considered

1. **Country selector dropdown** — Rejected for v1. Adds complexity. Singapore
   is the target market; a simple toggle is faster to ship and easier to
   understand.
2. **Pipeline-side calculation** — Rejected. The WHT rate depends on the
   user's tax residency, not the stock. This must be client-side (or at least
   build-time with a toggle).
3. **Separate page instead of card** — Rejected. The value is in seeing
   the adjusted yield *in context* next to the gross yield on the ticker page.
