// HerdDoc za telefon – logika (račun srodstva, gravidnost, ter, karenca, upis događaja).
// Prenesena 1:1 iz PC programa (rodoslov.py, gravidnost.py, obavestenja.py, istorija.py), da podaci budu isti.
"use strict";

const IST_KOLONE = ["grlo", "datum", "dogadjaj", "opis", "partner", "vrednost", "automatski", "uneto", "ishod",
  "ter", "karenca_meso", "karenca_mleko", "upisao", "mast", "proteini"];
const POD_KOLONE = ["grlo", "datum", "tip", "tekst", "ponavljanje", "gotovo", "uneto"];

// ---------------------------------------------------------------- stanje
const S = {
  jezik: "sr", prag: 0.0625, grav: null,
  grla: [], istorija: [], podsetnici: [],
  osnova: null,          // podaci kakvi su stigli sa računara (za spajanje kad se vrate)
  izvoz: null,           // {id, datum} – koji fajl sa računara je učitan
  promene: [],           // šta je urađeno na telefonu (za pregled pre slanja)
};
const EN = () => S.jezik === "en";
const K = () => {
  const k = KONST[S.jezik];
  return S.grav ? Object.assign({}, k, { GRAVIDNOST: S.grav }) : k;
};

// ---------------------------------------------------------------- pomoćne
const pad = n => String(n).padStart(2, "0");
function sada() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
function danas() { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
function dodajDane(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
function razlikaDana(a, b) { return Math.round((a - b) / 86400000); }   // a - b
function fmtD(d) { return d ? (EN() ? `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}` : `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`) : ""; }
function fmtKratko(d) { return d ? (EN() ? `${pad(d.getDate())}/${pad(d.getMonth() + 1)}` : `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.`) : ""; }
function uIso(d) { return d ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` : ""; }

// isti datumi se čitaju hiljade puta (veliko stado) – pamti se rezultat
const _datumi = new Map();
function parsirajDatum(t) {
  const s = String(t || "");
  let v = _datumi.get(s);
  if (v === undefined) {
    const d = _parsirajDatum(s);
    v = d ? d.getTime() : null;
    if (_datumi.size > 50000) _datumi.clear();
    _datumi.set(s, v);
  }
  return v === null ? null : new Date(v);
}
function _parsirajDatum(t) {
  t = String(t || "").trim().replace(/\.+$/, "");
  if (!t) return null;
  t = t.split(" ")[0];
  let g, m, d;
  if (t.includes("-")) [g, m, d] = t.split("-");
  else if (t.includes(".")) [d, m, g] = t.split(".");
  else if (t.includes("/")) [d, m, g] = t.split("/");
  else if (/^\d{4}$/.test(t)) return new Date(+t, 6, 1);
  else return null;
  g = parseInt(g, 10); m = parseInt(m, 10); d = parseInt(d, 10);
  if (!g || !m || !d || m > 12 || d > 31) return null;
  const r = new Date(g, m - 1, d);
  return r.getMonth() === m - 1 ? r : null;
}
const norm = t => String(t || "").toUpperCase().replace(/[^\p{L}\p{N}]/gu, "");
function sortKey(a, b) {
  const sa = String(a).split(/(\d+)/), sb = String(b).split(/(\d+)/);
  for (let i = 0; i < Math.max(sa.length, sb.length); i++) {
    const x = sa[i] ?? "", y = sb[i] ?? "";
    if (/^\d+$/.test(x) && /^\d+$/.test(y)) { if (+x !== +y) return +x - +y; }
    else { const c = x.toLowerCase().localeCompare(y.toLowerCase()); if (c) return c; }
  }
  return 0;
}
function pct(f) {
  const s = (f > 0 && f < 0.1) ? (f * 100).toFixed(2) : (f * 100).toFixed(1);
  return (EN() ? s : s.replace(".", ",")) + "%";
}
function nazivi(vrsta) {
  const N = K().NAZIVI[(vrsta || "").slice(0, 3)];
  return N || (EN() ? ["male", "female", "young", "young"] : ["mužjak", "ženka", "mladunče", "mladunčad"]);
}
function normRasa(r) {
  r = String(r || "").split(/\s+/).filter(Boolean).join(" ");
  const h = K().HIBRID;
  if (r.toLowerCase().startsWith(h)) {
    const kod = r.slice(6).trim().toUpperCase().replace(/X/g, "×").replace(/\*/g, "×").replace(/ /g, "");
    return kod ? `${h} ${kod}` : h;
  }
  return r.toLowerCase();
}
function kodRase(rasa, druga) {
  rasa = normRasa(rasa);
  const h = K().HIBRID;
  if (rasa.startsWith(h + " ")) return `(${rasa.slice(7)})`;
  if (!rasa) return "?";
  const d = normRasa(druga);
  if (d && !d.startsWith(h) && d[0] === rasa[0] && d !== rasa) return rasa[0].toUpperCase() + rasa.slice(1, 2);
  return rasa[0].toUpperCase();
}
function rasaPotomka(ro, rm) {
  ro = normRasa(ro); rm = normRasa(rm);
  if (!ro || ro === rm) return rm;
  if (!rm) return ro;
  return `${K().HIBRID} ${kodRase(ro, rm)}×${kodRase(rm, ro)}`;
}
function vrstaNorm(v) {
  v = String(v || "").trim().toLowerCase();
  const sr = { gov: "goveda", bik: "goveda", kra: "goveda", ovc: "ovce", ova: "ovce", koz: "koze", svi: "svinje", kon: "konji",
    cat: "goveda", cow: "goveda", bul: "goveda", she: "ovce", ewe: "ovce", ram: "ovce", goa: "koze", pig: "svinje",
    swi: "svinje", sow: "svinje", boa: "svinje", hor: "konji", mar: "konji" };
  const en = { cat: "cattle", cow: "cattle", bul: "cattle", gov: "cattle", bik: "cattle", kra: "cattle", she: "sheep", ewe: "sheep",
    ram: "sheep", ovc: "sheep", ova: "sheep", goa: "goats", koz: "goats", pig: "pigs", swi: "pigs", sow: "pigs", boa: "pigs",
    svi: "pigs", hor: "horses", mar: "horses", kon: "horses" };
  return (EN() ? en : sr)[v.slice(0, 3)] || v;
}
function starostMeseci(d) {
  if (!d) return null;
  const n = new Date();
  return (n.getFullYear() - d.getFullYear()) * 12 + n.getMonth() - d.getMonth() - (n.getDate() < d.getDate() ? 1 : 0);
}
function fmtStarost(m) {
  if (m === null || m === undefined) return "";
  if (m < 24) return EN() ? `${m} mo.` : `${m} mes.`;
  const g = Math.floor(m / 12);
  if (EN()) return `${g} ` + (g === 1 ? "year" : "years");
  return `${g} ` + ((g % 10 >= 2 && g % 10 <= 4 && !(g % 100 >= 12 && g % 100 <= 14)) ? "godine" : "godina");
}
const stareLista = r => String(r.stare_markice || "").split(",").map(x => x.trim()).filter(Boolean);

// ---------------------------------------------------------------- Model (rodoslov.py)
class Model {
  constructor(redovi) {
    this.A = {}; this.P = {}; this.byMark = {}; this.warn = [];
    this._gen = {}; this._kin = new Map(); this._dop = new Map();
    const en = EN();
    redovi.forEach((r, rb) => {
      const jid = String(r.id || "").trim();
      if (!jid) return;
      if (this.A[jid]) { this.warn.push(en ? `Tag ${jid} is entered more than once.` : `Oznaka ${jid} je upisana više puta.`); return; }
      this.A[jid] = { id: jid, markica: r.markica || "", rfid: r.rfid || "", vrsta: r.vrsta || K().DRUGO, rasa: r.rasa || "", namena: r.namena || "", autohtona: r.autohtona || "", pol: r.pol || null,
        datum: parsirajDatum(r.datum_rodjenja), aktivno: (r.status || "aktivno") === "aktivno", stado: r.stado || "",
        obrisano: r.status === "obrisano", osnivac: false, _otac: r.otac || "", _majka: r.majka || "", stare: stareLista(r),
        poreklo: (r.poreklo || "").trim(), poreklo_od: (r.poreklo_od || "").trim(), rb, uneto: r.uneto || "" };
      if (r.markica) {
        const n = norm(r.markica);
        if (this.byMark[n] && this.byMark[n] !== jid)
          this.warn.push(en ? `Ear tag ${r.markica} is entered for both ${this.byMark[n]} and ${jid}.` : `Markica ${r.markica} je upisana i za ${this.byMark[n]} i za ${jid}.`);
        this.byMark[n] = jid;
      }
    });
    for (const a of Object.values(this.A)) for (const st of a.stare) if (!(norm(st) in this.byMark)) this.byMark[norm(st)] = a.id;
    for (const a of Object.values(this.A)) if (a.rfid && !(norm(a.rfid) in this.byMark)) this.byMark[norm(a.rfid)] = a.id;   // elektronski broj (RFID)
    for (const a of Object.values(this.A))
      this.P[a.id] = [this.nadji(a._otac) || (a._otac || null), this.nadji(a._majka) || (a._majka || null)];
    for (const [jid, par] of Object.entries(this.P)) {
      par.forEach((r, i) => {
        if (r && !this.A[r]) {
          this.A[r] = { id: r, markica: "", vrsta: this.A[jid].vrsta, rasa: "", pol: i === 0 ? "m" : "z", datum: null, aktivno: false,
            stado: "", osnivac: true, obrisano: false, stare: [], poreklo: "", poreklo_od: "", rb: -1, uneto: "" };
          this.P[r] = [null, null];
        }
      });
    }
    for (const [o, m] of Object.values(this.P)) {
      if (o && !this.A[o].pol) this.A[o].pol = "m";
      if (m && !this.A[m].pol) this.A[m].pol = "z";
    }
    for (const [jid, [o, m]] of Object.entries(this.P))
      if (jid === o || jid === m) { this.warn.push(en ? `${jid} is entered as its own parent.` : `${jid} je upisan kao sopstveni roditelj.`); this.P[jid] = [null, null]; }
    for (const jid of (this.imaKrug() ? Object.keys(this.P) : []))   // sporo traženje samo kad krug stvarno postoji
      if (this.preci(jid).has(jid)) { this.warn.push(en ? `${jid} is its own ancestor – check the parents.` : `${jid} je sam sebi predak – proveri roditelje.`); this.P[jid] = [null, null]; }
  }
  imaKrug() {                                    // da li je neko grlo samo sebi predak – jedan prolaz kroz stado
    const st = new Map();
    for (const start of Object.keys(this.P)) {
      if (st.has(start)) continue;
      const stek = [[start, (this.P[start] || []).filter(Boolean), 0]];
      st.set(start, 1);
      while (stek.length) {
        const vrh = stek[stek.length - 1];
        if (vrh[2] >= vrh[1].length) { st.set(vrh[0], 2); stek.pop(); continue; }
        const r = vrh[1][vrh[2]++];
        if (st.get(r) === 1) return true;
        if (!st.has(r)) { st.set(r, 1); stek.push([r, (this.P[r] || []).filter(Boolean), 0]); }
      }
    }
    return false;
  }
  nadji(t) {
    t = String(t || "").trim();
    if (!t) return null;
    if (this.A[t]) return t;
    const n = norm(t);
    if (this.byMark[n]) return this.byMark[n];
    const broj = Object.keys(this.A).length;
    if (!this._norm || this._norm.n !== broj) {
      const ix = new Map();
      for (const k of Object.keys(this.A)) if (!ix.has(norm(k))) ix.set(norm(k), k);
      this._norm = { n: broj, ix };
    }
    return this._norm.ix.get(n) || null;
  }
  // broj sa čitača minđuša (RFID): tačno, ili upisana markica/RFID (bar 8 cifara) na kraju pročitanog broja
  nadjiCitac(procitano) {
    const x = this.nadji(procitano);
    if (x && !this.A[x].osnivac) return x;
    const cif = s => String(s || "").replace(/\D/g, ""), c = cif(procitano);
    const isti = b => b && (norm(b) === norm(procitano) || (cif(b).length >= 8 && c.endsWith(cif(b))));
    const nadj = Object.values(this.A).filter(a => !a.osnivac && (isti(a.rfid) || isti(a.markica))).map(a => a.id);
    return nadj.length === 1 ? nadj[0] : null;
  }
  grla(samoAktivna = false) {
    return Object.values(this.A).filter(a => !a.osnivac && !a.obrisano && (a.aktivno || !samoAktivna))
      .sort((a, b) => ((a.uneto || "") < (b.uneto || "") ? 1 : (a.uneto || "") > (b.uneto || "") ? -1 : b.rb - a.rb));
  }
  preci(x) {
    const rez = new Set(), stek = [x];
    while (stek.length) for (const r of (this.P[stek.pop()] || [null, null])) if (r && !rez.has(r)) { rez.add(r); stek.push(r); }
    return rez;
  }
  gen(x) {
    if (x === null || x === undefined) return -1;
    if (!(x in this._gen)) { const [o, m] = this.P[x] || [null, null]; this._gen[x] = 1 + Math.max(this.gen(o), this.gen(m)); }
    return this._gen[x];
  }
  kinship(a, b) {
    if (!a || !b) return 0;
    if (a === b) { const [o, m] = this.P[a] || [null, null]; return 0.5 * (1 + this.kinship(o, m)); }
    let ga = this.gen(a), gb = this.gen(b);
    if (ga > gb || (ga === gb && a > b)) [a, b] = [b, a];
    const k = a + "\u0000" + b;
    if (!this._kin.has(k)) { const [o, m] = this.P[b] || [null, null]; this._kin.set(k, 0.5 * (this.kinship(a, o) + this.kinship(a, m))); }
    return this._kin.get(k);
  }
  doprinos(x, predak) {
    if (!x) return 0;
    if (x === predak) return 1;
    const k = x + "\u0000" + predak;
    if (!this._dop.has(k)) { const [o, m] = this.P[x] || [null, null]; this._dop.set(k, 0.5 * (this.doprinos(o, predak) + this.doprinos(m, predak))); }
    return this._dop.get(k);
  }
  inbr(x) {
    if (!this._inbr) this._inbr = new Map();
    if (!this._inbr.has(x)) { const [o, m] = this.P[x] || [null, null]; this._inbr.set(x, this.kinship(o, m)); }
    return this._inbr.get(x);
  }
  r(a, b) { return 2 * this.kinship(a, b) / Math.sqrt((1 + this.inbr(a)) * (1 + this.inbr(b))); }
  odnos(a, b) {
    const [oa, ma] = this.P[a] || [null, null], [ob, mb] = this.P[b] || [null, null], en = EN();
    if (a === ob || a === mb || b === oa || b === ma) return en ? "parent–offspring" : "roditelj i potomak";
    if (oa && ma && oa === ob && ma === mb) return en ? "full sibling" : "puni brat / sestra";
    if ((oa && oa === ob) || (ma && ma === mb)) return en ? "half sibling" : "polubrat / polusestra";
    if (this.preci(b).has(a) || this.preci(a).has(b)) return en ? "ancestor and descendant" : "predak i potomak";
    const r = this.r(a, b);
    return r >= 0.2 ? (en ? "closely related" : "blisko srodni") : r >= 0.06 ? (en ? "distant relatives" : "dalji rod")
      : r > 0 ? (en ? "very distantly related" : "daleko srodni") : (en ? "unrelated" : "nesrodni");
  }
  polNaziv(x) {
    const a = this.A[x], n = nazivi(a.vrsta);
    return a.pol === "m" ? n[0] : a.pol === "z" ? n[1] : (EN() ? "sex unknown" : "pol nepoznat");
  }
  deca(x) { return Object.keys(this.P).filter(k => this.P[k][0] === x || this.P[k][1] === x).filter(k => !this.A[k].osnivac); }
}

function procena(f, prag) {
  const en = EN();
  if (f === 0) return [en ? "excellent" : "odlično", "ok"];
  if (f < prag / 2) return [en ? "good" : "dobro", "ok"];
  if (f <= prag) return [en ? "acceptable" : "prihvatljivo", "warn"];
  if (f < 0.125) return [en ? "risky" : "rizično", "bad"];
  return [en ? "not recommended" : "ne preporučuje se", "bad"];
}

// ---------------------------------------------------------------- istorija i podsetnici
let M = new Model([]);
function osveziModel() { M = new Model(S.grla); }

// ko je upisao: ime ovog telefona (podešava se pri uparivanju), da se na računaru vidi koji radnik je šta uneo
function imeTelefona() { return (S.sinh && S.sinh.ime) || S.imeTelefona || (S.jezik === "en" ? "Phone" : "Telefon"); }
function dodaj(grlo, dogadjaj, o = {}) {
  const z = { grlo, datum: o.datum || fmtD(danas()), dogadjaj, opis: o.opis || "", partner: o.partner || "", vrednost: o.vrednost || "",
    automatski: o.automatski ? "1" : "", uneto: sada(), ishod: "", ter: "", karenca_meso: o.karenca_meso || "", karenca_mleko: o.karenca_mleko || "", upisao: imeTelefona(),
    mast: o.mast || "", proteini: o.proteini || "" };
  S.istorija.push(z);
  return z;
}
// indeks istorije (po grlu i spisak parenja) – da i farma od više hiljada grla radi brzo
let _ix = { ref: null, n: -1, poGrlu: null, parenja: null, par: "" };
function ixIstorije() {
  const par = K().PARENJE;
  if (_ix.ref !== S.istorija || _ix.n !== S.istorija.length || _ix.par !== par) {
    const poGrlu = new Map(), parenja = [];
    for (const z of S.istorija) {
      let l = poGrlu.get(z.grlo);
      if (!l) poGrlu.set(z.grlo, (l = []));
      l.push(z);
      if (z.dogadjaj === par && !z.automatski) parenja.push(z);
    }
    _ix = { ref: S.istorija, n: S.istorija.length, poGrlu, parenja, par };
  }
  return _ix;
}
// dnevna mužnja se ne prikazuje u običnoj istoriji (ima svoj ekran) – osim kad se traži (mleko=true)
function istorijaZa(grlo, auto = true, mleko = false) {
  const mz = K().MUZNJA;
  return (grlo === null ? S.istorija : (ixIstorije().poGrlu.get(grlo) || [])).filter(x => (grlo === null || x.grlo === grlo) && (auto || !x.automatski) && (mleko || x.dogadjaj !== mz))
    .sort((a, b) => ((parsirajDatum(b.datum) || 0) - (parsirajDatum(a.datum) || 0)) || ((a.uneto || "") < (b.uneto || "") ? 1 : (a.uneto || "") > (b.uneto || "") ? -1 : 0));
}
function zabelezi(tekst) { S.promene.push({ vreme: sada(), tekst }); }

// ---------------------------------------------------------------- gravidnost (gravidnost.py)
function roditeljiParenja(z) {
  const g = z.grlo, p = (M.nadji(z.partner) || z.partner || "").trim() || null;
  if (M.A[g] && M.A[g].pol === "m") return [p, g];
  return [g, p];
}
function profilGravidnosti(vrsta, rasa) {
  const v = vrstaNorm(vrsta), r = normRasa(rasa), G = K().GRAVIDNOST;
  let kljuc = null;
  for (const [k, [naziv, vr, prepoznaj]] of Object.entries(G))
    if (prepoznaj.length && vr === v && prepoznaj.some(p => r.includes(p))) { kljuc = k; break; }
  if (kljuc === null) kljuc = Object.keys(G).find(k => G[k][1] === v && !G[k][2].length) ?? null;
  if (kljuc === null) return null;
  const [naziv, , , mn, mx, pr] = G[kljuc];
  return { kljuc, naziv, mn, mx, pr };
}
function vrstaParenja(z) { const [majka] = roditeljiParenja(z); const g = M.A[majka] ? majka : z.grlo; return M.A[g] ? M.A[g].vrsta : ""; }
function rasaParenja(z) { const [majka] = roditeljiParenja(z); return M.A[majka] ? M.A[majka].rasa : ""; }
function granicePorodjaja(z) {
  const d = parsirajDatum(z.datum), p = profilGravidnosti(vrstaParenja(z), rasaParenja(z));
  if (!d || !p) return [null, null, null];
  return [dodajDane(d, p.mn), dodajDane(d, p.pr), dodajDane(d, p.mx)];
}
const cekaPorodjaj = z => z.dogadjaj === K().PARENJE && !z.ishod && !z.automatski;
const _legla = new Map();
function leglo(z) {
  const ish = z.ishod || "";
  if (!ish.startsWith("leglo:")) return null;
  let v = _legla.get(ish);
  if (!v) {
    const d = (ish.split(":").slice(0, 3).concat([ish.split(":").slice(3).join(":")])).concat(["", "", "", ""]).slice(0, 4);
    v = [parseInt(d[1], 10) || 0, d[2], d[3].split(",").filter(Boolean)];
    if (_legla.size > 20000) _legla.clear();
    _legla.set(ish, v);
  }
  return [v[0], v[1], v[2].slice()];
}
function opisIshoda(z) {
  if (z.dogadjaj !== K().PARENJE || z.automatski) return "";
  const ish = z.ishod || "", en = EN();
  if (ish.startsWith("rodjeno:")) return (en ? "☑ born: " : "☑ rođeno: ") + ish.slice(8).replace(/,/g, ", ");
  const lg = leglo(z);
  if (lg) { const [uk, dd, vec] = lg; return (en ? `🏷 ${uk} born ${dd} – waiting for ear tag` : `🏷 ${uk} rođeno ${dd} – čeka minđušu`) + (vec.length ? ` (${vec.length}/${uk})` : ""); }
  if (ish === "uklonjeno") return en ? "✕ young not entered in the list" : "✕ mladi nisu upisani u listu";
  if (ish === "neuspelo") return en ? "✕ failed" : "✕ nije uspelo";
  if (ish === "ponovljeno") return en ? "– repeated mating" : "– ponovljeno parenje";
  const [od, oc] = granicePorodjaja(z);
  if (od && danas() < od) return en ? `⏳ pregnant until ${fmtD(oc)}` : `⏳ gravidna do ${fmtD(oc)}`;
  return "☐ " + (oc ? (en ? `entry open (due ${fmtD(oc)})` : `upis otvoren (termin ${fmtD(oc)})`) : (en ? "waiting for young" : "čeka mlade"));
}
function cekajuPorodjaj(x = null) {
  const posl = {};
  for (const z of ixIstorije().parenja) {
    if (z.dogadjaj !== K().PARENJE || z.automatski) continue;
    const [majka] = roditeljiParenja(z);
    if (x !== null && ![z.grlo, majka, M.nadji(z.partner)].includes(x)) continue;
    const kljuc = majka || z.grlo, d = parsirajDatum(z.datum) || new Date(0);
    if (!posl[kljuc] || d >= (parsirajDatum(posl[kljuc].datum) || new Date(0))) posl[kljuc] = z;
  }
  return Object.values(posl).filter(cekaPorodjaj).sort((a, b) => (granicePorodjaja(a)[1] || 8.64e15) - (granicePorodjaja(b)[1] || 8.64e15));
}
function zatvoriStaraParenja(nz) {
  if (nz.dogadjaj !== K().PARENJE) return;
  const [majka] = roditeljiParenja(nz), d = parsirajDatum(nz.datum) || new Date(0);
  for (const z of ixIstorije().parenja)
    if (z !== nz && cekaPorodjaj(z) && roditeljiParenja(z)[0] === majka && (parsirajDatum(z.datum) || new Date(0)) <= d) z.ishod = "ponovljeno";
}
function cekajuMindjusu(x = null) {
  return ixIstorije().parenja.filter(z => {
    if (!leglo(z)) return false;
    const [majka, otac] = roditeljiParenja(z);
    return x === null || [z.grlo, majka, otac].includes(x);
  }).sort((a, b) => (parsirajDatum(leglo(a)[1]) || 0) - (parsirajDatum(leglo(b)[1]) || 0));
}
function podaciLegla(z) {
  const [majka, otac] = roditeljiParenja(z), ref = M.A[majka] ? majka : z.grlo;
  const vrsta = (M.A[ref] || {}).vrsta || K().VRSTE[0];
  const rasa = rasaPotomka(M.A[otac] ? M.A[otac].rasa : "", M.A[majka] ? M.A[majka].rasa : "");
  return { majka, otac, vrsta, rasa, n: nazivi(vrsta) };
}

// ---------------------------------------------------------------- ter i karenca (obavestenja.py)
const ciklusTera = vrsta => K().TER_CIKLUS[vrstaNorm(vrsta)] || 21;
function posleNovogZapisa(nz) {
  zatvoriStaraParenja(nz);
  if (nz.dogadjaj === K().TER) {
    for (const z of cekajuPorodjaj(nz.grlo)) {
      const [majka] = roditeljiParenja(z);
      if (majka === nz.grlo && (parsirajDatum(z.datum) || new Date(0)) < (parsirajDatum(nz.datum) || new Date(8.64e15))) {
        z.ishod = "neuspelo"; z.ter = "da";
        dodaj(majka, K().AUTO, { opis: EN() ? `Mating of ${z.datum} marked as failed (the female is in heat again)` : `Parenje od ${z.datum} označeno kao neuspelo (ženka se ponovo tera)`, datum: nz.datum, automatski: true });
      }
    }
  }
}
function karenca(x) {
  const d0 = danas(), rez = {};
  for (const z of ixIstorije().poGrlu.get(x) || []) {
    const d = parsirajDatum(z.datum);
    if (!d) continue;
    for (const [vrsta, kljuc] of [["meso", "karenca_meso"], ["mleko", "karenca_mleko"]]) {
      const n = parseInt(z[kljuc] || "0", 10) || 0;
      if (n > 0) { const doD = dodajDane(d, n); if (doD >= d0 && (!rez[vrsta] || doD > rez[vrsta][0])) rez[vrsta] = [doD, z]; }
    }
  }
  return rez;
}
function opisKarence(x) {
  const k = karenca(x), en = EN(), del = [];
  for (const v of ["meso", "mleko"]) if (k[v]) {
    const ost = razlikaDana(k[v][0], danas());
    del.push((en ? `${{ meso: "meat", mleko: "milk" }[v]} until ${fmtKratko(k[v][0])}` : `${v} do ${fmtKratko(k[v][0])}`) + (en ? ` (${ost} d. left)` : ` (još ${ost} d.)`));
  }
  return del.join(", ");
}

// ---------------------------------------------------------------- obaveštenja
// nivo: 0 hitno, 1 uskoro, 2 info, 3 zakazano. akcije: [{tekst, radnja, glavno}]
function obavestenja(x = null) {
  const en = EN(), d0 = danas(), rez = [];
  for (const z of cekajuPorodjaj()) {
    const [majka, otac] = roditeljiParenja(z);
    if (x !== null && ![majka, otac, z.grlo].includes(x)) continue;
    const [od, oc, dk] = granicePorodjaja(z);
    if (!oc) continue;
    const dana = razlikaDana(oc, d0), par = en ? `${majka || "?"} × ${otac || "?"}, mated ${z.datum}` : `${majka || "?"} × ${otac || "?"}, pareno ${z.datum}`;
    const akc = [{ tekst: en ? "Young born" : "Dobijeni mladi", radnja: ["rodjenje", z], glavno: true },
      { tekst: en ? "Failed" : "Nije uspelo", radnja: ["neuspelo", z] }];
    if (dk && d0 > dk) rez.push({ nivo: 0, grlo: majka, naslov: en ? `Due date passed ${razlikaDana(d0, dk)} d. ago` : `Termin porođaja je prošao pre ${razlikaDana(d0, dk)} d.`,
      opis: en ? `Latest ${fmtD(dk)} · ${par}.` : `Najkasnije ${fmtD(dk)} · ${par}.`, datum: dk, akcije: akc });
    else if (od && d0 >= od) rez.push({ nivo: 1, grlo: majka, naslov: (en ? "Birth expected " : "Porođaj se očekuje ") +
      (dana === 0 ? (en ? "today" : "danas") : dana > 0 ? (en ? `in ${dana} d.` : `za ${dana} d.`) : (en ? "any day now" : "svakog dana")),
      opis: en ? `Around ${fmtD(oc)}, latest ${fmtD(dk)} · ${par}.` : `Oko ${fmtD(oc)}, najkasnije ${fmtD(dk)} · ${par}.`, datum: oc, akcije: akc });
    else if (dana <= 21) rez.push({ nivo: 2, grlo: majka, naslov: en ? `Birth in ${dana} d.` : `Porođaj za ${dana} d.`,
      opis: en ? `Due ${fmtD(oc)} · ${par}. Prepare the birthing area.` : `Termin ${fmtD(oc)} · ${par}. Pripremi prostor za porođaj.`, datum: oc, akcije: [] });
  }
  for (const z of cekajuMindjusu(x)) {
    const [uk, dd, vec] = leglo(z), [majka, otac] = roditeljiParenja(z), dr = parsirajDatum(dd);
    const star = dr ? razlikaDana(d0, dr) : 0, n = nazivi(vrstaParenja(z));
    rez.push({ nivo: star >= 14 ? 1 : 2, grlo: majka, naslov: en ? `${uk - vec.length} ${n[3]} waiting for ear tag (${star} d.)` : `${uk - vec.length} ${n[3]} čeka minđušu (${star} d.)`,
      opis: en ? `Born ${dd} · ${majka || "?"} × ${otac || "?"}.` : `Rođeno ${dd} · ${majka || "?"} × ${otac || "?"}.`, datum: dr,
      akcije: [{ tekst: en ? "Enter in list" : "Upiši u listu", radnja: ["upisListu", z], glavno: true }] });
  }
  for (const p of S.podsetnici.filter(p => !p.gotovo && (x === null || p.grlo === x))) {
    const d = parsirajDatum(p.datum) || d0, dana = razlikaDana(d, d0), pon = parseInt(p.ponavljanje || "0", 10) || 0;
    const kad = dana < 0 ? (en ? `${-dana} d. overdue` : `zakasnelo ${-dana} d.`) : dana === 0 ? (en ? "today" : "danas") : dana === 1 ? (en ? "tomorrow" : "sutra") : (en ? `in ${dana} d.` : `za ${dana} d.`);
    rez.push({ nivo: dana < 0 ? 0 : dana <= 3 ? 1 : 3, grlo: p.grlo || null, naslov: `${p.tip || (en ? "Reminder" : "Podsetnik")} – ${kad}`,
      opis: p.datum + (p.tekst ? ` · ${p.tekst}` : "") + (pon ? (en ? ` · repeats every ${pon} d.` : ` · ponavlja se na ${pon} d.`) : ""), datum: d,
      akcije: [{ tekst: en ? "Done" : "Urađeno", radnja: ["podsetnikUradjen", p], glavno: true }, { tekst: en ? "Postpone 7 d." : "Odloži 7 d.", radnja: ["podsetnikOdlozi", p] }] });
  }
  // ter posle parenja
  for (const z of cekajuPorodjaj()) {
    if (z.ter) continue;
    const [majka, otac] = roditeljiParenja(z);
    if (x !== null && x !== majka) continue;
    const dp = parsirajDatum(z.datum);
    if (!dp || !M.A[majka]) continue;
    const c = ciklusTera(M.A[majka].vrsta), ds = razlikaDana(d0, dp);
    if (ds >= c - 3 && ds <= c + 7) {
      const kad = dodajDane(dp, c);
      rez.push({ nivo: 1, grlo: majka, naslov: en ? `Check for heat – day ${ds} after mating` : `Proveri ter – ${ds}. dan od parenja`,
        opis: en ? `Mated ${z.datum} with ${otac || "?"}. If she is not in heat around ${fmtKratko(kad)} (cycle ${c} d.), she is probably pregnant.`
          : `Pareno ${z.datum} sa ${otac || "?"}. Ako se ne tera oko ${fmtKratko(kad)} (ciklus ${c} d.), verovatno je gravidna.`, datum: kad,
        akcije: [{ tekst: en ? "Not in heat" : "Ne tera se", radnja: ["neTeraSe", z], glavno: true }, { tekst: en ? "In heat" : "Tera se", radnja: ["teraSe", z] }] });
    }
  }
  // sledeći ter kod ženki koje nisu gravidne
  const poslednji = {};
  for (const z of S.istorija) if (z.dogadjaj === K().TER && !z.automatski) {
    const d = parsirajDatum(z.datum);
    if (d && (!poslednji[z.grlo] || d > poslednji[z.grlo])) poslednji[z.grlo] = d;
  }
  const gravidne = new Set(cekajuPorodjaj().map(z => roditeljiParenja(z)[0]));
  for (const [g, d] of Object.entries(poslednji)) {
    if ((x !== null && x !== g) || gravidne.has(g) || !M.A[g] || !M.A[g].aktivno) continue;
    if (ixIstorije().parenja.some(z => roditeljiParenja(z)[0] === g && (parsirajDatum(z.datum) || new Date(0)) >= d)) continue;
    const c = ciklusTera(M.A[g].vrsta);
    let sl = dodajDane(d, c);
    while (sl < dodajDane(d0, -2)) sl = dodajDane(sl, c);
    if (razlikaDana(sl, d0) <= 3) rez.push({ nivo: sl > d0 ? 2 : 1, grlo: g,
      naslov: (en ? "Heat expected " : "Očekuje se ter ") + (+sl === +d0 ? (en ? "today" : "danas") : (en ? `around ${fmtKratko(sl)}` : `oko ${fmtKratko(sl)}`)),
      opis: en ? `Last heat ${fmtD(d)} · cycle ${c} days.` : `Poslednji ter ${fmtD(d)} · ciklus ${c} dana.`, datum: sl,
      akcije: [{ tekst: en ? "Record mating" : "Upiši parenje", radnja: ["forma", g, K().PARENJE], glavno: true }, { tekst: en ? "In heat" : "Tera se", radnja: ["forma", g, K().TER] }] });
  }
  for (const a of M.grla(true)) {
    if (x !== null && a.id !== x) continue;
    const k = karenca(a.id);
    if (!Object.keys(k).length) continue;
    const z = Object.values(k).sort((p, q) => q[0] - p[0])[0][1];
    rez.push({ nivo: 2, grlo: a.id, naslov: (en ? "Withdrawal – " : "Karenca – ") + opisKarence(a.id),
      opis: (en ? `After: ${z.dogadjaj.toLowerCase()} ${z.datum}` : `Posle: ${z.dogadjaj.toLowerCase()} ${z.datum}`) + (z.vrednost ? ` (${z.vrednost})` : ""),
      datum: Math.min(...Object.values(k).map(t => t[0])), akcije: [] });
  }
  rez.sort((a, b) => a.nivo - b.nivo || (a.datum || 8.64e15) - (b.datum || 8.64e15));
  return rez;
}

// ---------------------------------------------------------------- radnje (isto kao na računaru)
function upisiDogadjaj({ grlo, datum, dogadjaj, partner, vrednost, opis, karenca_meso, karenca_mleko, vanZapata }) {
  const k = K(), leci = [k.LECENJE, k.VAKCINA].includes(dogadjaj);
  const par = leci ? "" : (M.nadji(partner) || (partner || "").trim());
  const z = dodaj(grlo, dogadjaj, { datum, opis, partner: par, vrednost, karenca_meso: leci ? karenca_meso : "", karenca_mleko: leci ? karenca_mleko : "" });
  posleNovogZapisa(z);
  if ([k.PRODAJA, k.UGINUCE].includes(dogadjaj) && vanZapata) {
    const r = S.grla.find(r => r.id === grlo);
    if (r && (r.status || "aktivno") === "aktivno") {
      r.status = "neaktivno";
      dodaj(grlo, k.AUTO, { opis: EN() ? `Status: out of herd (${dogadjaj.toLowerCase()})` : `Status: van zapata (${dogadjaj.toLowerCase()})`, automatski: true });
    }
  }
  zabelezi(`${grlo} – ${dogadjaj}` + (par ? ` (${par})` : ""));
  osveziModel();
  return z;
}
function teraSe(z) {
  const [majka] = roditeljiParenja(z);
  z.ter = "da"; z.ishod = "neuspelo";
  if (majka) dodaj(majka, K().TER, { opis: EN() ? `In heat again – mating of ${z.datum} failed` : `Ponovo se tera – parenje od ${z.datum} nije uspelo` });
  zabelezi(EN() ? `${majka || "?"}: in heat again (mating of ${z.datum} failed)` : `${majka || "?"}: ponovo se tera (parenje od ${z.datum} nije uspelo)`);
}
function neTeraSe(z) { z.ter = "ne"; zabelezi(EN() ? `${roditeljiParenja(z)[0]}: not in heat` : `${roditeljiParenja(z)[0]}: ne tera se`); }
function oznaciNeuspelo(z) { z.ishod = "neuspelo"; zabelezi(EN() ? `${z.grlo}: mating of ${z.datum} failed` : `${z.grlo}: parenje od ${z.datum} nije uspelo`); }

// rođenje mladih (rodjenje_dijalog) – vraća poruku o grešci ili null
function rodjenje(z, datumStr, zivih, mrtvih, prevremeni) {
  const en = EN(), d = parsirajDatum(datumStr), [od, oc] = granicePorodjaja(z), { majka, otac, n } = podaciLegla(z);
  if (!d) return en ? "The date of birth is not valid." : "Datum rođenja nije ispravan.";
  if (d > danas()) return en ? "The date of birth cannot be in the future." : "Datum rođenja ne može biti u budućnosti.";
  const dp = parsirajDatum(z.datum);
  if (dp && d <= dp) return en ? `The date of birth must be after the mating date (${z.datum}).` : `Datum rođenja mora biti posle datuma parenja (${z.datum}).`;
  if (od && d < od && !prevremeni) return en ? `The earliest date of birth is ${fmtD(od)}. For an earlier birth tick "Premature birth".` : `Najraniji datum rođenja je ${fmtD(od)}. Za raniji porođaj štikliraj „Prevremeni porođaj“.`;
  if (!(zivih >= 0) || !(mrtvih >= 0) || zivih + mrtvih === 0) return en ? "Enter how many young were born." : "Upiši koliko je mladih rođeno.";
  const dstr = fmtD(d);
  let opis = (en ? `Born alive: ${zivih}` : `Rođeno živih: ${zivih}`) + (mrtvih ? (en ? `, stillborn: ${mrtvih}` : `, mrtvorođenih: ${mrtvih}`) : "");
  if (od && d < od) opis += en ? ` – premature birth (${razlikaDana(oc, d)} days before due date)` : ` – prevremeni porođaj (${razlikaDana(oc, d)} dana pre termina)`;
  if (majka) dodaj(majka, K().POROD, { opis, datum: dstr, partner: otac || "", vrednost: String(zivih) });
  if (otac && M.A[otac] && !M.A[otac].osnivac) dodaj(otac, K().POTOMAK, { opis, datum: dstr, partner: majka || "", automatski: true });
  z.ishod = zivih ? `leglo:${zivih}:${dstr}:` : "rodjeno:";
  zabelezi(en ? `Birth: ${zivih} ${n[3]} (${majka || "?"} × ${otac || "?"})` : `Rođenje: ${zivih} ${n[3]} (${majka || "?"} × ${otac || "?"})`);
  return null;
}

function markicaZauzeta(mk, osim) {
  if (!mk) return null;
  const n = norm(mk);
  for (const r of S.grla) {
    if (r === osim) continue;
    if (norm(r.markica) === n || stareLista(r).some(s => norm(s) === n))
      return EN() ? `Ear tag ${mk} already belongs to ${r.id}.` : `Markica ${mk} već pripada grlu ${r.id}.`;
  }
  return null;
}

// upis mladih u listu kad dobiju minđušu (upis_u_listu); mladi: [{id, markica, pol}]
function upisUListu(z, mladi, stado, ostaliCekaju) {
  const en = EN(), lg = leglo(z);
  if (!lg) return en ? "This litter has already been entered." : "Ovo leglo je već upisano.";
  const [ukupno, dstr, vec] = lg, { majka, otac, vrsta, rasa } = podaciLegla(z);
  stado = (stado || "").trim() || K().STADO_PODMLADAK;
  const vidjeni = new Set(), novi = [];
  for (let i = 0; i < mladi.length; i++) {
    let nid = (mladi[i].id || "").trim();
    const mk = (mladi[i].markica || "").trim(), pol = mladi[i].pol;
    if (!nid) return en ? `Enter a tag for young no. ${i + 1}.` : `Upiši oznaku za ${i + 1}. mladunče.`;
    if (vidjeni.has(nid) || S.grla.some(r => r.id === nid) || M.A[nid])
      nid = slobodnaOznaka(nid, S.grla.map(r => r.id).concat(Object.keys(M.A), [...vidjeni]));
    if (mk) { const p = markicaZauzeta(mk, null); if (p || novi.some(x => norm(x.markica) === norm(mk))) return p || (en ? `Ear tag ${mk} is entered twice.` : `Markica ${mk} je upisana dva puta.`); }
    if (pol !== "m" && pol !== "z") return en ? `Choose the sex for ${nid}.` : `Izaberi pol za ${nid}.`;
    vidjeni.add(nid);
    novi.push({ id: nid, markica: mk, vrsta, rasa, namena: (majka && M.A[majka] && M.A[majka].namena) || "",
      autohtona: (majka && M.A[majka] && M.A[majka].autohtona) || "", pol, datum_rodjenja: dstr, otac: otac || "", majka: majka || "", status: "aktivno", stado,
      poreklo: K().SOPSTVENI, poreklo_od: "", stare_markice: "", uneto: sada() });
  }
  if (!novi.length) return en ? "Enter at least one young animal." : "Upiši bar jedno mladunče.";
  for (const x of novi) {
    S.grla.push(x);
    dodaj(x.id, K().AUTO, { opis: en ? `Born ${dstr} from ${majka || "?"} × ${otac || "?"} – entered in the list (herd ${stado})` : `Rođeno ${dstr} od ${majka || "?"} × ${otac || "?"} – upisano u listu (stado ${stado})`, automatski: true });
  }
  const sad = vec.concat(novi.map(x => x.id));
  const opis = novi.map(x => en ? `${x.id} (${x.pol === "m" ? "male" : "female"})` : `${x.id} (${x.pol === "m" ? "muško" : "žensko"})`).join(", ");
  if (majka) dodaj(majka, K().AUTO, { opis: en ? `Young stock entered in the list: ${opis}` : `Podmladak upisan u listu: ${opis}`, automatski: true });
  if (sad.length >= ukupno) z.ishod = "rodjeno:" + sad.join(",");
  else if (ostaliCekaju) z.ishod = `leglo:${ukupno}:${dstr}:${sad.join(",")}`;
  else {
    z.ishod = "rodjeno:" + sad.join(",");
    if (majka) dodaj(majka, K().AUTO, { opis: en ? `From the litter (${dstr}) ${ukupno - sad.length} not entered – died or sold` : `Od legla (${dstr}) nije upisano ${ukupno - sad.length} – uginuli ili prodati`, automatski: true });
  }
  zabelezi((en ? "Entered in the list: " : "Upisano u listu: ") + novi.map(x => x.id).join(", "));
  osveziModel();
  return null;
}

// novo grlo (forma u karton.py)
// namena rase: goveda, ovce i koze (mlečna/tovna/kombinovana), svinje (mesnata/masna/kombinovana); konji nemaju
function nameneZa(vrsta) {
  const v = String(vrsta || "").trim().toLowerCase().slice(0, 3);
  if (["gov", "bik", "kra", "cat", "cow", "bul", "ovc", "ova", "she", "ewe", "ram", "koz", "goa", "jar"].includes(v)) return K().NAMENE_MALI.slice();
  if (["svi", "pig", "sow", "swi", "ner", "boa"].includes(v)) return K().NAMENE_SVINJE.slice();
  return [];
}

// poznate autohtone rase u Srbiji – kvačica „autohtona“ se predloži sama (kao na računaru)
const AUTOHTONE_RASE = ["buša", "busa", "podolsk", "pramenka", "sjenič", "sjenic", "svrlji", "pirotsk", "krivovir", "karakačan",
  "karakacan", "lipsk", "bardoka", "vlaška vitoroga", "vlaska vitoroga", "cigaja", "balkansk", "mangulic", "mangalic", "moravk",
  "resavk", "brdski konj", "domaći brdski", "domaci brdski"];
const autohtonaRasa = r => { r = String(r || "").toLowerCase(); return AUTOHTONE_RASE.some(k => r.includes(k)); };

// isto ime/oznaka već postoji -> sledeći broj po redu: Bela, Bela 2, Bela 3… (kao na računaru)
function slobodnaOznaka(nid, postojece) {
  nid = String(nid || "").trim().split(/\s+/).join(" ");
  const zauzeto = new Set(postojece.filter(Boolean).map(norm));
  if (!zauzeto.has(norm(nid))) return nid;
  let osnova = nid, n = 2;
  const m = nid.match(/^(.*) (\d+)$/);
  if (m && parseInt(m[2], 10) >= 2) { osnova = m[1]; n = parseInt(m[2], 10) + 1; }
  while (zauzeto.has(norm(`${osnova} ${n}`))) n++;
  return `${osnova} ${n}`;
}

// vraća poruku o grešci (tekst) ili {id} sačuvanog grla
function novoGrlo(v) {
  const en = EN(), uneto = (v.id || "").trim();
  if (!uneto) return en ? "Enter the animal's tag." : "Upiši oznaku grla.";
  const nid = slobodnaOznaka(uneto, S.grla.map(r => r.id));
  const mk = (v.markica || "").trim(), z = markicaZauzeta(mk, null);
  if (z) return z;
  const rfid = String(v.rfid || "").trim().split(/\s+/).join(" ");
  const rz = rfid && S.grla.find(r => norm(r.rfid) === norm(rfid));
  if (rz) return en ? `Electronic ID ${rfid} is already entered for animal ${rz.id}.` : `Elektronski broj ${rfid} je već upisan za grlo ${rz.id}.`;
  if (v.pol !== "m" && v.pol !== "z") return en ? "Choose the sex." : "Izaberi pol.";
  const izbori = nameneZa(vrstaNorm(v.vrsta) || v.vrsta);
  if (izbori.length && !izbori.includes(v.namena)) return (en ? "Choose the breed purpose (" : "Izaberi namenu rase (") + izbori.join(" / ") + ").";
  if (v.status !== "aktivno" && v.status !== "neaktivno") return en ? "Choose whether the animal is active (on the farm) or inactive." : "Izaberi da li je grlo aktivno (na farmi) ili neaktivno.";
  const dat = (v.datum_rodjenja || "").trim();
  if (dat && !parsirajDatum(dat)) return en ? "The date is not valid." : "Datum nije ispravan.";
  const o = (v.otac || "").trim(), mj = (v.majka || "").trim();
  if (nid === o || nid === mj) return en ? "An animal cannot be its own parent." : "Grlo ne može biti sopstveni roditelj.";
  const novi = { id: nid, markica: mk, rfid, vrsta: vrstaNorm(v.vrsta) || K().VRSTE[0], rasa: normRasa(v.rasa), namena: izbori.length ? v.namena : "", autohtona: v.autohtona ? "1" : "", pol: v.pol,
    datum_rodjenja: dat ? fmtD(parsirajDatum(dat)) : "", otac: o, majka: mj, status: v.status, stado: (v.stado || "").trim(),
    poreklo: (v.poreklo || "").trim(), poreklo_od: (v.poreklo_od || "").trim(), stare_markice: "", uneto: sada() };
  S.grla.push(novi);
  dodaj(nid, K().AUTO, { opis: (en ? "Animal added to the records" : "Grlo upisano u evidenciju") + (novi.poreklo ? ` (${novi.poreklo}${novi.poreklo_od ? " – " + novi.poreklo_od : ""})` : ""), automatski: true });
  if (dat) for (const [rod, drugi] of [[mj, o], [o, mj]]) {
    const rid = rod ? M.nadji(rod) : null;
    if (rid && !M.A[rid].osnivac)
      dodaj(rid, rod === mj ? K().POROD : K().POTOMAK, { opis: en ? `Offspring born ${nid} (${v.pol === "m" ? "male" : "female"})` : `Rođen potomak ${nid} (${v.pol === "m" ? "muško" : "žensko"})`,
        datum: novi.datum_rodjenja, partner: M.nadji(drugi) || drugi || "", automatski: true });
  }
  zabelezi((en ? "New animal: " : "Novo grlo: ") + nid);
  osveziModel();
  return { id: nid, preimenovano: nid !== uneto ? uneto : "" };
}

// ---------------------------------------------------------------- mlečnost (isto kao mlecnost.py na računaru)
function broj(v) {
  const t = String(v == null ? "" : v).trim().replace(/\s/g, "").replace(",", ".");
  if (!t) return null;
  const x = Number(t);
  return Number.isFinite(x) ? x : null;
}
function fmtBroj(v, dec = 1) {
  const x = typeof v === "number" ? v : broj(v);
  if (x === null) return String(v || "");
  return x.toLocaleString(EN() ? "en-GB" : "sr-Latn-RS", { maximumFractionDigits: dec, minimumFractionDigits: 0 });
}
const zapisBroja = x => String(Math.round(x * 100) / 100);
function muznaVrsta(a) { return !!a && a.pol === "z" && !a.osnivac && nameneZa(a.vrsta).join() === K().NAMENE_MALI.join(); }
function mlecnoGrlo(a) { return muznaVrsta(a) && [K().NAMENE_MALI[0], K().NAMENE_MALI[2]].includes(a.namena); }
function telenja(x) {
  const t = new Set(), porod = K().POROD;
  for (const z of istorijaZa(x, true, false)) if (z.dogadjaj === porod) { const d = parsirajDatum(z.datum); if (d) t.add(+d); }
  for (const [c, par] of Object.entries(M.P)) if (par && par[1] === x && M.A[c] && M.A[c].datum) t.add(+M.A[c].datum);
  return [...t].sort((a, b) => a - b).map(n => new Date(n));
}
function muznjeZa(x) {               // {iso datum: zapis}; isti dan dvaput -> važi poslednji upis
  const mz = K().MUZNJA, rez = {};
  for (const z of istorijaZa(x, true, true)) {
    if (z.dogadjaj !== mz) continue;
    const d = parsirajDatum(z.datum); if (!d) continue;
    const k = uIso(d);
    if (!rez[k] || (z.uneto || "") >= (rez[k].uneto || "")) rez[k] = z;
  }
  return rez;
}
function statMleka(x, d = danas()) {
  const tel = telenja(x).filter(t => t <= d), poc = tel.length ? tel[tel.length - 1] : null;
  const od = poc || dodajDane(d, -304), mz = muznjeZa(x);
  const mer = Object.entries(mz).map(([k, z]) => [parsirajDatum(z.datum), broj(z.vrednost)]).filter(([dd, l]) => l !== null && dd >= od && dd <= d).sort((a, b) => a[0] - b[0]);
  const sedam = mer.filter(([dd]) => razlikaDana(d, dd) < 7).map(m => m[1]);
  return { br: tel.length, pocetak: poc, dan: poc ? razlikaDana(d, poc) + 1 : null, poslednje: mer.length ? mer[mer.length - 1] : null,
    prosek7: sedam.length ? sedam.reduce((a, b) => a + b, 0) / sedam.length : null, ukupno: mer.reduce((a, m) => a + m[1], 0), n: mer.length };
}
// upis/izmena mužnje za dan d; litara=null briše upis za taj dan
function upisiMuznju(x, d, litara, mast, proteini) {
  const mz = K().MUZNJA, iso = uIso(d);
  const stari = S.istorija.filter(z => z.grlo === x && z.dogadjaj === mz && uIso(parsirajDatum(z.datum)) === iso);
  if (litara === null) {
    if (!stari.length) return null;
    S.istorija = S.istorija.filter(z => !stari.includes(z));
    return "brisanje";
  }
  const vr = { vrednost: zapisBroja(litara), mast: mast ? zapisBroja(mast) : "", proteini: proteini ? zapisBroja(proteini) : "" };
  if (stari.length) {
    const z = stari.reduce((a, b) => ((b.uneto || "") >= (a.uneto || "") ? b : a));
    if (stari.length > 1) S.istorija = S.istorija.filter(s => s === z || !stari.includes(s));
    if (Object.keys(vr).every(k => (z[k] || "") === vr[k])) return null;
    Object.assign(z, vr);
    return "izmena";
  }
  dodaj(x, mz, Object.assign({ datum: fmtD(d) }, vr));
  return "novo";
}

function podsetnikUradjen(p) {
  const k = K(), d = fmtD(danas());
  p.gotovo = d;
  if (p.grlo) {
    const tip = k.DOGADJAJI.includes(p.tip) ? p.tip : k.NAPOMENA;
    dodaj(p.grlo, tip, { opis: (tip === k.NAPOMENA && p.tip && p.tip !== k.NAPOMENA ? p.tip + ": " : "") + (p.tekst || (EN() ? "done as reminded" : "urađeno po podsetniku")), datum: d });
  }
  const pon = parseInt(p.ponavljanje || "0", 10) || 0;
  if (pon) {
    let sl = dodajDane(parsirajDatum(p.datum) || danas(), pon);
    while (sl <= danas()) sl = dodajDane(sl, pon);
    S.podsetnici.push({ grlo: p.grlo || "", datum: fmtD(sl), tip: p.tip, tekst: p.tekst, ponavljanje: String(pon), gotovo: "", uneto: sada() });
  }
  zabelezi((EN() ? "Done: " : "Urađeno: ") + (p.tip || "") + (p.grlo ? ` – ${p.grlo}` : ""));
}
function podsetnikOdlozi(p, dana) {
  const d = dodajDane(new Date(Math.max(parsirajDatum(p.datum) || danas(), danas())), dana);
  p.datum = fmtD(d);
  zabelezi((EN() ? "Reminder postponed to " : "Podsetnik odložen za ") + p.datum + (p.grlo ? ` – ${p.grlo}` : ""));
}
function noviPodsetnik(grlo, datum, tip, tekst, ponavljanje) {
  S.podsetnici.push({ grlo: grlo || "", datum, tip, tekst: tekst || "", ponavljanje: ponavljanje ? String(ponavljanje) : "", gotovo: "", uneto: sada() });
  zabelezi((EN() ? "New reminder: " : "Novi podsetnik: ") + tip + (grlo ? ` – ${grlo}` : ""));
}

// najbolji partneri za grlo: suprotni pol, ista vrsta, u zapatu
function partneri(x) {
  const a = M.A[x];
  if (!a || !a.pol) return [];
  return M.grla(true).filter(b => b.id !== x && b.vrsta === a.vrsta && b.pol && b.pol !== a.pol)
    .map(b => ({ id: b.id, f: M.kinship(x, b.id), r: M.r(x, b.id), rasa: b.rasa }))
    .sort((p, q) => p.f - q.f || sortKey(p.id, q.id));
}

// ---------------------------------------------------------------- prenos (fajl računar <-> telefon)
function ucitajSaRacunara(obj) {
  if (!obj || obj.format !== "farmer-telefon") throw new Error(EN() ? "This is not a HerdDoc file for the phone." : "Ovo nije HerdDoc fajl za telefon.");
  S.jezik = obj.jezik === "en" ? "en" : "sr";
  S.prag = +obj.prag || 0.0625;
  S.grav = obj.gravidnost || null;
  S.grla = obj.grla || []; S.istorija = obj.istorija || []; S.podsetnici = obj.podsetnici || [];
  S.osnova = JSON.parse(JSON.stringify({ grla: S.grla, istorija: S.istorija, podsetnici: S.podsetnici }));
  S.izvoz = { id: obj.id, datum: obj.izvezeno, stada: obj.stada || [] };
  S.promene = [];
  osveziModel();
}
function paketZaRacunar() {
  return { format: "farmer-telefon-povratak", verzija: 1, jezik: S.jezik, napravljeno: sada(), izvoz_id: S.izvoz ? S.izvoz.id : null,
    osnova: S.osnova || { grla: [], istorija: [], podsetnici: [] }, grla: S.grla, istorija: S.istorija, podsetnici: S.podsetnici, promene: S.promene };
}

if (typeof module !== "undefined") module.exports = { S, K, Model, M: () => M, osveziModel, parsirajDatum, fmtD, pct, procena, nazivi, rasaPotomka, normRasa,
  vrstaNorm, upisiDogadjaj, rodjenje, upisUListu, novoGrlo, teraSe, neTeraSe, oznaciNeuspelo, podsetnikUradjen, podsetnikOdlozi, noviPodsetnik,
  obavestenja, cekajuPorodjaj, cekajuMindjusu, granicePorodjaja, opisIshoda, partneri, karenca, opisKarence, ucitajSaRacunara, paketZaRacunar,
  leglo, danas, dodajDane, istorijaZa, markicaZauzeta, roditeljiParenja, podaciLegla, sortKey };
