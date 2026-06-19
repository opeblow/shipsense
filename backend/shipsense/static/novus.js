(function () {
  'use strict';

  // currentScript works for the normal snippet; the querySelector fallback
  // covers programmatic injection (e.g. the demo page).
  var script = document.currentScript ||
    document.querySelector('script[src*="novus.js"][data-app-id]') ||
    document.querySelector('script[src*="novus.js"]');

  var apiUrl = (script && script.getAttribute('data-api-url')) ||
    (script && script.src ? new URL(script.src).origin : '');
  var appId = window._novusAppId || (script && script.getAttribute('data-app-id'));

  if (!apiUrl || !appId || appId === 'YOUR_APP_ID') {
    console.warn('[novus] missing/placeholder data-app-id or data-api-url — tracker idle');
    return;
  }
  var productId = parseInt(appId, 10);
  if (!productId) { console.warn('[novus] invalid app id'); return; }

  var ingestUrl = apiUrl.replace(/\/$/, '') + '/api/behavior/ingest';
  var STORAGE_KEY = 'novus_visitor_id';

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

  var queue = [];

  function enqueue(action, extra) {
    if (!action) return;
    var ev = { action: String(action).slice(0, 120), user_id: userId, timestamp: new Date().toISOString() };
    if (extra) ev.data = extra;
    queue.push(ev);
    if (queue.length >= 20) flush();
  }

  function flush() {
    if (!queue.length) return;
    var events = queue.splice(0, queue.length);
    try {
      // keepalive lets the request finish during page unload; CORS=* on the
      // backend allows the cross-origin preflight to succeed.
      fetch(ingestUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, events: events }),
        keepalive: true,
        mode: 'cors',
      }).catch(function () { /* fire-and-forget */ });
    } catch (e) { /* ignore */ }
  }

  // Public API (back-compat with window.Novus / window._novusQueue).
  function track(action, extra) { enqueue(action, extra); }
  window.Novus = { track: track, flush: flush };

  var pre = window._novusQueue || [];
  while (pre.length) {
    var item = pre.shift();
    if (typeof item === 'string') enqueue(item);
    else if (item && item.action) enqueue(item.action, item.data);
  }

  function labelFor(el) {
    var node = el;
    for (var i = 0; node && i < 4; i++) {
      if (node.getAttribute) {
        var tagged = node.getAttribute('data-novus');
        if (tagged) return tagged;
        var tag = (node.tagName || '').toLowerCase();
        if (tag === 'a' || tag === 'button' || node.getAttribute('role') === 'button') {
          var text = (node.innerText || node.textContent || '').trim().replace(/\s+/g, ' ');
          return 'click: ' + (text ? text.slice(0, 40) : tag);
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
