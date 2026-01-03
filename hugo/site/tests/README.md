# TickerEngine - Stock Ticker Extraction Algorithm

## Overview

TickerEngine is a JavaScript class that performs non-greedy backtracking search on text to find stock tickers. It implements a state machine that tags every character and supports multiple scoring strategies.

## Features

### 1. State Machine Character Tagging

Every character in the output is tagged as one of four types:

- **Ticker**: Characters that form the ticker symbol
- **In-Between**: Characters between the first and last character of a discovered ticker
- **Outside-Ticker**: Characters in a consumed word that fall outside the ticker boundaries  
- **Normal**: All other characters

### 2. Word Consumption Rule

If any character in a word is used for a ticker, the entire word is "consumed" and cannot be used for another ticker in the same portfolio.

### 3. Five Scoring Strategies

1. **Dividend Daddy** - Prioritizes stocks with high dividend yield
2. **The Moon Shot** - Prioritizes high beta (volatile) stocks
3. **Falling Knife** - Prioritizes stocks with negative momentum
4. **Over-Hyped** - Prioritizes stocks with high RSI (overbought)
5. **Institutional Whale** - Prioritizes stocks with high market cap

### 4. Performance Optimizations

- **3,000 character input limit** - Automatically truncates longer text
- **Memoization** - Caches sub-path results to avoid redundant calculations
- **Top 5 results** - Returns exactly the top 5 distinct portfolio options
- **Greedy ticker matching** - Finds longest matching tickers efficiently

## Installation

```bash
npm install --save-dev jest @types/jest
```

## Usage

### Basic Example

```javascript
// Build a trie from ticker symbols
const trie = buildTrie(['AAPL', 'TSLA', 'MSFT']);

// Create metadata for tickers
const metadata = {
  AAPL: { yield: 0.05, beta: 1.2, rsi: 30, momentum: 15, marketCap: 3000000000000 },
  TSLA: { yield: 0, beta: 2.5, rsi: 75, momentum: -5, marketCap: 800000000000 },
  MSFT: { yield: 0.08, beta: 0.9, rsi: 45, momentum: 10, marketCap: 2800000000000 }
};

// Create engine
const engine = new TickerEngine(trie, metadata);

// Extract portfolios
const portfolios = engine.extractPortfolios(
  'The Great Apple and Tesla',
  'DIVIDEND_DADDY'
);

// Access results
portfolios.forEach(portfolio => {
  console.log('Tickers:', portfolio.tickers);
  console.log('Score:', portfolio.score);
  console.log('Tokens:', portfolio.tokens);
});
```

### Building a Trie

```javascript
function buildTrie(symbols) {
  const trie = {};
  
  for (const symbol of symbols) {
    let node = trie;
    for (const char of symbol.toUpperCase()) {
      if (!node[char]) {
        node[char] = {};
      }
      node = node[char];
    }
    node._isEnd = true;
    node._sym = symbol;
  }
  
  return trie;
}
```

## API Reference

### Constructor

```javascript
new TickerEngine(trie, metadata)
```

- `trie`: Prefix tree of ticker symbols
- `metadata`: Object keyed by symbol containing financial metrics

### Methods

#### extractPortfolios(text, strategy)

Extracts top 5 portfolio options from text.

**Parameters:**
- `text` (string): Input text (max 3000 chars)
- `strategy` (string): One of the scoring strategy keys
  - `'DIVIDEND_DADDY'`
  - `'THE_MOON_SHOT'`
  - `'FALLING_KNIFE'`
  - `'OVER_HYPED'`
  - `'INSTITUTIONAL_WHALE'`

**Returns:** Array of portfolio objects, each containing:
- `tickers`: Array of ticker symbols
- `tokens`: Array of `{char, type}` objects
- `score`: Numerical score based on strategy
- `metadata`: Financial metrics for each ticker

## Testing

Run the comprehensive test suite:

```bash
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

Generate coverage report:

```bash
npm run test:coverage
```

### Test Results

✅ 20 out of 22 tests passing

**Passing Tests:**
- State machine token tagging (Ticker, In-Between, Outside-Ticker, Normal)
- All 5 scoring strategies
- Portfolio extraction with 3000 char limit
- Ticker spanning multiple words
- Word consumption rules
- Empty input handling
- Special characters
- Mixed case
- Metadata integration

## Integration with Hugo

The TickerEngine is integrated into a Hugo shortcode for use in static sites:

### Shortcode Usage

```markdown
{{< ticker-portfolio-extraction-tool >}}
```

### Files

- `hugo/site/static/js/TickerEngine.js` - Core algorithm
- `hugo/site/static/js/ticker-portfolio-extraction-tool.js` - UI integration
- `hugo/site/layouts/shortcodes/ticker-portfolio-extraction-tool.html` - HTML template
- `hugo/site/static/css/ticker-highlight.css` - Styling for token highlighting
- `hugo/site/tests/TickerEngine.test.js` - Comprehensive test suite

## Example Output

### Input
```
"The Great Apple"
```

### Strategy: DIVIDEND_DADDY

### Result
```javascript
{
  tickers: ['AAPL'],
  score: 0.05,
  tokens: [
    { char: 'T', type: 'Normal' },
    { char: 'h', type: 'Normal' },
    { char: 'e', type: 'Normal' },
    { char: ' ', type: 'Normal' },
    { char: 'G', type: 'Outside-Ticker' },
    { char: 'r', type: 'Outside-Ticker' },
    { char: 'e', type: 'Outside-Ticker' },
    { char: 'a', type: 'Ticker' },      // 'A' from "Great"
    { char: 't', type: 'In-Between' },
    { char: ' ', type: 'In-Between' },
    { char: 'A', type: 'Ticker' },      // 'A' from "Apple"
    { char: 'p', type: 'In-Between' },
    { char: 'p', type: 'Ticker' },      // 'P' from "Apple"
    { char: 'l', type: 'Ticker' },      // 'L' from "Apple"
    { char: 'e', type: 'Outside-Ticker' }
  ]
}
```

## Performance Considerations

- Maximum input length: 3,000 characters
- Maximum words scanned per ticker: 3 consecutive words
- Maximum portfolio combinations generated: 100
- Optimized for real-time user interaction

## License

ISC
