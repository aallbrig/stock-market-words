/**
 * Performance tests for TickerEngine.js
 * Tests the algorithm with sample texts from the UI, enforcing a 60-second timeout
 */

const TickerEngine = require('../../hugo/site/static/js/TickerEngine');

// Sample texts from the UI (portfolio-extractor.js DEMO_EXAMPLES)
const SAMPLE_TEXTS = {
  SHORT: "The cat sat on the mat eating a can of food while watching tv.",
  
  MEDIUM: "My dad works at Ford. Yesterday he drove his Uber to the store to buy some Pepsi and groceries from Costco. On the way back he stopped at the bar to meet his friend Jack who works at Target.",
  
  LONG: "The tech industry saw major changes this year. Companies like Apple and Dell released new products while Oracle expanded their cloud services. Meanwhile analysts noted how British American Tobacco continued its dominance in Asian markets.\n\nIn the automotive sector Ford announced electric vehicle plans and General Motors followed suit. Uber and Doordash both reported strong quarterly earnings. The ride sharing wars continue with Grab making moves in Southeast Asia.\n\nRetail giants Costco and Target adapted to changing consumer habits. Lowes improved their home improvement offerings while Home Depot focused on professional contractors. The fast food industry saw consolidation with Jack in the Box and Sonic exploring merger possibilities."
};

// Mock ticker data and trie for testing
function createMockTickerData() {
  const tickers = [
    'T', 'CAT', 'CAN', 'TV', 'F', 'UBER', 'PEP', 'COST', 'JACK', 'TGT',
    'AAPL', 'DELL', 'ORCL', 'BTI', 'GM', 'DASH', 'GRAB', 'LOW', 
    'HD', 'SONC', 'MA', 'TECH', 'BAR', 'A', 'O', 'C', 'ST', 'H', 'WH', 'ETN'
  ];
  
  const metadata = {};
  tickers.forEach((symbol, idx) => {
    metadata[symbol] = {
      symbol,
      name: `Company ${symbol}`,
      price: 100 + idx * 10,
      volume: 1000000,
      marketCap: 1000000000 + idx * 100000000,
      dividendYield: 0.02 + (idx * 0.001),
      beta: 1.0 + (idx * 0.1),
      rsi: 50 + (idx % 30),
      ma200: 95 + idx * 10
    };
  });
  
  return { tickers, metadata };
}

function buildTrie(symbols) {
  const trie = {};
  for (const sym of symbols) {
    let node = trie;
    for (const c of sym) {
      if (!node[c]) node[c] = {};
      node = node[c];
    }
    node._isEnd = true;
    node._sym = sym;
  }
  return trie;
}

describe('TickerEngine Performance Tests', () => {
  let engine;
  
  beforeAll(() => {
    const { tickers, metadata } = createMockTickerData();
    const trie = buildTrie(tickers);
    engine = new TickerEngine(trie, metadata);
  });
  
  describe('Sample Text Performance', () => {
    const MAX_RUNTIME_MS = 60000; // 60 seconds max
    
    test('SHORT sample text completes within 60 seconds', () => {
      const startTime = Date.now();
      const result = engine.extractPortfolios(SAMPLE_TEXTS.SHORT, 'DIVIDEND_DADDY');
      const duration = Date.now() - startTime;
      
      console.log(`SHORT text completed in ${duration}ms`);
      expect(duration).toBeLessThan(MAX_RUNTIME_MS);
      expect(Array.isArray(result)).toBe(true);
    }, MAX_RUNTIME_MS);
    
    test('MEDIUM sample text completes within 60 seconds', () => {
      const startTime = Date.now();
      const result = engine.extractPortfolios(SAMPLE_TEXTS.MEDIUM, 'DIVIDEND_DADDY');
      const duration = Date.now() - startTime;
      
      console.log(`MEDIUM text completed in ${duration}ms`);
      expect(duration).toBeLessThan(MAX_RUNTIME_MS);
      expect(Array.isArray(result)).toBe(true);
    }, MAX_RUNTIME_MS);
    
    test('LONG sample text completes within 60 seconds', () => {
      const startTime = Date.now();
      const result = engine.extractPortfolios(SAMPLE_TEXTS.LONG, 'DIVIDEND_DADDY');
      const duration = Date.now() - startTime;
      
      console.log(`LONG text completed in ${duration}ms`);
      expect(duration).toBeLessThan(MAX_RUNTIME_MS);
      expect(Array.isArray(result)).toBe(true);
    }, MAX_RUNTIME_MS);
  });
  
  describe('All Strategies Performance', () => {
    const MAX_RUNTIME_MS = 60000;
    const strategies = ['DIVIDEND_DADDY', 'MOON_SHOT', 'FALLING_KNIFE', 'OVER_HYPED', 'INSTITUTIONAL_WHALE'];
    
    strategies.forEach(strategy => {
      test(`${strategy} strategy on MEDIUM text completes within 60 seconds`, () => {
        const startTime = Date.now();
        const result = engine.extractPortfolios(SAMPLE_TEXTS.MEDIUM, strategy);
        const duration = Date.now() - startTime;
        
        console.log(`${strategy} completed in ${duration}ms`);
        expect(duration).toBeLessThan(MAX_RUNTIME_MS);
        expect(Array.isArray(result)).toBe(true);
      }, MAX_RUNTIME_MS);
    });
  });
  
  describe('Performance Benchmarking', () => {
    test('Measure average execution time for SHORT text', () => {
      const iterations = 10;
      const times = [];
      
      for (let i = 0; i < iterations; i++) {
        const start = Date.now();
        engine.extractPortfolios(SAMPLE_TEXTS.SHORT, 'DIVIDEND_DADDY');
        times.push(Date.now() - start);
      }
      
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      const min = Math.min(...times);
      const max = Math.max(...times);
      
      console.log(`SHORT text stats over ${iterations} runs:`);
      console.log(`  Average: ${avg.toFixed(2)}ms`);
      console.log(`  Min: ${min}ms`);
      console.log(`  Max: ${max}ms`);
      
      expect(avg).toBeLessThan(60000);
    });
    
    test('Measure average execution time for MEDIUM text', () => {
      const iterations = 10;
      const times = [];
      
      for (let i = 0; i < iterations; i++) {
        const start = Date.now();
        engine.extractPortfolios(SAMPLE_TEXTS.MEDIUM, 'DIVIDEND_DADDY');
        times.push(Date.now() - start);
      }
      
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      const min = Math.min(...times);
      const max = Math.max(...times);
      
      console.log(`MEDIUM text stats over ${iterations} runs:`);
      console.log(`  Average: ${avg.toFixed(2)}ms`);
      console.log(`  Min: ${min}ms`);
      console.log(`  Max: ${max}ms`);
      
      expect(avg).toBeLessThan(60000);
    });
    
    test('Measure average execution time for LONG text', () => {
      const iterations = 5; // Fewer iterations for longer text
      const times = [];
      
      for (let i = 0; i < iterations; i++) {
        const start = Date.now();
        engine.extractPortfolios(SAMPLE_TEXTS.LONG, 'DIVIDEND_DADDY');
        times.push(Date.now() - start);
      }
      
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      const min = Math.min(...times);
      const max = Math.max(...times);
      
      console.log(`LONG text stats over ${iterations} runs:`);
      console.log(`  Average: ${avg.toFixed(2)}ms`);
      console.log(`  Min: ${min}ms`);
      console.log(`  Max: ${max}ms`);
      
      expect(avg).toBeLessThan(60000);
    });
  });
  
  describe('Memory and Cache Performance', () => {
    test('Cache is cleared between runs', () => {
      engine.extractPortfolios(SAMPLE_TEXTS.SHORT, 'DIVIDEND_DADDY');
      expect(engine.memoCache.size).toBe(0); // Should be cleared after each run
    });
    
    test('Multiple sequential runs complete successfully', () => {
      const startTime = Date.now();
      
      for (let i = 0; i < 5; i++) {
        const result = engine.extractPortfolios(SAMPLE_TEXTS.MEDIUM, 'DIVIDEND_DADDY');
        expect(Array.isArray(result)).toBe(true);
      }
      
      const duration = Date.now() - startTime;
      console.log(`5 sequential runs completed in ${duration}ms`);
      expect(duration).toBeLessThan(60000);
    });
  });
  
  describe('Duplicate Prevention Tests', () => {
    test('SHORT sample should not have duplicate ticker symbols', () => {
      const result = engine.extractPortfolios(SAMPLE_TEXTS.SHORT, 'DIVIDEND_DADDY');
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      
      const portfolio = result[0];
      const symbols = portfolio.tickers;  // tickers is already an array of strings
      const uniqueSymbols = [...new Set(symbols)];
      
      console.log(`SHORT text found: ${symbols.join(', ')}`);
      console.log(`Unique count: ${uniqueSymbols.length}, Total count: ${symbols.length}`);
      
      expect(symbols.length).toBe(uniqueSymbols.length);
    });
    
    test('MEDIUM sample should not have duplicate ticker symbols', () => {
      const result = engine.extractPortfolios(SAMPLE_TEXTS.MEDIUM, 'DIVIDEND_DADDY');
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      
      const portfolio = result[0];
      const symbols = portfolio.tickers;
      const uniqueSymbols = [...new Set(symbols)];
      
      console.log(`MEDIUM text found: ${symbols.join(', ')}`);
      console.log(`Unique count: ${uniqueSymbols.length}, Total count: ${symbols.length}`);
      
      expect(symbols.length).toBe(uniqueSymbols.length);
    });
    
    test('LONG sample should not have duplicate ticker symbols', () => {
      const result = engine.extractPortfolios(SAMPLE_TEXTS.LONG, 'DIVIDEND_DADDY');
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      
      const portfolio = result[0];
      const symbols = portfolio.tickers;
      const uniqueSymbols = [...new Set(symbols)];
      
      console.log(`LONG text found: ${symbols.join(', ')}`);
      console.log(`Unique count: ${uniqueSymbols.length}, Total count: ${symbols.length}`);
      
      expect(symbols.length).toBe(uniqueSymbols.length);
    });
  });
});
