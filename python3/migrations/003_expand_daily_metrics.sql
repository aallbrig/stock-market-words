-- Migration 003: Expand daily_metrics with additional Yahoo Finance data
-- All fields below are available from ticker.info without additional API calls

-- Valuation metrics
ALTER TABLE daily_metrics ADD COLUMN pe_ratio REAL;
ALTER TABLE daily_metrics ADD COLUMN forward_pe REAL;
ALTER TABLE daily_metrics ADD COLUMN price_to_book REAL;
ALTER TABLE daily_metrics ADD COLUMN peg_ratio REAL;
ALTER TABLE daily_metrics ADD COLUMN enterprise_value REAL;

-- 52-week price range
ALTER TABLE daily_metrics ADD COLUMN week_52_high REAL;
ALTER TABLE daily_metrics ADD COLUMN week_52_low REAL;

-- Volume metrics
ALTER TABLE daily_metrics ADD COLUMN avg_volume_10day INTEGER;

-- Short interest
ALTER TABLE daily_metrics ADD COLUMN short_ratio REAL;
ALTER TABLE daily_metrics ADD COLUMN short_percent_float REAL;

-- Financial health
ALTER TABLE daily_metrics ADD COLUMN debt_to_equity REAL;
ALTER TABLE daily_metrics ADD COLUMN current_ratio REAL;
ALTER TABLE daily_metrics ADD COLUMN quick_ratio REAL;

-- Profitability metrics
ALTER TABLE daily_metrics ADD COLUMN profit_margin REAL;
ALTER TABLE daily_metrics ADD COLUMN operating_margin REAL;
ALTER TABLE daily_metrics ADD COLUMN return_on_equity REAL;
ALTER TABLE daily_metrics ADD COLUMN return_on_assets REAL;

-- Growth metrics
ALTER TABLE daily_metrics ADD COLUMN revenue_growth REAL;
ALTER TABLE daily_metrics ADD COLUMN earnings_growth REAL;

-- Analyst data
ALTER TABLE daily_metrics ADD COLUMN target_mean_price REAL;
ALTER TABLE daily_metrics ADD COLUMN recommendation_mean REAL;
ALTER TABLE daily_metrics ADD COLUMN num_analyst_opinions INTEGER;

-- Trading metrics
ALTER TABLE daily_metrics ADD COLUMN ma_50 REAL;
ALTER TABLE daily_metrics ADD COLUMN shares_outstanding INTEGER;
ALTER TABLE daily_metrics ADD COLUMN float_shares INTEGER;

-- DOWN: SQLite doesn't support DROP COLUMN
-- This is a one-way migration
