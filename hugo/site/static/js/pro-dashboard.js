(function () {
  'use strict';

  var cfg = {};
  var state = {
    watchlists: [],
    activeId: null,
    scores: {},    // symbol -> {dd,ms,fk,oh,iw,rr,p,pc}
    lookup: {},    // symbol -> name
    lookupArr: []  // [{s, n}]
  };

  // ── Debug logging ──────────────────────────────────────────────────────────
  function log(event, data) {
    var entry = { t: new Date().toISOString().slice(11, 23), event: event };
    if (data !== undefined) entry.data = data;
    console.log('[Dashboard]', event, data !== undefined ? data : '');
  }

  // ── Auth ───────────────────────────────────────────────────────────────────
  function apiFetch(method, path, body) {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    log('apiFetch', { method: method, path: path, body: body });
    return ProAuth.authFetch(cfg.apiBase + path, opts);
  }

  // ── Data loading ───────────────────────────────────────────────────────────
  function loadScores() {
    log('loadScores:start', cfg.scoresUrl);
    return fetch(cfg.scoresUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.scores = {};
        var tickers = data.tickers || data;
        tickers.forEach(function (row) { state.scores[row.s] = row; });
        log('loadScores:done', Object.keys(state.scores).length + ' tickers');
      })
      .catch(function (err) { log('loadScores:error', String(err)); throw err; });
  }

  function loadLookup() {
    log('loadLookup:start', cfg.lookupUrl);
    return fetch(cfg.lookupUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.lookup = {};
        state.lookupArr = data.tickers || data;
        state.lookupArr.forEach(function (row) { state.lookup[row.s] = row.n; });
        log('loadLookup:done', state.lookupArr.length + ' symbols');
      })
      .catch(function (err) { log('loadLookup:error', String(err)); throw err; });
  }

  function loadWatchlists() {
    log('loadWatchlists:start');
    return apiFetch('GET', '/pro/watchlists')
      .then(function (r) {
        log('loadWatchlists:http', r.status);
        return r.json();
      })
      .then(function (data) {
        state.watchlists = data.watchlists || [];
        log('loadWatchlists:done', state.watchlists.map(function (w) {
          return { id: w.watchlist_id, name: w.name, tickers: (w.tickers || []).length };
        }));
      })
      .catch(function (err) { log('loadWatchlists:error', String(err)); throw err; });
  }

  function createWatchlist(name) {
    log('createWatchlist', name);
    return apiFetch('POST', '/pro/watchlists', { name: name })
      .then(function (r) {
        log('createWatchlist:http', r.status);
        return r.json();
      })
      .then(function (wl) {
        log('createWatchlist:done', wl);
        return wl;
      });
  }

  function updateWatchlist(id, patch) {
    log('updateWatchlist', { id: id, patch: patch });
    return apiFetch('PUT', '/pro/watchlists/' + id, patch)
      .then(function (r) {
        log('updateWatchlist:http', r.status);
        return r.json();
      })
      .then(function (wl) {
        log('updateWatchlist:done', { id: wl.watchlist_id, tickers: (wl.tickers || []).length });
        return wl;
      });
  }

  function deleteWatchlist(id) {
    log('deleteWatchlist', id);
    return apiFetch('DELETE', '/pro/watchlists/' + id)
      .then(function (r) { log('deleteWatchlist:http', r.status); return r; });
  }

  // ── Sidebar ────────────────────────────────────────────────────────────────
  function renderSidebar() {
    log('renderSidebar', { count: state.watchlists.length, activeId: state.activeId });
    var list = document.getElementById('wl-list');
    if (!list) { log('renderSidebar:warn', '#wl-list not found'); return; }
    list.innerHTML = '';
    state.watchlists.forEach(function (wl) {
      var btn = document.createElement('button');
      btn.className = 'btn btn-sm w-100 text-start px-3 py-2 rounded-0 border-0' +
        (wl.watchlist_id === state.activeId ? ' active bg-primary text-white' : '');
      btn.textContent = wl.name;
      btn.addEventListener('click', function () { selectWatchlist(wl.watchlist_id); });
      list.appendChild(btn);
    });
  }

  function selectWatchlist(id) {
    log('selectWatchlist', id);
    state.activeId = id;
    renderSidebar();
    renderDetail();
  }

  // ── Detail ─────────────────────────────────────────────────────────────────
  function activeWatchlist() {
    return state.watchlists.find(function (w) { return w.watchlist_id === state.activeId; });
  }

  function renderDetail() {
    var wl = activeWatchlist();
    log('renderDetail', { activeId: state.activeId, wl: wl ? wl.name : null, tickers: wl ? (wl.tickers || []).length : 0 });
    var emptyEl = document.getElementById('wl-empty');
    var detail = document.getElementById('wl-detail');

    if (!state.activeId || !wl) {
      log('renderDetail:empty-state', 'no active watchlist');
      if (emptyEl) emptyEl.style.display = '';
      if (detail) detail.style.display = 'none';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';
    if (detail) detail.style.display = '';

    var nameEl = document.getElementById('wl-detail-name');
    if (nameEl) nameEl.textContent = wl.name;

    renderChips(wl);
    renderTable(wl);
    renderRadar(wl);
    renderHeatmap(wl);
  }

  // ── Chips ──────────────────────────────────────────────────────────────────
  function renderChips(wl) {
    var container = document.getElementById('wl-tickers');
    if (!container) return;
    container.innerHTML = '';
    (wl.tickers || []).forEach(function (sym) {
      var chip = document.createElement('span');
      chip.className = 'badge bg-secondary d-inline-flex align-items-center gap-1';
      chip.innerHTML =
        '<span>' + sym + '</span>' +
        '<button type="button" class="btn-close btn-close-white btn-sm" aria-label="Remove"></button>';
      chip.querySelector('button').addEventListener('click', function () { removeTicker(sym); });
      container.appendChild(chip);
    });
  }

  // ── Table ──────────────────────────────────────────────────────────────────
  function fmtScore(v) { return v != null ? v : '—'; }
  function fmtPct(v) { return v != null ? (v >= 0 ? '+' : '') + v.toFixed(2) + '%' : '—'; }
  function fmtPrice(v) { return v != null ? '$' + v.toFixed(2) : '—'; }

  function renderTable(wl) {
    var tbody = document.getElementById('wl-table-body');
    var tfoot = document.getElementById('wl-table-foot');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (tfoot) tfoot.innerHTML = '';
    var tickers = wl.tickers || [];
    if (tickers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-3">No tickers yet — search above to add one.</td></tr>';
      return;
    }

    var scoreKeys = ['p', 'pc', 'dd', 'ms', 'fk', 'oh', 'iw', 'rr'];
    var sums = {}, counts = {};
    scoreKeys.forEach(function (k) { sums[k] = 0; counts[k] = 0; });

    tickers.forEach(function (sym) {
      var sc = state.scores[sym] || {};
      var tr = document.createElement('tr');
      var pcClass = sc.pc > 0 ? 'text-success' : sc.pc < 0 ? 'text-danger' : '';
      tr.innerHTML =
        '<td class="ps-3"><a href="/tickers/' + encodeURIComponent(sym.toLowerCase()) + '/" target="_blank">' + sym + '</a></td>' +
        '<td class="text-muted small">' + (state.lookup[sym] || '') + '</td>' +
        '<td class="text-end">' + fmtPrice(sc.p) + '</td>' +
        '<td class="text-end ' + pcClass + '">' + fmtPct(sc.pc) + '</td>' +
        '<td class="text-end">' + fmtScore(sc.dd) + '</td>' +
        '<td class="text-end">' + fmtScore(sc.ms) + '</td>' +
        '<td class="text-end">' + fmtScore(sc.fk) + '</td>' +
        '<td class="text-end">' + fmtScore(sc.oh) + '</td>' +
        '<td class="text-end">' + fmtScore(sc.iw) + '</td>' +
        '<td class="text-end">' + fmtScore(sc.rr) + '</td>' +
        '<td class="pe-3"><button class="btn btn-sm btn-outline-danger py-0">✕</button></td>';
      tr.querySelector('button').addEventListener('click', function () { removeTicker(sym); });
      tbody.appendChild(tr);

      scoreKeys.forEach(function (k) {
        if (sc[k] != null) { sums[k] += sc[k]; counts[k]++; }
      });
    });

    if (tfoot && tickers.length > 1) {
      function avg(k) { return counts[k] > 0 ? sums[k] / counts[k] : null; }
      var avgPc = avg('pc');
      var avgPcClass = avgPc > 0 ? 'text-success' : avgPc < 0 ? 'text-danger' : '';
      function fmtAvgScore(k) {
        var v = avg(k);
        return v != null ? Math.round(v).toString() : '—';
      }
      tfoot.innerHTML =
        '<tr class="table-secondary fw-semibold border-top">' +
        '<td class="ps-3 text-muted small">Avg</td>' +
        '<td class="text-muted small">' + tickers.length + ' tickers</td>' +
        '<td class="text-end">' + fmtPrice(avg('p')) + '</td>' +
        '<td class="text-end ' + avgPcClass + '">' + fmtPct(avgPc) + '</td>' +
        '<td class="text-end">' + fmtAvgScore('dd') + '</td>' +
        '<td class="text-end">' + fmtAvgScore('ms') + '</td>' +
        '<td class="text-end">' + fmtAvgScore('fk') + '</td>' +
        '<td class="text-end">' + fmtAvgScore('oh') + '</td>' +
        '<td class="text-end">' + fmtAvgScore('iw') + '</td>' +
        '<td class="text-end">' + fmtAvgScore('rr') + '</td>' +
        '<td class="pe-3"></td>' +
        '</tr>';
    }
  }

  // ── Radar chart ────────────────────────────────────────────────────────────
  var AXES = [
    { key: 'dd', label: 'Div Daddy' },
    { key: 'ms', label: 'Moon Shot' },
    { key: 'fk', label: 'Falling Knife' },
    { key: 'oh', label: 'Over Hyped' },
    { key: 'iw', label: 'Inst. Whale' },
    { key: 'rr', label: 'REIT Radar' }
  ];

  function renderRadar(wl) {
    var svgEl = document.getElementById('radar-chart');
    if (!svgEl || typeof d3 === 'undefined') return;
    d3.select(svgEl).selectAll('*').remove();

    var size = 260, cx = size / 2, cy = size / 2, r = 100;
    var n = AXES.length;
    var step = (2 * Math.PI) / n;
    var svg = d3.select(svgEl).attr('width', size).attr('height', size);

    [25, 50, 75, 100].forEach(function (pct) {
      var pts = AXES.map(function (_, i) {
        var a = i * step - Math.PI / 2;
        return [cx + (r * pct / 100) * Math.cos(a), cy + (r * pct / 100) * Math.sin(a)];
      });
      svg.append('polygon')
        .attr('points', pts.map(function (p) { return p.join(','); }).join(' '))
        .attr('fill', 'none').attr('stroke', '#dee2e6').attr('stroke-width', 1);
    });

    AXES.forEach(function (ax, i) {
      var a = i * step - Math.PI / 2;
      svg.append('line')
        .attr('x1', cx).attr('y1', cy)
        .attr('x2', cx + r * Math.cos(a)).attr('y2', cy + r * Math.sin(a))
        .attr('stroke', '#adb5bd').attr('stroke-width', 1);
      svg.append('text')
        .attr('x', cx + (r + 18) * Math.cos(a)).attr('y', cy + (r + 18) * Math.sin(a))
        .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
        .attr('font-size', 10).attr('fill', '#495057')
        .text(ax.label);
    });

    var tickers = (wl.tickers || []).filter(function (s) { return state.scores[s]; });
    log('renderRadar', { wl: wl.name, tickers: tickers.length, scoresAvailable: Object.keys(state.scores).length });
    if (tickers.length === 0) {
      svg.append('text').attr('x', cx).attr('y', cy)
        .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
        .attr('fill', '#adb5bd').attr('font-size', 12)
        .text('Add tickers to see radar');
      return;
    }

    var avgs = AXES.map(function (ax) {
      var vals = tickers
        .map(function (s) { return state.scores[s][ax.key]; })
        .filter(function (v) { return v != null; });
      return vals.length ? vals.reduce(function (a, b) { return a + b; }, 0) / vals.length : 0;
    });
    var poly = avgs.map(function (v, i) {
      var a = i * step - Math.PI / 2;
      return [cx + (r * v / 100) * Math.cos(a), cy + (r * v / 100) * Math.sin(a)];
    });
    svg.append('polygon')
      .attr('points', poly.map(function (p) { return p.join(','); }).join(' '))
      .attr('fill', 'rgba(13,110,253,0.2)').attr('stroke', '#0d6efd').attr('stroke-width', 2);
  }

  // ── Heatmap ────────────────────────────────────────────────────────────────
  function renderHeatmap(wl) {
    var container = document.getElementById('heatmap-chart');
    if (!container || typeof d3 === 'undefined') return;
    d3.select(container).selectAll('*').remove();

    var tickers = (wl.tickers || []).filter(function (s) {
      return state.scores[s] && state.scores[s].pc != null;
    });
    log('renderHeatmap', { wl: wl.name, tickersWithPc: tickers.length });
    if (tickers.length === 0) {
      container.innerHTML = '<p class="text-center text-muted mt-3">Add tickers to see heatmap</p>';
      return;
    }

    var color = d3.scaleDiverging([-5, 0, 5], d3.interpolateRdYlGn);
    var cols = Math.min(tickers.length, 8);
    var tileW = Math.max(60, Math.floor((container.offsetWidth || 480) / cols));
    var tileH = 56;
    var rows = Math.ceil(tickers.length / cols);

    var svg = d3.select(container).append('svg')
      .attr('width', cols * tileW).attr('height', rows * tileH + 4);

    tickers.forEach(function (sym, i) {
      var sc = state.scores[sym];
      var col = i % cols, row = Math.floor(i / cols);
      var g = svg.append('g').attr('transform', 'translate(' + (col * tileW) + ',' + (row * tileH) + ')');
      g.append('rect')
        .attr('width', tileW - 2).attr('height', tileH - 2).attr('rx', 4)
        .attr('fill', color(sc.pc));
      g.append('text')
        .attr('x', tileW / 2).attr('y', tileH / 2 - 7)
        .attr('text-anchor', 'middle').attr('font-size', 11).attr('font-weight', 600).attr('fill', '#212529')
        .text(sym);
      g.append('text')
        .attr('x', tileW / 2).attr('y', tileH / 2 + 9)
        .attr('text-anchor', 'middle').attr('font-size', 10).attr('fill', '#212529')
        .text((sc.pc >= 0 ? '+' : '') + sc.pc.toFixed(2) + '%');
    });
  }

  // ── Add widget (autocomplete) ──────────────────────────────────────────────
  function initAddWidget() {
    var input = document.getElementById('wl-ticker-input');
    var addBtn = document.getElementById('wl-add-btn');
    var wrapper = document.getElementById('wl-add-wrapper');
    var errorEl = document.getElementById('wl-add-error');
    if (!input || !addBtn || !wrapper) return;

    var dropdown = document.createElement('ul');
    dropdown.className = 'list-group position-absolute w-100 shadow-sm';
    dropdown.style.cssText = 'top:100%;left:0;z-index:1000;max-height:200px;overflow-y:auto;display:none;';
    wrapper.appendChild(dropdown);

    function showSuggestions(q) {
      dropdown.innerHTML = '';
      if (!q) { dropdown.style.display = 'none'; return; }
      var wl = activeWatchlist();
      var existing = wl ? (wl.tickers || []) : [];
      var hits = state.lookupArr.filter(function (row) {
        return row.s.startsWith(q) && !existing.includes(row.s);
      }).slice(0, 10);
      if (!hits.length) { dropdown.style.display = 'none'; return; }
      hits.forEach(function (row) {
        var li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action py-1 px-2 small';
        li.innerHTML = '<strong>' + row.s + '</strong> <span class="text-muted">' + row.n + '</span>';
        li.addEventListener('mousedown', function (e) { e.preventDefault(); doAdd(row.s); });
        dropdown.appendChild(li);
      });
      dropdown.style.display = '';
    }

    input.addEventListener('input', function () {
      showSuggestions(input.value.trim().toUpperCase());
    });
    input.addEventListener('blur', function () {
      setTimeout(function () { dropdown.style.display = 'none'; }, 150);
    });

    function doAddFromInput() {
      var sym = input.value.trim().toUpperCase();
      if (!sym) return;
      if (!state.lookupArr.find(function (r) { return r.s === sym; })) {
        if (errorEl) errorEl.textContent = 'Unknown ticker: ' + sym;
        return;
      }
      doAdd(sym);
    }

    addBtn.addEventListener('click', doAddFromInput);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); doAddFromInput(); }
    });
  }

  function doAdd(sym) {
    var input = document.getElementById('wl-ticker-input');
    var errorEl = document.getElementById('wl-add-error');
    var wl = activeWatchlist();
    log('doAdd', { sym: sym, activeWatchlist: wl ? wl.name : null });
    if (!wl) { log('doAdd:warn', 'no active watchlist'); return; }
    if (errorEl) errorEl.textContent = '';
    var tickers = (wl.tickers || []).slice();
    if (tickers.includes(sym)) {
      if (errorEl) errorEl.textContent = sym + ' already in watchlist';
      return;
    }
    tickers.push(sym);
    updateWatchlist(wl.watchlist_id, { tickers: tickers }).then(function (updated) {
      log('doAdd:done', { sym: sym, updatedTickers: updated.tickers });
      wl.tickers = updated.tickers;
      if (input) input.value = '';
      renderChips(wl);
      renderTable(wl);
      renderRadar(wl);
      renderHeatmap(wl);
    }).catch(function (err) {
      log('doAdd:error', String(err));
      if (errorEl) errorEl.textContent = 'Failed to add ' + sym;
    });
  }

  function removeTicker(sym) {
    var wl = activeWatchlist();
    log('removeTicker', { sym: sym, wl: wl ? wl.name : null });
    if (!wl) return;
    var tickers = (wl.tickers || []).filter(function (s) { return s !== sym; });
    updateWatchlist(wl.watchlist_id, { tickers: tickers }).then(function (updated) {
      log('removeTicker:done', updated.tickers);
      wl.tickers = updated.tickers;
      renderChips(wl);
      renderTable(wl);
      renderRadar(wl);
      renderHeatmap(wl);
    });
  }

  // ── Modal (new / rename) ───────────────────────────────────────────────────
  var modalMode = 'new';

  function closeModal() {
    bootstrap.Modal.getOrCreateInstance(document.getElementById('wl-name-modal')).hide();
  }

  function openModal(mode) {
    log('openModal', mode);
    modalMode = mode;
    var title = document.getElementById('wl-modal-title');
    var nameInput = document.getElementById('wl-name-input');
    var errorEl = document.getElementById('wl-modal-error');
    if (title) title.textContent = mode === 'new' ? 'New Watchlist' : 'Rename Watchlist';
    if (nameInput) nameInput.value = mode === 'rename' ? ((activeWatchlist() || {}).name || '') : '';
    if (errorEl) errorEl.style.display = 'none';
    bootstrap.Modal.getOrCreateInstance(document.getElementById('wl-name-modal')).show();
    setTimeout(function () { if (nameInput) nameInput.focus(); }, 300);
  }

  function bindModal() {
    var saveBtn = document.getElementById('wl-modal-save');
    if (!saveBtn) return;
    saveBtn.addEventListener('click', function () {
      var nameInput = document.getElementById('wl-name-input');
      var errorEl = document.getElementById('wl-modal-error');
      var name = (nameInput ? nameInput.value : '').trim();
      log('modal:save', { mode: modalMode, name: name });
      if (!name) {
        if (errorEl) { errorEl.textContent = 'Name required'; errorEl.style.display = ''; }
        return;
      }
      if (errorEl) errorEl.style.display = 'none';
      if (modalMode === 'new') {
        createWatchlist(name).then(function (wl) {
          log('modal:created', wl);
          state.watchlists.push(wl);
          closeModal();
          selectWatchlist(wl.watchlist_id);
        }).catch(function (err) {
          log('modal:createError', String(err));
          if (errorEl) { errorEl.textContent = 'Failed to create watchlist'; errorEl.style.display = ''; }
        });
      } else {
        var wl = activeWatchlist();
        if (!wl) return;
        updateWatchlist(wl.watchlist_id, { name: name }).then(function (updated) {
          log('modal:renamed', updated);
          wl.name = updated.name;
          closeModal();
          renderSidebar();
          var nameEl = document.getElementById('wl-detail-name');
          if (nameEl) nameEl.textContent = wl.name;
        }).catch(function (err) {
          log('modal:renameError', String(err));
          if (errorEl) { errorEl.textContent = 'Failed to rename'; errorEl.style.display = ''; }
        });
      }
    });
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  function init(config) {
    ProAuth.requireLogin();
    cfg = config || {};
    log('init', { apiBase: cfg.apiBase, scoresUrl: cfg.scoresUrl });

    var spinner = document.getElementById('wl-spinner');
    var emptyEl = document.getElementById('wl-empty');
    var detail = document.getElementById('wl-detail');

    document.getElementById('wl-new-btn') &&
      document.getElementById('wl-new-btn').addEventListener('click', function () { openModal('new'); });
    document.getElementById('wl-empty-new-btn') &&
      document.getElementById('wl-empty-new-btn').addEventListener('click', function () { openModal('new'); });
    document.getElementById('wl-rename-btn') &&
      document.getElementById('wl-rename-btn').addEventListener('click', function () { openModal('rename'); });

    var deleteBtn = document.getElementById('wl-delete-btn');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', function () {
        var wl = activeWatchlist();
        if (!wl || !window.confirm('Delete "' + wl.name + '"?')) return;
        log('deleteWatchlist:confirm', wl.name);
        deleteWatchlist(wl.watchlist_id).then(function () {
          state.watchlists = state.watchlists.filter(function (w) { return w.watchlist_id !== wl.watchlist_id; });
          state.activeId = state.watchlists.length ? state.watchlists[0].watchlist_id : null;
          log('deleteWatchlist:removed', { remaining: state.watchlists.length });
          renderSidebar();
          renderDetail();
        });
      });
    }

    bindModal();
    initAddWidget();

    log('init:loading');
    Promise.all([loadWatchlists(), loadScores(), loadLookup()])
      .then(function () {
        log('init:loaded', { watchlists: state.watchlists.length, scores: Object.keys(state.scores).length, lookup: state.lookupArr.length });
        if (spinner) spinner.style.display = 'none';
        if (state.watchlists.length > 0) {
          state.activeId = state.watchlists[0].watchlist_id;
          log('init:selectFirst', state.activeId);
          renderSidebar();
          renderDetail();
        } else {
          log('init:noWatchlists');
          if (emptyEl) emptyEl.style.display = '';
          if (detail) detail.style.display = 'none';
          renderSidebar();
        }
      })
      .catch(function (err) {
        log('init:error', String(err));
        if (spinner) spinner.style.display = 'none';
        if (emptyEl) {
          emptyEl.style.display = '';
          emptyEl.innerHTML = '<p class="text-danger text-center">Failed to load dashboard. Please refresh.</p>';
        }
      });
  }

  window.ProDashboard = { init: init };

  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('wl-spinner')) return;
    var emailEl = document.getElementById('pro-email');
    if (emailEl) emailEl.textContent = ProAuth.getEmail() || '';
    var signout = document.getElementById('signout-link');
    if (signout) signout.addEventListener('click', function (e) {
      e.preventDefault();
      ProAuth.logout();
    });
    init({
      apiBase:   window.SMW_PRO_API_BASE || '',
      scoresUrl: (window.SITE_BASE_URL || '/') + 'data/pro-scores.json',
      lookupUrl: (window.SITE_BASE_URL || '/') + 'data/ticker-lookup.json',
    });
  });
})();
