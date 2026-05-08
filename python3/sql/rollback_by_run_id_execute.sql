-- Remove pipeline run records for the given run IDs.
-- Used by: ticker-cli rollback --run-ids <ids>
-- Python passes run_ids as a JSON array via json_each(?), e.g. '[51,52,54]'.
--
-- IMPORTANT: ticker_sync_history must be deleted first (foreign key dependency).
-- daily_metrics and strategy_scores are intentionally NOT touched here —
-- those tables use (symbol, date) PKs and the data is effectively identical
-- across runs on the same trading day.

DELETE FROM ticker_sync_history
WHERE run_id IN (SELECT value FROM json_each(?));

DELETE FROM pipeline_runs
WHERE run_id IN (SELECT value FROM json_each(?));
