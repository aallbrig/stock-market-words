---
title: "About"
---

# Stock Market Words: A Ticker Discovery Tool

**Stock Market Words** is a playful experiment that finds valid stock ticker symbols hidden in everyday English words and text.

## What Does It Do?

1. **Ticker Extraction Tool** (Homepage): Paste any text and our algorithm will extract stock tickers using a word-consuming backtracking search. It shows you 5 different portfolio strategies, each optimized for different investment goals:
   - 💰 **Dividend Daddy**: High dividend yield + low volatility stocks
   - 🚀 **Moon Shot**: High growth potential (high beta + oversold)
   - 🔪 **Falling Knife**: Contrarian plays (oversold + below moving average)
   - 🎈 **Over-Hyped**: Overbought stocks (potential short candidates)
   - 🐋 **Institutional Whale**: Large-cap stocks with institutional backing

2. **Filtered Data View**: Browse all ~5,400+ filtered common stocks with price data, sortable and filterable by exchange.

3. **Raw FTP Data**: See the unfiltered data directly from NASDAQ before our filtering pipeline.

## How It Works

- **Data Source**: NASDAQ FTP server (daily ticker lists)
- **Filtering**: Removes ETFs, warrants, test tickers, bankrupt companies
- **Price Data**: Yahoo Finance API for real-time pricing
- **Algorithm**: Trie-based prefix search with backtracking to find non-overlapping ticker matches

## Why?

Because finding "NVDA" hidden in "NVIDIA" is more fun than it should be. Plus, I amuse myself thinking this might provide some sort of trading edge (it probably doesn't).

## Data Updates

Data is refreshed daily from NASDAQ FTP servers. Last update: Check the homepage for the latest timestamp.

---

*Disclaimer: This is for educational and entertainment purposes only. Not financial advice. Do your own research before making investment decisions.*
