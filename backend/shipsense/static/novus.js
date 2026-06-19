(function() {
  'use strict';

  var script = document.currentScript;
  var apiUrl = script && script.getAttribute('data-api-url');
  var appId = window._novusAppId || (script && script.getAttribute('data-app-id'));
  var queue = window._novusQueue || [];
  var userId = 'anon-' + Math.random().toString(36).slice(2, 10);

  function sendEvents(events) {
    if (!apiUrl || !appId) return;
    var xhr = new XMLHttpRequest();
    xhr.open('POST', apiUrl + '/api/behavior/ingest', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify({
      product_id: parseInt(appId, 10) || appId,
      events: events
    }));
  }

  function track(action, extra) {
    var event = {
      action: action,
      user_id: userId,
      timestamp: new Date().toISOString()
    };
    if (extra) event.data = extra;
    sendEvents([event]);
  }

  function processQueue() {
    var batch = [];
    while (queue.length) {
      var item = queue.shift();
      if (typeof item === 'string') {
        batch.push({ action: item, user_id: userId, timestamp: new Date().toISOString() });
      } else if (item && item.action) {
        batch.push({ action: item.action, user_id: item.user_id || userId, timestamp: item.timestamp || new Date().toISOString() });
      }
    }
    if (batch.length) sendEvents(batch);
  }

  document.addEventListener('click', function(e) {
    var el = e.target;
    var label = el.getAttribute('data-novus') || el.tagName.toLowerCase() + (el.textContent ? ':' + el.textContent.trim().slice(0, 40) : '');
    track('click:' + label);
  }, true);

  window.addEventListener('beforeunload', function() {
    sendEvents([{ action: 'page_exit', user_id: userId, timestamp: new Date().toISOString() }]);
  });

  track('page_view:' + window.location.pathname);
  processQueue();

  window.Novus = { track: track, sendEvents: sendEvents };
})();
