-- Migration 007: Capture all Yahoo Finance data we were already fetching but discarding
-- All fields below come from requests already made in extract-prices and extract-metadata
-- with zero additional network calls.

-- ── extract_prices: yf.download() returns Open/High/Low/Close/AdjClose/Volume ───────
-- We only saved Close and Volume; now save the full OHLC + adjusted close.
ALTER TABLE daily_metrics ADD COLUMN open_price REAL;
ALTER TABLE daily_metrics ADD COLUMN high_price REAL;
ALTER TABLE daily_metrics ADD COLUMN low_price REAL;
ALTER TABLE daily_metrics ADD COLUMN adj_close REAL;

-- ── extract_metadata: yf.Ticker.info ─────────────────────────────────────────────────

-- Per-share earnings
ALTER TABLE daily_metrics ADD COLUMN trailing_eps REAL;
ALTER TABLE daily_metrics ADD COLUMN forward_eps REAL;
ALTER TABLE daily_metrics ADD COLUMN book_value REAL;

-- Absolute income statement (TTM) — enables Sankey diagram
ALTER TABLE daily_metrics ADD COLUMN total_revenue REAL;
ALTER TABLE daily_metrics ADD COLUMN gross_profit REAL;
ALTER TABLE daily_metrics ADD COLUMN ebitda REAL;
ALTER TABLE daily_metrics ADD COLUMN operating_cashflow REAL;
ALTER TABLE daily_metrics ADD COLUMN free_cashflow REAL;

-- Absolute balance sheet
ALTER TABLE daily_metrics ADD COLUMN total_cash REAL;
ALTER TABLE daily_metrics ADD COLUMN total_debt REAL;

-- Margin stack (gross and EBITDA; profit and operating already saved)
ALTER TABLE daily_metrics ADD COLUMN gross_margins REAL;
ALTER TABLE daily_metrics ADD COLUMN ebitda_margins REAL;

-- Ownership
ALTER TABLE daily_metrics ADD COLUMN held_percent_insiders REAL;
ALTER TABLE daily_metrics ADD COLUMN held_percent_institutions REAL;

-- Dividend detail (yield already saved; now add absolute rate, payout, and history)
ALTER TABLE daily_metrics ADD COLUMN dividend_rate REAL;
ALTER TABLE daily_metrics ADD COLUMN payout_ratio REAL;
ALTER TABLE daily_metrics ADD COLUMN five_year_avg_dividend_yield REAL;

-- Valuation
ALTER TABLE daily_metrics ADD COLUMN price_to_sales REAL;

-- Short interest (absolute; short_ratio and short_percent_float already saved)
ALTER TABLE daily_metrics ADD COLUMN shares_short INTEGER;

-- Momentum
ALTER TABLE daily_metrics ADD COLUMN week_52_change REAL;

-- ── extract_metadata: yf.Ticker.history() — computed, no extra requests ──────────────
ALTER TABLE daily_metrics ADD COLUMN hist_volatility REAL;   -- 20-day annualized log-return std
ALTER TABLE daily_metrics ADD COLUMN atr_14 REAL;            -- 14-day Average True Range

-- ── tickers: slowly-changing company attributes ───────────────────────────────────────
ALTER TABLE tickers ADD COLUMN country TEXT;
ALTER TABLE tickers ADD COLUMN full_time_employees INTEGER;

-- DOWN: SQLite does not support DROP COLUMN — one-way migration
