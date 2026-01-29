-- Migration 002: Add sector and industry to tickers table
-- These are slowly-changing dimensions that help with sector rotation strategies

ALTER TABLE tickers ADD COLUMN sector TEXT;
ALTER TABLE tickers ADD COLUMN industry TEXT;

