-- Migration 004: Add translation job tracking tables
-- Supports ticker-cli translate: parallel, SQLite-backed ETA heuristics

CREATE TABLE IF NOT EXISTS translate_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT    NOT NULL UNIQUE,
    started_at      REAL    NOT NULL,
    completed_at    REAL,
    status          TEXT    NOT NULL DEFAULT 'running',
    languages       TEXT    NOT NULL,
    model           TEXT    NOT NULL,
    backend         TEXT    NOT NULL,
    workers         INTEGER NOT NULL,
    total_files     INTEGER NOT NULL,
    completed_files INTEGER NOT NULL DEFAULT 0,
    failed_files    INTEGER NOT NULL DEFAULT 0,
    skipped_files   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS translate_file_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT    NOT NULL REFERENCES translate_runs(run_id),
    source_path      TEXT    NOT NULL,
    target_path      TEXT    NOT NULL,
    language         TEXT    NOT NULL,
    model            TEXT    NOT NULL,
    worker_id        INTEGER,
    queued_at        REAL    NOT NULL,
    started_at       REAL,
    completed_at     REAL,
    status           TEXT    NOT NULL DEFAULT 'queued',
    duration_seconds REAL,
    input_chars      INTEGER,
    output_chars     INTEGER,
    attempt          INTEGER NOT NULL DEFAULT 1,
    error_message    TEXT
);

CREATE INDEX IF NOT EXISTS idx_translate_file_jobs_language_model
    ON translate_file_jobs (language, model, status);
