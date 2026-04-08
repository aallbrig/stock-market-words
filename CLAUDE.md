
## Project Map (read these first)

stockmarketwords.com is a Hugo static site (`hugo/site/`) fed by a Python
CLI (`python3/`, entry point `ticker-cli`) that runs after each US trading
day, persisting state in a SQLite database (`data/market_data.db`) and
emitting JSON build artifacts that Hugo consumes. The site is multilingual
(English + Simplified Chinese) using Hugo's built-in i18n.

Foundation docs (read in order if you're new):

1. [`docs/design/20260408_013203_UTC_architecture_overview.md`](docs/design/20260408_013203_UTC_architecture_overview.md) — system map, where things live, what's hand-authored vs CLI-generated.
2. [`docs/design/20260408_013203_UTC_data_pipeline.md`](docs/design/20260408_013203_UTC_data_pipeline.md) — full `ticker-cli` command list and the FTP → SQLite → JSON → Hugo flow.
3. [`docs/design/20260408_013203_UTC_database_schema.md`](docs/design/20260408_013203_UTC_database_schema.md) — the six SQLite tables.
4. [`docs/design/20260408_013203_UTC_i18n_architecture.md`](docs/design/20260408_013203_UTC_i18n_architecture.md) — how zh-CN works today, what's broken, conventions for new content.
5. [`docs/design/20260408_013203_UTC_local_dev_setup.md`](docs/design/20260408_013203_UTC_local_dev_setup.md) — quickstart and prereqs.
6. [`docs/design/20260408_013203_UTC_deployment.md`](docs/design/20260408_013203_UTC_deployment.md) — how a change in `main` becomes a live deploy (incomplete, has TODOs).

Spec-driven development: feature work begins with a spec under
[`docs/specs/`](docs/specs/README.md). Read that README for the template
and lifecycle. Active specs:

- [zh-CN content backfill](docs/specs/zhcn_content_backfill.md)
- [zh-CN ticker pages](docs/specs/zhcn_ticker_pages.md)
- [Extract Tickers analytics](docs/specs/extract_tickers_analytics.md)

## Documentation

When creating documentation files:

- Place them in the `docs/` directory or a subdirectory.
- **For `docs/design/` and `docs/research/`:** prepend a UTC timestamp to the filename in the format `YYYYMMDD_HHMMSS_UTC_` so files sort chronologically (e.g., `docs/design/20260329_150800_UTC_architecture_overview.md`).
- **For `docs/specs/`:** use simple slugs without timestamps (e.g., `docs/specs/zhcn_content_backfill.md`). Specs are versioned by their "Status" field and links to "Supersedes"/"Superseded by", not timestamps.

