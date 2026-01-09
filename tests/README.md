# Test Suite Overview

This directory contains all automated tests for the Stock Market Words project.

## Test Structure

```
tests/
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
npm run test:e2e               # All E2E tests (requires Hugo server)
npm run test:e2e:pages         # Just page load tests
npm run test:e2e:ticker        # Just ticker performance tests

# Verbose output
npm run test:perf:verbose
npm run test:e2e:verbose
```

### E2E Test Requirements

E2E tests require the Hugo development server to be running:

```bash
# Terminal 1: Start Hugo server
./scripts/website-up.sh

# Terminal 2: Run E2E tests
npm run test:e2e
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
- 60-second timeout enforcement
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

1. Make changes to TickerEngine.js
2. Run unit tests for quick feedback: `npm run test:perf`
3. If passing, run E2E tests: `npm run test:e2e:ticker`
4. Iterate until E2E tests pass

### Before Committing

```bash
# Start Hugo server
./scripts/website-up.sh

# Run all tests
npm run test:perf && npm run test:e2e
```

### CI/CD Integration

These tests can be integrated into GitHub Actions or other CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Install dependencies
  run: npm install
  
- name: Start Hugo server
  run: ./scripts/website-up.sh &
  
- name: Wait for server
  run: sleep 5
  
- name: Run tests
  run: npm test
```

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
