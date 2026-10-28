/**
 * Raktsetu Service Worker
 * Precaches core application shell and provides runtime caching for API queries
 * with offline fallback support.
 */

const CACHE_NAME = 'raktsetu-shell-v5';
const DATA_CACHE_NAME = 'raktsetu-data-v5';

const APP_SHELL_FILES = [
  '/',
  '/css/style.css',
  '/js/app.js',
  '/manifest.json',
  '/assets/icon-192.svg',
  '/assets/icon-512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL_FILES);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME && key !== DATA_CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API Requests: Network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(DATA_CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            return new Response(JSON.stringify({
              error: 'offline',
              message: 'Offline mode active. No cached response available for this query.'
            }), {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }

  // App Shell: Network-first so code updates reach returning visitors; cache when offline
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache the shell plus CDN libraries/fonts (not map tiles, which would bloat the cache)
        const cacheable = APP_SHELL_FILES.includes(url.pathname) ||
          (url.origin !== self.location.origin && !url.hostname.includes('basemaps'));
        if ((response.ok || response.type === 'opaque') && cacheable) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
