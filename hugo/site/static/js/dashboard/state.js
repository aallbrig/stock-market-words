export const state = {
  watchlists: [],
  activeId: null,
  scores: {},
  lookup: {},
  lookupArr: []
};

export function log(event, data) {
  console.log('[Dashboard]', event, data !== undefined ? data : '');
}
