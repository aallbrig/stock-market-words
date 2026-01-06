// Web Worker for portfolio computation
// This runs in a separate thread to prevent UI freezing

let tickerData = null;
let tickerTrie = null;

const STRATEGIES = {
    DIVIDEND_DADDY: {
        scorer: (t) => ((t.dividendYield || 0) * 100) + (t.beta ? (100 - Math.abs(t.beta) * 20) : 50)
    },
    MOON_SHOT: {
        scorer: (t) => ((t.beta || 0) * 50) + (t.rsi ? (100 - t.rsi) : 0)
    },
    FALLING_KNIFE: {
        scorer: (t) => {
            const rsi = t.rsi ? (100 - t.rsi) : 0;
            const ma = (t.ma200 && t.price) ? Math.max(0, ((t.ma200 - t.price) / t.price) * 100) : 0;
            return rsi + ma;
        }
    },
    OVER_HYPED: {
        scorer: (t) => t.rsi || 0
    },
    INSTITUTIONAL_WHALE: {
        scorer: (t) => t.marketCap ? Math.log10(t.marketCap) : 0
    }
};

// Listen for messages from main thread
self.onmessage = function(e) {
    const { type, data } = e.data;
    
    if (type === 'INIT') {
        tickerData = data.tickerData;
        tickerTrie = data.tickerTrie;
        self.postMessage({ type: 'INIT_COMPLETE' });
    } 
    else if (type === 'COMPUTE') {
        const { text, words } = data;
        
        try {
            // Generate 5 different portfolios, one per strategy
            const portfolios = {};
            for (const key of Object.keys(STRATEGIES)) {
                portfolios[key] = findBestPortfolio(text, words, key);
            }
            
            self.postMessage({ 
                type: 'RESULT', 
                data: { portfolios, text, words } 
            });
        } catch (error) {
            self.postMessage({ 
                type: 'ERROR', 
                error: error.message 
            });
        }
    }
};

function findBestPortfolio(text, words, strategy) {
    const scorer = STRATEGIES[strategy].scorer;
    const memo = new Map();
    
    function search(wordIdx, currentTickers, usedWords) {
        if (wordIdx >= words.length) {
            return { 
                tickers: currentTickers, 
                score: currentTickers.reduce((s, t) => s + scorer(tickerData[t.symbol]), 0) 
            };
        }
        
        const key = `${wordIdx}-${Array.from(usedWords).sort().join(',')}`;
        if (memo.has(key)) {
            return memo.get(key);
        }
        
        const skipResult = search(wordIdx + 1, currentTickers, usedWords);
        let bestResult = skipResult;
        
        if (!usedWords.has(wordIdx) && wordIdx < words.length - 2) {
            for (let span = 1; span <= Math.min(3, words.length - wordIdx); span++) {
                const endWordIdx = wordIdx + span - 1;
                
                let spanUsed = false;
                for (let i = wordIdx; i <= endWordIdx; i++) {
                    if (usedWords.has(i)) {
                        spanUsed = true;
                        break;
                    }
                }
                if (spanUsed) continue;
                
                const ticker = findTickerInSpan(text, words, wordIdx, endWordIdx);
                if (ticker) {
                    const newUsed = new Set(usedWords);
                    for (let i = wordIdx; i <= endWordIdx; i++) newUsed.add(i);
                    
                    const restResult = search(endWordIdx + 1, [...currentTickers, ticker], newUsed);
                    if (restResult.score > bestResult.score) {
                        bestResult = restResult;
                    }
                }
            }
        }
        
        memo.set(key, bestResult);
        return bestResult;
    }
    
    return search(0, [], new Set());
}

function findTickerInSpan(text, words, startWordIdx, endWordIdx) {
    const chars = [];
    for (let i = startWordIdx; i <= endWordIdx; i++) {
        const word = words[i];
        for (let j = word.start; j <= word.end; j++) {
            chars.push({ char: text[j].toUpperCase(), pos: j, wordIdx: i });
        }
    }
    
    function search(charIdx, node, path) {
        let best = null;
        if (node._isEnd) {
            best = { 
                symbol: node._sym, 
                charIndices: path.map(idx => chars[idx].pos), 
                consumedWords: [startWordIdx, endWordIdx] 
            };
        }
        for (let i = charIdx; i < chars.length; i++) {
            if (node[chars[i].char]) {
                const result = search(i + 1, node[chars[i].char], [...path, i]);
                if (result && (!best || result.symbol.length > best.symbol.length)) {
                    best = result;
                }
            }
        }
        return best;
    }
    
    return search(0, tickerTrie, []);
}
