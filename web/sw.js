// Offline: siden virker uden net, når den først er åbnet. Filerne hentes fra cachen med det samme
// og opdateres i baggrunden, så næste besøg får den nyeste version.
const CACHE = "racetimer-lite";
const FILES = ["./", "index.html", "lite.js", "engine.js", "outcome.js", "display.html", "manifest.webmanifest",
               "static/style.css", "static/splash/racetiming.webp"];

self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); self.skipWaiting(); });
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;  // fx afsendelse til hjemmesiden
  e.respondWith(caches.open(CACHE).then(async cache => {
    const cached = await cache.match(e.request, {ignoreSearch: true});
    const fresh = fetch(e.request).then(res => { if (res.ok) cache.put(e.request, res.clone()); return res; }).catch(() => cached);
    return cached || fresh;
  }));
});
