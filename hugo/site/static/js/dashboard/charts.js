import { state, log } from './state.js';

const AXES = [
  { key: 'dd', label: 'Div Daddy' },
  { key: 'ms', label: 'Moon Shot' },
  { key: 'fk', label: 'Falling Knife' },
  { key: 'oh', label: 'Over Hyped' },
  { key: 'iw', label: 'Inst. Whale' },
  { key: 'rr', label: 'REIT Radar' }
];

export function renderRadar(wl) {
  const svgEl = document.getElementById('radar-chart');
  if (!svgEl || typeof d3 === 'undefined') return;
  d3.select(svgEl).selectAll('*').remove();

  const size = 260, cx = size / 2, cy = size / 2, r = 100;
  const n = AXES.length;
  const step = (2 * Math.PI) / n;
  const svg = d3.select(svgEl).attr('width', size).attr('height', size);

  [25, 50, 75, 100].forEach(pct => {
    const pts = AXES.map((_, i) => {
      const a = i * step - Math.PI / 2;
      return [cx + (r * pct / 100) * Math.cos(a), cy + (r * pct / 100) * Math.sin(a)];
    });
    svg.append('polygon')
      .attr('points', pts.map(p => p.join(',')).join(' '))
      .attr('fill', 'none').attr('stroke', '#dee2e6').attr('stroke-width', 1);
  });

  AXES.forEach((ax, i) => {
    const a = i * step - Math.PI / 2;
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

  const tickers = (wl.tickers || []).filter(s => state.scores[s]);
  log('renderRadar', { wl: wl.name, tickers: tickers.length, scoresAvailable: Object.keys(state.scores).length });
  if (tickers.length === 0) {
    svg.append('text').attr('x', cx).attr('y', cy)
      .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
      .attr('fill', '#adb5bd').attr('font-size', 12)
      .text('Add tickers to see radar');
    return;
  }

  const avgs = AXES.map(ax => {
    const vals = tickers
      .map(s => state.scores[s][ax.key])
      .filter(v => v != null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  });
  const poly = avgs.map((v, i) => {
    const a = i * step - Math.PI / 2;
    return [cx + (r * v / 100) * Math.cos(a), cy + (r * v / 100) * Math.sin(a)];
  });
  svg.append('polygon')
    .attr('points', poly.map(p => p.join(',')).join(' '))
    .attr('fill', 'rgba(13,110,253,0.2)').attr('stroke', '#0d6efd').attr('stroke-width', 2);
}

export function renderHeatmap(wl) {
  const container = document.getElementById('heatmap-chart');
  if (!container || typeof d3 === 'undefined') return;
  d3.select(container).selectAll('*').remove();

  const tickers = (wl.tickers || []).filter(s => state.scores[s] && state.scores[s].pc != null);
  log('renderHeatmap', { wl: wl.name, tickersWithPc: tickers.length });
  if (tickers.length === 0) {
    container.innerHTML = '<p class="text-center text-muted mt-3">Add tickers to see heatmap</p>';
    return;
  }

  const color = d3.scaleDiverging([-5, 0, 5], d3.interpolateRdYlGn);
  const cols = Math.min(tickers.length, 8);
  const tileW = Math.max(60, Math.floor((container.offsetWidth || 480) / cols));
  const tileH = 56;
  const rows = Math.ceil(tickers.length / cols);

  const svg = d3.select(container).append('svg')
    .attr('width', cols * tileW).attr('height', rows * tileH + 4);

  tickers.forEach((sym, i) => {
    const sc = state.scores[sym];
    const col = i % cols, row = Math.floor(i / cols);
    const g = svg.append('g').attr('transform', `translate(${col * tileW},${row * tileH})`);
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
