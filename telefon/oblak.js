// Farmer za telefon – automatsko usklađivanje sa računarom preko interneta (Firebase), uparivanje QR kodom.
// Podaci se pre slanja zaključavaju (AES-256-GCM) ključem iz QR koda – server vidi samo nečitljiv tekst.
"use strict";
const DEO = 900000;
const AAD = new TextEncoder().encode("farmer1");
const KOLONE_GRLA = ["id", "markica", "vrsta", "rasa", "pol", "datum_rodjenja", "otac", "majka", "status", "stado",
  "poreklo", "poreklo_od", "stare_markice", "uneto"];

function oblakKonfig() {
  let test = {};
  try { test = JSON.parse(localStorage.getItem("farmer-oblak-test") || "{}"); } catch (e) { /* */ }
  return Object.assign({ authUrl: "https://identitytoolkit.googleapis.com", tokenUrl: "https://securetoken.googleapis.com",
    firestoreUrl: "https://firestore.googleapis.com" }, FIREBASE, test);
}
const oblakPodesen = () => { const k = oblakKonfig(); return !!(k.apiKey && k.projectId); };

// ---------------------------------------------------------------- base64 i šifrovanje
const b64 = u8 => { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
const izB64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const izB64u = s => izB64(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
const uB64u = u8 => b64(u8).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
async function protok(podaci, vrsta, napred) {
  const s = new Blob([podaci]).stream().pipeThrough(napred ? new CompressionStream(vrsta) : new DecompressionStream(vrsta));
  return new Uint8Array(await new Response(s).arrayBuffer());
}
async function aesKljuc(kljuc, upotreba) {
  return crypto.subtle.importKey("raw", izB64u(kljuc), "AES-GCM", false, [upotreba]);
}
async function zakljucaj(obj, kljuc) {
  let podaci = new TextEncoder().encode(JSON.stringify(obj)), verzija = 2;
  if (typeof CompressionStream === "function") { podaci = await protok(podaci, "gzip", true); verzija = 1; }
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData: AAD }, await aesKljuc(kljuc, "encrypt"), podaci));
  const sve = new Uint8Array(13 + ct.length);
  sve[0] = verzija; sve.set(iv, 1); sve.set(ct, 13);
  return b64(sve);
}
async function otkljucaj(tekst, kljuc) {
  const s = izB64(tekst);
  let podaci;
  try {
    podaci = new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: s.subarray(1, 13), additionalData: AAD }, await aesKljuc(kljuc, "decrypt"), s.subarray(13)));
  } catch (e) { throw new Error(t("Podaci ne mogu da se otključaju – telefon je uparen sa drugim računarom?", "Data cannot be unlocked – is the phone paired with another computer?")); }
  if (s[0] === 1) podaci = await protok(podaci, "gzip", false);
  return JSON.parse(new TextDecoder().decode(podaci));
}

// ---------------------------------------------------------------- identitet telefona (za isključivanje jednog telefona)
// Svaki telefon ima svoj par ključeva (ECDH P-256). Kad računar isključi neki DRUGI telefon, novi ključ gazdinstva
// šalje ovom telefonu zaključan njegovim javnim ključem – isključeni telefon ne može da ga pročita.
const EC = { name: "ECDH", namedCurve: "P-256" };
async function osigurajIdentitet() {
  if (S.sinh.tid && S.sinh.ec) return;
  const par = await crypto.subtle.generateKey(EC, true, ["deriveBits"]);
  const pub = await crypto.subtle.exportKey("jwk", par.publicKey), priv = await crypto.subtle.exportKey("jwk", par.privateKey);
  S.sinh.tid = S.sinh.tid || uB64u(crypto.getRandomValues(new Uint8Array(12)));
  S.sinh.ec = { x: pub.x, y: pub.y, priv };
  S.sinh.predstavi = true;
  await sacuvaj();
}
async function odmotaj(dok) {
  const priv = await crypto.subtle.importKey("jwk", S.sinh.ec.priv, EC, false, ["deriveBits"]);
  const e = JSON.parse(dok.epub);
  const pub = await crypto.subtle.importKey("jwk", { kty: "EC", crv: "P-256", x: e.x, y: e.y, ext: true }, EC, false, []);
  const tajna = await crypto.subtle.deriveBits({ name: "ECDH", public: pub }, priv, 256);
  const hk = await crypto.subtle.importKey("raw", tajna, "HKDF", false, ["deriveBits"]);
  const k = await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt: new Uint8Array(0), info: new TextEncoder().encode("farmer-rotacija") }, hk, 256);
  return otkljucaj(dok.podaci, uB64u(new Uint8Array(k)));
}

// ---------------------------------------------------------------- Firestore preko REST-a
class GreskaMreze extends Error {}
class Oblak {
  constructor(farma, kljuc, token) { this.k = oblakKonfig(); this.farma = farma; this.kljuc = kljuc; this.token = Object.assign({}, token || {}); }
  async http(metod, url, telo, zaglavlja = {}, forma = false) {
    const z = Object.assign({}, zaglavlja);
    let body;
    if (telo !== undefined) {
      if (forma) { body = new URLSearchParams(telo).toString(); z["Content-Type"] = "application/x-www-form-urlencoded"; }
      else { body = JSON.stringify(telo); z["Content-Type"] = "application/json"; }
    }
    let r;
    try { r = await fetch(url, { method: metod, headers: z, body }); }
    catch (e) { throw new GreskaMreze(t("Nema interneta", "No internet")); }
    if (r.status === 404) return null;
    const tekst = await r.text();
    const j = tekst ? JSON.parse(tekst) : {};
    if (!r.ok) throw new Error(t("Server je odbio zahtev: ", "Server refused: ") + ((j.error && (j.error.message || j.error)) || r.status));
    return j;
  }
  async prijava() {
    const tk = this.token, k = this.k;
    if (tk.id && tk.istice > Date.now() + 120000) return tk.id;
    if (tk.osvezi) {
      try {
        const r = await this.http("POST", `${k.tokenUrl}/v1/token?key=${k.apiKey}`, { grant_type: "refresh_token", refresh_token: tk.osvezi }, {}, true);
        if (r && r.id_token) { this.token = { id: r.id_token, osvezi: r.refresh_token || tk.osvezi, istice: Date.now() + (+r.expires_in || 3600) * 1000 }; return this.token.id; }
      } catch (e) { if (e instanceof GreskaMreze) throw e; }
    }
    const r = await this.http("POST", `${k.authUrl}/v1/accounts:signUp?key=${k.apiKey}`, { returnSecureToken: true });
    if (!r || !r.idToken) throw new Error(t("Prijava na server nije uspela.", "Server sign-in failed."));
    this.token = { id: r.idToken, osvezi: r.refreshToken || "", istice: Date.now() + (+r.expiresIn || 3600) * 1000 };
    return this.token.id;
  }
  put(kol, dok) { return `${this.k.firestoreUrl}/v1/projects/${this.k.projectId}/databases/(default)/documents/farme/${this.farma}/${kol}` + (dok ? `/${dok}` : ""); }
  async z() { return { Authorization: "Bearer " + (await this.prijava()) }; }
  async upisi(kol, dok, polja) {
    const f = {};
    for (const [k, v] of Object.entries(polja)) f[k] = { stringValue: String(v) };
    await this.http("PATCH", this.put(kol, dok), { fields: f }, await this.z());
  }
  async citaj(kol, dok) {
    const r = await this.http("GET", this.put(kol, dok), undefined, await this.z());
    if (!r) return null;
    const o = {};
    for (const [k, v] of Object.entries(r.fields || {})) o[k] = v.stringValue || "";
    return o;
  }
  async upisiVeliko(kol, osnova, tekst) {
    const delovi = [];
    for (let i = 0; i < tekst.length; i += DEO) delovi.push(tekst.slice(i, i + DEO));
    if (!delovi.length) delovi.push("");
    for (let n = 0; n < delovi.length; n++)
      await this.upisi(kol, `${osnova}_${String(n).padStart(3, "0")}`, { pid: osnova, n, ukupno: delovi.length, deo: delovi[n] });
  }
  async procitajVeliko(kol, osnova, ukupno) {
    let s = "";
    for (let n = 0; n < ukupno; n++) {
      const d = await this.citaj(kol, `${osnova}_${String(n).padStart(3, "0")}`);
      if (!d) throw new Error(t("Deo podataka nedostaje na serveru – pokušaću ponovo.", "Part of the data is missing – will retry."));
      s += d.deo || "";
    }
    return s;
  }
}

// ---------------------------------------------------------------- spajanje (isto kao na računaru)
const PREVODNA = ["dogadjaj", "ishod", "ter", "tip", "poreklo"];
function prevediVr(v) {
  const P = KONST.PREVOD;
  return EN() ? (v in P.es ? v : (P.se[v] ?? v)) : (v in P.se ? v : (P.es[v] ?? v));
}
function normVr(k, v) {
  v = v === null || v === undefined ? "" : String(v);
  if (PREVODNA.includes(k)) return prevediVr(v);
  if (k === "rasa") return normRasa(prevediVr(v));
  if (k === "vrsta") return vrstaNorm(v);
  return v;
}
const kljucGrla = x => x.id || "";
const kljucIst = z => `${z.grlo || ""}|${z.uneto || ""}|${normVr("dogadjaj", z.dogadjaj)}`;
const kljucPod = z => `${z.grlo || ""}|${z.uneto || ""}|${normVr("tip", z.tip)}`;
function indeksiraj(lista, kljuc) {
  const brojac = {}, mapa = new Map(), red = [];
  for (const x of lista) { const k = kljuc(x), n = brojac[k] || 0; brojac[k] = n + 1; const kk = `${k}#${n}`; mapa.set(kk, x); red.push(kk); }
  return { mapa, red };
}
const potpis = (x, kolone) => (x ? JSON.stringify(kolone.map(k => normVr(k, x[k]))) : null);
function normalizovan(x) { const o = {}; for (const [k, v] of Object.entries(x)) o[k] = normVr(k, v); return o; }
// tri smera: baza (poslednje sa računara), tel (telefon sad), rac (novo sa računara); objekti telefona se zadržavaju
function spoji3(baza, tel, rac, kljuc, kolone) {
  const B = indeksiraj(baza || [], kljuc).mapa, T = indeksiraj(tel, kljuc), R = indeksiraj(rac, kljuc), rez = [];
  for (const k of R.red.concat(T.red.filter(k => !R.mapa.has(k)))) {
    const b = B.get(k), tt = T.mapa.get(k), r = R.mapa.get(k);
    const cb = potpis(b, kolone), ct = potpis(tt, kolone), cr = potpis(r, kolone);
    let izbor = (ct === cb || ct === cr) ? r : tt;      // telefon nije menjao -> računar; inače telefon
    if (!izbor) continue;
    const novo = normalizovan(izbor);
    if (tt) { for (const kk of Object.keys(tt)) delete tt[kk]; Object.assign(tt, novo); rez.push(tt); }
    else rez.push(novo);
  }
  return rez;
}
function primeniSnimak(snap) {
  S.jezik = snap.jezik === "en" ? "en" : "sr";
  const baza = S.osnova || { grla: [], istorija: [], podsetnici: [] };
  const kolG = [...new Set(KOLONE_GRLA.concat(...(snap.grla || []).map(Object.keys), ...S.grla.map(Object.keys)))];
  S.grla = spoji3(baza.grla, S.grla, snap.grla || [], kljucGrla, kolG);
  S.istorija = spoji3(baza.istorija, S.istorija, snap.istorija || [], kljucIst, IST_KOLONE);
  S.podsetnici = spoji3(baza.podsetnici, S.podsetnici, snap.podsetnici || [], kljucPod, POD_KOLONE);
  S.osnova = JSON.parse(JSON.stringify({ grla: snap.grla || [], istorija: snap.istorija || [], podsetnici: snap.podsetnici || [] }));
  S.prag = +snap.prag || S.prag;
  S.grav = snap.gravidnost || S.grav;
  S.izvoz = { id: snap.id, datum: snap.izvezeno, stada: snap.stada || [] };
  if (S.sinh) S.sinh.spisak = snap.telefoni || null;   // računar zna za ove telefone
  osveziModel();
}
// šta je telefon promenio u odnosu na poslednje sa računara: [{n, b, t}]
function razlike() {
  const baza = S.osnova || { grla: [], istorija: [], podsetnici: [] }, rez = {};
  const kolG = [...new Set(KOLONE_GRLA.concat(...S.grla.map(Object.keys)))];
  for (const [ime, lista, osn, kljuc, kolone] of [["grla", S.grla, baza.grla, kljucGrla, kolG],
    ["istorija", S.istorija, baza.istorija, kljucIst, IST_KOLONE], ["podsetnici", S.podsetnici, baza.podsetnici, kljucPod, POD_KOLONE]]) {
    const B = indeksiraj(osn || [], kljuc).mapa, T = indeksiraj(lista, kljuc);
    rez[ime] = [];
    for (const k of T.red) {
      const b = B.get(k) || null, tt = T.mapa.get(k);
      if (potpis(b, kolone) !== potpis(tt, kolone)) rez[ime].push({ n: +k.slice(k.lastIndexOf("#") + 1), b, t: tt });
    }
  }
  return rez;
}

// ---------------------------------------------------------------- usklađivanje
let sinhRadi = false, sinhOdlozeno = null;
const sinhStanje = { tekst: "", vrsta: "" };
function sinhStatus(tekst, vrsta) {
  sinhStanje.tekst = tekst; sinhStanje.vrsta = vrsta;
  const el = document.getElementById("oblak");
  if (el) { el.textContent = { ok: "☁✓", radi: "☁…", ceka: "☁⏳", greska: "☁!" }[vrsta] || ""; el.title = tekst; el.className = "oblak " + vrsta; }
  const el2 = document.getElementById("sinhTekst");
  if (el2) { el2.textContent = tekst; el2.className = "sinh-tekst " + vrsta; }
}
async function usaglasi(rucno, dubina = 0) {
  if (!S.sinh || !oblakPodesen()) return;
  if (S.sinh.iskljucen) return sinhStatus(t("Računar je isključio ovaj telefon", "The computer disconnected this phone"), "greska");
  if (sinhRadi) return;
  if (!navigator.onLine && !rucno) return sinhStatus(S.promene.length ? t(`${S.promene.length} promena čeka internet`, `${S.promene.length} changes waiting for internet`) : t("Nema interneta", "No internet"), "ceka");
  sinhRadi = true;
  sinhStatus(t("Usklađujem…", "Syncing…"), "radi");
  let novo = false, ponovo = false, poslato = false;
  if (rucno) sinhMirno = 0;
  try {
    await osigurajIdentitet();
    const sp = S.sinh.spisak;                     // računar još ne zna ovaj telefon (ili mu je promenjeno ime) -> predstavi se
    if (sp && sp[S.sinh.tid] !== imeTelefona() && S.sinh.predstavljenNa !== S.sinh.verzija) S.sinh.predstavi = true;
    const o = new Oblak(S.sinh.farma, S.sinh.kljuc, S.sinh.token);
    if (S.promene.length || S.sinh.predstavi) {   // 1) pošalji šta je urađeno na telefonu
      const n = S.promene.length;
      const paket = { format: "farmer-paket", verzija: 1, napravljeno: sada(), jezik: S.jezik, osnova_verzija: S.sinh.verzija || null,
        tel: { tid: S.sinh.tid, ime: imeTelefona(), javni: { x: S.sinh.ec.x, y: S.sinh.ec.y } },
        razlike: razlike(), promene: S.promene.slice(0, n) };
      const pid = `${Date.now()}${Math.random().toString(16).slice(2, 8)}`;
      await o.upisiVeliko("paketi", pid, await zakljucaj(paket, S.sinh.kljuc));
      S.poslato = (S.poslato || []).concat(S.promene.slice(0, n)).slice(-100);
      S.promene.splice(0, n);
      S.sinh.predstavi = false;
      poslato = true;
      S.sinh.predstavljenNa = S.sinh.verzija;
      await sacuvaj();
    }
    const pz = await o.citaj("stanje", "poslednji");  // 2) preuzmi novo sa računara
    if (pz && pz.premesteno) {                     // računar je promenio ključ (isključio neki telefon)
      const r = S.sinh.tid ? await o.citaj("rotacija", S.sinh.tid) : null;
      if (!r) {
        S.sinh.iskljucen = true;
        await sacuvaj();
        throw new Error(t("Računar je isključio ovaj telefon. Podaci ostaju na telefonu; za ponovno povezivanje skeniraj novi QR kod.",
          "The computer disconnected this phone. Data stays on the phone; scan a new QR code to reconnect."));
      }
      const nova = await odmotaj(r);
      Object.assign(S.sinh, { farma: nova.farma, kljuc: nova.kljuc, naziv: nova.naziv || S.sinh.naziv, verzija: null, predstavi: true });
      await sacuvaj();                              // ono što je bilo poslato na staru adresu, šalje se ponovo (spajanje to podnosi)
      ponovo = true;
    } else if (pz && pz.verzija && pz.verzija !== S.sinh.verzija) {
      const snap = await otkljucaj(await o.procitajVeliko("snimci", pz.verzija, +pz.ukupno || 1), S.sinh.kljuc);
      primeniSnimak(snap);
      S.sinh.verzija = pz.verzija;
      novo = true;
    }
    S.sinh.token = o.token;
    S.sinh.poslednje = sada();
    S.pocetak = true;
    await sacuvaj();
    const sad = new Date();
    sinhStatus(S.promene.length ? t(`${S.promene.length} promena čeka slanje`, `${S.promene.length} changes waiting`) :
      t(`Usklađeno u ${pad(sad.getHours())}:${pad(sad.getMinutes())}`, `Synced at ${pad(sad.getHours())}:${pad(sad.getMinutes())}`), S.promene.length ? "ceka" : "ok");
  } catch (e) {
    if (!(e instanceof GreskaMreze) && typeof zapisiGresku === "function") zapisiGresku("usklađivanje", e.message);
    sinhStatus(e instanceof GreskaMreze ? (S.promene.length ? t(`${S.promene.length} promena čeka internet`, `${S.promene.length} changes waiting for internet`) : t("Nema interneta – pokušaću ponovo", "No internet – will retry"))
      : t("Greška: ", "Error: ") + e.message, e instanceof GreskaMreze ? "ceka" : "greska");
  } finally {
    sinhRadi = false;
  }
  sinhMirno = (novo || poslato || ponovo) ? 0 : sinhMirno + 1;
  if (ponovo && dubina < 2) return usaglasi(rucno, dubina + 1);
  if (novo) osveziPosleSinh();
}
function osveziPosleSinh() {
  const { ekran: e } = delovi();
  if (["", "grla", "karton", "danas", "parenje", "vise", "prenos", "sinh"].includes(e)) prikazi();
  else meni(e);                                      // forma je otvorena – ne diramo je
}
function usaglasiUskoro() {                          // posle promene: sačekaj par sekundi (više upisa odjednom)
  if (!S.sinh) return;
  clearTimeout(sinhOdlozeno);
  sinhOdlozeno = setTimeout(() => usaglasi(), 4000);
  sinhBudi();
}
function pokreniUsaglasavanje() {
  if (!S.sinh) return;
  sinhStatus(S.promene.length ? t(`${S.promene.length} promena čeka slanje`, `${S.promene.length} changes waiting`) : "", S.promene.length ? "ceka" : "ok");
  usaglasi();
}
// koliko često: na minut dok se nešto dešava, a kad je mirno ređe (do 5 min) – štedi bateriju, internet i kvotu servera
let sinhMirno = 0, sinhTajmer = null;
function zakaziSinh() {
  clearTimeout(sinhTajmer);
  sinhTajmer = setTimeout(async () => {
    if (document.visibilityState === "visible") await usaglasi();
    zakaziSinh();
  }, sinhMirno < 5 ? 60000 : sinhMirno < 15 ? 180000 : 300000);
}
function sinhBudi() { sinhMirno = 0; zakaziSinh(); }
window.addEventListener("online", () => { sinhBudi(); usaglasi(); });
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") { sinhBudi(); usaglasi(); } });
zakaziSinh();

// ---------------------------------------------------------------- uparivanje
function procitajLink(tekst) {
  const m = String(tekst || "").match(/upari=([0-9a-f]{40,})\.([A-Za-z0-9_-]{40,})\.?([^&\s]*)/);
  return m ? { farma: m[1], kljuc: m[2], naziv: decodeURIComponent(m[3] || "") } : null;
}
async function upari(p) {
  if (S.sinh && S.sinh.iskljucen) {                // isključen telefon se ponovo uparuje – podaci ostaju
    S.imeTelefona = S.sinh.ime || S.imeTelefona;
    S.sinh = null;
  }
  if (S.sinh && S.sinh.farma === p.farma) { poruka(t("Telefon je već uparen sa ovim računarom.", "This phone is already paired with this computer.")); usaglasi(true); return true; }
  const ima = S.grla.length || S.istorija.length;
  if (S.sinh && S.sinh.farma !== p.farma) {
    if (!confirm(t(`Telefon je uparen sa gazdinstvom „${S.sinh.naziv || "?"}“. Preći na „${p.naziv || "novo gazdinstvo"}“?\n\nPodaci starog gazdinstva biće uklonjeni sa ovog telefona` + (S.promene.length ? ` (i ${S.promene.length} neposlatih promena!)` : "") + ".",
      `This phone is paired with „${S.sinh.naziv || "?"}“. Switch to „${p.naziv || "new farm"}“?\n\nThe old farm's data will be removed from this phone` + (S.promene.length ? ` (and ${S.promene.length} unsent changes!)` : "") + "."))) return false;
    Object.assign(S, { grla: [], istorija: [], podsetnici: [], osnova: null, izvoz: null, promene: [] });
  } else if (ima && !confirm(t("Na telefonu već ima podataka. Da li su sa ISTOG računara sa kojim se sada uparuješ?\n\nU redu = da, zadrži ih i spoji\nOtkaži = ne, obriši ih sa telefona",
    "There is already data on the phone. Is it from the SAME computer you are pairing with?\n\nOK = yes, keep and merge\nCancel = no, delete it from the phone"))) {
    Object.assign(S, { grla: [], istorija: [], podsetnici: [], osnova: null, izvoz: null, promene: [] });
  }
  const ime = (prompt(t("Ime ovog telefona – da se na računaru vidi ko je šta upisao (npr. Marko):",
    "Name of this phone – so the computer shows who entered what (e.g. Mark):"), S.imeTelefona || "") || "").trim().slice(0, 40);
  if (ime) S.imeTelefona = ime;
  S.sinh = { farma: p.farma, kljuc: p.kljuc, naziv: p.naziv, verzija: null, token: null, ime: S.imeTelefona || "" };
  S.pocetak = true;
  osveziModel();
  await sacuvaj();
  poruka(t("Upareno! Preuzimam podatke sa računara…", "Paired! Downloading data from the computer…"));
  await usaglasi(true);
  return true;
}
async function prekiniUparivanje() {
  if (!confirm(t("Prekinuti uparivanje sa računarom? Podaci ostaju na telefonu, ali se više neće sami usklađivati.",
    "Stop pairing with the computer? Data stays on the phone but will no longer sync."))) return;
  S.sinh = null;
  await sacuvaj();
  sinhStatus("", "");
  prikazi();
}

// ekran: Više → Povezivanje sa računarom
function ekranSinh(_, upit) {
  postaviVrh(t("Povezivanje sa računarom", "Connect to computer"), true); meni("vise");
  if (!oblakPodesen()) {
    ekran.innerHTML = `<div class="kart"><h2>☁ ${t("Automatsko povezivanje", "Automatic connection")}</h2><p class="mali">${t("Biće dostupno u sledećoj verziji. Do tada koristi prenos fajlom.", "Coming in the next version. Until then use file transfer.")}</p>
      <a class="dug puno" href="#prenos">⇅ ${t("Prenos fajlom", "File transfer")}</a></div>`;
    return;
  }
  if (S.sinh && S.sinh.iskljucen) {
    ekran.innerHTML = `<div class="kart"><h2>⛔ ${t("Telefon je isključen", "Phone disconnected")}</h2>
      <p>${t("Računar je isključio ovaj telefon", "The computer disconnected this phone")}${S.sinh.naziv ? ` (${h(S.sinh.naziv)})` : ""}.
      ${t("Podaci koji su na telefonu ostaju, ali se više ne usklađuju.", "Data on the phone stays, but no longer syncs.")}</p>
      <button class="dug glavno puno" id="sken">📷 ${t("Skeniraj novi QR kod sa računara", "Scan a new QR code from the computer")}</button></div>
      <div class="kart"><button class="dug opasno puno" id="prekini">${t("Prekini uparivanje", "Unpair")}</button></div>`;
    $("#sken").onclick = skenirajIUpari;
    $("#prekini").onclick = prekiniUparivanje;
    return;
  }
  if (S.sinh) {
    ekran.innerHTML = `<div class="kart"><h2>☁ ${t("Upareno sa računarom", "Paired with computer")}</h2>
      <dl class="polja"><dt>${t("Gazdinstvo", "Farm")}</dt><dd>${h(S.sinh.naziv || "–")}</dd>
      <dt>${t("Ovaj telefon", "This phone")}</dt><dd>📱 ${h(imeTelefona())} <a href="#" id="ime">${t("promeni", "change")}</a></dd>
      <dt>${t("Poslednje", "Last")}</dt><dd>${h(S.sinh.poslednje || "–")}</dd><dt>${t("Čeka slanje", "Waiting")}</dt><dd>${S.promene.length}</dd></dl>
      <p id="sinhTekst" class="sinh-tekst ${sinhStanje.vrsta}">${h(sinhStanje.tekst)}</p>
      <button class="dug glavno puno" id="sad">🔄 ${t("Usaglasi sada", "Sync now")}</button>
      <p class="mali">${t("Telefon se sam usklađuje kad ima internet – dugme ti ne treba, osim ako žuriš.", "The phone syncs by itself when online – the button is only if you are in a hurry.")}</p></div>
      <div class="kart"><button class="dug opasno puno" id="prekini">${t("Prekini uparivanje", "Unpair")}</button></div>`;
    $("#sad").onclick = () => usaglasi(true);
    $("#ime").onclick = async ev => {
      ev.preventDefault();
      const ime = (prompt(t("Ime ovog telefona (npr. Marko):", "Name of this phone (e.g. Mark):"), imeTelefona()) || "").trim().slice(0, 40);
      if (!ime) return;
      S.sinh.ime = S.imeTelefona = ime;
      S.sinh.predstavi = true;
      await sacuvaj();
      prikazi();
      usaglasi(true);
    };
    $("#prekini").onclick = prekiniUparivanje;
    return;
  }
  ekran.innerHTML = `<div class="kart"><h2>📱 ${t("Upari sa računarom", "Pair with computer")}</h2><ol class="koraci">
      <li>${t("Na računaru otvori Farmer → <b>Telefon</b> → <b>Upari telefon</b>. Pojaviće se QR kod.", "On the computer open Farmer → <b>Phone</b> → <b>Pair phone</b>. A QR code appears.")}</li>
      <li>${t("Klikni dugme ispod i uperi kameru u QR kod na ekranu računara.", "Tap the button below and point the camera at the QR code on the computer screen.")}</li></ol>
      <button class="dug glavno puno" id="sken">📷 ${t("Skeniraj QR kod sa računara", "Scan QR code from computer")}</button>
      <p class="mali">${t("Uparuje se samo jednom. Posle se telefon i računar sami usklađuju, i kad su daleko.", "You pair only once. After that they sync by themselves, even far apart.")}</p></div>`;
  $("#sken").onclick = skenirajIUpari;
}
async function skenirajIUpari() {
  const kod = await skeniraj(t("Skeniraj QR kod sa računara", "Scan the QR code on the computer"));
  if (!kod) return;
  const p = procitajLink(kod);
  if (!p) return poruka(t("Ovo nije Farmer QR kod za uparivanje.", "This is not a Farmer pairing QR code."));
  if (await upari(p)) idi("grla");
}
