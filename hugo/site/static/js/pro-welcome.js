(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('pro-welcome-status')) return;
    if (window.ProOtel) window.ProOtel.funnel('welcome_viewed');
    ProAuth.handleCheckoutSuccess();
  });
})();
