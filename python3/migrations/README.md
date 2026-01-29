# Database Migrations

This directory contains database schema migrations for the stock ticker application.

## Migration Files

Migrations are numbered sequentially and applied in order:

- `001_deprecate_sync_history.sql` - Remove redundant sync_history table
- `002_add_sector_industry.sql` - Add sector/industry columns to tickers
- `003_expand_daily_metrics.sql` - Add 24 new data fields from Yahoo Finance

## Running Migrations

### Check migration status
```bash
python3 -m stock_ticker status
```

If migrations are pending, the status command will show:
```
⚠️  Database migrations needed! Run: python3 -m stock_ticker migrate up
```

### Apply pending migrations
```bash
python3 -m stock_ticker migrate up
```

### Rollback last migration
```bash
python3 -m stock_ticker migrate down
```

### View migration history
```bash
python3 -m stock_ticker migrate status
```

## Creating New Migrations

1. Create a new file: `migrations/NNN_description.sql` (increment NNN)
2. Write the migration SQL
3. Add comments for UP (apply) and DOWN (revert) sections
4. Test on a copy of the database first!

## Notes

- **SQLite limitations**: SQLite doesn't support `DROP COLUMN`, so most migrations are one-way
- **Idempotent**: Migrations use `IF EXISTS` / `IF NOT EXISTS` where possible
- **Tracked in DB**: Applied migrations are stored in `schema_migrations` table
- **Safe to re-run**: The migration system is idempotent - already-applied migrations are skipped
