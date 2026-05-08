-- Preview what a rollback would remove for the given pipeline run IDs.
-- Used by: ticker-cli rollback --run-ids <ids> --dry-run
--
-- Python passes run_ids as a JSON array via json_each(?), e.g. '[51,52,54]'.
--
-- Interactive use (sqlite3 CLI):
--   sqlite3 data/market_data.db
--   SELECT * FROM pipeline_runs WHERE run_id IN (51, 52, 54);
--   SELECT COUNT(*) FROM ticker_sync_history WHERE run_id IN (51, 52, 54);

SELECT
    'pipeline_runs'       AS tbl,
    run_id                AS id,
    run_date,
    started_at,
    completed_at,
    status
FROM pipeline_runs
WHERE run_id IN (SELECT value FROM json_each(?))
UNION ALL
SELECT
    'ticker_sync_history' AS tbl,
    id,
    NULL,
    started_at,
    completed_at,
    status
FROM ticker_sync_history
WHERE run_id IN (SELECT value FROM json_each(?))
ORDER BY tbl, id;
