---
title: "About"
lastmod: 2026-03-13
---

# About Stock Market Words

**Stock Market Words** is an educational stock research project by **Andrew Allbright**. It started with a simple question: how often do valid stock ticker symbols hide inside normal English text, and can that pattern become a useful way to explore a market dataset?

The answer turned into two related products:

1. A **ticker extraction tool** that finds stock symbols hidden in words and phrases.
2. A **research site** that scores those symbols across five strategy lenses using market and technical data.

> **Last updated:** March 13, 2026

## Who runs this site?

My name is **Andrew Allbright**. I built this site and maintain the code, data pipeline, and Hugo front end.

- **GitHub:** [github.com/aallbrig](https://github.com/aallbrig)
- **Project source:** [github.com/aallbrig/stock-market-words](https://github.com/aallbrig/stock-market-words)

This project is intentionally transparent: the source code is public, the methodology is documented, and the site clearly distinguishes between raw data, filtered data, and opinionated strategy scores.

## What makes this site different?

There are plenty of stock screeners on the internet. This site is different in three ways:

### 1. It starts with text, not a watchlist

Most investing tools assume you already know which stocks you want to analyze. Stock Market Words starts with a block of text and asks a different question: **which real ticker symbols are hiding in this text?**

That means the homepage is not just a stock screener. It is a symbol-discovery tool with a custom extraction algorithm.

### 2. It shows the data pipeline openly

This site exposes:

- the **raw NASDAQ source universe**
- the **filtered ticker universe**
- the **strategy-specific datasets**
- the individual **ticker detail pages**

That transparency matters. You can see what was filtered out, what remained, and why a ticker appears in one strategy but not another.

### 3. It uses strategy scores as an educational lens

The five strategies on this site are not recommendations or promises. They are simplified lenses for learning how different market characteristics interact:

- **Dividend Daddy** — yield + lower volatility
- **Moon Shot** — high beta + room to run
- **Falling Knife** — oversold + below trend
- **Over-Hyped** — stretched momentum
- **Institutional Whale** — large-cap quality / liquidity

The point is not to tell you what to buy. The point is to make the dataset easier to reason about.

## What data does the site use?

The site combines:

- daily symbol and reference data from **NASDAQ**
- price and market metrics used by the project pipeline
- computed technical values such as **RSI**, **moving averages**, and **beta**
- site-specific **strategy scores**

For a full breakdown, see the **[Methodology](/methodology/)** page.

## What this site is for

This site is for:

- investors who like exploring stock ideas from unusual angles
- developers interested in data pipelines and text parsing
- readers who want a plain-English bridge between finance terms and actual market examples

It is **not** a brokerage, an investment adviser, or a replacement for full due diligence.

## Editorial approach

I am trying to make this site more useful than a generic database dump. That means:

- publishing explanatory articles alongside the tools
- documenting the scoring logic and data limitations
- linking data pages back to methodology and glossary pages
- being explicit about what the site can and cannot tell you

If you want to understand how the extraction engine works, start with **[How Ticker Extraction Works](/articles/how-ticker-extraction-works/)**.

If you want to understand the tradeoffs in the strategy pages, start with **[How to Read the Five Strategies](/articles/how-to-read-the-five-strategies/)**.

## Contact

Questions, bug reports, and corrections are welcome. Visit the **[Contact](/contact/)** page.

---

*Disclaimer: This site is for educational and informational purposes only. Nothing on Stock Market Words is investment advice.*
