import { configure, loadWatchlists, loadScores, loadLookup, deleteWatchlist } from './api.js';
import { state, log } from './state.js';
import { renderSidebar } from './sidebar.js';
import { renderDetail, initAddWidget } from './detail.js';
import { openModal, bindModal } from './modal.js';

function init(config) {
  ProAuth.requireLogin();
  configure(config);
  log('init', { apiBase: config.apiBase, scoresUrl: config.scoresUrl });

  const spinner = document.getElementById('wl-spinner');
  const emptyEl = document.getElementById('wl-empty');
  const detail = document.getElementById('wl-detail');

  document.getElementById('wl-new-btn')?.addEventListener('click', () => openModal('new'));
  document.getElementById('wl-empty-new-btn')?.addEventListener('click', () => openModal('new'));
  document.getElementById('wl-rename-btn')?.addEventListener('click', () => openModal('rename'));

  const deleteBtn = document.getElementById('wl-delete-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => {
      const wl = state.watchlists.find(w => w.watchlist_id === state.activeId);
      if (!wl || !window.confirm('Delete "' + wl.name + '"?')) return;
      log('deleteWatchlist:confirm', wl.name);
      deleteWatchlist(wl.watchlist_id).then(() => {
        state.watchlists = state.watchlists.filter(w => w.watchlist_id !== wl.watchlist_id);
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
    .then(() => {
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
    .catch(err => {
      log('init:error', String(err));
      if (spinner) spinner.style.display = 'none';
      if (emptyEl) {
        emptyEl.style.display = '';
        emptyEl.innerHTML = '<p class="text-danger text-center">Failed to load dashboard. Please refresh.</p>';
      }
    });
}

document.addEventListener('DOMContentLoaded', () => {
  if (!document.getElementById('wl-spinner')) return;
  const emailEl = document.getElementById('pro-email');
  if (emailEl) emailEl.textContent = ProAuth.getEmail() || '';
  const signout = document.getElementById('signout-link');
  if (signout) signout.addEventListener('click', e => { e.preventDefault(); ProAuth.logout(); });
  init({
    apiBase:   window.SMW_PRO_API_BASE || '',
    scoresUrl: (window.SITE_BASE_URL || '/') + 'data/pro-scores.json',
    lookupUrl: (window.SITE_BASE_URL || '/') + 'data/ticker-lookup.json',
  });
});
