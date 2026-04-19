// strategy-sparklines.js
// Renders a small Chart.js line chart for each <canvas.strategy-sparkline>
// on the ticker detail page, showing the last ~10 trading days of that
// strategy's 1-100 score. Gated upstream by Hugo site param
// enableStrategyHistoryChart — this file is not fetched when the flag is off.
//
// Chart.js is loaded separately (CDN) with `defer`; both scripts share the
// defer queue so Chart is defined by the time this runs after DOM parse.

(function () {
  function init() {
    if (typeof Chart === 'undefined') return;
    var canvases = document.querySelectorAll('canvas.strategy-sparkline');
    for (var i = 0; i < canvases.length; i++) renderOne(canvases[i]);
  }

  // External HTML tooltip: renders into the .sparkline-wrap parent as an
  // absolutely-positioned element so it can overflow the canvas bitmap
  // without being clipped. The positioner keeps it horizontally centered
  // over the active point and flips above/below based on available room.
  function externalTooltip(context) {
    var chart = context.chart;
    var wrap = chart.canvas.parentNode;
    var tip = wrap.querySelector('.sparkline-tooltip');
    if (!tip) {
      tip = document.createElement('div');
      tip.className = 'sparkline-tooltip';
      tip.style.cssText =
        'position:absolute;pointer-events:none;background:rgba(17,24,39,0.92);' +
        'color:#fff;border-radius:4px;padding:4px 8px;font-size:11px;' +
        'line-height:1.3;white-space:nowrap;opacity:0;transition:opacity 120ms;' +
        'transform:translate(-50%, 0);z-index:10';
      wrap.appendChild(tip);
    }

    var tt = context.tooltip;
    if (!tt || tt.opacity === 0) {
      tip.style.opacity = 0;
      return;
    }

    var title = (tt.title && tt.title[0]) || '';
    var body = (tt.body && tt.body[0] && tt.body[0].lines && tt.body[0].lines[0]) || '';
    tip.innerHTML =
      '<div style="font-weight:600">' + title + '</div>' +
      '<div>' + body + '</div>';

    // Position: centered horizontally on the caret, just above the point.
    // If that would push the tip off the top of the wrapper, drop it below.
    var canvasRect = chart.canvas.getBoundingClientRect();
    var wrapRect = wrap.getBoundingClientRect();
    var x = tt.caretX + (canvasRect.left - wrapRect.left);
    var yPoint = tt.caretY + (canvasRect.top - wrapRect.top);
    tip.style.opacity = 1;
    tip.style.left = x + 'px';

    var tipH = tip.offsetHeight;
    var above = yPoint - tipH - 8;
    if (above < 0) {
      tip.style.top = (yPoint + 8) + 'px';
    } else {
      tip.style.top = above + 'px';
    }
  }

  function renderOne(el) {
    var strategy = el.dataset.strategy;
    var color = el.dataset.color || '#0d6efd';
    var history = [];
    try {
      history = JSON.parse(el.dataset.history || '[]');
    } catch (e) { return; }
    if (!history.length) return;

    // Slice to the most recent N entries; data-window comes from the
    // Hugo site param strategySparklineWindow.
    var win = parseInt(el.dataset.window, 10);
    if (win > 0 && history.length > win) {
      history = history.slice(history.length - win);
    }

    var labels = history.map(function (row) { return row.date; });
    var scores = history.map(function (row) {
      var v = row[strategy];
      return (v === null || v === undefined) ? null : v;
    });

    var hasData = false;
    for (var j = 0; j < scores.length; j++) {
      if (scores[j] !== null) { hasData = true; break; }
    }
    if (!hasData) {
      // Hide the entire wrapper so the layout collapses cleanly.
      var wrap = el.parentNode;
      if (wrap && wrap.classList.contains('sparkline-wrap')) {
        wrap.style.display = 'none';
      } else {
        el.style.display = 'none';
      }
      return;
    }

    var row = el.closest('.strategy-row');

    new Chart(el, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          data: scores,
          borderColor: color,
          backgroundColor: color,
          borderWidth: 2.25,
          pointRadius: 2.5,
          pointHoverRadius: 5,
          pointBackgroundColor: color,
          pointBorderColor: color,
          tension: 0.3,
          fill: false,
          spanGaps: true,
        }],
      },
      options: {
        // Wrapper height is fixed (CSS), so responsive width resizing is
        // safe — no feedback loop.
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        // Breathing room around the line so points at the top/bottom of
        // the auto-scaled range aren't clipped by the canvas edge.
        layout: { padding: { top: 6, right: 4, bottom: 6, left: 4 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: false,
            external: externalTooltip,
            callbacks: {
              title: function (items) { return items[0].label; },
              label: function (item) {
                var y = item.raw;
                if (y === null || y === undefined) y = item.parsed && item.parsed.y;
                return (y === null || y === undefined) ? '—' : y + '/100';
              },
            },
          },
        },
        scales: {
          x: { display: false },
          y: { display: false },
        },
        interaction: { mode: 'nearest', intersect: false, axis: 'x' },
        onHover: function (_event, elements) {
          if (!row) return;
          if (elements.length > 0) {
            var idx = elements[0].index;
            var score = scores[idx];
            var date = labels[idx];
            if (score !== null && score !== undefined) {
              row.dispatchEvent(new CustomEvent('strategy-spark:hover', {
                bubbles: false,
                detail: { strategy: strategy, score: score, date: date }
              }));
            }
          } else {
            row.dispatchEvent(new CustomEvent('strategy-spark:leave', {
              bubbles: false,
              detail: { strategy: strategy }
            }));
          }
        },
      },
    });

    // Fallback: Chart.js onHover with empty elements can be unreliable
    // on fast mouse exits, so also listen for mouseleave on the canvas.
    el.addEventListener('mouseleave', function () {
      if (!row) return;
      row.dispatchEvent(new CustomEvent('strategy-spark:leave', {
        bubbles: false,
        detail: { strategy: strategy }
      }));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
