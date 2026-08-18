// ASTRA — Service Worker: WYŁĄCZNIE powiadomienia push.
//
// Cache celowo usunięty. Serwis stoi za auth_basic, a fetch z kontekstu Service Workera
// nie niesie poświadczeń — precache padał na /app.js z 401, a `.catch(() => {})` połykał
// błąd w ciszy: instalacja "udawała się" z pustym cache, po czym cache-first serwował
// martwy kod przez wiele deployów z rzędu (dowód: access.log 16.07, GET /app.js 401
// z refererem /sw.js; telefon nie pobrał app.js ani razu mimo trzech wdrożeń).
// Offline i tak nie istnieje — bez backendu aplikacja jest bezużyteczna.
// NIE przywracać cache bez rozwiązania sprawy poświadczeń.

const CACHE_PREFIX = 'astra-';

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k.startsWith(CACHE_PREFIX)).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Brak handlera 'fetch' — żądania idą prosto do sieci, z poświadczeniami strony.

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
          // Do UI idzie PEŁNA treść (`full`), nie skrócone `body` powiadomienia.
          // Inaczej strona dokłada bąbelek z tekstem uciętym na 100 znakach, polling
          // dokłada drugi z pełnym — dwa różne teksty, więc dedup po hashu je przepuszcza.
          client.postMessage({ type: 'ASTRA_MESSAGE', body: data.full || data.body });
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
