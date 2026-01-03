// Load ticker data and build trie
let tickerEngine = null;
let tickerTrie = null;
let tickerMetadata = null;

async function loadTickerData() {
    try {
        // Load ticker symbols
        const response = await fetch('/api/all-exchanges.txt');
        const text = await response.text();
        const symbols = text.split('\n').filter(s => s.trim());
        
        // Build trie
        tickerTrie = buildTrie(symbols);
        
        // Mock metadata (in production, load from API)
        tickerMetadata = {};
        symbols.forEach(symbol => {
            tickerMetadata[symbol] = {
                name: symbol,
                yield: Math.random() * 0.1,
                beta: Math.random() * 3,
                momentum: (Math.random() - 0.5) * 50,
                rsi: Math.random() * 100,
                marketCap: Math.random() * 3000000000000
            };
        });
        
        tickerEngine = new TickerEngine(tickerTrie, tickerMetadata);
        return true;
    } catch (error) {
        console.error('Failed to load ticker data:', error);
        return false;
    }
}

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

function getSelectedStrategy() {
    const strategySelect = document.getElementById('strategy-select');
    return strategySelect ? strategySelect.value : 'DIVIDEND_DADDY';
}

function renderTokens(tokens) {
    return tokens.map(token => {
        const className = `token-${token.type.toLowerCase().replace('_', '-')}`;
        return `<span class="${className}">${escapeHtml(token.char)}</span>`;
    }).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderPortfolioOptions(portfolios) {
    const container = document.getElementById('portfolio-options');
    container.innerHTML = '';
    
    if (portfolios.length === 0) {
        container.innerHTML = '<p class="text-muted">No tickers found in your text.</p>';
        return;
    }
    
    portfolios.forEach((portfolio, index) => {
        const option = document.createElement('div');
        option.className = 'portfolio-option';
        if (index === 0) option.classList.add('selected');
        option.dataset.index = index;
        
        const tickersList = portfolio.tickers.join(', ');
        const metadataHtml = portfolio.tickers.map(ticker => {
            const meta = portfolio.metadata[ticker];
            if (!meta) return '';
            return `
                <div class="ticker-meta">
                    <strong>${ticker}</strong>: 
                    Yield: ${(meta.yield * 100).toFixed(2)}%, 
                    Beta: ${meta.beta.toFixed(2)}, 
                    RSI: ${meta.rsi.toFixed(0)}
                </div>
            `;
        }).join('');
        
        option.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0">Portfolio ${index + 1}</h6>
                <span class="portfolio-score">Score: ${portfolio.score.toFixed(4)}</span>
            </div>
            <div class="mb-2">
                <strong>Tickers:</strong> ${tickersList}
            </div>
            ${metadataHtml}
            <div class="mt-2">
                <button class="btn btn-sm btn-primary select-portfolio" data-index="${index}">
                    Select This Portfolio
                </button>
            </div>
        `;
        
        container.appendChild(option);
    });
    
    // Add click handlers
    document.querySelectorAll('.select-portfolio').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            selectPortfolio(portfolios, index);
        });
    });
}

function selectPortfolio(portfolios, index) {
    const portfolio = portfolios[index];
    
    // Update UI
    document.querySelectorAll('.portfolio-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    document.querySelector(`.portfolio-option[data-index="${index}"]`).classList.add('selected');
    
    // Update output with token highlighting
    const userOutput = document.getElementById('user-output');
    userOutput.innerHTML = renderTokens(portfolio.tokens);
    
    // Update portfolio link
    updatePortfolioLink(portfolio.tickers);
}

function updatePortfolioLink(tickers) {
    if (tickers.length === 0) return;
    
    const allocation = (100 / tickers.length).toFixed(2);
    let baseUrl = 'https://www.portfoliovisualizer.com/backtest-portfolio?s=y&benchmark=-1&benchmarkSymbol=SPY&portfolioNames=true&portfolioName1=Test+Portfolio';
    
    const url = tickers.reduce((url, ticker, i) => {
        return url + `&symbol${i+1}=${ticker}&allocation${i+1}_1=${allocation}`;
    }, baseUrl);
    
    const portfolioLinkSection = document.getElementById('portfolio-link-section');
    const portfolioLink = document.getElementById('portfolio-link');
    const portfolioLinkMessage = document.getElementById('portfolio-link-message');
    
    portfolioLinkSection.style.display = 'block';
    portfolioLink.href = url;
    portfolioLinkMessage.textContent = 'Portfolio Visualizer is not embeddable. Click below to open your portfolio analysis in a new tab:';
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    if (!tickerEngine) {
        alert('Loading ticker data... please wait.');
        const loaded = await loadTickerData();
        if (!loaded) {
            alert('Failed to load ticker data. Please try again.');
            return;
        }
    }
    
    const userInput = document.getElementById('user-input').value;
    if (!userInput.trim()) {
        alert('Please enter some text.');
        return;
    }
    
    const strategy = getSelectedStrategy();
    const portfolios = tickerEngine.extractPortfolios(userInput, strategy);
    
    // Show results
    document.getElementById('result-card').style.display = 'block';
    
    // Render portfolio options
    renderPortfolioOptions(portfolios);
    
    // Auto-select first portfolio
    if (portfolios.length > 0) {
        selectPortfolio(portfolios, 0);
    }
}

function onDOMContentLoaded() {
    const form = document.getElementById('ticker-form');
    form.addEventListener('submit', handleFormSubmit);
    
    // Pre-load ticker data
    loadTickerData();
}

document.addEventListener('DOMContentLoaded', onDOMContentLoaded);
