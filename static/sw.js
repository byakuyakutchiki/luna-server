// Luna Service Worker — Offline cache + push notifications
var CACHE_NAME = "luna-v50";
var PRECACHE_URLS = [
  "/",
  "/guardian",
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

// Activate: clean old caches + claim clients immediately
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

// Listen for messages from the app
self.addEventListener("message", function(event) {
  if (!event.data) return;
  if (event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
  // PURGE_CACHE: vide tout le cache SW immediatement
  if (event.data.type === "PURGE_CACHE") {
    caches.keys().then(function(names) {
      return Promise.all(names.map(function(n) { return caches.delete(n); }));
    }).then(function() {
      // Notifie tous les clients que le cache est purgé
      self.clients.matchAll().then(function(clients) {
        clients.forEach(function(c) { c.postMessage({ type: "CACHE_PURGED" }); });
      });
    });
  }
});

// Fetch strategy:
// - API/WS/SSE: never cache (passthrough)
// - HTML pages (navigate): network-first (always get latest)
// - Other static assets: cache-first with network fallback
self.addEventListener("fetch", function(event) {
  var url = new URL(event.request.url);

  // Never cache API calls, WebSocket, SSE, or clear-cache page
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/") ||
      url.pathname === "/clear-cache" || url.pathname === "/simli" ||
      event.request.headers.get("accept") === "text/event-stream") {
    return;
  }

  // HTML pages (navigation): NETWORK-FIRST — always serve fresh
  if (event.request.mode === "navigate" ||
      url.pathname === "/" ||
      url.pathname.endsWith(".html")) {
    event.respondWith(
      fetch(event.request).then(function(response) {
        if (response.ok) {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
        }
        return response;
      }).catch(function() {
        return caches.match(event.request).then(function(cached) {
          return cached || caches.match("/static/index.html");
        });
      })
    );
    return;
  }

  // Other static assets: cache-first with network fallback
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      if (cached) return cached;
      return fetch(event.request).then(function(response) {
        if (response.ok && response.status !== 206 && event.request.method === "GET" &&
            url.pathname.startsWith("/static/")) {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
        }
        return response;
      });
    }).catch(function() {
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
