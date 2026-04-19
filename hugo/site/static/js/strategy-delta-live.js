// strategy-delta-live.js
// Listens for strategy-spark:hover / strategy-spark:leave CustomEvents
// dispatched by strategy-sparklines.js and updates the delta chip badge
// to show the delta between today's score and the hovered data point.
// Reverts to the server-rendered default on mouse-leave.
//
// Fully decoupled: if sparklines are disabled (no events fire), this
// script is inert. If delta chips are disabled (no .strategy-delta in
// DOM), the event listeners are never attached.

(function () {
  function init() {
    var rows = document.querySelectorAll('.strategy-row');
    for (var i = 0; i < rows.length; i++) {
      bindRow(rows[i]);
    }
  }

  function bindRow(row) {
    var chip = row.querySelector('.strategy-delta');
    if (!chip) return;

    var latestScore = parseInt(chip.dataset.latestScore, 10);
    if (isNaN(latestScore)) return;

    var originalHTML = chip.innerHTML;
    var originalClassName = chip.className;
    var originalTitle = chip.getAttribute('title') || '';

    row.addEventListener('strategy-spark:hover', function (e) {
      var d = e.detail;
      if (d.score === null || d.score === undefined) return;
      var delta = latestScore - d.score;
      chip.innerHTML = formatDelta(delta);
      chip.className = deltaClassName(delta);
      chip.setAttribute('title', 'vs ' + d.date);
    });

    row.addEventListener('strategy-spark:leave', function () {
      chip.innerHTML = originalHTML;
      chip.className = originalClassName;
      chip.setAttribute('title', originalTitle);
    });
  }

  function formatDelta(delta) {
    if (delta > 0) return '▲ +' + delta;
    if (delta < 0) return '▼ ' + delta;
    return '— 0';
  }

  function deltaClassName(delta) {
    var base = 'strategy-delta badge rounded-pill ms-2 align-middle';
    if (delta > 0) return base + ' bg-success-subtle text-success-emphasis';
    if (delta < 0) return base + ' bg-danger-subtle text-danger-emphasis';
    return base + ' bg-secondary-subtle text-muted';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
