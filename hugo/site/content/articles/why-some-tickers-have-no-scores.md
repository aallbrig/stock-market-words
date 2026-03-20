---
title: "Why Some Tickers Have No Strategy Scores"
description: "Not every ticker on this site has strategy scores. Here's exactly why — and what it tells you about coverage, data quality, and filtering."
date: 2026-03-20
lastmod: 2026-03-20
draft: false
---

When you look up a ticker on this site and see the message *"Strategy scores are not yet available for this ticker,"* you might wonder whether the score is being withheld, or whether the stock is somehow disqualified. Neither is quite right. The answer is more transparent than that — and understanding it helps you use the site more effectively.

## Scores Are Earned, Not Assigned

Each of the five strategies on this site (Dividend Daddy, Moon Shot, Falling Knife, Over-Hyped, and Institutional Whale) scores a stock against a specific profile. A ticker only receives a score if it passes that strategy's filters in the first place — and those filters exist for good reasons.

Think of it like a job application that requires certain credentials. If you don't have a driver's license, you won't appear in the candidate pool for a driving job. That's not a judgment about your overall worth; it's just a scoping decision.

## The Two Layers of Filtering

### Layer 1: Minimum data quality thresholds

The site's data pipeline filters the full ticker universe down to a working set before scoring even begins. A ticker must meet **all** of the following to be included:

- **Price ≥ $5.00** — sub-penny stocks and micro-caps are excluded because their data is often sparse, their prices are highly manipulated, and none of the five strategies apply meaningfully at that scale
- **Volume ≥ 100,000 shares/day** — tickers with very thin trading volume produce unreliable RSI calculations and moving-average signals; you can't reliably "catch a falling knife" if there's no real market for the stock

These thresholds also reduce noise. Including every listed security would balloon the dataset with hundreds of zombie shells, suspended ADRs, and barely-traded preferred shares that no reasonable investor would ever research.

### Layer 2: Strategy-specific metric availability

Each strategy requires a minimum set of metrics to calculate its score. If the data for any required metric is missing, that strategy's score is left blank rather than calculated from partial data.

Here's what each strategy needs:

| Strategy | Key required metrics |
|---|---|
| 💰 Dividend Daddy | Dividend yield, beta |
| 🚀 Moon Shot | Beta, RSI |
| 🔪 Falling Knife | RSI, 50-day MA, 200-day MA |
| 🎈 Over-Hyped | RSI |
| 🐋 Institutional Whale | Market cap, volume |

If a ticker doesn't have a dividend yield on record (because it pays no dividend), it simply doesn't qualify for the Dividend Daddy score — that strategy has nothing to evaluate. If RSI data isn't available for a thinly traded name, Moon Shot and Falling Knife are left blank.

## Why Tickers Without Scores Are Still Useful

Just because a ticker has no strategy scores doesn't mean the page is empty. The market data section still shows whatever information is available: price, volume, market cap, sector, exchange, 52-week range, and valuation ratios.

A ticker with no strategy scores but a full market data card is still a useful lookup destination. If you extract a symbol from a news article or an earnings report and want a quick overview, that data is still there.

The ticker extractor tool on the homepage works across your entire text input regardless of whether every extracted symbol has scores. The tool is about discovery — finding symbols you might not have caught — not just about surfacing highly-scored tickers.

## What the Score Range Actually Tells You

When scores are present, they run from 0 to 100. A score of 0 doesn't mean "avoid this ticker" — it means this stock barely fits this particular strategy's profile. A score of 100 is the strongest possible alignment with the strategy's criteria.

Scores are **relative** within the strategy, not absolute ratings. A Dividend Daddy score of 80 means this ticker is a stronger dividend candidate than most others in the dataset. It doesn't mean the dividend is safe, the yield is sustainable, or that buying it is a good idea.

See the [methodology page](/methodology/) for the exact formulas behind each strategy, and the article [How to Read the Five Strategies](/articles/how-to-read-the-five-strategies/) for guidance on combining scores intelligently.

## Coverage Over Time

The site's data comes from Yahoo Finance via a daily pipeline run. Coverage improves as the pipeline is re-run against an updated market universe. Tickers that were previously missing RSI or moving-average data sometimes pick up those values once sufficient price history has accumulated (the 200-day moving average, for example, requires a minimum of 200 trading days of data from the time a stock is listed).

If you're researching a recently-listed stock and see no scores, check back after it has accumulated a few months of trading history.

## Further Reading

- [How to Read the Five Strategies](/articles/how-to-read-the-five-strategies/) — what each score measures and what it doesn't
- [Methodology](/methodology/) — data sources, extraction logic, and scoring formulas
- [Glossary](/glossary/) — definitions for RSI, beta, moving averages, and other metrics used in scoring
