/**
 * pro-watchlist.js — "Add to Watch List" button on ticker pages
 *
 * Behaviour depends on auth state:
 *   - Logged-in Pro subscriber → calls POST /pro/portfolio to add ticker
 *   - Non-subscriber → opens a modal with subscribe CTA
 *
 * Requires pro-auth.js to be loaded first.
 */

(function () {
  'use strict';

  function initWatchlistButton(ticker) {
    const btn = document.getElementById('watchlist-btn');
    if (!btn) return;

    btn.setAttribute('data-ticker', ticker);

    if (typeof ProAuth !== 'undefined' && ProAuth.isLoggedIn()) {
      btn.textContent = '+ Add to Watch List';
      btn.addEventListener('click', function () {
        addToWatchlist(ticker, btn);
      });
    } else {
      btn.textContent = 'Add to Watch List 🔒';
      btn.addEventListener('click', function () {
        openSubscribeModal(ticker);
      });
    }
  }

  function addToWatchlist(ticker, btn) {
    btn.disabled = true;
    btn.textContent = 'Adding…';

    const apiBase = window.SMW_PRO_API_BASE || '';
    ProAuth.authFetch(apiBase + '/pro/portfolio', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickers: [ticker], benchmarks: [] })
    }).then(function (res) {
      if (res.status === 400) {
        btn.disabled = false;
        btn.textContent = '+ Add to Watch List';
        showInlineError('Portfolio full (max 50). Remove a ticker first.');
        return;
      }
      btn.textContent = '✓ Added';
    }).catch(function () {
      btn.disabled = false;
      btn.textContent = '+ Add to Watch List';
      showInlineError('Unable to add ticker. Please try again.');
    });
  }

  function showInlineError(msg) {
    var el = document.getElementById('watchlist-error');
    if (el) { el.textContent = msg; el.style.display = ''; }
  }

  function openSubscribeModal(ticker) {
    var modal = document.getElementById('pro-subscribe-modal');
    if (!modal) return;

    var tickerEl = modal.querySelector('[data-modal-ticker]');
    if (tickerEl) tickerEl.textContent = ticker;

    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');

    var closeBtn = modal.querySelector('[data-modal-close]');
    if (closeBtn) {
      closeBtn.onclick = function () { closeModal(modal); };
    }

    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeModal(modal);
    });

    var emailForm = modal.querySelector('[data-modal-email-form]');
    if (emailForm) {
      emailForm.addEventListener('submit', function (e) {
        e.preventDefault();
        handleModalEmailSubmit(modal);
      });
    }
  }

  function closeModal(modal) {
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
  }

  function handleModalEmailSubmit(modal) {
    var emailInput = modal.querySelector('[data-modal-email]');
    var statusEl = modal.querySelector('[data-modal-status]');
    if (!emailInput) return;

    var email = emailInput.value.trim();
    if (!email) return;

    var apiBase = window.SMW_PRO_API_BASE || '';
    fetch(apiBase + '/auth/magic-link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email })
    }).then(function (res) {
      if (!statusEl) return;
      if (res.status === 200) {
        statusEl.textContent = 'Check your inbox for a sign-in link.';
        statusEl.className = 'alert alert-success mt-2';
        statusEl.style.display = '';
      } else if (res.status === 403) {
        // No active subscription — show CTA only, no error
      }
      // All other errors: silently ignore
    }).catch(function () {
      // Best-effort — never block the CTA
    });
  }

  window.ProWatchlist = { init: initWatchlistButton };
})();
