-- Migration 008: Backfill progress ledger
-- Used only by `ticker-cli backfill`; nothing in the daily run reads or writes these tables.
-- pipeline_steps is keyed by (step, run_date) and drives run-all's resume logic, so backfill
-- progress lives in its own tables rather than sharing it.

CREATE TABLE IF NOT EXISTS backfill_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    range_from DATE NOT NULL,
    range_to DATE NOT NULL,
    refetch INTEGER NOT NULL DEFAULT 0,
    symbol_limit INTEGER,             -- NULL for a full-universe run; set for --limit test runs
    target_dates TEXT NOT NULL,       -- JSON {"YYYY-MM-DD": "fill"|"replace"}, frozen when the run starts
    status TEXT NOT NULL,             -- 'running', 'failed', 'completed', 'abandoned'
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    symbols_total INTEGER NOT NULL DEFAULT 0,
    download_calls INTEGER NOT NULL DEFAULT 0,
    rows_written INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_backfill_runs_status ON backfill_runs (status, range_from);

CREATE TABLE IF NOT EXISTS backfill_symbols (
    run_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    rows_written INTEGER NOT NULL DEFAULT 0,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, symbol),
    FOREIGN KEY (run_id) REFERENCES backfill_runs (run_id)
);
