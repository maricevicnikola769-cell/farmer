// HerdDoc za telefon – logika (račun srodstva, gravidnost, ter, karenca, upis događaja).
// Prenesena 1:1 iz PC programa (rodoslov.py, gravidnost.py, obavestenja.py, istorija.py), da podaci budu isti.
"use strict";

const IST_KOLONE = ["grlo", "datum", "dogadjaj", "opis", "partner", "vrednost", "automatski", "uneto", "ishod",
  "ter", "karenca_meso", "karenca_mleko", "upisao", "mast", "proteini", "lab", "uzorak", "fajl", "izvestaj"];
const POD_KOLONE = ["grlo", "datum", "tip", "tekst", "ponavljanje", "gotovo", "uneto", "vreme"];
// '7', '7:5', '07.30' -> '07:00', '07:05', '07:30'; neispravno -> ''
function normVreme(v) {
  const x = String(v || "").trim().match(/^(\d{1,2})(?:\s*[:.,h]\s*(\d{1,2}))?\s*h?$/);
  if (!x) return "";
  const hh = +x[1], mm = +(x[2] || 0);
  return hh < 24 && mm < 60 ? `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}` : "";
}

// ---------------------------------------------------------------- stanje
const S = {
  jezik: "sr", prag: 0.0625, grav: null,
  grla: [], istorija: [], podsetnici: [],
  osnova: null,          // podaci kakvi su stigli sa računara (za spajanje kad se vrate)
  izvoz: null,           // {id, datum} – koji fajl sa računara je učitan
  promene: [],           // šta je urađeno na telefonu (za pregled pre slanja)
  slike: {},             // slike DNK nalaza slikane telefonom: {ime fajla: data URL} – šalju se računaru
};
const JEZICI_TEL = [["sr", "Srpski"], ["en", "English"], ["fr", "Français"], ["de", "Deutsch"], ["es", "Español"], ["pt", "Português"]];
const EN = () => S.jezik !== "sr";     // svaki strani jezik: datumi i podaci kao na engleskom
// t(srpski, engleski): francuski, nemački, španski i portugalski se dobijaju iz engleskog teksta (prevodi.js)
const _sabloni = {}, _kes = {};
function prevedi(en, j) {
  j = j || S.jezik;
  if (j === "sr" || j === "en" || !en || typeof PREVODI === "undefined") return en;
  const rec = PREVODI[j] || {}, k = j + "\u0001" + en;
  if (k in _kes) return _kes[k];
  let rez = rec[en];
  if (rez === undefined || SABLONI.has(en)) {
    rez = en;
    if (!_sabloni[j]) {
      _sabloni[j] = [];
      for (const s of SABLONI) {
        if (!(s in rec)) continue;
        const delovi = s.replace(/\{\{/g, "\u0000").replace(/\}\}/g, "\u0002").split(/(\{\d+\})/);
        const vrati = d => d.replace(/\u0000/g, "{").replace(/\u0002/g, "}");
        const red = [];
        const izraz = delovi.map(d => { const m = /^\{(\d+)\}$/.exec(d); if (m) { red.push(+m[1]); return "([\\s\\S]*?)"; } return vrati(d).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("");
        _sabloni[j].push({ poc: vrati(delovi[0]), re: new RegExp("^" + izraz + "$"), red, prevod: rec[s], stalno: s.replace(/\{\d+\}/g, "").length });
      }
      _sabloni[j].sort((a, b) => b.stalno - a.stalno || b.poc.length - a.poc.length);
    }
    for (const x of _sabloni[j]) {
      if (!en.startsWith(x.poc)) continue;
      const m = x.re.exec(en);
      if (!m) continue;
      const v = [];
      x.red.forEach((i, n) => { v[i] = m[n + 1]; });
      rez = x.prevod.replace(/\{\{|\}\}|\{(\d+)\}/g, (c, i) => c === "{{" ? "{" : c === "}}" ? "}" : (v[+i] ?? ""));
      break;
    }
  }
  _kes[k] = rez;
  return rez;
}
const t = (sr, en) => (S.jezik === "sr" ? sr : (S.jezik === "en" || typeof en !== "string") ? en : prevedi(en));
// vrsta na bilo kom jeziku -> srpski ključ (goveda, ovce, koze, svinje, konji)
const PREFIKSI_VRSTA = { gov: "goveda", bik: "goveda", kra: "goveda", cat: "goveda", cow: "goveda", bul: "goveda",
  ovc: "ovce", ova: "ovce", she: "ovce", ewe: "ovce", ram: "ovce", koz: "koze", jar: "koze", goa: "koze",
  svi: "svinje", pig: "svinje", swi: "svinje", sow: "svinje", boa: "svinje", ner: "svinje", kon: "konji", hor: "konji", mar: "konji" };
// vrste koje je korisnik dodao na računaru (magarci, psi…): ključ je njihov naziv
const mojeVrste = () => (Array.isArray(S.vrste) ? S.vrste : []);
function vrstaKanon(v) {
  v = String(v || "").trim().split(/\s+/).join(" ").toLowerCase();
  if (!v) return "";
  if (mojeVrste().some(x => x.ime === v)) return v;
  return (KONST.VRSTE_RECI || {})[v] || PREFIKSI_VRSTA[v.slice(0, 3)] || "";
}
const K = () => {
  const k = KONST[S.jezik], moje = mojeVrste().filter(x => x && x.ime && !k.VRSTE.includes(x.ime));
  if (!S.grav && !moje.length) return k;
  const d = Object.assign({}, k);
  if (S.grav) d.GRAVIDNOST = S.grav;
  if (moje.length) {
    d.VRSTE = k.VRSTE.concat(moje.map(x => x.ime));
    d.NAZIVI = Object.assign({}, k.NAZIVI, Object.fromEntries(moje.map(x => [x.ime, [x.m, x.z, x.ml, x.mlm]])));
    d.TER_CIKLUS = Object.assign({}, k.TER_CIKLUS, Object.fromEntries(moje.filter(x => +x.ciklus > 0).map(x => [x.ime, +x.ciklus])));
  }
  return d;
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
function fmtD(d) { return d ? (t(`${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`, `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`)) : ""; }
function fmtKratko(d) { return d ? (t(`${pad(d.getDate())}.${pad(d.getMonth() + 1)}.`, `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`)) : ""; }
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
  const N = K().NAZIVI[vrstaKanon(vrsta)];
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
  const k = vrstaKanon(v), i = ["goveda", "ovce", "koze", "svinje", "konji"].indexOf(k);
  return i >= 0 ? K().VRSTE[i] : String(v || "").trim().toLowerCase();
}
function starostMeseci(d) {
  if (!d) return null;
  const n = new Date();
  return (n.getFullYear() - d.getFullYear()) * 12 + n.getMonth() - d.getMonth() - (n.getDate() < d.getDate() ? 1 : 0);
}
function fmtStarost(m) {
  if (m === null || m === undefined) return "";
  if (m < 24) return t(`${m} mes.`, `${m} mo.`);
  const g = Math.floor(m / 12);
  if (EN()) return `${g} ` + t("godina", g === 1 ? "year" : "years");
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
      if (this.A[jid]) { this.warn.push(t(`Oznaka ${jid} je upisana više puta.`, `Tag ${jid} is entered more than once.`)); return; }
      this.A[jid] = { id: jid, markica: r.markica || "", rfid: r.rfid || "", vrsta: r.vrsta || K().DRUGO, rasa: r.rasa || "", namena: r.namena || "", autohtona: r.autohtona || "", pol: r.pol || null,
        datum: parsirajDatum(r.datum_rodjenja), aktivno: (r.status || "aktivno") === "aktivno", stado: r.stado || "",
        obrisano: r.status === "obrisano", osnivac: false, _otac: r.otac || "", _majka: r.majka || "", stare: stareLista(r),
        poreklo: (r.poreklo || "").trim(), poreklo_od: (r.poreklo_od || "").trim(), rb, uneto: r.uneto || "",
        napomena: String(r.napomena || "").trim().split(/\s+/).join(" ") };
      if (r.markica) {
        const n = norm(r.markica);
        if (this.byMark[n] && this.byMark[n] !== jid)
          this.warn.push(t(`Markica ${r.markica} je upisana i za ${this.byMark[n]} i za ${jid}.`, `Ear tag ${r.markica} is entered for both ${this.byMark[n]} and ${jid}.`));
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
            stado: "", osnivac: true, obrisano: false, stare: [], poreklo: "", poreklo_od: "", rb: -1, uneto: "", napomena: "" };
          this.P[r] = [null, null];
        }
      });
    }
    for (const [o, m] of Object.values(this.P)) {
      if (o && !this.A[o].pol) this.A[o].pol = "m";
      if (m && !this.A[m].pol) this.A[m].pol = "z";
    }
    for (const [jid, [o, m]] of Object.entries(this.P))
      if (jid === o || jid === m) { this.warn.push(t(`${jid} je upisan kao sopstveni roditelj.`, `${jid} is entered as its own parent.`)); this.P[jid] = [null, null]; }
    for (const jid of (this.imaKrug() ? Object.keys(this.P) : []))   // sporo traženje samo kad krug stvarno postoji
      if (this.preci(jid).has(jid)) { this.warn.push(t(`${jid} je sam sebi predak – proveri roditelje.`, `${jid} is its own ancestor – check the parents.`)); this.P[jid] = [null, null]; }
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
    if (a === ob || a === mb || b === oa || b === ma) return t("roditelj i potomak", "parent–offspring");
    if (oa && ma && oa === ob && ma === mb) return t("puni brat / sestra", "full sibling");
    if ((oa && oa === ob) || (ma && ma === mb)) return t("polubrat / polusestra", "half sibling");
    if (this.preci(b).has(a) || this.preci(a).has(b)) return t("predak i potomak", "ancestor and descendant");
    const r = this.r(a, b);
    return r >= 0.2 ? (t("blisko srodni", "closely related")) : r >= 0.06 ? (t("dalji rod", "distant relatives"))
      : r > 0 ? (t("daleko srodni", "very distantly related")) : (t("nesrodni", "unrelated"));
  }
  polNaziv(x) {
    const a = this.A[x], n = nazivi(a.vrsta);
    return a.pol === "m" ? n[0] : a.pol === "z" ? n[1] : (t("pol nepoznat", "sex unknown"));
  }
  // mužjaci iste vrste u zapatu u istom stadu (pušteni sa ženkama) – oni je pare; mladi (< 6 meseci) se ne računaju
  muzjaciUStadu(x, minMeseci = 6) {
    const a = this.A[x];
    if (!a || !a.stado) return [];
    return Object.values(this.A).filter(b => b !== a && !b.osnivac && !b.obrisano && b.aktivno && b.pol === "m" && b.stado === a.stado &&
      b.vrsta === a.vrsta && !(b.datum && starostMeseci(b.datum) < minMeseci)).map(b => b.id).sort(sortKey);
  }
  deca(x) { return Object.keys(this.P).filter(k => this.P[k][0] === x || this.P[k][1] === x).filter(k => !this.A[k].osnivac); }
}

function procena(f, prag) {
  const en = EN();
  if (f === 0) return [t("odlično", "excellent"), "ok"];
  if (f < prag / 2) return [t("dobro", "good"), "ok"];
  if (f <= prag) return [t("prihvatljivo", "acceptable"), "warn"];
  if (f < 0.125) return [t("rizično", "risky"), "bad"];
  return [t("ne preporučuje se", "not recommended"), "bad"];
}

// ---------------------------------------------------------------- istorija i podsetnici
let M = new Model([]);
function osveziModel() { M = new Model(S.grla); }

// ko je upisao: ime ovog telefona (podešava se pri uparivanju), da se na računaru vidi koji radnik je šta uneo
function imeTelefona() { return (S.sinh && S.sinh.ime) || S.imeTelefona || t("Telefon", "Phone"); }
// ko upisuje: ime i prezime korisnika (obavezno u aplikaciji), inače ime telefona
function koUpisuje() { return cistoIme(S.korisnik || "") || imeTelefona(); }
function dodaj(grlo, dogadjaj, o = {}) {
  const z = { grlo, datum: o.datum || fmtD(danas()), dogadjaj, opis: o.opis || "", partner: o.partner || "", vrednost: o.vrednost || "",
    automatski: o.automatski ? "1" : "", uneto: sada(), ishod: "", ter: "", karenca_meso: o.karenca_meso || "", karenca_mleko: o.karenca_mleko || "", upisao: koUpisuje(),
    mast: o.mast || "", proteini: o.proteini || "", lab: o.lab || "", uzorak: o.uzorak || "", fajl: "" };
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
// napomena o grlu (vidi se svuda gde je grlo); prazna -> uklanja se
function postaviNapomenu(x, tekst) {
  const r = S.grla.find(g => g.id === x);
  if (!r) return;
  const novo = String(tekst || "").trim().split(/\s+/).join(" "), staro = r.napomena || "";
  if (novo === staro) return;
  r.napomena = novo;
  dodaj(x, K().AUTO, { opis: t(`Izmena podataka – napomena: ${staro || "–"} → ${novo || "–"}`, `Details changed – note: ${staro || "–"} → ${novo || "–"}`), automatski: true });
  zabelezi(`${x}: ` + (novo ? "⚠ " + novo : t("napomena uklonjena", "note removed")));
  osveziModel();
}

// ---------------------------------------------------------------- DNK test (dnk.py)
function srKljucVr(v) {              // vrednost na bilo kom jeziku -> srpski ključ (ili undefined)
  const V = KONST.VREDNOSTI;
  if (v in V) return v;
  for (const [k, sv] of Object.entries(V)) if (Object.values(sv).includes(v)) return k;
  return undefined;
}
const DNK_POREKLO_OK = { "Otac i majka potvrđeni": [true, true], "Otac potvrđen (majka nije testirana)": [true, null],
  "Otac isključen": [false, null], "Majka isključena": [null, false], "Otac i majka isključeni": [false, false] };
function dnkZapisi(x) {
  return S.istorija.filter(z => z.grlo === x && srKljucVr(z.dogadjaj) === "DNK test")
    .sort((a, b) => (parsirajDatum(b.datum) || 0) - (parsirajDatum(a.datum) || 0) || String(b.uneto || "").localeCompare(String(a.uneto || "")));
}
function proveraPorekla(x) {
  const z = dnkZapisi(x).find(z => srKljucVr(z.vrednost) === "Provera porekla (otac i majka)");
  return z ? (DNK_POREKLO_OK[srKljucVr(z.opis)] || [null, null]).concat([z]) : null;
}

// ---------------------------------------------------------------- prirast (prirast.py): težina iz događaja „Merenje težine“
function kgVr(v) { const m = /\d+(?:[.,]\d+)?/.exec(String(v || "")); if (!m) return null; const x = parseFloat(m[0].replace(",", ".")); return x > 0 && x < 3000 ? x : null; }
function merenjaTezine(x) {
  const dog = K().DOGADJAJI[5], poDanu = new Map();
  S.istorija.filter(z => z.grlo === x && z.dogadjaj === dog).sort((a, b) => String(a.uneto || "").localeCompare(String(b.uneto || "")))
    .forEach(z => { const d = parsirajDatum(z.datum), kg = kgVr(z.vrednost); if (d && kg) poDanu.set(+d, kg); });
  return [...poDanu.entries()].sort((a, b) => a[0] - b[0]).map(([d, kg]) => [new Date(d), kg]);
}
function prirastG(a, b) { const dana = Math.round((b[0] - a[0]) / 86400000); return dana > 0 ? Math.round((b[1] - a[1]) * 1000 / dana) : null; }

// ---------------------------------------------------------------- Nova rasa (nova_rasa.py, rodoslov.py): udeo krvi kroz generacije
const NEPOZNATO = "?", BLIZU = 0.0625;
function procitajUdeo(tekst) {
  const rez = {};
  for (const deo of String(tekst || "").split(/;|\n|,(?=\s*[^\d\s])/)) {
    const mt = /^\s*(.+?)\s*[=:]?\s*(\d+(?:[.,]\d+)?)\s*%?\s*$/.exec(deo);
    if (!mt) continue;
    const ime = mt[1].replace(/^[\s=:]+|[\s=:]+$/g, "").split(/\s+/).join(" ").toLowerCase(), br = parseFloat(mt[2].replace(",", "."));
    if (ime && br > 0) rez[ime] = (rez[ime] || 0) + br;
  }
  const uk = Object.values(rez).reduce((s, v) => s + v, 0);
  if (!Object.keys(rez).length || uk > 100.5) return {};
  for (const k of Object.keys(rez)) rez[k] /= 100;
  if (uk < 99.5) rez[NEPOZNATO] = (100 - uk) / 100;
  return rez;
}
const zapisiUdeo = s => Object.entries(s).filter(([k]) => k !== NEPOZNATO).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}=${+(v * 100).toFixed(2)}`).join(";");
function sastav(x) {
  if (!x) return { [NEPOZNATO]: 1 };
  const kes = M._sast || (M._sast = {});
  if (kes[x]) return kes[x];
  const r = S.grla.find(g => g.id === x), ud = r ? procitajUdeo(r.udeo_krvi) : {};
  let rez = {};
  if (Object.keys(ud).length) rez = ud;
  else {
    const [o, m] = M.P[x] || [null, null];
    if (o || m) for (const p of [o, m]) for (const [k, v] of Object.entries(sastav(p))) rez[k] = (rez[k] || 0) + v / 2;
    const a = M.A[x] || {}, cista = cistaRasaTel(a.rasa) ? String(a.rasa).trim().split(/\s+/).join(" ").toLowerCase() : "";
    const nep = Object.keys(rez).length ? (rez[NEPOZNATO] || 0) : 1;
    delete rez[NEPOZNATO];
    if (nep > 1e-9) { if (cista) rez[cista] = (rez[cista] || 0) + nep; else rez[NEPOZNATO] = nep; }
  }
  return (kes[x] = rez);
}
function generacijaUkrstanja(x) {
  const kes = M._gu || (M._gu = {});
  if (kes[x]) return kes[x];
  const s = sastav(x);
  let rez;
  if ((s[NEPOZNATO] || 0) >= 0.5) rez = [t("nepoznato", "unknown"), null];
  else if (Math.max(...Object.values(s)) >= 0.999) rez = [t("čistokrvno", "purebred"), 0];
  else {
    const [o, m] = M.P[x] || [null, null], go = o ? generacijaUkrstanja(o)[1] : null, gm = m ? generacijaUkrstanja(m)[1] : null;
    if (go == null || gm == null) rez = [t("ukršteno", "crossbred"), null];
    else if (go === 0 && gm === 0) rez = ["F1", 1];
    else if (go === 0 || gm === 0) rez = [t("povratno ukrštanje", "backcross"), Math.max(go, gm) + 1];
    else rez = [`F${Math.max(go, gm) + 1}`, Math.max(go, gm) + 1];
  }
  return (kes[x] = rez);
}
function sastavPotomka(a, b) { const r = {}; for (const s of [a, b]) for (const [k, v] of Object.entries(s)) r[k] = (r[k] || 0) + v / 2; return r; }
function odstupanje(s, cilj) {
  if (!cilj || !Object.keys(cilj).length) return null;
  const kl = new Set([...Object.keys(s), ...Object.keys(cilj)]);
  let z = 0; for (const k of kl) z += Math.abs((s[k] || 0) - (k !== NEPOZNATO ? (cilj[k] || 0) : 0));
  return z / 2;
}
function tekstUdela(s, najvise = 4) {
  const red = Object.entries(s).filter(([, v]) => v > 1e-9).sort((a, b) => (a[0] === NEPOZNATO) - (b[0] === NEPOZNATO) || b[1] - a[1] || a[0].localeCompare(b[0]));
  const d = red.slice(0, najvise).map(([k, v]) => `${k === NEPOZNATO ? t("nepoznato", "unknown") : k} ${pct(v)}`);
  if (red.length > najvise) d.push(t("ostalo", "other") + " " + pct(red.slice(najvise).reduce((x, [, v]) => x + v, 0)));
  return d.join(" · ");
}
const programRase = () => (S.novaRasa && typeof S.novaRasa === "object" ? S.novaRasa : {});
function sacuvajCiljRase(vrsta, ime, redovi) {
  const novi = {};
  for (const [r, p] of redovi) {
    const n = String(r || "").trim().split(/\s+/).join(" ").toLowerCase(), br = parseFloat(String(p || "").trim().replace(",", ".").replace("%", ""));
    if (!n && !String(p || "").trim()) continue;
    if (!n || !(br > 0)) return t("Za svaku rasu upiši naziv i udeo veći od nule.", "For each breed enter a name and a share above zero.");
    novi[n] = (novi[n] || 0) + br;
  }
  const zb = Object.values(novi).reduce((s, v) => s + v, 0);
  if (Object.keys(novi).length && Math.abs(zb - 100) > 0.5) return t(`Zbir udela je ${String(+zb.toFixed(2)).replace(".", ",")} %, a mora biti 100 %.`, `The shares add up to ${+zb.toFixed(2)} %, but must be 100 %.`);
  S.novaRasa = { vrsta, ime: String(ime || "").trim().split(/\s+/).join(" "), cilj: novi };
  podesIzmene().nova_rasa = S.novaRasa;
  zabelezi(t("Cilj nove rase", "New breed goal"));
  return null;
}
function paroviZaCilj(grla, cilj, koliko = 40) {
  const zenke = grla.filter(a => a.pol === "z" && (sastav(a.id)[NEPOZNATO] || 0) < 0.5).map(a => a.id);
  const muski = grla.filter(a => a.pol === "m" && (sastav(a.id)[NEPOZNATO] || 0) < 0.5 && (!a.datum || (danas() - a.datum) / 86400000 >= 182)).map(a => a.id);
  const rez = [];
  for (const z of zenke.slice(0, 400)) for (const mu of muski.slice(0, 150)) {
    const s = sastavPotomka(sastav(z), sastav(mu));
    rez.push([Math.round(odstupanje(s, cilj) * 1e6) / 1e6, M.kinship(z, mu), z, mu, s]);
  }
  const rizik = f => f > S.prag;
  rez.sort((a, b) => rizik(a[1]) - rizik(b[1]) || a[0] - b[0] || a[1] - b[1]);
  return rez.slice(0, koliko);
}

// ---------------------------------------------------------------- finansije (finansije.py): prihodi i troškovi
const PRIHOD = "prihod", TROSAK = "trosak";
function kategorijeFin(vrsta) {
  return vrsta === PRIHOD ? [t("Prodaja mleka", "Milk sales"), t("Prodaja grla", "Animal sales"), t("Prodaja mesa", "Meat sales"), t("Subvencije", "Subsidies"), t("Ostali prihodi", "Other income")]
    : [t("Hrana (koncentrat, seno, silaža)", "Feed (concentrate, hay, silage)"), t("Veterinar i lekovi", "Vet and medicines"), t("Osemenjavanje", "Insemination"),
       t("Kupovina grla", "Animal purchases"), t("Radnici", "Labour"), t("Gorivo i struja", "Fuel and electricity"), t("Oprema i popravke", "Equipment and repairs"),
       t("Zakup zemlje", "Land rent"), t("Ostali troškovi", "Other costs")];
}
function brojIznos(v) {
  let s = String(v == null ? "" : v).trim().replace(/[\s\u00a0]/g, "");
  if (!s) return null;
  if (s.includes(",") && s.includes(".")) s = s.lastIndexOf(",") > s.lastIndexOf(".") ? s.replace(/\./g, "").replace(",", ".") : s.replace(/,/g, "");
  else s = s.replace(",", ".");
  const x = Number(s);
  return Number.isFinite(x) ? x : null;
}
function fmtNovac(x, valuta) {
  const ceo = Math.abs(x - Math.round(x)) < 0.005;
  let s = x.toLocaleString(EN() ? "en-US" : "de-DE", { minimumFractionDigits: ceo ? 0 : 2, maximumFractionDigits: ceo ? 0 : 2 });
  return `${s} ${valuta || S.valuta || (EN() ? "EUR" : "RSD")}`.trim();
}
const finansije = () => (Array.isArray(S.finansije) ? S.finansije : (S.finansije = []));
function sacuvajFin(v, staro) {
  const d = parsirajDatum(v.datum), x = brojIznos(v.iznos);
  if (!d) return t("Datum nije ispravan.", "The date is not valid.");
  if (x === null || x <= 0) return t("Upiši iznos (npr. 12500 ili 12.500,50).", "Enter the amount (e.g. 12500 or 12,500.50).");
  if (!String(v.kategorija || "").trim()) return t("Izaberi ili upiši kategoriju.", "Choose or type a category.");
  const g = String(v.grlo || "").trim(), gid = g ? M.nadji(g) : "";
  if (g && !gid) return t(`Grlo „${g}“ nije nađeno.`, `Animal “${g}” not found.`);
  const z = { datum: fmtD(d), vrsta: v.vrsta === PRIHOD ? PRIHOD : TROSAK, kategorija: String(v.kategorija).trim(), iznos: String(Math.round(x * 100) / 100),
    grlo: gid || "", stado: String(v.stado || "").trim(), opis: String(v.opis || "").trim(), uneto: staro ? staro.uneto : sada() };
  if (staro) Object.assign(staro, z); else finansije().push(z);
  zabelezi(t("Finansije: ", "Finances: ") + z.kategorija);
  return null;
}
function obrisiFin(z) { S.finansije = finansije().filter(x => x !== z); zabelezi(t("Finansije: obrisan upis", "Finances: entry deleted")); }
function periodFin(izbor, d = danas()) {
  const g = d.getFullYear(), m = d.getMonth();
  if (izbor === "mesec") return [new Date(g, m, 1), d];
  if (izbor === "prosli_mesec") return [new Date(g, m - 1, 1), new Date(g, m, 0)];
  if (izbor === "godina") return [new Date(g, 0, 1), d];
  if (izbor === "prosla_godina") return [new Date(g - 1, 0, 1), new Date(g - 1, 11, 31)];
  return [null, null];
}
function finUPeriodu(od, doo) {
  return finansije().map(z => [z, parsirajDatum(z.datum)]).filter(([, d]) => d && (!od || d >= od) && (!doo || d <= doo))
    .sort((a, b) => b[1] - a[1] || String(b[0].uneto).localeCompare(String(a[0].uneto))).map(([z]) => z);
}
function zbirFin(lista) {
  let pr = 0, tr = 0; const kat = {}, grla = {};
  for (const z of lista) {
    const x = brojIznos(z.iznos) || 0, pri = z.vrsta === PRIHOD;
    if (pri) pr += x; else tr += x;
    const k = `${pri ? "+" : "-"}${z.kategorija || t("bez kategorije", "uncategorised")}`; kat[k] = (kat[k] || 0) + x;
    if (z.grlo) { grla[z.grlo] = grla[z.grlo] || [0, 0]; grla[z.grlo][pri ? 0 : 1] += x; }
  }
  return { pr, tr, kat, grla };
}

// ---------------------------------------------------------------- Moje rase i Moje vrste sa telefona
// Promene se šalju računaru u paketu (S.podesIzmene) – računar ih upiše u svoja podešavanja.
function podesIzmene() { if (!S.podesIzmene) S.podesIzmene = { rase: [], rase_skloni: [], vrste: [], vrste_skloni: [] }; return S.podesIzmene; }
const kljucRase = (vrsta, ime) => `${vrstaKanon(vrsta) || vrsta}|${_imeRase(ime)}`;
// {vrsta, ime, namena, autohtona}; staro = postojeća rasa (izmena) ili null; vraća string (greška) ili { promena grla }
function sacuvajRasu(v, staro) {
  const ime = normRasa(v.ime), vrsta = vrstaKanon(v.vrsta) || v.vrsta;
  if (!ime || !cistaRasaTel(ime)) return t("Upiši naziv rase (ne melez ni hibrid – oni se ne upisuju kao rasa).", "Enter the breed name (not a crossbred or hybrid – those are not entered as a breed).");
  const izb = nameneZa(vrsta);
  if (izb.length && !izb.includes(v.namena)) return t("Izaberi namenu rase (", "Choose the breed purpose (") + izb.join(" / ") + ").";
  const dupla = mojaRasa(vrsta, ime);
  if (dupla && dupla !== staro) return t(`Rasa „${ime}“ već postoji na spisku.`, `The breed “${ime}” is already on the list.`);
  if (!Array.isArray(S.rase)) S.rase = [];
  const nova = { vrsta, ime, namena: izb.length ? v.namena : "", autohtona: v.autohtona ? "1" : "" };
  let grla = 0;
  if (staro && kljucRase(staro.vrsta, staro.ime) !== kljucRase(vrsta, ime)) {          // novi naziv: i grla te rase
    for (const r of S.grla) if (r.status !== "obrisano" && vrstaKanon(r.vrsta) === vrstaKanon(staro.vrsta) && _imeRase(r.rasa) === _imeRase(staro.ime)) {
      dodaj(r.id, K().AUTO, { opis: t(`Rasa: ${r.rasa} → ${ime}`, `Breed: ${r.rasa} → ${ime}`), automatski: true }); r.rasa = ime; grla++;
    }
    podesIzmene().rase_skloni.push(kljucRase(staro.vrsta, staro.ime));
  }
  if (nova.namena) for (const r of S.grla)
    if (r.status !== "obrisano" && vrstaKanon(r.vrsta) === vrstaKanon(vrsta) && _imeRase(r.rasa) === _imeRase(ime) && (r.namena || "") !== nova.namena) {
      dodaj(r.id, K().AUTO, { opis: t(`Namena rase: ${r.namena || "–"} → ${nova.namena}`, `Breed purpose: ${r.namena || "–"} → ${nova.namena}`), automatski: true }); r.namena = nova.namena; grla++;
    }
  if (staro) Object.assign(staro, nova); else S.rase.push(nova);
  const pi = podesIzmene(); pi.rase = pi.rase.filter(x => kljucRase(x.vrsta, x.ime) !== kljucRase(vrsta, ime)).concat([nova]);
  pi.rase_skloni = pi.rase_skloni.filter(k => k !== kljucRase(vrsta, ime));
  zabelezi(t("Rasa: ", "Breed: ") + ime);
  osveziModel();
  return { grla };
}
function skloniRasu(r) {
  S.rase = mojeRase().filter(x => x !== r);
  const pi = podesIzmene(), k = kljucRase(r.vrsta, r.ime);
  pi.rase = pi.rase.filter(x => kljucRase(x.vrsta, x.ime) !== k); pi.rase_skloni.push(k);
  zabelezi(t("Rasa sklonjena: ", "Breed removed: ") + r.ime);
}
// grla koja bi promena namene/naziva rase dotakla (za pitanje pre čuvanja)
function grlaRase(vrsta, ime) { return S.grla.filter(r => r.status !== "obrisano" && vrstaKanon(r.vrsta) === vrstaKanon(vrsta) && _imeRase(r.rasa) === _imeRase(ime)); }
const primeriVrsta = () => [
  [t("magarci", "donkeys"), t("magarac", "jack"), t("magarica", "jenny"), t("magare", "foal"), t("magarad", "foals"), 355, 380, 365, 23],
  [t("bivoli", "buffalo"), t("bivo", "bull"), t("bivolica", "cow"), t("bivolče", "calf"), t("bivolčad", "calves"), 300, 320, 310, 21],
  [t("alpake", "alpacas"), t("mužjak", "male"), t("ženka", "female"), t("mladunče", "cria"), t("mladunčad", "crias"), 330, 350, 340, 0],
  [t("kunići", "rabbits"), t("mužjak", "buck"), t("ženka", "doe"), t("kunić", "kit"), t("kunići", "kits"), 29, 34, 31, 0],
  [t("psi", "dogs"), t("pas", "dog"), t("kuja", "bitch"), t("štene", "puppy"), t("štenad", "puppies"), 58, 68, 63, 0],
  [t("jeleni", "deer"), t("jelen", "stag"), t("košuta", "hind"), t("lane", "fawn"), t("lanad", "fawns"), 225, 240, 233, 18]];
// isto kao ocisti_vrstu na računaru
function ocistiVrstu(v) {
  const ime = String(v.ime || "").trim().split(/\s+/).join(" ").toLowerCase().slice(0, 30);
  const [gmin, gmax, gpr, cik] = ["gmin", "gmax", "gpr", "ciklus"].map(k => parseInt(v[k] || 0, 10));
  if (!ime || [gmin, gmax, gpr, cik].some(Number.isNaN) || !(10 <= gmin && gmin <= gpr && gpr <= gmax && gmax <= 500) || !(0 <= cik && cik <= 120)) return null;
  const tx = (k, d) => String(v[k] || "").trim().split(/\s+/).join(" ").slice(0, 30) || d;
  return { ime, m: tx("m", t("mužjak", "male")), z: tx("z", t("ženka", "female")), ml: tx("ml", t("mladunče", "young")), mlm: tx("mlm", t("mladunčad", "young")), gmin, gmax, gpr, ciklus: cik };
}
function sacuvajVrstu(v, staroIme) {
  const c = ocistiVrstu(v);
  if (!c) return t("Upiši naziv i ispravne dane gravidnosti (od ≤ prosek ≤ do, 10–500 dana) i ciklus (0–120).", "Enter the name and valid gestation days (from ≤ average ≤ to, 10–500 days) and cycle (0–120).");
  if (KONST.sr.VRSTE.includes(c.ime) || KONST.en.VRSTE.includes(c.ime)) return t(`„${c.ime}“ već postoji među osnovnim vrstama.`, `“${c.ime}” is already one of the basic species.`);
  if (mojeVrste().some(x => x.ime === c.ime && x.ime !== staroIme)) return t(`Vrsta „${c.ime}“ već postoji.`, `The species “${c.ime}” already exists.`);
  if (staroIme && staroIme !== c.ime && S.grla.some(r => vrstaKanon(r.vrsta) === staroIme)) return t("Naziv vrste koja već ima grla ne može da se menja.", "The name of a species that already has animals cannot be changed.");
  S.vrste = mojeVrste().filter(x => x.ime !== (staroIme || c.ime)).concat([c]);
  const pi = podesIzmene(); pi.vrste = pi.vrste.filter(x => x.ime !== c.ime).concat([c]);
  if (staroIme && staroIme !== c.ime) pi.vrste_skloni.push(staroIme);
  pi.vrste_skloni = pi.vrste_skloni.filter(x => x !== c.ime);
  zabelezi(t("Vrsta: ", "Species: ") + c.ime);
  osveziModel();
  return null;
}
function skloniVrstu(ime) {
  if (S.grla.some(r => r.status !== "obrisano" && vrstaKanon(r.vrsta) === ime)) return t("Ova vrsta ima grla – ne može da se skloni.", "This species has animals – it cannot be removed.");
  S.vrste = mojeVrste().filter(x => x.ime !== ime);
  const pi = podesIzmene(); pi.vrste = pi.vrste.filter(x => x.ime !== ime); pi.vrste_skloni.push(ime);
  zabelezi(t("Vrsta sklonjena: ", "Species removed: ") + ime);
  osveziModel();
  return null;
}

// ---------------------------------------------------------------- ocene grla (ocene.py): 1–5 ★
// ručne ocene u koloni "ocena": "karakter=4;gradja=3@2026-11-11"; automatske: prirast, plodnost, zdravlje
const rucneOsobine = () => [
  ["karakter", t("Karakter (ćud)", "Temperament"), t("5 = mirno i lako za rad · 1 = agresivno ili plašljivo", "5 = calm and easy to handle · 1 = aggressive or nervous"), false],
  ["gradja", t("Građa (eksterijer)", "Conformation"), t("5 = odlična građa za rasu · 1 = loša", "5 = excellent for the breed · 1 = poor"), false],
  ["noge", t("Noge i papci", "Legs and feet"), t("5 = zdrave, pravilne · 1 = česti problemi", "5 = sound, correct · 1 = frequent problems"), false],
  ["vime", t("Vime", "Udder"), t("5 = pravilno, zdravo · 1 = loše", "5 = well formed, healthy · 1 = poor"), true],
  ["majka", t("Majčinska svojstva", "Mothering ability"), t("5 = brine o mladima, lako se porađa · 1 = odbacuje mlade", "5 = cares for young, easy births · 1 = rejects young"), true]];
const autoOsobine = () => [["prirast", t("Prirast", "Weight gain")], ["plodnost", t("Plodnost", "Fertility")], ["zdravlje", t("Zdravlje", "Health")]];
// više ocenjivača: "Marko Marković:karakter=4@2026-11-12|Jovan Jović:karakter=5@…" (stari zapis bez imena = "")
const cistoIme = s => String(s || "").replace(/[|:;=@]/g, " ").trim().split(/\s+/).filter(Boolean).join(" ").slice(0, 60);
function procitajOcene(tekst) {
  const rez = {};
  for (let seg of String(tekst || "").split("|")) {
    seg = seg.trim(); if (!seg) continue;
    let ime = ""; const dv = seg.indexOf(":"), jed = seg.indexOf("=");
    if (dv !== -1 && (jed === -1 || dv < jed)) { ime = cistoIme(seg.slice(0, dv)); seg = seg.slice(dv + 1); }
    const [oc, dat] = jednaOcena(seg);
    if (Object.keys(oc).length) rez[ime] = [oc, dat];
  }
  return rez;
}
const zapisiOcene = mapa => Object.entries(mapa).filter(([, [oc]]) => Object.keys(oc).length).map(([ime, [oc, dat]]) => (cistoIme(ime) ? cistoIme(ime) + ":" : "") + zapisiOcenu(oc, dat)).join("|");
function procitajOcenu(tekst) {                 // prosek svih ocenjivača
  const sve = Object.values(procitajOcene(tekst)), zb = {};
  sve.forEach(([oc]) => Object.entries(oc).forEach(([k, v]) => (zb[k] = zb[k] || []).push(v)));
  const rez = {}; for (const [k, l] of Object.entries(zb)) rez[k] = Math.round(l.reduce((s, v) => s + v, 0) / l.length * 100) / 100;
  return [rez, sve.map(([, d]) => d).filter(Boolean).sort().pop() || ""];
}
function spojiOcene(baza, moja, njihova) {
  const B = procitajOcene(baza), Mo = procitajOcene(moja), rez = procitajOcene(njihova);
  for (const ime of new Set([...Object.keys(B), ...Object.keys(Mo)]))
    if (JSON.stringify(Mo[ime] || null) !== JSON.stringify(B[ime] || null)) { if (Mo[ime]) rez[ime] = Mo[ime]; else delete rez[ime]; }
  return zapisiOcene(rez);
}
const korisnik = () => cistoIme(S.korisnik || "");
function jednaOcena(tekst) {
  let s = String(tekst || ""), dat = "";
  if (s.includes("@")) { dat = s.slice(s.lastIndexOf("@") + 1).trim(); s = s.slice(0, s.lastIndexOf("@")); }
  const rez = {};
  for (const deo of s.split(";")) { const i = deo.indexOf("="); if (i < 0) continue; const v = parseInt(deo.slice(i + 1), 10); if (v >= 1 && v <= 5) rez[deo.slice(0, i).trim()] = v; }
  return [rez, dat];
}
const zapisiOcenu = (oc, dat) => Object.keys(oc).length ? Object.entries(oc).map(([k, v]) => `${k}=${v}`).join(";") + "@" + (dat || lokIso(new Date())) : "";
const lokIso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const zvezdice = n => n == null ? "–" : "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n));
function rangOcena(v, sve) {
  if (v == null || sve.length < 3) return null;
  const bolji = sve.filter(x => x > v).length;
  return 5 - Math.min(4, Math.floor(bolji / sve.length * 5));
}
// vime: samo ženke koje nisu mlečne rase (kod mlečnih se prati mlečnost)
function vimeSeOcenjuje(x) {
  const r = S.grla.find(g => g.id === x) || {};
  return r.pol === "z" && !(nameneZa(r.vrsta).join() === K().NAMENE_MALI.join() && r.namena === K().NAMENE_MALI[0]);
}
function velicinaLegla(x) {
  const poDanu = {};
  for (const [y, [, mj]] of Object.entries(M.P)) if (mj === x && M.A[y] && !M.A[y].osnivac && M.A[y].datum) { const k = +M.A[y].datum; poDanu[k] = (poDanu[k] || 0) + 1; }
  const v = Object.values(poDanu);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}
function brojLecenja(x, dana = 365) {
  const od = dodajDane(danas(), -dana), leci = K().LECENJE;
  return S.istorija.filter(z => z.grlo === x && z.dogadjaj === leci && (parsirajDatum(z.datum) || danas()) >= od).length;
}
function vrednostiVrste(vrsta) {
  const pr = {}, le = {};
  for (const a of M.grla(true)) {
    if (a.vrsta !== vrsta) continue;
    const m = merenjaTezine(a.id);
    if (m.length >= 2) { const g = prirastG(m[0], m[m.length - 1]); if (g != null) pr[a.id] = g; }
    if (a.pol === "z") { const v = velicinaLegla(a.id); if (v != null) le[a.id] = v; }
  }
  return [pr, le];
}
function oceneGrla(x, kes) {
  const a = M.A[x], red = S.grla.find(g => g.id === x) || {};
  const [rucne, dat] = procitajOcenu(red.ocena);
  if (!vimeSeOcenjuje(x)) delete rucne.vime;
  const [pr, le] = kes || vrednostiVrste(a.vrsta), auto = {};
  const p = pr[x];
  auto.prirast = [rangOcena(p, Object.values(pr)), p != null ? `${p > 0 ? "+" : ""}${p} ${t("g/dan", "g/day")}` : t("nema merenja", "no weighings")];
  if (a.pol === "z") {
    const v = le[x];
    auto.plodnost = [rangOcena(v, Object.values(le)), v != null ? `${v.toFixed(1).replace(".", EN() ? "." : ",")}${t(" mladih po porođaju", " young per birth")}` : t("nema upisanih mladih", "no recorded young")];
  }
  const n = brojLecenja(x);
  auto.zdravlje = [Math.max(1, 5 - n), t(`${n} lečenja za 12 meseci`, `${n} treatments in 12 months`)];
  const sve = Object.values(rucne).concat(Object.entries(auto).filter(([k, [o]]) => o != null && k !== "zdravlje").map(([, [o]]) => o));
  if (sve.length) sve.push(auto.zdravlje[0]);
  return { rucne, datum: dat, auto, ukupno: sve.length ? sve.reduce((s, v) => s + v, 0) / sve.length : null };
}
// sačuva ručne ocene ovog ocenjivača (prazno = briše njegovu ocenu) i upiše u istoriju
function sacuvajOcene(x, oc) {
  const r = S.grla.find(g => g.id === x);
  if (!r) return;
  const cist = {}; for (const [k, v] of Object.entries(oc)) if (v >= 1 && v <= 5) cist[k] = v;
  const mapa = procitajOcene(r.ocena), ime = korisnik();
  if (Object.keys(cist).length) mapa[ime] = [cist, lokIso(new Date())]; else delete mapa[ime];
  r.ocena = zapisiOcene(mapa);
  const kr = { karakter: t("Karakter", "Temper"), gradja: t("Građa", "Conform."), noge: t("Noge", "Legs"), vime: t("Vime", "Udder"), majka: t("Majka", "Mothering") };
  dodaj(x, K().AUTO, { opis: t("Ocena: ", "Score: ") + (ime ? `(${ime}) ` : "") + (Object.entries(cist).map(([k, v]) => `${kr[k] || k} ${v}`).join(", ") || t("obrisana", "removed")), automatski: true });
  zabelezi(t("Ocena: ", "Score: ") + x);
}

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
  if (ish.startsWith("rodjeno:")) return (t("☑ rođeno: ", "☑ born: ")) + ish.slice(8).replace(/,/g, ", ");
  const lg = leglo(z);
  if (lg) { const [uk, dd, vec] = lg; return (t(`🏷 ${uk} rođeno ${dd} – čeka minđušu`, `🏷 ${uk} born ${dd} – waiting for ear tag`)) + (vec.length ? ` (${vec.length}/${uk})` : ""); }
  if (ish === "uklonjeno") return t("✕ mladi nisu upisani u listu", "✕ young not entered in the list");
  if (ish === "neuspelo") return t("✕ nije uspelo", "✕ failed");
  if (ish === "ponovljeno") return t("– ponovljeno parenje", "– repeated mating");
  const [od, oc] = granicePorodjaja(z);
  if (od && danas() < od) return t(`⏳ gravidna do ${fmtD(oc)}`, `⏳ pregnant until ${fmtD(oc)}`);
  return "☐ " + (oc ? (t(`upis otvoren (termin ${fmtD(oc)})`, `entry open (due ${fmtD(oc)})`)) : (t("čeka mlade", "waiting for young")));
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
// upisan događaj (npr. Vakcinacija) zatvara podsetnik iste vrste za to grlo koji je bio na redu (do 14 dana unapred)
function zatvoriPodsetnike(nz) {
  const tip = String(nz.dogadjaj || "").trim().toLowerCase(), d = parsirajDatum(nz.datum) || danas();
  let n = 0;
  for (const p of S.podsetnici.filter(p => !p.gotovo && p.grlo && p.grlo === nz.grlo)) {
    if (String(p.tip || "").trim().toLowerCase() !== tip) continue;
    const pd = parsirajDatum(p.datum) || d;
    if (pd > dodajDane(d, 14)) continue;
    p.gotovo = fmtD(d);
    const pon = parseInt(p.ponavljanje || "0", 10) || 0;
    if (pon) {
      let sl = dodajDane(pd, pon);
      while (sl <= d) sl = dodajDane(sl, pon);
      S.podsetnici.push({ grlo: p.grlo, datum: fmtD(sl), tip: p.tip, tekst: p.tekst, ponavljanje: String(pon), gotovo: "", uneto: sada(), vreme: p.vreme || "" });
    }
    n++;
  }
  return n;
}
function posleNovogZapisa(nz) {
  zatvoriStaraParenja(nz);
  zatvoriPodsetnike(nz);
  if (nz.dogadjaj === K().TER) {
    for (const z of cekajuPorodjaj(nz.grlo)) {
      const [majka] = roditeljiParenja(z);
      if (majka === nz.grlo && (parsirajDatum(z.datum) || new Date(0)) < (parsirajDatum(nz.datum) || new Date(8.64e15))) {
        z.ishod = "neuspelo"; z.ter = "da";
        dodaj(majka, K().AUTO, { opis: t(`Parenje od ${z.datum} označeno kao neuspelo (ženka se ponovo tera)`, `Mating of ${z.datum} marked as failed (the female is in heat again)`), datum: nz.datum, automatski: true });
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
    del.push((t(`${v} do ${fmtKratko(k[v][0])}`, `${{ meso: "meat", mleko: "milk" }[v]} until ${fmtKratko(k[v][0])}`)) + (t(` (još ${ost} d.)`, ` (${ost} d. left)`)));
  }
  return del.join(", ");
}

// ---------------------------------------------------------------- obaveštenja
// nivo: 0 hitno, 1 uskoro, 2 info, 3 zakazano. akcije: [{tekst, radnja, glavno}]
// podešava se na računaru (Obaveštenja): od koliko sati i koliko dana pre roka
const danaUnapred = () => (S.obav && +S.obav.unapred >= 0 ? Math.min(30, +S.obav.unapred) : 3);
const obavSat = () => (S.obav && +S.obav.sat >= 0 ? Math.min(23, +S.obav.sat) : 7);
function obavestenja(x = null) {
  const en = EN(), d0 = danas(), rez = [];
  for (const z of cekajuPorodjaj()) {
    const [majka, otac] = roditeljiParenja(z);
    if (x !== null && ![majka, otac, z.grlo].includes(x)) continue;
    const [od, oc, dk] = granicePorodjaja(z);
    if (!oc) continue;
    const dana = razlikaDana(oc, d0), par = t(`${majka || "?"} × ${otac || "?"}, pareno ${z.datum}`, `${majka || "?"} × ${otac || "?"}, mated ${z.datum}`);
    const akc = [{ tekst: t("Dobijeni mladi", "Young born"), radnja: ["rodjenje", z], glavno: true },
      { tekst: t("Nije uspelo", "Failed"), radnja: ["neuspelo", z] }];
    if (dk && d0 > dk) rez.push({ nivo: 0, grlo: majka, naslov: t(`Termin porođaja je prošao pre ${razlikaDana(d0, dk)} d.`, `Due date passed ${razlikaDana(d0, dk)} d. ago`),
      opis: t(`Najkasnije ${fmtD(dk)} · ${par}.`, `Latest ${fmtD(dk)} · ${par}.`), datum: dk, akcije: akc });
    else if (od && d0 >= od) rez.push({ nivo: 1, grlo: majka, naslov: (t("Porođaj se očekuje ", "Birth expected ")) +
      (dana === 0 ? (t("danas", "today")) : dana > 0 ? (t(`za ${dana} d.`, `in ${dana} d.`)) : (t("svakog dana", "any day now"))),
      opis: t(`Oko ${fmtD(oc)}, najkasnije ${fmtD(dk)} · ${par}.`, `Around ${fmtD(oc)}, latest ${fmtD(dk)} · ${par}.`), datum: oc, akcije: akc });
    else if (dana <= 21) rez.push({ nivo: 2, grlo: majka, naslov: t(`Porođaj za ${dana} d.`, `Birth in ${dana} d.`),
      opis: t(`Termin ${fmtD(oc)} · ${par}. Pripremi prostor za porođaj.`, `Due ${fmtD(oc)} · ${par}. Prepare the birthing area.`), datum: oc, akcije: [] });
  }
  for (const z of cekajuMindjusu(x)) {
    const [uk, dd, vec] = leglo(z), [majka, otac] = roditeljiParenja(z), dr = parsirajDatum(dd);
    const star = dr ? razlikaDana(d0, dr) : 0, n = nazivi(vrstaParenja(z));
    rez.push({ nivo: star >= 14 ? 1 : 2, grlo: majka, naslov: t(`${uk - vec.length} ${n[3]} čeka minđušu (${star} d.)`, `${uk - vec.length} ${n[3]} waiting for ear tag (${star} d.)`),
      opis: t(`Rođeno ${dd} · ${majka || "?"} × ${otac || "?"}.`, `Born ${dd} · ${majka || "?"} × ${otac || "?"}.`), datum: dr,
      akcije: [{ tekst: t("Upiši u listu", "Enter in list"), radnja: ["upisListu", z], glavno: true }] });
  }
  for (const p of S.podsetnici.filter(p => !p.gotovo && (x === null || p.grlo === x))) {
    const d = parsirajDatum(p.datum) || d0, dana = razlikaDana(d, d0), pon = parseInt(p.ponavljanje || "0", 10) || 0;
    let kad = dana < 0 ? (t(`zakasnelo ${-dana} d.`, `${-dana} d. overdue`)) : dana === 0 ? (t("danas", "today")) : dana === 1 ? (t("sutra", "tomorrow")) : (t(`za ${dana} d.`, `in ${dana} d.`));
    let nivoP = dana < 0 ? 0 : dana <= danaUnapred() ? 1 : 3;
    const vr = normVreme(p.vreme), sad = new Date(), sadaHM = `${String(sad.getHours()).padStart(2, "0")}:${String(sad.getMinutes()).padStart(2, "0")}`;
    if (vr && dana === 0 && sadaHM >= vr) { kad = t(`sada (${vr})`, `now (${vr})`); nivoP = 0; }   // došao je zakazani sat
    else if (vr && dana >= 0) kad += t(` u ${vr}`, ` at ${vr}`);
    rez.push({ nivo: nivoP, grlo: p.grlo || null, naslov: `${p.tip || (t("Podsetnik", "Reminder"))} – ${kad}`,
      opis: p.datum + (p.tekst ? ` · ${p.tekst}` : "") + (pon ? (t(` · ponavlja se na ${pon} d.`, ` · repeats every ${pon} d.`)) : ""), datum: d,
      akcije: [{ tekst: t("Urađeno", "Done"), radnja: ["podsetnikUradjen", p], glavno: true }, { tekst: t("Odloži 7 d.", "Postpone 7 d."), radnja: ["podsetnikOdlozi", p] }] });
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
      rez.push({ nivo: 1, grlo: majka, naslov: t(`Proveri ter – ${ds}. dan od parenja`, `Check for heat – day ${ds} after mating`),
        opis: t(`Pareno ${z.datum} sa ${otac || "?"}. Ako se ne tera oko ${fmtKratko(kad)} (ciklus ${c} d.), verovatno je gravidna.`, `Mated ${z.datum} with ${otac || "?"}. If she is not in heat around ${fmtKratko(kad)} (cycle ${c} d.), she is probably pregnant.`), datum: kad,
        akcije: [{ tekst: t("Ne tera se", "Not in heat"), radnja: ["neTeraSe", z], glavno: true }, { tekst: t("Tera se", "In heat"), radnja: ["teraSe", z] }] });
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
      naslov: (t("Očekuje se ter ", "Heat expected ")) + (+sl === +d0 ? (t("danas", "today")) : (t(`oko ${fmtKratko(sl)}`, `around ${fmtKratko(sl)}`))),
      opis: t(`Poslednji ter ${fmtD(d)} · ciklus ${c} dana.`, `Last heat ${fmtD(d)} · cycle ${c} days.`), datum: sl,
      akcije: [{ tekst: t("Upiši parenje", "Record mating"), radnja: ["forma", g, K().PARENJE], glavno: true }, { tekst: t("Tera se", "In heat"), radnja: ["forma", g, K().TER] }] });
  }
  for (const a of M.grla(true)) {
    if (x !== null && a.id !== x) continue;
    const k = karenca(a.id);
    if (!Object.keys(k).length) continue;
    const z = Object.values(k).sort((p, q) => q[0] - p[0])[0][1];
    rez.push({ nivo: 2, grlo: a.id, naslov: (t("Karenca – ", "Withdrawal – ")) + opisKarence(a.id),
      opis: (t(`Posle: ${z.dogadjaj.toLowerCase()} ${z.datum}`, `After: ${z.dogadjaj.toLowerCase()} ${z.datum}`)) + (z.vrednost ? ` (${z.vrednost})` : ""),
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
      dodaj(grlo, k.AUTO, { opis: t(`Status: van zapata (${dogadjaj.toLowerCase()})`, `Status: out of herd (${dogadjaj.toLowerCase()})`), automatski: true });
    }
  }
  zabelezi(`${grlo} – ${dogadjaj}` + (par ? ` (${par})` : ""));
  osveziModel();
  return z;
}
function teraSe(z) {
  const [majka] = roditeljiParenja(z);
  z.ter = "da"; z.ishod = "neuspelo";
  if (majka) dodaj(majka, K().TER, { opis: t(`Ponovo se tera – parenje od ${z.datum} nije uspelo`, `In heat again – mating of ${z.datum} failed`) });
  zabelezi(t(`${majka || "?"}: ponovo se tera (parenje od ${z.datum} nije uspelo)`, `${majka || "?"}: in heat again (mating of ${z.datum} failed)`));
}
function neTeraSe(z) { z.ter = "ne"; zabelezi(t(`${roditeljiParenja(z)[0]}: ne tera se`, `${roditeljiParenja(z)[0]}: not in heat`)); }
function oznaciNeuspelo(z) { z.ishod = "neuspelo"; zabelezi(t(`${z.grlo}: parenje od ${z.datum} nije uspelo`, `${z.grlo}: mating of ${z.datum} failed`)); }

// rođenje mladih (rodjenje_dijalog) – vraća poruku o grešci ili null
function rodjenje(z, datumStr, zivih, mrtvih, prevremeni) {
  const en = EN(), d = parsirajDatum(datumStr), [od, oc] = granicePorodjaja(z), { majka, otac, n } = podaciLegla(z);
  if (!d) return t("Datum rođenja nije ispravan.", "The date of birth is not valid.");
  if (d > danas()) return t("Datum rođenja ne može biti u budućnosti.", "The date of birth cannot be in the future.");
  const dp = parsirajDatum(z.datum);
  if (dp && d <= dp) return t(`Datum rođenja mora biti posle datuma parenja (${z.datum}).`, `The date of birth must be after the mating date (${z.datum}).`);
  if (od && d < od && !prevremeni) return t(`Najraniji datum rođenja je ${fmtD(od)}. Za raniji porođaj štikliraj „Prevremeni porođaj“.`, `The earliest date of birth is ${fmtD(od)}. For an earlier birth tick "Premature birth".`);
  if (!(zivih >= 0) || !(mrtvih >= 0) || zivih + mrtvih === 0) return t("Upiši koliko je mladih rođeno.", "Enter how many young were born.");
  const dstr = fmtD(d);
  let opis = (t(`Rođeno živih: ${zivih}`, `Born alive: ${zivih}`)) + (mrtvih ? (t(`, mrtvorođenih: ${mrtvih}`, `, stillborn: ${mrtvih}`)) : "");
  if (od && d < od) opis += t(` – prevremeni porođaj (${razlikaDana(oc, d)} dana pre termina)`, ` – premature birth (${razlikaDana(oc, d)} days before due date)`);
  if (majka) dodaj(majka, K().POROD, { opis, datum: dstr, partner: otac || "", vrednost: String(zivih) });
  if (otac && M.A[otac] && !M.A[otac].osnivac) dodaj(otac, K().POTOMAK, { opis, datum: dstr, partner: majka || "", automatski: true });
  z.ishod = zivih ? `leglo:${zivih}:${dstr}:` : "rodjeno:";
  zabelezi(t(`Rođenje: ${zivih} ${n[3]} (${majka || "?"} × ${otac || "?"})`, `Birth: ${zivih} ${n[3]} (${majka || "?"} × ${otac || "?"})`));
  return null;
}

function markicaZauzeta(mk, osim) {
  if (!mk) return null;
  const n = norm(mk);
  for (const r of S.grla) {
    if (r === osim) continue;
    if (norm(r.markica) === n || stareLista(r).some(s => norm(s) === n))
      return t(`Markica ${mk} već pripada grlu ${r.id}.`, `Ear tag ${mk} already belongs to ${r.id}.`);
  }
  return null;
}

// upis mladih u listu kad dobiju minđušu (upis_u_listu); mladi: [{id, markica, pol}]
function upisUListu(z, mladi, stado, ostaliCekaju) {
  const en = EN(), lg = leglo(z);
  if (!lg) return t("Ovo leglo je već upisano.", "This litter has already been entered.");
  const [ukupno, dstr, vec] = lg, { majka, otac, vrsta, rasa } = podaciLegla(z);
  stado = (stado || "").trim() || K().STADO_PODMLADAK;
  const vidjeni = new Set(), novi = [];
  for (let i = 0; i < mladi.length; i++) {
    let nid = (mladi[i].id || "").trim();
    const mk = (mladi[i].markica || "").trim(), pol = mladi[i].pol;
    if (!nid) return t(`Upiši oznaku za ${i + 1}. mladunče.`, `Enter a tag for young no. ${i + 1}.`);
    if (vidjeni.has(nid) || S.grla.some(r => r.id === nid) || M.A[nid])
      nid = slobodnaOznaka(nid, S.grla.map(r => r.id).concat(Object.keys(M.A), [...vidjeni]));
    if (mk) { const p = markicaZauzeta(mk, null); if (p || novi.some(x => norm(x.markica) === norm(mk))) return p || (t(`Markica ${mk} je upisana dva puta.`, `Ear tag ${mk} is entered twice.`)); }
    if (pol !== "m" && pol !== "z") return t(`Izaberi pol za ${nid}.`, `Choose the sex for ${nid}.`);
    vidjeni.add(nid);
    novi.push({ id: nid, markica: mk, vrsta, rasa, namena: namenaRase(vrsta, rasa) || (majka && M.A[majka] && M.A[majka].namena) || "",
      autohtona: (majka && M.A[majka] && M.A[majka].autohtona) || "", pol, datum_rodjenja: dstr, otac: otac || "", majka: majka || "", status: "aktivno", stado,
      poreklo: K().SOPSTVENI, poreklo_od: "", stare_markice: "", uneto: sada() });
  }
  if (!novi.length) return t("Upiši bar jedno mladunče.", "Enter at least one young animal.");
  const pl = porukaLimita(novi.length); if (pl) return pl;
  for (const x of novi) {
    S.grla.push(x);
    dodaj(x.id, K().AUTO, { opis: t(`Rođeno ${dstr} od ${majka || "?"} × ${otac || "?"} – upisano u listu (stado ${stado})`, `Born ${dstr} from ${majka || "?"} × ${otac || "?"} – entered in the list (herd ${stado})`), automatski: true });
  }
  const sad = vec.concat(novi.map(x => x.id));
  const opis = novi.map(x => t(`${x.id} (${x.pol === "m" ? "muško" : "žensko"})`, `${x.id} (${x.pol === "m" ? "male" : "female"})`)).join(", ");
  if (majka) dodaj(majka, K().AUTO, { opis: t(`Podmladak upisan u listu: ${opis}`, `Young stock entered in the list: ${opis}`), automatski: true });
  if (sad.length >= ukupno) z.ishod = "rodjeno:" + sad.join(",");
  else if (ostaliCekaju) z.ishod = `leglo:${ukupno}:${dstr}:${sad.join(",")}`;
  else {
    z.ishod = "rodjeno:" + sad.join(",");
    if (majka) dodaj(majka, K().AUTO, { opis: t(`Od legla (${dstr}) nije upisano ${ukupno - sad.length} – uginuli ili prodati`, `From the litter (${dstr}) ${ukupno - sad.length} not entered – died or sold`), automatski: true });
  }
  zabelezi((t("Upisano u listu: ", "Entered in the list: ")) + novi.map(x => x.id).join(", "));
  osveziModel();
  return null;
}

// novo grlo (forma u karton.py)
// namena se zadaje za celu rasu (na računaru); melezi, hibridi i neodređena rasa – po grlu
function cistaRasaTel(rasa) {
  const r = String(rasa || "").split(/\s+/).filter(Boolean).join(" ").toLowerCase();
  return !!r && !/^(hibrid|hybrid|melez|crossbred|mešanac|mesanac|neodređ|neodred|undetermined)/.test(r) && !r.includes("×") && !` ${r} `.includes(" x ");
}
// moje rase (upisane na računaru): [{vrsta, ime, namena, autohtona}]
const mojeRase = () => (Array.isArray(S.rase) ? S.rase : []);
const _imeRase = r => String(r || "").split(/\s+/).filter(Boolean).join(" ").toLowerCase();
function mojaRasa(vrsta, rasa) { return mojeRase().find(r => vrstaKanon(r.vrsta) === vrstaKanon(vrsta) && _imeRase(r.ime) === _imeRase(rasa)); }
function raseZaVrstu(vrsta) {
  const im = {};
  mojeRase().forEach(r => { if (vrstaKanon(r.vrsta) === vrstaKanon(vrsta)) im[_imeRase(r.ime)] = r.ime; });
  S.grla.forEach(a => { if (a.status !== "obrisano" && vrstaKanon(a.vrsta) === vrstaKanon(vrsta) && cistaRasaTel(a.rasa) && !im[_imeRase(a.rasa)]) im[_imeRase(a.rasa)] = a.rasa; });
  return Object.values(im).sort((a, b) => a.localeCompare(b));
}
function namenaRase(vrsta, rasa) {
  if (!cistaRasaTel(rasa)) return "";
  const izbori = nameneZa(vrsta), r0 = String(rasa).split(/\s+/).filter(Boolean).join(" ").toLowerCase(), c = {};
  const moja = mojaRasa(vrsta, rasa);
  if (moja && izbori.includes(moja.namena)) return moja.namena;
  for (const r of S.grla) {
    if (r.status === "obrisano" || vrstaKanon(r.vrsta) !== vrstaKanon(vrsta) || String(r.rasa || "").split(/\s+/).filter(Boolean).join(" ").toLowerCase() !== r0) continue;
    if (izbori.includes(r.namena)) c[r.namena] = (c[r.namena] || 0) + 1;
  }
  const top = Object.entries(c).sort((a, b) => b[1] - a[1])[0];
  return top ? top[0] : "";
}

// namena rase: goveda, ovce i koze (mlečna/tovna/kombinovana), svinje (mesnata/masna/kombinovana); konji nemaju
function nameneZa(vrsta) {
  const v = vrstaKanon(vrsta);
  if (["goveda", "ovce", "koze"].includes(v)) return K().NAMENE_MALI.slice();
  if (v === "svinje") return K().NAMENE_SVINJE.slice();
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

// licenca: paket i broj grla stižu sa računara; null = bez ograničenja
function aktivnihGrla() { return S.grla.filter(r => (r.status || "aktivno") === "aktivno").length; }
function porukaLimita(novih) {
  const l = S.licenca, akt = aktivnihGrla();
  if (!l || l.limit == null || akt + novih <= l.limit) return "";
  return t(`Paket „${l.naziv}“ dozvoljava ${l.limit} aktivnih grla, a sada ih imaš ${akt}. Sva grla i podaci ostaju. Za nova grla izaberi veći paket na računaru (levi meni → 🔑).`,
    `The “${l.naziv}” package allows ${l.limit} active animals, and you now have ${akt}. All animals and data stay. For new animals choose a larger package on the computer (left menu → 🔑).`);
}

// vraća poruku o grešci (tekst) ili {id} sačuvanog grla
function novoGrlo(v) {
  const en = EN(), uneto = (v.id || "").trim() || String(v.markica || "").trim().split(/\s+/).join(" ");   // bez oznake: oznaka = markica
  if (!uneto) return t("Upiši oznaku grla ili ušnu markicu.", "Enter the animal's tag or ear tag.");
  const nid = slobodnaOznaka(uneto, S.grla.map(r => r.id));
  const mk = (v.markica || "").trim(), z = markicaZauzeta(mk, null);
  if (z) return z;
  const rfid = String(v.rfid || "").trim().split(/\s+/).join(" ");
  const rz = rfid && S.grla.find(r => norm(r.rfid) === norm(rfid));
  if (rz) return t(`Elektronski broj ${rfid} je već upisan za grlo ${rz.id}.`, `Electronic ID ${rfid} is already entered for animal ${rz.id}.`);
  if (v.pol !== "m" && v.pol !== "z") return t("Izaberi pol.", "Choose the sex.");
  const izbori = nameneZa(vrstaNorm(v.vrsta) || v.vrsta);
  if (izbori.length && !v.namena) v = { ...v, namena: namenaRase(vrstaNorm(v.vrsta) || v.vrsta, normRasa(v.rasa)) };
  if (izbori.length && !izbori.includes(v.namena)) return (t("Izaberi namenu rase (", "Choose the breed purpose (")) + izbori.join(" / ") + ").";
  if (v.status !== "aktivno" && v.status !== "neaktivno") return t("Izaberi da li je grlo aktivno (na farmi) ili neaktivno.", "Choose whether the animal is active (on the farm) or inactive.");
  const dat = (v.datum_rodjenja || "").trim();
  if (dat && !parsirajDatum(dat)) return t("Datum nije ispravan.", "The date is not valid.");
  const o = (v.otac || "").trim(), mj = (v.majka || "").trim();
  if (nid === o || nid === mj) return t("Grlo ne može biti sopstveni roditelj.", "An animal cannot be its own parent.");
  const novi = { id: nid, markica: mk, rfid, vrsta: vrstaNorm(v.vrsta) || K().VRSTE[0], rasa: normRasa(v.rasa), namena: izbori.length ? v.namena : "", autohtona: v.autohtona ? "1" : "", pol: v.pol,
    datum_rodjenja: dat ? fmtD(parsirajDatum(dat)) : "", otac: o, majka: mj, status: v.status, stado: (v.stado || "").trim(),
    poreklo: (v.poreklo || "").trim(), poreklo_od: (v.poreklo_od || "").trim(), stare_markice: "", uneto: sada(),
    napomena: String(v.napomena || "").trim().split(/\s+/).join(" ") };
  if (novi.status === "aktivno") { const pl = porukaLimita(1); if (pl) return pl; }
  S.grla.push(novi);
  dodaj(nid, K().AUTO, { opis: (t("Grlo upisano u evidenciju", "Animal added to the records")) + (novi.poreklo ? ` (${novi.poreklo}${novi.poreklo_od ? " – " + novi.poreklo_od : ""})` : ""), automatski: true });
  if (dat) for (const [rod, drugi] of [[mj, o], [o, mj]]) {
    const rid = rod ? M.nadji(rod) : null;
    if (rid && !M.A[rid].osnivac)
      dodaj(rid, rod === mj ? K().POROD : K().POTOMAK, { opis: t(`Rođen potomak ${nid} (${v.pol === "m" ? "muško" : "žensko"})`, `Offspring born ${nid} (${v.pol === "m" ? "male" : "female"})`),
        datum: novi.datum_rodjenja, partner: M.nadji(drugi) || drugi || "", automatski: true });
  }
  zabelezi((t("Novo grlo: ", "New animal: ")) + nid);
  osveziModel();
  return { id: nid, preimenovano: nid !== uneto ? uneto : "" };
}

// izmena podataka grla (oznaka se ne menja; grlo se ne briše) – isto kao forma na računaru
// v: polja kao kod novoGrlo; vraća string (greška) ili { id, promene, rasaGrla } (rasaGrla = koliko drugih grla rase dobija namenu)
function izmeniGrlo(id, v, celaRasa = true) {
  const r = S.grla.find(x => x.id === id);
  if (!r) return t("Grlo nije nađeno.", "Animal not found.");
  const mk = String(v.markica || "").trim().split(/\s+/).join(" ");
  if (norm(mk) !== norm(r.markica)) { const z = markicaZauzeta(mk, r); if (z) return z; }
  const rfid = String(v.rfid || "").trim().split(/\s+/).join(" ");
  const rz = rfid && S.grla.find(x => x !== r && norm(x.rfid) === norm(rfid));
  if (rz) return t(`Elektronski broj ${rfid} je već upisan za grlo ${rz.id}.`, `Electronic ID ${rfid} is already entered for animal ${rz.id}.`);
  if (v.pol !== "m" && v.pol !== "z") return t("Izaberi pol.", "Choose the sex.");
  const vrsta = vrstaNorm(v.vrsta) || r.vrsta, izbori = nameneZa(vrsta);
  if (izbori.length && !izbori.includes(v.namena)) return (t("Izaberi namenu rase (", "Choose the breed purpose (")) + izbori.join(" / ") + ").";
  if (v.status !== "aktivno" && v.status !== "neaktivno") return t("Izaberi da li je grlo aktivno (na farmi) ili neaktivno.", "Choose whether the animal is active (on the farm) or inactive.");
  const dat = (v.datum_rodjenja || "").trim();
  if (dat && !parsirajDatum(dat)) return t("Datum nije ispravan.", "The date is not valid.");
  const o = (v.otac || "").trim(), mj = (v.majka || "").trim();
  if (id === o || id === mj) return t("Grlo ne može biti sopstveni roditelj.", "An animal cannot be its own parent.");
  for (const [rod, n] of [[o, t("otac", "sire")], [mj, t("majka", "dam")]]) {          // roditelj ne sme biti potomak ovog grla
    const rid = rod && M.nadji(rod);
    if (rid && jePredak(id, rid)) return t(`${rod} ne može biti ${n} – on je potomak grla ${id}.`, `${rod} cannot be the ${n} – it is a descendant of ${id}.`);
  }
  if (v.status === "aktivno" && (r.status || "aktivno") !== "aktivno") { const pl = porukaLimita(1); if (pl) return pl; }
  const novi = { markica: mk, rfid, vrsta, rasa: normRasa(v.rasa), namena: izbori.length ? v.namena : "", autohtona: v.autohtona ? "1" : "", pol: v.pol,
    datum_rodjenja: dat ? fmtD(parsirajDatum(dat)) : "", otac: o, majka: mj, status: v.status, stado: (v.stado || "").trim(),
    poreklo: (v.poreklo || "").trim(), poreklo_od: (v.poreklo_od || "").trim(), napomena: String(v.napomena || "").trim().split(/\s+/).join(" "),
    udeo_krvi: String(v.udeo_krvi == null ? (r.udeo_krvi || "") : v.udeo_krvi).trim() };
  const nazivi = { markica: t("markica", "ear tag"), rfid: t("elektronski broj", "electronic ID"), vrsta: t("vrsta", "species"), rasa: t("rasa", "breed"),
    namena: t("namena", "purpose"), autohtona: t("autohtona", "native breed"), pol: t("pol", "sex"), datum_rodjenja: t("datum rođenja", "date of birth"),
    otac: t("otac", "sire"), majka: t("majka", "dam"), status: t("status", "status"), stado: t("stado", "herd"), poreklo: t("poreklo", "origin"),
    poreklo_od: t("poreklo od", "origin from"), napomena: t("napomena", "note"), udeo_krvi: t("udeo krvi", "breed share") };
  const promene = Object.keys(nazivi).filter(k => (r[k] || "") !== (novi[k] || "")).map(k => `${nazivi[k]}: ${r[k] || "–"} → ${novi[k] || "–"}`);
  if (!promene.length) return { id, promene: [], rasaGrla: 0 };
  if (norm(r.markica) !== norm(mk) && r.markica) r.stare_markice = [...stareLista(r), r.markica].join(", ");   // stara markica se pamti
  Object.assign(r, novi);
  dodaj(id, K().AUTO, { opis: t("Izmena podataka – ", "Details changed – ") + promene.join("; "), automatski: true });
  let rasaGrla = 0;
  if (celaRasa && novi.namena && cistaRasaTel(novi.rasa))                 // namena važi za celu rasu
    for (const x of S.grla)
      if (x !== r && x.status !== "obrisano" && vrstaKanon(x.vrsta) === vrstaKanon(vrsta) && _imeRase(x.rasa) === _imeRase(novi.rasa) && (x.namena || "") !== novi.namena) {
        dodaj(x.id, K().AUTO, { opis: t(`Namena rase: ${x.namena || "–"} → ${novi.namena}`, `Breed purpose: ${x.namena || "–"} → ${novi.namena}`), automatski: true });
        x.namena = novi.namena; rasaGrla++;
      }
  zabelezi(t("Izmenjeno grlo: ", "Animal edited: ") + id);
  osveziModel();
  return { id, promene, rasaGrla };
}
// da li je a predak grla x (preko M.P: id -> [otac, majka])
function jePredak(a, x, vidjeno = new Set()) {
  for (const r of (M.P[x] || [])) {
    if (!r || vidjeno.has(r)) continue;
    if (r === a) return true;
    vidjeno.add(r);
    if (jePredak(a, r, vidjeno)) return true;
  }
  return false;
}
// koliko drugih grla iste rase ima drugačiju namenu (za pitanje pre čuvanja)
function drugaNamenaRase(id, vrsta, rasa, namena) {
  if (!namena || !cistaRasaTel(rasa)) return 0;
  return S.grla.filter(x => x.id !== id && x.status !== "obrisano" && vrstaKanon(x.vrsta) === vrstaKanon(vrstaNorm(vrsta) || vrsta) && _imeRase(x.rasa) === _imeRase(normRasa(rasa)) && (x.namena || "") !== namena).length;
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
  return x.toLocaleString(t("sr-Latn-RS", "en-GB"), { maximumFractionDigits: dec, minimumFractionDigits: 0 });
}
const zapisBroja = x => String(Math.round(x * 100) / 100);
// mlečnost samo za ženke goveda, ovaca i koza koje nisu tovne rase (svinje, konji i tovna grla nemaju mlečnost)
function muznaVrsta(a) { return !!a && a.pol === "z" && !a.osnivac && nameneZa(a.vrsta).join() === K().NAMENE_MALI.join() && a.namena !== K().NAMENE_MALI[1]; }
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
    dodaj(p.grlo, tip, { opis: (tip === k.NAPOMENA && p.tip && p.tip !== k.NAPOMENA ? p.tip + ": " : "") + (p.tekst || (t("urađeno po podsetniku", "done as reminded"))), datum: d });
  }
  const pon = parseInt(p.ponavljanje || "0", 10) || 0;
  if (pon) {
    let sl = dodajDane(parsirajDatum(p.datum) || danas(), pon);
    while (sl <= danas()) sl = dodajDane(sl, pon);
    S.podsetnici.push({ grlo: p.grlo || "", datum: fmtD(sl), tip: p.tip, tekst: p.tekst, ponavljanje: String(pon), gotovo: "", uneto: sada(), vreme: p.vreme || "" });
  }
  zabelezi((t("Urađeno: ", "Done: ")) + (p.tip || "") + (p.grlo ? ` – ${p.grlo}` : ""));
}
function podsetnikOdlozi(p, dana) {
  const d = dodajDane(new Date(Math.max(parsirajDatum(p.datum) || danas(), danas())), dana);
  p.datum = fmtD(d);
  zabelezi((t("Podsetnik odložen za ", "Reminder postponed to ")) + p.datum + (p.grlo ? ` – ${p.grlo}` : ""));
}
function noviPodsetnik(grlo, datum, tip, tekst, ponavljanje, vreme) {
  S.podsetnici.push({ grlo: grlo || "", datum, tip, tekst: tekst || "", ponavljanje: ponavljanje ? String(ponavljanje) : "", gotovo: "", uneto: sada(), vreme: normVreme(vreme) });
  zabelezi((t("Novi podsetnik: ", "New reminder: ")) + tip + (grlo ? ` – ${grlo}` : ""));
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
  if (!obj || obj.format !== "farmer-telefon") throw new Error(t("Ovo nije HerdDoc fajl za telefon.", "This is not a HerdDoc file for the phone."));
  S.jezik = jezikTelefona(obj.jezik);
  S.prag = +obj.prag || 0.0625;
  S.grav = gravNaJeziku(obj.gravidnost || null);
  S.grla = (obj.grla || []).map(normalizovan); S.istorija = (obj.istorija || []).map(normalizovan); S.podsetnici = (obj.podsetnici || []).map(normalizovan);
  S.osnova = JSON.parse(JSON.stringify({ grla: S.grla, istorija: S.istorija, podsetnici: S.podsetnici }));
  S.izvoz = { id: obj.id, datum: obj.izvezeno, stada: obj.stada || [] };
  S.licenca = obj.licenca || null;      // paket licence sa računara (telefon ne kupuje posebno)
  S.vrste = Array.isArray(obj.vrste) ? obj.vrste : [];
  S.rase = Array.isArray(obj.rase) ? obj.rase : [];
  S.promene = [];
  osveziModel();
}
// izabrani jezik telefona ostaje zauvek; dok ga korisnik ne izabere, telefon preuzima jezik računara
const jeJezik = j => JEZICI_TEL.some(x => x[0] === j);
function jezikTelefona(jezikRacunara) {
  if (jeJezik(S.jezikIzabran)) return S.jezikIzabran;
  return jeJezik(jezikRacunara) ? jezikRacunara : "en";
}
function gravNaJeziku(g) {
  if (!g) return null;
  return Object.fromEntries(Object.entries(g).map(([k, v]) => [prevediVr(k), [prevediVr(v[0]), prevediVr(v[1])].concat(v.slice(2))]));
}
function izaberiJezik(j) {
  if (!jeJezik(j)) return;
  S.jezik = j; S.jezikIzabran = j;
  // podaci (događaji, vrste, poreklo, namena…) se prevode na novi jezik, da se poklope sa nazivima u aplikaciji
  S.grla = S.grla.map(normalizovan); S.istorija = S.istorija.map(normalizovan); S.podsetnici = S.podsetnici.map(normalizovan);
  S.grav = gravNaJeziku(S.grav);
  sacuvaj();
  if (typeof osveziModel === "function") osveziModel();
}
function paketZaRacunar() {
  return { format: "farmer-telefon-povratak", verzija: 1, jezik: S.jezik, napravljeno: sada(), izvoz_id: S.izvoz ? S.izvoz.id : null,
    osnova: S.osnova || { grla: [], istorija: [], podsetnici: [] }, grla: S.grla, istorija: S.istorija, podsetnici: S.podsetnici, promene: S.promene,
    slike: slikeZa(S.istorija) };
}
// slike (iz S.slike) koje pominju dati zapisi istorije – idu računaru uz zapise
function slikeZa(zapisi) {
  const o = {};
  for (const z of zapisi || []) for (const ime of String((z && z.fajl) || "").split("|")) if (ime && S.slike && S.slike[ime]) o[ime] = S.slike[ime];
  return o;
}
// slika sa kamere/galerije -> JPEG najviše 1600 px (da stane u memoriju i prenos)
function smanjiSliku(fajl, maks = 1600, kvalitet = 0.78) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onerror = () => rej(r.error);
    r.onload = () => {
      const img = new Image();
      img.onerror = () => rej(new Error("slika"));
      img.onload = () => {
        const k = Math.min(1, maks / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        res(c.toDataURL("image/jpeg", kvalitet));
      };
      img.src = r.result;
    };
    r.readAsDataURL(fajl);
  });
}

if (typeof module !== "undefined") module.exports = { S, K, Model, M: () => M, osveziModel, parsirajDatum, fmtD, pct, procena, nazivi, rasaPotomka, normRasa, namenaRase, danaUnapred, obavSat, normVreme, izmeniGrlo, drugaNamenaRase, rucneOsobine, autoOsobine, procitajOcenu, procitajOcene, zapisiOcene, spojiOcene, korisnik, oceneGrla, sacuvajOcene, vrednostiVrste, zvezdice, vimeSeOcenjuje, procitajUdeo, zapisiUdeo, sastav, generacijaUkrstanja, sastavPotomka, odstupanje, tekstUdela, programRase, sacuvajCiljRase, paroviZaCilj, kategorijeFin, brojIznos, fmtNovac, sacuvajFin, obrisiFin, periodFin, finUPeriodu, zbirFin, PRIHOD, TROSAK, sacuvajRasu, skloniRasu, grlaRase, primeriVrsta, ocistiVrstu, sacuvajVrstu, skloniVrstu, mojeRase, raseZaVrstu, mojaRasa,
  vrstaNorm, upisiDogadjaj, rodjenje, upisUListu, novoGrlo, teraSe, neTeraSe, oznaciNeuspelo, podsetnikUradjen, podsetnikOdlozi, noviPodsetnik,
  obavestenja, cekajuPorodjaj, cekajuMindjusu, granicePorodjaja, opisIshoda, partneri, karenca, opisKarence, ucitajSaRacunara, paketZaRacunar,
  leglo, danas, dodajDane, istorijaZa, markicaZauzeta, roditeljiParenja, podaciLegla, sortKey };
