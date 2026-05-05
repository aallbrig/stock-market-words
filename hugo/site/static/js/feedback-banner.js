/**
 * Feedback Survey Banner System
 *
 * Manages a dismissable banner for the user feedback survey.
 *
 * Dismiss triggers: close button click OR survey link click.
 *
 * Configuration via window.feedbackBannerConfig (injected by baseof.html):
 * {
 *   enabled: true,
 *   url: "https://forms.gle/...",
 *   expirationDays: 14
 * }
 */

document.addEventListener('DOMContentLoaded', function() {
  const banner = document.getElementById('feedback-banner');
  const closeBtn = document.getElementById('feedback-banner-close');
  const config = window.feedbackBannerConfig;

  if (!banner) return;

  // Disabled or no URL — stay hidden
  if (!config || !config.enabled || !config.url) return;

  var expirationDays = config.expirationDays || 14;
  var expirationMs = expirationDays * 24 * 60 * 60 * 1000;
  var dismissalKey = 'feedbackBannerDismissed';
  var expirationKey = 'feedbackBannerExpiration';

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

  // Also dismiss if they click the link (assumed they took the survey or at least saw it)
  const surveyLink = banner.querySelector('a');
  if (surveyLink) {
    surveyLink.addEventListener('click', function() { dismiss(); });
  }
});
