// @module service-worker — App Shell + API Cache + Background Sync
/* eslint-disable no-restricted-globals */

const CACHE_NAME = 'avalieimob-v2';
const API_CACHE = 'avalieimob-api-v2';
const SYNC_TAG = 'avalieimob-sync-tvi';

const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
  '/brand/icone.png',
  '/brand/logo_principal.png',
];

// Install: pre-cache App Shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(APP_SHELL).catch(() => {})
    ).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME && k !== API_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch: stale-while-revalidate for assets, network-first for API
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and chrome-extension
  if (request.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  // API routes: network-first, fallback to cache
  if (url.pathname.startsWith('/api/tvi')) {
    event.respondWith(networkFirstAPI(request));
    return;
  }

  // Static assets: stale-while-revalidate
  event.respondWith(staleWhileRevalidate(request));
});

async function networkFirstAPI(request) {
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response(JSON.stringify({ offline: true, data: [] }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const fetchPromise = fetch(request.clone())
    .then((response) => {
      if (response.ok) {
        caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
      }
      return response;
    })
    .catch(() => null);

  return cached || (await fetchPromise) || new Response('Offline', { status: 503 });
}

// Background Sync: retry pending TVI vistorias
self.addEventListener('sync', (event) => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(syncPendingVistorias());
  }
});

async function syncPendingVistorias() {
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_PENDING' });
  });
}

// Push: notify
self.addEventListener('push', (event) => {
  const data = event.data?.json() || { title: 'AvalieImob', body: 'Nova notificação' };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/brand/icone.png',
    })
  );
});
