const CACHE = 'astra-v3';
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

// ── Push notifications ────────────────────────────────────────
self.addEventListener('push', e => {
  let data = { title: 'Astra', body: 'Napisała do Ciebie.' };
  try {
    data = e.data.json();
  } catch {}

  e.waitUntil(
    Promise.all([
      // Pokaż powiadomienie systemowe
      self.registration.showNotification(data.title || 'Astra', {
        body: data.body || '',
        icon: '/astra.jpg',
        badge: '/astra.jpg',
        vibrate: [200, 100, 200],
        tag: 'astra-message',
        renotify: true,
      }),
      // Jeśli aplikacja jest otwarta w tle — wyślij wiadomość do UI
      clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
        list.forEach(client => {
          client.postMessage({ type: 'ASTRA_MESSAGE', body: data.body });
        });
      }),
    ])
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      if (list.length > 0) return list[0].focus();
      return clients.openWindow('/');
    })
  );
});
