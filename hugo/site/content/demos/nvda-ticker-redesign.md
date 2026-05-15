---
title: "Ticker Page Redesign"
description: "Enriched NVDA ticker page with a 1-year D3 price chart, income statement Sankey diagram, full margin stack, and all new Yahoo Finance fields captured in migration 007."
symbol: "NVDA"
status: "prototype"
tags: ["d3", "sankey", "price-chart", "yfinance"]
schemas:
  - label: "TickerDetail"
    url: "/schemas/ticker_detail.schema.json"
  - label: "IncomeStatement"
    url: "/schemas/income_statement.schema.json"
---

This prototype shows what the ticker detail page looks like once we store the full Yahoo Finance data captured in migration 007:

- **Price chart** — 1-year daily close with MA50/MA200 overlays and 52W high/low markers
- **Sankey diagram** — income statement flow (Revenue → Gross Profit → Operating Income → Net Income) switchable across FY2023/2024/2025
- **Enriched fundamentals** — full margin stack, balance sheet snapshot, EPS, P/S, P/B, FCF, ownership breakdown
- **Multi-year income table** — 4-year trend with YoY deltas

The page pulls live data from Yahoo Finance via `yfinance` (`Ticker.info`, `Ticker.history`, `Ticker.income_stmt`) as of 2026-05-14.
