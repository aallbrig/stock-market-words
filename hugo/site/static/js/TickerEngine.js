/**
 * TickerEngine: A non-greedy backtracking search engine for finding stock tickers in text
 * 
 * State Machine Tags:
 * - Ticker: Characters forming the ticker symbol
 * - In-Between: Characters between first and last ticker character
 * - Outside-Ticker: Characters in consumed word outside ticker boundaries
 * - Normal: All other characters
 */

class TickerEngine {
  constructor(trie, metadata) {
    this.trie = trie;
    this.metadata = metadata;
    this.MAX_INPUT_LENGTH = 3000;
    this.memoCache = new Map();
    
    // Scoring strategies
    this.strategies = {
      DIVIDEND_DADDY: (meta) => meta.yield || 0,
      THE_MOON_SHOT: (meta) => meta.beta || 0,
      FALLING_KNIFE: (meta) => -(meta.momentum || 0),
      OVER_HYPED: (meta) => meta.rsi || 0,
      INSTITUTIONAL_WHALE: (meta) => meta.marketCap || 0
    };
  }

  /**
   * Extract top 5 portfolio options from text
   * @param {string} text - Input text (max 3000 chars)
   * @param {string} strategy - Scoring strategy key
   * @returns {Array} Top 5 portfolio options with tokens and scores
   */
  extractPortfolios(text, strategy = 'DIVIDEND_DADDY') {
    if (text.length > this.MAX_INPUT_LENGTH) {
      text = text.substring(0, this.MAX_INPUT_LENGTH);
    }

    this.memoCache.clear();
    const scoringFn = this.strategies[strategy] || this.strategies.DIVIDEND_DADDY;
    
    // Parse text into words with their positions
    const words = this.parseWords(text);
    
    if (words.length === 0) {
      return [];
    }
    
    // Find all possible tickers
    const allTickers = this.findAllTickers(text, words);
    
    // Generate portfolio combinations
    const portfolios = this.generatePortfolios(text, words, allTickers, scoringFn);
    
    // Return top 5 distinct portfolios
    return this.getTopDistinctPortfolios(portfolios, 5);
  }

  /**
   * Parse text into words with position tracking
   */
  parseWords(text) {
    const words = [];
    let currentWord = '';
    let startIdx = -1;
    
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      if (/[A-Za-z]/.test(char)) {
        if (startIdx === -1) startIdx = i;
        currentWord += char;
      } else {
        if (currentWord) {
          words.push({
            text: currentWord,
            start: startIdx,
            end: i - 1
          });
          currentWord = '';
          startIdx = -1;
        }
      }
    }
    
    if (currentWord) {
      words.push({
        text: currentWord,
        start: startIdx,
        end: text.length - 1
      });
    }
    
    return words;
  }

  /**
   * Find all possible tickers in the text
   */
  findAllTickers(text, words) {
    const tickers = [];
    
    // Try every combination of up to 3 consecutive words
    for (let startIdx = 0; startIdx < words.length; startIdx++) {
      for (let endIdx = startIdx; endIdx < Math.min(startIdx + 3, words.length); endIdx++) {
        const matches = this.findTickerInWordRange(text, words, startIdx, endIdx);
        tickers.push(...matches);
      }
    }
    
    return tickers;
  }

  /**
   * Find tickers spanning a range of words
   */
  findTickerInWordRange(text, words, startIdx, endIdx) {
    const results = [];
    const involvedWordIndices = [];
    for (let i = startIdx; i <= endIdx; i++) {
      involvedWordIndices.push(i);
    }
    
    // Collect all characters from involved words
    const charPositions = [];
    for (const wordIdx of involvedWordIndices) {
      const word = words[wordIdx];
      for (let i = word.start; i <= word.end; i++) {
        charPositions.push({
          char: text[i].toUpperCase(),
          position: i,
          wordIdx: wordIdx
        });
      }
    }
    
    // Try to match tickers
    const matches = this.matchTickersInChars(charPositions, involvedWordIndices);
    return matches;
  }

  /**
   * Match ticker symbols from character positions using trie
   */
  matchTickersInChars(charPositions, involvedWordIndices) {
    const matches = [];
    
    // Greedy search for the longest ticker
    const search = (startIdx, node, path, usedPositions) => {
      let foundMatch = null;
      
      if (node._isEnd && path.length > 0) {
        foundMatch = {
          symbol: node._sym,
          path: [...path],
          usedPositions: [...usedPositions]
        };
      }
      
      for (let i = startIdx; i < charPositions.length; i++) {
        const { char, position } = charPositions[i];
        
        if (node[char]) {
          const result = search(i + 1, node[char], [...path, i], [...usedPositions, position]);
          if (result && (!foundMatch || result.symbol.length > foundMatch.symbol.length)) {
            foundMatch = result;
          }
        }
      }
      
      return foundMatch;
    };
    
    const match = search(0, this.trie, [], []);
    
    if (match) {
      matches.push({
        symbol: match.symbol,
        charIndices: match.path.map(idx => charPositions[idx].position),
        consumedWordIndices: involvedWordIndices
      });
    }
    
    return matches;
  }

  /**
   * Generate portfolios from found tickers
   */
  generatePortfolios(text, words, allTickers, scoringFn) {
    const portfolios = [];
    
    // Single ticker portfolios
    for (const ticker of allTickers) {
      portfolios.push(this.createPortfolio(text, words, [ticker], new Set(ticker.consumedWordIndices), scoringFn));
    }
    
    // Multi-ticker portfolios (non-overlapping)
    for (let i = 0; i < allTickers.length && portfolios.length < 100; i++) {
      for (let j = i + 1; j < allTickers.length && portfolios.length < 100; j++) {
        const ticker1 = allTickers[i];
        const ticker2 = allTickers[j];
        
        // Check if they don't overlap
        const overlap = ticker1.consumedWordIndices.some(idx => 
          ticker2.consumedWordIndices.includes(idx)
        );
        
        if (!overlap) {
          const consumed = new Set([...ticker1.consumedWordIndices, ...ticker2.consumedWordIndices]);
          portfolios.push(this.createPortfolio(text, words, [ticker1, ticker2], consumed, scoringFn));
        }
      }
    }
    
    return portfolios;
  }

  /**
   * Create a portfolio object with token tagging
   */
  createPortfolio(text, words, tickers, consumedWords, scoringFn) {
    const tokens = [];
    const tickerSymbols = tickers.map(t => t.symbol);
    
    // Create a map of character index to ticker info
    const charToTicker = new Map();
    tickers.forEach(ticker => {
      ticker.charIndices.forEach(charIdx => {
        charToTicker.set(charIdx, ticker);
      });
    });
    
    // Tag each character
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      let type = 'Normal';
      
      // Check if this position belongs to a ticker
      if (charToTicker.has(i)) {
        type = 'Ticker';
      } else {
        // Check if this character is in a consumed word
        const word = words.find(w => i >= w.start && i <= w.end);
        if (word && consumedWords.has(words.indexOf(word))) {
          // Check if it's between ticker boundaries
          const relatedTicker = tickers.find(t => 
            t.consumedWordIndices.includes(words.indexOf(word))
          );
          
          if (relatedTicker) {
            const minIdx = Math.min(...relatedTicker.charIndices);
            const maxIdx = Math.max(...relatedTicker.charIndices);
            
            if (i < minIdx || i > maxIdx) {
              type = 'Outside-Ticker';
            } else if (i > minIdx && i < maxIdx) {
              type = 'In-Between';
            }
          }
        }
      }
      
      tokens.push({ char, type });
    }
    
    // Calculate portfolio score
    let score = 0;
    let validTickers = 0;
    
    for (const symbol of tickerSymbols) {
      if (this.metadata[symbol]) {
        score += scoringFn(this.metadata[symbol]);
        validTickers++;
      }
    }
    
    score = validTickers > 0 ? score / validTickers : 0;
    
    return {
      tickers: tickerSymbols,
      tokens,
      score,
      metadata: tickerSymbols.reduce((acc, sym) => {
        if (this.metadata[sym]) {
          acc[sym] = this.metadata[sym];
        }
        return acc;
      }, {})
    };
  }

  /**
   * Get top N distinct portfolios
   */
  getTopDistinctPortfolios(portfolios, n) {
    // Create unique portfolios by ticker combination
    const uniqueMap = new Map();
    
    for (const portfolio of portfolios) {
      const key = portfolio.tickers.sort().join(',');
      if (!uniqueMap.has(key) || uniqueMap.get(key).score < portfolio.score) {
        uniqueMap.set(key, portfolio);
      }
    }
    
    // Sort by score and return top N
    return Array.from(uniqueMap.values())
      .sort((a, b) => b.score - a.score)
      .slice(0, n);
  }
}

// Export for both Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TickerEngine;
} else if (typeof window !== 'undefined') {
  window.TickerEngine = TickerEngine;
}
