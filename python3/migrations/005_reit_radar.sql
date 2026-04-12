-- Migration 005: Add REIT Radar strategy support
-- Adds is_reit flag to tickers table and reit_radar_score to strategy_scores

-- Flag tickers identified as REITs (industry LIKE 'REIT%' from Yahoo Finance)
ALTER TABLE tickers ADD COLUMN is_reit INTEGER DEFAULT 0;

-- REIT Radar strategy score (NULL for non-REIT tickers)
ALTER TABLE strategy_scores ADD COLUMN reit_radar_score INTEGER;
