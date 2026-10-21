// Farmer za telefon – skeniranje minđuše (bar kod / QR kod) kamerom telefona.
// Koristi ugrađeni čitač kodova u Chrome-u (BarcodeDetector); kamera se uključuje samo dok je skener otvoren.
"use strict";
const SKENER_FORMATI = ["qr_code", "code_128", "code_39", "code_93", "ean_13", "ean_8", "upc_a", "upc_e", "itf", "codabar", "data_matrix", "pdf417", "aztec"];

// skeniraj(naslov) -> Promise<string|null>  (null = otkazano)
function skeniraj(naslov) {
  return new Promise(resolve => {
    const ov = document.createElement("div");
    ov.className = "skener";
    ov.innerHTML = `<video playsinline muted></video><div class="okvir"></div>
      <div class="skener-vrh"><b>${h(naslov || t("Skeniraj minđušu", "Scan the ear tag"))}</b><span>${t("Uperi kameru u bar kod ili QR kod na minđuši", "Point the camera at the barcode or QR code on the ear tag")}</span></div>
      <div class="skener-dno"><button class="dug skriveno" data-s="lampa">🔦 ${t("Lampa", "Light")}</button>
        <button class="dug" data-s="rucno">⌨ ${t("Upiši ručno", "Type it")}</button><button class="dug glavno" data-s="otkazi">${t("Otkaži", "Cancel")}</button></div>`;
    document.body.appendChild(ov);
    const video = ov.querySelector("video");
    let tok = null, gotovo = false, lampa = false;
    const kraj = vrednost => {
      if (gotovo) return;
      gotovo = true;
      if (tok) tok.getTracks().forEach(x => x.stop());
      ov.remove();
      resolve(vrednost);
    };
    ov.querySelector('[data-s="otkazi"]').onclick = () => kraj(null);
    ov.querySelector('[data-s="rucno"]').onclick = () => {
      const v = prompt(t("Broj minđuše:", "Ear tag number:"));
      kraj(v && v.trim() ? v.trim() : null);
    };
    const greska = tekst => {
      ov.querySelector(".skener-vrh span").textContent = tekst;
      ov.querySelector(".okvir").classList.add("skriveno");
    };
    if (!("BarcodeDetector" in window) || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      greska(t("Ovaj telefon ili pregledač ne može da čita kodove. Otvori Farmer u Chrome-u, ili upiši broj ručno.",
        "This phone or browser cannot read codes. Open Farmer in Chrome, or type the number."));
      return;
    }
    (async () => {
      let detektor;
      try {
        const podrzani = await BarcodeDetector.getSupportedFormats();
        detektor = new BarcodeDetector({ formats: SKENER_FORMATI.filter(f => podrzani.includes(f)) });
      } catch (e) {
        return greska(t("Čitač kodova nije dostupan na ovom telefonu. Upiši broj ručno.", "The code reader is not available on this phone. Type the number."));
      }
      try {
        tok = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
      } catch (e) {
        return greska(e.name === "NotAllowedError"
          ? t("Kamera nije dozvoljena. U Chrome-u klikni ikonicu levo od adrese → Dozvole → Kamera → Dozvoli.", "Camera is not allowed. In Chrome tap the icon left of the address → Permissions → Camera → Allow.")
          : t("Kamera ne može da se uključi: ", "The camera cannot start: ") + e.message);
      }
      if (gotovo) { tok.getTracks().forEach(x => x.stop()); return; }
      video.srcObject = tok;
      try { await video.play(); } catch (e) { /* */ }
      const traka = tok.getVideoTracks()[0];
      try {
        if (traka.getCapabilities && traka.getCapabilities().torch) {
          const b = ov.querySelector('[data-s="lampa"]');
          b.classList.remove("skriveno");
          b.onclick = () => { lampa = !lampa; traka.applyConstraints({ advanced: [{ torch: lampa }] }).catch(() => {}); };
        }
      } catch (e) { /* */ }
      const trazi = async () => {
        if (gotovo) return;
        try {
          if (video.readyState >= 2) {
            const kodovi = await detektor.detect(video);
            const kod = kodovi.map(k => (k.rawValue || "").trim()).find(Boolean);
            if (kod) { if (navigator.vibrate) navigator.vibrate(80); return kraj(kod); }
          }
        } catch (e) { /* sledeći pokušaj */ }
        setTimeout(trazi, 180);
      };
      trazi();
    })();
  });
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
