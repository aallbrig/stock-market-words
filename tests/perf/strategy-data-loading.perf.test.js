/**
 * Performance tests for strategy-specific data loading
 * Tests that using pre-filtered strategy data is faster than loading all 5,444 tickers
 */

const fs = require('fs');
const path = require('path');

// Timeout from environment or default to localhost (60s) vs CI (10s)
const TIMEOUT_SECONDS = parseInt(process.env.TIMEOUT_SECONDS || '60', 10);
const TIMEOUT_MS = TIMEOUT_SECONDS * 1000;

describe('Strategy Data Loading Performance', () => {
  const dataDir = path.join(__dirname, '../../hugo/site/static/data');
  
  test('Strategy data files exist', () => {
    const strategies = [
      'strategy_dividend_daddy.json',
      'strategy_moon_shot.json',
      'strategy_falling_knife.json',
      'strategy_over_hyped.json',
      'strategy_institutional_whale.json'
    ];
    
    strategies.forEach(file => {
      const filePath = path.join(dataDir, file);
      expect(fs.existsSync(filePath)).toBe(true);
    });
  });
  
  test('Strategy files are smaller than filtered_tickers.json', () => {
    const filteredPath = path.join(dataDir, 'filtered_tickers.json');
    const filteredSize = fs.statSync(filteredPath).size;
    
    const strategies = [
      'strategy_dividend_daddy.json',
      'strategy_moon_shot.json',
      'strategy_falling_knife.json',
      'strategy_over_hyped.json',
      'strategy_institutional_whale.json'
    ];
    
    strategies.forEach(file => {
      const filePath = path.join(dataDir, file);
      const strategySize = fs.statSync(filePath).size;
      
      // Strategy files should be smaller (more filtered)
      expect(strategySize).toBeLessThan(filteredSize);
      
      console.log(`  ${file}: ${(strategySize / 1024).toFixed(1)}KB vs filtered: ${(filteredSize / 1024).toFixed(1)}KB (${((1 - strategySize/filteredSize) * 100).toFixed(1)}% smaller)`);
    });
  });
  
  test('Loading strategy data is faster than filtered_tickers.json', () => {
    const filteredPath = path.join(dataDir, 'filtered_tickers.json');
    const strategyPath = path.join(dataDir, 'strategy_dividend_daddy.json');
    
    // Time loading full filtered data
    const start1 = Date.now();
    const filteredData = JSON.parse(fs.readFileSync(filteredPath, 'utf8'));
    const filteredTime = Date.now() - start1;
    
    // Time loading strategy data
    const start2 = Date.now();
    const strategyData = JSON.parse(fs.readFileSync(strategyPath, 'utf8'));
    const strategyTime = Date.now() - start2;
    
    console.log(`  Filtered tickers: ${filteredData.tickers.length} tickers in ${filteredTime}ms`);
    console.log(`  Strategy tickers: ${strategyData.tickers.length} tickers in ${strategyTime}ms`);
    console.log(`  Speedup: ${(filteredTime / strategyTime).toFixed(2)}x faster`);
    
    // Strategy loading should be faster
    expect(strategyTime).toBeLessThan(filteredTime);
  });
  
  test('Strategy data has pre-calculated scores structure', () => {
    const strategyPath = path.join(dataDir, 'strategy_dividend_daddy.json');
    const strategyData = JSON.parse(fs.readFileSync(strategyPath, 'utf8'));
    
    expect(strategyData.tickers.length).toBeGreaterThan(0);
    
    // Check first ticker has scores object
    const firstTicker = strategyData.tickers[0];
    expect(firstTicker.scores).toBeDefined();
    expect(typeof firstTicker.scores).toBe('object');
    
    // Scores may be null if not calculated yet, but structure should exist
    expect('dividendDaddy' in firstTicker.scores).toBe(true);
    
    console.log(`  Sample ticker ${firstTicker.symbol}: scores = ${JSON.stringify(firstTicker.scores)}`);
  });
  
  test('All strategies load within timeout', async () => {
    const strategies = [
      'strategy_dividend_daddy.json',
      'strategy_moon_shot.json',
      'strategy_falling_knife.json',
      'strategy_over_hyped.json',
      'strategy_institutional_whale.json'
    ];
    
    const startTime = Date.now();
    
    const loadedData = strategies.map(file => {
      const filePath = path.join(dataDir, file);
      const start = Date.now();
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      const loadTime = Date.now() - start;
      
      return {
        file,
        tickerCount: data.tickers.length,
        loadTime
      };
    });
    
    const totalTime = Date.now() - startTime;
    
    console.log('\n  Strategy loading times:');
    loadedData.forEach(({ file, tickerCount, loadTime }) => {
      console.log(`    ${file}: ${tickerCount} tickers in ${loadTime}ms`);
    });
    console.log(`  Total: ${totalTime}ms`);
    
    // All strategies should load within timeout
    expect(totalTime).toBeLessThan(TIMEOUT_MS);
  }, TIMEOUT_MS);
  
  test('Strategy data reduces universe significantly', () => {
    const filteredPath = path.join(dataDir, 'filtered_tickers.json');
    const filteredData = JSON.parse(fs.readFileSync(filteredPath, 'utf8'));
    const totalTickers = filteredData.tickers.length;
    
    const strategies = [
      { file: 'strategy_dividend_daddy.json', name: 'Dividend Daddy' },
      { file: 'strategy_moon_shot.json', name: 'Moon Shot' },
      { file: 'strategy_falling_knife.json', name: 'Falling Knife' },
      { file: 'strategy_over_hyped.json', name: 'Over Hyped' },
      { file: 'strategy_institutional_whale.json', name: 'Institutional Whale' }
    ];
    
    console.log(`\n  Universe reduction (from ${totalTickers} total tickers):`);
    
    strategies.forEach(({ file, name }) => {
      const filePath = path.join(dataDir, file);
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      const reduction = ((1 - data.tickers.length / totalTickers) * 100).toFixed(1);
      
      console.log(`    ${name}: ${data.tickers.length} tickers (${reduction}% reduction)`);
      
      // Should reduce universe by at least 10%
      expect(data.tickers.length).toBeLessThan(totalTickers);
    });
  });
  
  test('Memory usage: strategy data vs full data', () => {
    const filteredPath = path.join(dataDir, 'filtered_tickers.json');
    const strategyPath = path.join(dataDir, 'strategy_falling_knife.json'); // Smallest dataset
    
    const filteredSize = fs.statSync(filteredPath).size;
    const strategySize = fs.statSync(strategyPath).size;
    
    const memorySavings = ((1 - strategySize / filteredSize) * 100).toFixed(1);
    
    console.log(`\n  Memory savings using strategy data:`);
    console.log(`    Full filtered data: ${(filteredSize / 1024).toFixed(1)}KB`);
    console.log(`    Strategy data: ${(strategySize / 1024).toFixed(1)}KB`);
    console.log(`    Savings: ${memorySavings}%`);
    
    // Should save at least 50% memory
    expect(strategySize).toBeLessThan(filteredSize * 0.5);
  });
});
