-- Migration 001: Deprecate sync_history table
-- This table is redundant with pipeline_steps and pipeline_runs tracking

DROP TABLE IF EXISTS sync_history;

