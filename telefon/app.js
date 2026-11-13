// HerdDoc za telefon – ekrani. Podaci se čuvaju u telefonu (radi i bez interneta).
"use strict";
const VERZIJA_TEL = "5.9";
const PODRSKA = "herddoc7@gmail.com";   // e-pošta za prijavu problema
const $ = s => document.querySelector(s);
const h = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ekran = $("#ekran");
const KLJUC = "farmer-telefon-v1";

// ---------------------------------------------------------------- čuvanje u telefonu
// IndexedDB: baza u telefonu bez male granice od 5 MB (i farma od 10.000 grla staje).
// Ako je telefon/pregledač ne podržava, koristi se staro čuvanje (localStorage).
const BAZA = "farmer", SKLADISTE = "stanje";
let bazaP = null, bezBaze = false, redCuvanja = Promise.resolve();
function otvoriBazu() {
  if (!bazaP) bazaP = new Promise((res, rej) => {
    if (!window.indexedDB) return rej(new Error("IndexedDB"));
    const r = indexedDB.open(BAZA, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(SKLADISTE);
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
  return bazaP;
}
function bazaRadnja(nacin, fn) {
  return otvoriBazu().then(db => new Promise((res, rej) => {
    const tx = db.transaction(SKLADISTE, nacin), st = tx.objectStore(SKLADISTE);
    let rez;
    const zahtev = fn(st);
    if (zahtev) zahtev.onsuccess = () => { rez = zahtev.result; };
    tx.oncomplete = () => res(rez);
    tx.onerror = tx.onabort = () => rej(tx.error || new Error("IndexedDB"));
  }));
}
const bazaCitaj = k => bazaRadnja("readonly", st => st.get(k));
const bazaUpisi = (k, v) => bazaRadnja("readwrite", st => st.put(v, k));
const bazaBrisi = k => bazaRadnja("readwrite", st => st.delete(k));
const kopija = o => (typeof structuredClone === "function" ? structuredClone(o) : JSON.parse(JSON.stringify(o)));
const stanjeZaCuvanje = () => ({ jezik: S.jezik, jezikIzabran: S.jezikIzabran || null, prag: S.prag, grav: S.grav, grla: S.grla, istorija: S.istorija,
  podsetnici: S.podsetnici, osnova: S.osnova, izvoz: S.izvoz, promene: S.promene, pocetak: S.pocetak || false,
  sinh: S.sinh || null, poslato: S.poslato || [], slike: S.slike || {}, licenca: S.licenca || null, vrste: S.vrste || [], rase: S.rase || [],
  korisnik: S.korisnik || "", novaRasa: S.novaRasa || null, finansije: S.finansije || [], valuta: S.valuta || "", obav: S.obav || null, podesIzmene: S.podesIzmene || null, mreza: S.mreza || null, mrezaPodaci: S.mrezaPodaci || null, mrezaToken: S.mrezaToken || null });
function sacuvajStaro(podaci) {
  try { localStorage.setItem(KLJUC, JSON.stringify(podaci)); return true; }
  catch (e) { poruka(t("Podaci nisu sačuvani u telefonu: ", "Data was not saved on the phone: ") + e.message); return false; }
}
function sacuvaj() {
  planUskoro();
  const podaci = kopija(stanjeZaCuvanje());          // snimak trenutnog stanja, upisuje se redom
  if (bezBaze) return sacuvajStaro(podaci);
  redCuvanja = redCuvanja.then(() => bazaUpisi("glavno", podaci)).catch(() => { bezBaze = true; sacuvajStaro(podaci); });
  return redCuvanja;
}
async function ucitajIzTelefona() {
  let d = null;
  try { d = await bazaCitaj("glavno"); } catch (e) { bezBaze = true; }
  let staro = null;
  try { staro = JSON.parse(localStorage.getItem(KLJUC) || "null"); } catch (e) { /* */ }
  if (!d && staro) {
    d = staro;
    if (!bezBaze) {                                    // prvi put posle nove verzije: prebaci podatke u bazu
      try { await bazaUpisi("glavno", staro); localStorage.removeItem(KLJUC); } catch (e) { bezBaze = true; }
    }
  }
  if (d) Object.assign(S, d);
  osveziModel();
}
const imaPodatke = () => S.izvoz || S.pocetak || S.grla.length;

let tajmer;
function poruka(tekst) {
  document.querySelectorAll(".toast").forEach(x => x.remove());
  const d = document.createElement("div");
  d.className = "toast"; d.textContent = tekst;
  document.body.appendChild(d);
  clearTimeout(tajmer); tajmer = setTimeout(() => d.remove(), 3200);
}
function promena(tekst) { sacuvaj(); if (tekst) poruka(tekst); usaglasiUskoro(); }

// ---------------------------------------------------------------- ruter (#grla, #karton/ID ...)
const idi = adresa => { location.hash = adresa; };
function delovi() {
  const [put, upit] = decodeURIComponent(location.hash.slice(1) || "").split("?");
  const p = (put || "").split("/");
  return { ekran: p[0] || "", arg: p.slice(1).join("/"), upit: new URLSearchParams(upit || "") };
}

$("#nazad").onclick = () => (history.length > 1 ? history.back() : idi("grla"));

function postaviVrh(naslov, nazad) {
  $("#naslov").textContent = naslov;
  $("#nazad").classList.toggle("skriveno", !nazad);
  $("#logo").classList.toggle("skriveno", !!nazad);
  document.title = naslov === "HerdDoc" ? "HerdDoc" : `${naslov} – HerdDoc`;
}
function meni(akt) {
  const n = imaPodatke() ? obavestenja().filter(o => o.nivo <= 1).length : 0;
  const stavke = [["grla", "☰", t("Grla", "Animals")], ["danas", "◉", t("Danas", "Today")], ["dogadjaj", "+", t("Upiši", "Record"), "plus"],
    ["parenje", "⚭", t("Parenje", "Mating")], ["vise", "⋯", t("Više", "More")]];
  $("#meni").innerHTML = stavke.map(([k, ik, naziv, kl]) =>
    `<a href="#${k}" class="${kl || ""} ${k === akt ? "akt" : ""}"><span class="ik">${ik}</span>${h(naziv)}${k === "danas" && n ? `<span class="brojac">${n}</span>` : ""}</a>`).join("");
  $("#meni").classList.toggle("skriveno", !imaPodatke());
  document.documentElement.lang = S.jezik;
}

function prikazi() {
  if (location.hash.startsWith("#upari=")) {            // QR kod sa računara (skeniran i običnom kamerom)
    const p = procitajLink(location.hash);
    history.replaceState(null, "", location.pathname + "#grla");   // ključ ne ostaje u adresi
    if (p && oblakPodesen()) { upari(p).then(() => prikazi()); return; }
  }
  const { ekran: e, arg, upit } = delovi();
  window.scrollTo(0, 0);
  if (!imaPodatke() && e !== "prenos" && e !== "sinh") return dobrodoslica();
  const ekrani = { grla: ekranGrla, karton: ekranKarton, danas: ekranDanas, dogadjaj: ekranDogadjaj, parenje: ekranParenje, srodstvo: ekranSrodstvo,
    vise: ekranVise, prenos: ekranPrenos, sinh: ekranSinh, novo: ekranNovoGrlo, rodjenje: ekranRodjenje, mindjuse: ekranMindjuse, podsetnik: ekranPodsetnik, muznja: ekranMuznja, dnk: ekranDnk, udruzenje: ekranUdruzenje, oceni: ekranOceni, rang: ekranRang, rase: ekranRase, vrste: ekranVrste, novarasa: ekranNovaRasa, rodoslov: ekranRodoslov, finansije: ekranFinansije, finupis: ekranFinUpis, istorija: ekranIstorija, statistika: ekranStatistika };
  (ekrani[e] || ekranGrla)(arg, upit);
}

// ---------------------------------------------------------------- delovi ekrana
function cip(id, link = true) {
  const a = M.A[id], siv = !a || a.osnivac;
  const nap = a && a.napomena ? `<span class="nap-znak" title="${h(a.napomena)}">!</span>` : "";   // grlo ima napomenu
  return link && !siv ? `<a class="cip" href="#karton/${encodeURIComponent(id)}">${h(id)}${nap}</a>` : `<span class="cip ${siv ? "siv" : ""}">${h(id || "?")}${nap}</span>`;
}
function znakInbr(f) {
  if (!f) return "";
  const [tekst, kl] = procena(f, S.prag);
  return `<span class="znak ${kl}" title="${h(tekst)}">F ${pct(f)}</span>`;
}
function opisGrla(a) {
  const del = [M.polNaziv(a.id), a.rasa || "", fmtStarost(starostMeseci(a.datum))].filter(Boolean);
  if (a.markica) del.unshift("🏷 " + a.markica);
  return del.join(" · ");
}
const NA_STRANI = 100;
function listaGrla(spisak, prazanTekst, koliko = NA_STRANI) {
  if (!spisak.length) return `<div class="prazno">${h(prazanTekst)}</div>`;
  const gravidne = new Set(cekajuPorodjaj().map(z => roditeljiParenja(z)[0]));
  return `<div class="lista">` + spisak.slice(0, koliko).map(a => {
    const gr = gravidne.has(a.id), kar = Object.keys(karenca(a.id)).length;
    return `<a class="red" href="#karton/${encodeURIComponent(a.id)}">${cip(a.id, false)}<div class="sred"><b>${h(opisGrla(a))}</b>` +
      (a.napomena ? `<span class="nap-tekst">⚠ ${h(a.napomena)}</span>` : "") +
      `<span>${[a.stado, !a.aktivno ? t("van zapata", "out of herd") : "", gr ? "⏳ " + t("gravidna", "pregnant") : "", kar ? "⚠ " + t("karenca", "withdrawal") : ""].filter(Boolean).map(h).join(" · ") || "&nbsp;"}</span></div>${znakInbr(M.inbr(a.id))}</a>`;
  }).join("") + `</div>` + (spisak.length > koliko ? `<button class="dug puno" data-jos="${koliko + NA_STRANI}">${t(`Prikaži još (${spisak.length - koliko})`, `Show more (${spisak.length - koliko})`)}</button>` : "");
}
function datalistGrla(id, spisak) {
  return `<datalist id="${id}">${spisak.map(a => `<option value="${h(a.id)}">${h(opisGrla(a))}</option>`).join("")}</datalist>`;
}
function kartObavestenja(o) {
  return `<div class="ob"><div class="traka n${o.nivo}"></div><div class="tekst">${o.grlo ? cip(o.grlo) : ""}<b>${h(o.naslov)}</b><div class="mali">${h(o.opis)}</div>` +
    (o.akcije.length ? `<div class="dugmad">${o.akcije.map((a, i) => `<button class="dug ${a.glavno ? "glavno" : ""}" data-akcija="${i}">${h(a.tekst)}</button>`).join("")}</div>` : "") +
    `</div></div>`;
}
function vezAkcije(koren, spisak) {
  koren.querySelectorAll(".ob").forEach((el, i) => el.querySelectorAll("[data-akcija]").forEach(b => {
    b.onclick = () => izvrsi(spisak[i].akcije[+b.dataset.akcija].radnja);
  }));
}
function indeks(z) { return S.istorija.indexOf(z); }
function izvrsi([vrsta, x, y]) {
  if (vrsta === "rodjenje") return idi(`rodjenje/${indeks(x)}`);
  if (vrsta === "upisListu") return idi(`mindjuse/${indeks(x)}`);
  if (vrsta === "forma") return idi(`dogadjaj?grlo=${encodeURIComponent(x)}&tip=${encodeURIComponent(y)}`);
  if (vrsta === "neuspelo") { if (!confirm(t(`Označiti parenje od ${x.datum} kao neuspelo?`, `Mark the mating of ${x.datum} as failed?`))) return; oznaciNeuspelo(x); promena(t("Parenje označeno kao neuspelo.", "Mating marked as failed.")); }
  if (vrsta === "teraSe") { teraSe(x); promena(t("Zabeleženo: ponovo se tera.", "Recorded: in heat again.")); const [majka, otac] = roditeljiParenja(x); return idi(`dogadjaj?grlo=${encodeURIComponent(majka)}&tip=${encodeURIComponent(K().PARENJE)}&partner=${encodeURIComponent(otac || "")}`); }
  if (vrsta === "neTeraSe") { neTeraSe(x); promena(t("Zabeleženo: ne tera se – verovatno je gravidna.", "Recorded: not in heat – probably pregnant.")); }
  if (vrsta === "podsetnikUradjen") { podsetnikUradjen(x); promena(t("Urađeno.", "Done.")); }
  if (vrsta === "podsetnikOdlozi") { podsetnikOdlozi(x, 7); promena(t("Odloženo 7 dana.", "Postponed 7 days.")); }
  prikazi();
}

// ---------------------------------------------------------------- instalacija na telefon
let ponudaInstalacije = null;
window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); ponudaInstalacije = e; osveziInstalaciju(); });
window.addEventListener("appinstalled", () => { ponudaInstalacije = null; osveziInstalaciju(); poruka(t("HerdDoc je instaliran – ikonica je na početnom ekranu.", "HerdDoc is installed – the icon is on your home screen.")); });
function instalirana() {
  return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
}
function dugmeInstalacije() {
  if (instalirana()) return "";
  return `<button class="dug glavno puno" id="instaliraj">📲 ${t("Instaliraj HerdDoc na telefon", "Install HerdDoc on this phone")}</button><div style="height:10px"></div>`;
}
function osveziInstalaciju() {
  const d = $("#instaliraj");
  if (!d) return;
  if (instalirana()) { d.nextElementSibling && d.nextElementSibling.remove(); d.remove(); return; }
  d.onclick = instaliraj;
}
async function instaliraj() {
  if (ponudaInstalacije) {
    ponudaInstalacije.prompt();
    try { await ponudaInstalacije.userChoice; } catch (e) { /* */ }
    ponudaInstalacije = null;
    return;
  }
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  alert(ios
    ? t("Na iPhone-u: u Safariju dodirni dugme Deli (kvadrat sa strelicom) → „Dodaj na početni ekran“ → Dodaj.",
        "On iPhone: in Safari tap Share (square with arrow) → “Add to Home Screen” → Add.")
    : t("U Chrome-u dodirni ⋮ (gore desno) → „Instaliraj aplikaciju“ ili „Dodaj na početni ekran“ → Instaliraj.\n\nAko te opcije nema, aplikacija je možda već instalirana – potraži ikonicu HerdDoc.",
        "In Chrome tap ⋮ (top right) → “Install app” or “Add to Home screen” → Install.\n\nIf the option is missing, the app may already be installed – look for the HerdDoc icon."));
}

// ---------------------------------------------------------------- dobrodošlica
function dobrodoslica() {
  postaviVrh("HerdDoc", false); meni("");
  ekran.innerHTML = `<div class="dobrodoslica"><img src="ikone/ikona-192.png" alt=""><h2>HerdDoc</h2>
    <p class="mali">${t("Rodoslov stada, srodstvo i parenje – u štali, i bez interneta.", "Herd pedigree, relationship and mating – in the barn, even offline.")}</p></div>
    <div class="kart"><h2>${t("Kako počinješ", "How to start")}</h2><ol class="koraci">
      <li>${t("U programu HerdDoc na računaru otvori <b>Telefon</b> i klikni <b>Pošalji na telefon</b>.", "In HerdDoc on the computer open <b>Phone</b> and click <b>Send to phone</b>.")}</li>
      <li>${t("Fajl prebaci na telefon (Google Drive, Viber, kabl…).", "Move the file to the phone (Google Drive, Viber, cable…).")}</li>
      <li>${t("Ovde klikni <b>Učitaj sa računara</b> i izaberi taj fajl.", "Here, tap <b>Load from computer</b> and choose that file.")}</li></ol></div>
    ${dugmeInstalacije()}
    ${oblakPodesen() ? `<a class="dug glavno puno" href="#sinh">📱 ${t("Upari sa računarom (QR kod ili kod)", "Pair with computer (QR or code)")}</a><div style="height:10px"></div>` : ""}
    <button class="dug ${oblakPodesen() ? "" : "glavno"} puno" id="ucitaj">📂 ${t("Učitaj sa računara (fajl)", "Load from computer (file)")}</button>
    <div style="height:10px"></div>
    <div class="dugmad"><button class="dug" id="pocni">${t("Počni bez računara", "Start without computer")}</button>
      <select class="dug" id="jezik" aria-label="Language">${JEZICI_TEL.map(([k, n]) => `<option value="${k}"${k === S.jezik ? " selected" : ""}>🌐 ${n}</option>`).join("")}</select></div>`;
  $("#ucitaj").onclick = izaberiFajl;
  osveziInstalaciju();
  $("#pocni").onclick = () => { S.pocetak = true; sacuvaj(); idi("grla"); prikazi(); };
  $("#jezik").onchange = e => { izaberiJezik(e.target.value); dobrodoslica(); };
}

// ---------------------------------------------------------------- Grla
const izMem = k => { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } };
const filt = { q: "", pol: "", van: false, vrsta: izMem("herddoc-vrsta"), stado: izMem("herddoc-stado"),
  poreklo: izMem("herddoc-poreklo"), red: izMem("herddoc-red") };     // poreklo i redosled: broj (0, 1, 2…) – isti na svakom jeziku
const uMem = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* nije važno */ } };
function poredajGrla(g) {                       // kao na računaru: poslednje upisana, prvo upisana, po oznaci, najmlađa
  const r = +filt.red || 0;
  if (r === 2) return g.slice().sort((a, b) => sortKey(a.id, b.id));
  if (r === 3) return g.slice().sort((a, b) => (b.datum ? +b.datum : -1e15) - (a.datum ? +a.datum : -1e15) || b.rb - a.rb);
  if (r === 1) return g.slice().reverse();
  return g;
}
// dugmad za vrstu iznad liste (samo vrste koje postoje u stadu); izbor se pamti
function trakaVrsta(sva) {
  const broj = {};
  for (const a of sva) { const k = vrstaKanon(a.vrsta) || "drugo"; broj[k] = (broj[k] || 0) + (a.aktivno ? 1 : 0); }
  if (filt.vrsta && !(filt.vrsta in broj)) filt.vrsta = "";
  const imena = ["goveda", "ovce", "koze", "svinje", "konji"];
  const naziv = k => { const i = imena.indexOf(k); const n = i >= 0 ? K().VRSTE[i] : k === "drugo" ? t("ostalo", "other") : k; return n.charAt(0).toUpperCase() + n.slice(1); };
  const opcije = [["", t("Sve vrste", "All species"), Object.values(broj).reduce((x, y) => x + y, 0)]]
    .concat(imena.concat(mojeVrste().map(x => x.ime), ["drugo"]).filter(k => k in broj).map(k => [k, naziv(k), broj[k]]));
  return `<div class="filteri">${opcije.map(([k, n, c]) => `<button data-vr="${k}" class="${filt.vrsta === k ? "akt" : ""}">${h(n)} <span style="opacity:.7">${c}</span></button>`).join("")}</div>`;
}
function ekranGrla() {
  postaviVrh("HerdDoc", false); meni("grla");
  const sva = M.grla(false);
  const stada = [...new Set(sva.map(a => a.stado).filter(Boolean))].sort(sortKey);
  if (filt.stado && !stada.includes(filt.stado)) filt.stado = "";
  ekran.innerHTML = `${sva.length ? trakaVrsta(sva) : ""}<div class="sakam"><input class="pretraga" id="q" type="search" placeholder="🔍 ${t("Traži oznaku, markicu, rasu…", "Search tag, ear tag, breed…")}" value="${h(filt.q)}"><button type="button" class="kam" id="skenGrla" aria-label="${t("Skeniraj minđušu", "Scan ear tag")}">📷</button></div>
    <div class="filteri">${[["", t("Sva", "All")], ["z", t("Ženska", "Females")], ["m", t("Muška", "Males")]].map(([k, n]) =>
      `<button data-pol="${k}" class="${filt.pol === k ? "akt" : ""}">${n}</button>`).join("")}
      <button id="van" class="${filt.van ? "akt" : ""}">${t("i van zapata", "incl. out of herd")}</button>
      <button id="novo">＋ ${t("Novo grlo", "New animal")}</button></div>
    ${stada.length > 0 ? `<select id="stadoF" class="stado-izbor ${filt.stado ? "akt" : ""}"><option value="">🏠 ${t("Sva stada", "All herds")}</option>${stada.map(s => `<option value="${h(s)}"${s === filt.stado ? " selected" : ""}>🏠 ${h(s)}</option>`).join("")}</select>` : ""}
    <div class="dve-izbor"><select id="porF" class="stado-izbor ${filt.poreklo !== "" ? "akt" : ""}"><option value="">${t("Svako poreklo", "Any origin")}</option>${K().POREKLA.map((p, i) => `<option value="${i}"${String(i) === filt.poreklo ? " selected" : ""}>${h(p)}</option>`).join("")}</select>
      <select id="redF" class="stado-izbor">${K().REDOSLEDI.map((p, i) => `<option value="${i}"${i === (+filt.red || 0) ? " selected" : ""}>↕ ${h(p)}</option>`).join("")}</select></div><div id="sp"></div>`;
  const crtaj = (koliko = NA_STRANI) => {
    const q = norm(filt.q), ql = filt.q.trim().toLowerCase();
    const por = filt.poreklo !== "" ? K().POREKLA[+filt.poreklo] : "";
    const sp = poredajGrla(sva).filter(a => (!por || norm(a.poreklo) === norm(por)) && (filt.van || a.aktivno) && (!filt.pol || a.pol === filt.pol) && (!filt.vrsta || (vrstaKanon(a.vrsta) || "drugo") === filt.vrsta) && (!filt.stado || a.stado === filt.stado) &&
      (!q || norm(a.id).includes(q) || norm(a.markica).includes(q) || norm(a.rfid).includes(q) || a.stare.some(s => norm(s).includes(q)) || norm(a.stado).includes(q) || norm(a.poreklo_od).includes(q) || (ql && (a.rasa || "").includes(ql))));
    $("#sp").innerHTML = `<div class="mali" style="margin:0 4px 8px">${t(`${sp.length} grla`, `${sp.length} animals`)}</div>` +
      listaGrla(sp, sva.length ? t("Nema grla za ovu pretragu.", "No animals match.") : t("Stado je još prazno. Učitaj podatke sa računara ili dodaj grlo.", "The herd is empty. Load data from the computer or add an animal."), koliko);
    const jos = $("#sp [data-jos]");
    if (jos) jos.onclick = () => crtaj(+jos.dataset.jos);
  };
  $("#q").oninput = e => { filt.q = e.target.value; crtaj(); };
  // Bluetooth čitač minđuša (radi kao tastatura) upiše broj u pretragu i pritisne Enter -> karton grla
  $("#q").onkeydown = e => { if (e.key === "Enter") { const x = M.nadjiCitac(e.target.value.trim()); if (x) idi(`karton/${encodeURIComponent(x)}`); } };
  ekran.querySelectorAll("[data-pol]").forEach(b => b.onclick = () => { filt.pol = b.dataset.pol; ekranGrla(); });
  ekran.querySelectorAll("[data-vr]").forEach(b => b.onclick = () => {
    filt.vrsta = b.dataset.vr;
    try { localStorage.setItem("herddoc-vrsta", filt.vrsta); } catch (e) { /* nije važno */ }
    ekranGrla();
  });
  const aktV = ekran.querySelector("[data-vr].akt");          // izabrana vrsta uvek vidljiva u traci
  if (aktV && aktV.parentNode) aktV.parentNode.scrollLeft = Math.max(0, aktV.offsetLeft - 12);
  $("#van").onclick = () => { filt.van = !filt.van; ekranGrla(); };
  $("#porF").onchange = e => { filt.poreklo = e.target.value; uMem("herddoc-poreklo", filt.poreklo); ekranGrla(); };
  $("#redF").onchange = e => { filt.red = e.target.value; uMem("herddoc-red", filt.red); ekranGrla(); };
  if ($("#stadoF")) $("#stadoF").onchange = e => {
    filt.stado = e.target.value;
    try { localStorage.setItem("herddoc-stado", filt.stado); } catch (er) { /* nije važno */ }
    ekranGrla();
  };
  $("#novo").onclick = () => idi("novo");
  $("#skenGrla").onclick = skenirajIOtvori;
  crtaj();
}

// ---------------------------------------------------------------- Karton
function ekranKarton(id) {
  const a = M.A[id];
  if (!a) { postaviVrh(t("Grlo", "Animal"), true); ekran.innerHTML = `<div class="prazno">${t("Grlo nije pronađeno.", "Animal not found.")}</div>`; return; }
  postaviVrh(id, true); meni("grla");
  const [o, m] = M.P[id] || [null, null], f = M.inbr(id), [ftekst, fkl] = procena(f, S.prag);
  const preci2 = [o, m].flatMap(p => (p ? M.P[p] || [null, null] : [null, null]));
  const deca = M.deca(id).sort(sortKey);
  const kar = opisKarence(id), ob = obavestenja(id);
  const posl = cekajuPorodjaj(id).filter(z => roditeljiParenja(z)[0] === id || roditeljiParenja(z)[1] === id);
  const ist = istorijaZa(id);
  ekran.innerHTML = `<div class="kart"><div style="display:flex;gap:12px;align-items:center;margin-bottom:12px">${cip(id, false).replace("cip", "cip veliki")}
      <div><b>${h(M.polNaziv(id))}</b><div class="mali">${h([a.vrsta, a.rasa, a.namena, a.autohtona ? t("autohtona rasa", "native breed") : ""].filter(Boolean).join(" · "))}</div></div></div>
    <dl class="polja">
      ${a.markica ? `<dt>${t("Markica", "Ear tag")}</dt><dd>${h(a.markica)}</dd>` : ""}
      ${a.stare.length ? `<dt>${t("Ranije markice", "Previous ear tags")}</dt><dd class="mali">${h(a.stare.join(", "))}</dd>` : ""}
      ${a.rfid ? `<dt>RFID</dt><dd>${h(a.rfid)}</dd>` : ""}
      <dt>${t("Rođen", "Born")}</dt><dd>${a.datum ? `${fmtD(a.datum)} (${h(fmtStarost(starostMeseci(a.datum)))})` : "–"}</dd>
      ${a.stado ? `<dt>${t("Stado", "Herd")}</dt><dd>${h(a.stado)}</dd>` : ""}
      ${a.poreklo ? `<dt>${t("Poreklo", "Origin")}</dt><dd>${h(a.poreklo + (a.poreklo_od ? " – " + a.poreklo_od : ""))}</dd>` : ""}
      <dt>${t("Inbriding", "Inbreeding")}</dt><dd><span class="znak ${f ? fkl : "ok"}">${pct(f)}</span> <span class="mali">${f ? h(ftekst) : ""}</span></dd>
      <dt>Status</dt><dd>${a.aktivno ? t("u zapatu", "in herd") : `<span class="znak siv">${t("van zapata", "out of herd")}</span>`}</dd>
    </dl>
    ${a.napomena ? `<div class="info nap" style="margin:12px 0 0">⚠ <b>${h(a.napomena)}</b></div>` : ""}
    ${(() => { const pp = proveraPorekla(id); if (!pp || (pp[0] !== false && pp[1] !== false)) return "";
      const d = (pp[0] === false ? [t(`otac ${o || "?"}`, `sire ${o || "?"}`)] : []).concat(pp[1] === false ? [t(`majka ${m || "?"}`, `dam ${m || "?"}`)] : []);
      return `<div class="info bad" style="margin:12px 0 0">🧬 <b>${t("DNK test isključio: ", "DNA test excluded: ")}${h(d.join(", "))}</b>${t(" – proveri roditelje.", " – check the parents.")}</div>`; })()}
    ${kar ? `<div class="info bad" style="margin:12px 0 0">⚠ ${t("Karenca", "Withdrawal")}: ${h(kar)}</div>` : ""}
    ${posl.map(z => `<div class="info siv" style="margin:12px 0 0">${t("Parenje", "Mating")} ${h(z.datum)} · ${h(opisIshoda(z))}</div>`).join("")}
  </div>
  <div class="dugmad" style="margin-bottom:12px">
    <a class="dug glavno" href="#dogadjaj?grlo=${encodeURIComponent(id)}">＋ ${t("Upiši događaj", "Record event")}</a>
    <a class="dug" href="#podsetnik?grlo=${encodeURIComponent(id)}">⏰ ${t("Podsetnik", "Reminder")}</a>
    <a class="dug" href="#novo?izmena=${encodeURIComponent(id)}">✎ ${t("Izmeni podatke", "Edit details")}</a>
    <a class="dug" href="#rodoslov/${encodeURIComponent(id)}">🖨 ${t("Rodoslovni list", "Pedigree")}</a>
    ${a.pol ? `<a class="dug" href="#parenje/${encodeURIComponent(id)}">⚭ ${t("Partneri", "Partners")}</a>` : ""}
    <a class="dug" href="#srodstvo?a=${encodeURIComponent(id)}">${t("Srodstvo", "Relationship")}</a>
    <button class="dug" id="napBtn">⚠ ${a.napomena ? t("Izmeni napomenu", "Edit note") : t("Dodaj napomenu", "Add note")}</button></div>
  ${ob.length ? `<div id="ob">${ob.map(kartObavestenja).join("")}</div>` : ""}
  <div class="kart"><h2>${t("Roditelji", "Parents")}</h2><div class="cipovi">${o ? cip(o) : `<span class="mali">${t("otac nepoznat", "sire unknown")}</span>`} ${m ? cip(m) : `<span class="mali">${t("majka nepoznata", "dam unknown")}</span>`}</div>
    ${preci2.some(Boolean) ? `<h2 style="margin-top:14px">${t("Babe i dede", "Grandparents")}</h2><div class="cipovi">${preci2.map(p => (p ? cip(p) : `<span class="cip siv">?</span>`)).join("")}</div>` : ""}
  </div>
  ${kartPrirasta(id)}
  ${kartOcene(id)}
  ${kartDnk(id)}
  ${kartMleka(id, a)}
  <div class="kart"><h2>${t("Potomci", "Offspring")} <small>(${deca.length})</small></h2>${deca.length ? `<div class="cipovi">${deca.map(d => cip(d)).join("")}</div>` : `<span class="mali">${t("nema upisanih", "none recorded")}</span>`}</div>
  <div class="kart"><h2>${t("Istorija", "History")} <small>(${ist.length})</small></h2>${ist.length ? ist.slice(0, 60).map(z =>
    `<div class="ist ${z.automatski ? "auto" : ""}"><div class="d">${h(z.datum)}${z.partner ? " · " + cip(z.partner) : ""}${z.upisao ? ` · 📱 ${h(z.upisao)}` : ""}</div><b>${h(z.dogadjaj)}</b>${z.vrednost ? ` – ${h(z.vrednost)}` : ""}
      ${z.opis ? `<div class="mali">${h(z.opis)}</div>` : ""}${opisIshoda(z) ? `<div class="mali">${h(opisIshoda(z))}</div>` : ""}</div>`).join("") : `<span class="mali">${t("još nema zapisa", "no records yet")}</span>`}</div>`;
  if (ob.length) vezAkcije($("#ob"), ob);
  $("#napBtn").onclick = () => {
    const v = prompt(t("Napomena o grlu – vidi se svuda gde je grlo (prazno = ukloni):", "Note about the animal – shown wherever the animal appears (empty = remove):"), a.napomena || "");
    if (v === null) return;
    postaviNapomenu(id, v);
    promena(t("Napomena sačuvana.", "Note saved."));
    ekranKarton(id);
  };
}

// ---------------------------------------------------------------- Mlečnost
function kartDnk(id) {
  const zap = dnkZapisi(id), pp = proveraPorekla(id), [o, m] = M.P[id] || [null, null];
  let por = "";
  if (pp) {
    const [ook, mok] = pp;
    if (ook !== null) por += `<div class="info ${ook ? "ok" : "bad"}" style="margin:6px 0">${ook ? "✓" : "⚠"} ${t("Poreklo po DNK", "Parentage by DNA")}: ${ook ? t(`otac ${h(o || "?")} potvrđen`, `sire ${h(o || "?")} confirmed`) : t(`otac ${h(o || "?")} ISKLJUČEN`, `sire ${h(o || "?")} EXCLUDED`)}</div>`;
    if (mok !== null) por += `<div class="info ${mok ? "ok" : "bad"}" style="margin:6px 0">${mok ? "✓" : "⚠"} ${t("Poreklo po DNK", "Parentage by DNA")}: ${mok ? t(`majka ${h(m || "?")} potvrđena`, `dam ${h(m || "?")} confirmed`) : t(`majka ${h(m || "?")} ISKLJUČENA`, `dam ${h(m || "?")} EXCLUDED`)}</div>`;
  }
  const red = zap.slice(0, 8).map(z => {
    const fajlovi = String(z.fajl || "").split("|").filter(Boolean), naTel = fajlovi.filter(f => S.slike && S.slike[f]), naPc = fajlovi.length - naTel.length;
    return `<div style="padding:6px 0;border-bottom:1px solid var(--surf2)"><span class="mali">${h(z.datum)}</span> <b>${h(prevediVr(z.vrednost))}</b>: ${h(prevediVr(z.opis))}
    ${(z.lab || z.uzorak || naPc) ? `<div class="mali">${h([z.lab, prevediVr(z.uzorak || "")].filter(Boolean).join(" · "))}${naPc ? ` · 📎 ${naPc} ${t("na računaru", "on the computer")}` : ""}</div>` : ""}
    ${z.izvestaj ? `<details class="mali"><summary>${t("Tekst izveštaja", "Report text")}</summary><div style="white-space:pre-wrap">${h(z.izvestaj)}</div></details>` : ""}
    ${naTel.length ? `<div class="cipovi" style="margin-top:6px">${naTel.map(f => `<img data-slika="${h(f)}" src="${S.slike[f]}" style="width:72px;height:72px;object-fit:cover;border-radius:8px">`).join("")}</div>` : ""}</div>`;
  }).join("");
  return `<div class="kart"><h2>🧬 ${t("DNK testovi", "DNA tests")}</h2>${por}${red || `<span class="mali">${t("nema upisanih", "none recorded")}</span>`}
    <a class="dug puno" style="margin-top:10px" href="#dnk?grlo=${encodeURIComponent(id)}">＋ ${t("Dodaj DNK test", "Add DNA test")}</a></div>`;
}
document.addEventListener("click", e => {          // slika DNK nalaza preko celog ekrana
  const im = e.target.closest && e.target.closest("img[data-slika]");
  if (!im) return;
  const o = document.createElement("div");
  o.style.cssText = "position:fixed;inset:0;z-index:50;background:#000e;display:grid;place-items:center";
  o.innerHTML = `<img src="${im.src}" style="max-width:100%;max-height:100%">`;
  o.onclick = () => o.remove();
  document.body.appendChild(o);
});
function ekranDnk(_, upit) {
  const x = M.nadji(upit && upit.get("grlo") || ""), k = K();
  postaviVrh(t("DNK test", "DNA test") + (x ? ` – ${x}` : ""), true); meni("grla");
  if (!x) { ekran.innerHTML = `<div class="prazno">${t("Grlo nije pronađeno.", "Animal not found.")}</div>`; return; }
  const [o, m] = M.P[x] || [null, null], labs = [...new Set(S.istorija.map(z => z.lab).filter(Boolean))];
  ekran.innerHTML = `<div class="kart">
    <label class="polje"><span>${t("Datum uzorkovanja *", "Sampling date *")}</span><input class="unos" id="d" type="date" value="${uIso(danas())}"></label>
    <label class="polje"><span>${t("Vrsta testa *", "Test type *")}</span><select class="unos" id="tip">${k.DNK_TESTOVI.map(v => `<option>${h(v)}</option>`).join("")}</select></label>
    <label class="polje"><span>${t("Laboratorija", "Laboratory")}</span><input class="unos" id="lab" list="dl-lab"><datalist id="dl-lab">${labs.map(l => `<option value="${h(l)}">`).join("")}</datalist></label>
    <label class="polje"><span>${t("Uzorak", "Sample")}</span><select class="unos" id="uz"><option value=""></option>${k.DNK_UZORCI.map(v => `<option>${h(v)}</option>`).join("")}</select></label>
    <label class="polje"><span>${t("Rezultat *", "Result *")}</span><input class="unos" id="rez" list="dl-rez"><datalist id="dl-rez"></datalist></label>
    <div class="mali">${t(`Upisani roditelji: otac ${h(o || "?")}, majka ${h(m || "?")}`, `Recorded parents: sire ${h(o || "?")}, dam ${h(m || "?")}`)}</div>
    <label class="polje"><span>${t("Tekst izveštaja", "Report text")}</span><textarea class="unos" id="izv" rows="5" placeholder="${t("nalepi tekst iz mejla ili nalaza", "paste the text from the e-mail or report")}"></textarea></label>
    <div class="polje"><span class="mali" style="font-weight:700">${t("Slike rezultata", "Pictures of the result")}</span>
      <div class="cipovi" id="prev" style="margin:6px 0"></div>
      <label class="dug puno" style="text-align:center">📷 ${t("Slikaj ili izaberi sliku", "Take or choose a picture")}<input type="file" id="foto" accept="image/*" capture="environment" multiple class="skriveno"></label>
      <button class="dug puno skriveno" id="ocr" style="margin-top:8px">🔎 ${t("Prepiši tekst sa slike", "Copy text from the picture")}</button>
      <div class="info skriveno" id="ocrst" style="margin:8px 0 0"></div>
      <div class="mali">${t("PDF nalaz se prilaže na računaru – tamo se i tekst iz PDF-a prepisuje tačno.", "A PDF report is attached on the computer – there the text from the PDF is copied exactly.")}</div></div>
    <div class="greska" id="gr"></div><button class="dug glavno puno" id="sac">${t("Sačuvaj", "Save")}</button></div>`;
  const tip = () => { $("#dl-rez").innerHTML = $("#tip").value === k.DNK_PROVERA ? k.DNK_POREKLO.map(v => `<option value="${h(v)}">`).join("") : ""; };
  $("#tip").onchange = tip; tip();
  const slike = [], originali = [];          // [data URL] – nove slike ovog testa; originali – za čitanje teksta (oštrije)
  let procitano = false;
  const stOcr = (klasa, tekst) => { const e = $("#ocrst"); e.className = "info " + klasa; e.textContent = tekst; };
  const prikaziSlike = () => { $("#ocr").classList.toggle("skriveno", !slike.length); $("#prev").innerHTML = slike.map((s, i) => `<span style="position:relative"><img src="${s}" style="width:84px;height:84px;object-fit:cover;border-radius:10px"><button data-ukloni="${i}" style="position:absolute;top:2px;right:2px;border:0;border-radius:10px;background:#000a;color:#fff">✕</button></span>`).join(""); };
  $("#prev").onclick = e => { const b = e.target.closest("[data-ukloni]"); if (b) { slike.splice(+b.dataset.ukloni, 1); originali.splice(+b.dataset.ukloni, 1); prikaziSlike(); } };
  $("#foto").onchange = async e => {
    for (const f of e.target.files) { try { slike.push(await smanjiSliku(f)); originali.push(f); } catch (er) { poruka(t("Slika ne može da se učita.", "The picture cannot be loaded.")); } }
    e.target.value = ""; prikaziSlike();
  };
  $("#ocr").onclick = async () => {
    const dug = $("#ocr");
    if (!navigator.onLine && !window.Tesseract) return stOcr("bad", t("Za čitanje teksta sa slike potreban je internet (prvi put se preuzima oko 10 MB).", "Reading text from a picture needs the internet (about 10 MB is downloaded the first time)."));
    dug.disabled = true; stOcr("siv", t("Čitam tekst sa slike…", "Reading the text from the picture…"));
    try {
      const tekstovi = await procitajSlike(originali, p => stOcr("siv", t(`Čitam tekst sa slike… ${Math.round(p * 100)}%`, `Reading the text from the picture… ${Math.round(p * 100)}%`)));
      const novo = tekstovi.map(srediTekst).filter(Boolean).join("\n\n");
      if (!novo) return stOcr("bad", t("Na slici nije pronađen tekst. Slikaj nalaz ravno, oštro i pri dobrom svetlu, ili upiši tekst ručno.", "No text was found on the picture. Photograph the report flat, sharp and in good light, or type the text in."));
      const izv = $("#izv"), staro = izv.value.trim();
      if (!staro.includes(novo)) izv.value = (staro ? staro + "\n\n" : "") + novo;
      procitano = true;
      stOcr("warn", t("⚠ Tekst je prepoznat sa slike. Program može da pogreši slovo ili broj – proveri tekst i upiši rezultat.", "⚠ The text was recognised from a picture. The program can misread a letter or a number – check the text and enter the result."));
    } catch (er) {
      stOcr("bad", er && er.message === "mreza" ? t("Za čitanje teksta sa slike potreban je internet (prvi put se preuzima oko 10 MB).", "Reading text from a picture needs the internet (about 10 MB is downloaded the first time).")
        : t("Tekst sa slike nije mogao da se pročita. Upiši ga ručno.", "The text could not be read from the picture. Type it in."));
    } finally { dug.disabled = false; }
  };
  $("#sac").onclick = () => {
    const d = parsirajDatum($("#d").value), izv = $("#izv").value.trim();
    let rez = $("#rez").value.trim().split(/\s+/).join(" ");
    if (!rez && procitano) return ($("#gr").textContent = t("Upiši rezultat – pogledaj ga u tekstu nalaza.", "Enter the result – find it in the report text."));
    if (!rez && izv) rez = izv.split("\n")[0].slice(0, 120);       // samo tekst izveštaja: rezultat = prvi red
    if (!d || !rez) return ($("#gr").textContent = t("Upiši vrstu testa i rezultat.", "Enter the test type and the result."));
    const imena = slike.map((s, i) => `${x}_${uIso(d)}_${Date.now().toString(36)}${i}.jpg`.replace(/[^\w.\- ]/g, "_"));
    imena.forEach((ime, i) => { S.slike[ime] = slike[i]; });
    const z = dodaj(x, k.DNK, { datum: fmtD(d), vrednost: $("#tip").value, opis: rez, lab: $("#lab").value.trim(), uzorak: $("#uz").value });
    z.fajl = imena.join("|"); z.izvestaj = izv;
    zabelezi(`${x}: ${k.DNK} – ${rez}`);
    promena(t(`Upisan DNK test – ${x}`, `DNA test recorded – ${x}`)); idi(`karton/${encodeURIComponent(x)}`);
  };
}
// Čitanje teksta sa slike nalaza (Tesseract.js, Apache 2.0). Učitava se tek kad zatreba, sa interneta (~10 MB prvi put).
const TESSERACT_URL = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";
const OCR_JEZICI = { sr: "srp_latn+eng", en: "eng", de: "deu+eng", fr: "fra+eng", es: "spa+eng", pt: "por+eng" };
let _tesseract = null;
function ucitajTesseract() {
  if (window.Tesseract) return Promise.resolve();
  return _tesseract || (_tesseract = new Promise((ok, ne) => {
    const s = document.createElement("script");
    s.src = TESSERACT_URL; s.crossOrigin = "anonymous"; s.onload = ok;
    s.onerror = () => { _tesseract = null; s.remove(); ne(new Error("mreza")); };
    document.head.appendChild(s);
  }));
}
async function procitajSlike(fajlovi, napredak) {
  await ucitajTesseract();
  let i = 0;
  const w = await Tesseract.createWorker(OCR_JEZICI[S.jezik] || "eng", 1,
    { logger: m => { if (m.status === "recognizing text") napredak((i + m.progress) / fajlovi.length); } });
  try {
    const out = [];
    for (; i < fajlovi.length; i++) {
      const slika = await smanjiSliku(fajlovi[i], 2400, 0.92);      // dovoljno oštro, a telefon ne čita predugo
      out.push((await w.recognize(slika)).data.text || "");
    }
    return out;
  } finally { w.terminate(); }
}
function srediTekst(s) {
  return String(s || "").replace(/\r/g, "").split("\n").map(r => r.split(/\s+/).filter(Boolean).join(" "))
    .join("\n").replace(/\n{3,}/g, "\n\n").trim();
}
// ---------------------------------------------------------------- ocene grla (kao na računaru)
function kartOcene(id) {
  const o = oceneGrla(id), dec = v => v.toFixed(1).replace(".", EN() ? "." : ",");
  const nOc = Object.keys(procitajOcene((S.grla.find(g => g.id === id) || {}).ocena)).length;
  const redovi = rucneOsobine().filter(([k]) => k in o.rucne).map(([k, n]) => `<dt>${h(n)}</dt><dd style="color:var(--warn)">${zvezdice(o.rucne[k])}${o.rucne[k] % 1 ? ` <span class="mali">${dec(o.rucne[k])}</span>` : ""}</dd>`)
    .concat(autoOsobine().filter(([k]) => k in o.auto).map(([k, n]) => `<dt>${h(n)}</dt><dd><span style="color:var(--warn)">${zvezdice(o.auto[k][0])}</span> <span class="mali">${h(o.auto[k][1])}</span></dd>`));
  return `<div class="kart"><h2>⭐ ${t("Ocena grla", "Animal score")} ${o.ukupno != null ? `<span style="color:var(--warn)">${zvezdice(o.ukupno)} ${dec(o.ukupno)}</span>` : ""}</h2>
    ${nOc > 1 ? `<p class="mali" style="margin:0 0 6px">${t(`prosek ${nOc} ocenjivača`, `average of ${nOc} scorers`)}</p>` : ""}<dl class="polja">${redovi.join("")}</dl>
    ${Object.keys(o.rucne).length ? "" : `<p class="mali">${t("Karakter, građa, noge… još nisu ocenjeni.", "Temperament, conformation, legs… not scored yet.")}</p>`}
    <div class="dugmad" style="margin-top:10px"><a class="dug" href="#oceni/${encodeURIComponent(id)}">⭐ ${t("Oceni", "Score")}</a><a class="dug" href="#rang">${t("Rang lista", "Ranking")}</a></div></div>`;
}
function ekranOceni(id) {
  const x = M.nadji(id);
  if (!x) return idi("grla");
  postaviVrh(t(`Oceni: ${x}`, `Score: ${x}`), true); meni("grla");
  if (!korisnik()) { traziIme(); return idi(`karton/${encodeURIComponent(x)}`); }
  const sve = procitajOcene((S.grla.find(g => g.id === x) || {}).ocena), oc = { ...((sve[korisnik()] || [{}])[0]) };
  const drugi = Object.entries(sve).filter(([i]) => i !== korisnik());
  const osobine = rucneOsobine().filter(([k, , , samoZ]) => !samoZ || (M.A[x].pol === "z" && (k !== "vime" || vimeSeOcenjuje(x))));
  ekran.innerHTML = `<div class="kart"><p style="margin:0 0 4px"><b>👤 ${h(korisnik())}</b></p>
    <p class="mali" style="margin-top:0">${t("Svako ocenjuje za sebe – na kraju se računa prosek svih ocena.", "Everyone scores for themselves – the average of all scores counts.")}
    ${t("Dodirni zvezdice (1 = loše, 5 = odlično). Ponovni dodir iste zvezdice briše ocenu.", "Tap the stars (1 = poor, 5 = excellent). Tapping the same star again clears it.")}</p>
    ${drugi.length ? `<p class="mali">${t("Ocenili su i:", "Also scored by:")} ${drugi.map(([i, [o_]]) => `<b>${h(i || t("ranije", "earlier"))}</b> (${Object.entries(o_).map(([k, v]) => `${(rucneOsobine().find(r => r[0] === k) || [k, k])[1].split(" (")[0]} ${v}`).join(", ")})`).join("; ")}</p>` : ""}
    ${osobine.map(([k, n, opis]) => `<div class="polje"><b>${h(n)}</b><div class="mali">${h(opis)}</div>
      <div class="zvezde" data-k="${k}">${[1, 2, 3, 4, 5].map(i => `<button data-v="${i}" aria-label="${i}">☆</button>`).join("")}</div></div>`).join("")}
    <p class="mali">${t("Prirast, plodnost i zdravlje program računa sam iz merenja, porođaja i lečenja.", "Gain, fertility and health are calculated from weighings, births and treatments.")}</p>
    <button class="dug glavno puno" id="sac">${t("Sačuvaj ocenu", "Save score")}</button></div>`;
  const crtaj = () => ekran.querySelectorAll(".zvezde").forEach(z => z.querySelectorAll("button").forEach(b => { const on = +b.dataset.v <= (oc[z.dataset.k] || 0); b.textContent = on ? "★" : "☆"; b.classList.toggle("akt", on); }));
  ekran.querySelectorAll(".zvezde").forEach(z => z.onclick = e => { const b = e.target.closest("button"); if (!b) return; const v = +b.dataset.v; if (oc[z.dataset.k] === v) delete oc[z.dataset.k]; else oc[z.dataset.k] = v; crtaj(); });
  crtaj();
  $("#sac").onclick = () => { sacuvajOcene(x, oc); promena(t("Ocena je sačuvana.", "Score saved.")); idi(`karton/${encodeURIComponent(x)}`); };
}
// ---------------------------------------------------------------- Moje rase (kao na računaru): rasa se upiše jednom
function ekranRase(_, upit) {
  postaviVrh(t("Moje rase", "My breeds"), true); meni("vise");
  const k = K(), izm = upit && upit.get("i") != null ? mojeRase()[+upit.get("i")] : null;
  const vrste = [...new Set(k.VRSTE.concat(mojeVrste().map(v => v.ime)))];
  const sve = mojeRase().map((r, i) => [r, i]).sort((a, b) => (a[0].vrsta + a[0].ime).localeCompare(b[0].vrsta + b[0].ime));
  ekran.innerHTML = `<div class="kart"><h2>${izm ? t(`Izmena: ${h(izm.ime)}`, `Editing: ${h(izm.ime)}`) : t("Nova rasa", "New breed")}</h2>
    <p class="mali" style="margin-top:0">${t("Rasu upišeš jednom, sa namenom. Posle je kod novog grla samo izabereš, a namena se sama popuni.", "Enter a breed once, with its purpose. Then just pick it for a new animal and the purpose fills in.")}</p>
    <div class="dve"><label class="polje"><span>${t("Vrsta *", "Species *")}</span><select class="unos" id="rv">${vrste.map(v => `<option ${izm && vrstaKanon(izm.vrsta) === vrstaKanon(v) ? "selected" : ""}>${h(v)}</option>`).join("")}</select></label>
      <label class="polje"><span>${t("Naziv rase *", "Breed name *")}</span><input class="unos" id="ri" value="${h(izm ? izm.ime : "")}"></label></div>
    <label class="polje" id="rn-p"><span>${t("Namena", "Purpose")}</span><select class="unos" id="rn"></select></label>
    <label class="polje" style="display:flex;align-items:center;gap:10px"><input type="checkbox" id="ra" style="width:22px;height:22px" ${izm && izm.autohtona ? "checked" : ""}><span style="font-weight:700">${t("Autohtona rasa", "Native breed")}</span></label>
    <div class="greska" id="gr"></div>
    <div class="dugmad">${izm ? `<a class="dug" href="#rase">${t("Otkaži", "Cancel")}</a><button class="dug" id="rs">${t("Skloni sa spiska", "Remove from list")}</button>` : ""}<button class="dug glavno" id="sac">${t("Sačuvaj rasu", "Save breed")}</button></div></div>
    <div class="kart"><h2>${t("Spisak", "List")} <small>(${sve.length})</small></h2>${sve.length ? `<div class="lista">${sve.map(([r, i]) =>
      `<a class="red" href="#rase?i=${i}"><div class="sred"><b>${h(r.ime)}${r.autohtona ? " ★" : ""}</b><span>${h(vrstaNorm(r.vrsta) || r.vrsta)} · ${h(r.namena || "–")} · ${t(`${grlaRase(r.vrsta, r.ime).length} grla`, `${grlaRase(r.vrsta, r.ime).length} animals`)}</span></div><span>✎</span></a>`).join("")}</div>`
      : `<span class="mali">${t("Još nema rasa.", "No breeds yet.")}</span>`}</div>`;
  const namene = () => { const izb = nameneZa($("#rv").value), sad = $("#rn").value || (izm ? izm.namena : "");
    $("#rn-p").classList.toggle("skriveno", !izb.length);
    $("#rn").innerHTML = `<option value="">${t("– izaberi –", "– choose –")}</option>` + izb.map(x => `<option ${x === sad ? "selected" : ""}>${h(x)}</option>`).join(""); };
  $("#rv").onchange = namene; namene();
  $("#ri").oninput = () => { if (autohtonaRasa($("#ri").value)) $("#ra").checked = true; };
  $("#sac").onclick = () => {
    const v = { vrsta: $("#rv").value, ime: $("#ri").value, namena: $("#rn").value, autohtona: $("#ra").checked };
    const pogodjena = grlaRase(v.vrsta, v.ime).filter(r => v.namena && (r.namena || "") !== v.namena).length + (izm && kljucR(izm) !== kljucR(v) ? grlaRase(izm.vrsta, izm.ime).length : 0);
    if (pogodjena && !confirm(t(`Promena važi i za ${pogodjena} grla te rase. Nastaviti?`, `The change also applies to ${pogodjena} animals of this breed. Continue?`))) return;
    const rez = sacuvajRasu(v, izm);
    if (typeof rez === "string") return ($("#gr").textContent = rez);
    promena(t(`Rasa „${normRasa(v.ime)}“ je sačuvana.`, `Breed “${normRasa(v.ime)}” saved.`));
    idi("rase");
  };
  if (izm) $("#rs").onclick = () => { if (confirm(t(`Skloniti rasu „${izm.ime}“ sa spiska? Grla zadržavaju svoju rasu.`, `Remove the breed “${izm.ime}” from the list? Animals keep their breed.`))) { skloniRasu(izm); promena(t("Rasa je sklonjena sa spiska.", "Breed removed from the list.")); idi("rase"); } };
}
const kljucR = r => `${vrstaKanon(r.vrsta) || r.vrsta}|${String(r.ime || "").trim().toLowerCase()}`;
// ---------------------------------------------------------------- Moje vrste (kao na računaru)
function ekranVrste(_, upit) {
  postaviVrh(t("Moje vrste", "My species"), true); meni("vise");
  const izm = upit && upit.get("v") ? mojeVrste().find(v => v.ime === upit.get("v")) : null;
  const polja = [["ime", t("Naziv vrste (množina) *", "Species name (plural) *"), "text"], ["m", t("Mužjak", "Male"), "text"], ["z", t("Ženka", "Female"), "text"],
    ["ml", t("Mladunče", "Young (one)"), "text"], ["mlm", t("Mladunčad", "Young (many)"), "text"], ["gmin", t("Gravidnost od (dana) *", "Gestation from (days) *"), "number"],
    ["gmax", t("Gravidnost do (dana) *", "Gestation to (days) *"), "number"], ["gpr", t("Gravidnost prosek (dana) *", "Gestation average (days) *"), "number"],
    ["ciklus", t("Ciklus teranja (dana, 0 = bez)", "Heat cycle (days, 0 = none)"), "number"]];
  ekran.innerHTML = `<div class="kart"><h2>${izm ? t(`Izmena: ${h(izm.ime)}`, `Editing: ${h(izm.ime)}`) : t("Nova vrsta", "New species")}</h2>
    ${izm ? "" : `<p class="mali" style="margin-top:0">${t("Brzi primeri – dodirni i sve se popuni:", "Quick examples – tap and everything fills in:")}</p><div class="filteri">${primeriVrsta().map((p, i) => `<button data-pr="${i}">${h(p[0])}</button>`).join("")}</div>`}
    ${polja.map(([k, n, tip]) => `<label class="polje"><span>${n}</span><input class="unos" id="v_${k}" type="${tip}" ${tip === "number" ? 'inputmode="numeric"' : ""} value="${h(izm ? izm[k] : (k === "ciklus" ? "0" : ""))}"></label>`).join("")}
    <div class="greska" id="gr"></div>
    <div class="dugmad">${izm ? `<a class="dug" href="#vrste">${t("Otkaži", "Cancel")}</a><button class="dug" id="vs">${t("Skloni", "Remove")}</button>` : ""}<button class="dug glavno" id="sac">${t("Sačuvaj vrstu", "Save species")}</button></div></div>
    <div class="kart"><h2>${t("Moje vrste", "My species")} <small>(${mojeVrste().length})</small></h2>${mojeVrste().length ? `<div class="lista">${mojeVrste().map(v =>
      `<a class="red" href="#vrste?v=${encodeURIComponent(v.ime)}"><div class="sred"><b>${h(v.ime)}</b><span>${h(v.z)} · ${h(v.m)} · ${t(`gravidnost ${v.gpr} d.`, `gestation ${v.gpr} d.`)}</span></div><span>✎</span></a>`).join("")}</div>`
      : `<span class="mali">${t("Osnovne vrste (goveda, ovce, koze, svinje, konji) su već tu. Ovde dodaješ druge.", "Basic species (cattle, sheep, goats, pigs, horses) are already there. Add others here.")}</span>`}</div>`;
  ekran.querySelectorAll("[data-pr]").forEach(b => b.onclick = () => { const p = primeriVrsta()[+b.dataset.pr];
    ["ime", "m", "z", "ml", "mlm", "gmin", "gmax", "gpr", "ciklus"].forEach((k, i) => { $("#v_" + k).value = p[i]; }); });
  $("#sac").onclick = () => {
    const v = {}; ["ime", "m", "z", "ml", "mlm", "gmin", "gmax", "gpr", "ciklus"].forEach(k => { v[k] = $("#v_" + k).value; });
    const g = sacuvajVrstu(v, izm ? izm.ime : null);
    if (g) return ($("#gr").textContent = g);
    promena(t("Vrsta je sačuvana.", "Species saved.")); idi("vrste");
  };
  if (izm) $("#vs").onclick = () => { const g = skloniVrstu(izm.ime); if (g) return ($("#gr").textContent = g); promena(t("Vrsta je sklonjena.", "Species removed.")); idi("vrste"); };
}

// ---------------------------------------------------------------- Finansije (kao na računaru)
const filtF = { period: "mesec" };
function ekranFinansije() {
  postaviVrh(t("Finansije", "Finances"), true); meni("vise");
  const [od, doo] = periodFin(filtF.period), lista = finUPeriodu(od, doo), z = zbirFin(lista), raz = z.pr - z.tr;
  const per = [["mesec", t("Ovaj mesec", "This month")], ["prosli_mesec", t("Prošli mesec", "Last month")], ["godina", t("Ova godina", "This year")],
    ["prosla_godina", t("Prošla godina", "Last year")], ["sve", t("Sve", "All")]];
  const kat = Object.entries(z.kat).sort((a, b) => b[1] - a[1]), mx = Math.max(1, ...kat.map(([, v]) => v));
  ekran.innerHTML = `<div class="filteri">${per.map(([k, n]) => `<button data-per="${k}" class="${filtF.period === k ? "akt" : ""}">${n}</button>`).join("")}</div>
    <div class="kart"><dl class="polja"><dt>${t("Prihodi", "Income")}</dt><dd style="color:var(--ok)">${fmtNovac(z.pr)}</dd>
      <dt>${t("Troškovi", "Costs")}</dt><dd style="color:var(--bad)">${fmtNovac(z.tr)}</dd>
      <dt>${t("Razlika", "Balance")}</dt><dd style="color:var(--${raz >= 0 ? "ok" : "bad"});font-size:18px">${raz >= 0 ? "+" : "−"}${fmtNovac(Math.abs(raz))}</dd></dl>
      <div class="dugmad" style="margin-top:12px"><a class="dug glavno" href="#finupis?v=trosak">− ${t("Trošak", "Cost")}</a><a class="dug glavno" href="#finupis?v=prihod">+ ${t("Prihod", "Income")}</a></div></div>
    ${kat.length ? `<div class="kart"><h2>${t("Po kategoriji", "By category")}</h2>${kat.map(([k, v]) => `<div style="margin:8px 0"><div class="mali" style="display:flex;justify-content:space-between"><span>${h(k.slice(1))}</span><b>${fmtNovac(v)}</b></div>
      <div style="height:8px;border-radius:4px;background:var(--line)"><div style="height:8px;border-radius:4px;width:${Math.round(v / mx * 100)}%;background:var(--${k[0] === "+" ? "ok" : "bad"})"></div></div></div>`).join("")}</div>` : ""}
    <div class="kart"><h2>${t("Upisi", "Entries")} <small>(${lista.length})</small></h2>${lista.length ? `<div class="lista">${lista.slice(0, 200).map(x => `<a class="red" href="#finupis?i=${finansije().indexOf(x)}">
      <div class="sred"><b>${h(x.kategorija)}</b><span>${h(x.datum)}${x.grlo ? " · " + h(x.grlo) : ""}${x.opis ? " · " + h(x.opis) : ""}</span></div>
      <b style="color:var(--${x.vrsta === PRIHOD ? "ok" : "bad"});white-space:nowrap">${x.vrsta === PRIHOD ? "+" : "−"}${fmtNovac(brojIznos(x.iznos) || 0)}</b></a>`).join("")}</div>`
      : `<span class="mali">${t("Nema upisa u ovom periodu.", "No entries in this period.")}</span>`}</div>`;
  ekran.querySelectorAll("[data-per]").forEach(b => b.onclick = () => { filtF.period = b.dataset.per; ekranFinansije(); });
}
function ekranFinUpis(_, upit) {
  const izm = upit && upit.get("i") != null ? finansije()[+upit.get("i")] : null;
  let vrsta = izm ? izm.vrsta : (upit && upit.get("v") === PRIHOD ? PRIHOD : TROSAK);
  postaviVrh(izm ? t("Izmena upisa", "Edit entry") : t("Novi upis", "New entry"), true); meni("vise");
  const pd = izm ? parsirajDatum(izm.datum) : danas();
  ekran.innerHTML = `<div class="kart"><div class="izbor" id="fv"><button data-v="trosak">− ${t("Trošak", "Cost")}</button><button data-v="prihod">+ ${t("Prihod", "Income")}</button></div><div style="height:12px"></div>
    <div class="dve"><label class="polje"><span>${t("Datum *", "Date *")}</span><input class="unos" id="fd" type="date" value="${uIso(pd || danas())}"></label>
      <label class="polje"><span>${t("Iznos *", "Amount *")} (${h(S.valuta || (EN() ? "EUR" : "RSD"))})</span><input class="unos" id="fi" inputmode="decimal" value="${h(izm ? izm.iznos : "")}"></label></div>
    <label class="polje"><span>${t("Kategorija *", "Category *")}</span><input class="unos" id="fk" list="dl-fk" value="${h(izm ? izm.kategorija : "")}"></label><datalist id="dl-fk"></datalist>
    <label class="polje"><span>${t("Grlo (nije obavezno)", "Animal (optional)")}</span><input class="unos" id="fg" list="dl-fg" autocomplete="off" value="${h(izm ? izm.grlo : "")}"></label>${datalistGrla("dl-fg", M.grla(false))}
    <label class="polje"><span>${t("Opis", "Description")}</span><input class="unos" id="fo" value="${h(izm ? izm.opis : "")}"></label>
    <div class="greska" id="gr"></div>
    <div class="dugmad">${izm ? `<button class="dug" id="fx">🗑 ${t("Obriši upis", "Delete entry")}</button>` : ""}<button class="dug glavno" id="sac">${t("Sačuvaj", "Save")}</button></div></div>`;
  const vr = () => { $("#fv").querySelectorAll("button").forEach(b => b.classList.toggle("akt", b.dataset.v === vrsta));
    $("#dl-fk").innerHTML = kategorijeFin(vrsta).map(k => `<option value="${h(k)}">`).join(""); };
  $("#fv").onclick = e => { const b = e.target.closest("button"); if (b) { vrsta = b.dataset.v; vr(); } }; vr();
  $("#sac").onclick = () => {
    const g = sacuvajFin({ vrsta, datum: $("#fd").value ? fmtD(parsirajDatum($("#fd").value)) : "", iznos: $("#fi").value, kategorija: $("#fk").value, grlo: $("#fg").value, opis: $("#fo").value }, izm);
    if (g) return ($("#gr").textContent = g);
    promena(t("Sačuvano.", "Saved.")); idi("finansije");
  };
  if (izm) $("#fx").onclick = () => { if (confirm(t("Obrisati ovaj upis?", "Delete this entry?"))) { obrisiFin(izm); promena(t("Upis je obrisan.", "Entry deleted.")); idi("finansije"); } };
}
// ---------------------------------------------------------------- Istorija cele farme
const filtI = { dog: "", q: "" };
function ekranIstorija() {
  postaviVrh(t("Istorija", "History"), true); meni("vise");
  const dog = [...new Set(S.istorija.map(z => z.dogadjaj).filter(Boolean))];
  const q = filtI.q.trim().toLowerCase();
  const lista = S.istorija.map(z => [z, parsirajDatum(z.datum)]).filter(([z]) => (!filtI.dog || z.dogadjaj === filtI.dog) &&
      (!q || [z.grlo, z.dogadjaj, z.vrednost, z.opis, z.partner].join(" ").toLowerCase().includes(q)))
    .sort((a, b) => (b[1] || 0) - (a[1] || 0) || String(b[0].uneto || "").localeCompare(String(a[0].uneto || "")));
  ekran.innerHTML = `<input class="pretraga" id="iq" type="search" placeholder="🔍 ${t("Traži grlo, događaj, opis…", "Search animal, event, description…")}" value="${h(filtI.q)}">
    <div class="filteri"><button data-d="" class="${!filtI.dog ? "akt" : ""}">${t("Sve", "All")}</button>${dog.map(d => `<button data-d="${h(d)}" class="${filtI.dog === d ? "akt" : ""}">${h(d)}</button>`).join("")}</div>
    <div class="mali" style="margin:0 4px 8px">${t(`${lista.length} upisa`, `${lista.length} entries`)}</div>
    <div class="kart">${lista.slice(0, 300).map(([z]) => `<div class="ist ${z.automatski ? "auto" : ""}"><div class="d">${h(z.datum)} · ${cip(z.grlo)}${z.partner ? " · " + cip(z.partner) : ""}${z.upisao ? ` · 📱 ${h(z.upisao)}` : ""}</div>
      <b>${h(z.dogadjaj)}</b>${z.vrednost ? ` – ${h(z.vrednost)}` : ""}${z.opis ? `<div class="mali">${h(z.opis)}</div>` : ""}</div>`).join("") || `<span class="mali">${t("Nema upisa.", "No entries.")}</span>`}
      ${lista.length > 300 ? `<p class="mali">${t("Prikazano je 300 najnovijih.", "Showing the 300 newest.")}</p>` : ""}</div>`;
  $("#iq").onchange = e => { filtI.q = e.target.value; ekranIstorija(); };
  ekran.querySelectorAll("[data-d]").forEach(b => b.onclick = () => { filtI.dog = b.dataset.d; ekranIstorija(); });
}
// ---------------------------------------------------------------- Statistika i pregled stada
function stubici(naslov, podaci, boja = "brand", fmt = v => v) {
  if (!podaci.length || !podaci.some(([, v]) => v)) return `<div class="kart"><h2>${naslov}</h2><span class="mali">${t("Još nema podataka.", "No data yet.")}</span></div>`;
  const mx = Math.max(1, ...podaci.map(([, v]) => v));
  return `<div class="kart"><h2>${naslov}</h2><div style="display:flex;align-items:flex-end;gap:6px;height:150px;margin-top:8px">${podaci.map(([k, v]) =>
    `<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0"><b style="font-size:12px">${v ? fmt(v) : ""}</b>
      <div style="width:70%;height:${Math.max(2, Math.round(v / mx * 110))}px;background:var(--${boja});border-radius:4px 4px 0 0"></div>
      <span class="mali" style="font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%">${h(String(k))}</span></div>`).join("")}</div></div>`;
}
function ekranStatistika() {
  postaviVrh(t("Statistika", "Statistics"), true); meni("vise");
  const akt = M.grla(true);
  if (!akt.length) { ekran.innerHTML = `<div class="kart mali">${t("U zapatu još nema grla.", "There are no animals in the herd yet.")}</div>`; return; }
  const fs = akt.map(a => M.inbr(a.id)), zen = akt.filter(a => a.pol === "z").length, muz = akt.filter(a => a.pol === "m").length, iznad = fs.filter(f => f > S.prag).length;
  const rase = {}; akt.forEach(a => { const k = a.rasa || t("bez rase", "no breed"); rase[k] = (rase[k] || 0) + 1; });
  const god = {}; M.grla(false).forEach(a => { if (a.datum) god[a.datum.getFullYear()] = (god[a.datum.getFullYear()] || 0) + 1; });
  const kl = [0, 0, 0, 0, 0]; fs.forEach(f => kl[f === 0 ? 0 : f < 0.03125 ? 1 : f < 0.0625 ? 2 : f < 0.125 ? 3 : 4]++);
  const d = danas(), meseci = [...Array(12)].map((_, i) => new Date(d.getFullYear(), d.getMonth() - 11 + i, 1)), por = meseci.map(() => 0);
  S.istorija.forEach(z => { if (z.dogadjaj !== K().POROD) return; const pd = parsirajDatum(z.datum); if (!pd) return;
    const i = meseci.findIndex(m => m.getFullYear() === pd.getFullYear() && m.getMonth() === pd.getMonth()); if (i >= 0) por[i]++; });
  const ocevi = {}; akt.forEach(a => { const o = (M.P[a.id] || [])[0]; if (o) ocevi[o] = (ocevi[o] || 0) + 1; });
  const top = Object.entries(ocevi).sort((a, b) => b[1] - a[1]).slice(0, 5), dec = n => EN() ? n : String(n).replace(".", ",");
  ekran.innerHTML = `<div class="kart"><dl class="polja"><dt>${t("Grla u zapatu", "Animals in herd")}</dt><dd>${akt.length}</dd>
      <dt>${t("Ženska / muška", "Female / male")}</dt><dd>${zen} / ${muz}</dd>
      <dt>${t("Prosečan inbriding", "Average inbreeding")}</dt><dd>${pct(fs.reduce((s, f) => s + f, 0) / fs.length)}</dd>
      <dt>${t("Iznad granice rizika", "Above the risk limit")}</dt><dd style="color:var(--${iznad ? "bad" : "ok"})">${iznad}</dd></dl></div>
    ${stubici(t("Grla po rasi", "Animals by breed"), Object.entries(rase).sort((a, b) => b[1] - a[1]).slice(0, 8))}
    ${stubici(t("Rođena grla po godinama", "Animals born per year"), Object.entries(god).sort().slice(-8), "brand")}
    ${stubici(t("Inbriding grla u zapatu", "Inbreeding of animals in the herd"), [["0%", kl[0]], [dec("<3.1%"), kl[1]], [dec("<6.25%"), kl[2]], [dec("<12.5%"), kl[3]], [dec("≥12.5%"), kl[4]]], "warn")}
    ${stubici(t("Porođaji u poslednjih 12 meseci", "Births in the last 12 months"), meseci.map((m, i) => [String(m.getMonth() + 1), por[i]]), "ok")}
    <div class="kart"><h2>${t("Najčešći očevi", "Most common sires")}</h2>${top.length ? top.map(([o, n]) => `<div style="margin:6px 0">${cip(o)} <span class="mali">${t(`${n} potomaka u zapatu`, `${n} offspring in the herd`)}</span></div>`).join("")
      + `<p class="mali">${t("Kad jedan mužjak ima previše potomaka, sledeća generacija postaje srodna.", "When one male has too many offspring, the next generation becomes related.")}</p>` : `<span class="mali">${t("Još nema upisanih očeva.", "No sires recorded yet.")}</span>`}</div>
    ${M.warn && M.warn.length ? `<div class="kart"><h2>⚠ ${t("Greške u podacima", "Data problems")}</h2>${M.warn.slice(0, 30).map(w => `<div class="mali" style="margin:4px 0">${h(w)}</div>`).join("")}</div>` : ""}`;
}

// ---------------------------------------------------------------- Nova rasa (kao na računaru)
function ekranNovaRasa(_, upit) {
  postaviVrh(t("Nova rasa", "New breed"), true); meni("vise");
  const sva = M.grla(true);
  if (!sva.length) { ekran.innerHTML = `<div class="kart mali">${t("U zapatu još nema grla.", "There are no animals in the herd yet.")}</div>`; return; }
  const prog = programRase(), vrste = [...new Set(sva.map(a => a.vrsta))];
  const izabrana = (upit && upit.get("v")) || vrste.find(v => vrstaKanon(v) === vrstaKanon(prog.vrsta)) || vrste[0];
  const grla = sva.filter(a => vrstaKanon(a.vrsta) === vrstaKanon(izabrana)), isti = vrstaKanon(prog.vrsta) === vrstaKanon(izabrana);
  const cilj = {}; if (isti) for (const [k, v] of Object.entries(prog.cilj || {})) cilj[k] = v / 100;
  const rase = [...new Set(grla.flatMap(a => Object.keys(sastav(a.id))).filter(k => k !== NEPOZNATO).concat(Object.keys(cilj)))].sort();
  const stari = isti ? Object.entries(prog.cilj || {}).sort((a, b) => b[1] - a[1]) : [];
  const pod = grla.map(a => { const s = sastav(a.id), d = odstupanje(s, cilj); return [d == null ? 9 : d, s[NEPOZNATO] || 0, a, s, d]; }).sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2].id.localeCompare(b[2].id));
  const uCilju = pod.filter(x => x[4] != null && x[4] <= BLIZU + 1e-9).length;
  const parovi = Object.keys(cilj).length ? paroviZaCilj(grla, cilj) : [];
  const osnivaci = grla.filter(a => !(M.P[a.id] || []).some(Boolean));
  ekran.innerHTML = `<div class="kart"><h2>${t("Cilj programa", "Breeding goal")}</h2>
    <p class="mali" style="margin-top:0">${t("Upiši koje rase i u kom odnosu treba da ima nova rasa. Zbir mora biti 100 %.", "Enter which breeds the new breed should have and in what share. The total must be 100 %.")}</p>
    <div class="dve"><label class="polje"><span>${t("Vrsta", "Species")}</span><select class="unos" id="nv">${vrste.map(v => `<option ${v === izabrana ? "selected" : ""}>${h(v)}</option>`).join("")}</select></label>
      <label class="polje"><span>${t("Naziv nove rase", "Name of the new breed")}</span><input class="unos" id="ni" value="${h(isti ? prog.ime || "" : "")}"></label></div>
    <datalist id="dl-nr">${rase.map(r => `<option value="${h(r)}">`).join("")}</datalist>
    ${[0, 1, 2, 3].map(i => `<div class="dve"><label class="polje"><span>${t("Rasa", "Breed")}</span><input class="unos" id="nr${i}" list="dl-nr" value="${h(stari[i] ? stari[i][0] : "")}"></label>
      <label class="polje"><span>${t("Udeo %", "Share %")}</span><input class="unos" id="np${i}" inputmode="decimal" value="${h(stari[i] ? String(stari[i][1]).replace(".", EN() ? "." : ",") : "")}"></label></div>`).join("")}
    <div class="greska" id="gr"></div><button class="dug glavno puno" id="sac">${t("Sačuvaj cilj", "Save goal")}</button></div>
    <div class="kart"><h2>${t("Grla po udelu krvi", "Animals by breed share")}</h2>
      ${Object.keys(cilj).length ? `<p class="mali" style="margin-top:0;color:var(--${uCilju ? "ok" : "ink2"})">${t(`Cilju odgovara ${uCilju} od ${pod.length} grla (razlika do ${pct(BLIZU)}).`, `${uCilju} of ${pod.length} animals match the goal (difference up to ${pct(BLIZU)}).`)}</p>` : ""}
      <div class="lista">${pod.slice(0, 200).map(([, , a, s, d]) => `<a class="red" href="#karton/${encodeURIComponent(a.id)}"><div class="sred"><b>${h(a.id)} ${a.pol === "m" ? "♂" : "♀"} <span class="mali">${h(generacijaUkrstanja(a.id)[0])}</span></b>
        <span style="white-space:normal">${h(tekstUdela(s))}</span></div>${d != null ? `<b style="color:var(--${d <= BLIZU + 1e-9 ? "ok" : "ink2"});white-space:nowrap">${pct(d)}</b>` : ""}</a>`).join("")}</div></div>
    ${Object.keys(cilj).length ? `<div class="kart"><h2>${t("Parenja koja vode ka cilju", "Matings that lead to the goal")}</h2>
      <p class="mali" style="margin-top:0">${t("Na vrhu su parovi čiji je potomak najbliži cilju, uz manji inbriding. Rizični parovi su na dnu.", "At the top are pairs whose offspring is closest to the goal, with lower inbreeding. Risky pairs are at the bottom.")}</p>
      ${parovi.length ? `<div class="lista">${parovi.map(([d, f, z, mu, s]) => { const [tx, kl] = procena(f, S.prag); return `<a class="red" href="#srodstvo?a=${encodeURIComponent(z)}&b=${encodeURIComponent(mu)}"><div class="sred"><b>${h(z)} ♀ × ${h(mu)} ♂</b>
        <span style="white-space:normal">${h(tekstUdela(s))}</span><span>${t("razlika", "difference")} ${pct(d)} · F ${pct(f)} · <span class="znak ${kl}">${h(tx)}</span></span></div></a>`; }).join("")}</div>`
        : `<span class="mali">${t("Nema dovoljno mužjaka i ženki sa poznatim udelom krvi.", "Not enough males and females with a known breed share.")}</span>`}</div>` : ""}
    <div class="kart"><h2>${t("Udeo krvi osnivača", "Breed share of founders")}</h2>
      <p class="mali" style="margin-top:0">${t("Grlima bez upisanih roditelja (npr. kupljenim melezima) upiši udeo krvi: otvori grlo → ✎ Izmeni podatke → Udeo krvi.", "For animals without recorded parents (e.g. purchased crossbreds) enter the breed share: open the animal → ✎ Edit details → Breed share.")}</p>
      ${osnivaci.length ? `<div class="cipovi">${osnivaci.map(a => `<a class="cip" href="#novo?izmena=${encodeURIComponent(a.id)}">${h(a.id)}</a>`).join("")}</div>` : `<span class="mali">${t("Sva grla ove vrste imaju upisane roditelje.", "All animals of this species have recorded parents.")}</span>`}</div>`;
  $("#nv").onchange = e => idi(`novarasa?v=${encodeURIComponent(e.target.value)}`);
  $("#sac").onclick = () => {
    const g = sacuvajCiljRase($("#nv").value, $("#ni").value, [0, 1, 2, 3].map(i => [$("#nr" + i).value, $("#np" + i).value]));
    if (g) return ($("#gr").textContent = g);
    promena(t("Cilj je sačuvan.", "Goal saved.")); ekranNovaRasa(_, upit);
  };
}
// ---------------------------------------------------------------- rodoslovni list za štampu / PDF (kao na računaru)
function ekranRodoslov(id, upit) {
  const x = M.nadji(id);
  if (!x) return idi("grla");
  const kolena = Math.min(6, Math.max(2, +(upit && upit.get("k")) || 4));
  postaviVrh(t("Rodoslovni list", "Pedigree"), true); meni("grla");
  const a = M.A[x], f = M.inbr(x), [o, mj] = M.P[x] || [null, null];
  let niz = [[x]];
  for (let g = 0; g < kolena; g++) niz.push(niz[g].flatMap(y => (y ? (M.P[y] || [null, null]) : [null, null])));
  let gens = 2; for (let g = 1; g <= kolena; g++) if (niz[g].some(Boolean)) gens = Math.max(gens, g);
  const redovi = 2 ** gens, imena = [t("Roditelji", "Parents"), t("Babe i dede", "Grandparents"), t("Prababe i pradede", "Great-grandparents")];
  let tab = `<table class="rod"><tr>${[...Array(gens)].map((_, g) => `<th>${g < 3 ? imena[g] : t(`${g + 1}. koleno`, `Generation ${g + 1}`)}</th>`).join("")}</tr>`;
  for (let r = 0; r < redovi; r++) {
    tab += "<tr>";
    for (let g = 1; g <= gens; g++) {
      const span = redovi / 2 ** g;
      if (r % span) continue;
      const y = niz[g][r / span], b = y && M.A[y];
      if (b && !b.osnivac) { const fy = M.inbr(y), det = [b.markica, b.rasa, b.datum ? b.datum.getFullYear() : ""].filter(Boolean).join(" · ");
        tab += `<td rowspan="${span}" class="${b.pol === "m" ? "m" : "z"}"><b>${h(y)}</b>${det && gens < 6 ? `<br><small>${h(det)}</small>` : ""}${fy > 0 ? `<br><small>F ${pct(fy)}</small>` : ""}</td>`; }
      else if (y) tab += `<td rowspan="${span}" class="${g && niz[g].indexOf(y) % 2 ? "z" : "m"}"><b>${h(y)}</b></td>`;
      else tab += `<td rowspan="${span}" class="n">${t("nepoznat", "unknown")}</td>`;
    }
    tab += "</tr>";
  }
  tab += "</table>";
  const deca = Object.entries(M.P).filter(([y, p]) => p.includes(x) && M.A[y] && !M.A[y].osnivac).map(([y]) => y);
  const red = (k, v) => (v ? `<tr><td>${h(k)}</td><td><b>${h(v)}</b></td></tr>` : "");
  const dok = `<div class="rodlist"><h1>${t("Rodoslovni list", "Pedigree certificate")}</h1>
    <table class="podaci">${red(t("Oznaka", "ID"), x)}${red(t("Ušna markica", "Ear tag"), a.markica)}${red(t("Vrsta", "Species"), a.vrsta)}${red(t("Rasa", "Breed"), a.rasa)}
      ${red(t("Pol", "Sex"), M.polNaziv(x))}${red(t("Datum rođenja", "Date of birth"), a.datum ? fmtD(a.datum) : "")}${red(t("Otac", "Sire"), o)}${red(t("Majka", "Dam"), mj)}
      ${red(t("Stado", "Herd"), a.stado)}${red(t("Udeo krvi", "Breed share"), (S.grla.find(g => g.id === x) || {}).udeo_krvi ? tekstUdela(sastav(x)) : "")}${red(t("Inbriding (F)", "Inbreeding (F)"), pct(f))}</table>
    <h2>${t("Rodoslov", "Pedigree")}</h2>${tab}
    ${deca.length ? `<h2>${t("Potomci", "Offspring")} (${deca.length})</h2><p>${deca.map(h).join(", ")}</p>` : ""}
    <p class="potpis">${t("Datum", "Date")}: ${fmtD(danas())} &nbsp; · &nbsp; HerdDoc</p></div>`;
  ekran.innerHTML = `<div class="kart ne-stampa"><div class="filteri">${[3, 4, 5, 6].map(k => `<button data-k="${k}" class="${k === kolena ? "akt" : ""}">${t(`${k} kolena`, `${k} generations`)}</button>`).join("")}</div>
    <button class="dug glavno puno" id="stampa">🖨 ${t("Štampaj / Sačuvaj kao PDF", "Print / Save as PDF")}</button>
    <p class="mali">${t("U prozoru za štampu izaberi štampač ili „Sačuvaj kao PDF“.", "In the print window choose a printer or “Save as PDF”.")}</p></div>${dok}`;
  ekran.querySelectorAll("[data-k]").forEach(b => b.onclick = () => idi(`rodoslov/${encodeURIComponent(x)}?k=${b.dataset.k}`));
  $("#stampa").onclick = () => { document.body.classList.add("stampam"); setTimeout(() => { window.print(); document.body.classList.remove("stampam"); }, 50); };
}

const filtR = { vrsta: "", pol: "" };
function ekranRang() {
  postaviVrh(t("⭐ Rang lista", "⭐ Ranking"), true); meni("grla");
  const sva = M.grla(true), vrste = [...new Set(sva.map(a => a.vrsta).filter(Boolean))];
  if (!filtR.vrsta || !vrste.includes(filtR.vrsta)) filtR.vrsta = vrste[0] || "";
  const kes = vrednostiVrste(filtR.vrsta);
  const lista = sva.filter(a => a.vrsta === filtR.vrsta && (!filtR.pol || a.pol === filtR.pol)).map(a => [a, oceneGrla(a.id, kes)])
    .filter(([, o]) => o.ukupno != null).sort((a, b) => b[1].ukupno - a[1].ukupno);
  const dec = v => v.toFixed(1).replace(".", EN() ? "." : ",");
  ekran.innerHTML = `<div class="dve-izbor"><select id="rV" class="stado-izbor">${vrste.map(v => `<option${v === filtR.vrsta ? " selected" : ""}>${h(v)}</option>`).join("")}</select>
    <select id="rP" class="stado-izbor">${[["", t("Svi", "All")], ["z", t("Ženska", "Females")], ["m", t("Muška", "Males")]].map(([k, n]) => `<option value="${k}"${k === filtR.pol ? " selected" : ""}>${n}</option>`).join("")}</select></div>
    ${lista.length ? `<div class="lista">${lista.map(([a, o], i) => `<a class="red" href="#karton/${encodeURIComponent(a.id)}"><span style="font-size:18px;font-weight:800;min-width:28px">${i + 1}.</span>
      <div class="sred"><b>${h(a.id)}</b><span>${h([a.rasa, a.pol === "m" ? "♂" : "♀"].filter(Boolean).join(" · "))} · ${Object.entries(o.rucne).map(([k, v]) => `${(rucneOsobine().find(r => r[0] === k) || [k, k])[1].split(" (")[0]} ${v}`).join(", ") || t("samo automatske", "automatic only")}</span></div>
      <span style="color:var(--warn);font-weight:800;white-space:nowrap">★ ${dec(o.ukupno)}</span></a>`).join("")}</div>`
      : `<div class="kart mali">${t("Još nema ocenjenih grla ove vrste. Otvori grlo → ⭐ Oceni.", "No scored animals of this species yet. Open an animal → ⭐ Score.")}</div>`}`;
  $("#rV").onchange = e => { filtR.vrsta = e.target.value; ekranRang(); };
  $("#rP").onchange = e => { filtR.pol = e.target.value; ekranRang(); };
}

function kartPrirasta(id) {
  const m = merenjaTezine(id);
  if (!m.length) return "";
  const [d, kg] = m[m.length - 1], fk = x => fmtBroj(x, 1), fg = g => `${g > 0 ? "+" : ""}${g} ${t("g/dan", "g/day")}`;
  const p = m.length > 1 ? prirastG(m[m.length - 2], m[m.length - 1]) : null, dana = m.length > 1 ? Math.round((d - m[m.length - 2][0]) / 86400000) : 0;
  const pr = m.length > 2 ? prirastG(m[0], m[m.length - 1]) : null;
  const red = m.slice(-6).map((x, i, arr) => { const pp = i ? prirastG(arr[i - 1], x) : (m.length > 6 ? prirastG(m[m.length - 7], x) : null);
    return `<tr><td>${fmtD(x[0])}</td><td style="text-align:right"><b>${fk(x[1])} kg</b></td><td style="color:var(--${pp > 0 ? "ok" : "bad"})">${pp === null ? "" : fg(pp)}</td></tr>`; }).join("");
  return `<div class="kart"><h2>${t("Težina i prirast", "Weight and gain")}</h2><dl class="polja">
    <dt>${t("Poslednja težina", "Last weight")}</dt><dd>${fk(kg)} kg (${fmtD(d)})</dd>
    ${p !== null ? `<dt>${t("Prirast od prethodnog merenja", "Gain since previous weighing")}</dt><dd style="color:var(--${p > 0 ? "ok" : "bad"})"><b>${fg(p)}</b> <span class="mali">${t(`za ${dana} dana`, `over ${dana} days`)}</span></dd>` : ""}
    ${pr !== null ? `<dt>${t("Prosečan dnevni prirast", "Average daily gain")}</dt><dd>${fg(pr)}</dd>` : ""}</dl>
    ${m.length > 1 ? `<table class="mali" style="width:100%;margin-top:8px">${red}</table>` : ""}</div>`;
}
function kartMleka(id, a) {
  const mz = muznjeZa(id);
  if (!muznaVrsta(a) || (!mlecnoGrlo(a) && !Object.keys(mz).length)) return "";
  const s = statMleka(id);
  return `<div class="kart"><h2>${t("Mlečnost", "Milk")}</h2><dl class="polja">
    <dt>${t("Laktacija", "Lactation")}</dt><dd>${s.br ? `${s.br}.${s.dan ? ` · ${t("dan", "day")} ${s.dan}` : ""}` : t("telenje nije upisano", "no calving recorded")}</dd>
    ${s.poslednje ? `<dt>${t("Poslednja mužnja", "Last milking")}</dt><dd>${fmtBroj(s.poslednje[1])} L (${fmtKratko(s.poslednje[0])})</dd>` : ""}
    ${s.prosek7 ? `<dt>${t("Prosek 7 dana", "7-day average")}</dt><dd>${fmtBroj(s.prosek7)} L</dd>` : ""}
    ${s.n ? `<dt>${t("Izmereno u laktaciji", "Recorded this lactation")}</dt><dd>${fmtBroj(s.ukupno, 0)} L</dd>` : ""}</dl>
    <a class="dug puno" href="#muznja" style="margin-top:10px">🥛 ${t("Upiši mužnju", "Record milking")}</a></div>`;
}

function ekranMuznja(_, upit) {
  postaviVrh(t("Mužnja", "Milking"), true); meni("vise");
  const d = (upit && parsirajDatum(upit.get("d"))) || danas(), sve = upit && upit.get("sve") === "1";
  let saMast = false;                    // mast i proteini se ne upisuju svaki dan – polja samo kad se uključe
  try { saMast = localStorage.getItem("herddoc-mleko-mast") === "1"; } catch (e) { /* */ }
  const muzne = M.grla(true).filter(muznaVrsta);
  const grla = (sve ? muzne : muzne.filter(a => (mlecnoGrlo(a) && telenja(a.id).length) || Object.keys(muznjeZa(a.id)).length))
    .sort((a, b) => sortKey(a.id, b.id));
  const iso = uIso(d), juce = uIso(dodajDane(d, -1));
  const adresa = (nd, ns) => `#muznja?d=${uIso(nd)}${ns ? "&sve=1" : ""}`;
  let ukupno = 0, n = 0;
  const redovi = grla.map(a => {
    const mz = muznjeZa(a.id), z = mz[iso] || {}, zj = mz[juce], s = statMleka(a.id, d);
    if (broj(z.vrednost) !== null) { ukupno += broj(z.vrednost); n++; }
    return `<div class="kart" style="padding:12px 14px" data-g="${h(a.id)}">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">${cip(a.id)}
        <span class="mali">${s.br ? `${s.br}. ${t("lakt.", "lact.")}${s.dan ? ` · ${t("dan", "day")} ${s.dan}` : ""}` : ""}${zj && zj.vrednost ? ` · ${t("juče", "yesterday")} ${fmtBroj(zj.vrednost)} L` : ""}</span></div>
      <div class="mlekopolja" style="display:grid;grid-template-columns:${saMast ? "1.3fr 1fr 1fr" : "1fr"};gap:8px;margin-top:8px">
        <input class="unos" inputmode="decimal" placeholder="${t("Litara", "Litres")}" data-k="l" value="${z.vrednost ? h(fmtBroj(z.vrednost, 2)) : ""}">
        <input class="unos ${saMast ? "" : "skriveno"}" inputmode="decimal" placeholder="${t("Mast %", "Fat %")}" data-k="m" value="${z.mast ? h(fmtBroj(z.mast, 2)) : ""}">
        <input class="unos ${saMast ? "" : "skriveno"}" inputmode="decimal" placeholder="${t("Prot. %", "Prot. %")}" data-k="p" value="${z.proteini ? h(fmtBroj(z.proteini, 2)) : ""}"></div></div>`;
  }).join("");
  ekran.innerHTML = `<div class="kart"><div style="display:flex;gap:8px;align-items:center">
      <a class="dug" href="${adresa(dodajDane(d, -1), sve)}" style="flex:0 0 52px">◀</a>
      <input class="unos" type="date" id="dat" value="${iso}" style="flex:1">
      <a class="dug" href="${adresa(dodajDane(d, 1), sve)}" style="flex:0 0 52px">▶</a></div>
    <p class="mali" style="margin:10px 2px 0">${t(`Pomuženo ${n} od ${grla.length} grla · ukupno ${fmtBroj(ukupno)} L`, `Milked ${n} of ${grla.length} animals · total ${fmtBroj(ukupno)} L`)}</p>
    <label class="mali" style="display:flex;gap:8px;align-items:center;margin-top:8px"><input type="checkbox" id="sve" ${sve ? "checked" : ""}> ${t("Prikaži sve ženke", "Show all females")}</label>
    <label class="mali" style="display:flex;gap:8px;align-items:center;margin-top:6px"><input type="checkbox" id="mp" ${saMast ? "checked" : ""}> ${t("Upisujem i mast i proteine", "Also enter fat and protein")}</label></div>
    ${grla.length ? redovi : `<div class="kart mali">${t("Nema muznih grla. Na listi su ženke goveda, ovaca i koza mlečne ili kombinovane namene koje su se telile. Uključi „Prikaži sve ženke“ ili upiši namenu na računaru.", "No animals to milk. The list shows dairy or dual-purpose female cattle, sheep and goats that have given birth. Tick “Show all females” or set the purpose on the computer.")}</div>`}
    <div class="greska" id="gr"></div>
    ${grla.length ? `<button class="dug glavno puno" id="sac">${t("Sačuvaj mužnju", "Save milking")}</button>
    <p class="mali" style="margin:8px 4px">${t("Prazno polje = nije muženo tog dana.", "Empty field = not milked that day.")}</p>` : ""}`;
  $("#dat").onchange = () => { const nd = parsirajDatum($("#dat").value); if (nd) location.hash = adresa(nd, sve); };
  $("#sve").onchange = () => { location.hash = adresa(d, $("#sve").checked); };
  $("#mp").onchange = () => { try { localStorage.setItem("herddoc-mleko-mast", $("#mp").checked ? "1" : ""); } catch (e) { /* */ } ekranMuznja(_, upit); };
  if (!grla.length) return;
  $("#sac").onclick = () => {
    const greske = [], plan = [];
    ekran.querySelectorAll("[data-g]").forEach(k => {
      const x = k.dataset.g, v = q => k.querySelector(`[data-k="${q}"]`).value.trim();
      const [l, m, p] = [v("l"), v("m"), v("p")];
      if (!l) return plan.push([x, null]);            // bez litara = nije muženo tog dana
      const lit = broj(l), mas = broj(m), pro = broj(p);
      if (lit === null || !(lit > 0 && lit < 150)) return greske.push(t(`${x}: litri nisu ispravni`, `${x}: litres are not valid`));
      if (m && (mas === null || !(mas > 0 && mas < 20))) return greske.push(t(`${x}: mast nije ispravna`, `${x}: fat is not valid`));
      if (p && (pro === null || !(pro > 0 && pro < 15))) return greske.push(t(`${x}: proteini nisu ispravni`, `${x}: protein is not valid`));
      plan.push([x, lit, mas, pro]);
    });
    if (greske.length) return ($("#gr").textContent = greske.slice(0, 4).join(" · "));
    let novo = 0, uk = 0;
    for (const [x, lit, mas, pro] of plan) {
      const r = upisiMuznju(x, d, lit, mas, pro);
      if (r === "novo" || r === "izmena") novo++;
      if (lit) uk += lit;
    }
    const muzeno = plan.filter(([, lit]) => lit).length;
    if (novo || plan.some(([, lit]) => lit === null)) zabelezi(t(`Mužnja ${fmtD(d)}: ${muzeno} grla, ${fmtBroj(uk)} L`, `Milking ${fmtD(d)}: ${muzeno} animals, ${fmtBroj(uk)} L`));
    promena(t(`Mužnja sačuvana: ${muzeno} grla, ukupno ${fmtBroj(uk)} L`, `Milking saved: ${muzeno} animals, total ${fmtBroj(uk)} L`));
    ekranMuznja(_, upit);
  };
}

// ---------------------------------------------------------------- Danas (obaveštenja)
let danasLim = 50;                                  // veliko stado: obaveštenja se prikazuju u delovima
function ekranDanas() {
  postaviVrh(t("Danas", "Today"), false); meni("danas");
  const ob = obavestenja(), so = stanjeObavestenja();
  ekran.innerHTML = (so[0] === "iskljuceno" ? `<button class="dug puno" id="obUk2" style="margin-bottom:10px">🔔 ${t("Uključi obaveštenja – da telefon javi i kad je aplikacija zatvorena", "Turn on notifications – so the phone alerts you even when the app is closed")}</button>` : "") + (ob.length ? ob.slice(0, danasLim).map(kartObavestenja).join("") : `<div class="prazno">✓ ${t("Nema obaveštenja. Sve je u redu.", "No notifications. All good.")}</div>`) +
    (ob.length > danasLim ? `<button class="dug puno" id="josOb">${t("Prikaži još", "Show more")} (${ob.length - danasLim})</button><div style="height:10px"></div>` : "") +
    `<a class="dug puno" href="#podsetnik">＋ ${t("Novi podsetnik", "New reminder")}</a>`;
  vezAkcije(ekran, ob);
  const uk2 = document.getElementById("obUk2");
  if (uk2) uk2.onclick = ukljuciObavestenja;
  const jos = document.getElementById("josOb");
  if (jos) jos.onclick = () => { const y = window.scrollY; danasLim += 100; ekranDanas(); window.scrollTo(0, y); };
}

// ---------------------------------------------------------------- Upis događaja
const PON_TEL = () => [[t("ne ponavlja se", "does not repeat"), 0], [t("svake nedelje", "every week"), 7], [t("svakog meseca", "every month"), 30],
  [t("na 3 meseca", "every 3 months"), 90], [t("na 6 meseci", "every 6 months"), 182], [t("svake godine", "every year"), 365]];
const SLED_TEL = () => [[t("ne", "no"), 0], [t("za 1 mesec", "in 1 month"), 30], [t("za 3 meseca", "in 3 months"), 90],
  [t("za 6 meseci", "in 6 months"), 182], [t("za 1 godinu", "in 1 year"), 365]];
function ekranDogadjaj(_, upit) {
  postaviVrh(t("Novi događaj", "New event"), true); meni("dogadjaj");
  const k = K(), sva = M.grla(true);
  const st = { grlo: upit.get("grlo") || "", dogadjaj: upit.get("tip") || "", partner: upit.get("partner") || "" };
  const nazivVr = { [k.DOGADJAJI[5]]: t("Težina (kg)", "Weight (kg)"), [k.VAKCINA]: t("Vakcina / preparat", "Vaccine / product"), [k.LECENJE]: t("Lek / dijagnoza", "Drug / diagnosis"),
    [k.PRODAJA]: t("Kupac / cena", "Buyer / price"), [k.DOGADJAJI[6]]: t("Novo stado / lokacija", "New herd / location"), [k.PARENJE]: t("Način (prirodno / VO)", "Method (natural / AI)") };
  ekran.innerHTML = `<div class="kart">
    <label class="polje"><span>${t("Grlo *", "Animal *")}</span>${saKamerom(`<input class="unos" id="grlo" list="dl-grla" value="${h(st.grlo)}" autocomplete="off" placeholder="${t("oznaka ili markica", "tag or ear tag")}">`, "grlo")}</label>
    ${datalistGrla("dl-grla", sva)}
    <label class="polje"><span>${t("Datum *", "Date *")}</span><input class="unos" id="datum" type="date" value="${uIso(danas())}"></label>
    <div class="polje"><span class="mali" style="font-weight:700">${t("Događaj *", "Event *")}</span><div class="izbor" id="tipovi" style="margin-top:6px">
      ${k.DOGADJAJI.filter(d => d !== k.POROD).map(d => `<button data-d="${h(d)}" class="${d === st.dogadjaj ? "akt" : ""}">${h(d)}</button>`).join("")}</div></div>
    <div style="height:12px"></div>
    <div id="dPar"><label class="polje"><span>${t("Partner (bik / ovan…)", "Partner (bull / ram…)")}</span><input class="unos" id="partner" list="dl-par" value="${h(st.partner)}" autocomplete="off"></label><datalist id="dl-par"></datalist>
      <div id="inbr"></div></div>
    <label class="polje" id="dVr"><span id="lVr">${t("Vrednost", "Value")}</span><input class="unos" id="vrednost"></label>
    <div class="dve skriveno" id="dKar"><label class="polje"><span style="color:var(--bad)">${t("Karenca meso (dana)", "Meat withdrawal (days)")}</span><input class="unos" id="km" inputmode="numeric"></label>
      <label class="polje"><span style="color:var(--bad)">${t("mleko (dana)", "milk (days)")}</span><input class="unos" id="kml" inputmode="numeric"></label></div>
    <label class="polje"><span>${t("Opis / napomena", "Description / note")}</span><textarea class="unos" id="opis"></textarea></label>
    <label class="provera" id="dTreba"><input type="checkbox" id="treba"> ⏰ ${t("Treba uraditi – samo podsetnik (još nije urađeno)", "To do – reminder only (not done yet)")}</label>
    <label class="polje skriveno" id="dPon"><span>${t("Ponavljanje", "Repeat")}</span><select class="unos" id="pon">${PON_TEL().map(([n, v]) => `<option value="${v}">${h(n)}</option>`).join("")}</select></label>
    <label class="polje skriveno" id="dVrT"><span>${t("Vreme (nije obavezno)", "Time (optional)")}</span><input class="unos" id="vrT" type="time"></label>
    <label class="polje skriveno" id="dSled"><span>⏰ ${t("Podseti me za sledeću", "Remind me of the next one")}</span><select class="unos" id="sled">${SLED_TEL().map(([n, v]) => `<option value="${v}">${h(n)}</option>`).join("")}</select></label>
    <label class="provera skriveno" id="dVan"><input type="checkbox" id="van" checked> ${t("Označi grlo kao van zapata", "Mark the animal as out of herd")}</label>
    <div class="greska" id="gr"></div>
    <button class="dug glavno puno" id="sac">${t("Sačuvaj", "Save")}</button></div>
    ${!st.dogadjaj ? `<div class="dugmad"><a class="dug" href="#novo">＋ ${t("Novo grlo", "New animal")}</a></div>` : ""}`;
  const prilagodi = () => {
    const d = st.dogadjaj, g = M.nadji($("#grlo").value), leci = [k.LECENJE, k.VAKCINA].includes(d), treba = $("#treba").checked, nap = d === k.NAPOMENA;
    $("#dPar").classList.toggle("skriveno", leci || nap);
    $("#dVr").classList.toggle("skriveno", nap);               // napomena: samo datum i tekst
    $("#dKar").classList.toggle("skriveno", !leci || treba);
    $("#dPon").classList.toggle("skriveno", !treba);
    $("#dVrT").classList.toggle("skriveno", !treba);
    $("#dSled").classList.toggle("skriveno", !leci || treba);
    $("#dVan").classList.toggle("skriveno", ![k.PRODAJA, k.UGINUCE].includes(d));
    $("#lVr").textContent = nazivVr[d] || t("Vrednost", "Value");
    const dl = $("#dl-par");
    if (g && !leci && dl.dataset.za !== g) {        // predlozi partnera: računa se jednom po grlu, najviše 300 (ostale možeš da upišeš)
      const a = M.A[g];
      dl.dataset.za = g;
      dl.innerHTML = M.grla(true).filter(b => b.vrsta === a.vrsta && b.pol && b.pol !== a.pol).slice(0, 300)
        .map(b => `<option value="${h(b.id)}">F ${pct(M.kinship(g, b.id))}</option>`).join("");
    }
    // ženka i parenje/porođaj: mužjak iz njenog stada se upiše sam (jednom; može da se promeni)
    if (g && M.A[g].pol === "z" && [k.PARENJE, k.POROD].includes(d) && !$("#partner").value.trim() && st.autoPar !== g + "|" + d) {
      st.autoPar = g + "|" + d;
      const kand = M.muzjaciUStadu(g);
      if (kand.length === 1) $("#partner").value = kand[0];
    }
    const p = M.nadji($("#partner").value);
    if (d === k.PARENJE && g && p && g !== p) {
      const f = M.kinship(g, p), [tx, kl] = procena(f, S.prag);
      $("#inbr").innerHTML = `<div class="info ${kl}">${t(`Očekivani inbriding potomka: <b>${pct(f)}</b> (${h(tx)}), zajednički geni ${pct(M.r(g, p))}.`, `Expected inbreeding of offspring: <b>${pct(f)}</b> (${h(tx)}), shared genes ${pct(M.r(g, p))}.`)}</div>`;
    } else $("#inbr").innerHTML = "";
  };
  $("#tipovi").onclick = e => { const b = e.target.closest("button"); if (!b) return; st.dogadjaj = b.dataset.d; $("#tipovi").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x === b)); prilagodi(); };
  ["grlo", "partner"].forEach(i => $("#" + i).addEventListener("input", prilagodi));
  $("#treba").onchange = prilagodi;
  prilagodi();
  $("#sac").onclick = () => {
    const g = M.nadji($("#grlo").value), gr = $("#gr");
    if (!g || M.A[g].osnivac) return (gr.textContent = t("Izaberi grlo sa spiska (oznaka ili markica).", "Choose an animal from the list (tag or ear tag)."));
    const d = parsirajDatum($("#datum").value);
    if (!d) return (gr.textContent = t("Datum nije ispravan.", "The date is not valid."));
    if (!st.dogadjaj) return (gr.textContent = t("Izaberi događaj.", "Choose an event."));
    const broj = v => { const x = String(v || "").replace(/\D/g, ""); return x && +x > 0 ? x : ""; };
    if ($("#treba").checked) {                       // još nije urađeno: samo podsetnik, ništa u istoriju
      S.podsetnici.push({ grlo: g, datum: fmtD(d), tip: st.dogadjaj, tekst: $("#opis").value.trim(), ponavljanje: String(+$("#pon").value || ""), gotovo: "", uneto: sada(), vreme: $("#vrT") ? normVreme($("#vrT").value) : "" });
      zabelezi(t(`Podsetnik: ${g} – ${st.dogadjaj} (${fmtD(d)})`, `Reminder: ${g} – ${st.dogadjaj} (${fmtD(d)})`));
      promena(t(`Podsetnik zakazan: ${g} – ${st.dogadjaj} (${fmtD(d)})`, `Reminder scheduled: ${g} – ${st.dogadjaj} (${fmtD(d)})`));
      return idi(`karton/${encodeURIComponent(g)}`);
    }
    upisiDogadjaj({ grlo: g, datum: fmtD(d), dogadjaj: st.dogadjaj, partner: $("#partner").value, vrednost: $("#vrednost").value.trim(),
      opis: $("#opis").value.trim(), karenca_meso: broj($("#km").value), karenca_mleko: broj($("#kml").value), vanZapata: $("#van").checked });
    const sled = [k.LECENJE, k.VAKCINA].includes(st.dogadjaj) ? +$("#sled").value || 0 : 0;
    if (sled) S.podsetnici.push({ grlo: g, datum: fmtD(dodajDane(d, sled)), tip: st.dogadjaj, tekst: $("#opis").value.trim(), ponavljanje: String(sled), gotovo: "", uneto: sada() });
    promena(t(`Zapisano: ${g} – ${st.dogadjaj}`, `Recorded: ${g} – ${st.dogadjaj}`));
    idi(`karton/${encodeURIComponent(g)}`);
  };
}

// ---------------------------------------------------------------- Rođenje mladih
function brojac(id, vrednost, min) {
  return `<div class="brojevi"><button type="button" data-za="${id}" data-k="-1">−</button><input id="${id}" inputmode="numeric" value="${vrednost}" data-min="${min}"><button type="button" data-za="${id}" data-k="1">+</button></div>`;
}
function vezBrojace() {
  ekran.querySelectorAll("[data-za]").forEach(b => b.onclick = () => {
    const i = $("#" + b.dataset.za); i.value = Math.max(+i.dataset.min, (parseInt(i.value, 10) || 0) + +b.dataset.k);
  });
}
function ekranRodjenje(ix) {
  const z = S.istorija[+ix];
  postaviVrh(t("Rođeni mladi", "Young born"), true); meni("danas");
  if (!z || !cekaPorodjaj(z)) { ekran.innerHTML = `<div class="prazno">${t("Za ovo parenje je već upisano.", "Already recorded for this mating.")}</div>`; return; }
  const { majka, otac, n } = podaciLegla(z), [od, oc] = granicePorodjaja(z), rani = od && danas() < od;
  ekran.innerHTML = `<div class="kart"><div class="cipovi" style="align-items:center">${t("Majka", "Dam")} ${cip(majka)} ${t("Otac", "Sire")} ${otac ? cip(otac) : "?"}</div>
    <p class="mali">${t("Parenje", "Mating")} ${h(z.datum)}${oc ? ` · ${t("termin", "due")} ${fmtD(oc)}` : ""}</p>
    ${rani ? `<div class="info warn">${t(`Gravidnost još traje – upis je moguć od ${fmtD(od)}. Ako je bio prevremeni porođaj, štikliraj ispod.`, `Pregnancy still in progress – entry possible from ${fmtD(od)}. If it was a premature birth, tick below.`)}</div>` : ""}
    <label class="polje"><span>${t("Datum rođenja", "Date of birth")}</span><input class="unos" id="datum" type="date" value="${uIso(danas())}"></label>
    <div class="dve"><div class="polje"><span class="mali" style="font-weight:700">${t(`Živih (${n[3]})`, `Alive (${n[3]})`)}</span><div style="margin-top:6px">${brojac("ziv", 1, 0)}</div></div>
      <div class="polje"><span class="mali" style="font-weight:700">${t("Mrtvorođenih", "Stillborn")}</span><div style="margin-top:6px">${brojac("mrt", 0, 0)}</div></div></div>
    ${od ? `<label class="provera"><input type="checkbox" id="prev" ${rani ? "checked" : ""}> ${t(`Prevremeni porođaj (pre ${fmtD(od)})`, `Premature birth (before ${fmtD(od)})`)}</label>` : ""}
    <div class="info ok">${t("Pol i oznake ne moraš sada da znaš – mladi čekaju na spisku „Čeka minđušu“.", "You don't need sex and tags now – the young wait on the \"Waiting for ear tag\" list.")}</div>
    <div class="greska" id="gr"></div>
    <div class="dugmad"><button class="dug glavno" id="sac">${t("Zabeleži rođenje", "Record birth")}</button><button class="dug" id="odmah">${t("Odmah upiši u listu", "Enter in list now")}</button></div></div>`;
  vezBrojace();
  const sacuvajR = odmah => {
    const gr = rodjenje(z, fmtD(parsirajDatum($("#datum").value)), parseInt($("#ziv").value, 10) || 0, parseInt($("#mrt").value, 10) || 0, $("#prev") ? $("#prev").checked : false);
    if (gr) return ($("#gr").textContent = gr);
    osveziModel(); promena(t("Rođenje je zabeleženo.", "Birth recorded."));
    if (odmah && leglo(z)) idi(`mindjuse/${ix}`); else idi(`karton/${encodeURIComponent(majka)}`);
  };
  $("#sac").onclick = () => sacuvajR(false);
  $("#odmah").onclick = () => sacuvajR(true);
}

// ---------------------------------------------------------------- Upis mladih u listu (minđuše)
function ekranMindjuse(ix) {
  const z = S.istorija[+ix], lg = z && leglo(z);
  postaviVrh(t("Upis u listu grla", "Entry in animal list"), true); meni("danas");
  if (!lg) { ekran.innerHTML = `<div class="prazno">${t("Ovo leglo je već upisano.", "This litter has already been entered.")}</div>`; return; }
  const [uk, dstr, vec] = lg, { majka, otac, vrsta, rasa, n } = podaciLegla(z), ost = Math.max(1, uk - vec.length);
  const stada = [...new Set([K().STADO_PODMLADAK, ...M.grla().map(a => a.stado).filter(Boolean)])];
  ekran.innerHTML = `<div class="kart"><div class="cipovi" style="align-items:center">${cip(majka)} × ${otac ? cip(otac) : "?"}</div>
    <p class="mali">${t(`Leglo: ${uk} ${n[3]}, rođeno ${dstr}`, `Litter: ${uk} ${n[3]}, born ${dstr}`)}${vec.length ? t(`, već upisano ${vec.length}`, `, already entered ${vec.length}`) : ""} · ${h(vrsta)}${rasa ? ", " + h(rasa) : ""}
      ${M.A[majka] && M.A[otac] ? ` · ${t("inbriding mladih", "inbreeding of young")} ${pct(M.kinship(majka, otac))}` : ""}</p>
    <label class="polje"><span>${t("Stado", "Herd")}</span><input class="unos" id="stado" list="dl-st" value="${h(K().STADO_PODMLADAK)}"></label>
    <datalist id="dl-st">${stada.map(s => `<option value="${h(s)}">`).join("")}</datalist>
    <div id="mladi"></div>
    <button class="dug puno" id="jos">＋ ${t(`Dodaj još jedno ${n[2]}`, `Add another ${n[2]}`)}</button>
    <label class="provera skriveno" id="dCek"><input type="checkbox" id="cek" checked> ${t("Ostali još čekaju minđušu (inače: uginuli ili prodati)", "The others are still waiting for ear tags (otherwise: died or sold)")}</label>
    <div class="greska" id="gr"></div>
    <button class="dug glavno puno" id="sac">${t("Upiši u listu grla", "Enter in animal list")}</button></div>`;
  const redovi = [];
  const dodajRed = () => {
    const i = redovi.length, d = document.createElement("div");
    d.className = "mlado";
    d.innerHTML = `<div class="zag">${i + 1}. ${h(n[2])} <button class="dug" style="min-height:36px" data-x>✕</button></div>
      <div class="dve"><label class="polje"><span>${t("Oznaka *", "Tag *")}</span><input class="unos" data-id></label>
      <label class="polje"><span>${t("Markica", "Ear tag")}</span>${saKamerom('<input class="unos" data-mk>', "markica")}</label></div>
      <div class="izbor" data-pol><button data-p="z">${t("Žensko", "Female")}</button><button data-p="m">${t("Muško", "Male")}</button></div>`;
    const r = { el: d, pol: "" };
    d.querySelector("[data-pol]").onclick = e => { const b = e.target.closest("button"); if (!b) return; r.pol = b.dataset.p; d.querySelectorAll("[data-p]").forEach(x => x.classList.toggle("akt", x === b)); };
    d.querySelector("[data-x]").onclick = () => { if (redovi.length > 1) { redovi.splice(redovi.indexOf(r), 1); d.remove(); azur(); } };
    redovi.push(r); $("#mladi").appendChild(d); azur();
  };
  const azur = () => $("#dCek").classList.toggle("skriveno", vec.length + redovi.length >= uk);
  for (let i = 0; i < ost; i++) dodajRed();
  $("#jos").onclick = dodajRed;
  $("#sac").onclick = () => {
    const mladi = redovi.map(r => ({ id: r.el.querySelector("[data-id]").value, markica: r.el.querySelector("[data-mk]").value, pol: r.pol }));
    const gr = upisUListu(z, mladi, $("#stado").value, $("#cek").checked);
    if (gr) return ($("#gr").textContent = gr);
    promena(t("Upisano u listu: ", "Entered in the list: ") + mladi.map(x => x.id).join(", "));
    idi(`karton/${encodeURIComponent(majka)}`);
  };
}

// ---------------------------------------------------------------- Novo grlo
function ekranNovoGrlo(_, upit) {
  const izm = upit && upit.get("izmena") ? S.grla.find(r => r.id === upit.get("izmena")) : null;   // izmena postojećeg grla
  postaviVrh(izm ? t(`Izmeni: ${izm.id}`, `Edit: ${izm.id}`) : t("Novo grlo", "New animal"), true); meni("grla");
  const k = K(), sva = M.grla(), posl = izm || sva[0] || {};
  const cesto = l => { const c = {}; l.forEach(x => { if (x) c[x] = (c[x] || 0) + 1; }); return Object.keys(c).sort((a, b) => c[b] - c[a])[0] || ""; };
  const stada = [...new Set(sva.map(a => a.stado).filter(Boolean))], rase = [...new Set(sva.map(a => a.rasa).filter(Boolean))];
  let pol = izm ? izm.pol || "" : "", status = izm ? ((izm.status || "aktivno") === "aktivno" ? "aktivno" : "neaktivno") : "";
  ekran.innerHTML = `<div class="kart">
    <div class="dve"><label class="polje"><span>${t("Oznaka (ime)", "Tag (name)")}</span><input class="unos" id="id" ${izm ? `value="${h(izm.id)}" readonly style="opacity:.6"` : `placeholder="${t("prazno = markica", "empty = ear tag")}"`}></label>
      <label class="polje"><span>${t("Markica", "Ear tag")}</span>${saKamerom(`<input class="unos" id="mk" value="${h(upit ? upit.get("mk") || "" : "")}">`, "markica")}</label></div>
    <div class="polje"><span class="mali" style="font-weight:700">${t("Pol *", "Sex *")}</span><div class="izbor" id="pol" style="margin-top:6px"><button data-p="z">${t("Žensko", "Female")}</button><button data-p="m">${t("Muško", "Male")}</button></div></div>
    <div style="height:12px"></div>
    <div class="dve"><label class="polje"><span>${t("Vrsta", "Species")}</span><select class="unos" id="vrsta">${k.VRSTE.map(v => `<option ${v === (posl.vrsta || k.VRSTE[0]) ? "selected" : ""}>${h(v)}</option>`).join("")}</select></label>
      <label class="polje"><span>${t("Rasa", "Breed")}</span><input class="unos" id="rasa" list="dl-r"></label></div>
    <datalist id="dl-r"></datalist>
    <label class="polje skriveno" id="nam-p"><span>${t("Namena rase *", "Breed purpose *")}</span><select class="unos" id="nam"></select></label>
    <label class="polje"><span>${t("Datum rođenja", "Date of birth")}</span><input class="unos" id="dat" type="date"></label>
    ${izm ? `<label class="polje"><span>${t("Udeo krvi (npr. romanovska=50;pramenka=50)", "Breed share (e.g. romanov=50;pramenka=50)")}</span><input class="unos" id="udeo" value="${h(izm.udeo_krvi || "")}"></label>` : ""}
    <div class="dve"><label class="polje"><span>${t("Otac", "Sire")}</span><input class="unos" id="otac" list="dl-o" autocomplete="off"></label>
      <label class="polje"><span>${t("Majka", "Dam")}</span><input class="unos" id="majka" list="dl-m" autocomplete="off"></label></div>
    ${datalistGrla("dl-o", sva.filter(a => a.pol === "m"))}${datalistGrla("dl-m", sva.filter(a => a.pol === "z"))}
    <div class="dve"><label class="polje"><span>${t("Stado", "Herd")}</span><input class="unos" id="stado" list="dl-s" value="${h(cesto(sva.map(a => a.stado)))}"></label>
      <label class="polje"><span>${t("Poreklo", "Origin")}</span><select class="unos" id="por"><option></option>${k.POREKLA.map(p => `<option>${h(p)}</option>`).join("")}</select></label></div>
    <datalist id="dl-s">${stada.map(s => `<option value="${h(s)}">`).join("")}</datalist>
    <label class="polje"><span>${t("Poreklo od (kupljeno od…)", "Origin from (bought from…)")}</span><input class="unos" id="pod"></label>
    <label class="polje"><span>${t("Elektronski broj (RFID čitač)", "Electronic ID (RFID reader)")}</span><input class="unos" id="rfid" value="${h(upit ? upit.get("rfid") || "" : "")}" placeholder="${t("nije obavezno", "optional")}"></label>
    <label class="polje"><span>⚠ ${t("Napomena o grlu", "Note about the animal")}</span><input class="unos" id="nap" placeholder="${t("vidi se svuda gde je grlo (npr. Agresivna, Ne muzi – lečenje)", "shown wherever the animal appears (e.g. Aggressive, Do not milk – treatment)")}"></label>
    <label class="polje" style="display:flex;align-items:center;gap:10px"><input type="checkbox" id="autoh" style="width:22px;height:22px"><span style="font-weight:700">${t("Autohtona rasa", "Native (indigenous) breed")}</span></label>
    <div class="polje"><span class="mali" style="font-weight:700">${t("Status grla *", "Status *")}</span><div class="izbor" id="status" style="margin-top:6px"><button data-s="aktivno">${t("Aktivno – na farmi", "Active – on the farm")}</button><button data-s="neaktivno">${t("Neaktivno – nije na farmi", "Inactive – not on the farm")}</button></div></div>
    <div class="greska" id="gr"></div>
    <button class="dug glavno puno" id="sac">${izm ? t("Sačuvaj izmene", "Save changes") : t("Sačuvaj grlo", "Save animal")}</button></div>`;
  if (izm) {                                       // popuni polja postojećim podacima
    const pd = parsirajDatum(izm.datum_rodjenja);
    for (const [sel, v] of [["#mk", izm.markica], ["#rasa", izm.rasa], ["#otac", izm.otac], ["#majka", izm.majka], ["#stado", izm.stado],
      ["#pod", izm.poreklo_od], ["#rfid", izm.rfid], ["#nap", izm.napomena], ["#dat", pd ? uIso(pd) : ""]]) $(sel).value = v || "";
    if (izm.vrsta && ![...$("#vrsta").options].some(o => o.value === izm.vrsta)) $("#vrsta").insertAdjacentHTML("beforeend", `<option>${h(izm.vrsta)}</option>`);
    $("#vrsta").value = izm.vrsta || $("#vrsta").value;
    if (izm.poreklo && ![...$("#por").options].some(o => o.value === izm.poreklo)) $("#por").insertAdjacentHTML("beforeend", `<option>${h(izm.poreklo)}</option>`);
    $("#por").value = izm.poreklo || "";
    $("#autoh").checked = !!izm.autohtona;
    $("#pol").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x.dataset.p === pol));
    $("#status").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x.dataset.s === status));
  }
  $("#pol").onclick = e => { const b = e.target.closest("button"); if (!b) return; pol = b.dataset.p; $("#pol").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x === b)); };
  $("#status").onclick = e => { const b = e.target.closest("button"); if (!b) return; status = b.dataset.s; $("#status").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x === b)); };
  const namene = () => {                 // namena rase za goveda, ovce, koze i svinje
    const izbori = nameneZa($("#vrsta").value), sad = $("#nam").value;
    $("#nam-p").classList.toggle("skriveno", !izbori.length);
    $("#nam").innerHTML = `<option value="">${t("– izaberi –", "– choose –")}</option>` + izbori.map(x => `<option ${x === sad ? "selected" : ""}>${h(x)}</option>`).join("");
  };
  const raseLista = () => { $("#dl-r").innerHTML = raseZaVrstu($("#vrsta").value).map(r => `<option value="${h(r)}">`).join(""); };
  $("#vrsta").onchange = () => { namene(); raseLista(); }; namene(); raseLista();
  if (izm && izm.namena && [...$("#nam").options].some(o => o.value === izm.namena)) $("#nam").value = izm.namena;
  $("#rasa").addEventListener("input", () => { if (autohtonaRasa($("#rasa").value)) $("#autoh").checked = true; });
  $("#rasa").addEventListener("change", () => {      // namena važi za celu rasu – popuni je kad rasa već ima grla
    const nm = namenaRase($("#vrsta").value, normRasa($("#rasa").value));
    if (nm && [...$("#nam").options].some(o => o.value === nm)) $("#nam").value = nm;
    const moja = mojaRasa($("#vrsta").value, $("#rasa").value);
    if (moja && moja.autohtona) $("#autoh").checked = true;
  });
  $("#majka").addEventListener("change", () => {     // otac: mužjak iz stada majke (pušten sa ženkama), ako nije upisan
    const mj = M.nadji($("#majka").value), kand = mj ? M.muzjaciUStadu(mj) : [];
    if (kand.length === 1 && !$("#otac").value.trim()) { $("#otac").value = kand[0]; poruka(t(`Otac: ${kand[0]} – mužjak iz stada majke`, `Sire: ${kand[0]} – male in the dam's herd`)); }
    else if (kand.length > 1 && !$("#otac").value.trim()) poruka(t(`U stadu majke su mužjaci: ${kand.join(", ")} – izaberi oca`, `Males in the dam's herd: ${kand.join(", ")} – choose the sire`));
  });
  $("#majka").addEventListener("change", () => {     // namena od majke, ako još nije izabrana
    const mj = M.nadji($("#majka").value);
    if (mj && M.A[mj].namena && !$("#nam").value && [...$("#nam").options].some(o => o.value === M.A[mj].namena)) $("#nam").value = M.A[mj].namena;
  });
  $("#sac").onclick = () => {
    const dat = $("#dat").value ? fmtD(parsirajDatum($("#dat").value)) : "";
    if (izm) {
      const v = { markica: $("#mk").value, pol, vrsta: $("#vrsta").value, rasa: $("#rasa").value, namena: $("#nam").value, autohtona: $("#autoh").checked,
        rfid: $("#rfid").value, napomena: $("#nap").value, status, datum_rodjenja: dat, otac: $("#otac").value, majka: $("#majka").value,
        stado: $("#stado").value, poreklo: $("#por").value, poreklo_od: $("#pod").value, udeo_krvi: $("#udeo").value };
      const n = drugaNamenaRase(izm.id, v.vrsta, v.rasa, v.namena);
      if (n && !confirm(t(`Namena važi za celu rasu ${normRasa(v.rasa)}.\n\nPromeniti namenu u „${v.namena}“ i kod još ${n} grla te rase?`,
                          `The purpose applies to the whole ${normRasa(v.rasa)} breed.\n\nChange the purpose to “${v.namena}” for ${n} more animals of this breed?`))) return;
      const rez = izmeniGrlo(izm.id, v);
      if (typeof rez === "string") return ($("#gr").textContent = rez);
      promena(rez.promene.length ? t(`Sačuvano: ${izm.id}`, `Saved: ${izm.id}`) : t("Nema izmena.", "No changes."));
      return idi(`karton/${encodeURIComponent(izm.id)}`);
    }
    const rez = novoGrlo({ id: $("#id").value, markica: $("#mk").value, pol, vrsta: $("#vrsta").value, rasa: $("#rasa").value, namena: $("#nam").value, autohtona: $("#autoh").checked, rfid: $("#rfid").value, napomena: $("#nap").value,
      status, datum_rodjenja: dat, otac: $("#otac").value, majka: $("#majka").value, stado: $("#stado").value, poreklo: $("#por").value, poreklo_od: $("#pod").value });
    if (typeof rez === "string") return ($("#gr").textContent = rez);
    promena(rez.preimenovano ? t(`${rez.preimenovano} već postoji – upisano kao ${rez.id}`, `${rez.preimenovano} already exists – saved as ${rez.id}`)
                             : t(`Sačuvano: ${rez.id}`, `Saved: ${rez.id}`));
    idi(`karton/${encodeURIComponent(rez.id)}`);
  };
}

// ---------------------------------------------------------------- Parenje (najbolji partneri)
function ekranParenje(id) {
  postaviVrh(id ? t(`Partneri za ${id}`, `Partners for ${id}`) : t("Parenje", "Mating"), !!id); meni("parenje");
  if (!id || !M.A[id]) {
    const zenke = M.grla(true).filter(a => a.pol === "z");
    ekran.innerHTML = `<p class="mali" style="margin:4px 4px 10px">${t("Izaberi ženku – program pokazuje sa kojim mužjacima je najmanji inbriding potomaka.", "Choose a female – the program shows which males give the least inbreeding in the offspring.")}</p>
      <input class="pretraga" id="q" type="search" placeholder="🔍 ${t("Traži ženku", "Search female")}"><div style="height:10px"></div><div id="sp"></div>`;
    const crtaj = (koliko = NA_STRANI) => {
      const q = norm($("#q").value);
      $("#sp").innerHTML = listaGrla(zenke.filter(a => !q || norm(a.id).includes(q) || norm(a.markica).includes(q)), t("Nema ženki u zapatu.", "No females in the herd."), koliko)
        .replace(/href="#karton\//g, 'href="#parenje/');
      const jos = $("#sp [data-jos]");
      if (jos) jos.onclick = () => crtaj(+jos.dataset.jos);
    };
    $("#q").oninput = () => crtaj(); crtaj();
    return;
  }
  const svi = partneri(id), p = svi.slice(0, 60), a = M.A[id];
  ekran.innerHTML = `<div class="kart" style="display:flex;gap:10px;align-items:center">${cip(id)}<div class="mali">${h(opisGrla(a))}<br>${t("Granica rizika", "Risk limit")} ${pct(S.prag)}</div></div>` +
    (p.length ? `<div class="lista">${p.map(x => { const [tx, kl] = procena(x.f, S.prag); return `<a class="red" href="#dogadjaj?grlo=${encodeURIComponent(id)}&tip=${encodeURIComponent(K().PARENJE)}&partner=${encodeURIComponent(x.id)}">${cip(x.id, false)}
      <div class="sred"><b class="znak ${kl}" style="display:inline-block">${h(tx)}</b><span>${t("zajednički geni", "shared genes")} ${pct(x.r)}${x.rasa ? " · " + h(x.rasa) : ""} · ${h(M.odnos(id, x.id))}</span></div><div class="f">${pct(x.f)}</div></a>`; }).join("")}</div>
      <p class="mali" style="margin:0 4px">${svi.length > p.length ? t(`Prikazano ${p.length} najboljih od ${svi.length}. `, `Showing the best ${p.length} of ${svi.length}. `) : ""}${t("Broj desno = očekivani inbriding potomka. Klikni partnera da upišeš parenje.", "Number on the right = expected inbreeding of the offspring. Tap a partner to record the mating.")}</p>`
      : `<div class="prazno">${t("Nema grla suprotnog pola iste vrste u zapatu.", "No animals of the opposite sex and same species in the herd.")}</div>`);
}

// ---------------------------------------------------------------- Srodstvo dva grla
function ekranSrodstvo(_, upit) {
  postaviVrh(t("Srodstvo", "Relationship"), true); meni("vise");
  const sva = M.grla();
  ekran.innerHTML = `<div class="kart"><div class="dve"><label class="polje"><span>${t("Grlo A", "Animal A")}</span><input class="unos" id="a" list="dl" value="${h(upit.get("a") || "")}" autocomplete="off"></label>
    <label class="polje"><span>${t("Grlo B", "Animal B")}</span><input class="unos" id="b" list="dl" value="${h(upit.get("b") || "")}" autocomplete="off"></label></div>${datalistGrla("dl", sva)}<div id="rez"></div></div>`;
  const crtaj = () => {
    const a = M.nadji($("#a").value), b = M.nadji($("#b").value);
    if (!a || !b || a === b) { $("#rez").innerHTML = `<p class="mali">${t("Upiši dva različita grla.", "Enter two different animals.")}</p>`; return; }
    const f = M.kinship(a, b), [tx, kl] = procena(f, S.prag);
    const zaj = [...M.preci(a)].filter(x => M.preci(b).has(x)).map(x => [x, M.doprinos(a, x), M.doprinos(b, x)]).sort((p, q) => q[1] + q[2] - p[1] - p[2]).slice(0, 8);
    $("#rez").innerHTML = `<dl class="polja"><dt>${t("Odnos", "Relationship")}</dt><dd>${h(M.odnos(a, b))}</dd><dt>${t("Zajednički geni", "Shared genes")}</dt><dd>${pct(M.r(a, b))}</dd>
      <dt>${t("Inbriding potomka", "Offspring inbreeding")}</dt><dd><span class="znak ${kl}">${pct(f)}</span> ${h(tx)}</dd></dl>
      ${zaj.length ? `<h2 style="margin-top:14px">${t("Zajednički preci", "Common ancestors")}</h2>${zaj.map(([x, da, db]) => `<div class="ist">${cip(x)} <span class="mali">${a}: ${pct(da)} · ${b}: ${pct(db)}</span></div>`).join("")}` : ""}`;
  };
  $("#a").oninput = $("#b").oninput = crtaj; crtaj();
}

// ---------------------------------------------------------------- Podsetnik
function ekranPodsetnik() {
  postaviVrh(t("Novi podsetnik", "New reminder"), true); meni("danas");
  const k = K();
  const zaGrlo = delovi().upit.get("grlo") || "";            // otvoreno sa kartice grla – grlo je već upisano
  ekran.innerHTML = `<div class="kart"><label class="polje"><span>${t("Grlo (može i prazno)", "Animal (can be empty)")}</span><input class="unos" id="g" list="dl" autocomplete="off" value="${h(zaGrlo)}"></label>${datalistGrla("dl", M.grla(true))}
    <label class="polje"><span>${t("Datum *", "Date *")}</span><input class="unos" id="d" type="date" value="${uIso(dodajDane(danas(), 7))}"></label>
    <label class="polje"><span>${t("Vreme (nije obavezno – javi tačno u to vreme)", "Time (optional – notify exactly then)")}</span><input class="unos" id="vr" type="time"></label>
    <label class="polje"><span>${t("Vrsta *", "Type *")}</span><input class="unos" id="tip" list="dl-t" value="${h(k.VAKCINA)}"></label>
    <datalist id="dl-t">${k.DOGADJAJI.map(d => `<option value="${h(d)}">`).join("")}</datalist>
    <label class="polje"><span>${t("Tekst", "Text")}</span><input class="unos" id="tx"></label>
    <label class="polje"><span>${t("Ponavlja se na (dana, prazno = ne)", "Repeat every (days, empty = no)")}</span><input class="unos" id="pon" inputmode="numeric"></label>
    <div class="greska" id="gr"></div><button class="dug glavno puno" id="sac">${t("Sačuvaj", "Save")}</button></div>`;
  $("#sac").onclick = () => {
    const g = $("#g").value.trim() ? M.nadji($("#g").value) : "", d = parsirajDatum($("#d").value), tip = $("#tip").value.trim();
    if ($("#g").value.trim() && !g) return ($("#gr").textContent = t("Grlo nije pronađeno.", "Animal not found."));
    if (!d || !tip) return ($("#gr").textContent = t("Upiši datum i vrstu.", "Enter date and type."));
    noviPodsetnik(g, fmtD(d), tip, $("#tx").value.trim(), parseInt($("#pon").value, 10) || 0, $("#vr").value);
    promena(t("Podsetnik je sačuvan.", "Reminder saved.")); idi("danas");
  };
}

// ---------------------------------------------------------------- Više
function ekranVise() {
  postaviVrh(t("Više", "More"), false); meni("vise");
  const n = S.promene.length;
  ekran.innerHTML = `${dugmeInstalacije()}<div class="lista">
    ${oblakPodesen() ? `<a class="red" href="#sinh"><span style="font-size:24px">☁</span><div class="sred"><b>${S.sinh ? t("Povezano sa računarom", "Connected to computer") : t("Upari sa računarom (QR kod ili kod)", "Pair with computer (QR or code)")}</b><span>${h(S.sinh ? (sinhStanje.tekst || S.sinh.naziv || "") : t("jednom skeniraš i sve se samo usklađuje", "scan once and everything syncs"))}</span></div></a>` : ""}
    <a class="red" href="#prenos"><span style="font-size:24px">⇅</span><div class="sred"><b>${t("Prenos sa računarom", "Transfer with computer")}</b><span>${n ? t(`${n} promena čeka slanje računaru`, `${n} changes waiting to be sent`) : t("sve je poslato", "everything sent")}</span></div>${n ? `<span class="znak warn">${n}</span>` : ""}</a>
    ${S.mreza ? `<a class="red" href="#udruzenje"><span style="font-size:24px">⌂</span><div class="sred"><b>${t("Udruženje – druge farme", "Association – other farms")}</b><span>${h(S.mreza.naziv || "")} · 🔒 ${t("samo pregled", "view only")}</span></div></a>` : ""}
    <a class="red" href="#novarasa"><span style="font-size:24px">✦</span><div class="sred"><b>${t("Nova rasa", "New breed")}</b><span>${t("udeo krvi, cilj programa, parenja", "breed share, goal, matings")}</span></div></a>
    <a class="red" href="#finansije"><span style="font-size:24px">💰</span><div class="sred"><b>${t("Finansije", "Finances")}</b><span>${t("prihodi i troškovi", "income and costs")}</span></div></a>
    <a class="red" href="#istorija"><span style="font-size:24px">📜</span><div class="sred"><b>${t("Istorija farme", "Farm history")}</b><span>${t("svi događaji, pretraga", "all events, search")}</span></div></a>
    <a class="red" href="#statistika"><span style="font-size:24px">📊</span><div class="sred"><b>${t("Statistika", "Statistics")}</b><span>${t("stado u brojevima, inbriding, očevi", "herd in numbers, inbreeding, sires")}</span></div></a>
    <a class="red" href="#rase"><span style="font-size:24px">🧬</span><div class="sred"><b>${t("Moje rase", "My breeds")}</b><span>${t("rasa se upiše jednom, sa namenom", "enter a breed once, with its purpose")}</span></div></a>
    <a class="red" href="#vrste"><span style="font-size:24px">🦌</span><div class="sred"><b>${t("Moje vrste", "My species")}</b><span>${t("magarci, bivoli, jeleni…", "donkeys, buffalo, deer…")}</span></div></a>
    <a class="red" href="#" id="jaIme"><span style="font-size:24px">👤</span><div class="sred"><b>${h(S.korisnik || t("Ime i prezime nije upisano", "Name not entered"))}</b><span>${t("ko radi u aplikaciji – dodirni za promenu", "who is using the app – tap to change")}</span></div></a>
    <a class="red" href="#rang"><span style="font-size:24px">⭐</span><div class="sred"><b>${t("Rang lista grla", "Animal ranking")}</b><span>${t("najbolja grla za priplod", "best animals for breeding")}</span></div></a>
    <a class="red" href="#srodstvo"><span style="font-size:24px">⚯</span><div class="sred"><b>${t("Srodstvo dva grla", "Relationship of two animals")}</b><span>${t("koliko su srodni, zajednički preci", "how related they are, common ancestors")}</span></div></a>
    <a class="red" href="#novo"><span style="font-size:24px">＋</span><div class="sred"><b>${t("Novo grlo", "New animal")}</b><span>${t("kupljeno ili rođeno", "bought or born")}</span></div></a>
    <a class="red" href="#muznja"><span style="font-size:24px">🥛</span><div class="sred"><b>${t("Mužnja", "Milking")}</b><span>${t("dnevni upis mleka za mlečna grla", "daily milk entry for dairy animals")}</span></div></a>
    <a class="red" href="#podsetnik"><span style="font-size:24px">⏰</span><div class="sred"><b>${t("Novi podsetnik", "New reminder")}</b><span>${t("vakcinacija, lečenje…", "vaccination, treatment…")}</span></div></a>
    <a class="red" href="#" id="obUk"><span style="font-size:24px">🔔</span><div class="sred"><b>${t("Obaveštenja na telefonu", "Phone notifications")}</b><span>${h(stanjeObavestenja()[1])}</span><span>${h(t(`od ${obavSat()}:00 h · ${danaUnapred()} dana pre roka (menja se na računaru)`, `from ${obavSat()}:00 · ${danaUnapred()} days before due (set on the computer)`))}</span></div>${stanjeObavestenja()[0] === "da" ? `<span class="znak">✓</span>` : ""}</a>
    <a class="red" href="#" id="problem"><span style="font-size:24px">⚠</span><div class="sred"><b>${t("Prijavi problem", "Report a problem")}</b><span>${t("pošalji izveštaj o greškama (bez podataka o grlima)", "send an error report (no animal data)")}</span></div></a>
    </div>
    <div class="kart"><label class="mali" for="jezikV">🌐 ${t("Jezik", "Language")}</label>
      <select class="dug puno" id="jezikV" style="margin-top:6px">${JEZICI_TEL.map(([k, n]) => `<option value="${k}"${k === S.jezik ? " selected" : ""}>${n}</option>`).join("")}</select>
      <div class="mali" style="margin-top:6px">${t("Telefon ostaje na jeziku koji izabereš, bez obzira na jezik računara.", "The phone keeps the language you choose, whatever the computer's language.")}</div></div>
    <div class="kart mali">HerdDoc ${t("za telefon", "for phone")} ${VERZIJA_TEL}<br>
    ${S.licenca ? `🔑 ${t("Licenca", "Licence")}: ${h(S.licenca.naziv)}${S.licenca.limit == null ? "" : " – " + t(`do ${S.licenca.limit} grla`, `up to ${S.licenca.limit} animals`)}<br>` : ""}
    ${S.izvoz ? t(`Podaci sa računara od ${h(S.izvoz.datum || "")}`, `Data from computer of ${h(S.izvoz.datum || "")}`) : t("Podaci su upisani samo na telefonu.", "Data entered on the phone only.")}<br>
    ${t("Podrška", "Support")}: <a href="mailto:${PODRSKA}">${PODRSKA}</a></div>`;
  $("#problem").onclick = ev => { ev.preventDefault(); prijaviProblem(); };
  $("#obUk").onclick = ev => { ev.preventDefault(); if (stanjeObavestenja()[0] !== "da") ukljuciObavestenja(); else poruka(stanjeObavestenja()[1]); };
  $("#jezikV").onchange = e => { izaberiJezik(e.target.value); prikazi(); };
  $("#jaIme").onclick = ev => { ev.preventDefault(); traziIme(!!S.korisnik); };
  osveziInstalaciju();
}

// ---------------------------------------------------------------- udruženje: grla drugih farmi, samo pregled (nema izmene)
const filtU = { farma: "", vrsta: "", pol: "", q: "", sva: false };
function ekranUdruzenje() {
  postaviVrh(t("Udruženje", "Association"), true); meni("vise");
  if (!S.mreza) { ekran.innerHTML = `<div class="kart mali">${t("Telefon nije u udruženju. Udruženje se podešava na računaru.", "The phone is not in an association. The association is set up on the computer.")}</div>`; return; }
  const P = S.mrezaPodaci, farme = P ? P.farme : [];
  const sva = [];
  farme.forEach(f => f.grla.forEach(g => sva.push([f.naziv, g])));
  const vrste = [...new Set(sva.map(([, g]) => g.vrsta).filter(Boolean))].sort();
  ekran.innerHTML = `<div class="kart"><h2>${h(P ? P.naziv : S.mreza.naziv)}</h2>
      <div class="mali">🔒 ${t("Samo pregled. Grla menja samo farma kojoj pripadaju – ne ulaze u tvoj spisak grla.", "View only. Only the farm that owns the animals changes them – they do not go into your list.")}</div>
      <div class="mali" id="uSt" style="margin-top:6px">${P ? t(`Učitano ${h(P.ucitano)}`, `Loaded ${h(P.ucitano)}`) : t("Još nije učitano.", "Not loaded yet.")}${P && !P.provereno ? " · " + t("potpisi nisu provereni na ovom telefonu", "signatures not checked on this phone") : ""}</div>
      <button class="dug puno" id="uOsv" style="margin-top:10px">⟳ ${t("Osveži", "Refresh")}</button></div>
    ${farme.length ? `<div class="kart"><h2>${t("Farme", "Farms")}</h2>${farme.map(f => `<div class="mali" style="margin:4px 0"><b style="color:var(--ink)">${h(f.naziv)}</b>${f.mesto ? " · " + h(f.mesto) : ""}${f.mapa ? ` · <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(f.mapa)}" target="_blank" rel="noopener">📍 ${t("mapa", "map")}</a>` : ""} · ${f.greska ? `<span class="znak warn">${h(f.greska)}</span>` : t(`${f.grla.filter(g => (g.status || "aktivno") === "aktivno").length} grla`, `${f.grla.filter(g => (g.status || "aktivno") === "aktivno").length} animals`)}</div>`).join("")}</div>` : ""}
    <input class="pretraga" id="uq" type="search" placeholder="🔍 ${t("Traži oznaku, rasu, roditelje…", "Search ID, breed, parents…")}" value="${h(filtU.q)}">
    <div class="filteri">${[["", t("Sva", "All")], ["z", t("Ženska", "Females")], ["m", t("Muška", "Males")]].map(([k, n]) =>
      `<button data-upol="${k}" class="${filtU.pol === k ? "akt" : ""}">${n}</button>`).join("")}
      <button id="uSva" class="${filtU.sva ? "akt" : ""}">${t("i neaktivna", "incl. inactive")}</button></div>
    <div class="dve-izbor"><select id="uF" class="stado-izbor ${filtU.farma ? "akt" : ""}"><option value="">${t("Sve farme", "All farms")}</option>${farme.map(f => `<option${f.naziv === filtU.farma ? " selected" : ""}>${h(f.naziv)}</option>`).join("")}</select>
      <select id="uV" class="stado-izbor ${filtU.vrsta ? "akt" : ""}"><option value="">${t("Sve vrste", "All species")}</option>${vrste.map(v => `<option${v === filtU.vrsta ? " selected" : ""}>${h(v)}</option>`).join("")}</select></div>
    <div id="usp"></div>`;
  const crtaj = () => {
    const q = filtU.q.trim().toLowerCase();
    const sp = sva.filter(([f, g]) => (!filtU.farma || f === filtU.farma) && (!filtU.vrsta || g.vrsta === filtU.vrsta) && (!filtU.pol || g.pol === filtU.pol) &&
      (filtU.sva || (g.status || "aktivno") === "aktivno") && (!q || [g.id, g.markica, g.rasa, g.otac, g.majka, f].join(" ").toLowerCase().includes(q)))
      .sort((a, b) => a[0].localeCompare(b[0]) || sortKey(a[1].id || "", b[1].id || ""));
    $("#usp").innerHTML = `<div class="mali" style="margin:0 4px 8px">${P ? t(`${sp.length} grla`, `${sp.length} animals`) : ""}</div>` +
      (sp.length ? `<div class="lista">${sp.slice(0, 300).map(([f, g], i) => {
        const d = parsirajDatum(g.datum_rodjenja);
        return `<a class="red" href="#" data-ug="${i}"><span style="font-size:22px">${g.pol === "m" ? "♂" : g.pol === "z" ? "♀" : "•"}</span><div class="sred"><b>${h(g.id || "?")}</b><span>${h(f)} · ${h([g.rasa, d ? fmtD(d) : ""].filter(Boolean).join(" · "))}</span><span class="uDet skriveno" style="white-space:normal">${
          [[t("Vrsta", "Species"), g.vrsta], [t("Markica", "Ear tag"), g.markica], [t("Namena", "Purpose"), g.namena], [t("Otac", "Sire"), g.otac], [t("Majka", "Dam"), g.majka],
           [t("Status", "Status"), g.status], [t("Udeo krvi", "Breed share"), g.udeo_krvi], [t("Ocena", "Score"), g.ocena ? Object.entries(procitajOcenu(g.ocena)[0]).map(([k, v]) => `${(rucneOsobine().find(r => r[0] === k) || [k, k])[1].split(" (")[0]} ${String(v).replace(".", EN() ? "." : ",")}`).join(", ") : ""]]
            .filter(x => x[1]).map(([n, v]) => `${h(n)}: <b style="display:inline">${h(v)}</b>`).join("<br>")}<br>🔒 ${h(t(`menja ga samo: ${f}`, `changed only by: ${f}`))}</span></div></a>`;
      }).join("")}</div>` : (P ? `<div class="kart mali">${farme.length ? t("Nema grla za ovaj izbor.", "No animals for this selection.") : t("Druge farme još nisu poslale podatke.", "Other farms have not sent data yet.")}</div>` : ""));
    $("#usp").querySelectorAll("[data-ug]").forEach(a => a.onclick = ev => { ev.preventDefault(); a.querySelector(".uDet").classList.toggle("skriveno"); });
  };
  crtaj();
  $("#uq").oninput = e => { filtU.q = e.target.value; crtaj(); };
  ekran.querySelectorAll("[data-upol]").forEach(b => b.onclick = () => { filtU.pol = b.dataset.upol; ekranUdruzenje(); });
  $("#uSva").onclick = () => { filtU.sva = !filtU.sva; ekranUdruzenje(); };
  $("#uF").onchange = e => { filtU.farma = e.target.value; ekranUdruzenje(); };
  $("#uV").onchange = e => { filtU.vrsta = e.target.value; ekranUdruzenje(); };
  const osvezi = () => {
    $("#uSt").textContent = "⟳ " + t("učitavam…", "loading…");
    ucitajUdruzenje().then(() => { if (delovi().ekran === "udruzenje") ekranUdruzenje(); })
      .catch(e => { $("#uSt").textContent = (e instanceof GreskaMreze ? t("Nema interneta – prikazano je poslednje učitano.", "No internet – showing the last loaded data.") : e.message); });
  };
  $("#uOsv").onclick = osvezi;
  if (!P) osvezi();
}

async function prijaviProblem() {
  let greske = [];
  try { greske = JSON.parse(localStorage.getItem("farmer-greske") || "[]"); } catch (e) { /* */ }
  const tekst = [`HerdDoc ${t("za telefon", "for phone")} ${VERZIJA_TEL} – ${t("izveštaj o problemu", "problem report")}`, navigator.userAgent,
    `${t("Grla", "Animals")}: ${S.grla.length} · ${t("istorija", "history")}: ${S.istorija.length} · ${t("čeka slanje", "waiting")}: ${S.promene.length}`,
    `${t("Upareno", "Paired")}: ${!!S.sinh}${S.sinh ? " · " + (S.sinh.iskljucen ? t("isključen", "disconnected") : sinhStanje.tekst) : ""}`, "",
    t("--- poslednje greške ---", "--- last errors ---")].concat(greske.length ? greske.map(g => `${g.v} [${g.g}] ${g.p}`) : [t("(nema zapisanih grešaka)", "(no recorded errors)")]).join("\n");
  if (confirm(t(`Poslati izveštaj mejlom na ${PODRSKA}?\n\nOK = mejl · Otkaži = Viber / druga aplikacija`,
                `Send the report by e-mail to ${PODRSKA}?\n\nOK = e-mail · Cancel = Viber / other app`))) {
    const telo = t("Opis problema (šta si radio kad se pojavio):\n\n\n", "Problem description (what you were doing):\n\n\n") + tekst.slice(0, 1500);
    location.href = `mailto:${PODRSKA}?subject=${encodeURIComponent("HerdDoc – " + t("prijava problema", "problem report") + " " + VERZIJA_TEL)}&body=${encodeURIComponent(telo)}`;
    return;
  }
  try {
    if (navigator.share) { await navigator.share({ title: "HerdDoc – " + t("izveštaj o problemu", "problem report"), text: tekst + "\n\n" + t("Za", "To") + ": " + PODRSKA }); return; }
  } catch (e) { if (e && e.name === "AbortError") return; }
  try { await navigator.clipboard.writeText(tekst); poruka(t("Izveštaj je kopiran – nalepi ga u poruku (Viber, mejl).", "Report copied – paste it into a message.")); }
  catch (e) { prompt(t("Kopiraj izveštaj:", "Copy the report:"), tekst); }
}

// ---------------------------------------------------------------- Prenos
function izaberiFajl() {
  const f = $("#fajl");
  f.value = "";
  f.onchange = async () => {
    const fajl = f.files[0];
    if (!fajl) return;
    try {
      const obj = JSON.parse(await fajl.text());
      if (obj.format === "farmer-telefon-povratak") throw new Error(t("Ovo je fajl koji je telefon napravio za računar. Učitaj ga na računaru.", "This is the file the phone made for the computer. Load it on the computer."));
      if (S.promene.length && !confirm(t(`Na telefonu ima ${S.promene.length} promena koje NISU poslate računaru. Ako učitaš novi fajl, te promene se gube.\n\nIpak učitati?`,
        `The phone has ${S.promene.length} changes NOT sent to the computer. Loading a new file discards them.\n\nLoad anyway?`))) return;
      ucitajSaRacunara(obj);
      S.pocetak = true; sacuvaj();
      poruka(t(`Učitano ${M.grla().length} grla.`, `Loaded ${M.grla().length} animals.`));
      idi("grla"); prikazi();
    } catch (e) { alert(t("Fajl ne može da se učita.\n\n", "The file cannot be loaded.\n\n") + e.message); }
  };
  f.click();
}
async function posaljiRacunaru() {
  const d = new Date(), ime = `farmer-sa-telefona-${uIso(d)}-${pad(d.getHours())}${pad(d.getMinutes())}.txt`;
  const tekst = JSON.stringify(paketZaRacunar());
  const fajl = new File([tekst], ime, { type: "text/plain" });
  try {
    if (navigator.canShare && navigator.canShare({ files: [fajl] })) {
      await navigator.share({ files: [fajl], title: "HerdDoc", text: t("Podaci sa telefona za HerdDoc na računaru", "Phone data for HerdDoc on the computer") });
      return poruka(t("Poslato. Na računaru: Telefon → Učitaj sa telefona.", "Sent. On the computer: Phone → Load from phone."));
    }
  } catch (e) { if (e.name === "AbortError") return; }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(fajl); a.download = ime; document.body.appendChild(a); a.click(); a.remove();
  poruka(t("Fajl je sačuvan u Preuzimanja (Download).", "The file is saved in Downloads."));
}
function ekranPrenos() {
  postaviVrh(t("Prenos sa računarom", "Transfer with computer"), true); meni("vise");
  const n = S.promene.length;
  ekran.innerHTML = `<div class="kart"><h2>📲 ${t("Sa računara na telefon", "From computer to phone")}</h2>
    <p class="mali">${t("Na računaru: HerdDoc → Telefon → <b>Pošalji na telefon</b>. Zatim ga otvori ovde.", "On the computer: HerdDoc → Phone → <b>Send to phone</b>. Then open it here.")}</p>
    <button class="dug glavno puno" id="uc">📂 ${t("Učitaj sa računara", "Load from computer")}</button></div>
    <div class="kart"><h2>💻 ${t("Sa telefona na računar", "From phone to computer")} ${n ? `<span class="znak warn">${n}</span>` : ""}</h2>
    ${n ? `<p class="mali">${t("Šta je urađeno na telefonu:", "Done on the phone:")}</p><div style="max-height:220px;overflow:auto;margin-bottom:12px">${S.promene.slice().reverse().map(p =>
      `<div class="ist"><div class="d">${h(p.vreme)}</div>${h(p.tekst)}</div>`).join("")}</div>` : `<p class="mali">${t("Nema novih promena na telefonu.", "No new changes on the phone.")}</p>`}
    <button class="dug ${n ? "glavno" : ""} puno" id="sl">📤 ${t("Pošalji računaru", "Send to computer")}</button>
    <p class="mali">${t("Pošalji fajl sebi (Google Drive, Viber, Gmail…). Na računaru: HerdDoc → Telefon → <b>Učitaj sa telefona</b>. Posle toga pošalji telefonu novi fajl sa računara.",
      "Send the file to yourself (Google Drive, Viber, Gmail…). On the computer: HerdDoc → Phone → <b>Load from phone</b>. Then send a fresh file from the computer to the phone.")}</p></div>
    <div class="kart"><button class="dug opasno puno" id="br">${t("Obriši sve podatke sa telefona", "Delete all data from the phone")}</button></div>`;
  $("#uc").onclick = izaberiFajl;
  $("#sl").onclick = posaljiRacunaru;
  $("#br").onclick = () => {
    if (!confirm(t("Obrisati sve podatke sa ovog telefona? (Na računaru ostaju.)", "Delete all data from this phone? (They stay on the computer.)"))) return;
    if (S.promene.length && !confirm(t(`${S.promene.length} promena nije poslato računaru i biće izgubljeno. Sigurno?`, `${S.promene.length} changes were not sent and will be lost. Sure?`))) return;
    try { localStorage.removeItem(KLJUC); } catch (e) { /* */ }
    const kraj = () => { location.hash = ""; location.reload(); };
    redCuvanja.then(() => bazaBrisi("glavno")).then(kraj, kraj);
  };
}

// ---------------------------------------------------------------- obaveštenje pri ulasku u aplikaciju
// Kad se aplikacija otvori (ili vrati iz pozadine posle 3 sata), hitne stvari iskoče odmah na ekranu.
let obavestenoU = 0;
function obavestiPriUlasku(sila) {
  if (!imaPodatke() || (!sila && (document.querySelector(".obavesti") || delovi().ekran === "danas"))) return;
  const ob = obavestenja().filter(o => o.nivo <= 1);
  obavestenoU = Date.now();
  if (!ob.length) return;
  const hitno = ob.filter(o => o.nivo === 0).length;
  const d = document.createElement("div");
  d.className = "obavesti";
  d.innerHTML = `<div class="okvir"><h2>🔔 ${ob.length === 1 ? t("1 stvar traži pažnju", "1 thing needs attention") : t(`${ob.length} stvari traže pažnju`, `${ob.length} things need attention`)}</h2>
    <p class="mali" style="margin:0 0 12px">${[hitno ? `<b style="color:var(--bad)">${t(`${hitno} hitno`, `${hitno} urgent`)}</b>` : "", ob.length - hitno ? t(`${ob.length - hitno} uskoro`, `${ob.length - hitno} soon`) : ""].filter(Boolean).join(" · ")}</p>
    ${ob.slice(0, 3).map(o => `<div class="ob"><div class="traka n${o.nivo}"></div><div class="tekst">${o.grlo ? `<b style="margin:0">${h(o.grlo)}</b>` : ""}<b>${h(o.naslov)}</b><div class="mali">${h(o.opis)}</div></div></div>`).join("")}
    ${ob.length > 3 ? `<p class="mali">${t(`… i još ${ob.length - 3}`, `… and ${ob.length - 3} more`)}</p>` : ""}
    <div class="dugmad" style="display:flex;gap:8px;margin-top:6px"><button class="dug" id="obK">${t("Kasnije", "Later")}</button>
    <button class="dug glavno" id="obP">${t("Pogledaj", "View")}</button></div></div>`;
  document.body.appendChild(d);
  const zatvori = () => d.remove();
  d.onclick = e => { if (e.target === d) zatvori(); };
  d.querySelector("#obK").onclick = zatvori;
  d.querySelector("#obP").onclick = () => { zatvori(); idi("danas"); };
  try { if (navigator.vibrate) navigator.vibrate(200); } catch (e) { /* */ }
}
// podsetnik sa tačnim vremenom: dok je aplikacija otvorena, javi se tačno u to vreme (i kad se vratiš posle tog vremena)
let _vrT = null, _vrJavljeno = new Set();
function zakaziVremenske() {
  clearTimeout(_vrT);
  const sad = new Date(), d0 = danas();
  let najblize = null;
  for (const p of S.podsetnici.filter(p => !p.gotovo && normVreme(p.vreme))) {
    const pd = parsirajDatum(p.datum);
    if (!pd || +pd !== +d0) continue;
    const [hh, mm] = normVreme(p.vreme).split(":").map(Number), kad = new Date(sad); kad.setHours(hh, mm, 2, 0);
    const k = `${p.grlo}|${p.tip}|${p.datum}|${p.vreme}`, ms = kad - sad;
    if (ms <= 0 && !_vrJavljeno.has(k)) { _vrJavljeno.add(k); document.querySelector(".obavesti")?.remove(); obavestiPriUlasku(true); }
    else if (ms > 0 && (najblize === null || ms < najblize)) najblize = ms;
  }
  if (najblize !== null) _vrT = setTimeout(zakaziVremenske, Math.min(najblize, 6 * 3600 * 1000));
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && Date.now() - obavestenoU > 3 * 3600 * 1000) obavestiPriUlasku();
  if (document.visibilityState === "visible") zakaziVremenske();
});

// ---------------------------------------------------------------- obaveštenja kad je aplikacija zatvorena
// Telefon (Android, instalirana aplikacija) povremeno sam probudi aplikaciju u pozadini (periodicSync) i pokaže
// obaveštenje iz unapred napravljenog plana – bez servera; podaci ostaju u telefonu.
const lokDatum = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
function planObavestenja() {
  const d0 = danas(), plan = [];
  for (const o of obavestenja().filter(o => o.nivo <= 1)) plan.push({ k: `${o.grlo || ""}|${o.naslov}`, n: (o.grlo ? o.grlo + " – " : "") + o.naslov, od: lokDatum(d0) });
  for (const p of S.podsetnici.filter(p => !p.gotovo && normVreme(p.vreme))) {   // tačno vreme: posebno obaveštenje tog dana
    const pd = parsirajDatum(p.datum);
    if (pd && pd >= d0) plan.push({ k: `v|${p.grlo || ""}|${p.tip}|${p.datum}|${p.vreme}`, n: `${p.grlo ? p.grlo + " – " : ""}${p.tip || t("Podsetnik", "Reminder")} (${normVreme(p.vreme)})`, od: lokDatum(pd), u: normVreme(p.vreme) });
  }
  for (const p of S.podsetnici.filter(p => !p.gotovo)) {
    const pd = parsirajDatum(p.datum);
    if (pd && pd > dodajDane(d0, danaUnapred())) plan.push({ k: `p|${p.grlo || ""}|${p.tip}|${p.datum}`, n: `${p.grlo ? p.grlo + " – " : ""}${p.tip || t("Podsetnik", "Reminder")} (${p.datum})`, od: lokDatum(dodajDane(pd, -danaUnapred())) });
  }
  for (const z of cekajuPorodjaj()) {
    const [od, oc] = granicePorodjaja(z), [majka] = roditeljiParenja(z);
    if (od && oc && od > d0) plan.push({ k: `r|${majka || ""}|${z.datum}`, n: `${majka || "?"} – ${t("porođaj se očekuje oko", "birth expected around")} ${fmtD(oc)}`, od: lokDatum(od) });
  }
  return { plan, sat: obavSat(), naslov: t("HerdDoc – podsetnik", "HerdDoc – reminder"), jos: t("… i još {0}", "… and {0} more"), napravljeno: lokDatum(d0) };
}
let _planT = null;
function planUskoro() {
  clearTimeout(_planT);
  setTimeout(zakaziVremenske, 100);
  _planT = setTimeout(() => { try { if (!bezBaze && imaPodatke()) bazaUpisi("obavestenja", planObavestenja()).catch(() => {}); } catch (e) { /* */ } }, 1500);
}
const podrzavaObavestenja = () => "Notification" in window && "serviceWorker" in navigator;
const podrzavaPozadinu = () => podrzavaObavestenja() && "ServiceWorkerRegistration" in window && "periodicSync" in ServiceWorkerRegistration.prototype;
function stanjeObavestenja() {
  if (!podrzavaObavestenja()) return ["ne", t("ovaj telefon javlja samo kad otvoriš aplikaciju", "this phone only notifies when you open the app")];
  if (Notification.permission === "denied") return ["ne", t("zabranjeno u podešavanjima telefona", "blocked in the phone settings")];
  if (Notification.permission !== "granted") return ["iskljuceno", t("dodirni da uključiš", "tap to turn on")];
  return podrzavaPozadinu() ? ["da", t("uključeno – javlja i kad je aplikacija zatvorena", "on – notifies even when the app is closed")]
    : ["da", t("uključeno – kad otvoriš aplikaciju (ovaj telefon ne budi aplikacije u pozadini)", "on – when you open the app (this phone doesn't wake apps in the background)")];
}
async function prijaviPozadinu(reg) {
  try { if (reg.periodicSync) await reg.periodicSync.register("herddoc-obavestenja", { minInterval: 6 * 3600 * 1000 }); } catch (e) { /* telefon odlučuje */ }
}
async function ukljuciObavestenja() {
  if (!podrzavaObavestenja()) return poruka(stanjeObavestenja()[1]);
  const dozvola = await Notification.requestPermission();
  if (dozvola !== "granted") { prikazi(); return poruka(t("Obaveštenja nisu dozvoljena. Uključi ih u podešavanjima telefona za HerdDoc.", "Notifications were not allowed. Turn them on in the phone settings for HerdDoc.")); }
  planUskoro();
  try {
    const reg = await navigator.serviceWorker.ready;
    await prijaviPozadinu(reg);
    await reg.showNotification("HerdDoc", { body: t("Obaveštenja su uključena. Ovako će izgledati podsetnici.", "Notifications are on. This is how reminders will look."),
      icon: "ikone/ikona-192.png", badge: "ikone/ikona-192.png", tag: "herddoc-proba" });
  } catch (e) { /* */ }
  prikazi();
}
if ("serviceWorker" in navigator) navigator.serviceWorker.addEventListener("message", e => { if (e.data && e.data.idi) idi(e.data.idi); });
if (podrzavaObavestenja() && Notification.permission === "granted") navigator.serviceWorker.ready.then(prijaviPozadinu).catch(() => {});

// ---------------------------------------------------------------- ime i prezime korisnika (obavezno)
// Svako ko radi u aplikaciji ostavi ime i prezime: vidi se kod svakog upisa i kod ocena grla.
function traziIme(menja = false) {
  if (document.querySelector(".ime-okvir")) return;
  const [ime0, ...pr0] = (S.korisnik || "").split(" ");
  const d = document.createElement("div");
  d.className = "obavesti ime-okvir";
  d.innerHTML = `<div class="okvir"><h2>👤 ${t("Ko radi u aplikaciji?", "Who is using the app?")}</h2>
    <p class="mali" style="margin:0 0 12px">${t("Upiši svoje ime i prezime. Vidi se kod svakog upisa i kod ocena grla, da se zna ko je šta uradio.", "Enter your first and last name. It is shown with every entry and every animal score, so it is clear who did what.")}</p>
    <label class="polje"><span>${t("Ime *", "First name *")}</span><input class="unos" id="kIme" autocomplete="given-name" value="${h(menja ? ime0 || "" : "")}"></label>
    <label class="polje"><span>${t("Prezime *", "Last name *")}</span><input class="unos" id="kPrezime" autocomplete="family-name" value="${h(menja ? pr0.join(" ") : "")}"></label>
    <div class="greska" id="kGr"></div>
    <div style="display:flex;gap:8px;margin-top:6px">${menja ? `<button class="dug" id="kOtk">${t("Otkaži", "Cancel")}</button>` : ""}<button class="dug glavno" id="kSac" style="flex:1">${t("Sačuvaj", "Save")}</button></div></div>`;
  document.body.appendChild(d);
  const sac = () => {
    const i = cistoIme($("#kIme").value), p = cistoIme($("#kPrezime").value);
    if (i.length < 2 || p.length < 2) return ($("#kGr").textContent = t("Upiši i ime i prezime.", "Enter both first and last name."));
    S.korisnik = `${i} ${p}`;
    sacuvaj(); d.remove();
    poruka(t(`Zdravo, ${i}!`, `Hello, ${i}!`));
    if (delovi().ekran === "vise") prikazi();
    if (!menja) setTimeout(obavestiPriUlasku, 300);
  };
  $("#kSac").onclick = sac;
  $("#kPrezime").onkeydown = e => { if (e.key === "Enter") sac(); };
  if (menja) $("#kOtk").onclick = () => d.remove();
  setTimeout(() => $("#kIme").focus(), 50);
}
const proveriIme = () => { if (imaPodatke() && !cistoIme(S.korisnik || "")) traziIme(); };

// ---------------------------------------------------------------- start
ekran.innerHTML = `<div class="prazno">${t("Učitavam…", "Loading…")}</div>`;
ucitajIzTelefona().then(() => {
  window.addEventListener("hashchange", prikazi);
  window.addEventListener("hashchange", proveriIme);
  prikazi();
  pokreniUsaglasavanje();
  proveriIme();
  setTimeout(obavestiPriUlasku, 600);
  setTimeout(() => { const sd = new Date(), hm = `${String(sd.getHours()).padStart(2, "0")}:${String(sd.getMinutes()).padStart(2, "0")}`; for (const p of S.podsetnici) if (normVreme(p.vreme) && normVreme(p.vreme) <= hm && +(parsirajDatum(p.datum) || 0) === +danas()) _vrJavljeno.add(`${p.grlo}|${p.tip}|${p.datum}|${p.vreme}`); zakaziVremenske(); }, 700);   // već prošla vremena pokriva prozor pri ulasku
  planUskoro();
});
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) navigator.serviceWorker.register("sw.js").catch(() => {});
if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
