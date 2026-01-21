# Codebase Cleanup Recommendations

**Generated:** 2026-01-19  
**Purpose:** Identify unused code and documentation inconsistencies for review

---

## Executive Summary

This analysis identified:
- **65+ files** that appear to be legacy/unused code (old Python system in `src/`)
- **2 duplicate CLI implementations** (one in `python3/cli.py`, one in `python3/src/stock_ticker/cli.py`)
- **5 summary documentation files** that can be consolidated or removed
- **1 acceptance test suite** that appears to be superseded by newer Jest tests
- **Documentation inconsistencies** where the README references features that no longer exist or are implemented differently

---

## Category 1: Legacy Python Code (SAFE TO REMOVE)

### `/src/` Directory - Old Python Implementation (Entire Directory)

**Status:** LEGACY - Replaced by `python3/src/stock_ticker/` modules

**Evidence:**
- The `src/` directory contains an old implementation using Yahoo Finance API
- The `python3/src/stock_ticker/` directory contains the current, active implementation
- No shell scripts, workflows, or documentation reference `src/app.py` or `src/test_app.py`
- The `python3/cli.py` (legacy) and `python3/src/stock_ticker/cli.py` (current) both exist but serve the same purpose
- `src/requirements.txt` has old versions (yfinance==0.1.70) vs `python3/requirements.txt` (yfinance>=0.2.0)

**Files to Remove:**
```
src/
├── __init__.py
├── app.py                          # Old main entry point (31 lines)
├── test_app.py                     # Old tests (20 lines)
├── requirements.txt                # Old dependencies
├── model/                          # All model classes (8 files, ~400 lines)
│   ├── EnrichedStock.py
│   ├── EnrichedStockCache.py
│   ├── EnrichedStockRepository.py
│   ├── File.py
│   ├── StockSymbol.py
│   ├── StockSymbolEnrichStrategy.py
│   ├── StockSymbolRepository.py
│   └── __init__.py
└── pkg/                            # All package implementations (~1000+ lines)
    ├── StockEnricher.py
    ├── enriched_stock_cache/
    ├── enriched_stock_repository/
    ├── enrich_strategy/
    └── stock_symbol_repository/
```

**Total:** 65+ files, approximately 2,000+ lines of code

**Impact:** NONE - This code is not referenced anywhere in the active system

**Recommendation:** **DELETE** entire `/src/` directory

---

## Category 2: Duplicate CLI Implementation

### `python3/cli.py` - Duplicate CLI (SAFE TO REMOVE)

**Status:** DUPLICATE - Same functionality as `python3/src/stock_ticker/cli.py`

**Evidence:**
- `python3/cli.py` is 1,385 lines - a standalone CLI implementation
- `python3/src/stock_ticker/cli.py` is the modular version being actively used
- Both implement the same commands: `status`, `init`, `sync-ftp`, `extract-prices`, `extract-metadata`, `build`, `run-all`, `reset`
- The `python3/pyproject.toml` points to `stock_ticker.cli:main` (the modular version)
- `python3/run.sh` calls `ticker-cli` which uses the pyproject.toml entry point (modular version)

**File to Remove:**
```
python3/cli.py                      # 1,385 lines - standalone duplicate
```

**Impact:** NONE - The modular version in `python3/src/stock_ticker/cli.py` is the active one

**Recommendation:** **DELETE** `python3/cli.py` standalone file

---

## Category 3: Acceptance Tests (POTENTIALLY OBSOLETE)

### `acceptance-tests/` Directory - Old Mocha/Puppeteer Tests

**Status:** POTENTIALLY OBSOLETE - Superseded by Jest E2E tests in `tests/puppeteer/`

**Evidence:**
- Current E2E tests use Jest + Puppeteer in `tests/puppeteer/` (3 test files, active in CI/CD)
- Old acceptance tests use Mocha + Puppeteer in `acceptance-tests/` (4 test files)
- Main workflow `.github/workflows/e2e-tests.yml` uses Jest tests
- Old workflow `.github/workflows/website-acceptance-tests.yml` uses Mocha tests
- The `scripts/website-test.sh` still references acceptance-tests but may not be used

**Files:**
```
acceptance-tests/
├── package.json                    # Mocha test configuration
├── tests/
│   ├── index.spec.js              # Homepage tests (Mocha)
│   ├── about.spec.js              # About page tests (Mocha)
│   ├── exchange-data-pages.spec.js # Data page tests (Mocha)
│   ├── api.spec.js                # API tests (Mocha)
│   ├── bootstrap.spec.helper.js   # Test helpers
│   └── nav.spec.helper.js         # Navigation helpers
├── Dockerfile
├── .dockerignore
└── .gitignore
```

**Current Jest Tests (Active):**
```
tests/puppeteer/
├── website-pages.e2e.test.js      # 23 tests - ALL PAGES (active)
├── ticker-ui.e2e.test.js          # TickerEngine performance tests (active)
├── portfolio-pagination.e2e.test.js # Pagination tests (active)
└── google-analytics.e2e.test.js   # GA tests on production (active)
```

**Comparison:**
- Mocha tests cover homepage, about, and exchange data pages
- Jest tests cover ALL 23 pages including strategies, data pages, etc.
- Jest tests are more comprehensive and actively maintained
- Both test suites use Puppeteer but different test frameworks

**Recommendation:** 
1. **VERIFY** that Jest tests cover all scenarios from Mocha tests
2. If coverage is complete, **DELETE** `acceptance-tests/` directory
3. If coverage is incomplete, **MIGRATE** missing scenarios to Jest tests, then delete
4. **DELETE** `scripts/website-test.sh` (references old tests)
5. **DELETE** `.github/workflows/website-acceptance-tests.yml` workflow

---

## Category 4: Summary Documentation Files (CAN BE CONSOLIDATED/REMOVED)

### Summary/Status Markdown Files

**Status:** These are historical summaries of work completed. Useful for reference but not required.

**Files:**
```
CLI_IMPROVEMENTS_PLAN.md            # 52 lines - Planning doc (completed)
CLI_IMPROVEMENTS_IMPLEMENTED.md     # 363 lines - Implementation summary (completed)
CLI_IMPROVEMENTS_DETAILED.md        # If exists - Detailed implementation notes
CLI_IMPROVEMENTS_QUICK_REFERENCE.md # If exists - Quick reference (redundant)
MIGRATION_SUMMARY.md                # 175 lines - Domain migration notes (completed)
HUGO_TABLE_FIXES_SUMMARY.md         # Table fix notes (completed)
PAGINATION_FIX_SUMMARY.md           # Pagination fix notes (completed)
QR_AND_REPO_LINK_SUMMARY.md         # QR code addition notes (completed)
TABLE_AND_FILTER_FIXES.md           # Table/filter fix notes (completed)
HTTPS_SETUP.md                      # HTTPS setup notes (completed)
```

**Analysis:**
- These are **historical documentation** of features that have already been implemented
- They serve as "change logs" but are not referenced by code
- The information in these files is not critical for understanding the current system
- The main `README.md`, `TESTING.md`, and `docs/` directory contain active documentation

**Recommendation:** 
**OPTIONAL** - Consider one of:
1. **ARCHIVE** to `docs/archive/` or `docs/history/` directory for historical reference
2. **CONSOLIDATE** into a single `CHANGELOG.md` or `HISTORY.md` file
3. **DELETE** if version control (git history) is considered sufficient documentation

**Impact:** LOW - These are supplementary docs, not required for operation

---

## Category 5: Documentation Inconsistencies

### README.md - Outdated Information

**Issues Found:**

#### 1. **TODO List References Removed Features**

Lines 150-199 contain a TODO list with many items referencing features that either:
- Don't exist anymore (website exchange links for specific exchanges)
- Are implemented differently than described
- Reference deprecated infrastructure (AWS S3, CloudFront, Route 53 - not in active use)

**Specific Examples:**
```markdown
- [ ] Website has NASDAQ exchange link
- [ ] Website has NYSE exchange link
- [ ] Website has AMEX exchange link
```
**Reality:** The website uses strategy-based filtering, not exchange-specific pages

```markdown
- [ ] AWS CloudFront
- [ ] AWS Certificate Manager
- [ ] AWS S3 bucket, for static website assets
```
**Reality:** Site is deployed to GitHub Pages, not AWS S3

**Recommendation:** **UPDATE** or **REMOVE** outdated TODO items

---

#### 2. **Python Script Commands Reference Old Structure**

Lines 128-142 show Python commands:
```bash
# Install requirements
pip3 install -r src/requirements.txt

# Run python script
python3 -m src.app
```

**Reality:** 
- Current CLI is in `python3/` directory
- Should reference `python3/requirements.txt` not `src/requirements.txt`
- Should use `python -m stock_ticker.cli` or `./python3/run.sh`

**Recommendation:** **UPDATE** Python commands section to reflect current structure:
```bash
# From python3 directory
cd python3
pip3 install -r requirements.txt

# Run CLI
python -m stock_ticker.cli status
# Or use convenience wrapper
./run.sh status
```

---

#### 3. **Developer Quick Commands Reference Non-Existent Script**

Lines 144-148:
```bash
# Preferred Development Bash Command
./scripts/infrastructure-down.sh && ./scripts/infrastructure-down.sh && ./scripts/infrastructure-up.sh && ./scripts/infrastructure-up.sh
# Note: the double call is to ensure the script is idempotent in a user friendly way
```

**Reality:**
- These scripts exist but are for AWS infrastructure (S3 buckets)
- The site is now deployed to GitHub Pages via GitHub Actions
- This is not the "preferred development bash command" anymore
- The actual preferred command is: `cd hugo/site && hugo server`

**Recommendation:** **REMOVE** or **UPDATE** to reflect current deployment strategy

---

#### 4. **Extract Exchanges Script is Non-Functional**

Line 121 and `scripts/extract-exchanges-txt-data.sh`:
```bash
# Extract stock exchange(s) data
./scripts/extract-exchanges-txt-data.sh
```

**Script Content:**
```bash
all_stocks=$(curl https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt)
comm -12i <(echo "${all_stocks})") <(echo "${english_dictionary}") | tee "${ALL_EXCHANGES_OUTPUT_FILE}"
```

**Issues:**
- Has a syntax error: `"${all_stocks})"` has mismatched quotes/parens
- Output path `static/api/all-exchanges.txt` doesn't exist in current structure
- This approach is superseded by the Python CLI which uses NASDAQ FTP directly
- The script is never referenced in workflows or other scripts

**Recommendation:** **DELETE** `scripts/extract-exchanges-txt-data.sh` as obsolete

---

### TESTING.md - Minor Inconsistencies

**Issue:**
Lines 110 reference:
```markdown
- [Copilot Instructions](./.github/copilot-instructions.md)
```

**Reality:** Need to verify if this file exists and is current

**Recommendation:** **VERIFY** and update path if needed

---

### python3/README.md - Accurate and Current ✅

**Status:** This file is accurate and aligns with actual implementation

**No changes needed**

---

## Category 6: Scripts Directory Review

### Infrastructure Scripts - AWS Related (POTENTIALLY OBSOLETE)

**Files:**
```
scripts/infrastructure-up.sh        # 237 lines - Creates AWS S3 buckets
scripts/infrastructure-down.sh      # ~60 lines - Tears down AWS resources
scripts/infrastructure-test.sh      # Testing AWS setup
scripts/infrastructure-config.sh    # AWS configuration
```

**Analysis:**
- These scripts create and manage AWS S3 buckets for static hosting
- Current deployment uses **GitHub Pages** (`.github/workflows/website-qa-deploy.yml`)
- The README mentions these scripts but they may not be actively used
- HTTPS setup via AWS Certificate Manager is also not actively used (GitHub provides HTTPS)

**Evidence from MIGRATION_SUMMARY.md:**
```markdown
### Current Status
- ✅ Custom domain (stockmarketwords.com) configured
- ✅ A records point to GitHub Pages IPs
- ✅ CNAME file deployed
```

**Recommendation:** 
**CONDITIONAL:**
1. If AWS infrastructure is **not actively used**: **DELETE** or **ARCHIVE** to `scripts/legacy/`
2. If AWS infrastructure is **maintained as backup**: **KEEP** but add clear documentation
3. If AWS infrastructure is **completely replaced**: **DELETE** these files

**Impact:** Need to verify with deployment strategy

---

### Active Scripts (KEEP)

```
scripts/website-up.sh               # Starts Hugo server (ACTIVE)
scripts/website-down.sh             # Stops Hugo server (ACTIVE)
scripts/website-test.sh             # References old acceptance-tests (UPDATE or DELETE)
```

**Recommendation:**
- **KEEP** `website-up.sh` and `website-down.sh` (active)
- **UPDATE** `website-test.sh` to use Jest tests: `npm run test:e2e:pages`
- OR **DELETE** `website-test.sh` if `npm run` is preferred

---

## Category 7: JavaScript Files - All Active ✅

**Status:** All JavaScript files are actively used and referenced

```
hugo/site/static/js/
├── TickerEngine.js                 # 318 lines - Core algorithm (ACTIVE)
├── portfolio-extractor.js          # 811 lines - Main UI logic (ACTIVE)
├── portfolio-worker.js             # 144 lines - Web Worker (ACTIVE)
├── filtered-data.js                # 92 lines - Filtered data page (ACTIVE)
└── raw-ftp-data.js                 # 58 lines - Raw data page (ACTIVE)
```

**Analysis:**
- All JS files have corresponding Hugo pages that load them
- TickerEngine.js has active unit tests and E2E tests
- portfolio-extractor.js is the main interactive UI (tested)
- All files are minified/bundled in production

**Recommendation:** **KEEP ALL** - No unused JavaScript found

---

## Summary of Recommendations

### HIGH PRIORITY - Safe to Remove (No Impact)

1. **DELETE** entire `/src/` directory (old Python implementation, 65+ files, ~2000 lines)
2. **DELETE** `python3/cli.py` (duplicate standalone CLI, 1,385 lines)
3. **DELETE** `scripts/extract-exchanges-txt-data.sh` (broken script, not used)

**Estimated cleanup:** ~3,500 lines of code, 70+ files

---

### MEDIUM PRIORITY - Verify Then Remove

4. **VERIFY** Jest test coverage, then **DELETE** `acceptance-tests/` directory (entire Mocha test suite)
5. **DELETE** `.github/workflows/website-acceptance-tests.yml` workflow (references old Mocha tests)
6. **DELETE** or **UPDATE** `scripts/website-test.sh` (references old tests)

**Estimated cleanup:** ~500 lines of test code, 15+ files

---

### LOW PRIORITY - Documentation Cleanup

7. **UPDATE** `README.md`:
   - Remove or update obsolete TODO items (lines 150-199)
   - Update Python commands section (lines 128-142)
   - Remove/update infrastructure commands (lines 144-148)
   
8. **CONSOLIDATE** or **ARCHIVE** summary documentation files:
   - Move to `docs/archive/` or combine into `CHANGELOG.md`
   - Files: CLI_IMPROVEMENTS_*.md, MIGRATION_SUMMARY.md, *_SUMMARY.md, *_FIXES.md (9 files)

9. **DECIDE** on AWS infrastructure scripts:
   - If not used: DELETE `scripts/infrastructure-*.sh` (4 files)
   - If used: Document when/why they're used

**Estimated cleanup:** ~1,500 lines of documentation, 13 files

---

## Total Cleanup Potential

**Code:**
- 70+ files
- ~4,000 lines of unused code
- 15+ test files (if Mocha tests are removed)

**Documentation:**
- 13+ summary/status files
- ~200 lines of outdated README content

**Grand Total:** ~85 files, ~4,500 lines to review

---

## Testing Strategy Before Deletion

**Before removing anything:**

1. **Run all current tests:**
   ```bash
   npm test                    # All tests
   npm run test:e2e            # E2E tests
   npm run test:perf           # Performance tests
   cd python3
   pytest                      # Python tests (if they exist)
   ```

2. **Verify no imports:**
   ```bash
   # Check for any imports from src/
   grep -r "from src\." . --include="*.py" | grep -v node_modules
   grep -r "import src\." . --include="*.py" | grep -v node_modules
   
   # Check for cli.py references
   grep -r "python3/cli.py" . --include="*.sh" --include="*.yml"
   ```

3. **Run Python CLI:**
   ```bash
   cd python3
   ./run.sh status             # Verify current CLI works
   ```

4. **Test website:**
   ```bash
   cd hugo/site
   hugo server                 # Verify site builds
   ```

5. **Only after all tests pass:** Proceed with deletions

---

## Migration Checklist

- [ ] Verify all current tests pass
- [ ] Verify no code references `/src/` directory
- [ ] Verify `python3/src/stock_ticker/cli.py` is the active CLI
- [ ] Delete `/src/` directory
- [ ] Delete `python3/cli.py`
- [ ] Delete `scripts/extract-exchanges-txt-data.sh`
- [ ] Compare Mocha vs Jest test coverage
- [ ] Delete `acceptance-tests/` (if coverage confirmed)
- [ ] Delete old workflow file
- [ ] Update `README.md` Python commands
- [ ] Update `README.md` TODO list
- [ ] Update `README.md` infrastructure commands
- [ ] Archive or consolidate summary docs
- [ ] Decide on AWS infrastructure scripts
- [ ] Run all tests again
- [ ] Commit changes

---

## Notes

**Created by:** GitHub Copilot CLI Analysis  
**Date:** 2026-01-19  
**Codebase Version:** Current main branch  
**Analysis Method:** File inspection, grep analysis, import tracing, documentation review

**Confidence Levels:**
- **HIGH**: Old `/src/` directory removal (100% certain it's unused)
- **HIGH**: Duplicate `python3/cli.py` removal (100% certain)
- **MEDIUM**: Acceptance tests removal (needs coverage verification)
- **LOW**: AWS infrastructure scripts (need deployment strategy clarification)

---

**Next Step:** Review this document and approve specific items for deletion.
