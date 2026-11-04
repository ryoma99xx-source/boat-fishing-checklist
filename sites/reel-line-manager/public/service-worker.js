const CACHE_NAME = "reel-line-manager-public-v70";
const APP_SHELL = [
"./",
"index.html",
"help.html",
"favicon.ico",
"favicon-48.png",
"manifest.json",
"icons/icon-192.png",
"icons/icon-512.png",
"icons/apple-touch-icon.png"
];
self.addEventListener("install", event => {
event.waitUntil(
caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
);
self.skipWaiting();
});
self.addEventListener("activate", event => {
event.waitUntil(
caches.keys().then(keys =>
Promise.all(
keys
.filter(key => key !== CACHE_NAME)
.map(key => caches.delete(key))
)
)
);
self.clients.claim();
});
self.addEventListener("fetch", event => {
if (event.request.method !== "GET") return;
const url = new URL(event.request.url);
if (url.origin !== self.location.origin) return;
const refresh = fetch(event.request)
.then(response => {
if (response.ok) {
const copy = response.clone();
caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
}
return response;
});
event.respondWith(
caches.match(event.request).then(cached => {
return cached || refresh.catch(() => Response.error());
})
);
event.waitUntil(refresh.catch(() => undefined));
});