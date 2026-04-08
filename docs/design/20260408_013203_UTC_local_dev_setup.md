# Local Development Setup

**Status:** Design / Foundation
**Last updated:** 2026-04-08

Single source of truth for getting stockmarketwords.com running locally.
Replaces the scattered quick-starts in `README.md`, `python3/README.md`,
`tests/README.md`, and `TESTING.md`.

---

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Hugo (extended) | 0.120+ | Builds and serves the static site |
| Python | 3.10+ | The `ticker-cli` data pipeline |
| Node.js | 18+ | Test runners (Jest + Playwright/Puppeteer) |
| SQLite | bundled with Python | Database (`data/market_data.db`) |
| Ollama (optional) | latest | Local LLM for translation script (qwen2.5:7b) |

## First-time setup

```bash
# 1. Clone and enter the repo
git clone <repo> stock-market-words && cd stock-market-words

# 2. Python CLI
pip install -e python3/
ticker-cli --help                       # should print the Click help

# 3. Initialize the database (idempotent)
ticker-cli init

# 4. Run a small slice of the pipeline to populate sample data
ticker-cli run-all --limit 50
# This pulls FTP listings, fetches Yahoo data for ~50 tickers,
# scores them, and writes the JSON files Hugo needs.

# 5. Node deps for tests
npm install
```

## Run the website locally

```bash
cd hugo/site
hugo server
# Visit http://localhost:1313/
# Visit http://localhost:1313/zh-cn/ for the Chinese variant
```

Hugo's `--baseURL` override automatically switches to localhost — never
require environment variables for local dev to work. (See
`.github/copilot-instructions.md` for the rationale.)

## Refresh the data

```bash
# Full pipeline (run after market close)
ticker-cli run-all

# Or run individual steps
ticker-cli sync-ftp
ticker-cli extract-prices --limit 100
ticker-cli extract-metadata --limit 100
ticker-cli build
ticker-cli hugo all

# Check status
ticker-cli status
```

If you make a mistake, `ticker-cli reset --force` clears today's data
and lets you re-run the day from scratch.

## Run the tests

```bash
# JavaScript perf tests (Jest)
npm run test:perf

# E2E tests (Playwright/Puppeteer)
npm run test:e2e
npm run test:e2e:pages          # just the page-renders smoke
npm run test:e2e:ticker         # just the TickerEngine UI

# Python tests (pytest)
cd python3 && pytest
```

The E2E test runner auto-starts a local Hugo server when needed; you do not
have to run `hugo server` in a separate terminal. See `tests/README.md` for
the auto-server details.

## Optional: local LLM for translations

Some specs (e.g. the zh-CN content backfill) propose a `ticker-cli translate`
command that drives a local LLM via Ollama. To set up:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b              # or qwen2.5:14b for better quality
ollama run qwen2.5:7b "你好"          # smoke test
```

The translator script reads `STOCK_TRANSLATE_MODEL` from the environment;
default is `qwen2.5:7b`. You can also use any HF pipeline by setting
`STOCK_TRANSLATE_BACKEND=huggingface STOCK_TRANSLATE_MODEL=Helsinki-NLP/opus-mt-en-zh`.

## File locations to know

- SQLite DB: `data/market_data.db`
- Hugo content: `hugo/site/content/`
- Hugo layouts: `hugo/site/layouts/`
- Browser JS: `hugo/site/static/js/`
- JSON build artifacts: `hugo/site/static/data/` and `hugo/site/data/`
- Python CLI source: `python3/src/stock_ticker/`
- Test suites: `tests/perf/`, `tests/puppeteer/`

## Common gotchas

- **`hugo server` shows English content even on `/zh-cn/...` pages.** That
  page's `.zh-cn.md` is missing. See
  [`i18n_architecture.md`](./20260408_013203_UTC_i18n_architecture.md).
- **`ticker-cli run-all` says "step already completed."** That's the
  per-day idempotency guard. Use `--force` to re-run, or `reset --force` to
  start over for today.
- **`/tickers/<symbol>/` 404s after a fresh clone.** You haven't run
  `ticker-cli hugo all-tickers` yet — `all_tickers.json` is the data file
  the content adapter reads.
- **GA / AdSense not loading locally.** Expected — `googleAnalyticsId` is
  empty in dev. Production sets `HUGO_PARAMS_GOOGLEANALYTICSID` via env var.
