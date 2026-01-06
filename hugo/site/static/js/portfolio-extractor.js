// Portfolio Extractor with Web Worker for non-blocking computation
let tickerData = null;
let tickerTrie = null;
let worker = null;

const STRATEGIES = {
    DIVIDEND_DADDY: {
        name: '💰 Dividend Daddy',
        description: 'High yield + low volatility',
        help: 'Finds stocks with high dividend yields and low volatility (beta). Best for income-focused, conservative investors seeking steady returns.',
        scorer: (t) => ((t.dividendYield || 0) * 100) + (t.beta ? (100 - Math.abs(t.beta) * 20) : 50)
    },
    MOON_SHOT: {
        name: '🚀 Moon Shot',
        description: 'High beta + oversold',
        help: 'Identifies high-growth potential stocks with high beta (volatility) and oversold conditions (low RSI). For aggressive growth seekers willing to take risks.',
        scorer: (t) => ((t.beta || 0) * 50) + (t.rsi ? (100 - t.rsi) : 0)
    },
    FALLING_KNIFE: {
        name: '🔪 Falling Knife',
        description: 'Oversold + below MA',
        help: 'Contrarian strategy finding oversold stocks trading below their 200-day moving average. "Catching a falling knife" - high risk but potential for bounce-back gains.',
        scorer: (t) => {
            const rsi = t.rsi ? (100 - t.rsi) : 0;
            const ma = (t.ma200 && t.price) ? Math.max(0, ((t.ma200 - t.price) / t.price) * 100) : 0;
            return rsi + ma;
        }
    },
    OVER_HYPED: {
        name: '🎈 Over-Hyped',
        description: 'Overbought',
        help: 'Finds overbought stocks with high RSI values, suggesting momentum exhaustion. Good for short sellers or mean-reversion traders expecting pullbacks.',
        scorer: (t) => t.rsi || 0
    },
    INSTITUTIONAL_WHALE: {
        name: '🐋 Institutional Whale',
        description: 'Large cap',
        help: 'Targets large-cap stocks likely held by institutional investors. "Follow the smart money" - more stable, liquid, and widely covered by analysts.',
        scorer: (t) => t.marketCap ? Math.log10(t.marketCap) : 0
    }
};

// Initialize Web Worker
function initWorker() {
    if (!worker && typeof Worker !== 'undefined') {
        worker = new Worker('/js/portfolio-worker.js');
        
        worker.onmessage = function(e) {
            const { type, data, error } = e.data;
            
            if (type === 'INIT_COMPLETE') {
                console.log('Worker initialized');
            } 
            else if (type === 'RESULT') {
                handleWorkerResult(data);
            } 
            else if (type === 'ERROR') {
                console.error('Worker error:', error);
                document.getElementById('loading-indicator').style.display = 'none';
                document.querySelector('#ticker-form button[type="submit"]').disabled = false;
                alert('An error occurred while processing your text. Please try again.');
            }
        };
        
        worker.onerror = function(error) {
            console.error('Worker failed:', error);
            worker = null; // Fallback to main thread
        };
    }
}

async function loadTickerData() {
    try {
        const response = await fetch('/data/filtered_tickers.json');
        const data = await response.json();
        tickerData = {};
        const symbols = [];
        data.tickers.forEach(t => {
            if (t.price_data && t.price_data.price) {
                tickerData[t.symbol] = {
                    symbol: t.symbol, name: t.name, exchange: t.exchange,
                    price: t.price_data.price, volume: t.price_data.volume,
                    marketCap: t.price_data.market_cap, dividendYield: t.price_data.dividend_yield,
                    beta: t.price_data.beta, rsi: t.price_data.rsi_14, ma200: t.price_data.ma_200
                };
                symbols.push(t.symbol);
            }
        });
        tickerTrie = buildTrie(symbols);
        console.log(`Loaded ${symbols.length} tickers`);
        
        // Initialize and send data to worker
        initWorker();
        if (worker) {
            worker.postMessage({
                type: 'INIT',
                data: { tickerData, tickerTrie }
            });
        }
        
        return true;
    } catch (error) {
        console.error('Failed to load:', error);
        return false;
    }
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

function parseWords(text) {
    const words = [];
    let word = '', start = -1;
    for (let i = 0; i < text.length; i++) {
        if (/[A-Za-z]/.test(text[i])) {
            if (start === -1) start = i;
            word += text[i];
        } else {
            if (word) {
                words.push({ text: word, start, end: i - 1 });
                word = '';
                start = -1;
            }
        }
    }
    if (word) words.push({ text: word, start, end: text.length - 1 });
    return words;
}

function findBestPortfolio(text, words, strategy) {
    // Backtracking to find highest scoring set of non-overlapping tickers
    const scorer = STRATEGIES[strategy].scorer;
    
    // Memoization for performance
    const memo = new Map();
    
    function search(wordIdx, currentTickers, usedWords) {
        if (wordIdx >= words.length) {
            return { tickers: currentTickers, score: currentTickers.reduce((s, t) => s + scorer(tickerData[t.symbol]), 0) };
        }
        
        // Check memo
        const key = `${wordIdx}-${Array.from(usedWords).sort().join(',')}`;
        if (memo.has(key)) {
            return memo.get(key);
        }
        
        // Option 1: Skip this word
        const skipResult = search(wordIdx + 1, currentTickers, usedWords);
        
        // Option 2: Try to find a ticker starting at this word (limit search depth)
        let bestResult = skipResult;
        
        if (!usedWords.has(wordIdx) && wordIdx < words.length - 2) { // Optimization: limit lookahead
            // Try 1, 2, 3 consecutive words
            for (let span = 1; span <= Math.min(3, words.length - wordIdx); span++) {
                const endWordIdx = wordIdx + span - 1;
                
                // Check if any word in span is already used
                let spanUsed = false;
                for (let i = wordIdx; i <= endWordIdx; i++) {
                    if (usedWords.has(i)) {
                        spanUsed = true;
                        break;
                    }
                }
                if (spanUsed) continue;
                
                // Try to find ticker in this span
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
    // Collect all characters from these words
    const chars = [];
    for (let i = startWordIdx; i <= endWordIdx; i++) {
        const word = words[i];
        for (let j = word.start; j <= word.end; j++) {
            chars.push({ char: text[j].toUpperCase(), pos: j, wordIdx: i });
        }
    }
    
    // Greedy search for longest ticker
    function search(charIdx, node, path) {
        let best = null;
        if (node._isEnd) {
            best = { symbol: node._sym, charIndices: path.map(idx => chars[idx].pos), consumedWords: [startWordIdx, endWordIdx] };
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

function renderHighlighted(text, words, tickers) {
    const charTypes = new Array(text.length).fill('normal');
    const charToTicker = new Map(); // Map char index to ticker symbol
    
    // Mark all consumed characters
    tickers.forEach(t => {
        t.charIndices.forEach(idx => {
            charTypes[idx] = 'ticker';
            charToTicker.set(idx, t.symbol);
        });
        
        const [startWord, endWord] = t.consumedWords;
        for (let i = startWord; i <= endWord; i++) {
            const word = words[i];
            for (let j = word.start; j <= word.end; j++) {
                if (charTypes[j] === 'normal') {
                    charTypes[j] = 'consumed';
                    charToTicker.set(j, t.symbol); // In-between chars also get ticker for grouping
                }
            }
        }
    });
    
    // Group consecutive chars by ticker into spans
    let html = '';
    let currentTicker = null;
    let currentGroupChars = [];
    
    for (let i = 0; i < text.length; i++) {
        const type = charTypes[i];
        const char = text[i];
        const ticker = charToTicker.get(i);
        
        if (ticker && ticker === currentTicker) {
            // Continue building current group
            currentGroupChars.push({ char, type, idx: i });
        } else {
            // Finish previous group if exists
            if (currentTicker) {
                html += renderTickerGroup(currentGroupChars, currentTicker);
                currentGroupChars = [];
            }
            
            // Start new group or add normal char
            if (ticker) {
                currentTicker = ticker;
                currentGroupChars.push({ char, type, idx: i });
            } else {
                currentTicker = null;
                html += escapeHtml(char);
            }
        }
    }
    
    // Finish last group if exists
    if (currentTicker) {
        html += renderTickerGroup(currentGroupChars, currentTicker);
    }
    
    return html;
}

function renderTickerGroup(charArray, ticker) {
    // Separate ticker chars from consumed chars
    let styledContent = '';
    let tickerCharCount = 0;
    
    for (let i = 0; i < charArray.length; i++) {
        const { char, type } = charArray[i];
        
        if (type === 'ticker') {
            tickerCharCount++;
        }
    }
    
    let tickerCharsSeen = 0;
    
    for (let i = 0; i < charArray.length; i++) {
        const { char, type } = charArray[i];
        
        if (type === 'ticker') {
            tickerCharsSeen++;
            let cssClass = 'token-ticker';
            
            if (tickerCharCount === 1) {
                cssClass += ' token-ticker-single';
            } else if (tickerCharsSeen === 1) {
                cssClass += ' token-ticker-first';
            } else if (tickerCharsSeen === tickerCharCount) {
                cssClass += ' token-ticker-last';
            } else {
                cssClass += ' token-ticker-middle';
            }
            
            styledContent += `<span class="${cssClass}">${escapeHtml(char.toUpperCase())}</span>`;
        } else if (type === 'consumed') {
            // In-between/outside chars - muted styling
            styledContent += `<span class="token-in-between">${escapeHtml(char)}</span>`;
        }
    }
    
    return `<span class="ticker-group" title="${ticker}">${styledContent}</span>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderPortfolios(text, words, portfolios) {
    const container = document.getElementById('portfolio-strategies');
    
    if (Object.values(portfolios).every(p => p.tickers.length === 0)) {
        container.innerHTML = '<div class="alert alert-warning">No tickers found. Try: "I love NVIDIA and Tesla stock."</div>';
        return;
    }
    
    let html = '';
    Object.entries(portfolios).forEach(([strategyKey, portfolio]) => {
        const strategy = STRATEGIES[strategyKey];
        html += `
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">
                        ${strategy.name}
                        <span class="strategy-help" title="${strategy.help}">ℹ️</span>
                    </h6>
                    <small>${strategy.description}</small>
                </div>
                <div class="card-body">
        `;
        
        if (portfolio.tickers.length === 0) {
            html += '<p class="text-muted">No tickers scored for this strategy.</p>';
        } else {
            // 1. Show highlighted text FIRST
            html += '<div class="mb-4">';
            html += '<h6>Highlighted Input Text:</h6>';
            html += '<div class="bg-light p-3 border rounded" style="font-family: monospace; white-space: pre-wrap;">';
            html += renderHighlighted(text, words, portfolio.tickers);
            html += '</div>';
            html += '<div class="mt-2"><small class="text-muted">';
            html += '<span class="token-ticker token-ticker-single">Green</span> = Ticker (hover to see symbol)';
            html += '</small></div>';
            html += '</div>';
            
            // 2. Show tickers found
            const symbols = portfolio.tickers.map(t => t.symbol.toUpperCase());
            html += `<p><strong>Tickers found:</strong> ${symbols.join(', ')}</p>`;
            
            // 3. Show ticker details table (with pagination for 10+)
            const tickersPerPage = 10;
            const needsPagination = portfolio.tickers.length > tickersPerPage;
            const tableId = `table-${strategyKey}`;
            
            html += `<table class="table table-sm table-striped mb-3" id="${tableId}"><thead><tr><th>Symbol</th><th>Name</th><th>Price</th></tr></thead><tbody>`;
            portfolio.tickers.forEach((t, idx) => {
                const data = tickerData[t.symbol];
                const rowClass = needsPagination && idx >= tickersPerPage ? 'ticker-row-hidden' : '';
                html += `<tr class="${rowClass}" data-page="${Math.floor(idx / tickersPerPage)}"><td><span class="badge bg-secondary">${t.symbol.toUpperCase()}</span></td><td>${data.name}</td><td>$${data.price.toFixed(2)}</td></tr>`;
            });
            html += '</tbody></table>';
            
            // Add pagination if needed
            if (needsPagination) {
                const totalPages = Math.ceil(portfolio.tickers.length / tickersPerPage);
                html += `<div class="pagination-controls" data-table="${tableId}">`;
                html += `<button class="btn btn-sm btn-outline-secondary" onclick="changePage('${tableId}', -1)">Previous</button> `;
                html += `<span class="mx-2">Page <span id="${tableId}-page">1</span> of ${totalPages}</span> `;
                html += `<button class="btn btn-sm btn-outline-secondary" onclick="changePage('${tableId}', 1)">Next</button>`;
                html += '</div>';
            }
            
            // Portfolio Visualizer button
            html += `<div class="mt-3"><button class="btn btn-sm btn-primary" onclick="openPortfolioVisualizer('${symbols.join(',')}')">📊 View in Portfolio Visualizer</button></div>`;
        }
        
        html += '</div></div>';
    });
    
    container.innerHTML = html;
    
    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// Demo examples
const DEMO_EXAMPLES = [
    // Simple sentence
    "The cat sat on the mat eating a can of food while watching tv.",
    
    // Paragraph
    "My dad works at Ford. Yesterday he drove his Uber to the store to buy some Pepsi and groceries from Costco. On the way back he stopped at the bar to meet his friend Jack who works at Target.",
    
    // Article (2-3 paragraphs)
    "The tech industry saw major changes this year. Companies like Apple and Dell released new products while Oracle expanded their cloud services. Meanwhile analysts noted how British American Tobacco continued its dominance in Asian markets.\n\nIn the automotive sector Ford announced electric vehicle plans and General Motors followed suit. Uber and Doordash both reported strong quarterly earnings. The ride sharing wars continue with Grab making moves in Southeast Asia.\n\nRetail giants Costco and Target adapted to changing consumer habits. Lowes improved their home improvement offerings while Home Depot focused on professional contractors. The fast food industry saw consolidation with Jack in the Box and Sonic exploring merger possibilities."
];

function fillExample(index) {
    const textarea = document.getElementById('user-input');
    if (textarea && DEMO_EXAMPLES[index]) {
        textarea.value = DEMO_EXAMPLES[index];
        textarea.focus();
    }
}

// Pagination helper
const paginationState = {};

function changePage(tableId, direction) {
    if (!paginationState[tableId]) {
        paginationState[tableId] = { currentPage: 0 };
    }
    
    const table = document.getElementById(tableId);
    const rows = table.querySelectorAll('tbody tr');
    const tickersPerPage = 10;
    const totalPages = Math.ceil(rows.length / tickersPerPage);
    
    paginationState[tableId].currentPage += direction;
    
    // Wrap around
    if (paginationState[tableId].currentPage < 0) {
        paginationState[tableId].currentPage = totalPages - 1;
    } else if (paginationState[tableId].currentPage >= totalPages) {
        paginationState[tableId].currentPage = 0;
    }
    
    const currentPage = paginationState[tableId].currentPage;
    
    // Show/hide rows
    rows.forEach((row, idx) => {
        const page = Math.floor(idx / tickersPerPage);
        row.style.display = page === currentPage ? '' : 'none';
    });
    
    // Update page number
    document.getElementById(`${tableId}-page`).textContent = currentPage + 1;
}

function openPortfolioVisualizer(symbolsStr) {
    const symbols = symbolsStr.split(',');
    const alloc = (100 / symbols.length).toFixed(2);
    let url = 'https://www.portfoliovisualizer.com/backtest-portfolio?s=y&benchmark=-1&benchmarkSymbol=SPY&portfolioNames=true&portfolioName1=Portfolio';
    symbols.forEach((sym, i) => {
        url += `&symbol${i+1}=${sym}&allocation${i+1}_1=${alloc}`;
    });
    window.open(url, '_blank');
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    if (!tickerData) {
        alert('Loading ticker data...');
        const loaded = await loadTickerData();
        if (!loaded) {
            alert('Failed to load data. Please try again.');
            return;
        }
    }
    
    const text = document.getElementById('user-input').value;
    if (!text.trim()) {
        alert('Please enter some text.');
        return;
    }
    
    // Show loading indicator
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultCard = document.getElementById('result-card');
    const submitButton = e.target.querySelector('button[type="submit"]');
    const timerDisplay = document.getElementById('compute-timer');
    
    loadingIndicator.style.display = 'block';
    resultCard.style.display = 'none';
    submitButton.disabled = true;
    
    // Start timer
    let startTime = Date.now();
    let timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        timerDisplay.textContent = elapsed;
    }, 100); // Update every 100ms for smooth counting
    
    const words = parseWords(text);
    
    // Try to use Web Worker if available
    if (worker) {
        worker.postMessage({
            type: 'COMPUTE',
            data: { text, words }
        });
        
        // Store timer interval globally so worker result handler can clear it
        window.computeTimerInterval = timerInterval;
    } else {
        // Fallback to main thread with setTimeout
        setTimeout(() => {
            try {
                const portfolios = {};
                for (const key of Object.keys(STRATEGIES)) {
                    portfolios[key] = findBestPortfolio(text, words, key);
                }
                clearInterval(timerInterval);
                handleWorkerResult({ portfolios, text, words });
            } catch (error) {
                console.error('Error processing text:', error);
                alert('An error occurred while processing your text. Please try again.');
                clearInterval(timerInterval);
                loadingIndicator.style.display = 'none';
                submitButton.disabled = false;
            }
        }, 100);
    }
}

function handleWorkerResult(data) {
    const { portfolios, text, words } = data;
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultCard = document.getElementById('result-card');
    const submitButton = document.querySelector('#ticker-form button[type="submit"]');
    const timerDisplay = document.getElementById('compute-timer');
    
    // Clear timer
    if (window.computeTimerInterval) {
        clearInterval(window.computeTimerInterval);
        window.computeTimerInterval = null;
    }
    
    // Reset timer display for next run
    timerDisplay.textContent = '0';
    
    resultCard.style.display = 'block';
    renderPortfolios(text, words, portfolios);
    
    loadingIndicator.style.display = 'none';
    submitButton.disabled = false;
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('ticker-form').addEventListener('submit', handleFormSubmit);
    loadTickerData();
});
