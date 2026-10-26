// HerdDoc za telefon – skeniranje minđuše (bar kod / QR kod) kamerom telefona.
// Kamera se uključuje samo dok je skener otvoren. Čitač: ugrađeni u Chrome ili sopstveni (ZXing) – radi na svakom telefonu.
"use strict";
const SKENER_FORMATI = ["qr_code", "code_128", "code_39", "code_93", "ean_13", "ean_8", "upc_a", "upc_e", "itf", "codabar", "data_matrix", "pdf417", "aztec"];

// skeniraj(naslov) -> Promise<string|null>  (null = otkazano)
// Kamera samo prikazuje sliku; kod se čita tek kad se pritisne „Skeniraj“ (da se slučajno ne pročita pogrešan kod).
// Kamera: prvo zadnja; ako za 2,5 s ne da sliku (telefoni sa više sočiva), sama proba sledeću. Dugme "Druga kamera" menja ručno.
function skeniraj(naslov) {
  return new Promise(resolve => {
    const ov = document.createElement("div");
    ov.className = "skener";
    ov.innerHTML = `<video autoplay playsinline muted></video><div class="okvir"></div>
      <div class="skener-vrh"><b>${h(naslov || t("Skeniraj minđušu", "Scan the ear tag"))}</b><span>${t("Pokrećem kameru…", "Starting the camera…")}</span></div>
      <div class="skener-info"></div>
      <div class="skener-dno"><button class="dug glavno okidac" data-s="skeniraj" disabled>📷 ${t("Skeniraj", "Scan")}</button>
        <button class="dug skriveno" data-s="lampa">🔦</button><button class="dug skriveno" data-s="druga">🔄 ${t("Druga kamera", "Other camera")}</button>
        <button class="dug" data-s="rucno">⌨ ${t("Ručno", "Type")}</button><button class="dug" data-s="otkazi">${t("Otkaži", "Cancel")}</button></div>`;
    document.body.appendChild(ov);
    const video = ov.querySelector("video"), natpis = ov.querySelector(".skener-vrh span"), info = ov.querySelector(".skener-info");
    video.muted = true; video.playsInline = true; video.setAttribute("playsinline", ""); video.setAttribute("webkit-playsinline", "");
    let tok = null, gotovo = false, lampa = false, citac = null, kamere = [], trenutna = -1, pokusaj = 0;
    const ugasi = () => { if (tok) tok.getTracks().forEach(x => x.stop()); tok = null; };
    const kraj = vrednost => {
      if (gotovo) return;
      gotovo = true;
      ugasi();
      ov.remove();
      resolve(vrednost);
    };
    ov.querySelector('[data-s="otkazi"]').onclick = () => kraj(null);
    ov.querySelector('[data-s="rucno"]').onclick = () => {
      const v = prompt(t("Broj minđuše:", "Ear tag number:"));
      if (v && v.trim()) kraj(v.trim());
    };
    const greska = tekst => { natpis.textContent = tekst; ov.querySelector(".okvir").classList.add("skriveno"); };
    if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      greska(t("Ovaj pregledač ne dozvoljava kameru. Otvori HerdDoc u Chrome-u (adresa mora počinjati sa https://), ili upiši broj ručno.",
        "This browser does not allow the camera. Open HerdDoc in Chrome (the address must start with https://), or type the number."));
      return;
    }
    // čeka da kamera stvarno da sliku (širina > 0 i vreme videa ide napred)
    const imaSliku = ms => new Promise(res => {
      const kraj_ = Date.now() + ms;
      const proveri = () => {
        if (gotovo) return res(false);
        if (video.videoWidth > 0 && video.currentTime > 0.2) return res(true);
        if (Date.now() > kraj_) return res(false);
        setTimeout(proveri, 100);
      };
      proveri();
    });
    const pokreni = async uslovi => {
      ugasi();
      const ostro = { width: { ideal: 1920 }, height: { ideal: 1080 } };   // veća slika = sitan QR kod (npr. sa ekrana računara) se čita
      const t_ = await navigator.mediaDevices.getUserMedia({ video: uslovi === true ? ostro : Object.assign({}, ostro, uslovi), audio: false });
      if (gotovo) { t_.getTracks().forEach(x => x.stop()); return false; }
      tok = t_;
      video.srcObject = tok;
      const pl = video.play();                           // ne čekamo: crna kamera nikad ne krene
      if (pl && pl.catch) pl.catch(() => {});
      const traka = tok.getVideoTracks()[0], pod = traka.getSettings ? traka.getSettings() : {};
      try { traka.applyConstraints({ advanced: [{ focusMode: "continuous" }] }).catch(() => {}); } catch (e) { /* telefon ne podržava */ }
      const ok = await imaSliku(2500);
      info.textContent = `${traka.label || t("kamera", "camera")} · ${video.videoWidth}×${video.videoHeight}${ok ? "" : " · " + t("nema slike", "no picture")}`;
      const lb = ov.querySelector('[data-s="lampa"]');
      lb.classList.add("skriveno");
      try {
        if (traka.getCapabilities && traka.getCapabilities().torch) {
          lb.classList.remove("skriveno");
          lb.onclick = () => { lampa = !lampa; traka.applyConstraints({ advanced: [{ torch: lampa }] }).catch(() => {}); };
        }
      } catch (e) { /* */ }
      if (pod.deviceId) trenutna = Math.max(trenutna, kamere.findIndex(k => k.deviceId === pod.deviceId));
      const radiId = (uslovi && uslovi.deviceId && uslovi.deviceId.exact) || pod.deviceId;
      if (ok && radiId) { try { localStorage.setItem("farmer-kamera", radiId); } catch (e) { /* */ } }
      return ok;
    };
    const ucitajKamere = async () => {
      try {
        const sve = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === "videoinput");
        const zadnja = d => /back|rear|environment|zadnj|stražnj|0, facing back/i.test(d.label || "");
        const broj = d => { const m = (d.label || "").match(/\d+/); return m ? +m[0] : 99; };   // "camera 0" je obično glavna
        const zap = (() => { try { return localStorage.getItem("farmer-kamera") || ""; } catch (e) { return ""; } })();
        kamere = sve.filter(zadnja).sort((a, b) => broj(a) - broj(b)).concat(sve.filter(d => !zadnja(d)))
          .sort((a, b) => (b.deviceId === zap) - (a.deviceId === zap));                      // zapamćena prva
      } catch (e) { kamere = []; }
      ov.querySelector('[data-s="druga"]').classList.toggle("skriveno", kamere.length < 2);
    };
    const sledeca = async () => {           // probaj kamere redom dok neka ne da sliku
      for (let n = 0; n < kamere.length && !gotovo; n++) {
        trenutna = (trenutna + 1) % kamere.length;
        natpis.textContent = t(`Probam kameru ${trenutna + 1} od ${kamere.length}…`, `Trying camera ${trenutna + 1} of ${kamere.length}…`);
        try { if (await pokreni({ deviceId: { exact: kamere[trenutna].deviceId } })) return true; } catch (e) { /* sledeća */ }
      }
      return false;
    };
    ov.querySelector('[data-s="druga"]').onclick = async () => {
      if (await sledeca()) natpis.textContent = t("Uperi kameru u bar kod ili QR kod na minđuši", "Point the camera at the barcode or QR code on the ear tag");
    };
    (async () => {
      try {
        citac = await napraviCitac();
      } catch (e) {
        return greska(t("Čitač kodova ne može da se učita. Otvori aplikaciju jednom sa internetom, ili upiši broj ručno.",
          "The code reader cannot be loaded. Open the app once with internet, or type the number."));
      }
      let ok = false;
      try {
        let zap = "";
        try { zap = localStorage.getItem("farmer-kamera") || ""; } catch (e) { /* */ }
        ok = await pokreni(zap ? { deviceId: { ideal: zap }, facingMode: { ideal: "environment" } } : { facingMode: { ideal: "environment" } });
      } catch (e) {
        if (e.name === "NotAllowedError" || e.name === "SecurityError")
          return greska(t("Kamera nije dozvoljena. U Chrome-u klikni ikonicu levo od adrese (ili ⋮ → Podešavanja → Podešavanja sajta → Kamera) i dozvoli kameru za HerdDoc.",
            "Camera is not allowed. In Chrome tap the icon left of the address (or ⋮ → Settings → Site settings → Camera) and allow the camera for HerdDoc."));
        if (e.name === "NotReadableError" || e.name === "AbortError")
          return greska(t("Kameru trenutno koristi druga aplikacija (Viber, kamera…). Zatvori je pa probaj ponovo.", "Another app is using the camera (Viber, camera…). Close it and try again."));
        if (e.name === "NotFoundError" || e.name === "OverconstrainedError") ok = false;
        else return greska(t("Kamera ne može da se uključi: ", "The camera cannot start: ") + e.message);
      }
      if (gotovo) return;
      await ucitajKamere();
      if (!ok) ok = await sledeca();
      if (gotovo) return;
      if (!ok) {
        try { ok = await pokreni(true); } catch (e) { /* */ }
      }
      if (!ok) return greska(t("Kamera se uključila, ali ne daje sliku. Zatvori druge aplikacije koje koriste kameru i probaj ponovo, ili upiši broj ručno.",
        "The camera started but gives no picture. Close other apps that use the camera and try again, or type the number."));
      const uputstvo = t("Uperi kameru u kod, pa pritisni „Skeniraj“", "Point the camera at the code, then press „Scan“");
      natpis.textContent = uputstvo;
      const okidac = ov.querySelector('[data-s="skeniraj"]');
      okidac.disabled = false;
      let doKada = 0;
      const trazi = async () => {                        // čita samo ~3 s posle pritiska na dugme
        if (gotovo) return;
        if (Date.now() > doKada) {
          okidac.disabled = false;
          okidac.textContent = "📷 " + t("Skeniraj", "Scan");
          natpis.textContent = t("Kod nije pročitan – približi ili udalji telefon i pritisni ponovo", "Code not read – move the phone closer or further and press again");
          return;
        }
        try {
          if (video.readyState >= 2 && video.videoWidth) {
            const kod = await citac(video);
            if (kod) { if (navigator.vibrate) navigator.vibrate(80); return kraj(kod); }
          }
        } catch (e) { /* sledeći pokušaj */ }
        setTimeout(trazi, 80);
      };
      okidac.onclick = () => {
        if (doKada > Date.now()) return;
        doKada = Date.now() + 3000;
        okidac.disabled = true;
        okidac.textContent = "⏳ " + t("Čitam kod…", "Reading code…");
        natpis.textContent = uputstvo;
        trazi();
      };
    })();
  });
}

// Čitač: ugrađeni u Chrome (BarcodeDetector) ako ga telefon ima; inače sopstveni (ZXing, radi na svakom telefonu).
let _zxing = null;
function ucitajZxing() {
  if (window.ZXing) return Promise.resolve(window.ZXing);
  if (!_zxing) _zxing = new Promise((res, rej) => {
    const sc = document.createElement("script");
    sc.src = "zxing.min.js";
    sc.onload = () => (window.ZXing ? res(window.ZXing) : rej(new Error("ZXing")));
    sc.onerror = () => { _zxing = null; rej(new Error("ZXing")); };
    document.head.appendChild(sc);
  });
  return _zxing;
}
async function napraviCitac() {
  if ("BarcodeDetector" in window && !window.__samoZxing) {
    try {
      const podrzani = await BarcodeDetector.getSupportedFormats();
      const f = SKENER_FORMATI.filter(x => podrzani.includes(x));
      if (f.length) {
        const d = new BarcodeDetector({ formats: f });
        await d.detect(document.createElement("canvas"));          // proba: neki telefoni ga imaju, a ne rade
        return async video => (await d.detect(video)).map(k => (k.rawValue || "").trim()).find(Boolean) || null;
      }
    } catch (e) { /* prelazi na ZXing */ }
  }
  const Z = await ucitajZxing(), F = Z.BarcodeFormat, hint = new Map();
  hint.set(Z.DecodeHintType.POSSIBLE_FORMATS, [F.QR_CODE, F.CODE_128, F.CODE_39, F.CODE_93, F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E,
    F.ITF, F.CODABAR, F.DATA_MATRIX, F.PDF_417, F.AZTEC]);
  hint.set(Z.DecodeHintType.TRY_HARDER, true);
  const r = new Z.MultiFormatReader();
  r.setHints(hint);
  const c = document.createElement("canvas"), ctx = c.getContext("2d", { willReadFrequently: true });
  let okret = false;
  return async video => {
    const w = video.videoWidth, v = video.videoHeight;
    if (!w || !v) return null;
    const k = Math.min(1, 1000 / Math.max(w, v));                // manja slika = brže čitanje
    okret = !okret;                                              // svaki drugi put okrenuto za 90° (minđuša postavljena uspravno)
    c.width = Math.round((okret ? v : w) * k); c.height = Math.round((okret ? w : v) * k);
    ctx.save();
    if (okret) { ctx.translate(c.width, 0); ctx.rotate(Math.PI / 2); }
    ctx.drawImage(video, 0, 0, w * k, v * k);
    ctx.restore();
    try {
      return r.decodeWithState(new Z.BinaryBitmap(new Z.HybridBinarizer(new Z.HTMLCanvasElementLuminanceSource(c)))).getText().trim() || null;
    } catch (e) { return null; } finally { r.reset(); }
  };
}

// pronađi grlo po skeniranom kodu: oznaka, markica, stara markica; kod sa minđuše često ima i oznaku zemlje (RS…)
function nadjiPoKodu(kod) {
  const x = M.nadji(kod);
  if (x && !M.A[x].osnivac) return x;
  const n = norm(kod);
  if (n.length < 3) return null;
  const kand = M.grla().filter(a => [a.markica, a.id, ...a.stare].some(m => {
    const nm = norm(m);
    return nm.length >= 4 && (n.endsWith(nm) || nm.endsWith(n) || n.includes(nm));
  }));
  return kand.length === 1 ? kand[0].id : null;
}

// dugme 📷 pored polja: <div class="sakam"><input ...><button class="kam" data-kam="grlo|markica">📷</button></div>
const saKamerom = (polje, vrsta) => `<div class="sakam">${polje}<button type="button" class="kam" data-kam="${vrsta}" aria-label="${t("Skeniraj", "Scan")}">📷</button></div>`;
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-kam]");
  if (!b) return;
  e.preventDefault();
  const polje = b.parentElement.querySelector("input");
  const kod = await skeniraj(b.dataset.kam === "grlo" ? t("Skeniraj minđušu grla", "Scan the animal's ear tag") : t("Skeniraj novu minđušu", "Scan the new ear tag"));
  if (!kod) return;
  if (b.dataset.kam === "grlo") {
    const id = nadjiPoKodu(kod);
    polje.value = id || kod;
    if (!id) poruka(t(`Grlo sa minđušom ${kod} nije pronađeno.`, `No animal with ear tag ${kod}.`));
  } else {
    polje.value = kod;
    const zauzeto = markicaZauzeta(kod, null);
    if (zauzeto) poruka(zauzeto);
  }
  polje.dispatchEvent(new Event("input", { bubbles: true }));
});

// pretraga: skeniraj i odmah otvori karton
async function skenirajIOtvori() {
  const kod = await skeniraj();
  if (!kod) return;
  const id = nadjiPoKodu(kod);
  if (id) return idi(`karton/${encodeURIComponent(id)}`);
  if (confirm(t(`Grlo sa minđušom ${kod} nije pronađeno.\n\nUpisati novo grlo sa ovom minđušom?`, `No animal with ear tag ${kod}.\n\nAdd a new animal with this ear tag?`)))
    idi(`novo?mk=${encodeURIComponent(kod)}`);
}
