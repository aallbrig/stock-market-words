# Test Suite Overview

This directory contains all automated tests for the Stock Market Words project.

## Test Structure

```
tests/
├── test-server.js                 # Test server management utility
├── perf/                          # Unit performance tests
│   └── TickerEngine.perf.test.js  # Algorithm performance tests
└── puppeteer/                     # E2E browser tests
    ├── ticker-ui.e2e.test.js      # Ticker extraction tool performance
    └── website-pages.e2e.test.js  # Basic page load & error tests
```

## Running Tests

### Quick Commands

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:perf              # Unit performance tests (fast)
npm run test:e2e               # All E2E tests (auto-manages server)
npm run test:e2e:pages         # Just page load tests
npm run test:e2e:ticker        # Just ticker performance tests

# CI-optimized (10-second timeout)
npm run test:e2e:ci            # Page load tests with 10s timeout

# Test against deployed QA site
npm run test:e2e:qa            # Tests against GitHub Pages

# Custom timeout
TIMEOUT_SECONDS=10 npm run test:e2e:ticker  # 10s timeout
TIMEOUT_SECONDS=120 npm run test:e2e:ticker # 120s timeout

# Test against custom URL
TEST_URL=https://example.com START_SERVER=false npm run test:e2e
```

## Test Server Management

The test suite now includes automatic server management via `test-server.js`.

### Environment Variables

- **TEST_URL**: Override base URL (e.g., `https://stockmarketwords.com/`)
  - When set, tests use this URL instead of starting a local server
- **START_SERVER**: Set to `'false'` to skip server startup (default: `'true'`)
- **SERVER_PORT**: Port for local server (default: `8668`)
- **SERVER_HOST**: Host for local server (default: `127.0.0.1`)
- **TIMEOUT_SECONDS**: Max processing time in seconds (default: `60`)

### How It Works

1. **Local Testing (default)**: Tests automatically start/stop Hugo server
2. **Remote Testing**: Set `TEST_URL` to test against deployed site
3. **Manual Server**: Set `START_SERVER=false` if you're running Hugo manually

### Examples

```bash
# Auto-managed local server (default)
npm run test:e2e

# Test against production site
TEST_URL=https://stockmarketwords.com/ START_SERVER=false npm run test:e2e

# Test against QA deployment
TEST_URL=https://aallbrig.github.io/stock-market-words/ START_SERVER=false npm run test:e2e

# Test with manual server (you start Hugo yourself)
START_SERVER=false npm run test:e2e

# Custom port
SERVER_PORT=8080 npm run test:e2e
```

## E2E Test Requirements

### Option 1: Auto-Managed Server (Recommended)
Just run tests - server starts/stops automatically:
```bash
npm run test:e2e
```

### Option 2: Manual Server
```bash
# Terminal 1: Start Hugo server
./scripts/website-up.sh

# Terminal 2: Run tests
START_SERVER=false npm run test:e2e
```

### Option 3: Test Remote Site
```bash
# Test against deployed site
npm run test:e2e:qa
```

## Test Suites Explained

### 1. Unit Performance Tests (`tests/perf/`)

**Purpose:** Test the TickerEngine algorithm directly with mock data for fast iteration.

**What it tests:**
- Algorithm execution time with 3 sample texts (SHORT, MEDIUM, LONG)
- All 5 investment strategies
- Cache behavior
- Sequential execution

**Status:** ✅ PASSING (algorithm is fast with small mock dataset)

**Run:** `npm run test:perf`

---

### 2. Ticker UI E2E Tests (`tests/puppeteer/ticker-ui.e2e.test.js`)

**Purpose:** Test the actual UI with real ticker data to validate production performance.

**What it tests:**
- Clicking sample text buttons
- Form submission
- Processing time with real ticker database
- **Timeout enforcement** (60s local, 10s CI - configurable via `TIMEOUT_SECONDS` env var)
- Result rendering

**Status:** ⚠️ PARTIALLY FAILING
- SHORT sample: ✅ PASSES (~1s)
- MEDIUM sample: ❌ FAILS (timeout after 60s)
- LONG sample: ❌ FAILS (timeout after 60s)

**Why failing:** The algorithm is too slow with the complete ticker database (thousands of tickers vs ~20 in mock data).

**Goal:** Optimize TickerEngine.js until all samples pass under 60 seconds.

**Run:** `npm run test:e2e:ticker`

---

### 3. Website Pages E2E Tests (`tests/puppeteer/website-pages.e2e.test.js`)

**Purpose:** Ensure all website pages load correctly with no JavaScript errors.

**What it tests:**
- ✅ HTTP 200 responses
- ✅ Page titles
- ✅ No console errors
- ✅ Navigation structure
- ✅ Content presence
- ✅ CSS/JS asset loading
- ✅ Responsive design (mobile/desktop)
- ✅ SEO meta tags
- ✅ Accessibility (headings, link text)
- ✅ Load time performance

**Pages tested:**
- `/` (Home)
- `/about/` (About)
- `/raw-ftp-data/` (Raw FTP Data)
- `/filtered-data/` (Filtered Data)

**Status:** ✅ **ALL PASSING** (23/23 tests pass)

**Fixed Issues:**
- ✅ jQuery loading errors fixed
- ✅ DataTables initialization errors handled
- ✅ 404 errors for missing data files filtered (expected in dev)

**Run:** `npm run test:e2e:pages`

---

## Test Results Summary

| Test Suite | Status | Pass Rate | Notes |
|------------|--------|-----------|-------|
| Unit Performance | ✅ PASSING | 13/13 | Fast with mock data |
| Ticker UI E2E | ❌ FAILING | 4/7 | MEDIUM/LONG samples timeout |
| Website Pages E2E | ✅ **ALL PASSING** | **23/23** | **jQuery errors fixed!** |

## Known Issues

### 1. TickerEngine Performance (HIGH PRIORITY)
- **Issue:** Algorithm takes 60+ seconds on MEDIUM/LONG sample texts
- **Impact:** Poor user experience
- **Location:** `hugo/site/static/js/TickerEngine.js`
- **Fix:** Optimize algorithm (see profiling-guide.md)

### 2. ~~jQuery Not Defined~~ ✅ FIXED
- ~~**Issue:** jQuery errors on Raw FTP Data and Filtered Data pages~~
- ~~**Impact:** Potential functionality issues~~
- ~~**Location:** `/raw-ftp-data/` and `/filtered-data/` pages~~
- **Status:** ✅ Fixed by loading jQuery before DataTables

## Continuous Testing Workflow

### During Development

1. Make changes to code
2. Run tests: `npm run test:e2e` (server auto-managed)
3. Iterate until tests pass

### Before Committing

```bash
# Run all tests (server auto-managed)
npm run test:perf && npm run test:e2e
```

### CI/CD Integration

Tests now automatically manage the Hugo server. No manual server setup needed!

#### GitHub Actions Workflows

1. **E2E Tests** (`.github/workflows/e2e-tests.yml`)
   - Runs on push/PR to main/develop
   - Tests local build with auto-managed server
   - Fast CI-optimized timeouts

2. **QA Tests** (`.github/workflows/qa-tests.yml`)
   - Runs after deployment to GitHub Pages
   - Tests live QA site: `https://aallbrig.github.io/stock-market-words/`
   - Auto-extracts URL from repository info
   - Waits for deployment to be available

3. **Website Acceptance Tests** (`.github/workflows/website-acceptance-tests.yml`)
   - Runs after QA deployment completes
   - Tests both stage (GitHub Pages) and production (stockmarketwords.com)
   - Uses acceptance-tests directory with Mocha/Puppeteer

4. **Website QA Deploy** (`.github/workflows/website-qa-deploy.yml`)
   - Builds and deploys to GitHub Pages
   - Triggers QA Tests and Acceptance Tests workflows on success

## Performance Profiling

See [../docs/profiling-guide.md](../docs/profiling-guide.md) for detailed instructions on:
- Using Node.js built-in profiler
- Chrome DevTools profiling
- WebStorm profiler (recommended)
- Identifying and fixing bottlenecks

Quick start:
```bash
npm run profile
node --prof-process isolate-*.log > profile.txt
less profile.txt
```

## Adding New Tests

### Adding a New Page Test

Edit `tests/puppeteer/website-pages.e2e.test.js`:

```javascript
const PAGES = [
  { path: '/', name: 'Home' },
  { path: '/about/', name: 'About' },
  // Add your new page here
  { path: '/new-page/', name: 'New Page' }
];
```

### Adding a New Test Suite

1. Create new file in appropriate directory:
   - Unit tests: `tests/perf/new-test.test.js`
   - E2E tests: `tests/puppeteer/new-test.e2e.test.js`

2. Follow existing patterns (use Puppeteer for E2E)

3. Update this README with new test info

## Troubleshooting

### E2E Tests Timeout
- Ensure Hugo server is running
- Check server is on correct port (8668)
- Verify network connectivity: `curl http://localhost:8668`

### Tests Pass Locally But Fail in CI
- Check CI environment has Hugo installed
- Ensure sufficient timeout values
- Verify all assets are committed (data files, etc.)

### Puppeteer Issues
- Update to latest: `npm install puppeteer@latest`
- Check Chrome/Chromium version compatibility
- Try running with `headless: false` for debugging

## Resources

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Puppeteer Documentation](https://pptr.dev/)
- [Hugo Testing Best Practices](https://gohugo.io/hosting-and-deployment/hugo-deploy/)
- [Performance Profiling Guide](../docs/profiling-guide.md)
