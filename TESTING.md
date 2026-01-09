# Testing Quick Reference

## Run Tests

```bash
# All tests
npm test

# Performance tests only
npm run test:perf

# All E2E tests
npm run test:e2e

# Page load tests only
npm run test:e2e:pages

# Ticker performance tests only
npm run test:e2e:ticker
```

## View Test Reports

```bash
# Run tests (auto-generates reports)
npm run test:e2e:pages

# Open HTML report
open test-reports/index.html        # macOS
xdg-open test-reports/index.html    # Linux
start test-reports/index.html       # Windows

# Or use HTTP server
npx http-server test-reports -o
```

## Before Committing

```bash
# Start Hugo
./scripts/website-up.sh

# Run all E2E tests (in another terminal)
npm run test:e2e

# Stop Hugo
pkill -f "hugo server"
```

## GitHub Actions

Push to trigger automatically:
```bash
git add .
git commit -m "Your changes"
git push
```

View results:
1. Go to GitHub → Actions tab
2. Click on latest workflow run
3. Download "test-reports" artifact
4. Extract and open index.html

## When Making Changes

### Changing Page Content
1. Check `tests/puppeteer/website-pages.e2e.test.js`
2. Update test if needed
3. Run: `npm run test:e2e:pages`

### Adding New Page
Add to `tests/puppeteer/website-pages.e2e.test.js`:
```javascript
const PAGES = [
  // ...existing pages
  { path: '/new-page/', name: 'New Page' }
];
```

### Modifying TickerEngine
1. Run: `npm run test:perf`
2. Run: `npm run test:e2e:ticker`
3. Check performance didn't degrade

## Troubleshooting

**Tests won't run:**
- Ensure Hugo server is running
- Check: `curl http://localhost:8668`

**Reports not generated:**
- Check test-reports/ directory exists
- Verify jest-html-reporter is installed

**GitHub Actions failing:**
- Check workflow logs in Actions tab
- Verify all dependencies in package.json

## Resources

- [Full Test Suite Docs](./tests/README.md)
- [Test Reports Guide](./docs/test-reports-guide.md)
- [Profiling Guide](./docs/profiling-guide.md)
- [Copilot Instructions](./.github/copilot-instructions.md)
