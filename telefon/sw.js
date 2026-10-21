// Farmer za telefon – radi i bez interneta: svi fajlovi aplikacije se čuvaju u telefonu.
const VERZIJA = "farmer-tel-2.0";
const FAJLOVI = ["./", "index.html", "app.js", "skener.js", "oblak.js", "oblak-konfig.js", "zxing.min.js", "logika.js", "konstante.js", "manifest.webmanifest",
  "ikone/ikona-192.png", "ikone/ikona-512.png", "ikone/ikona-maskable-512.png"];
self.addEventListener("install", e => e.waitUntil(caches.open(VERZIJA).then(c => c.addAll(FAJLOVI)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys()
  .then(k => Promise.all(k.filter(x => x !== VERZIJA).map(x => caches.delete(x)))).then(() => self.clients.claim())));
// prvo internet (da stigne nova verzija), a bez interneta – sačuvana kopija
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => {
    const kopija = r.clone();
    caches.open(VERZIJA).then(c => c.put(e.request, kopija));
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match("index.html"))));
});
