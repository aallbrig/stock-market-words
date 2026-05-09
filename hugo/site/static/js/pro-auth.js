/**
 * pro-auth.js — ProAuth global authentication module
 *
 * Must be loaded before any other Pro JS files.
 * Exposes the ProAuth global object used across all /pro/* pages.
 */

(function () {
  'use strict';

  const JWT_KEY = 'smw_pro_token';
  const EMAIL_KEY = 'smw_pro_email';

  function decodePayload(token) {
    try {
      const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(atob(base64));
    } catch (_) {
      return null;
    }
  }

  const ProAuth = {
    getToken: function () {
      return localStorage.getItem(JWT_KEY);
    },

    isLoggedIn: function () {
      const token = this.getToken();
      if (!token) return false;
      const payload = decodePayload(token);
      if (!payload || !payload.exp) return false;
      return payload.exp * 1000 > Date.now();
    },

    getEmail: function () {
      return localStorage.getItem(EMAIL_KEY);
    },

    logout: function () {
      localStorage.removeItem(JWT_KEY);
      localStorage.removeItem(EMAIL_KEY);
      window.location.href = '/pro/';
    },

    requireLogin: function () {
      if (!this.isLoggedIn()) {
        window.location.href = '/pro/login/';
        // Prevent any further execution on the page
        throw new Error('redirecting to login');
      }
    },

    authFetch: function (url, options) {
      const token = this.getToken();
      const opts = Object.assign({}, options || {});
      opts.headers = Object.assign({}, opts.headers || {}, {
        'Authorization': 'Bearer ' + token
      });
      return fetch(url, opts).then(function (res) {
        if (res.status === 401 || res.status === 403) {
          ProAuth.logout();
          // Return a never-resolving promise to stop the chain
          return new Promise(function () {});
        }
        return res;
      });
    },

    handleMagicCallback: function () {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');
      const statusEl = document.getElementById('pro-callback-status');

      if (!token) {
        if (statusEl) statusEl.textContent = 'No token found in URL. Please request a new magic link.';
        return;
      }

      const apiBase = window.SMW_PRO_API_BASE || '';
      fetch(apiBase + '/auth/callback?token=' + encodeURIComponent(token))
        .then(function (res) { return res.json().then(function (data) { return { status: res.status, data: data }; }); })
        .then(function (result) {
          if (result.status !== 200 || !result.data.token) {
            if (statusEl) statusEl.textContent = result.data.error || 'Invalid or expired link. Please request a new one.';
            return;
          }
          localStorage.setItem(JWT_KEY, result.data.token);
          if (result.data.email) localStorage.setItem(EMAIL_KEY, result.data.email);
          window.location.href = '/pro/dashboard/';
        })
        .catch(function () {
          if (statusEl) statusEl.textContent = 'Network error. Please check your connection and try again.';
        });
    },

    handleCheckoutSuccess: function () {
      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get('session_id');
      const statusEl = document.getElementById('pro-welcome-status');
      const apiBase = window.SMW_PRO_API_BASE || '';

      if (!sessionId) {
        if (statusEl) statusEl.textContent = 'No session found. If you completed payment, please sign in below.';
        return;
      }

      let attempts = 0;
      const maxAttempts = 3;

      function tryExchange() {
        attempts++;
        fetch(apiBase + '/auth/session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        })
          .then(function (res) { return res.json().then(function (data) { return { status: res.status, data: data }; }); })
          .then(function (result) {
            if (result.status === 200 && result.data.token) {
              localStorage.setItem(JWT_KEY, result.data.token);
              if (result.data.email) localStorage.setItem(EMAIL_KEY, result.data.email);
              if (statusEl) statusEl.textContent = 'Welcome to Pro! Redirecting to your dashboard…';
              setTimeout(function () { window.location.href = '/pro/dashboard/'; }, 1000);
              return;
            }
            if (attempts < maxAttempts) {
              if (statusEl) statusEl.textContent = 'Setting up your account… (attempt ' + attempts + ' of ' + maxAttempts + ')';
              setTimeout(tryExchange, 3000);
            } else {
              if (statusEl) {
                statusEl.innerHTML = 'This is taking longer than expected. If you completed payment, please check your email, then try <a href="/pro/login/">signing in</a>.';
              }
            }
          })
          .catch(function () {
            if (attempts < maxAttempts) {
              setTimeout(tryExchange, 3000);
            } else {
              if (statusEl) statusEl.innerHTML = 'Unable to complete setup. Please try <a href="/pro/login/">signing in</a>.';
            }
          });
      }

      tryExchange();
    }
  };

  window.ProAuth = ProAuth;
})();
