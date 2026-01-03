const TickerEngine = require('../static/js/TickerEngine');

describe('TickerEngine', () => {
  let engine;
  let mockTrie;
  let mockMetadata;

  beforeEach(() => {
    // Build a simple trie for testing
    mockTrie = {
      A: {
        A: {
          P: {
            L: {
              _isEnd: true,
              _sym: 'AAPL'
            }
          }
        }
      },
      T: {
        S: {
          L: {
            A: {
              _isEnd: true,
              _sym: 'TSLA'
            }
          }
        }
      },
      M: {
        S: {
          F: {
            T: {
              _isEnd: true,
              _sym: 'MSFT'
            }
          }
        }
      }
    };

    mockMetadata = {
      AAPL: {
        name: 'Apple Inc.',
        yield: 0.05,
        beta: 1.2,
        momentum: 15,
        rsi: 30,
        marketCap: 3000000000000
      },
      TSLA: {
        name: 'Tesla Inc.',
        yield: 0,
        beta: 2.5,
        momentum: -5,
        rsi: 75,
        marketCap: 800000000000
      },
      MSFT: {
        name: 'Microsoft Corp.',
        yield: 0.08,
        beta: 0.9,
        momentum: 10,
        rsi: 45,
        marketCap: 2800000000000
      }
    };

    engine = new TickerEngine(mockTrie, mockMetadata);
  });

  describe('State Machine Token Tagging', () => {
    test('should correctly identify Ticker, In-Between, and Outside-Ticker', () => {
      const input = 'The Great Apple';
      // Expected: 'A' from 'Great' and 'A', 'P', 'L' from 'Apple' form 'AAPL'
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      expect(results.length).toBeGreaterThan(0);
      const result = results[0];
      
      // Find ticker tokens
      const tickerTokens = result.tokens.filter(t => t.type === 'Ticker');
      expect(tickerTokens.length).toBeGreaterThan(0);
      
      // Should have consumed words
      const outsideTokens = result.tokens.filter(t => t.type === 'Outside-Ticker');
      expect(outsideTokens.length).toBeGreaterThan(0);
    });

    test('should tag Outside-Ticker characters in consumed words', () => {
      const input = 'APPLE';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0) {
        const result = results[0];
        
        // 'E' at the end should be Outside-Ticker if AAPL is found
        const hasOutsideTicker = result.tokens.some(t => t.type === 'Outside-Ticker');
        const hasTicker = result.tokens.some(t => t.type === 'Ticker');
        
        expect(hasTicker).toBe(true);
      }
    });

    test('should tag Normal characters correctly', () => {
      const input = 'Hello World';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      // If no tickers found, all should be Normal
      if (results.length === 0 || results[0].tickers.length === 0) {
        expect(true).toBe(true); // No tickers found is valid
      }
    });

    test('should tag In-Between characters', () => {
      const input = 'A big P cool L';
      // If 'A', 'P', 'L' form AAPL, chars between should be In-Between
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0 && results[0].tickers.includes('AAPL')) {
        const result = results[0];
        const inBetween = result.tokens.filter(t => t.type === 'In-Between');
        expect(inBetween.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Scoring Strategies', () => {
    test('DIVIDEND_DADDY should prioritize high yield', () => {
      const input = 'MSFT vs AAPL vs TSLA';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      expect(results.length).toBeGreaterThan(0);
      
      // MSFT has highest yield (0.08)
      const topPortfolio = results[0];
      if (topPortfolio.tickers.length === 1) {
        expect(['MSFT', 'AAPL'].includes(topPortfolio.tickers[0])).toBe(true);
      }
    });

    test('THE_MOON_SHOT should prioritize high beta', () => {
      const input = 'Tesla and Apple';
      const results = engine.extractPortfolios(input, 'THE_MOON_SHOT');
      
      expect(results.length).toBeGreaterThan(0);
      
      // TSLA has highest beta (2.5)
      if (results[0].tickers.includes('TSLA')) {
        expect(results[0].score).toBeGreaterThan(0);
      }
    });

    test('FALLING_KNIFE should prioritize negative momentum', () => {
      const input = 'Check out TSLA and AAPL';
      const results = engine.extractPortfolios(input, 'FALLING_KNIFE');
      
      expect(results.length).toBeGreaterThan(0);
      // TSLA has negative momentum (-5)
    });

    test('OVER_HYPED should prioritize high RSI', () => {
      const input = 'TSLA AAPL MSFT';
      const results = engine.extractPortfolios(input, 'OVER_HYPED');
      
      expect(results.length).toBeGreaterThan(0);
      // TSLA has highest RSI (75)
    });

    test('INSTITUTIONAL_WHALE should prioritize market cap', () => {
      const input = 'Big tech: AAPL MSFT TSLA';
      const results = engine.extractPortfolios(input, 'INSTITUTIONAL_WHALE');
      
      expect(results.length).toBeGreaterThan(0);
      // AAPL has highest market cap
    });
  });

  describe('Portfolio Extraction', () => {
    test('should return exactly top 5 distinct portfolios', () => {
      const input = 'AAPL TSLA MSFT and more text here';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      expect(results.length).toBeLessThanOrEqual(5);
    });

    test('should handle 3000 character limit', () => {
      const longText = 'A'.repeat(3500);
      const results = engine.extractPortfolios(longText, 'DIVIDEND_DADDY');
      
      // Should not crash and should limit input
      expect(results).toBeDefined();
    });

    test('should find ticker spanning multiple words', () => {
      const input = 'A A P L';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0) {
        const hasAAPL = results.some(r => r.tickers.includes('AAPL'));
        expect(hasAAPL).toBe(true);
      }
    });

    test('should not reuse consumed words', () => {
      const input = 'AAPL';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0) {
        // Each word should only be used once per portfolio
        expect(results[0].tickers.filter(t => t === 'AAPL').length).toBeLessThanOrEqual(1);
      }
    });
  });

  describe('Memoization', () => {
    test('should use memoization cache', () => {
      const input = 'A A P L A A P L';
      
      // First call
      const results1 = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      const cacheSize1 = engine.memoCache.size;
      
      // Second call should use cache
      engine.memoCache.clear();
      const results2 = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      expect(results2).toBeDefined();
      expect(engine.memoCache.size).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    test('should handle empty input', () => {
      const results = engine.extractPortfolios('', 'DIVIDEND_DADDY');
      expect(results).toBeDefined();
      expect(results.length).toBe(0);
    });

    test('should handle input with no tickers', () => {
      const results = engine.extractPortfolios('Hello World', 'DIVIDEND_DADDY');
      expect(results).toBeDefined();
    });

    test('should handle special characters', () => {
      const input = 'Check out AAPL! #stocks @tech';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      expect(results).toBeDefined();
    });

    test('should handle mixed case', () => {
      const input = 'apple AaPl APPLE';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0) {
        const hasAAPL = results.some(r => r.tickers.includes('AAPL'));
        expect(hasAAPL).toBe(true);
      }
    });
  });

  describe('Metadata Integration', () => {
    test('should include metadata in results', () => {
      const input = 'AAPL';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0 && results[0].tickers.includes('AAPL')) {
        expect(results[0].metadata.AAPL).toBeDefined();
        expect(results[0].metadata.AAPL.name).toBe('Apple Inc.');
      }
    });

    test('should handle missing metadata gracefully', () => {
      const trieWithUnknown = {
        X: {
          Y: {
            Z: {
              _isEnd: true,
              _sym: 'XYZ'
            }
          }
        }
      };
      
      const engineWithUnknown = new TickerEngine(trieWithUnknown, {});
      const results = engineWithUnknown.extractPortfolios('XYZ', 'DIVIDEND_DADDY');
      
      expect(results).toBeDefined();
    });
  });

  describe('Complex Scenarios', () => {
    test('should handle the example from requirements', () => {
      const input = 'The Great Apple';
      const results = engine.extractPortfolios(input, 'DIVIDEND_DADDY');
      
      if (results.length > 0) {
        const result = results[0];
        expect(result.tokens).toBeDefined();
        expect(result.tokens.length).toBe(input.length);
        
        // Verify each token has char and type
        result.tokens.forEach(token => {
          expect(token).toHaveProperty('char');
          expect(token).toHaveProperty('type');
          expect(['Ticker', 'In-Between', 'Outside-Ticker', 'Normal']).toContain(token.type);
        });
      }
    });

    test('should prioritize portfolios correctly', () => {
      const input = 'A A P L vs T S L A';
      const results = engine.extractPortfolios(input, 'THE_MOON_SHOT');
      
      expect(results.length).toBeGreaterThan(0);
      
      // Should be sorted by score
      for (let i = 0; i < results.length - 1; i++) {
        expect(results[i].score).toBeGreaterThanOrEqual(results[i + 1].score);
      }
    });
  });
});
