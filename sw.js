const CACHE_NAME = 'seztools-v2';
const CORE_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './pump-module.html',
  './linesizing-module.html',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './vendor/react.production.min.js',
  './vendor/react-dom.production.min.js',
  './vendor/babel.min.js',
  './vendor/xlsx.full.min.js',
  './vendor/jspdf.umd.min.js',
  './vendor/fonts/jetbrains-mono-latin-400-normal.woff2',
  './vendor/fonts/jetbrains-mono-latin-600-normal.woff2',
  './vendor/fonts/jetbrains-mono-latin-700-normal.woff2'
];

// Install: pre-cache everything the app needs to run fully offline.
self.addEventListener('install', function(event){
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache){
      return cache.addAll(CORE_ASSETS);
    }).then(function(){
      return self.skipWaiting();
    })
  );
});

// Activate: drop old caches from previous versions.
self.addEventListener('activate', function(event){
  event.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(
        keys.filter(function(k){ return k !== CACHE_NAME; })
            .map(function(k){ return caches.delete(k); })
      );
    }).then(function(){
      return self.clients.claim();
    })
  );
});

// Fetch: cache-first, so the app opens instantly with zero network calls
// once installed. Falls back to network only if something wasn't cached,
// and updates the cache in the background when it does hit the network.
self.addEventListener('fetch', function(event){
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(function(cached){
      if (cached) return cached;

      return fetch(event.request).then(function(response){
        if (response && response.status === 200 && response.type === 'basic'){
          var copy = response.clone();
          caches.open(CACHE_NAME).then(function(cache){
            cache.put(event.request, copy);
          });
        }
        return response;
      }).catch(function(){
        // No cache, no network — nothing more we can do for this request.
        return cached;
      });
    })
  );
});
