/* Cache only the generic reconnect page. Room HTML and data always use the network. */
const CACHE = 'chaosconsole-offline-v1';
const OFFLINE = '/offline.html';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.add(new Request(OFFLINE, { cache: 'reload' }))));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith('chaosconsole-offline-') && key !== CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});
// No forced activation: an update takes over after the existing app windows close.
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate' || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(event.request).catch(async () => {
    return (await caches.match(OFFLINE)) || new Response('Reconnect to open ChaosConsole.', { status: 503, headers: { 'Content-Type': 'text/plain' } });
  }));
});
