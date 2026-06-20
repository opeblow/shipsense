(function () {
  'use strict';

  // currentScript works for the normal snippet; the querySelector fallback
  // covers programmatic injection (e.g. the demo page).
  var script = document.currentScript ||
    document.querySelector('script[src*="shipsense-collector.js"][data-product-id]') ||
    document.querySelector('script[src*="shipsense-collector.js"]');

  var apiUrl = (script && script.getAttribute('data-api-url')) ||
    (script && script.src ? new URL(script.src).origin : '');
  var appId = window._shipsenseProductId ||
    (script && script.getAttribute('data-product-id'));
  var collectorKey = window._shipsenseCollectorKey ||
    (script && script.getAttribute('data-collector-key'));

  if (!apiUrl || !appId || !collectorKey || appId === 'YOUR_PRODUCT_ID') {
    console.warn('[ShipSense] missing product id, collector key, or API URL — collector idle');
    return;
  }
  var ingestUrl = apiUrl.replace(/\/$/, '') + '/api/behavior/ingest';
  var STORAGE_KEY = 'shipsense_visitor_id';
  var SESSION_KEY = 'shipsense_session';
  var SESSION_TIMEOUT_MS = 30 * 60 * 1000;

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'anon-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  // Persist an anonymous visitor id so the same person isn't counted as a new
  // user on every page load.
  var userId;
  try {
    userId = localStorage.getItem(STORAGE_KEY);
    if (!userId) { userId = uuid(); localStorage.setItem(STORAGE_KEY, userId); }
  } catch (e) { userId = uuid(); }

  function currentSessionId() {
    var now = Date.now();
    try {
      var stored = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
      if (!stored || !stored.id || now - stored.lastActivity >= SESSION_TIMEOUT_MS) {
        stored = { id: uuid(), lastActivity: now };
      } else {
        stored.lastActivity = now;
      }
      localStorage.setItem(SESSION_KEY, JSON.stringify(stored));
      return stored.id;
    } catch (e) {
      return uuid();
    }
  }

  var queue = [];
  var flushing = false;

  function enqueue(action, extra) {
    if (!action) return;
    var ev = {
      event_id: uuid(),
      schema_version: 1,
      action: String(action).slice(0, 120),
      user_id: userId,
      session_id: currentSessionId(),
      timestamp: new Date().toISOString(),
      page_url: location.origin + location.pathname,
      properties: extra && typeof extra === 'object' ? extra : {}
    };
    queue.push(ev);
    if (queue.length >= 20) flush();
  }

  function flush() {
    if (!queue.length || flushing) return;
    var events = queue.splice(0, queue.length);
    flushing = true;

    function restoreBatch() {
      queue = events.concat(queue).slice(0, 200);
    }

    try {
      // keepalive lets the request finish during page unload; CORS=* on the
      // backend allows the cross-origin preflight to succeed.
      fetch(ingestUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: String(appId),
          collector_key: collectorKey,
          events: events
        }),
        keepalive: true,
        mode: 'cors',
      }).then(function (response) {
        if (!response.ok) restoreBatch();
      }).catch(function () {
        restoreBatch();
      }).finally(function () {
        flushing = false;
      });
    } catch (e) {
      restoreBatch();
      flushing = false;
    }
  }

  // Public API for manually recording product-specific actions.
  function track(action, extra) { enqueue(action, extra); }
  window.ShipSense = { track: track, flush: flush };

  var pre = window._shipsenseQueue || [];
  while (pre.length) {
    var item = pre.shift();
    if (typeof item === 'string') enqueue(item);
    else if (item && item.action) enqueue(item.action, item.data);
  }

  function labelFor(el) {
    var node = el;
    for (var i = 0; node && i < 4; i++) {
      if (node.getAttribute) {
        var tagged = node.getAttribute('data-shipsense');
        if (tagged) return tagged;
        var tag = (node.tagName || '').toLowerCase();
        if (tag === 'a' || tag === 'button' || node.getAttribute('role') === 'button') {
          var stableName = node.getAttribute('id') || node.getAttribute('name');
          return stableName ? 'click: ' + tag + '#' + stableName.slice(0, 40) : 'click: ' + tag;
        }
      }
      node = node.parentNode;
    }
    return null;
  }

  function pageview() { enqueue('view ' + (location.pathname || '/')); }

  document.addEventListener('click', function (e) {
    var label = labelFor(e.target);
    if (label) enqueue(label);
  }, true);

  // SPA navigations
  var push = history.pushState;
  history.pushState = function () { var r = push.apply(this, arguments); pageview(); return r; };
  window.addEventListener('popstate', pageview);

  // Flush on hide + on a steady interval
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') flush(); });
  window.addEventListener('pagehide', flush);
  setInterval(flush, 5000);

  pageview();
})();
// v2 — persistent visitor id, batching, keepalive flush
