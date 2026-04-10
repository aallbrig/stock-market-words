# Status Command Database Initialization Clarity

**Status:** Accepted
**Author:** GitHub Copilot
**Created:** 2026-04-10

---

## Context

The `status` command's recommendation section (line 366–370 in `cli.py`) displays
"Database not initialized" for any database issue, including when migrations are
pending. This conflates two different problems:

1. **Schema not initialized**: Database file exists but has no tables → operator
   should run `python -m stock_ticker.cli init`
2. **Migrations pending**: Database schema exists with tables, but migrations
   haven't been applied → operator should run `python -m stock_ticker.cli migrate up`

When an operator sees "Database not initialized" but the database file contains
tables, they are confused about what action to take. This reduces clarity and
increases support burden.

Related migration code:
- `python3/src/stock_ticker/migrations.py` — `check_migrations_needed()`
- `python3/src/stock_ticker/cli.py` lines 224–228 — detects pending migrations
- `python3/src/stock_ticker/cli.py` lines 366–370 — blanket recommendation

---

## Goal

The `status` command's recommendation section must distinguish between database
schema not initialized vs. migrations pending, and recommend the correct action
for each case.

---

## Non-goals

- Changing the migration system itself.
- Changing the database initialization logic.
- Adding new database checks or validations.
- Changing the exit codes or overall status command behavior.

---

## User stories

- As an operator running `status`, I want to see a specific recommendation
  ("run `migrate up`") when migrations are pending, not a generic "database not
  initialized" message.
- As an operator with a truly uninitialized schema, I want to see a specific
  recommendation ("run `init`") so I know exactly what to do.

---

## Design

**Approach:** Track the reason for `db_issue = True` and use it in the
recommendation section.

### Changes to `python3/src/stock_ticker/cli.py`

1. Replace `db_issue: bool` with `db_issue_reason: str | None` (default `None`).
   Valid values:
   - `None` — no database issue
   - `"schema_missing"` — database file exists but no tables
   - `"tables_incomplete"` — tables exist but some expected tables are missing
   - `"migrations_pending"` — all tables present but migrations are pending
   - `"connection_error"` — cannot connect or other unexpected error

2. Update all `db_issue = True` assignments (lines 184, 204, 220, 228, 246) to
   set `db_issue_reason` to the appropriate reason string:
   - Line 184 (no DB_PATH) → `"schema_missing"`
   - Line 204 (no tables) → `"schema_missing"`
   - Line 220 (missing tables) → `"tables_incomplete"`
   - Line 228 (pending migrations) → `"migrations_pending"`
   - Line 246 (connection error) → `"connection_error"`

3. Update the recommendation section (lines 356–370) to check `db_issue_reason`
   and emit the appropriate message:
   ```python
   if db_issue_reason == "migrations_pending":
       logger.warning("   ⚠️  Database migrations pending")
       logger.info("   → Run migrations with: python -m stock_ticker.cli migrate up")
       sys.exit(3)
   elif db_issue_reason in ("schema_missing", "tables_incomplete"):
       logger.warning("   ⚠️  Database schema not initialized")
       logger.info("   → Initialize with: python -m stock_ticker.cli init")
       sys.exit(3)
   elif db_issue_reason == "connection_error":
       logger.warning("   ⚠️  Database connection error")
       logger.info("   → Check database file permissions and connectivity")
       sys.exit(3)
   ```

### Affected files

- `python3/src/stock_ticker/cli.py` (lines 104–246 in dependency check section,
  lines 356–370 in recommendation section)

---

## Verification

**Manual:**
1. With pending migrations, run `python -m stock_ticker.cli status` and verify
   the recommendation says "Run migrations with: python -m stock_ticker.cli
   migrate up" (not "Database not initialized").
2. With an uninitialized database (schema missing), run `status` and verify it
   says "Initialize with: python -m stock_ticker.cli init".
3. With a valid initialized database, run `status` and verify no database error
   messages appear.

**Automated:**
- No new tests required (this is a messaging change, not logic change).
- Existing tests for `status` command should still pass without modification.

---

## Open questions

- **Are there other `db_issue = True` cases I'm missing?** Default: scan all
  assignments in the function before implementing; add cases as discovered.

---

## Alternatives considered

1. **Create a custom exception hierarchy** (e.g., `SchemaMissingError`,
   `MigrationsPendingError`): Over-engineered for a CLI recommendation message;
   violates KISS principle. Rejected.

2. **Check migration status before checking schema**: Doesn't help — migration
   status query itself requires schema to exist. The current order is correct.
   Rejected.
