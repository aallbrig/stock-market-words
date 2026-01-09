# TickerEngine Performance Profiling Guide

This guide explains how to profile and optimize the `TickerEngine.js` algorithm performance using JavaScript profiling tools.

## Quick Start

Run the performance test suite to measure baseline performance:

```bash
npm test -- TickerEngine.perf.test.js
```

This will run tests against the three sample texts with a 60-second timeout limit.

## Performance Testing

### Running Performance Tests

The test suite includes:
- **Sample text tests**: Tests each of the three UI sample texts (short, medium, long)
- **Strategy tests**: Tests all five investment strategies
- **Benchmark tests**: Measures average, min, and max execution times
- **Memory tests**: Validates cache clearing and sequential runs

```bash
# Run all performance tests
npm test -- TickerEngine.perf.test.js

# Run with verbose output
npm test -- TickerEngine.perf.test.js --verbose

# Run a specific test
npm test -- TickerEngine.perf.test.js -t "SHORT sample text"
```

### Understanding Test Output

Each test reports execution time:
```
SHORT text completed in 125ms
MEDIUM text completed in 450ms
LONG text completed in 1250ms
```

Benchmark tests provide statistics:
```
MEDIUM text stats over 10 runs:
  Average: 445.20ms
  Min: 420ms
  Max: 485ms
```

## Node.js Profiling

### Built-in Profiler

Node.js has a built-in CPU profiler using V8's inspector:

```bash
# Profile the performance tests
node --prof node_modules/.bin/jest TickerEngine.perf.test.js

# Process the log file (creates a readable text file)
node --prof-process isolate-*.log > profile.txt

# View the profile
less profile.txt
```

The profile shows:
- Function call statistics (time spent in each function)
- Hot paths (most expensive code paths)
- Call tree (function call hierarchy)

### Chrome DevTools Profiler

For a visual profiling experience:

```bash
# Run with inspector enabled
node --inspect-brk node_modules/.bin/jest TickerEngine.perf.test.js
```

Then:
1. Open Chrome and navigate to `chrome://inspect`
2. Click "Open dedicated DevTools for Node"
3. Go to the "Profiler" tab
4. Click "Start" to begin profiling
5. Let the tests run
6. Click "Stop" and analyze the flame graph

### Memory Profiling

To detect memory leaks or excessive allocations:

```bash
# Run with heap profiling
node --inspect node_modules/.bin/jest TickerEngine.perf.test.js --runInBand
```

In Chrome DevTools:
1. Navigate to `chrome://inspect`
2. Open dedicated DevTools
3. Go to "Memory" tab
4. Take heap snapshots before and after test runs
5. Compare snapshots to find memory leaks

## WebStorm Profiling (Recommended for WebStorm Users)

### Setup

1. Open your project in WebStorm
2. Navigate to `hugo/site/static/js/TickerEngine.perf.test.js`
3. Right-click the file in the editor or project tree

### Running Performance Tests in WebStorm

**Method 1: Run with Coverage**
1. Right-click `TickerEngine.perf.test.js` → "Run with Coverage"
2. View execution times in the test runner panel
3. See code coverage to identify untested code paths

**Method 2: Debug Configuration**
1. Click "Edit Configurations" in the top toolbar
2. Click "+" → "Jest"
3. Configure:
   - Name: `TickerEngine Performance Tests`
   - Jest options: `--testPathPattern=TickerEngine.perf.test.js`
   - Working directory: Your project root
4. Run or Debug this configuration

### Profiling in WebStorm

WebStorm provides excellent CPU and memory profiling:

**CPU Profiling:**
1. Right-click `TickerEngine.perf.test.js`
2. Select "Run 'TickerEngine.perf.test.js' with Coverage"
3. Or use: Run → Profile 'TickerEngine.perf.test.js'
4. View results in the Profiler tool window
   - Flame graph shows function call hierarchy
   - Call tree shows time spent per function
   - Hot spots highlighted automatically

**Analyzing Results:**
- **Flame Graph**: Wider bars = more time spent. Look for unexpectedly wide bars
- **Call Tree**: Sort by "Total Time" to find bottlenecks
- **Methods List**: Find expensive individual function calls

**Finding Bottlenecks:**
1. Look for functions taking >10% of total time
2. Check for deep recursion (tall flame graph sections)
3. Identify frequent function calls (high "count" numbers)
4. Find allocation-heavy code in the memory profiler

### WebStorm Debugging for Performance

To step through slow code:

1. Set breakpoints in `TickerEngine.js`:
   - `extractPortfolios()` - Entry point
   - `findAllTickers()` - Ticker search loop
   - `generatePortfolios()` - Portfolio generation
   - `matchTickersInChars()` - Trie matching logic

2. Right-click test file → "Debug 'TickerEngine.perf.test.js'"

3. Use debugger features:
   - **Evaluate Expression** (Alt+F8): Test variables or expressions
   - **Watches**: Monitor variable values continuously
   - **Step Into** (F7): Dive into function calls
   - **Step Over** (F8): Execute current line
   - **Resume** (F9): Continue to next breakpoint

4. Performance debugging tips:
   - Add conditional breakpoints: Right-click breakpoint → "Condition"
   - Use "Mute Breakpoints" to skip breakpoints temporarily
   - Check "Variables" panel for object sizes and types

### WebStorm Performance Tips

**Live Templates for Profiling:**
Create custom live templates for quick performance logging:

1. Settings → Editor → Live Templates
2. Create new template: `perf`
3. Template text:
```javascript
const start$VAR$ = Date.now();
$SELECTION$
console.log('$DESC$ took', Date.now() - start$VAR$, 'ms');
```

4. Use: Select code, type `perf`, press Tab

**Benchmarking in WebStorm:**
1. Use "Run → Run..." → Edit Configurations
2. Add "Before launch" task: "Run npm script"
3. Set npm script to `test:perf` (add to package.json)
4. Run multiple times and compare console output

## Optimization Strategies

### Common Bottlenecks

Based on the algorithm structure, check these areas:

1. **Trie Traversal** (`matchTickersInChars`)
   - Deep recursion with backtracking
   - Multiple character combinations tested
   - **Optimization**: Prune paths early, limit recursion depth

2. **Word Combinations** (`findAllTickers`)
   - Nested loops testing up to 3-word combinations
   - Grows exponentially with word count
   - **Optimization**: Skip unlikely word spans, cache results

3. **Portfolio Generation** (`generatePortfolios`)
   - Combines tickers in multiple ways
   - Limited to 100 portfolios but still expensive
   - **Optimization**: Use better heuristics for combinations

4. **Token Tagging** (`createPortfolio`)
   - Character-by-character iteration
   - Multiple map lookups per character
   - **Optimization**: Batch operations, reduce map lookups

### Profiling Workflow

1. **Measure baseline**: Run performance tests, note times
2. **Profile**: Use Node profiler or WebStorm to find hot spots
3. **Optimize**: Make targeted changes to expensive functions
4. **Test**: Re-run tests to verify improvements
5. **Repeat**: Continue until performance goals met

### Performance Goals

Current timeout: 60 seconds
Target goals:
- SHORT text: < 100ms
- MEDIUM text: < 500ms
- LONG text: < 2000ms (2 seconds)

## Advanced Profiling

### Comparing Optimizations

```bash
# Before optimization
npm test -- TickerEngine.perf.test.js > before.log

# Make changes to TickerEngine.js

# After optimization
npm test -- TickerEngine.perf.test.js > after.log

# Compare
diff before.log after.log
```

### Continuous Performance Testing

Add to your development workflow:

```bash
# Run performance tests before committing
git add .
npm test -- TickerEngine.perf.test.js && git commit -m "Performance improvements"
```

Or add to `package.json`:
```json
{
  "scripts": {
    "test:perf": "jest TickerEngine.perf.test.js",
    "test:perf:watch": "jest TickerEngine.perf.test.js --watch",
    "precommit": "npm run test:perf"
  }
}
```

## Resources

- [Node.js Profiling Guide](https://nodejs.org/en/docs/guides/simple-profiling/)
- [Chrome DevTools CPU Profiler](https://developer.chrome.com/docs/devtools/performance/)
- [WebStorm Profiler Documentation](https://www.jetbrains.com/help/webstorm/cpu-profiler.html)
- [Jest Performance Testing](https://jestjs.io/docs/timer-mocks)
- [V8 Optimization Tips](https://v8.dev/blog/elements-kinds)

## Troubleshooting

**Tests timeout before 60 seconds:**
- Increase Jest timeout: Add `jest.setTimeout(120000)` in test file
- Or set globally in `package.json`: `"jest": { "testTimeout": 120000 }`

**Profiler output is confusing:**
- Start with flame graph view (most intuitive)
- Focus on widest bars first (biggest time consumers)
- Use "filter" to search for specific functions

**WebStorm profiler won't start:**
- Check Node.js version: `node --version` (requires Node 12+)
- Update WebStorm to latest version
- Try "Invalidate Caches / Restart" in WebStorm

**Memory usage keeps growing:**
- Check for cache not being cleared (memoCache)
- Look for global variables accumulating data
- Use heap snapshots to find retention paths
