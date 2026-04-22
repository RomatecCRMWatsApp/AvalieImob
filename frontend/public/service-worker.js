// @module service-worker — Network-first, minimal caching
/* eslint-disable no-restricted-globals */

const CACHE_NAME = 'avalieimob-v3';

// Install: skip waiting immediately
self.addEventListener('install', () => self.skipWaiting());

// Activate: delete ALL old caches, claim clients
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch: network-first for everything, no caching of API or HTML
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  if (!new URL(request.url).protocol.startsWith('http')) return;

  // API and navigation: always network
  const url = new URL(request.url);
  if (url.pathname.startsWith('/api') || request.mode === 'navigate') {
    return; // let browser handle normally
  }

  // Static assets only: cache with network fallback
  if (url.pathname.match(/\.(js|css|png|jpg|svg|woff2?)$/)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
  }
});

// Push notifications
self.addEventListener('push', (event) => {
  const data = event.data?.json() || { title: 'AvalieImob', body: 'Nova notificação' };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/brand/icone.png',
    })
  );
});
