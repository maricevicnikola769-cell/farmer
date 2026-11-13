// HerdDoc za telefon – radi i bez interneta: svi fajlovi aplikacije se čuvaju u telefonu.
const VERZIJA = "farmer-tel-6.2";
const FAJLOVI = ["./", "index.html", "app.js", "skener.js", "oblak.js", "oblak-konfig.js", "zxing.min.js", "logika.js", "konstante.js", "prevodi.js", "manifest.webmanifest",
  "ikone/ikona-192.png", "ikone/ikona-512.png", "ikone/ikona-maskable-512.png"];
self.addEventListener("install", e => e.waitUntil(caches.open(VERZIJA).then(c => c.addAll(FAJLOVI.map(f => new Request(f, { cache: "reload" })))).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys()
  .then(k => Promise.all(k.filter(x => x !== VERZIJA).map(x => caches.delete(x)))).then(() => self.clients.claim())));
// ---- obaveštenja kad je aplikacija zatvorena (plan pravi aplikacija i čuva u bazi "farmer")
function bazaSW() {
  return new Promise((res, rej) => {
    const r = indexedDB.open("farmer", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("stanje");
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  });
}
const swRadnja = (db, nacin, fn) => new Promise((res, rej) => {
  const tx = db.transaction("stanje", nacin), z = fn(tx.objectStore("stanje"));
  tx.oncomplete = () => res(z && z.result); tx.onerror = tx.onabort = () => rej(tx.error);
});
function danasISO() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }
async function javiPodsetnike() {
  const db = await bazaSW();
  const p = await swRadnja(db, "readonly", st => st.get("obavestenja"));
  if (!p || !Array.isArray(p.plan)) return;
  const sad = new Date(), hm = `${String(sad.getHours()).padStart(2, "0")}:${String(sad.getMinutes()).padStart(2, "0")}`;
  const rano = sad.getHours() < (+p.sat || 0);                 // pre izabranog sata – samo podsetnici sa tačnim vremenom
  const d = danasISO(), pok = (await swRadnja(db, "readonly", st => st.get("pokazano"))) || {};
  const vec = pok.datum === d ? pok.k || [] : [];
  const nova = p.plan.filter(x => x.od <= d && !vec.includes(x.k) && (x.u ? x.od === d && hm >= x.u : !rano));
  if (!nova.length) return;
  await self.registration.showNotification(p.naslov || "HerdDoc", {
    body: nova.slice(0, 3).map(x => x.n).join("\n") + (nova.length > 3 ? "\n" + String(p.jos || "+{0}").replace("{0}", nova.length - 3) : ""),
    icon: "ikone/ikona-192.png", badge: "ikone/ikona-192.png", tag: "herddoc-obavestenja", renotify: true, silent: false,   // zvuk telefona i kad stara poruka još stoji
    vibrate: [300, 150, 300], data: { url: "./#danas" } });
  await swRadnja(db, "readwrite", st => st.put({ datum: d, k: vec.concat(nova.map(x => x.k)).slice(-300) }, "pokazano"));
}
self.addEventListener("periodicsync", e => { if (e.tag === "herddoc-obavestenja") e.waitUntil(javiPodsetnike().catch(() => {})); });
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "./#danas";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(cs => {
    for (const c of cs) { if ("focus" in c) { c.postMessage({ idi: "danas" }); return c.focus(); } }
    return self.clients.openWindow(url);
  }));
});

// prvo internet (da stigne nova verzija), a bez interneta – sačuvana kopija
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request, { cache: "no-cache" }).then(r => {
    const kopija = r.clone();
    caches.open(VERZIJA).then(c => c.put(e.request, kopija));
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match("index.html"))));
});
