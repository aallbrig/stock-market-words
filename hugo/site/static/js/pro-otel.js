/**
 * pro-otel.js — minimal OpenTelemetry (OTLP/HTTP JSON) client for the Pro funnel.
 *
 * Emits the client half of the subscription conversion funnel as the SAME metric
 * the Go Lambdas use — smw.funnel.events{stage} → Prometheus smw_funnel_events_total
 * — plus a lightweight trace span per event (→ Tempo). No build step, no SDK: it
 * POSTs OTLP/JSON straight to the collector, so it drops into a static Hugo site.
 *
 * Gated on window.SMW_OTEL_ENDPOINT (set from the hugo `otelEndpoint` param). When
 * empty — i.e. production until we wire a collector — every call is a no-op.
 *
 * Funnel events are fire-and-forget and wrapped in try/catch: telemetry must never
 * block or break the subscribe flow. Email/PII is never sent as an attribute.
 *
 * API:  ProOtel.funnel('cta_click', { source: 'pricing' })
 */
(function () {
  'use strict';

  var ENDPOINT = (window.SMW_OTEL_ENDPOINT || '').replace(/\/$/, '');
  var SERVICE = 'smw-pro-web';

  function hex(bytes) {
    var a = new Uint8Array(bytes);
    (window.crypto || {}).getRandomValues
      ? window.crypto.getRandomValues(a)
      : a.forEach(function (_, i) { a[i] = Math.floor(Math.random() * 256); });
    return Array.prototype.map.call(a, function (b) {
      return ('0' + b.toString(16)).slice(-2);
    }).join('');
  }

  function attrs(stage, extra) {
    var out = [{ key: 'stage', value: { stringValue: stage } }];
    extra = extra || {};
    Object.keys(extra).forEach(function (k) {
      out.push({ key: k, value: { stringValue: String(extra[k]) } });
    });
    return out;
  }

  function post(path, body) {
    try {
      fetch(ENDPOINT + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        keepalive: true // survive the page navigation on checkout_redirect
      }).catch(function () {});
    } catch { /* never break UX for telemetry */ }
  }

  function resource() {
    return { attributes: [{ key: 'service.name', value: { stringValue: SERVICE } }] };
  }

  // Records one funnel event: a DELTA counter increment (collector converts to
  // cumulative for Prometheus) and a matching span.
  function funnel(stage, extra) {
    if (!ENDPOINT) return;
    var now = String(Date.now() * 1e6); // ms → ns
    var a = attrs(stage, extra);

    post('/v1/metrics', {
      resourceMetrics: [{
        resource: resource(),
        scopeMetrics: [{
          scope: { name: 'smw-pro/funnel' },
          metrics: [{
            name: 'smw.funnel.events',
            sum: {
              aggregationTemporality: 1, // DELTA
              isMonotonic: true,
              dataPoints: [{ asInt: '1', startTimeUnixNano: now, timeUnixNano: now, attributes: a }]
            }
          }]
        }]
      }]
    });

    post('/v1/traces', {
      resourceSpans: [{
        resource: resource(),
        scopeSpans: [{
          scope: { name: 'smw-pro/funnel' },
          spans: [{
            traceId: hex(16), spanId: hex(8), name: 'funnel.' + stage,
            kind: 1, startTimeUnixNano: now, endTimeUnixNano: now, attributes: a
          }]
        }]
      }]
    });
  }

  window.ProOtel = { funnel: funnel };
})();
