# GitHub Copilot Instructions for Stock Market Words Project

## Testing Guidelines

### When to Update Tests

When making changes to the codebase, **always consider** if tests need to be updated:

1. **Page Content Changes**: If modifying content or layout of a specific page, check `tests/puppeteer/website-pages.e2e.test.js` to see if:
   - The test expectations are still valid
   - New assertions should be added
   - Selectors need updating

2. **New Page Creation**: When adding a new page to the Hugo site, add it to the `PAGES` array in `tests/puppeteer/website-pages.e2e.test.js`:
   ```javascript
   const PAGES = [
     { path: '/', name: 'Home' },
     { path: '/about/', name: 'About' },
     // Add new pages here
     { path: '/new-page/', name: 'New Page Name' }
   ];
   ```

3. **TickerEngine Changes**: If modifying `hugo/site/static/js/TickerEngine.js`:
   - Check `tests/perf/TickerEngine.perf.test.js` for unit test updates
   - Check `tests/puppeteer/ticker-ui.e2e.test.js` for E2E test updates
   - Consider if new test cases are needed

4. **UI Component Changes**: When modifying forms, buttons, or interactive elements:
   - Update selectors in tests if HTML IDs or classes change
   - Add new test cases for new functionality
   - Verify existing tests still pass

### Test-Driven Development Process

Before implementing a feature:

1. **Read existing tests** in `tests/puppeteer/` to understand current behavior
2. **Consider new test cases** that should be added
3. **Implement the feature**
4. **Update tests** to match new behavior
5. **Run tests** to verify: `npm run test:e2e:pages`

### Running Tests Before Changes

Always run relevant tests before making changes to establish a baseline:

```bash
# For page content changes
npm run test:e2e:pages

# For TickerEngine algorithm changes
npm run test:perf
npm run test:e2e:ticker

# For any JavaScript changes
npm run test:e2e
```

## Code Quality Standards

### JavaScript

- Use strict equality (`===`) over loose equality (`==`)
- Avoid global variables
- Use `const` for immutable values, `let` for mutable
- Add JSDoc comments for complex functions
- Keep functions small and focused

### HTML/Hugo Templates

- Use semantic HTML elements
- Ensure all interactive elements are keyboard accessible
- Load jQuery before jQuery-dependent libraries (DataTables, etc.)
- Use proper ARIA labels where appropriate

### Performance Considerations

- TickerEngine.js is performance-critical - always profile changes
- Avoid blocking the main thread with long-running operations
- Use Web Workers for expensive computations (see portfolio-worker.js)
- Cache expensive calculations when possible

## Documentation

When making significant changes:

1. Update relevant README files
2. Add code comments for complex logic
3. Update test documentation if test behavior changes
4. Document breaking changes clearly

## Debugging Tips

- Use browser DevTools to inspect E2E test failures
- Check console for JavaScript errors during tests
- Run tests with `--verbose` flag for detailed output
- Use `headless: false` in Puppeteer tests for visual debugging

## File Structure Awareness

Key locations:
- Tests: `tests/perf/` and `tests/puppeteer/`
- Hugo layouts: `hugo/site/layouts/`
- JavaScript: `hugo/site/static/js/`
- Documentation: `docs/` and `tests/README.md`
- Database: `data/market_data.db` (SQLite database with tickers, daily_metrics, strategy_scores tables)
- Hugo data files: `hugo/site/static/data/` (JSON files for website consumption)

## Testing Philosophy

This project uses a **test-driven quality approach**:

- Tests are not optional - they catch real bugs
- Failing tests indicate real problems to fix
- Green tests mean the feature works as expected
- Tests serve as living documentation

**Always ask**: "Should this change have a test?" before committing code.

## Hugo Development Guidelines

### Local Development MUST Always Work

When making changes to Hugo configuration or deployment settings:

1. **Always preserve local development workflow**
   - Local development uses: `hugo server` (no flags required)
   - Hugo's `--baseURL` flag automatically overrides config for local server
   - Never require environment variables for local development to work

2. **BaseURL Configuration Strategy**
   - `hugo.toml`: Set production `baseURL = 'https://stockmarketwords.com/'`
   - Local dev: Hugo server automatically overrides to `http://localhost:1313/`
   - This is Hugo's expected behavior - no special handling needed

3. **Environment-Specific Features**
   - Features like Google Analytics should be **optional** via parameters
   - Default parameter values must allow local dev without configuration
   - Use Hugo params with empty defaults: `googleAnalyticsId = ""`
   - Production sets params via environment: `HUGO_PARAMS_GOOGLEANALYTICSID`

4. **Testing Configuration Changes**
   Before committing changes to `hugo.toml` or deployment workflows:
   ```bash
   # Test local development still works
   cd hugo/site
   hugo server
   # Visit http://localhost:1313/ - should work without errors
   
   # Test production build still works
   hugo --minify
   # Check public/ folder for correct URLs
   ```

5. **Configuration Change Checklist**
   - [ ] Local `hugo server` starts without errors
   - [ ] No environment variables required for local dev
   - [ ] Assets load correctly on localhost
   - [ ] Production build generates correct absolute URLs
   - [ ] Optional features (GA, etc.) don't break local dev

### Common Pitfalls to Avoid

❌ **Don't**: Require environment variables for basic local development
❌ **Don't**: Break `hugo server` with production-only settings
❌ **Don't**: Hardcode production URLs in templates (use `.Site.BaseURL`)

✅ **Do**: Use Hugo's built-in baseURL override in dev mode
✅ **Do**: Make tracking/analytics optional via parameters
✅ **Do**: Test both local and production builds before committing

### Why This Matters

Local development is the primary workflow for:
- Content creation
- Layout changes
- JavaScript development
- Quick iteration and testing

Breaking local development slows down all contributors and makes the project harder to work with.

### Other Instructions
If you feel compelled to create a doc about the code changes you're making, please channel your energy into creating a doc in the temp/ directory (create one if it does not exist)
