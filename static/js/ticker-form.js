document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('ticker-form');
    const userInput = document.getElementById('user-input');
    const resultSection = document.getElementById('result-section');
    const userOutput = document.getElementById('user-output');

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const text = userInput.value;
        // For now, just redisplay the text. Highlight uppercase words (simulate tickers)
        const highlighted = text.replace(/\b([A-Z]{2,})\b/g, '<span class="ticker-highlight">$1</span>');
        userOutput.innerHTML = highlighted;
        resultSection.style.display = 'block';
    });
});
