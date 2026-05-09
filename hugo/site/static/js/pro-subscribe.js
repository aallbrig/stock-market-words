/**
 * pro-subscribe.js — shared "Subscribe Now" button logic
 *
 * Used by /pro/ (pricing page) and /pro/product/ (product page).
 * Calls POST /checkout/session → redirects browser to Stripe-hosted Checkout.
 *
 * Usage: call initSubscribeButton('subscribe-btn', 'subscribe-error') after DOM ready.
 */

(function () {
  'use strict';

  function initSubscribeButton(btnId, errorId) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    btn.addEventListener('click', function () {
      const errorEl = errorId ? document.getElementById(errorId) : null;
      btn.disabled = true;
      btn.textContent = 'Loading…';

      const apiBase = window.SMW_PRO_API_BASE || '';
      fetch(apiBase + '/checkout/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_lookup_key: 'pro-monthly-sgd-2999' })
      })
        .then(function (res) {
          if (!res.ok) throw new Error('checkout failed');
          return res.json();
        })
        .then(function (data) {
          if (!data.url) throw new Error('no redirect URL');
          window.location.href = data.url;
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = 'Subscribe Now';
          if (errorEl) errorEl.textContent = 'Something went wrong. Please try again.';
        });
    });
  }

  window.ProSubscribe = { initSubscribeButton: initSubscribeButton };
})();
