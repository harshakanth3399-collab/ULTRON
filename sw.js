const CACHE_NAME = 'ultron-livelink-v2';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Network-first with cache-busting for HTML
  if (event.request.mode === 'navigate' || event.request.url.includes('index.html')) {
      event.respondWith(
          fetch(event.request, { cache: 'no-cache' })
          .catch(() => caches.match(event.request))
      );
      return;
  }

  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
