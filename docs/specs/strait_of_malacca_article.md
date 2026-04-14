# Strait of Malacca: Shipping, Energy, and the Stock Tickers Behind a Global Chokepoint

**Status:** Draft
**Author:** Andrew Allbright
**Created:** 2026-04-14
**Supersedes:** —
**Superseded by:** —

## Context

stockmarketwords.com already hosts an article targeting Singaporean investors
([GRAB analysis](/articles/southeast-asia-unicorn-tickerengine-grab/)). That
article demonstrated strong engagement from the Singapore investor community.

The Strait of Malacca is the second-busiest shipping lane in the world
(120,000+ vessel transits/year), channels ~25 % of global maritime trade
(~US $3.5 T annually), and is the world's largest oil chokepoint at 23.7
million barrels/day. It sits between Malaysia, Indonesia, and Singapore —
making it deeply relevant to our Singaporean audience.

We have **53 US-listed tickers** in our database that are directly linked to
trade flowing through the strait: container shipping, tankers, LNG carriers,
oil majors, refiners, defense contractors, and GRAB itself. This creates an
exceptional cross-linking opportunity — an article that educates readers about
a real-world chokepoint while linking them to dozens of ticker pages on our
site.

Source material: [Grokipedia — Strait of Malacca](https://grokipedia.com/page/Strait_of_Malacca)

## Goal

Publish a long-form article at `/articles/strait-of-malacca-trade-and-tickers/`
that explains what the Strait of Malacca is, what flows through it, and links
readers to 53 ticker pages on stockmarketwords.com — creating a compelling
educational experience and a powerful internal linking structure.

## Non-goals

- **Not a live-data article** — unlike the GRAB article, this does not embed
  real-time charts or TickerEngine analysis. It is editorial/educational with
  static ticker links. The one interactive element is an OpenStreetMap embed.
- **Not a buy/sell recommendation** — article is informational, not advisory.
- **Not covering Singapore-listed stocks in depth** — we mention DBS, OCBC,
  Keppel, etc. for context but cannot link them (not in our US-ticker database).
  This gap should be noted transparently in the article.
- **Not a zh-CN translation** — English-only for the initial spec. Translation
  can follow under the existing zh-CN content backfill spec.

## User stories

- As a **Singaporean investor**, I want to understand how the Strait of Malacca
  connects to publicly traded companies so that I can discover investment ideas
  relevant to my region.
- As a **site visitor**, I want to click through from an article to individual
  ticker pages so that I can explore metrics and strategy scores for companies
  mentioned.
- As a **returning user**, I want the article banner to notify me about this new
  content so that I don't miss it.
- As a **curious reader**, I want an interactive map of the strait so that I can
  visualize the geography and key ports.

## Design

### Interactive map

The article includes an interactive OpenStreetMap embed via a Hugo shortcode
(`strait-map.html`). Implementation:

- **Library:** Leaflet.js v1.9.4 from jsDelivr CDN (with SRI hashes)
- **Tiles:** OpenStreetMap standard tiles
- **Features:**
  - Dashed polyline showing the primary shipping lane (~800 km)
  - Shaded polygon overlay for the strait area
  - Red port markers: Singapore, Port Klang, Penang, Tanjung Pelepas, Belawan, Batam
  - Orange marker at the narrowest point with depth annotation
  - Trade flow direction labels ("← Middle East oil & LNG" / "→ China, Japan, S. Korea")
  - Click popups with port statistics
  - Scroll-wheel zoom disabled (prevents accidental map hijacking)

### Ad placement

Per the [Article Ad Placement ADR](../design/20260414_230800_UTC_article_ad_placement.md):

- **Mid-article ad:** Placed via `{{</* article-ad */>}}` shortcode after the
  tanker fleet section (~45% through the article). This is after the reader has
  received substantial value (map, oil majors, full tanker breakdown) but before
  the container shipping and summary sections.
- **End-of-article ad:** Automatic via the article layout template. No author
  action needed.

### Article structure (implemented)

```
1. Introduction — "The Strait That Moves the World"
   - 800 km long, 65 km at narrowest, 25 m depth at shallowest
   - 120,000+ vessel transits/year, ~25% of world maritime trade
   - $3.5 T in goods annually, 23.7M barrels of oil/day
   - Three littoral states: Malaysia, Indonesia, Singapore

2. What Flows Through the Strait?
   a. Crude Oil & Petroleum Products (23.7M bbl/day)
      - 80% of China's crude imports
      - Middle East → East Asia energy corridor
      - Link tickers: XOM, CVX, BP, TTE, EQNR, COP, OXY
   b. Liquefied Natural Gas (LNG)
      - 66% of China's LNG imports transit here
      - Link tickers: LNG, GLNG, FLNG, LPG, EE, BWLP, GASS
   c. Containerized Cargo
      - Electronics, consumer goods, manufactured exports
      - Link tickers: ZIM, DAC, GSL, CMRE, ASC, MATX
   d. Dry Bulk (iron ore, coal, grains)
      - Record 19,507 bulk carrier transits in 2024
      - Link tickers: SBLK, GNK, PANL, SB

3. The Tanker Fleet — Who Carries the Oil?
   - Deep-dive on tanker companies: FRO, HAFN, STNG, TRMD, TNK, TK,
     NAT, DHT, INSW, TEN, ECO, SFL, HSHP, SHIP, ESEA, SVRN, SMHI
   - Brief explanation of tanker types (VLCC, Suezmax, Aframax, etc.)
   - Note: shallow depth (25m) limits fully-loaded supertankers

4. The Downstream Chain — Refiners Who Process What Arrives
   - US refiners processing Middle East crude: MPC, PSX, VLO, PBF, DK
   - How strait disruptions ripple into US gasoline prices

5. Defense & Security — Protecting the Sea Lanes
   - Piracy surge: 80 incidents in H1 2025 (400% YoY increase)
   - US Indo-Pacific strategy: $1.5B+ in maritime security since 2017
   - Link tickers: RTX, LMT, NOC, BA
   - The "Malacca Dilemma" — China's Achilles' heel

6. Singapore: The Gateway City
   - 30M+ containers/year, port = ~7% of GDP
   - GRAB as the sole US-listed Singapore company in our database
   - Mention (but cannot link): DBS, OCBC, UOB, SGX, Keppel,
     Sembcorp, Singapore Airlines, Wilmar, PSA
   - Note about the SGX Ticker Support spec for future coverage

7. The "What If" — Strait Disruption Scenarios
   - Week-long closure → $85M+ rerouting costs
   - Alternative routes: Sunda Strait, Lombok Strait (longer/deeper)
   - Historical context: Srivijaya Empire (7th C), Portuguese (1511),
     Dutch (1641), British Straits Settlements (1826)

8. Ticker Summary Table
   - Full table of all 53 tickers with: symbol, name, category, link
   - Visual: tickers we cover vs. tickers we wish we could
   - Callout box: "These tickers represent X% of daily Malacca traffic"

9. Conclusion
   - The strait isn't just geography — it's a portfolio
   - Call to action: explore ticker pages, try TickerEngine
```

### File locations

- **Article**: `hugo/site/content/articles/strait-of-malacca-trade-and-tickers.md`
- **Banner update**: `hugo/site/hugo.toml` → `[params.latestArticle]` section

### Ticker linking convention

Use the existing pattern from other articles:
```markdown
[ZIM](/tickers/zim/)
```

All 53 tickers should be linked at least once. The summary table in section 8
should link every ticker.

### Key statistics to include (sourced from Grokipedia)

| Fact | Value | Source note |
|---|---|---|
| Length | ~800 km | Grokipedia |
| Minimum width | ~65 km (1.5 mi at narrowest point) | Grokipedia |
| Minimum depth | ~25 m in southern portions | Grokipedia |
| Annual vessel transits | 120,000+ | Grokipedia |
| Share of global trade | ~25% | Grokipedia |
| Annual trade value | ~US $3.5 trillion | Grokipedia |
| Oil flow (2023) | 23.7 million barrels/day | Grokipedia citing EIA |
| China oil import dependence | >80% via strait | Grokipedia |
| China LNG import dependence | ~66% via strait | Grokipedia |
| Piracy incidents H1 2025 | 80 (400% YoY increase) | Grokipedia citing ReCAAP |
| Singapore container throughput | 30M+ TEU/year | Grokipedia |
| Singapore port GDP contribution | ~7% | Grokipedia |
| Bulk carrier transits (2024) | 19,507 (record) | Grokipedia |
| Hypothetical closure cost | >$85M/week rerouting | Grokipedia |

## Affected files

- [x] `hugo/site/content/articles/strait-of-malacca-trade-and-tickers.md` — **new** article
- [x] `hugo/site/layouts/shortcodes/strait-map.html` — **new** Leaflet.js map shortcode
- [x] `hugo/site/layouts/shortcodes/article-ad.html` — **new** inline ad shortcode
- [x] `hugo/site/hugo.toml` — updated `[params.latestArticle]` for banner
- [x] `hugo/site/content/articles/_index.md` — added article to listing
- [x] `docs/design/20260414_230800_UTC_article_ad_placement.md` — **new** ADR for article ads
- [ ] `tests/puppeteer/website-pages.e2e.test.js` — add article URL to PAGES array

## Verification

- **Manual**: `hugo server`, visit `/articles/strait-of-malacca-trade-and-tickers/`,
  confirm all 53 ticker links resolve to valid pages.
- **Manual**: Confirm article banner appears with new article title.
- **Automated**: Add article URL to `tests/puppeteer/website-pages.e2e.test.js`
  PAGES array.
- **Link audit**: Spot-check 10 random ticker links (e.g., `/tickers/zim/`,
  `/tickers/fro/`, `/tickers/xom/`) to confirm they return 200.

## Open questions

1. **Should we include a map or diagram of the strait?**
   Default: No — keep it text-only for V1. A map could be added later as a
   static image or interactive element.

2. **How many words should the article target?**
   Default: 3,000–4,000 words (comparable to the GRAB article). Long enough
   for SEO value, short enough to maintain engagement.

3. **Should we include strategy scores for any of the 53 tickers?**
   Default: No — that would require live data integration. Instead, link to
   ticker pages where scores are already displayed. A future "Top Malacca
   Tickers by Strategy" could be a follow-up article.

4. **Should we attribute the Grokipedia source in-article?**
   Default: Yes — include a "Sources" or "Further Reading" section at the
   bottom linking to the Grokipedia page and any other references used.

## Alternatives considered

- **Interactive map with clickable ticker pins**: Rejected for V1 — too complex.
  Could be a compelling V2 enhancement.
- **Data-driven article with live metrics**: Rejected — would require embedding
  TickerEngine for 53 tickers, which is a different article format. Keep this
  one editorial/educational.
- **Splitting into a series**: Rejected — a single comprehensive article with
  a clear table of contents provides better SEO value and user experience than
  a fragmented series.
