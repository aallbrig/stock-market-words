/**
 * pro-magic-link.js — magic link request form logic
 *
 * Used by /pro/login/ page.
 * Calls POST /auth/magic-link with the user's email.
 */

(function () {
  'use strict';

  function initMagicLinkForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const emailInput = form.querySelector('input[type="email"]');
    const submitBtn = form.querySelector('button[type="submit"]');
    const statusEl = document.getElementById('pro-login-status');

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const email = emailInput ? emailInput.value.trim() : '';
      if (!email) return;

      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Sending…'; }

      const apiBase = window.SMW_PRO_API_BASE || '';
      fetch(apiBase + '/auth/magic-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      })
        .then(function (res) { return res.json().then(function (data) { return { status: res.status, data: data }; }); })
        .then(function (result) {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Send Magic Link'; }
          if (!statusEl) return;

          if (result.status === 200) {
            statusEl.className = 'alert alert-success';
            statusEl.textContent = 'Check your inbox! A magic link has been sent to ' + email + '. It expires in 10 minutes.';
          } else if (result.status === 429) {
            statusEl.className = 'alert alert-warning';
            statusEl.textContent = 'A magic link was recently sent. Please check your email.';
          } else if (result.status === 403) {
            statusEl.className = 'alert alert-warning';
            statusEl.innerHTML = 'We don\'t have a Pro subscription for that email. <a href="/pro/">Subscribe for SGD $29.99/month →</a>';
          } else {
            statusEl.className = 'alert alert-danger';
            statusEl.textContent = (result.data && result.data.error) || 'Something went wrong. Please try again.';
          }
          statusEl.style.display = '';
        })
        .catch(function () {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Send Magic Link'; }
          if (statusEl) {
            statusEl.className = 'alert alert-danger';
            statusEl.textContent = 'Network error. Please check your connection and try again.';
            statusEl.style.display = '';
          }
        });
    });
  }

  window.ProMagicLink = { initMagicLinkForm: initMagicLinkForm };
})();
