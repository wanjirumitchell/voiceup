// VoiceUp Service Worker v2
// Caches static assets for fast loading and basic offline support

const CACHE_NAME = 'voiceup-v2';
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/submit',
  '/my-suggestions',
  '/notifications',
  '/static/css/style.css',
  '/manifest.json'
];

// Install — pre-cache key pages and assets
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Silently fail if any asset can't be cached (e.g. user not logged in)
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean up old caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch — Network first, fall back to cache
// API and admin routes always go to network (never cache)
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Skip non-GET, external requests, admin routes, and API calls
  if (
    e.request.method !== 'GET' ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith('/admin') ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/vote/') ||
    url.pathname.includes('logout')
  ) {
    return; // Let browser handle normally
  }

  e.respondWith(
    fetch(e.request)
      .then((response) => {
        // Cache successful responses for static assets
        if (response.ok && (
          url.pathname.startsWith('/static/') ||
          url.pathname === '/manifest.json'
        )) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Offline fallback — serve from cache
        return caches.match(e.request).then((cached) => {
          if (cached) return cached;
          // If it's a page request and we're offline, show offline message
          if (e.request.headers.get('accept')?.includes('text/html')) {
            return new Response(
              `<!DOCTYPE html>
              <html><head><title>VoiceUp — Offline</title>
              <meta name="viewport" content="width=device-width,initial-scale=1">
              <style>body{font-family:sans-serif;text-align:center;padding:60px 20px;background:#f8fafc}
              h1{color:#6366f1}p{color:#64748b}</style></head>
              <body><h1>🎙 VoiceUp</h1>
              <p>You're offline. Please check your internet connection and try again.</p>
              <button onclick="location.reload()" style="background:#6366f1;color:#fff;border:none;
              padding:12px 24px;border-radius:10px;font-size:1rem;cursor:pointer;margin-top:16px">
              Try Again</button></body></html>`,
              { headers: { 'Content-Type': 'text/html' } }
            );
          }
        });
      })
  );
});
