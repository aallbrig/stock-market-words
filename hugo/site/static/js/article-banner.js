/**
 * Article Announcement Banner System
 *
 * Manages a dismissable banner for new articles with configurable expiration.
 * Banner starts hidden and is revealed only when a valid article is configured
 * and the user hasn't dismissed it within the expiration window.
 *
 * Dismiss triggers: close button click OR article link click.
 *
 * Configuration via window.articleBannerConfig (injected by baseof.html):
 * {
 *   articleTitle: "Article Title",
 *   articleUrl: "/articles/article-slug/",
 *   expirationDays: 7
 * }
 */

document.addEventListener('DOMContentLoaded', function() {
  const banner = document.getElementById('article-banner');
  const closeBtn = document.getElementById('article-banner-close');
  const link = document.getElementById('article-banner-link');
  const config = window.articleBannerConfig;

  if (!banner) return;

  // No article configured — stay hidden
  if (!config || !config.articleTitle || !config.articleUrl) return;

  // Populate link
  if (link) {
    link.textContent = config.articleTitle;
    link.href = config.articleUrl;
  }

  var expirationDays = config.expirationDays || 7;
  var expirationMs = expirationDays * 24 * 60 * 60 * 1000;
  var dismissalKey = 'articleBannerDismissed_' + config.articleUrl;
  var expirationKey = 'articleBannerExpiration_' + config.articleUrl;

  function isDismissed() {
    var ts = localStorage.getItem(dismissalKey);
    if (!ts) return false;
    var exp = parseInt(localStorage.getItem(expirationKey), 10);
    if (Date.now() > exp) {
      localStorage.removeItem(dismissalKey);
      localStorage.removeItem(expirationKey);
      return false;
    }
    return true;
  }

  function dismiss() {
    var now = Date.now();
    localStorage.setItem(dismissalKey, String(now));
    localStorage.setItem(expirationKey, String(now + expirationMs));
    banner.classList.add('hidden');
  }

  // Show banner only if not previously dismissed
  if (!isDismissed()) {
    banner.classList.remove('hidden');
  }

  // Dismiss on close button
  if (closeBtn) {
    closeBtn.addEventListener('click', function() { dismiss(); });
  }

  // Dismiss on article link click (user is navigating to the article)
  if (link) {
    link.addEventListener('click', function() { dismiss(); });
  }
});

/**
 * Utility: clear ALL article banner dismissals.
 * Run in browser console: clearAllArticleBannerDismissals()
 */
window.clearAllArticleBannerDismissals = function() {
  var keysToRemove = [];
  for (var i = 0; i < localStorage.length; i++) {
    var key = localStorage.key(i);
    if (key && (key.indexOf('articleBannerDismissed_') === 0 || key.indexOf('articleBannerExpiration_') === 0)) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach(function(k) { localStorage.removeItem(k); });
  console.log('Cleared ' + keysToRemove.length + ' article banner dismissal(s). Refresh the page.');
};

/**
 * Utility: clear dismissal for a specific article URL.
 * Run in browser console: clearArticleBannerDismissal('/articles/slug/')
 */
window.clearArticleBannerDismissal = function(articleUrl) {
  localStorage.removeItem('articleBannerDismissed_' + articleUrl);
  localStorage.removeItem('articleBannerExpiration_' + articleUrl);
  console.log('Cleared dismissal for ' + articleUrl + '. Refresh the page.');
};
