// HelpDesk Service Worker — кеширование для PWA
const CACHE_NAME = 'helpdesk-v1';
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin === location.origin) {
    e.respondWith(
      fetch(e.request).then(r => {
        // Проверяем что ответ валидный
        if (!r || r.status !== 200 || r.type === 'error') {
          return r;
        }
        // Клонируем один раз для кеша
        const responseForCache = r.clone();
        // Кешируем асинхронно (в фоне)
        caches.open(CACHE_NAME).then(c => c.put(e.request, responseForCache));
        // Возвращаем оригинальный response
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  e.respondWith(caches.match(e.request).then(c => c || fetch(e.request)));
});
