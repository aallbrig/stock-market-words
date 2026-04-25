document.addEventListener('DOMContentLoaded', function() {
  var BANNER_VERSION = 'v2-welcome';
  var STORAGE_KEY = 'bannerDismissed_' + BANNER_VERSION;

  var banner = document.getElementById('localization-banner');
  var closeBtn = document.getElementById('localization-banner-close');

  if (localStorage.getItem(STORAGE_KEY) !== 'true') {
    banner.classList.remove('hidden');
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', function() {
      localStorage.setItem(STORAGE_KEY, 'true');
      banner.classList.add('hidden');
    });
  }
});
