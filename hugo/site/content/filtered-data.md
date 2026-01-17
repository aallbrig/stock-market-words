---
title: "Filtered Ticker Data"
description: "Ticker data after Pass 1 filtering and price extraction"
date: 2026-01-17T15:09:04.218367
type: "page"
layout: "filtered-data"
---

This page shows the ticker data **after** filtering has been applied.

## Filtering Pipeline

1. **Test Issue Filter**: Removes test tickers (ZZZZ, TEST, etc.)
2. **ETF Filter**: Removes ETFs (common stocks only)
3. **Financial Status Filter**: Removes bankrupt/deficient tickers
4. **Keyword Filter**: Removes Units, Warrants, Rights, Preferred Stock
5. **Symbol Validation**: Removes invalid symbols and suffixes

## Pass 1: Price Extraction

After filtering, price/volume data is extracted from Yahoo Finance for all remaining tickers.

