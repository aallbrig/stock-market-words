-- Migration 006: Add business_summary to tickers table
-- Populated from Yahoo Finance longBusinessSummary in Pass 2 (no extra request).

ALTER TABLE tickers ADD COLUMN business_summary TEXT;
