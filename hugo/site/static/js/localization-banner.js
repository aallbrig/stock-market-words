document.addEventListener('DOMContentLoaded', function() {
  const banner = document.getElementById('localization-banner');
  const closeBtn = document.getElementById('localization-banner-close');

  // Check if user has dismissed the banner
  if (localStorage.getItem('localizationBannerDismissed') === 'true') {
    banner.classList.add('hidden');
  }

  // Handle close button click
  if (closeBtn) {
    closeBtn.addEventListener('click', function() {
      localStorage.setItem('localizationBannerDismissed', 'true');
      banner.classList.add('hidden');
    });
  }
});
