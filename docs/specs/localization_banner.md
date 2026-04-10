# Localization Efforts Banner

**Status:** Done
**Author:** Copilot
**Created:** 2026-04-09
**Completed:** 2026-04-09

## Context

The stockmarketwords.com project aims to serve Singaporean and Chinese audiences through Simplified Chinese localization (zh-CN). However, there is no visible indicator to users that localization efforts are actively underway. This can create confusion—users may encounter partially-translated content or empty Chinese pages and assume the site is incomplete or abandoned. A prominent banner communicating active localization efforts builds confidence and sets user expectations appropriately.

## Goal

Display a sitewide banner (on all pages, all languages) stating that localization efforts are ongoing with a goal of fully supporting Singaporean and Chinese audiences. The banner should be dismissible by users and persist across visits via localStorage.

## Non-goals

- Translating the banner into Chinese (it appears sitewide including the English site).
- Providing a timeline or specific completion date.
- Collecting user feedback on the localization effort.
- Creating a dedicated localization status page.

## User stories

- As a visitor to the zh-CN section, I want to understand that the English → Chinese translation is actively in progress, so I know gaps are temporary rather than permanent.
- As a Singaporean user, I want to see that the site is specifically targeting my audience, so I feel welcome.
- As a returning visitor, I want to dismiss the banner so it doesn't clutter my experience, knowing I can re-enable it if needed.

## Design

### Banner placement and styling

- **Position:** At the very top of the page, above the Hugo header (add to Hugo's base layout template).
- **HTML structure:** A `.localization-banner` div with an info icon and close button.
- **Styling:** A soft blue or neutral background (#f0f4f8 or similar) that is visually distinct but not intrusive. Use accent color for the close button.
- **Text:** "🌍 Localization efforts underway — we're working towards full support of all languages of our audiences."
- **Note:** Text is intentionally language-agnostic and does not require translation across locales.

### JavaScript behavior

- **Close button:** Clicking the close button:
  1. Sets `localStorage.setItem('localizationBannerDismissed', 'true')`.
  2. Hides the banner with `display: none`.
- **On page load:** Check `localStorage.getItem('localizationBannerDismissed')`. If truthy, add a class `display: none` to the banner.
- **Reset mechanism:** Users can manually clear localStorage or the site can provide an admin option to re-show the banner (out of scope for v1).

### Files to create/modify

**New:**

- `hugo/site/static/js/localization-banner.js` — banner logic (show/dismiss).

**Modified:**

- `hugo/site/layouts/_default/baseof.html` — add banner div at the top.
- `hugo/site/static/css/style.css` (or relevant CSS file) — add banner styling.

### Banner markup (in baseof.html)

```html
<!-- Localization banner at the very top -->
<div id="localization-banner" class="localization-banner">
  <div class="localization-banner-content">
    <div class="localization-banner-message">
      <strong>🌍 Localization efforts underway</strong> — we're working towards full support of all languages of our audiences.
    </div>
    <button id="localization-banner-close" class="localization-banner-close" aria-label="Close localization banner">
      ✕
    </button>
  </div>
</div>
```

### Banner CSS (in style.css)

```css
/* Localization banner styling */
.localization-banner {
  background: linear-gradient(135deg, #e8f1f8 0%, #f0f6fb 100%);
  border-bottom: 2px solid #4a90e2;
  padding: 14px 16px;
  font-size: 14px;
  color: #2c3e50;
}

.localization-banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  max-width: 1200px;
  margin: 0 auto;
}

.localization-banner-message {
  flex: 1;
  line-height: 1.4;
}

.localization-banner-message strong {
  color: #2c3e50;
  font-weight: 600;
}

.localization-banner-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
  padding: 4px 8px;
  line-height: 1;
  transition: color 0.2s ease;
  flex-shrink: 0;
}

.localization-banner-close:hover {
  color: #2c3e50;
}

.localization-banner.hidden {
  display: none;
}

@media (max-width: 768px) {
  .localization-banner {
    padding: 12px 12px;
  }

  .localization-banner-content {
    flex-wrap: wrap;
    gap: 8px;
  }

  .localization-banner-message {
    width: 100%;
    font-size: 13px;
  }

  .localization-banner-close {
    align-self: flex-start;
  }
}
```

### Banner JavaScript (in localization-banner.js)

```javascript
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
```

### Script inclusion

Add a line to baseof.html to load the banner script:

```html
<script src="{{ .Site.BaseURL }}/js/localization-banner.js"></script>
```

(Ensure this is placed after the main header/body content loads, or wrap in `DOMContentLoaded`.)

## Affected files

**New:**

- `hugo/site/static/js/localization-banner.js`

**Modified:**

- `hugo/site/layouts/_default/baseof.html`
- `hugo/site/static/css/style.css` (or whichever CSS file is the main stylesheet)

## Verification

1. **Manual local testing:**
   - Run `cd hugo/site && hugo server`.
   - Visit `http://localhost:1313/` (English homepage) → banner appears at the top.
   - Visit `http://localhost:1313/zh-cn/` (Chinese homepage) → banner appears at the top.
   - Click the close button → banner disappears.
   - Hard-refresh or open a new tab on the same site → banner remains hidden (localStorage persists).
   - Open DevTools and clear localStorage; reload → banner reappears.

2. **Production build check:**
   - Run `cd hugo/site && hugo --minify`.
   - Check that `public/js/localization-banner.js` exists and is minified (or not, per the project's build config).
   - Spot-check a few HTML files in `public/` to ensure the banner markup is present.

3. **Responsive check:**
   - Open `http://localhost:1313/` on a mobile viewport (< 768px width).
   - Confirm the banner text and close button stack vertically or adjust sensibly.

4. **No test breakage:**
   - Run `npm run test:e2e:pages` to ensure Puppeteer tests still pass.
   - The banner should not interfere with existing page tests (it is at the top, outside the main content area).

## Open questions

- **Q1:** Should the banner include a link (e.g., "Learn more about our localization roadmap")? **Default: no in v1.** The banner is informational; we can add a link in v2 if there is a dedicated roadmap page.
- **Q2:** Should the banner display different messages based on locale (e.g., a shorter Chinese-translated version on `/zh-cn/`)? **Default: no.** Use the same message globally for simplicity. If localization of the banner itself becomes needed, create a follow-up spec.
- **Q3:** Should the dismiss preference be global or per-device/browser? **Default: global (via localStorage).** This is device-specific and that's acceptable.

## Alternatives considered

- **Alert box or modal:** More intrusive and harder to dismiss. Chosen a banner for a better UX.
- **Only show on zh-CN pages:** Narrower reach; the banner serves the entire project's mission, so showing it globally is appropriate.
- **Hardcoded HTML in each layout:** Not scalable. A shared component in `baseof.html` is cleaner.
