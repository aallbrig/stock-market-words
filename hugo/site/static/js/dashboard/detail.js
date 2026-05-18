import { state, log } from './state.js';
import { updateWatchlist } from './api.js';
import { renderRadar, renderHeatmap } from './charts.js';

export function activeWatchlist() {
  return state.watchlists.find(w => w.watchlist_id === state.activeId);
}

export function renderDetail() {
  const wl = activeWatchlist();
  log('renderDetail', { activeId: state.activeId, wl: wl ? wl.name : null, tickers: wl ? (wl.tickers || []).length : 0 });
  const emptyEl = document.getElementById('wl-empty');
  const detail = document.getElementById('wl-detail');

  if (!state.activeId || !wl) {
    log('renderDetail:empty-state', 'no active watchlist');
    if (emptyEl) emptyEl.style.display = '';
    if (detail) detail.style.display = 'none';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  if (detail) detail.style.display = '';

  const nameEl = document.getElementById('wl-detail-name');
  if (nameEl) nameEl.textContent = wl.name;

  renderChips(wl);
  renderTable(wl);
  renderRadar(wl);
  renderHeatmap(wl);
}

export function renderChips(wl) {
  const container = document.getElementById('wl-tickers');
  if (!container) return;
  container.innerHTML = '';
  (wl.tickers || []).forEach(sym => {
    const chip = document.createElement('span');
    chip.className = 'badge bg-secondary d-inline-flex align-items-center gap-1';
    chip.innerHTML =
      '<span>' + sym + '</span>' +
      '<button type="button" class="btn-close btn-close-white btn-sm" aria-label="Remove"></button>';
    chip.querySelector('button').addEventListener('click', () => removeTicker(sym));
    container.appendChild(chip);
  });
}

function fmtScore(v) { return v != null ? v : '—'; }
function fmtPct(v) { return v != null ? (v >= 0 ? '+' : '') + v.toFixed(2) + '%' : '—'; }
function fmtPrice(v) { return v != null ? '$' + v.toFixed(2) : '—'; }

export function renderTable(wl) {
  const tbody = document.getElementById('wl-table-body');
  const tfoot = document.getElementById('wl-table-foot');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (tfoot) tfoot.innerHTML = '';
  const tickers = wl.tickers || [];
  if (tickers.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-3">No tickers yet — search above to add one.</td></tr>';
    return;
  }

  const scoreKeys = ['p', 'pc', 'dd', 'ms', 'fk', 'oh', 'iw', 'rr'];
  const sums = {}, counts = {};
  scoreKeys.forEach(k => { sums[k] = 0; counts[k] = 0; });

  tickers.forEach(sym => {
    const sc = state.scores[sym] || {};
    const tr = document.createElement('tr');
    const pcClass = sc.pc > 0 ? 'text-success' : sc.pc < 0 ? 'text-danger' : '';
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
    tr.querySelector('button').addEventListener('click', () => removeTicker(sym));
    tbody.appendChild(tr);

    scoreKeys.forEach(k => {
      if (sc[k] != null) { sums[k] += sc[k]; counts[k]++; }
    });
  });

  if (tfoot && tickers.length > 1) {
    const avg = k => counts[k] > 0 ? sums[k] / counts[k] : null;
    const avgPc = avg('pc');
    const avgPcClass = avgPc > 0 ? 'text-success' : avgPc < 0 ? 'text-danger' : '';
    const fmtAvgScore = k => { const v = avg(k); return v != null ? Math.round(v).toString() : '—'; };
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

function refreshDetail(wl) {
  renderChips(wl);
  renderTable(wl);
  renderRadar(wl);
  renderHeatmap(wl);
}

export function initAddWidget() {
  const input = document.getElementById('wl-ticker-input');
  const addBtn = document.getElementById('wl-add-btn');
  const wrapper = document.getElementById('wl-add-wrapper');
  const errorEl = document.getElementById('wl-add-error');
  if (!input || !addBtn || !wrapper) return;

  const dropdown = document.createElement('ul');
  dropdown.className = 'list-group position-absolute w-100 shadow-sm';
  dropdown.style.cssText = 'top:100%;left:0;z-index:1000;max-height:200px;overflow-y:auto;display:none;';
  wrapper.appendChild(dropdown);

  function showSuggestions(q) {
    dropdown.innerHTML = '';
    if (!q) { dropdown.style.display = 'none'; return; }
    const wl = activeWatchlist();
    const existing = wl ? (wl.tickers || []) : [];
    const hits = state.lookupArr.filter(row => row.s.startsWith(q) && !existing.includes(row.s)).slice(0, 10);
    if (!hits.length) { dropdown.style.display = 'none'; return; }
    hits.forEach(row => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action py-1 px-2 small';
      li.innerHTML = '<strong>' + row.s + '</strong> <span class="text-muted">' + row.n + '</span>';
      li.addEventListener('mousedown', e => { e.preventDefault(); doAdd(row.s); });
      dropdown.appendChild(li);
    });
    dropdown.style.display = '';
  }

  input.addEventListener('input', () => showSuggestions(input.value.trim().toUpperCase()));
  input.addEventListener('blur', () => setTimeout(() => { dropdown.style.display = 'none'; }, 150));

  function doAddFromInput() {
    const sym = input.value.trim().toUpperCase();
    if (!sym) return;
    if (!state.lookupArr.find(r => r.s === sym)) {
      if (errorEl) errorEl.textContent = 'Unknown ticker: ' + sym;
      return;
    }
    doAdd(sym);
  }

  addBtn.addEventListener('click', doAddFromInput);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); doAddFromInput(); } });
}

function doAdd(sym) {
  const input = document.getElementById('wl-ticker-input');
  const errorEl = document.getElementById('wl-add-error');
  const wl = activeWatchlist();
  log('doAdd', { sym, activeWatchlist: wl ? wl.name : null });
  if (!wl) { log('doAdd:warn', 'no active watchlist'); return; }
  if (errorEl) errorEl.textContent = '';
  const tickers = (wl.tickers || []).slice();
  if (tickers.includes(sym)) {
    if (errorEl) errorEl.textContent = sym + ' already in watchlist';
    return;
  }
  tickers.push(sym);
  updateWatchlist(wl.watchlist_id, { tickers }).then(updated => {
    log('doAdd:done', { sym, updatedTickers: updated.tickers });
    wl.tickers = updated.tickers;
    if (input) input.value = '';
    refreshDetail(wl);
  }).catch(err => {
    log('doAdd:error', String(err));
    if (errorEl) errorEl.textContent = 'Failed to add ' + sym;
  });
}

function removeTicker(sym) {
  const wl = activeWatchlist();
  log('removeTicker', { sym, wl: wl ? wl.name : null });
  if (!wl) return;
  const tickers = (wl.tickers || []).filter(s => s !== sym);
  updateWatchlist(wl.watchlist_id, { tickers }).then(updated => {
    log('removeTicker:done', updated.tickers);
    wl.tickers = updated.tickers;
    refreshDetail(wl);
  });
}
