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

  var PRICE_KEYS = {
    monthly: 'pro-monthly-usd-2999',
    annual:  'pro-annual-usd-29900'
  };

  function selectedBillingPeriod() {
    var el = document.querySelector('input[name="billing-period"]:checked');
    return (el && el.value === 'annual') ? 'annual' : 'monthly';
  }

  function initBillingToggle() {
    var radios = document.querySelectorAll('input[name="billing-period"]');
    if (!radios.length) return;

    function update(period) {
      var isAnnual = period === 'annual';
      var monthly  = document.getElementById('price-monthly');
      var annual   = document.getElementById('price-annual');
      var label    = document.getElementById('billing-label');
      if (monthly) monthly.style.display = isAnnual ? 'none' : '';
      if (annual)  annual.style.display  = isAnnual ? ''     : 'none';
      if (label)   label.textContent     = isAnnual ? 'Billed annually' : 'Billed monthly';
    }

    radios.forEach(function (r) {
      r.addEventListener('change', function () { update(r.value); });
    });
  }

  function initSubscribeButton(btnId, errorId) {
    var btn = document.getElementById(btnId);
    if (!btn) return;

    btn.addEventListener('click', function () {
      var errorEl = errorId ? document.getElementById(errorId) : null;
      btn.disabled = true;
      btn.textContent = 'Loading…';

      var priceKey = PRICE_KEYS[selectedBillingPeriod()];
      var apiBase  = window.SMW_PRO_API_BASE || '';

      fetch(apiBase + '/checkout/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_lookup_key: priceKey })
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

  document.addEventListener('DOMContentLoaded', function () {
    initBillingToggle();

    var btn = document.getElementById('subscribe-btn');
    if (!btn) return;
    if (typeof ProAuth !== 'undefined' && ProAuth.isLoggedIn()) {
      btn.textContent = 'Access your dashboard →';
      btn.onclick = function () { window.location.href = '/pro/dashboard/'; };
    } else {
      initSubscribeButton('subscribe-btn', 'subscribe-error');
    }
  });
})();
