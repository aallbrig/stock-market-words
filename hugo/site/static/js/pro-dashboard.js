/**
 * pro-dashboard.js — Pro dashboard data fetching and rendering
 *
 * Requires pro-auth.js to be loaded first.
 * Fetches portfolio and analysis data, renders the dashboard UI.
 */

(function () {
  'use strict';

  const SITE_BASE = window.SITE_BASE_URL || 'https://stockmarketwords.com';
  const API_BASE = window.SMW_PRO_API_BASE || '';

  // Cache of valid tickers for the add-ticker input
  let tickerCache = null;

  function filingLink(ticker) {
    if (ticker.endsWith('.SI')) {
      return 'https://www.sgx.com/securities/equities/' + encodeURIComponent(ticker.replace('.SI', ''));
    }
    return 'https://finance.yahoo.com/quote/' + encodeURIComponent(ticker) + '/financials/';
  }

  function pct(val) {
    if (val == null) return '—';
    return (val >= 0 ? '+' : '') + (val * 100).toFixed(1) + '%';
  }

  function money(val) {
    if (val == null || val === 0) return '—';
    return '$' + val.toFixed(2);
  }

  function renderStatCards(portfolio, analysis) {
    const tickers = analysis && analysis.tickers ? analysis.tickers : [];
    const empty = tickers.length === 0;

    function setCard(id, val) {
      const el = document.getElementById(id);
      if (el) el.textContent = empty ? '—' : val;
      const sub = document.getElementById(id + '-sub');
      if (sub) sub.textContent = empty ? 'Add tickers to see stats' : '';
    }

    if (tickers.length > 0) {
      const avgYield = tickers.reduce(function (s, t) { return s + (t.dividend_yield || 0); }, 0) / tickers.length;
      const avgYTD = tickers.reduce(function (s, t) { return s + (t.ytd_return || 0); }, 0) / tickers.length;
      const drag = tickers.reduce(function (a, b) { return (a.ytd_return || 0) < (b.ytd_return || 0) ? a : b; });

      setCard('stat-yield', pct(avgYield));
      setCard('stat-ytd', pct(avgYTD));

      const sp500 = analysis.benchmarks && analysis.benchmarks.find(function (b) { return b.ticker === 'SPY'; });
      setCard('stat-sp500', sp500 ? 'S&P: ' + pct(sp500.ytd_return) : '—');
      setCard('stat-drag', drag.ticker + ' ' + pct(drag.ytd_return));
    } else {
      ['stat-yield', 'stat-ytd', 'stat-sp500', 'stat-drag'].forEach(setCard);
    }
  }

  function renderPortfolioTable(portfolio, analysis) {
    const tbody = document.getElementById('portfolio-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const tickers = (portfolio && portfolio.tickers) ? portfolio.tickers : [];
    const analysisMap = {};
    if (analysis && analysis.tickers) {
      analysis.tickers.forEach(function (t) { analysisMap[t.ticker] = t; });
    }

    if (tickers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No tickers yet. Add one above.</td></tr>';
      return;
    }

    tickers.forEach(function (ticker) {
      const a = analysisMap[ticker] || {};
      const tr = document.createElement('tr');
      tr.innerHTML = [
        '<td><a href="' + SITE_BASE + '/stocks/' + encodeURIComponent(ticker) + '/" target="_blank">' + ticker + '</a></td>',
        '<td><a href="' + filingLink(ticker) + '" target="_blank" rel="noopener">🔗</a></td>',
        '<td>' + money(a.last_price) + '</td>',
        '<td>' + pct(a.dividend_yield) + '</td>',
        '<td>' + money(a.last_price && a.dividend_yield ? a.last_price * a.dividend_yield : null) + '</td>',
        '<td>' + pct(a.ytd_return) + ' <button class="btn btn-sm btn-outline-danger ms-1 remove-ticker" data-ticker="' + ticker + '">✕</button></td>'
      ].join('');
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.remove-ticker').forEach(function (btn) {
      btn.addEventListener('click', function () {
        removeTicker(btn.getAttribute('data-ticker'), btn.closest('tr'));
      });
    });
  }

  function renderWatchlist(portfolio, analysis) {
    const tbody = document.getElementById('watchlist-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const tickers = (portfolio && portfolio.tickers) ? portfolio.tickers : [];
    if (tickers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Your watchlist is empty. Visit a <a href="/tickers/">stock page</a> and click \'Add to Watch List\'.</td></tr>';
      return;
    }

    const analysisMap = {};
    if (analysis && analysis.tickers) {
      analysis.tickers.forEach(function (t) { analysisMap[t.ticker] = t; });
    }

    tickers.forEach(function (ticker) {
      const a = analysisMap[ticker] || {};
      const tr = document.createElement('tr');
      tr.innerHTML = [
        '<td>' + ticker + '</td>',
        '<td>' + (a.name || '') + '</td>',
        '<td>',
        '<a href="' + SITE_BASE + '/stocks/' + encodeURIComponent(ticker) + '/" target="_blank" class="btn btn-sm btn-outline-primary me-1">View</a>',
        '<button class="btn btn-sm btn-outline-danger remove-ticker" data-ticker="' + ticker + '">✕</button>',
        '</td>'
      ].join('');
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.remove-ticker').forEach(function (btn) {
      btn.addEventListener('click', function () {
        removeTicker(btn.getAttribute('data-ticker'), btn.closest('tr'));
      });
    });
  }

  function renderBenchmarks(analysis) {
    const el = document.getElementById('benchmark-rows');
    if (!el) return;
    el.innerHTML = '';
    if (!analysis || !analysis.benchmarks || analysis.benchmarks.length === 0) return;

    const avgYTD = analysis.tickers && analysis.tickers.length > 0
      ? analysis.tickers.reduce(function (s, t) { return s + (t.ytd_return || 0); }, 0) / analysis.tickers.length
      : null;

    analysis.benchmarks.forEach(function (b) {
      const beats = avgYTD != null && b.ytd_return > avgYTD;
      const tr = document.createElement('tr');
      tr.innerHTML = '<td><strong>' + b.ticker + '</strong></td><td>' + pct(b.ytd_return) + ' ' + (beats ? '↑' : '↓') + '</td>';
      el.appendChild(tr);
    });
  }

  function removeTicker(ticker, rowEl) {
    if (rowEl) rowEl.style.opacity = '0.5';
    ProAuth.authFetch(API_BASE + '/pro/portfolio', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickers: [], benchmarks: [] })
    }).then(function () {
      if (rowEl) rowEl.remove();
    });
  }

  function initAddTicker() {
    const input = document.getElementById('add-ticker-input');
    const btn = document.getElementById('add-ticker-btn');
    const errorEl = document.getElementById('add-ticker-error');
    if (!input || !btn) return;

    input.addEventListener('focus', function () {
      if (tickerCache) return;
      ProAuth.authFetch(API_BASE + '/pro/tickers')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          tickerCache = data.tickers || [];
          const dl = document.getElementById('ticker-datalist');
          if (dl) {
            tickerCache.forEach(function (t) {
              const opt = document.createElement('option');
              opt.value = t;
              dl.appendChild(opt);
            });
          }
        });
    });

    function addTicker() {
      const ticker = input.value.trim().toUpperCase();
      if (!ticker) return;
      if (errorEl) errorEl.textContent = '';

      ProAuth.authFetch(API_BASE + '/pro/portfolio', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: [ticker], benchmarks: [] })
      }).then(function (res) {
        if (res.status === 400) {
          if (errorEl) errorEl.textContent = 'Portfolio full (max 50). Remove a ticker first.';
          return;
        }
        input.value = '';
        window.location.reload();
      });
    }

    btn.addEventListener('click', addTicker);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); addTicker(); }
    });
  }

  function showDataFreshness(analysis) {
    const el = document.getElementById('data-freshness');
    if (!el || !analysis || !analysis.data_as_of) return;
    const d = new Date(analysis.data_as_of);
    const isStale = (Date.now() - d.getTime()) > 24 * 60 * 60 * 1000;
    el.className = 'badge ' + (isStale ? 'bg-warning text-dark' : 'bg-success');
    el.textContent = '📅 Data as of ' + d.toLocaleString('en-SG', { timeZone: 'Asia/Singapore' }) + ' SGT'
      + (isStale ? ' — market data may be outdated' : '');
    el.style.display = '';
  }

  function showError(msg) {
    const el = document.getElementById('dashboard-error');
    if (el) { el.textContent = msg; el.style.display = ''; }
    const spinner = document.getElementById('dashboard-spinner');
    if (spinner) spinner.style.display = 'none';
  }

  function initDashboard() {
    try {
      ProAuth.requireLogin();
    } catch (_) {
      return;
    }

    const emailEl = document.getElementById('pro-email');
    if (emailEl) emailEl.textContent = ProAuth.getEmail() || '';

    const spinner = document.getElementById('dashboard-spinner');

    Promise.all([
      ProAuth.authFetch(API_BASE + '/pro/portfolio'),
      ProAuth.authFetch(API_BASE + '/pro/portfolio/analysis')
    ])
      .then(function (responses) {
        return Promise.all([responses[0].json(), responses[1].json()]);
      })
      .then(function (results) {
        const portfolio = results[0];
        const analysis = results[1];
        if (spinner) spinner.style.display = 'none';
        renderStatCards(portfolio, analysis);
        renderPortfolioTable(portfolio, analysis);
        renderWatchlist(portfolio, analysis);
        renderBenchmarks(analysis);
        showDataFreshness(analysis);
      })
      .catch(function () {
        showError('Unable to load dashboard. Check your connection and try again.');
      });

    initAddTicker();
  }

  window.ProDashboard = { init: initDashboard };
})();
