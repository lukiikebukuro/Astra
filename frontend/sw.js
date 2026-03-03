const CACHE = 'astra-v1';
const SHELL = ['/', '/style.css', '/app.js', '/astra.jpg', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API — zawsze sieć (nigdy cache)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Shell — cache-first, fallback do sieci
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
