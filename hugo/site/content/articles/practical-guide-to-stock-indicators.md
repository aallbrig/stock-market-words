---
title: "A Practical Guide to Reading Stock Indicators"
author: "Andrew Allbright"
date: 2026-03-20
description: "RSI, beta, moving averages, P/E ratio, and dividend yield explained clearly — with real examples drawn from this site's own ticker universe."
lastmod: 2026-03-20
draft: false
---

The market data section on every ticker page on this site shows up to nine different indicators. If you've ever stared at a number like *RSI: 14.3* and wondered what to actually do with that, this guide is for you. Each section below explains what the metric measures, why it matters, and — crucially — where it breaks down.

All examples are drawn from real tickers in the current dataset (data as of March 2026).

---

## RSI — Relative Strength Index

**What it is:** RSI measures the speed and magnitude of recent price changes, normalized to a 0–100 scale. The standard window is 14 trading days.

**What the numbers mean:**
- **Above 70** — overbought territory. The stock has moved up sharply relative to recent history. This doesn't mean it will fall, but it does mean momentum is stretched.
- **Below 30** — oversold territory. The stock has declined sharply. This doesn't mean it will recover, but the move has been extreme by recent standards.
- **40–60** — neutral. No strong signal either way.

**Real examples from this dataset:**
- **ACLX** has an RSI of 99.4 — as high as this metric goes. It scores 100/100 on the Over-Hyped strategy, which specifically targets extended momentum names.
- **BDX** (Becton Dickinson) has an RSI of 0.2 — nearly as low as possible. It scores 83/100 on Falling Knife, which looks for deeply oversold names trading below their moving averages.

**Where it breaks:** RSI is a momentum indicator, not a valuation one. A biotech in a clinical trial can stay "overbought" for months if the news keeps coming. A blue chip can stay "oversold" for quarters during a prolonged sector rotation. RSI tells you *where the recent move has gone*, not *where the price will go next*.

**How it's used on this site:** RSI is a primary input for the [Moon Shot](/strategy/moon-shot/), [Falling Knife](/strategy/falling-knife/), and [Over-Hyped](/strategy/over-hyped/) strategies. See the [RSI glossary entry](/glossary/rsi/) for the full formula.

---

## Beta — Market Sensitivity

**What it is:** Beta measures how much a stock's price tends to move relative to the broader market (usually the S&P 500). A beta of 1.0 means the stock moves in line with the index. A beta of 2.0 means it tends to move twice as much in either direction.

**What the numbers mean:**
- **Beta > 1.5** — high volatility. The stock amplifies market moves. Gains can be bigger but so can losses.
- **Beta 0.5–1.0** — lower volatility than the market. Common in utilities, consumer staples, and high-dividend names.
- **Beta < 0** — inversely correlated with the market. Rare; examples include gold miners and some defensive ETFs during certain periods.

**Real examples from this dataset:**
- **OXLC** (Oxford Lane Capital) has a beta of 0.77. It's a high-yield closed-end fund and scores 100/100 on Dividend Daddy. Low beta is by design — the Dividend Daddy strategy specifically rewards stability.
- **NVDA** (Nvidia), with a market cap of $4.45T, has scores of 95/100 on Moon Shot and 60/100 on Over-Hyped. Its elevated beta is one reason it ranks so highly for growth-oriented strategies.

**Where it breaks:** Beta is calculated from historical price data, usually over 3–5 years. It reflects past behavior, not future behavior. A stock that was low-beta for years can become high-beta after a major business change. Beta also doesn't distinguish between upside and downside volatility — a stock that only goes up still has high beta.

**How it's used on this site:** Beta is central to [Dividend Daddy](/strategy/dividend-daddy/) (rewards low beta) and [Moon Shot](/strategy/moon-shot/) (rewards high beta). See the [beta glossary entry](/glossary/beta/).

---

## Moving Averages — 50-Day and 200-Day

**What they are:** A moving average smooths out daily price noise by averaging the closing price over a rolling window. The 50-day MA tracks medium-term trend; the 200-day MA tracks the long-term trend.

**What the relationship between price and MA tells you:**
- **Price above both MAs** — bullish trend. The stock is in an established uptrend at both timeframes.
- **Price below both MAs** — bearish trend. The stock is in a sustained downtrend.
- **Price below 50-day but above 200-day** — short-term weakness within a longer-term uptrend. A common setup for contrarian plays.
- **Price below both, RSI also low** — the setup that [Falling Knife](/strategy/falling-knife/) looks for specifically.

**Real example:** **WGO** (Winnebago Industries) has an RSI of 1.7 — one of the lowest in the dataset — and scores 90/100 on Falling Knife. A name like this has declined sharply and is trading well below its moving averages, which is exactly the profile the Falling Knife strategy surfaces.

**The "death cross" and "golden cross":** Two widely-watched events: when the 50-day crosses below the 200-day (death cross, bearish) or above (golden cross, bullish). These are lagging signals and can generate false positives in choppy markets, but they're widely followed enough that they become self-reinforcing at times.

**Where it breaks:** Moving averages are lagging indicators. They confirm a trend that already happened, they don't predict future direction. A stock can be "above its 200-day MA" while in the middle of a breakdown — it just takes time for the average to reflect the new reality.

**How it's used on this site:** Both MAs appear in the [Falling Knife](/strategy/falling-knife/) scoring algorithm. See glossary entries for [50-Day MA](/glossary/moving-average-50/) and [200-Day MA](/glossary/moving-average-200/).

---

## P/E Ratio and Forward P/E

**What they are:** The P/E (price-to-earnings) ratio divides the current stock price by trailing earnings per share. Forward P/E uses analyst estimates of future earnings rather than past results. Both measure how much investors are paying per dollar of earnings.

**What the numbers mean:**
- **P/E of 10–15** — historically considered "cheap." Common in mature industries with limited growth.
- **P/E of 20–30** — typical for solid growth companies.
- **P/E above 50** — either high-growth expectations are priced in, or earnings are temporarily depressed.
- **Negative or missing P/E** — the company is currently unprofitable. Many early-stage tech and biotech names have no P/E until they reach profitability.

**From the dataset:** Large-cap institutional names like **AAPL** (Apple, $3.76T market cap) and **MSFT** (Microsoft, $2.99T) score 99/100 on Institutional Whale — they have extensive analyst coverage, massive liquidity, and consistent earnings that support a meaningful P/E calculation. Their P/E ratios are tracked and updated in the daily pipeline.

**Forward P/E vs. trailing P/E:** Forward P/E is often lower than trailing P/E for growing companies (because future earnings are expected to be higher). When forward P/E is *higher* than trailing P/E, analysts expect earnings to fall — a potential yellow flag worth investigating.

**Where it breaks:** P/E is meaningless for unprofitable companies and can be distorted by one-time events (asset sales, write-downs, accounting changes). A single quarter of inflated earnings creates an artificially low P/E that disappears next quarter. Always look at the trend across multiple periods, not just the current number.

**How it's used on this site:** P/E and Forward P/E appear on ticker data pages for informational context. See the [P/E Ratio](/glossary/pe-ratio/) and [Forward P/E](/glossary/forward-pe/) glossary entries.

---

## Dividend Yield

**What it is:** Dividend yield is the annual dividend payment expressed as a percentage of the current stock price. A stock paying $2/year with a price of $50 has a 4% dividend yield.

**What the numbers mean:**
- **Yield 1–3%** — modest income component, typical of blue chips with growing dividends.
- **Yield 4–7%** — meaningful income. Common in REITs, utilities, and established dividend payers.
- **Yield above 10%** — high yield that warrants scrutiny. Is the dividend sustainable? High yields often reflect a falling stock price more than an increasing dividend.

**Real examples from this dataset:**
- **OXLC** yields 27.12% and scores 100/100 on Dividend Daddy. This is an extremely high yield — the Dividend Daddy strategy surfaces it, but the score is a measure of *how much the stock fits this strategy's profile*, not a recommendation that the yield is safe or the fund is well-managed.
- **FSK** and **CION** both yield above 22% and score 99/100 on Dividend Daddy. All three are closed-end credit funds with very different risk profiles than a consumer staples stock with a 3% yield.

**The yield trap:** Yield rises when stock price falls (if the dividend stays constant). A stock yielding 15% might have been a 4% yielder a year ago — and the high yield might be the market's way of saying it expects the dividend to be cut. Always check whether the dividend has been maintained or grown, not just the current headline number.

**How it's used on this site:** Dividend yield is the primary driver of the [Dividend Daddy](/strategy/dividend-daddy/) score. See the [dividend yield glossary entry](/glossary/dividend-yield/).

---

## Putting It All Together

No single indicator tells the whole story. The value in this site's strategy scores is that they combine multiple indicators into a single lens. But even that combination is a starting point, not a conclusion.

The [methodology page](/methodology/) explains exactly how each strategy uses these indicators. The [How to Read the Five Strategies](/articles/how-to-read-the-five-strategies/) article explains how to interpret score combinations responsibly.

Use these indicators to narrow your research — not to replace it.

---

## Further Reading

- [RSI glossary entry](/glossary/rsi/)
- [Beta glossary entry](/glossary/beta/)
- [50-Day Moving Average](/glossary/moving-average-50/) and [200-Day Moving Average](/glossary/moving-average-200/)
- [P/E Ratio](/glossary/pe-ratio/) and [Forward P/E](/glossary/forward-pe/)
- [Dividend Yield](/glossary/dividend-yield/)
- [Methodology — how scores are calculated](/methodology/)
- [Why some tickers have no scores](/articles/why-some-tickers-have-no-scores/)
