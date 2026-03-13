---
title: "Methodology"
lastmod: 2026-03-13
---

# Methodology

This page explains how Stock Market Words builds its dataset, extracts ticker symbols from text, and scores tickers across the site's five strategy pages.

> **Last updated:** March 13, 2026

## The short version

The site combines a **text parsing engine** with a **daily market-data pipeline**:

1. Build a universe of valid stock symbols.
2. Filter out instruments that are not useful for this project.
3. Enrich the remaining symbols with price, liquidity, and technical data.
4. Score symbols against five educational strategy lenses.
5. Render the results into Hugo pages, datasets, and ticker detail pages.

## Data sources

The project uses market data gathered by the pipeline that powers this repository. The site distinguishes between:

- **Raw FTP data** — the broad symbol universe before project filtering
- **Filtered tickers** — the stock universe kept by this project
- **Strategy datasets** — subsets that match specific screening logic
- **Ticker detail pages** — per-symbol summaries built from the merged data file

You can inspect the raw and filtered views at:

- [Raw FTP Data](/raw-ftp-data/)
- [Filtered Tickers](/filtered-data/)

## Ticker extraction logic

The homepage tool does not simply split text on spaces and hope for the best. It uses a custom symbol matching approach designed to find **valid ticker strings embedded inside normal text**.

At a high level, the extractor:

1. normalizes the input text
2. walks the text with a prefix-aware search structure
3. tries non-overlapping symbol matches
4. backtracks when a local match blocks a better global solution

This matters because stock symbols are short and ambiguous. Many are also common English fragments. A naive approach would generate too many false positives.

For a full walkthrough, read **[How Ticker Extraction Works](/articles/how-ticker-extraction-works/)**.

## Filtering rules

The site does not keep every symbol that appears in the raw source data. The pipeline filters out many items that would reduce quality or make the research pages harder to use, including instruments that are outside the project's target scope.

The exact pipeline evolves, but the practical goal is consistent:

- focus on tradable, recognizable equity symbols
- avoid clutter from low-quality or non-target instruments
- keep enough liquidity and data coverage for useful comparison

## Base inclusion thresholds

Many site views rely on a practical minimum quality bar before a symbol is shown prominently:

- **Price >= $5**
- **Volume >= 100,000**

Those thresholds help remove many illiquid, low-information tickers from strategy views and ticker detail generation.

## Strategy scores

The site uses five educational strategies. These are **not** claims of future performance. They are ways to rank the current dataset using different preferences.

### Dividend Daddy

Looks for dividend-paying stocks and rewards:

- higher dividend yield
- lower beta / volatility

### Moon Shot

Looks for aggressive growth candidates and rewards:

- higher beta
- RSI that is not already overbought

### Falling Knife

Looks for deep pullbacks and rewards:

- low RSI
- price below the 200-day moving average

### Over-Hyped

Looks for stretched momentum and rewards:

- very high RSI

### Institutional Whale

Looks for large, liquid companies and rewards:

- larger market capitalization

Read the editorial guide **[How to Read the Five Strategies](/articles/how-to-read-the-five-strategies/)** before treating any strategy table as a decision tool.

## Why some tickers have no scores

Not every ticker page has a full strategy score block. That usually means one of three things:

1. the symbol did not pass the base filters used for the strategy datasets
2. the symbol had incomplete supporting data for the scoring step
3. the symbol simply did not match any strategy criteria on the latest run

This is expected. Absence of a score is not a judgment that a company is bad; it usually means the site does not have enough aligned inputs to score it in a meaningful way.

## Freshness and update cadence

The market data behind the site is refreshed by the project pipeline and then written into Hugo data files used by the site build. When you see a ticker page, strategy page, or filtered dataset, you are seeing a static view of the latest successfully generated data at build time.

## Limitations

This site has important limits:

- it is a research and education tool, not a brokerage platform
- it simplifies complex investing ideas into compact screens
- it depends on upstream data quality and pipeline freshness
- it does not replace reading filings, earnings reports, or company guidance

## Related pages

- [About](/about/)
- [Investment Strategies](/strategies/)
- [How Ticker Extraction Works](/articles/how-ticker-extraction-works/)
- [How to Read the Five Strategies](/articles/how-to-read-the-five-strategies/)

---

*This site is for educational and informational purposes only and does not provide investment advice.*
