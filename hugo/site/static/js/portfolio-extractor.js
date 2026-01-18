// Portfolio Extractor with Web Worker for non-blocking computation
let strategyDataCache = {}; // Cache for all strategy data
let tickerData = null;
let tickerTrie = null;
let worker = null;
let currentStrategy = 'DIVIDEND_DADDY';

// Get base URL from global variable or default to root
const BASE_URL = (window.SITE_BASE_URL || '/').replace(/\/$/, '');

const STRATEGIES = {
    DIVIDEND_DADDY: {
        name: '💰 Dividend Daddy',
        description: 'High yield + low volatility',
        help: 'Finds stocks with high dividend yields and low volatility (beta). Best for income-focused, conservative investors seeking steady returns.',
        dataFile: 'data/strategy_dividend_daddy.json',
        scoreKey: 'dividendDaddy'
    },
    MOON_SHOT: {
        name: '🚀 Moon Shot',
        description: 'High beta + oversold',
        help: 'Identifies high-growth potential stocks with high beta (volatility) and oversold conditions (low RSI). For aggressive growth seekers willing to take risks.',
        dataFile: 'data/strategy_moon_shot.json',
        scoreKey: 'moonShot'
    },
    FALLING_KNIFE: {
        name: '🔪 Falling Knife',
        description: 'Oversold + below MA',
        help: 'Contrarian strategy finding oversold stocks trading below their 200-day moving average. "Catching a falling knife" - high risk but potential for bounce-back gains.',
        dataFile: 'data/strategy_falling_knife.json',
        scoreKey: 'fallingKnife'
    },
    OVER_HYPED: {
        name: '🎈 Over-Hyped',
        description: 'Overbought',
        help: 'Finds overbought stocks with high RSI values, suggesting momentum exhaustion. Good for short sellers or mean-reversion traders expecting pullbacks.',
        dataFile: 'data/strategy_over_hyped.json',
        scoreKey: 'overHyped'
    },
    INSTITUTIONAL_WHALE: {
        name: '🐋 Institutional Whale',
        description: 'Large cap',
        help: 'Targets large-cap stocks likely held by institutional investors. "Follow the smart money" - more stable, liquid, and widely covered by analysts.',
        dataFile: 'data/strategy_institutional_whale.json',
        scoreKey: 'instWhale'
    }
};

// Initialize Web Worker
function initWorker() {
    if (!worker && typeof Worker !== 'undefined') {
        worker = new Worker(`${BASE_URL}/js/portfolio-worker.js`.replace(/([^:])\/\//g, '$1/'));

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

async function loadTickerData(strategy = 'DIVIDEND_DADDY') {
    try {
        // Return cached data if already loaded
        if (strategyDataCache[strategy]) {
            console.log(`Using cached data for ${strategy}`);
            return strategyDataCache[strategy];
        }

        currentStrategy = strategy;
        const strategyConfig = STRATEGIES[strategy];

        // Load strategy-specific pre-filtered data
        const response = await fetch(`${BASE_URL}/${strategyConfig.dataFile}`.replace(/([^:])\/\//g, '$1/'));
        const data = await response.json();

        const tickerData = {};
        const symbols = [];

        // Use pre-filtered tickers from strategy JSON
        data.tickers.forEach(t => {
            tickerData[t.symbol] = {
                symbol: t.symbol,
                name: t.name,
                exchange: t.exchange,
                price: t.price,
                volume: t.volume,
                marketCap: t.marketCap,
                dividendYield: t.dividendYield,
                beta: t.beta,
                rsi: t.rsi,
                ma200: t.ma200,
                // Use pre-calculated strategy score
                strategyScore: t.scores ? t.scores[strategyConfig.scoreKey] : 0
            };
            symbols.push(t.symbol);
        });

        const tickerTrie = buildTrie(symbols);
        console.log(`Loaded ${symbols.length} pre-filtered tickers for ${strategy}`);

        // Cache for future use
        strategyDataCache[strategy] = { tickerData, tickerTrie };

        return { tickerData, tickerTrie };
    } catch (error) {
        console.error('Failed to load strategy data:', error);
        // Fallback to old method if strategy files don't exist
        return await loadLegacyTickerData();
    }
}

// Load all strategies in parallel for faster overall performance
async function loadAllStrategyData() {
    const strategies = Object.keys(STRATEGIES);
    const loadPromises = strategies.map(strategy => loadTickerData(strategy));

    try {
        const results = await Promise.all(loadPromises);
        // Verify all results are valid
        const allValid = results.every(result => result && result.tickerData && result.tickerTrie);
        if (!allValid) {
            console.error('Some strategies failed to load properly');
            return false;
        }
        console.log('All strategy data loaded');
        return true;
    } catch (error) {
        console.error('Failed to load all strategy data:', error);
        // At least load one strategy
        await loadTickerData('DIVIDEND_DADDY');
        return false;
    }
}

// Fallback to old method if strategy files don't exist
async function loadLegacyTickerData() {
    try {
        const response = await fetch(`${BASE_URL}/data/filtered_tickers.json`.replace(/([^:])\/\//g, '$1/'));
        const data = await response.json();
        tickerData = {};
        const symbols = [];
        data.tickers.forEach(t => {
            if (t.price_data && t.price_data.price) {
                tickerData[t.symbol] = {
                    symbol: t.symbol, name: t.name, exchange: t.exchange,
                    price: t.price_data.price, volume: t.price_data.volume,
                    marketCap: t.price_data.market_cap, dividendYield: t.price_data.dividend_yield,
                    beta: t.price_data.beta, rsi: t.price_data.rsi_14, ma200: t.price_data.ma_200,
                    strategyScore: 0
                };
                symbols.push(t.symbol);
            }
        });
        tickerTrie = buildTrie(symbols);
        console.log(`Loaded ${symbols.length} tickers (legacy mode)`);

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

/*
"So the problem here is essentially: given a sequence of words (tokenized from user input text) and a dictionary of valid stock tickers (accessed via a trie for fast prefix matching), find the segmentation of the sequence into consecutive spans (1–3 words long) that forms valid tickers and maximizes the total score of the chosen tickers — where score comes from strategy-specific metrics like dividend yield, RSI, market cap, etc.
This is a classic dynamic programming optimization problem on a linear structure — very similar to the LeetCode 'Word Break' series or 'maximum score segmentation' variants, but instead of boolean feasibility or counting ways, we're maximizing a cumulative score, and we allow skipping words (gaps/non-ticker text).
Naive recursive backtracking would try every possible way to take or skip each position, branching on spans of 1–3 words, leading to exponential time — roughly O(3^n) in the worst case for n words, which is why the original version froze the browser on longer inputs like 40–50 tokens.
To fix that, we recognize optimal substructure and overlapping subproblems:

Optimal substructure: The best score starting from position i is the max over (skip to i+1, or take a valid ticker span ending at j and add its score + best from j+1).
Overlapping: Many paths recompute the same suffix starting from the same i.

So we apply dynamic programming to compute each subproblem once.
We chose bottom-up DP (tabulation) over top-down memoization for a few reasons:

Avoids recursion stack risk — on very long inputs (hundreds of words), deep recursion could blow the call stack in JavaScript.
Slightly cleaner iterative control flow, easier to reason about space/time in interviews.
No function call overhead, which matters in tight client-side loops.
The dependencies are strictly forward (we fill from the end backwards), so bottom-up is natural and guarantees we compute in the right order.

Data structures we used and why:

dp array of size n+1: dp[i] holds the best {score, tickers list} achievable from word index i to the end.
→ Space O(n), but since we store the full list, worst-case O(n²) if we copy arrays naively each time (we mitigate by spreading [...prev] only when improving).
possibleTickers precompute: array where possibleTickers[start] = list of {ticker, span} that are valid from that position.
→ This is O(n × maxSpan) = O(n) pre-work (with trie lookups assumed fast), but it moves expensive string/trie operations outside the main DP loop — huge win for constant factors.
scoreCache Map: memoizes per-symbol scores since the same ticker can appear many times and scoring involves object property access or calculations.

Time & Space Complexity:

Precompute: O(n × 3) × O(1) trie lookup ≈ O(n)
DP fill: for each of n positions, check O(1) precomputed options + skip → O(n)
Overall: O(n) time — linear in the number of words, which is excellent for client-side (even 200–300 word inputs finish in <10ms).
Space: O(n) for dp + precompute (ignoring the output list size).

Tradeoffs we made:

We allow skipping words → maximizes score even if not every token becomes a ticker (realistic for noisy user text like "My dad works at Ford" → might pick F but skip the rest).
If we wanted full coverage (no skips), we'd remove the skip option and only set dp[i] if a ticker was taken.
We cap spans at 3 → assumes most stock tickers are short; if we allowed arbitrary length we'd need to adjust precompute and lose some efficiency.
Reconstructing the ticker list by spreading arrays → convenient but O(n²) worst-case space/time in pathological cases (deep chains of improvements). For production we could use a prev index array + reconstruct at the end in O(n) — a good follow-up optimization.

When would we NOT use this exact approach?

If we only needed feasibility (can segment at all?) or just one valid segmentation → classic Word Break boolean DP is simpler/cheaper (no need for score or list reconstruction).
If the goal was all possible segmentations → we'd need backtracking or a different structure (exponential output size anyway).
If n was tiny (<10) and we wanted simplicity → plain recursion might be fine.
If scores were uniform (just maximize count) → could simplify to greedy longest-match, but here scores vary so DP is necessary.
Very long inputs + memory tight → could stream/process in chunks or use space-optimized DP (only keep last few cells if we don't need the full path).
If trie lookups were extremely expensive → might precompute all possible valid spans in a different way.

Overall, this is a great example of turning an exponential search into efficient linear DP by precomputing candidates, memoizing subproblem results in a table, and choosing bottom-up for predictability in a browser environment."
 */
function findBestPortfolio(text, words, strategy, strategyTickerData, strategyTickerTrie) {
    // Pre-compute scores (unchanged)
    const scoreCache = new Map();
    const scorer = (symbol) => {
        if (scoreCache.has(symbol)) return scoreCache.get(symbol);
        const ticker = strategyTickerData[symbol];
        let score;
        if (ticker.strategyScore && ticker.strategyScore > 0) {
            score = ticker.strategyScore;
        } else {
            switch(strategy) {
                case 'DIVIDEND_DADDY': score = ticker.dividendYield || 0; break;
                case 'MOON_SHOT': score = (ticker.beta || 0) * (100 - (ticker.rsi || 50)); break;
                case 'FALLING_KNIFE': score = (100 - (ticker.rsi || 50)) * (ticker.price < ticker.ma200 ? 2 : 1); break;
                case 'OVER_HYPED': score = ticker.rsi || 0; break;
                case 'INSTITUTIONAL_WHALE': score = ticker.marketCap || 0; break;
                default: score = 1;
            }
        }
        scoreCache.set(symbol, score);
        return score;
    };

    const n = words.length;
    if (n === 0) return { tickers: [], score: 0 };

    // Precompute possible tickers for each start position (array of arrays)
    const possibleTickers = Array.from({ length: n }, () => []);
    for (let start = 0; start < n; start++) {
        for (let span = 1; span <= Math.min(3, n - start); span++) {
            const end = start + span - 1;
            const ticker = findTickerInSpan(text, words, start, end, strategyTickerTrie);
            if (ticker) {
                possibleTickers[start].push({ ticker, span });
            }
        }
    }

    // Bottom-up DP: dp[i] = { score, tickers } for best from i to end
    const dp = Array(n + 1).fill(null);
    dp[n] = { score: 0, tickers: [] };

    for (let i = n - 1; i >= 0; i--) {
        // Skip this position
        let best = dp[i + 1] ? { score: dp[i + 1].score, tickers: [...dp[i + 1].tickers] } : { score: 0, tickers: [] };

        // Try each possible ticker starting at i
        for (const { ticker, span } of possibleTickers[i]) {
            const next = i + span;
            if (dp[next]) {
                const candidateScore = scorer(ticker.symbol) + dp[next].score;
                if (candidateScore > best.score) {
                    best = { score: candidateScore, tickers: [ticker, ...dp[next].tickers] };
                }
            }
        }
        dp[i] = best;
    }

    return dp[0];
}

function findTickerInSpan(text, words, startWordIdx, endWordIdx, trie) {
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

    return search(0, trie, []);
}

function renderHighlighted(text, words, tickers, tickerData) {
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
                html += renderTickerGroup(currentGroupChars, currentTicker, tickerData);
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
        html += renderTickerGroup(currentGroupChars, currentTicker, tickerData);
    }

    return html;
}

function renderTickerGroup(charArray, ticker, tickerData) {
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

    // Get ticker name from metadata
    const tickerName = tickerData && tickerData[ticker] ? tickerData[ticker].name : ticker;
    const tooltipText = `${ticker} - ${tickerName}`;

    return `<span class="ticker-group" title="${escapeHtml(tooltipText)}">${styledContent}</span>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderPortfolios(text, words, portfolios) {
    const container = document.getElementById('portfolio-strategies');

    if (Object.values(portfolios).every(p => p.tickers.length === 0)) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <h5 class="alert-heading">No Tickers Found in Any Strategy</h5>
                <p>We didn't find any stock tickers in your text that match any of our 5 investment strategies.</p>
                <hr>
                <div class="mb-3">
                    <h6>Your Input Text:</h6>
                    <div class="bg-light p-3 border rounded text-muted" style="font-family: monospace; white-space: pre-wrap;">${escapeHtml(text)}</div>
                </div>
                <p class="mb-0"><strong>Why?</strong> Each strategy only includes tickers that match specific criteria (e.g., high dividends, high beta, etc.). 
                Common tickers like NVDA or TSLA might not appear in dividend-focused strategies. 
                Try browsing the <a href="/strategy-dividend-daddy/">strategy pages</a> to see which tickers are included.</p>
            </div>`;
        return;
    }

    let html = '';
    Object.entries(portfolios).forEach(([strategyKey, portfolio]) => {
        const strategy = STRATEGIES[strategyKey];
        const strategyData = strategyDataCache[strategyKey];
        if (!strategyData) return;

        const { tickerData } = strategyData;

        html += `
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">
                        <a href="/strategy-${strategyKey.toLowerCase().replace(/_/g, '-')}/" class="text-white text-decoration-none" target="_blank">
                            ${strategy.name}
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-box-arrow-up-right" viewBox="0 0 16 16" style="vertical-align: baseline;">
                                <path fill-rule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5"/>
                                <path fill-rule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0z"/>
                            </svg>
                        </a>
                        <span class="strategy-help" title="${strategy.help}">ℹ️</span>
                    </h6>
                    <small>${strategy.description}</small>
                </div>
                <div class="card-body">
        `;

        if (portfolio.tickers.length === 0) {
            // Show the input text in muted color with helpful message
            const strategyUrl = `/strategy-${strategyKey.toLowerCase().replace(/_/g, '-')}/`;
            html += '<div class="alert alert-info">';
            html += '<h6 class="alert-heading">No Tickers Found</h6>';
            html += '<p>We didn\'t find any stock tickers in your text that match this strategy\'s criteria.</p>';
            html += '</div>';

            html += '<div class="mb-3">';
            html += '<h6>Your Input Text:</h6>';
            html += '<div class="bg-light p-3 border rounded text-muted" style="font-family: monospace; white-space: pre-wrap;">';
            html += escapeHtml(text);
            html += '</div>';
            html += '</div>';

            html += '<p class="mb-0"><small>';
            html += `<strong>Why?</strong> This strategy only includes tickers that match specific criteria. `;
            html += `<a href="${strategyUrl}" target="_blank">View all ${Object.keys(strategyData.tickerData).length} tickers in this strategy →</a>`;
            html += '</small></p>';
        } else {
            // 1. Show highlighted text FIRST
            html += '<div class="mb-4">';
            html += '<h6>Highlighted Input Text:</h6>';
            html += '<div class="bg-light p-3 border rounded" style="font-family: monospace; white-space: pre-wrap;">';
            html += renderHighlighted(text, words, portfolio.tickers, tickerData);
            html += '</div>';
            html += '<div class="mt-2"><small class="text-muted">';
            html += '<span class="token-ticker token-ticker-single">Green</span> = Ticker (hover to see symbol and name)';
            html += '</small></div>';
            html += '</div>';

            // 2. Show tickers found (deduplicate by symbol)
            const uniqueSymbols = [...new Set(portfolio.tickers.map(t => t.symbol.toUpperCase()))];
            html += `<p><strong>Tickers found:</strong> ${uniqueSymbols.join(', ')}</p>`;

            // 3. Show ticker details table (with pagination for 10+)
            // Deduplicate tickers by symbol
            const uniqueTickers = [];
            const seenSymbols = new Set();
            portfolio.tickers.forEach(t => {
                if (!seenSymbols.has(t.symbol)) {
                    seenSymbols.add(t.symbol);
                    uniqueTickers.push(t);
                }
            });
            
            const tickersPerPage = 10;
            const needsPagination = uniqueTickers.length > tickersPerPage;
            const tableId = `table-${strategyKey}`;

            html += `<table class="table table-sm table-striped mb-3" id="${tableId}"><thead><tr><th>Symbol</th><th>Name</th><th>Price</th></tr></thead><tbody>`;
            uniqueTickers.forEach((t, idx) => {
                const data = tickerData[t.symbol];
                const page = Math.floor(idx / tickersPerPage);
                const shouldHide = needsPagination && page > 0;
                const rowStyle = shouldHide ? ' style="display: none;"' : '';
                html += `<tr data-page="${page}"${rowStyle}><td><a href="https://finance.yahoo.com/quote/${t.symbol.toUpperCase()}" target="_blank" rel="noopener" title="${t.symbol.toUpperCase()} - ${data.name}"><span class="badge bg-secondary">${t.symbol.toUpperCase()}</span></a></td><td>${data.name}</td><td>$${data.price.toFixed(2)}</td></tr>`;
            });
            html += '</tbody></table>';

            // Add pagination if needed
            if (needsPagination) {
                const totalPages = Math.ceil(uniqueTickers.length / tickersPerPage);
                html += `<div class="pagination-controls" data-table="${tableId}">`;
                html += `<button class="btn btn-sm btn-outline-secondary" onclick="changePage('${tableId}', -1)">Previous</button> `;
                html += `<span class="mx-2">Page <span id="${tableId}-page">1</span> of ${totalPages}</span> `;
                html += `<button class="btn btn-sm btn-outline-secondary" onclick="changePage('${tableId}', 1)">Next</button>`;
                html += '</div>';
            }

            // Portfolio Visualizer button
            html += `<div class="mt-3"><button class="btn btn-sm btn-primary" onclick="openPortfolioVisualizer('${uniqueSymbols.join(',')}')">📊 View in Portfolio Visualizer</button></div>`;
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

    const text = document.getElementById('user-input').value;
    if (!text.trim()) {
        alert('Please enter some text.');
        return;
    }

    // Show loading indicator immediately
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultCard = document.getElementById('result-card');
    const submitButton = e.target.querySelector('button[type="submit"]');
    const timerDisplay = document.getElementById('compute-timer');

    loadingIndicator.style.display = 'block';
    resultCard.style.display = 'none';
    submitButton.disabled = true;

    // Ensure all strategy data is loaded
    if (Object.keys(strategyDataCache).length === 0) {
        console.log('Loading strategy data for first time...');
        try {
            const loaded = await loadAllStrategyData();
            console.log('loadAllStrategyData returned:', loaded, 'type:', typeof loaded);
            if (!loaded) {
                loadingIndicator.style.display = 'none';
                submitButton.disabled = false;
                console.error('Failed to load strategy data');
                // Show error in the result card instead of alert
                resultCard.style.display = 'block';
                document.getElementById('portfolio-strategies').innerHTML =
                    '<div class="alert alert-danger">Failed to load ticker data. Please refresh the page and try again.</div>';
                return;
            }
            console.log('Data loaded successfully, continuing...');
        } catch (error) {
            console.error('Error loading data:', error);
            loadingIndicator.style.display = 'none';
            submitButton.disabled = false;
            // Show error in the result card instead of alert
            resultCard.style.display = 'block';
            document.getElementById('portfolio-strategies').innerHTML =
                `<div class="alert alert-danger">Error loading data: ${error.message}<br>Please check console for details.</div>`;
            return;
        }
    }

    // Start timer AFTER data is loaded
    let startTime = Date.now();
    window.computeTimerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        if (timerDisplay) {
            timerDisplay.textContent = elapsed;
        }
    }, 100); // Update every 100ms for smooth counting

    const words = parseWords(text);

    // Run all strategies with their specific cached data
    setTimeout(() => {
        try {
            const portfolios = {};
            for (const key of Object.keys(STRATEGIES)) {
                const cached = strategyDataCache[key];
                const { tickerData: strategyTickerData, tickerTrie: strategyTickerTrie } = cached || {};
                if (strategyTickerData && strategyTickerTrie) {
                    portfolios[key] = findBestPortfolio(text, words, key, strategyTickerData, strategyTickerTrie);
                }
            }
            clearInterval(window.computeTimerInterval);
            handleWorkerResult({ portfolios, text, words });
        } catch (error) {
            console.error('Error processing text:', error);
            console.error('Error stack:', error.stack);
            clearInterval(window.computeTimerInterval);
            loadingIndicator.style.display = 'none';
            submitButton.disabled = false;
            // Show error in result card instead of alert
            resultCard.style.display = 'block';
            document.getElementById('portfolio-strategies').innerHTML =
                `<div class="alert alert-danger"><strong>Error processing text:</strong> ${error.message}</div>`;
        }
    }, 10); // Small delay to allow UI to update
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
    // Don't load data immediately - let it load on first submit for faster page load
    console.log('Ticker extraction tool ready. Data will load on first submit.');
});
