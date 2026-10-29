# Stock Market Words: A Website
Why? Why not. I remembered reading about how linux has a file with a dictionary in it.

I amuse myself imagining this list providing some sort of trading edge for any type of investor.

## Links

### [Stock Market Words](https://stockmarketwords.com)
Production site: https://stockmarketwords.com

![QR Code for stockmarketwords.com](./hugo/site/static/media/stockmarketwords.com.qr.png)

*Scan to visit on mobile*

## Developer Section

### Performance Testing & Profiling

The TickerEngine algorithm can be performance tested and profiled. See the [Performance Profiling Guide](./docs/profiling-guide.md) for detailed instructions on:
- Running performance tests with sample texts
- Profiling with Node.js and Chrome DevTools
- Using WebStorm's built-in profiler (recommended for WebStorm users)
- Identifying and fixing bottlenecks

Quick start:
```bash
# Run unit performance tests (fast - tests algorithm directly)
npm run test:perf

# Run E2E performance tests (requires Hugo server running)
# First start the server: ./scripts/website-up.sh
npm run test:e2e:ticker       # 60s timeout (local dev)
npm run test:e2e:ci           # 10s timeout (CI-optimized)

# Run page load tests (ensures all pages work without errors)
npm run test:e2e:pages

# Profile with Node.js built-in profiler
node --prof node_modules/.bin/jest tests/perf/
node --prof-process isolate-*.log > profile.txt
```

**Test Status:**
- ✅ Unit tests: All passing (~20ms with mock data)
- ❌ E2E ticker tests: MEDIUM/LONG samples timeout after 60s (needs optimization!)
- ✅ E2E page tests: **All 23 tests passing!** (jQuery errors fixed)

**CI/CD Configuration:**
- GitHub Actions uses **10-second timeout** to conserve minutes
- Local development uses 60-second timeout
- Configurable via `TIMEOUT_SECONDS` environment variable

**Test Reports:**
- HTML reports generated automatically in `test-reports/index.html`
- Open in browser after running tests to see detailed results
- GitHub Actions uploads reports as artifacts
- See [docs/test-reports-guide.md](./docs/test-reports-guide.md) for details

See [tests/README.md](./tests/README.md) for complete test suite documentation.

### Hugo Site Development

The website is built using [Hugo](https://gohugo.io/), a fast static site generator.

**Running the development server:**

```bash
# Option 1: Change directory and run
cd hugo/site
hugo server

# Option 2: Run from repo root with flags
hugo server --source hugo/site

# Option 3: Run with additional flags (bind to all interfaces, custom port)
cd hugo/site
hugo server --bind 0.0.0.0 --port 1313
```

The site will be available at `http://localhost:1313` with live reload enabled.

**Building for production:**

```bash
# Option 1: From hugo/site directory
cd hugo/site
hugo

# Option 2: From repo root
hugo --source hugo/site

# Built files will be in hugo/site/public/
```

### Hugo Project Structure

```
hugo/site/
├── content/              # Markdown content files
├── layouts/              # HTML templates
│   ├── shortcodes/      # Reusable content widgets
│   ├── partials/        # Shared template components
│   └── _default/        # Default layouts
├── static/              # Static assets (CSS, JS, images, API data)
└── hugo.toml            # Site configuration
```

### Getting Started

**Local Development (Hugo website):**
```bash
# Start Hugo development server
./scripts/website-up.sh
# Or manually:
cd hugo/site && hugo server

# Stop Hugo server
./scripts/website-down.sh
# Or: pkill -f "hugo server"
```

**Data Pipeline (Python CLI):**
```bash
cd python3
./run.sh status        # Check system status
./run.sh run-all       # Run full data extraction pipeline

# Clean today's data before running (use when data is corrupted or incomplete)
./run.sh run-all --clean

# See the --clean flag guide for more options
# docs/CLEAN_FLAG_GUIDE.md
```

**Testing:**
```bash
npm test               # All tests
npm run test:e2e       # E2E tests (requires Hugo server)
```

Python CLI (Data Pipeline)
```bash
# Change to python3 directory
cd python3

# Install requirements
pip3 install -r requirements.txt

# Run CLI commands
python -m stock_ticker.cli status        # Check system status
python -m stock_ticker.cli run-all       # Run full data pipeline
python -m stock_ticker.cli run-all --clean  # Reset today's data before running

# Or use convenience wrapper
./run.sh status
./run.sh run-all
./run.sh run-all --clean

# See all commands
./run.sh --help
```

**Pipeline Data Management:**
- Use `--clean` flag to reset today's data before running
- Useful when downloads are interrupted or data looks corrupted
- Only removes today's data, never previous days
- See [docs/CLEAN_FLAG_GUIDE.md](./docs/CLEAN_FLAG_GUIDE.md) for details

### Backfilling missed days

`backfill` fills NYSE sessions that are missing from, or only partly present in, `daily_metrics`
(for example after weeks without a run), then refreshes the price-derived data for the rows it wrote.

```bash
# What is missing, and how many Yahoo requests would it take? (writes nothing)
task backfill -- --from 2026-01-02 --dry-run

# Fill it. Re-running resumes an interrupted run and is otherwise a no-op.
task backfill -- --from 2026-01-02 [--to 2026-10-28] [--strategy pia-vpn]
```

- **Gaps:** a session is flagged when it has no rows, fewer than 85% of the median of the 5 nearest
  populated dates on each side, fewer than 75% of the ticker universe, or when its prices were
  captured before that session's close (the daily run replaces such rows itself the same evening).
  Rows stamped on weekends and holidays are reported and left alone.
- **Requests:** one `yf.download` call per 100 tickers covers the whole date range (plus 320 days of
  lookback for MA-200). yfinance sends one chart request per ticker inside that call, so a full run is
  about one request per ticker, not one per ticker per day.
- **Writes:** prices go through the same row builder as `extract_prices`, upserted on `(symbol, date)`.
  Absent rows are inserted, existing rows and all fundamentals are left alone. Only sessions captured
  before the close have their price columns replaced. `--refetch` replaces every session in the range.
- **Resume:** progress is journaled in `backfill_runs` / `backfill_symbols` (migration 008, created on
  first use). Throttled tickers back off through `retry.py` (or the `pia-vpn` strategy); if the budget
  runs out the run stops and the same command picks up at the next ticker. `--restart` discards it.
- **Derived data:** RSI-14, MA-50, MA-200, volatility and ATR are recomputed from the downloaded bars
  for the rows written, and `strategy_scores` is re-ranked for replaced sessions that have fundamentals.
  Fundamentals (market cap, beta, yield, ...) are point-in-time Yahoo snapshots that cannot be
  recovered for a past date, so backfilled rows have none and get no scores. If a recent session
  changed, run `ticker-cli build && ticker-cli generate-hugo`.
- Set `STOCK_TICKER_DB=/path/to/copy.db` to point any command at a copy of the database.

### Developer quick commands
```bash
# Preferred Development Command (Hugo website)
cd hugo/site
hugo server

# Run tests
npm test              # All tests
npm run test:perf     # Performance tests only
npm run test:e2e      # E2E tests (requires Hugo server running)
```

### Current Status

**✅ Completed Features:**
- Website deployed to GitHub Pages at [stockmarketwords.com](https://stockmarketwords.com)
- Data pipeline extracts tickers from NASDAQ FTP
- Strategy-based filtering (5 investment strategies)
- Interactive ticker extraction tool
- Performance-optimized data loading
- Comprehensive E2E test suite
- Google Analytics tracking

**📊 Data Pipeline:**
- Python CLI tool for data extraction and processing
- FTP sync from NASDAQ (daily ticker lists)
- Yahoo Finance API integration for metrics
- Strategy scoring algorithm (5 strategies)
- Hugo site content generation

**🧪 Testing:**
- 23 E2E tests (Jest + Puppeteer)
- Performance tests for TickerEngine
- Test reports with HTML output

See [TESTING.md](./TESTING.md) for test documentation.

### Future Enhancements

**Data Features:**
- [ ] Add historical price charts
- [ ] Add sector/industry filtering
- [ ] Add market cap filtering
- [ ] Add dividend history
- [ ] Real-time data updates (WebSocket)

**UI Features:**
- [ ] Dark mode toggle
- [ ] Save/export ticker portfolios
- [ ] Comparison tool for multiple tickers
- [ ] Mobile app (PWA)

**API:**
- [ ] Public REST API for ticker data
- [ ] API documentation page
- [ ] Rate limiting and authentication
- [ ] CSV/JSON export endpoints
    - [ ] /api/stocks?filter[]=NASDAQ&filter[]=NYSE&filter[]=AMEX
    - [ ] /api/stocks.json or /api/stocks?format=json
    - [ ] /api/stocks.csv or /api/stocks?format=csv
    - [ ] /api/stocks.xml or /api/stocks?format=xml
    - [ ] /api/stocks.txt or /api/stocks?format=txt
    - [ ] /api/stocks.html or /api/stocks?format=html
- [ ] Terraform exists to generate AWS resources
    - [ ] S3 bucket (for public website assets
    - [ ] Route 53 DNS configuration (link domain to S3 bucket)
- [ ] Website is deployed to AWS S3 using Github Actions
- [ ] Amazon associates product links? (Maybe book links? Investor books? Linux books? An investor related toy?)

### Resources
- https://github.com/rreichel3/US-Stock-Symbols
- /usr/share/dict/words (location of dictionary file on my mac)
- https://gist.github.com/mgeeky/cebe7a05557569008c892e2130ec1ec9
