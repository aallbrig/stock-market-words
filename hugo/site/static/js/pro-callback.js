(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('pro-callback-status')) return;
    ProAuth.handleMagicCallback();
  });
})();
