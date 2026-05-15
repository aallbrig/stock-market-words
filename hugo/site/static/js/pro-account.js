(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('billing-portal-btn')) return;

    try { ProAuth.requireLogin(); } catch (_) { return; }

    var emailEl = document.getElementById('pro-email');
    if (emailEl) emailEl.textContent = ProAuth.getEmail() || '—';

    var apiBase = window.SMW_PRO_API_BASE || '';

    // Prefetch the billing portal URL and show subscription status on load.
    ProAuth.authFetch(apiBase + '/pro/subscription/portal', { method: 'POST' })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.url) {
          var btn = document.getElementById('billing-portal-btn');
          if (btn) btn.dataset.portalUrl = data.url;
        }
        var detailsEl = document.getElementById('pro-sub-details');
        var badgeEl = document.getElementById('pro-sub-status-badge');
        var renewsEl = document.getElementById('pro-sub-renews');
        if (detailsEl && badgeEl && data.url) {
          badgeEl.textContent = 'Active';
          badgeEl.className = 'badge bg-success me-2';
          if (renewsEl && data.current_period_end) {
            var d = new Date(data.current_period_end * 1000);
            renewsEl.textContent = 'Renews ' + d.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
          }
          detailsEl.style.display = '';
        }
      })
      .catch(function () {});

    var billingBtn = document.getElementById('billing-portal-btn');
    if (billingBtn) {
      billingBtn.addEventListener('click', function () {
        var url = billingBtn.dataset.portalUrl;
        if (url) { window.location.href = url; return; }
        billingBtn.disabled = true;
        billingBtn.textContent = 'Loading…';
        ProAuth.authFetch(apiBase + '/pro/subscription/portal', { method: 'POST' })
          .then(function (res) { return res.json(); })
          .then(function (data) {
            if (data.url) { window.location.href = data.url; }
            else { throw new Error('no url'); }
          })
          .catch(function () {
            billingBtn.disabled = false;
            billingBtn.textContent = 'Manage billing →';
            var err = document.getElementById('billing-error');
            if (err) { err.textContent = 'Unable to open billing portal. Please try again.'; err.style.display = ''; }
          });
      });
    }

    var deleteBtn = document.getElementById('delete-account-btn');
    var modal = document.getElementById('delete-confirm-modal');
    var confirmYes = document.getElementById('delete-confirm-yes');
    var confirmNo = document.getElementById('delete-confirm-no');

    if (deleteBtn && modal) {
      deleteBtn.addEventListener('click', function () { modal.style.display = 'flex'; });
      confirmNo.addEventListener('click', function () { modal.style.display = 'none'; });
      confirmYes.addEventListener('click', function () {
        confirmYes.disabled = true;
        confirmYes.textContent = 'Deleting…';
        ProAuth.authFetch(apiBase + '/pro/account', { method: 'DELETE' })
          .then(function (res) {
            if (res.status === 204) { ProAuth.logout(); }
            else { throw new Error('delete failed'); }
          })
          .catch(function () {
            modal.style.display = 'none';
            confirmYes.disabled = false;
            confirmYes.textContent = 'Yes, delete everything';
            var err = document.getElementById('delete-error');
            if (err) { err.textContent = 'Unable to delete account. Please try again or contact support.'; err.style.display = ''; }
          });
      });
    }
  });
})();
