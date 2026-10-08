const CACHE_NAME = 'ultron-livelink-v20261008-a';
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
            console.log("Deleting old cache:", cacheName);
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
  
  // Strict Network-first for ALL assets to ensure UI updates show immediately
  event.respondWith(
      fetch(event.request, { cache: 'no-store' })
      .then((response) => {
          // Cache the latest version if successful
          if (response && response.status === 200 && response.type === 'basic') {
              const responseToCache = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                  cache.put(event.request, responseToCache);
              });
          }
          return response;
      })
      .catch(() => caches.match(event.request))
  );
});
