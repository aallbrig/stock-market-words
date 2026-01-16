# Quick Reference: Running Tests

## Most Common Commands

```bash
# Run all E2E tests (auto-manages server)
npm run test:e2e

# Run just page tests
npm run test:e2e:pages

# Run ticker performance tests
npm run test:e2e:ticker

# Test against QA/production site
npm run test:e2e:qa
```

## Environment Variable Cheat Sheet

```bash
# Test against custom URL
TEST_URL=https://example.com START_SERVER=false npm run test:e2e

# Use custom port
SERVER_PORT=9000 npm run test:e2e

# Disable auto-server (run your own)
START_SERVER=false npm run test:e2e

# Custom timeout for ticker tests
TIMEOUT_SECONDS=120 npm run test:e2e:ticker
```

## Common Scenarios

### Scenario 1: Local Development
```bash
# Just run tests - server auto-managed
npm run test:e2e:pages
```

### Scenario 2: Test Live Site
```bash
# Test the deployed GitHub Pages site
npm run test:e2e:qa
```

### Scenario 3: Debug with Manual Server
```bash
# Terminal 1
cd hugo/site && hugo server -p 8668

# Terminal 2
START_SERVER=false npm run test:e2e:pages
```

### Scenario 4: CI/CD
Tests work automatically in GitHub Actions - no special configuration needed!

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Server failed to start" | Check if port 8668 is already in use |
| "Connection refused" | Verify Hugo is installed: `hugo version` |
| Tests timeout | Increase timeout: `TIMEOUT_SECONDS=120` |
| "External server not accessible" | Check URL and network connectivity |

## Quick Links

- Full documentation: [tests/README.md](../tests/README.md)
- Infrastructure update details: [test-infrastructure-update.md](./test-infrastructure-update.md)
- Server manager code: [tests/test-server.js](../tests/test-server.js)
