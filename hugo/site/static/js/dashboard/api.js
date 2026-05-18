import { state, log } from './state.js';

let cfg = {};

export function configure(config) {
  cfg = config;
}

function apiFetch(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  log('apiFetch', { method, path, body });
  return ProAuth.authFetch(cfg.apiBase + path, opts);
}

export function loadScores() {
  log('loadScores:start', cfg.scoresUrl);
  return fetch(cfg.scoresUrl)
    .then(r => r.json())
    .then(data => {
      state.scores = {};
      const tickers = data.tickers || data;
      tickers.forEach(row => { state.scores[row.s] = row; });
      log('loadScores:done', Object.keys(state.scores).length + ' tickers');
    })
    .catch(err => { log('loadScores:error', String(err)); throw err; });
}

export function loadLookup() {
  log('loadLookup:start', cfg.lookupUrl);
  return fetch(cfg.lookupUrl)
    .then(r => r.json())
    .then(data => {
      state.lookup = {};
      state.lookupArr = data.tickers || data;
      state.lookupArr.forEach(row => { state.lookup[row.s] = row.n; });
      log('loadLookup:done', state.lookupArr.length + ' symbols');
    })
    .catch(err => { log('loadLookup:error', String(err)); throw err; });
}

export function loadWatchlists() {
  log('loadWatchlists:start');
  return apiFetch('GET', '/pro/watchlists')
    .then(r => { log('loadWatchlists:http', r.status); return r.json(); })
    .then(data => {
      state.watchlists = data.watchlists || [];
      log('loadWatchlists:done', state.watchlists.map(w => ({
        id: w.watchlist_id, name: w.name, tickers: (w.tickers || []).length
      })));
    })
    .catch(err => { log('loadWatchlists:error', String(err)); throw err; });
}

export function createWatchlist(name) {
  log('createWatchlist', name);
  return apiFetch('POST', '/pro/watchlists', { name })
    .then(r => { log('createWatchlist:http', r.status); return r.json(); })
    .then(wl => { log('createWatchlist:done', wl); return wl; });
}

export function updateWatchlist(id, patch) {
  log('updateWatchlist', { id, patch });
  return apiFetch('PUT', '/pro/watchlists/' + id, patch)
    .then(r => { log('updateWatchlist:http', r.status); return r.json(); })
    .then(wl => {
      log('updateWatchlist:done', { id: wl.watchlist_id, tickers: (wl.tickers || []).length });
      return wl;
    });
}

export function deleteWatchlist(id) {
  log('deleteWatchlist', id);
  return apiFetch('DELETE', '/pro/watchlists/' + id)
    .then(r => { log('deleteWatchlist:http', r.status); return r; });
}
