# Singaporean Investor Personas & Feature Strategy

**Author:** Copilot  
**Created:** 2026-04-12  
**Purpose:** Market analysis, persona definitions, and ranked feature ideas to
evolve stockmarketwords.com for Singaporean investors.

---

## 1. Why Singapore?

Singapore is Southeast Asia's financial hub with characteristics that make it
an ideal target market for stockmarketwords.com:

| Factor | Detail |
|--------|--------|
| **Retail investor population** | ~1.5 million active brokerage accounts (population 5.9M) |
| **US market access** | Widely available via Tiger Brokers, moomoo, Interactive Brokers, Saxo |
| **Language** | English (official business language) + Mandarin Chinese widely spoken — aligns with existing zh-CN support |
| **Tax regime** | No capital gains tax, but **30% US dividend withholding tax** is the #1 pain point |
| **REIT culture** | Largest REIT market in Asia ex-Japan; REITs are Singapore's favorite asset class |
| **CPF/SRS** | Government retirement schemes (CPF-OA, SRS) allow approved stock/ETF investments |
| **Digital literacy** | Among the highest internet/smartphone penetration globally |
| **Regulatory** | MAS-regulated, PDPA for data privacy (our GA4 spec already addresses this) |

### Current app alignment

- ✅ zh-CN i18n support (in progress) — serves Mandarin-speaking Singaporeans
- ✅ Free, fast static site — matches SG's high-speed internet expectations
- ✅ Educational content (glossary, articles) — SG investors value financial literacy
- ✅ Strategy scoring — maps to different SG investor archetypes
- ❌ US-only data — misses SGX entirely
- ❌ No tax awareness — the #1 cost for SG investors in US markets
- ❌ No REIT focus — misses Singapore's dominant investment culture
- ❌ No SGD context — every SG investor thinks in SGD

---

## 2. Investor Personas

### Persona 1: "Ah Huat" — The CPF Investor

| Attribute | Detail |
|-----------|--------|
| **Age** | 40–55 |
| **Risk profile** | Conservative |
| **Investment style** | Uses CPF-OA to invest in approved blue-chip stocks and ETFs |
| **Goal** | Preserve capital, beat CPF-OA interest rate (2.5%), steady dividends |
| **Reads** | The Straits Times, CNA Business, The Business Times |
| **Behavior** | Copy-pastes news articles to find mentioned tickers |
| **Pain point** | Doesn't know which mentioned stocks are CPF-approved or dividend-safe |
| **Strategy alignment** | Dividend Daddy 💰, Institutional Whale 🐋 |
| **Language** | English, some Mandarin |
| **Broker** | DBS Vickers, OCBC Securities (SGX-focused), IBKR for US |

### Persona 2: "Wei Lin" — The REIT Hunter

| Attribute | Detail |
|-----------|--------|
| **Age** | 30–45 |
| **Risk profile** | Moderate, yield-focused |
| **Investment style** | Heavily invested in S-REITs; exploring US REITs for diversification |
| **Goal** | Build a passive income portfolio via distributions (DPU) |
| **Reads** | REITsweek, The Fifth Person, Seedly, zh-CN finance forums |
| **Behavior** | Compares distribution yields, price-to-NAV, gearing ratios |
| **Pain point** | US REIT dividends lose 30% to WHT; needs to compare effective yields |
| **Strategy alignment** | Dividend Daddy 💰 (needs REIT-specific strategy) |
| **Language** | Mandarin-dominant, reads zh-CN financial content |
| **Broker** | Tiger Brokers, moomoo |

### Persona 3: "Raj" — The Growth Techie

| Attribute | Detail |
|-----------|--------|
| **Age** | 25–35 |
| **Risk profile** | Aggressive |
| **Investment style** | Tech stocks, IPOs, momentum plays; follows WSB-style analysis |
| **Goal** | Capital appreciation, find the next 10-bagger |
| **Reads** | HackerNews, Reddit (r/wallstreetbets, r/singaporefi), earnings transcripts |
| **Behavior** | Pastes Reddit threads and earnings calls to extract tickers; wants quick scores |
| **Pain point** | Information overload; needs fast screening of mentioned tickers |
| **Strategy alignment** | Moon Shot 🚀, Over-Hyped 🎈 |
| **Language** | English |
| **Broker** | Interactive Brokers, Tiger Brokers |

### Persona 4: "Mei Ling" — The Financial Planner

| Attribute | Detail |
|-----------|--------|
| **Age** | 35–50 |
| **Risk profile** | Varies by client |
| **Investment style** | Professional — screens stocks for client portfolios |
| **Goal** | Quick screening tool for tickers mentioned in analyst reports |
| **Reads** | Bloomberg, Reuters, Morningstar, analyst research reports |
| **Behavior** | Pastes dense analyst reports → extracts all tickers → cross-references strategies |
| **Pain point** | Needs methodology transparency for compliance; wants exportable data |
| **Strategy alignment** | All strategies (matches clients to strategies) |
| **Language** | English + Mandarin (bilingual client base) |
| **Broker** | Institutional platforms |

### Persona 5: "Darren" — The Passive Indexer

| Attribute | Detail |
|-----------|--------|
| **Age** | 25–40 |
| **Risk profile** | Low to moderate |
| **Investment style** | Robo-advisors (Syfe, StashAway, Endowus), occasional individual stocks |
| **Goal** | Set-and-forget investing; occasionally curious about stocks in the news |
| **Reads** | Seedly, Investment Moats, mainstream news |
| **Behavior** | Low engagement but high potential volume (largest SG investor segment) |
| **Pain point** | "Is this stock worth looking at?" — wants a quick answer, not deep analysis |
| **Strategy alignment** | Institutional Whale 🐋 (blue-chips feel safe) |
| **Language** | English |
| **Broker** | Robo-advisors, DBS digiPortfolio |

### Persona 6: "Uncle Tan" — The Kopitiam Trader

| Attribute | Detail |
|-----------|--------|
| **Age** | 50–65 |
| **Risk profile** | Speculative |
| **Investment style** | Active SGX trader, follows penny stock forums and coffee shop tips |
| **Goal** | Short-term gains, find momentum stocks before they move |
| **Reads** | The Edge Singapore, SGX forums, Telegram trading groups, NextInsight |
| **Behavior** | Copies forum posts to find mentioned tickers; loves falling knives and recoveries |
| **Pain point** | Forum posts mention tickers he can't keep track of; needs batch extraction |
| **Strategy alignment** | Falling Knife 🔪, Moon Shot 🚀 |
| **Language** | English + Mandarin |
| **Broker** | CGS-CIMB, Phillip Securities |

---

## 3. Ten High-Leverage Feature Ideas

Ranked by **leverage** = (value to SG investors × number of personas served) ÷ implementation effort.

### 🥇 Idea 1: Dividend Withholding Tax Calculator — "Tax-Smart Yields"

**Leverage: ★★★★★ (Highest)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Show effective dividend yield after US 30% WHT on every ticker page. Toggle for "I filed W-8BEN" (reduces to 15%). |
| **Value** | Every SG investor buying US dividend stocks loses 15–30% of dividends to tax. This is the #1 surprise for new investors. A calculator that shows *effective* yield is immediately actionable. |
| **Effort** | LOW — Pure frontend calculation. Data already exists (dividend_yield in daily_metrics). No new API calls, no pipeline changes. |
| **Architecture fit** | Add a toggle + computed display to ticker detail Hugo template. |
| **Personas served** | Wei Lin, Ah Huat, Darren, Mei Ling, Uncle Tan (5 of 6) |

### 🥈 Idea 2: SGX Ticker Support — "Go Local"

**Leverage: ★★★★★ (Very High)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Add ~700 Singapore Exchange tickers to the database and extraction engine. SGX tickers follow the pattern `D05.SI` (DBS), `O39.SI` (OCBC), `Z74.SI` (Singtel). |
| **Value** | Transformative — makes the entire site relevant for SGX trading, which is the primary market for most Singaporean investors. |
| **Effort** | MEDIUM — Yahoo Finance already supports SGX (`.SI` suffix). Pipeline needs: new data source for SGX ticker list, TickerEngine needs `.SI` pattern support, Hugo needs exchange filter. |
| **Architecture fit** | Extends existing pipeline cleanly — new FTP/source → same SQLite → same JSON → same Hugo. |
| **Personas served** | ALL 6 personas |

### 🥉 Idea 3: REIT Radar Strategy — "REIT Radar"

**Leverage: ★★★★☆ (High)**

| Dimension | Assessment |
|-----------|------------|
| **What** | 6th investment strategy purpose-built for REIT investors. Scores REITs by distribution yield, price-to-NAV, gearing ratio. Filter to show only REITs. |
| **Value** | REITs are Singapore's favorite asset class. No other free tool combines REIT screening with ticker extraction. |
| **Effort** | MEDIUM — New strategy in builders.py, new strategy JSON, new Hugo page. Needs REIT-specific data fields (some available via Yahoo Finance: `dividendYield`, but `gearing` and `NAV` may need alternative sources). |
| **Architecture fit** | Clean extension of the existing 5-strategy framework. |
| **Personas served** | Wei Lin, Ah Huat, Mei Ling, Uncle Tan (4 of 6) |

### Idea 4: Singapore Financial Glossary — "SG Investor Guide"

**Leverage: ★★★★☆ (High)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Expand the existing 14-term glossary with Singapore-specific terms: CPF-OA, SRS, S-REIT, DPU, NAV, Gearing Ratio, STI, PDPA, MAS, W-8BEN. Add a "New to US Stocks from Singapore?" beginner guide. |
| **Value** | SEO goldmine for Singapore financial literacy queries. Builds trust and establishes the site as a resource for SG investors. Low effort, compounding returns. |
| **Effort** | LOW — Content creation + Hugo pages using existing glossary template. |
| **Personas served** | Ah Huat, Darren, Wei Lin (3 of 6) |

### Idea 5: Currency-Adjusted View — "SGD View"

**Leverage: ★★★★☆ (High)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Show all prices in SGD alongside USD. Daily SGD/USD rate from a free FX API or static snapshot in the pipeline. Toggle between USD and SGD display. |
| **Value** | Every Singaporean investor converts mentally to SGD. Showing it directly eliminates friction and makes the data immediately relatable. |
| **Effort** | MEDIUM — Need FX rate data source (one more API call in pipeline or client-side fetch), frontend toggle, dual display. |
| **Personas served** | ALL 6 personas |

### Idea 6: Broker Deep Links — "Trade Now"

**Leverage: ★★★☆☆ (Good)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Add "Open in Tiger Brokers" / "Open in moomoo" / "Open in IBKR" links on ticker detail pages. Deep link to the specific stock on each broker's web platform. |
| **Value** | Bridges discovery → action. Potential future affiliate revenue stream. |
| **Effort** | LOW — URL templates per broker, Hugo partial template. |
| **Personas served** | Raj, Wei Lin, Uncle Tan (3 of 6) |

### Idea 7: Watchlist & Portfolio Tracker — "My Tickers"

**Leverage: ★★★☆☆ (Good)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Save tickers to a browser-local watchlist (localStorage). Show aggregated strategy scores. Export as CSV. |
| **Value** | Drives repeat visits, increases stickiness. Users build a relationship with the tool. |
| **Effort** | MEDIUM — New JS module, new Hugo page, localStorage API, UI for add/remove/export. |
| **Personas served** | Raj, Mei Ling, Uncle Tan (3 of 6) |

### Idea 8: Singapore News Examples — "Paste & Discover"

**Leverage: ★★★☆☆ (Good)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Add pre-loaded example texts from Singapore financial news (CNA Business, Straits Times, The Edge). "Try with SG news" button on home page. |
| **Value** | Reduces friction, shows immediate value to SG visitors. Demonstrates the tool works with content they actually read. |
| **Effort** | LOW — New example texts in Hugo content, minor JS changes to example selector. |
| **Personas served** | Ah Huat, Uncle Tan, Wei Lin (3 of 6) |

### Idea 9: Sector Heatmap — "Market Pulse"

**Leverage: ★★☆☆☆ (Moderate)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Visual treemap heatmap showing sector performance, color-coded by daily change, sized by market cap. |
| **Value** | Visually engaging, drives exploration, good for the "at a glance" user. |
| **Effort** | HIGH — New D3.js/treemap library, new page, responsive design, significant frontend work. |
| **Personas served** | Raj, Mei Ling, Uncle Tan (3 of 6) |

### Idea 10: Telegram Strategy Alerts — "Score Alerts"

**Leverage: ★★☆☆☆ (Moderate)**

| Dimension | Assessment |
|-----------|------------|
| **What** | Telegram bot sends daily top-5 movers per strategy. Singapore's finance community is heavily on Telegram. |
| **Value** | Push engagement → daily habit. But requires standing infrastructure (not static site). |
| **Effort** | HIGH — Telegram Bot API, scheduling service, hosting, new infrastructure outside Hugo/static paradigm. |
| **Personas served** | ALL 6 personas (but only if they use Telegram) |

---

## 4. Recommended Implementation Order

| Phase | Feature | Rationale |
|-------|---------|-----------|
| **Phase 1** | Dividend WHT Calculator | Quick win. Low effort, high delight. Proves SG-investor value. |
| **Phase 2** | SGX Ticker Support | Transformative. Unlocks the local market. |
| **Phase 3** | REIT Radar Strategy | Builds on SGX data. Speaks to SG's investment culture. |
| **Phase 4+** | SG Glossary, SGD View, Broker Links, News Examples | Incremental enhancements once the foundation is in place. |

Specs for Phase 1–3 follow in `docs/specs/`.
