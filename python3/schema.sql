-- Table 1: Static Identity (The "Phonebook")
-- Stores names and exchange info. Updates only when FTP changes.
CREATE TABLE IF NOT EXISTS tickers (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    exchange TEXT,
    is_etf BOOLEAN,
    first_seen DATE DEFAULT CURRENT_DATE
);

-- Table 2: Daily Snapshot (The "Heartbeat")
-- Stores the high-churn data. One row per ticker per day.
CREATE TABLE IF NOT EXISTS daily_metrics (
    symbol TEXT,
    date DATE,
    price REAL,
    volume INTEGER,
    market_cap REAL,
    dividend_yield REAL,
    beta REAL,
    rsi_14 REAL,
    ma_200 REAL,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES tickers (symbol)
);

-- Index for fast lookup during the 'build' command
CREATE INDEX IF NOT EXISTS idx_date_filter ON daily_metrics (date, price, volume);

-- Table 3: Strategy Scores (The "Brain")
-- Stores the normalized 1-100 scores we calculated in Python.
-- This makes the 'build' step lightning fast.
CREATE TABLE IF NOT EXISTS strategy_scores (
    symbol TEXT,
    date DATE,
    dividend_daddy_score INTEGER,
    moon_shot_score INTEGER,
    falling_knife_score INTEGER,
    over_hyped_score INTEGER,
    inst_whale_score INTEGER,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES tickers (symbol)
);

-- Table 4: FTP Sync Tracking
-- Tracks when we last synced the FTP lists
CREATE TABLE IF NOT EXISTS sync_history (
    sync_date DATE PRIMARY KEY,
    tickers_synced INTEGER,
    sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 5: Pipeline Step Tracking
-- Tracks when each pipeline step was completed for the current date
CREATE TABLE IF NOT EXISTS pipeline_steps (
    step_name TEXT,
    run_date DATE,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tickers_processed INTEGER,
    status TEXT,
    PRIMARY KEY (step_name, run_date)
);

-- Table 6: Pipeline Run History
-- Tracks complete pipeline runs with metrics and status
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATE NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,  -- 'pending', 'completed', 'failed'
    failed_step TEXT,
    nasdaq_ftp_reachable BOOLEAN,
    yahoo_finance_reachable BOOLEAN,
    total_requests INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0,
    total_bytes_downloaded INTEGER DEFAULT 0,
    tickers_processed_prices INTEGER DEFAULT 0,
    tickers_processed_metadata INTEGER DEFAULT 0,
    timing_sync_ftp REAL,
    timing_extract_prices REAL,
    timing_extract_metadata REAL,
    timing_build REAL,
    timing_generate_hugo REAL,
    timing_total REAL
);

-- Table 7: Ticker Sync History
-- Tracks success/failure state of each ticker for each Yahoo Finance sync operation
CREATE TABLE IF NOT EXISTS ticker_sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    sync_type TEXT NOT NULL,  -- 'price' or 'metadata'
    symbol TEXT NOT NULL,
    batch_number INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,  -- 'pending', 'success', 'failed'
    error_message TEXT,
    bytes_downloaded INTEGER DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id),
    FOREIGN KEY (symbol) REFERENCES tickers (symbol)
);

-- Index for fast lookup of ticker sync history
CREATE INDEX IF NOT EXISTS idx_ticker_sync_run ON ticker_sync_history (run_id, sync_type);
CREATE INDEX IF NOT EXISTS idx_ticker_sync_symbol ON ticker_sync_history (symbol, sync_type, completed_at);
