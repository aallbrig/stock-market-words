---
title: "Data Sets"
layout: "page"
---

# Data Sets

View the different data sets used by the Stock Market Words ticker extraction tool.

## Raw Data

- **[Raw FTP Data](/raw-ftp-data/)** - Direct downloads from NASDAQ FTP (unprocessed)
- **[Filtered Tickers](/filtered-data/)** - Cleaned and filtered dataset (5,444 tickers)

## Strategy-Specific Data

Each strategy uses pre-filtered tickers that match specific investment criteria:

- **[💰 Dividend Daddy](/strategy-dividend-daddy/)** - High yield dividend stocks
- **[🚀 Moon Shot](/strategy-moon-shot/)** - High beta growth stocks
- **[🔪 Falling Knife](/strategy-falling-knife/)** - Oversold value opportunities  
- **[🎈 Over-Hyped](/strategy-over-hyped/)** - Overbought momentum plays
- **[🐋 Institutional Whale](/strategy-institutional-whale/)** - Large cap institutional favorites

## Data Pipeline

```
NASDAQ FTP Download
    ↓
Pass 1: Basic Validation
    ↓
Pass 2: Price Data Enrichment
    ↓
Strategy Filtering & Scoring
    ↓
Strategy-Specific Datasets
```

## Learn More

- [Strategy Filters Documentation](/strategies/) - How each strategy works
- [About](/about/) - Project overview
