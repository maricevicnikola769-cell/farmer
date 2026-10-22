// Farmer za telefon – ekrani. Podaci se čuvaju u telefonu (radi i bez interneta).
"use strict";
const VERZIJA_TEL = "2.4";
const t = (sr, en) => (EN() ? en : sr);
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
const stanjeZaCuvanje = () => ({ jezik: S.jezik, prag: S.prag, grav: S.grav, grla: S.grla, istorija: S.istorija,
  podsetnici: S.podsetnici, osnova: S.osnova, izvoz: S.izvoz, promene: S.promene, pocetak: S.pocetak || false,
  sinh: S.sinh || null, poslato: S.poslato || [] });
function sacuvajStaro(podaci) {
  try { localStorage.setItem(KLJUC, JSON.stringify(podaci)); return true; }
  catch (e) { poruka(t("Podaci nisu sačuvani u telefonu: ", "Data was not saved on the phone: ") + e.message); return false; }
}
function sacuvaj() {
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
  document.title = naslov === "Farmer" ? "Farmer" : `${naslov} – Farmer`;
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
    vise: ekranVise, prenos: ekranPrenos, sinh: ekranSinh, novo: ekranNovoGrlo, rodjenje: ekranRodjenje, mindjuse: ekranMindjuse, podsetnik: ekranPodsetnik };
  (ekrani[e] || ekranGrla)(arg, upit);
}

// ---------------------------------------------------------------- delovi ekrana
function cip(id, link = true) {
  const a = M.A[id], siv = !a || a.osnivac;
  return link && !siv ? `<a class="cip" href="#karton/${encodeURIComponent(id)}">${h(id)}</a>` : `<span class="cip ${siv ? "siv" : ""}">${h(id || "?")}</span>`;
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

// ---------------------------------------------------------------- dobrodošlica
function dobrodoslica() {
  postaviVrh("Farmer", false); meni("");
  ekran.innerHTML = `<div class="dobrodoslica"><img src="ikone/ikona-192.png" alt=""><h2>Farmer</h2>
    <p class="mali">${t("Rodoslov stada, srodstvo i parenje – u štali, i bez interneta.", "Herd pedigree, relationship and mating – in the barn, even offline.")}</p></div>
    <div class="kart"><h2>${t("Kako počinješ", "How to start")}</h2><ol class="koraci">
      <li>${t("U programu Farmer na računaru otvori <b>Telefon</b> i klikni <b>Pošalji na telefon</b>.", "In Farmer on the computer open <b>Phone</b> and click <b>Send to phone</b>.")}</li>
      <li>${t("Fajl prebaci na telefon (Google Drive, Viber, kabl…).", "Move the file to the phone (Google Drive, Viber, cable…).")}</li>
      <li>${t("Ovde klikni <b>Učitaj sa računara</b> i izaberi taj fajl.", "Here, tap <b>Load from computer</b> and choose that file.")}</li></ol></div>
    ${oblakPodesen() ? `<a class="dug glavno puno" href="#sinh">📱 ${t("Upari sa računarom (QR kod)", "Pair with computer (QR code)")}</a><div style="height:10px"></div>` : ""}
    <button class="dug ${oblakPodesen() ? "" : "glavno"} puno" id="ucitaj">📂 ${t("Učitaj sa računara (fajl)", "Load from computer (file)")}</button>
    <div style="height:10px"></div>
    <div class="dugmad"><button class="dug" id="pocni">${t("Počni bez računara", "Start without computer")}</button>
      <button class="dug" id="jezik">🌐 ${S.jezik === "en" ? "Srpski" : "English"}</button></div>`;
  $("#ucitaj").onclick = izaberiFajl;
  $("#pocni").onclick = () => { S.pocetak = true; sacuvaj(); idi("grla"); prikazi(); };
  $("#jezik").onclick = () => { S.jezik = S.jezik === "en" ? "sr" : "en"; sacuvaj(); dobrodoslica(); };
}

// ---------------------------------------------------------------- Grla
const filt = { q: "", pol: "", van: false };
function ekranGrla() {
  postaviVrh("Farmer", false); meni("grla");
  const sva = M.grla(false);
  ekran.innerHTML = `<div class="sakam"><input class="pretraga" id="q" type="search" placeholder="🔍 ${t("Traži oznaku, markicu, rasu…", "Search tag, ear tag, breed…")}" value="${h(filt.q)}"><button type="button" class="kam" id="skenGrla" aria-label="${t("Skeniraj minđušu", "Scan ear tag")}">📷</button></div>
    <div class="filteri">${[["", t("Sva", "All")], ["z", t("Ženska", "Females")], ["m", t("Muška", "Males")]].map(([k, n]) =>
      `<button data-pol="${k}" class="${filt.pol === k ? "akt" : ""}">${n}</button>`).join("")}
      <button id="van" class="${filt.van ? "akt" : ""}">${t("i van zapata", "incl. out of herd")}</button>
      <button id="novo">＋ ${t("Novo grlo", "New animal")}</button></div><div id="sp"></div>`;
  const crtaj = (koliko = NA_STRANI) => {
    const q = norm(filt.q), ql = filt.q.trim().toLowerCase();
    const sp = sva.filter(a => (filt.van || a.aktivno) && (!filt.pol || a.pol === filt.pol) &&
      (!q || norm(a.id).includes(q) || norm(a.markica).includes(q) || a.stare.some(s => norm(s).includes(q)) || (ql && (a.rasa || "").includes(ql))));
    $("#sp").innerHTML = `<div class="mali" style="margin:0 4px 8px">${t(`${sp.length} grla`, `${sp.length} animals`)}</div>` +
      listaGrla(sp, sva.length ? t("Nema grla za ovu pretragu.", "No animals match.") : t("Stado je još prazno. Učitaj podatke sa računara ili dodaj grlo.", "The herd is empty. Load data from the computer or add an animal."), koliko);
    const jos = $("#sp [data-jos]");
    if (jos) jos.onclick = () => crtaj(+jos.dataset.jos);
  };
  $("#q").oninput = e => { filt.q = e.target.value; crtaj(); };
  ekran.querySelectorAll("[data-pol]").forEach(b => b.onclick = () => { filt.pol = b.dataset.pol; ekranGrla(); });
  $("#van").onclick = () => { filt.van = !filt.van; ekranGrla(); };
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
      <div><b>${h(M.polNaziv(id))}</b><div class="mali">${h([a.vrsta, a.rasa].filter(Boolean).join(" · "))}</div></div></div>
    <dl class="polja">
      ${a.markica ? `<dt>${t("Markica", "Ear tag")}</dt><dd>${h(a.markica)}</dd>` : ""}
      <dt>${t("Rođen", "Born")}</dt><dd>${a.datum ? `${fmtD(a.datum)} (${h(fmtStarost(starostMeseci(a.datum)))})` : "–"}</dd>
      ${a.stado ? `<dt>${t("Stado", "Herd")}</dt><dd>${h(a.stado)}</dd>` : ""}
      ${a.poreklo ? `<dt>${t("Poreklo", "Origin")}</dt><dd>${h(a.poreklo + (a.poreklo_od ? " – " + a.poreklo_od : ""))}</dd>` : ""}
      <dt>${t("Inbriding", "Inbreeding")}</dt><dd><span class="znak ${f ? fkl : "ok"}">${pct(f)}</span> <span class="mali">${f ? h(ftekst) : ""}</span></dd>
      <dt>Status</dt><dd>${a.aktivno ? t("u zapatu", "in herd") : `<span class="znak siv">${t("van zapata", "out of herd")}</span>`}</dd>
    </dl>
    ${kar ? `<div class="info bad" style="margin:12px 0 0">⚠ ${t("Karenca", "Withdrawal")}: ${h(kar)}</div>` : ""}
    ${posl.map(z => `<div class="info siv" style="margin:12px 0 0">${t("Parenje", "Mating")} ${h(z.datum)} · ${h(opisIshoda(z))}</div>`).join("")}
  </div>
  <div class="dugmad" style="margin-bottom:12px">
    <a class="dug glavno" href="#dogadjaj?grlo=${encodeURIComponent(id)}">＋ ${t("Upiši događaj", "Record event")}</a>
    ${a.pol ? `<a class="dug" href="#parenje/${encodeURIComponent(id)}">⚭ ${t("Partneri", "Partners")}</a>` : ""}
    <a class="dug" href="#srodstvo?a=${encodeURIComponent(id)}">${t("Srodstvo", "Relationship")}</a></div>
  ${ob.length ? `<div id="ob">${ob.map(kartObavestenja).join("")}</div>` : ""}
  <div class="kart"><h2>${t("Roditelji", "Parents")}</h2><div class="cipovi">${o ? cip(o) : `<span class="mali">${t("otac nepoznat", "sire unknown")}</span>`} ${m ? cip(m) : `<span class="mali">${t("majka nepoznata", "dam unknown")}</span>`}</div>
    ${preci2.some(Boolean) ? `<h2 style="margin-top:14px">${t("Babe i dede", "Grandparents")}</h2><div class="cipovi">${preci2.map(p => (p ? cip(p) : `<span class="cip siv">?</span>`)).join("")}</div>` : ""}
  </div>
  <div class="kart"><h2>${t("Potomci", "Offspring")} <small>(${deca.length})</small></h2>${deca.length ? `<div class="cipovi">${deca.map(d => cip(d)).join("")}</div>` : `<span class="mali">${t("nema upisanih", "none recorded")}</span>`}</div>
  <div class="kart"><h2>${t("Istorija", "History")} <small>(${ist.length})</small></h2>${ist.length ? ist.slice(0, 60).map(z =>
    `<div class="ist ${z.automatski ? "auto" : ""}"><div class="d">${h(z.datum)}${z.partner ? " · " + cip(z.partner) : ""}${z.upisao ? ` · 📱 ${h(z.upisao)}` : ""}</div><b>${h(z.dogadjaj)}</b>${z.vrednost ? ` – ${h(z.vrednost)}` : ""}
      ${z.opis ? `<div class="mali">${h(z.opis)}</div>` : ""}${opisIshoda(z) ? `<div class="mali">${h(opisIshoda(z))}</div>` : ""}</div>`).join("") : `<span class="mali">${t("još nema zapisa", "no records yet")}</span>`}</div>`;
  if (ob.length) vezAkcije($("#ob"), ob);
}

// ---------------------------------------------------------------- Danas (obaveštenja)
let danasLim = 50;                                  // veliko stado: obaveštenja se prikazuju u delovima
function ekranDanas() {
  postaviVrh(t("Danas", "Today"), false); meni("danas");
  const ob = obavestenja();
  ekran.innerHTML = (ob.length ? ob.slice(0, danasLim).map(kartObavestenja).join("") : `<div class="prazno">✓ ${t("Nema obaveštenja. Sve je u redu.", "No notifications. All good.")}</div>`) +
    (ob.length > danasLim ? `<button class="dug puno" id="josOb">${t("Prikaži još", "Show more")} (${ob.length - danasLim})</button><div style="height:10px"></div>` : "") +
    `<a class="dug puno" href="#podsetnik">＋ ${t("Novi podsetnik", "New reminder")}</a>`;
  vezAkcije(ekran, ob);
  const jos = document.getElementById("josOb");
  if (jos) jos.onclick = () => { const y = window.scrollY; danasLim += 100; ekranDanas(); window.scrollTo(0, y); };
}

// ---------------------------------------------------------------- Upis događaja
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
    <label class="provera skriveno" id="dVan"><input type="checkbox" id="van" checked> ${t("Označi grlo kao van zapata", "Mark the animal as out of herd")}</label>
    <div class="greska" id="gr"></div>
    <button class="dug glavno puno" id="sac">${t("Sačuvaj", "Save")}</button></div>
    ${!st.dogadjaj ? `<div class="dugmad"><a class="dug" href="#novo">＋ ${t("Novo grlo", "New animal")}</a></div>` : ""}`;
  const prilagodi = () => {
    const d = st.dogadjaj, g = M.nadji($("#grlo").value), leci = [k.LECENJE, k.VAKCINA].includes(d);
    $("#dPar").classList.toggle("skriveno", leci);
    $("#dKar").classList.toggle("skriveno", !leci);
    $("#dVan").classList.toggle("skriveno", ![k.PRODAJA, k.UGINUCE].includes(d));
    $("#lVr").textContent = nazivVr[d] || t("Vrednost", "Value");
    const dl = $("#dl-par");
    if (g && !leci && dl.dataset.za !== g) {        // predlozi partnera: računa se jednom po grlu, najviše 300 (ostale možeš da upišeš)
      const a = M.A[g];
      dl.dataset.za = g;
      dl.innerHTML = M.grla(true).filter(b => b.vrsta === a.vrsta && b.pol && b.pol !== a.pol).slice(0, 300)
        .map(b => `<option value="${h(b.id)}">F ${pct(M.kinship(g, b.id))}</option>`).join("");
    }
    const p = M.nadji($("#partner").value);
    if (d === k.PARENJE && g && p && g !== p) {
      const f = M.kinship(g, p), [tx, kl] = procena(f, S.prag);
      $("#inbr").innerHTML = `<div class="info ${kl}">${t(`Očekivani inbriding potomka: <b>${pct(f)}</b> (${h(tx)}), zajednički geni ${pct(M.r(g, p))}.`, `Expected inbreeding of offspring: <b>${pct(f)}</b> (${h(tx)}), shared genes ${pct(M.r(g, p))}.`)}</div>`;
    } else $("#inbr").innerHTML = "";
  };
  $("#tipovi").onclick = e => { const b = e.target.closest("button"); if (!b) return; st.dogadjaj = b.dataset.d; $("#tipovi").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x === b)); prilagodi(); };
  ["grlo", "partner"].forEach(i => $("#" + i).addEventListener("input", prilagodi));
  prilagodi();
  $("#sac").onclick = () => {
    const g = M.nadji($("#grlo").value), gr = $("#gr");
    if (!g || M.A[g].osnivac) return (gr.textContent = t("Izaberi grlo sa spiska (oznaka ili markica).", "Choose an animal from the list (tag or ear tag)."));
    const d = parsirajDatum($("#datum").value);
    if (!d) return (gr.textContent = t("Datum nije ispravan.", "The date is not valid."));
    if (!st.dogadjaj) return (gr.textContent = t("Izaberi događaj.", "Choose an event."));
    const broj = v => { const x = String(v || "").replace(/\D/g, ""); return x && +x > 0 ? x : ""; };
    upisiDogadjaj({ grlo: g, datum: fmtD(d), dogadjaj: st.dogadjaj, partner: $("#partner").value, vrednost: $("#vrednost").value.trim(),
      opis: $("#opis").value.trim(), karenca_meso: broj($("#km").value), karenca_mleko: broj($("#kml").value), vanZapata: $("#van").checked });
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
  postaviVrh(t("Novo grlo", "New animal"), true); meni("grla");
  const k = K(), sva = M.grla(), posl = sva[0] || {};
  const cesto = l => { const c = {}; l.forEach(x => { if (x) c[x] = (c[x] || 0) + 1; }); return Object.keys(c).sort((a, b) => c[b] - c[a])[0] || ""; };
  const stada = [...new Set(sva.map(a => a.stado).filter(Boolean))], rase = [...new Set(sva.map(a => a.rasa).filter(Boolean))];
  let pol = "";
  ekran.innerHTML = `<div class="kart">
    <div class="dve"><label class="polje"><span>${t("Oznaka *", "Tag *")}</span><input class="unos" id="id"></label>
      <label class="polje"><span>${t("Markica", "Ear tag")}</span>${saKamerom(`<input class="unos" id="mk" value="${h(upit ? upit.get("mk") || "" : "")}">`, "markica")}</label></div>
    <div class="polje"><span class="mali" style="font-weight:700">${t("Pol *", "Sex *")}</span><div class="izbor" id="pol" style="margin-top:6px"><button data-p="z">${t("Žensko", "Female")}</button><button data-p="m">${t("Muško", "Male")}</button></div></div>
    <div style="height:12px"></div>
    <div class="dve"><label class="polje"><span>${t("Vrsta", "Species")}</span><select class="unos" id="vrsta">${k.VRSTE.map(v => `<option ${v === (posl.vrsta || k.VRSTE[0]) ? "selected" : ""}>${h(v)}</option>`).join("")}</select></label>
      <label class="polje"><span>${t("Rasa", "Breed")}</span><input class="unos" id="rasa" list="dl-r"></label></div>
    <datalist id="dl-r">${rase.map(r => `<option value="${h(r)}">`).join("")}</datalist>
    <label class="polje"><span>${t("Datum rođenja", "Date of birth")}</span><input class="unos" id="dat" type="date"></label>
    <div class="dve"><label class="polje"><span>${t("Otac", "Sire")}</span><input class="unos" id="otac" list="dl-o" autocomplete="off"></label>
      <label class="polje"><span>${t("Majka", "Dam")}</span><input class="unos" id="majka" list="dl-m" autocomplete="off"></label></div>
    ${datalistGrla("dl-o", sva.filter(a => a.pol === "m"))}${datalistGrla("dl-m", sva.filter(a => a.pol === "z"))}
    <div class="dve"><label class="polje"><span>${t("Stado", "Herd")}</span><input class="unos" id="stado" list="dl-s" value="${h(cesto(sva.map(a => a.stado)))}"></label>
      <label class="polje"><span>${t("Poreklo", "Origin")}</span><select class="unos" id="por"><option></option>${k.POREKLA.map(p => `<option>${h(p)}</option>`).join("")}</select></label></div>
    <datalist id="dl-s">${stada.map(s => `<option value="${h(s)}">`).join("")}</datalist>
    <label class="polje"><span>${t("Poreklo od (kupljeno od…)", "Origin from (bought from…)")}</span><input class="unos" id="pod"></label>
    <div class="greska" id="gr"></div>
    <button class="dug glavno puno" id="sac">${t("Sačuvaj grlo", "Save animal")}</button></div>`;
  $("#pol").onclick = e => { const b = e.target.closest("button"); if (!b) return; pol = b.dataset.p; $("#pol").querySelectorAll("button").forEach(x => x.classList.toggle("akt", x === b)); };
  $("#sac").onclick = () => {
    const dat = $("#dat").value ? fmtD(parsirajDatum($("#dat").value)) : "";
    const gr = novoGrlo({ id: $("#id").value, markica: $("#mk").value, pol, vrsta: $("#vrsta").value, rasa: $("#rasa").value, datum_rodjenja: dat,
      otac: $("#otac").value, majka: $("#majka").value, stado: $("#stado").value, poreklo: $("#por").value, poreklo_od: $("#pod").value });
    if (gr) return ($("#gr").textContent = gr);
    const id = $("#id").value.trim();
    promena(t(`Sačuvano: ${id}`, `Saved: ${id}`));
    idi(`karton/${encodeURIComponent(id)}`);
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
    <label class="polje"><span>${t("Grlo B", "Animal B")}</span><input class="unos" id="b" list="dl" autocomplete="off"></label></div>${datalistGrla("dl", sva)}<div id="rez"></div></div>`;
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
  ekran.innerHTML = `<div class="kart"><label class="polje"><span>${t("Grlo (može i prazno)", "Animal (can be empty)")}</span><input class="unos" id="g" list="dl" autocomplete="off"></label>${datalistGrla("dl", M.grla(true))}
    <label class="polje"><span>${t("Datum *", "Date *")}</span><input class="unos" id="d" type="date" value="${uIso(dodajDane(danas(), 7))}"></label>
    <label class="polje"><span>${t("Vrsta *", "Type *")}</span><input class="unos" id="tip" list="dl-t" value="${h(k.VAKCINA)}"></label>
    <datalist id="dl-t">${k.DOGADJAJI.map(d => `<option value="${h(d)}">`).join("")}</datalist>
    <label class="polje"><span>${t("Tekst", "Text")}</span><input class="unos" id="tx"></label>
    <label class="polje"><span>${t("Ponavlja se na (dana, prazno = ne)", "Repeat every (days, empty = no)")}</span><input class="unos" id="pon" inputmode="numeric"></label>
    <div class="greska" id="gr"></div><button class="dug glavno puno" id="sac">${t("Sačuvaj", "Save")}</button></div>`;
  $("#sac").onclick = () => {
    const g = $("#g").value.trim() ? M.nadji($("#g").value) : "", d = parsirajDatum($("#d").value), tip = $("#tip").value.trim();
    if ($("#g").value.trim() && !g) return ($("#gr").textContent = t("Grlo nije pronađeno.", "Animal not found."));
    if (!d || !tip) return ($("#gr").textContent = t("Upiši datum i vrstu.", "Enter date and type."));
    noviPodsetnik(g, fmtD(d), tip, $("#tx").value.trim(), parseInt($("#pon").value, 10) || 0);
    promena(t("Podsetnik je sačuvan.", "Reminder saved.")); idi("danas");
  };
}

// ---------------------------------------------------------------- Više
function ekranVise() {
  postaviVrh(t("Više", "More"), false); meni("vise");
  const n = S.promene.length;
  ekran.innerHTML = `<div class="lista">
    ${oblakPodesen() ? `<a class="red" href="#sinh"><span style="font-size:24px">☁</span><div class="sred"><b>${S.sinh ? t("Povezano sa računarom", "Connected to computer") : t("Upari sa računarom (QR kod)", "Pair with computer (QR code)")}</b><span>${h(S.sinh ? (sinhStanje.tekst || S.sinh.naziv || "") : t("jednom skeniraš i sve se samo usklađuje", "scan once and everything syncs"))}</span></div></a>` : ""}
    <a class="red" href="#prenos"><span style="font-size:24px">⇅</span><div class="sred"><b>${t("Prenos sa računarom", "Transfer with computer")}</b><span>${n ? t(`${n} promena čeka slanje računaru`, `${n} changes waiting to be sent`) : t("sve je poslato", "everything sent")}</span></div>${n ? `<span class="znak warn">${n}</span>` : ""}</a>
    <a class="red" href="#srodstvo"><span style="font-size:24px">⚯</span><div class="sred"><b>${t("Srodstvo dva grla", "Relationship of two animals")}</b><span>${t("koliko su srodni, zajednički preci", "how related they are, common ancestors")}</span></div></a>
    <a class="red" href="#novo"><span style="font-size:24px">＋</span><div class="sred"><b>${t("Novo grlo", "New animal")}</b><span>${t("kupljeno ili rođeno", "bought or born")}</span></div></a>
    <a class="red" href="#podsetnik"><span style="font-size:24px">⏰</span><div class="sred"><b>${t("Novi podsetnik", "New reminder")}</b><span>${t("vakcinacija, lečenje…", "vaccination, treatment…")}</span></div></a>
    <a class="red" href="#" id="problem"><span style="font-size:24px">⚠</span><div class="sred"><b>${t("Prijavi problem", "Report a problem")}</b><span>${t("pošalji izveštaj o greškama (bez podataka o grlima)", "send an error report (no animal data)")}</span></div></a>
    </div>
    <div class="kart mali">Farmer ${t("za telefon", "for phone")} ${VERZIJA_TEL} · ${t("jezik podataka", "data language")}: ${S.jezik === "en" ? "English" : "srpski"}<br>
    ${S.izvoz ? t(`Podaci sa računara od ${h(S.izvoz.datum || "")}`, `Data from computer of ${h(S.izvoz.datum || "")}`) : t("Podaci su upisani samo na telefonu.", "Data entered on the phone only.")}<br>
    ${t("Jezik se menja na računaru – telefon preuzima jezik iz fajla.", "Language is changed on the computer – the phone uses the file's language.")}</div>`;
  $("#problem").onclick = ev => { ev.preventDefault(); prijaviProblem(); };
}

async function prijaviProblem() {
  let greske = [];
  try { greske = JSON.parse(localStorage.getItem("farmer-greske") || "[]"); } catch (e) { /* */ }
  const tekst = [`Farmer ${t("za telefon", "for phone")} ${VERZIJA_TEL} – ${t("izveštaj o problemu", "problem report")}`, navigator.userAgent,
    `${t("Grla", "Animals")}: ${S.grla.length} · ${t("istorija", "history")}: ${S.istorija.length} · ${t("čeka slanje", "waiting")}: ${S.promene.length}`,
    `${t("Upareno", "Paired")}: ${!!S.sinh}${S.sinh ? " · " + (S.sinh.iskljucen ? t("isključen", "disconnected") : sinhStanje.tekst) : ""}`, "",
    t("--- poslednje greške ---", "--- last errors ---")].concat(greske.length ? greske.map(g => `${g.v} [${g.g}] ${g.p}`) : [t("(nema zapisanih grešaka)", "(no recorded errors)")]).join("\n");
  try {
    if (navigator.share) { await navigator.share({ title: "Farmer – " + t("izveštaj o problemu", "problem report"), text: tekst }); return; }
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
      await navigator.share({ files: [fajl], title: "Farmer", text: t("Podaci sa telefona za Farmer na računaru", "Phone data for Farmer on the computer") });
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
    <p class="mali">${t("Na računaru: Farmer → Telefon → <b>Pošalji na telefon</b>. Zatim ga otvori ovde.", "On the computer: Farmer → Phone → <b>Send to phone</b>. Then open it here.")}</p>
    <button class="dug glavno puno" id="uc">📂 ${t("Učitaj sa računara", "Load from computer")}</button></div>
    <div class="kart"><h2>💻 ${t("Sa telefona na računar", "From phone to computer")} ${n ? `<span class="znak warn">${n}</span>` : ""}</h2>
    ${n ? `<p class="mali">${t("Šta je urađeno na telefonu:", "Done on the phone:")}</p><div style="max-height:220px;overflow:auto;margin-bottom:12px">${S.promene.slice().reverse().map(p =>
      `<div class="ist"><div class="d">${h(p.vreme)}</div>${h(p.tekst)}</div>`).join("")}</div>` : `<p class="mali">${t("Nema novih promena na telefonu.", "No new changes on the phone.")}</p>`}
    <button class="dug ${n ? "glavno" : ""} puno" id="sl">📤 ${t("Pošalji računaru", "Send to computer")}</button>
    <p class="mali">${t("Pošalji fajl sebi (Google Drive, Viber, Gmail…). Na računaru: Farmer → Telefon → <b>Učitaj sa telefona</b>. Posle toga pošalji telefonu novi fajl sa računara.",
      "Send the file to yourself (Google Drive, Viber, Gmail…). On the computer: Farmer → Phone → <b>Load from phone</b>. Then send a fresh file from the computer to the phone.")}</p></div>
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

// ---------------------------------------------------------------- start
ekran.innerHTML = `<div class="prazno">${t("Učitavam…", "Loading…")}</div>`;
ucitajIzTelefona().then(() => {
  window.addEventListener("hashchange", prikazi);
  prikazi();
  pokreniUsaglasavanje();
});
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) navigator.serviceWorker.register("sw.js").catch(() => {});
if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
