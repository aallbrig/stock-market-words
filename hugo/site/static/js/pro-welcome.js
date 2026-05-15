(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('pro-welcome-status')) return;
    ProAuth.handleCheckoutSuccess();
  });
})();
