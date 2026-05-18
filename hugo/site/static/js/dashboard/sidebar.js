import { state, log } from './state.js';
import { renderDetail } from './detail.js';

export function renderSidebar() {
  log('renderSidebar', { count: state.watchlists.length, activeId: state.activeId });
  const list = document.getElementById('wl-list');
  if (!list) { log('renderSidebar:warn', '#wl-list not found'); return; }
  list.innerHTML = '';
  state.watchlists.forEach(wl => {
    const btn = document.createElement('button');
    btn.className = 'btn btn-sm w-100 text-start px-3 py-2 rounded-0 border-0' +
      (wl.watchlist_id === state.activeId ? ' active bg-primary text-white' : '');
    btn.textContent = wl.name;
    btn.addEventListener('click', () => selectWatchlist(wl.watchlist_id));
    list.appendChild(btn);
  });
}

export function selectWatchlist(id) {
  log('selectWatchlist', id);
  state.activeId = id;
  renderSidebar();
  renderDetail();
}
