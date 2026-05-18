import { state, log } from './state.js';
import { createWatchlist, updateWatchlist } from './api.js';
import { selectWatchlist, renderSidebar } from './sidebar.js';
import { activeWatchlist } from './detail.js';

let modalMode = 'new';

function closeModal() {
  bootstrap.Modal.getOrCreateInstance(document.getElementById('wl-name-modal')).hide();
}

export function openModal(mode) {
  log('openModal', mode);
  modalMode = mode;
  const title = document.getElementById('wl-modal-title');
  const nameInput = document.getElementById('wl-name-input');
  const errorEl = document.getElementById('wl-modal-error');
  if (title) title.textContent = mode === 'new' ? 'New Watchlist' : 'Rename Watchlist';
  if (nameInput) nameInput.value = mode === 'rename' ? ((activeWatchlist() || {}).name || '') : '';
  if (errorEl) errorEl.style.display = 'none';
  bootstrap.Modal.getOrCreateInstance(document.getElementById('wl-name-modal')).show();
  setTimeout(() => { if (nameInput) nameInput.focus(); }, 300);
}

export function bindModal() {
  const saveBtn = document.getElementById('wl-modal-save');
  if (!saveBtn) return;
  saveBtn.addEventListener('click', () => {
    const nameInput = document.getElementById('wl-name-input');
    const errorEl = document.getElementById('wl-modal-error');
    const name = (nameInput ? nameInput.value : '').trim();
    log('modal:save', { mode: modalMode, name });
    if (!name) {
      if (errorEl) { errorEl.textContent = 'Name required'; errorEl.style.display = ''; }
      return;
    }
    if (errorEl) errorEl.style.display = 'none';
    if (modalMode === 'new') {
      createWatchlist(name).then(wl => {
        log('modal:created', wl);
        state.watchlists.push(wl);
        closeModal();
        selectWatchlist(wl.watchlist_id);
      }).catch(err => {
        log('modal:createError', String(err));
        if (errorEl) { errorEl.textContent = 'Failed to create watchlist'; errorEl.style.display = ''; }
      });
    } else {
      const wl = activeWatchlist();
      if (!wl) return;
      updateWatchlist(wl.watchlist_id, { name }).then(updated => {
        log('modal:renamed', updated);
        wl.name = updated.name;
        closeModal();
        renderSidebar();
        const nameEl = document.getElementById('wl-detail-name');
        if (nameEl) nameEl.textContent = wl.name;
      }).catch(err => {
        log('modal:renameError', String(err));
        if (errorEl) { errorEl.textContent = 'Failed to rename'; errorEl.style.display = ''; }
      });
    }
  });
}
