# TickerEngine Performance Testing - Quick Start

## Run Tests

```bash
# Run all performance tests
npm run test:perf

# Run with verbose output
npm run test:perf:verbose

# Run specific test
npm test -- TickerEngine.perf.test.js -t "SHORT sample"
```

## Profile with Node.js

```bash
# Generate profile
npm run profile

# Process profile (after tests complete)
node --prof-process isolate-*.log > profile.txt

# View profile
less profile.txt
```

## Profile in WebStorm

1. Open `tests/TickerEngine.perf.test.js`
2. Right-click → **Run with Coverage** or **Profile**
3. View flame graph in Profiler tool window
4. Look for wide bars = expensive functions

## Understanding Results

### Test Output
```
SHORT text completed in 4ms      ✅ Fast
MEDIUM text completed in 6ms     ✅ Fast
LONG text completed in 47ms      ✅ Fast
```

All times should be well under 60,000ms (60 seconds).

### Profile Output
Look for:
- Functions with high "Total Time %"
- Deep recursion (many stack frames)
- Frequent calls (high "Count")

## Optimization Workflow

1. **Baseline**: Run `npm run test:perf > baseline.txt`
2. **Profile**: Run `npm run profile` or use WebStorm profiler
3. **Identify**: Find functions taking >10% of total time
4. **Optimize**: Edit `hugo/site/static/js/TickerEngine.js`
5. **Test**: Re-run `npm run test:perf`
6. **Compare**: Check if times improved
7. **Repeat**: Continue until satisfied

## Common Bottlenecks

Based on algorithm analysis, likely slow areas:

| Function | Issue | Solution |
|----------|-------|----------|
| `findAllTickers()` | Nested loops over word combinations | Limit span size, skip unlikely combos |
| `matchTickersInChars()` | Recursive backtracking | Early pruning, depth limits |
| `generatePortfolios()` | Testing ticker combinations | Better heuristics, limit to top candidates |
| `createPortfolio()` | Character-by-character tagging | Batch operations, reduce lookups |

## Quick Commands

```bash
# Watch mode (re-run on file changes)
npm test -- TickerEngine.perf.test.js --watch

# Run with debugger
node --inspect-brk node_modules/.bin/jest TickerEngine.perf.test.js

# Compare performance
npm run test:perf | tee baseline.txt
# ... make changes ...
npm run test:perf | tee improved.txt
diff baseline.txt improved.txt
```

## WebStorm Tips

- **Breakpoint in slow function**: Set conditional breakpoint to pause only on large inputs
- **Evaluate Expression** (Alt+F8): Check variable sizes during debugging
- **Flame Graph**: Hover over bars to see function names and times
- **Call Tree**: Sort by "Total Time" to find bottlenecks

## Need More Help?

See [profiling-guide.md](./profiling-guide.md) for detailed instructions.
