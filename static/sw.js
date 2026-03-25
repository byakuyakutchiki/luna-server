// Luna Service Worker — Offline cache + push notifications
var CACHE_NAME = "luna-v1";
var PRECACHE_URLS = [
  "/",
  "/static/index.html",
  "/static/manifest.json"
];

// Install: precache shell
self.addEventListener("install", function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(PRECACHE_URLS);
    }).then(function() { self.skipWaiting(); })
  );
});

// Activate: clean old caches
self.addEventListener("activate", function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(n) { return n !== CACHE_NAME; })
             .map(function(n) { return caches.delete(n); })
      );
    }).then(function() { return self.clients.claim(); })
  );
});

// Fetch: network-first for API, cache-first for static
self.addEventListener("fetch", function(event) {
  var url = new URL(event.request.url);

  // Never cache API calls, WebSocket, or SSE streams
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/") ||
      event.request.headers.get("accept") === "text/event-stream") {
    return;
  }

  // Static assets: cache-first with network fallback
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      if (cached) return cached;
      return fetch(event.request).then(function(response) {
        // Cache successful GET responses for static files
        if (response.ok && event.request.method === "GET" &&
            (url.pathname.startsWith("/static/") || url.pathname === "/")) {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
        }
        return response;
      });
    }).catch(function() {
      // Offline fallback: serve cached index
      if (event.request.mode === "navigate") {
        return caches.match("/static/index.html");
      }
    })
  );
});

// Push notification handler
self.addEventListener("push", function(event) {
  var data = { title: "Luna", body: "Nouveau message", icon: "/static/assets/luna-icon-192.png" };
  try {
    if (event.data) data = Object.assign(data, event.data.json());
  } catch(e) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || "/static/assets/luna-icon-192.png",
      badge: "/static/assets/luna-icon-192.png",
      vibrate: [200, 100, 200],
      data: data
    })
  );
});

// Click on notification → open app
self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        if (clientList[i].url.indexOf("/") >= 0 && "focus" in clientList[i]) {
          return clientList[i].focus();
        }
      }
      return clients.openWindow("/");
    })
  );
});
