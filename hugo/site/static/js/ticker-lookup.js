/**
 * ticker-lookup.js
 *
 * Powers the ticker lookup widget — supports multiple instances on the same page:
 *   - Home page: full-feature mode with persistent error div and recent chips below the form.
 *   - Nav bar: compact mode with errors and recents shown inside the autocomplete dropdown.
 *
 * Three features:
 *   1. Autocomplete — real-time dropdown filtered by symbol prefix or company name substring.
 *   2. Not-found feedback — inline warning instead of a 404 redirect.
 *   3. Recent lookups — last 5 looked-up symbols persisted in localStorage.
 *
 * Depends on window.SITE_BASE_URL being set by the enclosing Hugo template.
 * Data source: {SITE_BASE_URL}data/ticker-lookup.json (lazy-loaded on first focus).
 */
(function () {
  'use strict';

  var DATA_URL = (window.SITE_BASE_URL || '/') + 'data/ticker-lookup.json';
  var RECENT_KEY = 'smw-recent-tickers';
  var MAX_RECENT = 5;
  var MAX_SUGGESTIONS = 8;

  // Shared across all instances — fetch fires at most once.
  var lookupTickers = null;
  var loadPromise = null;

  // ---------------------------------------------------------------------------
  // Shared: data loading
  // ---------------------------------------------------------------------------

  function loadData() {
    if (loadPromise) return loadPromise;
    loadPromise = fetch(DATA_URL)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        lookupTickers = d.tickers || [];
        return lookupTickers;
      })
      .catch(function (err) {
        console.warn('ticker-lookup: failed to load data —', err);
        lookupTickers = [];
        return [];
      });
    return loadPromise;
  }

  // ---------------------------------------------------------------------------
  // Shared: filtering
  // ---------------------------------------------------------------------------

  function filterTickers(query) {
    if (!query || !lookupTickers) return [];
    var upper = query.toUpperCase();
    var lower = query.toLowerCase();
    var results = [];
    for (var i = 0; i < lookupTickers.length; i++) {
      if (results.length >= MAX_SUGGESTIONS) break;
      var t = lookupTickers[i];
      if (t.s.startsWith(upper) || t.n.toLowerCase().indexOf(lower) !== -1) {
        results.push(t);
      }
    }
    return results;
  }

  // ---------------------------------------------------------------------------
  // Shared: localStorage recents
  // ---------------------------------------------------------------------------

  function getRecents() {
    try {
      var raw = localStorage.getItem(RECENT_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (_) {
      return [];
    }
  }

  function saveRecent(sym) {
    var recents = getRecents().filter(function (s) { return s !== sym; });
    recents.unshift(sym);
    if (recents.length > MAX_RECENT) recents.length = MAX_RECENT;
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(recents));
    } catch (_) {
      // Ignore storage errors (private browsing, quota exceeded, etc.)
    }
  }

  // ---------------------------------------------------------------------------
  // Shared: utilities
  // ---------------------------------------------------------------------------

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ---------------------------------------------------------------------------
  // Per-instance initialisation
  // ---------------------------------------------------------------------------

  function initTickerLookup(config) {
    var formId   = config.formId   || 'ticker-lookup-form';
    var inputId  = config.inputId  || 'ticker-lookup-input';
    var errorId  = config.errorId  || null;   // full mode only
    var recentId = config.recentId || null;   // full mode only
    var compact  = !!config.compact;

    // Dropdown element ID derived from the input ID (e.g. "ticker-lookup-input" → "ticker-lookup-dropdown").
    var dropdownId = inputId.replace(/-input$/, '-dropdown');

    var form  = document.getElementById(formId);
    var input = document.getElementById(inputId);
    if (!form || !input) return;

    // Per-instance mutable state.
    var activeIndex  = -1;
    var errorTimeout = null;

    // The autocomplete dropdown anchors to the input's wrapper (position:relative).
    function getWrapper()  { return input.parentElement; }
    function getDropdown() { return getWrapper().querySelector('.ticker-lookup-dropdown'); }

    // -- Dropdown helpers --------------------------------------------------

    function createMenuEl() {
      var menu = document.createElement('ul');
      menu.id        = dropdownId;
      menu.className = 'dropdown-menu show ticker-lookup-dropdown';
      menu.setAttribute('role', 'listbox');
      menu.style.cssText =
        'position:absolute;top:100%;left:0;right:0;z-index:1050;' +
        'max-height:280px;overflow-y:auto;margin-top:2px;';
      return menu;
    }

    function removeDropdown() {
      clearTimeout(errorTimeout);
      var existing = getDropdown();
      if (existing) existing.remove();
      activeIndex = -1;
    }

    function highlightItem(idx) {
      var menu = getDropdown();
      if (!menu) return;
      var items = menu.querySelectorAll('[data-symbol]');
      items.forEach(function (el, i) {
        el.classList.toggle('active', i === idx);
      });
      activeIndex = idx;
    }

    function showDropdown(items) {
      removeDropdown();
      if (!items.length) return;

      var menu = createMenuEl();
      items.forEach(function (t) {
        var li  = document.createElement('li');
        var btn = document.createElement('button');
        btn.type      = 'button';
        btn.className = 'dropdown-item d-flex align-items-baseline gap-2';
        btn.setAttribute('role', 'option');
        btn.dataset.symbol = t.s;

        var sym  = document.createElement('strong');
        sym.textContent = t.s;
        var name = document.createElement('span');
        name.className  = 'text-muted small text-truncate';
        name.textContent = t.n;

        btn.appendChild(sym);
        btn.appendChild(name);
        btn.addEventListener('mousedown', function (e) {
          // Use mousedown so it fires before the input blur event.
          e.preventDefault();
          selectSuggestion(t.s);
        });
        li.appendChild(btn);
        menu.appendChild(li);
      });

      activeIndex = -1;
      getWrapper().appendChild(menu);
    }

    function showRecentDropdown() {
      var recents = getRecents();
      if (!recents.length) return;
      removeDropdown();

      var menu = createMenuEl();

      var header     = document.createElement('li');
      var headerSpan = document.createElement('span');
      headerSpan.className  = 'dropdown-item-text text-muted small';
      headerSpan.textContent = '🕐 Recent';
      header.appendChild(headerSpan);
      menu.appendChild(header);

      recents.forEach(function (sym) {
        var li  = document.createElement('li');
        var btn = document.createElement('button');
        btn.type           = 'button';
        btn.className      = 'dropdown-item';
        btn.dataset.symbol = sym;
        btn.textContent    = sym;
        btn.addEventListener('mousedown', function (e) {
          e.preventDefault();
          selectSuggestion(sym);
        });
        li.appendChild(btn);
        menu.appendChild(li);
      });

      activeIndex = -1;
      getWrapper().appendChild(menu);
    }

    function showErrorDropdown(msg) {
      removeDropdown();
      var menu = createMenuEl();
      var li   = document.createElement('li');
      var span = document.createElement('span');
      span.className  = 'dropdown-item-text text-warning-emphasis bg-warning-subtle px-3 py-1 d-block';
      span.textContent = '⚠ ' + msg;
      li.appendChild(span);
      menu.appendChild(li);
      getWrapper().appendChild(menu);
      errorTimeout = setTimeout(removeDropdown, 3000);
    }

    // -- Error / recents (full mode) ---------------------------------------

    function showError(msg) {
      if (compact) {
        showErrorDropdown(msg);
        return;
      }
      var el = errorId ? document.getElementById(errorId) : null;
      if (!el) return;
      el.className = 'alert alert-warning py-2 px-3 mt-2 mb-0';
      el.textContent = msg;
      el.style.display = '';
    }

    function clearError() {
      if (compact) return;
      var el = errorId ? document.getElementById(errorId) : null;
      if (el) { el.style.display = 'none'; el.textContent = ''; }
    }

    function renderRecentsFullMode() {
      var container = recentId ? document.getElementById(recentId) : null;
      if (!container) return;
      var recents = getRecents();
      if (!recents.length) { container.style.display = 'none'; return; }
      var base = window.SITE_BASE_URL || '/';
      var html = '<small class="text-muted me-1">Recent:</small>';
      recents.forEach(function (sym) {
        html +=
          '<a href="' + base + 'tickers/' + sym.toLowerCase() + '/" ' +
          'class="badge bg-secondary-subtle text-secondary-emphasis ' +
          'text-decoration-none me-1">' +
          escHtml(sym) + '</a>';
      });
      container.innerHTML = html;
      container.style.display = '';
    }

    // -- Validation + navigation -------------------------------------------

    function isKnownTicker(sym) {
      if (!lookupTickers) return true; // data not yet loaded — allow navigation
      return lookupTickers.some(function (t) { return t.s === sym; });
    }

    function selectSuggestion(sym) {
      input.value = sym;
      removeDropdown();
      submitLookup(sym);
    }

    function submitLookup(rawSym) {
      var sym = (rawSym || '').trim().toUpperCase();
      if (!sym) return;

      if (!isKnownTicker(sym)) {
        showError(
          '"' + sym + '" was not found. ' +
          'Try the full company name or browse all tickers.'
        );
        return;
      }

      clearError();
      saveRecent(sym);
      if (!compact) renderRecentsFullMode();
      window.location.href =
        (window.SITE_BASE_URL || '/') + 'tickers/' + sym.toLowerCase() + '/';
    }

    // -- Event listeners ---------------------------------------------------

    form.removeAttribute('onsubmit');

    input.addEventListener('focus', function () {
      loadData();
      if (compact && !input.value.trim()) showRecentDropdown();
    });

    input.addEventListener('input', function () {
      clearError();
      var q = input.value.trim();
      if (!q) {
        removeDropdown();
        if (compact) showRecentDropdown();
        return;
      }
      loadData().then(function () {
        if (input.value.trim() !== q) return; // user typed more while loading
        showDropdown(filterTickers(q));
      });
    });

    input.addEventListener('keydown', function (e) {
      var menu = getDropdown();
      if (!menu) return;
      var items = menu.querySelectorAll('[data-symbol]');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        highlightItem(Math.min(activeIndex + 1, items.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        highlightItem(Math.max(activeIndex - 1, 0));
        return;
      }
      if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        var highlighted = items[activeIndex];
        if (highlighted && highlighted.dataset.symbol) {
          selectSuggestion(highlighted.dataset.symbol);
        }
        return;
      }
      if (e.key === 'Escape') {
        removeDropdown();
      }
    });

    document.addEventListener('click', function (e) {
      if (!form.contains(e.target)) removeDropdown();
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      removeDropdown();
      submitLookup(input.value);
    });

    // Render existing recents on page load (full mode only).
    if (!compact) renderRecentsFullMode();
  }

  // ---------------------------------------------------------------------------
  // Default initialisation — home page and nav bar instances
  // ---------------------------------------------------------------------------

  function init() {
    // Home page "Look Up a Ticker" card — full-feature mode.
    initTickerLookup({
      formId:   'ticker-lookup-form',
      inputId:  'ticker-lookup-input',
      errorId:  'ticker-lookup-error',
      recentId: 'ticker-recent-lookups',
      compact:  false,
    });

    // Navigation bar — compact mode (errors and recents inside the dropdown).
    initTickerLookup({
      formId:  'nav-ticker-lookup-form',
      inputId: 'nav-ticker-lookup-input',
      compact: true,
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
