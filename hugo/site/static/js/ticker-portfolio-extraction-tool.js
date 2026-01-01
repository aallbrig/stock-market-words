function isValidStockSymbol(symbol) {
    // For now, all symbols are valid
    return true;
}

function setStockTickersFromUrl(form) {
    // Get current URL
    const urlParams = new URLSearchParams(window.location.search);
    const tickers = urlParams.getAll('tickers').filter(isValidStockSymbol);
    // Remove existing ticker inputs
    const oldInputs = form.querySelectorAll('input[name="tickers[]"]');
    oldInputs.forEach(input => input.remove());
    // Add new ticker inputs
    tickers.forEach(ticker => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'tickers[]';
        input.value = ticker;
        form.appendChild(input);
    });
}

function getTickersFromForm(form) {
    const tickerInputs = form.querySelectorAll('input[name="tickers[]"]');
    return Array.from(tickerInputs).map(input => input.value).filter(Boolean);
}

function calculateEqualAllocation(tickers) {
    return (100 / tickers.length).toFixed(2);
}

function buildPortfolioVisualizerUrl(tickers) {
    const allocation = calculateEqualAllocation(tickers);
    let baseUrl = 'https://www.portfoliovisualizer.com/backtest-portfolio?s=y&benchmark=-1&benchmarkSymbol=SPY&portfolioNames=true&portfolioName1=Test+Portfolio';
    return tickers.reduce(function(url, ticker, i) {
        return url + `&symbol${i+1}=${ticker}&allocation${i+1}_1=${allocation}`;
    }, baseUrl);
}

function handleFormSubmit(e) {
    e.preventDefault();
    // Hardcoded tickers for now
    const tickers = ['NVDA', 'AAPL', 'SPOT', 'TSLA'];
    // Remove existing ticker inputs
    const form = e.target;
    const oldInputs = form.querySelectorAll('input[name="tickers[]"]');
    oldInputs.forEach(input => input.remove());
    // Add new ticker inputs
    tickers.forEach(ticker => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'tickers[]';
        input.value = ticker;
        form.appendChild(input);
    });
    // Display user input in result card
    const userInput = document.getElementById('user-input').value;
    const userOutput = document.getElementById('user-output');
    userOutput.textContent = userInput;
    showPortfolioLinkIfTickersExist(form);
}

function showPortfolioLinkIfTickersExist(form) {
    const tickers = getTickersFromForm(form);
    if (tickers.length > 0) {
        const url = buildPortfolioVisualizerUrl(tickers);
        const resultCard = document.getElementById('result-card');
        const portfolioLinkSection = document.getElementById('portfolio-link-section');
        const portfolioLink = document.getElementById('portfolio-link');
        const portfolioLinkMessage = document.getElementById('portfolio-link-message');
        resultCard.style.display = 'block';
        portfolioLinkSection.style.display = 'block';
        portfolioLink.href = url;
        portfolioLinkMessage.textContent = 'Portfolio Visualizer is not embeddable. Click below to open your portfolio analysis in a new tab:';
    }
}

function onDOMContentLoaded() {
    const form = document.getElementById('ticker-form');
    setStockTickersFromUrl(form);
    form.addEventListener('submit', handleFormSubmit);
    showPortfolioLinkIfTickersExist(form);
}

document.addEventListener('DOMContentLoaded', onDOMContentLoaded);
