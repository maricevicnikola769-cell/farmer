"""Rodoslov: račun srodstva, inbridinga i udela gena (Model) i procena rizika parenja."""
from datetime import date

from osnova import EN
from jezik import T
from podaci import isti_broj_citaca, nazivi, norm, parsiraj_datum, sort_key, stare_lista
from izgled import BAD, OK, WARN


# =============================================================== racunanje

class Model:
    def __init__(self, redovi):
        self.A, self.P, self.by_mark, self.warn = {}, {}, {}, []
        self._gen, self._kin, self._inbr, self._norm = {}, {}, {}, (0, {})
        for rb, r in enumerate(redovi):
            jid = r["id"].strip()
            if jid in self.A:
                self.warn.append((T(f"Oznaka {jid} je upisana više puta.", f"Tag {jid} is entered more than once.")))
                continue
            self.A[jid] = dict(id=jid, markica=r.get("markica", ""), rfid=r.get("rfid", ""), vrsta=r.get("vrsta") or (T("drugo", "other")),
                               rasa=r.get("rasa", ""), namena=r.get("namena", ""), autohtona=r.get("autohtona", ""), pol=r.get("pol") or None,
                               datum=parsiraj_datum(r.get("datum_rodjenja")),
                               aktivno=r.get("status", "aktivno") == "aktivno", stado=r.get("stado", ""),
                               obrisano=r.get("status") == "obrisano",
                               osnivac=False, _otac=r.get("otac", ""), _majka=r.get("majka", ""),
                               stare=stare_lista(r), poreklo=r.get("poreklo", "").strip(),
                               poreklo_od=r.get("poreklo_od", "").strip(), rb=rb, uneto=r.get("uneto", ""),
                               napomena=" ".join(str(r.get("napomena") or "").split()),
                               udeo=procitaj_udeo(r.get("udeo_krvi")))
            if r.get("markica"):
                n = norm(r["markica"])
                if n in self.by_mark and self.by_mark[n] != jid:
                    self.warn.append((T(f"Markica {r['markica']} je upisana i za {self.by_mark[n]} i za {jid}.", f"Ear tag {r['markica']} is entered for both {self.by_mark[n]} and {jid}.")))
                self.by_mark[n] = jid
            if r.get("rfid"):                     # elektronski broj (RFID) takođe nalazi grlo
                self.by_mark.setdefault(norm(r["rfid"]), jid)
        for a in list(self.A.values()):   # stari brojevi markica i dalje nalaze grlo
            for st in a.get("stare", []):
                self.by_mark.setdefault(norm(st), a["id"])
        for a in list(self.A.values()):
            self.P[a["id"]] = (self.nadji(a["_otac"]) or (a["_otac"] or None),
                               self.nadji(a["_majka"]) or (a["_majka"] or None))
        for jid, par in list(self.P.items()):
            for i, r in enumerate(par):
                if r and r not in self.A:
                    self.A[r] = dict(id=r, markica="", rfid="", vrsta=self.A[jid]["vrsta"], rasa="", namena="", autohtona="",
                                     pol="m" if i == 0 else "z", datum=None, aktivno=False, stado="",
                                     osnivac=True, obrisano=False, stare=[], poreklo="", poreklo_od="",
                                     rb=-1, uneto="", napomena="", udeo={})
                    self.P[r] = (None, None)
        for o, m in list(self.P.values()):
            if o and not self.A[o]["pol"]:
                self.A[o]["pol"] = "m"
            if m and not self.A[m]["pol"]:
                self.A[m]["pol"] = "z"
        # provere
        for jid, (o, m) in list(self.P.items()):
            if jid in (o, m):
                self.warn.append((T(f"{jid} je upisan kao sopstveni roditelj.", f"{jid} is entered as its own parent.")))
                self.P[jid] = (None, None)
        for jid in (list(self.P) if self._ima_krug() else ()):   # brza provera; sporo traženje samo kad krug postoji
            if jid in self.preci(jid):
                self.warn.append((T(f"{jid} je sam sebi predak – proveri roditelje "
                                 "(rodoslov ovog grla je privremeno zanemaren).", f"{jid} is its own ancestor – check the parents "
                                 "(this animal's pedigree is temporarily ignored).")))
                self.P[jid] = (None, None)
        for jid, (o, m) in self.P.items():
            a = self.A[jid]
            for r in (o, m):
                if not r:
                    continue
                p = self.A[r]
                if p["vrsta"] != a["vrsta"] and not p["osnivac"]:
                    self.warn.append((T(f"{jid} ({a['vrsta']}) ima roditelja {r} ({p['vrsta']}) – različite vrste.", f"{jid} ({a['vrsta']}) has parent {r} ({p['vrsta']}) – different species.")))
                if p["datum"] and a["datum"] and p["datum"] >= a["datum"]:
                    self.warn.append((T(f"{r} je rođen posle svog potomka {jid} – proveri datume.", f"{r} was born after its offspring {jid} – check the dates.")))
            if o and self.A[o]["pol"] == "z":
                self.warn.append((T(f"{o} je upisan kao otac grla {jid}, a označen je kao žensko.", f"{o} is entered as sire of {jid}, but is marked as female.")))
            if m and self.A[m]["pol"] == "m":
                self.warn.append((T(f"{m} je upisana kao majka grla {jid}, a označena je kao muško.", f"{m} is entered as dam of {jid}, but is marked as male.")))

    def _ima_krug(self):
        """Da li je neko grlo (preko roditelja) samo sebi predak – jedan prolaz kroz celo stado."""
        stanje = {}                                   # 1 = u obradi, 2 = gotovo
        for start in self.P:
            if start in stanje:
                continue
            stek = [(start, iter([r for r in self.P.get(start, ()) if r]))]
            stanje[start] = 1
            while stek:
                x, dalje = stek[-1]
                r = next(dalje, None)
                if r is None:
                    stanje[x] = 2
                    stek.pop()
                elif stanje.get(r) == 1:
                    return True
                elif r not in stanje:
                    stanje[r] = 1
                    stek.append((r, iter([q for q in self.P.get(r, ()) if q])))
        return False

    def nadji(self, t):
        t = str(t or "").strip()
        if not t:
            return None
        if t in self.A:
            return t
        n = norm(t)
        if n in self.by_mark:
            return self.by_mark[n]
        if self._norm[0] != len(self.A):              # indeks oznaka bez razmaka i velikih slova (pravi se jednom)
            ix = {}
            for k in self.A:
                ix.setdefault(norm(k), k)
            self._norm = (len(self.A), ix)
        return self._norm[1].get(n)

    def nadji_citac(self, procitano):
        """Grlo za broj sa čitača minđuša (RFID): tačno poklapanje oznake, markice ili RFID broja,
        a inače upisana markica/RFID na kraju pročitanog broja (čitač često doda kod zemlje i nule)."""
        x = self.nadji(procitano)
        if x and not self.A[x]["osnivac"]:
            return x
        nadjena = [a["id"] for a in self.A.values() if not a["osnivac"]
                   and any(isti_broj_citaca(procitano, a.get(k)) for k in ("rfid", "markica"))]
        return nadjena[0] if len(nadjena) == 1 else None

    def grla(self, samo_aktivna=False, redosled="Poslednje upisana prvo"):
        """Grla za liste i pretragu (obrisana se ne prikazuju, ali ostaju u rodoslovu).
        Podrazumevano: poslednje upisano grlo je prvo, pa sve starija."""
        g = [a for a in self.A.values() if not a["osnivac"] and not a["obrisano"]
             and (a["aktivno"] or not samo_aktivna)]
        return self.poredaj(g, redosled)

    @staticmethod
    def poredaj(g, redosled="Poslednje upisana prvo"):
        if redosled == (T("Po oznaci", "By tag")):
            return sorted(g, key=lambda a: sort_key(a["id"]))
        if redosled == (T("Najmlađa prvo", "Youngest first")):
            return sorted(g, key=lambda a: (a["datum"] or date.min, a["rb"]), reverse=True)
        kljuc = lambda a: (a["uneto"] or "", a["rb"])     # bez datuma upisa -> mesto u tablici
        return sorted(g, key=kljuc, reverse=redosled != (T("Prvo upisana prvo", "First added first")))

    def obrisana(self):
        return self.poredaj([a for a in self.A.values() if a.get("obrisano")])

    def preci(self, x):
        rez, stek = set(), [x]
        while stek:
            for r in self.P.get(stek.pop(), (None, None)):
                if r and r not in rez:
                    rez.add(r)
                    stek.append(r)
        return rez

    def srodnici(self, ids):
        """Sva grla u srodstvu sa grlima ids: preci, potomci i bočni srodnici (braća, sestre, rođaci…)
        = preci i svi potomci tih predaka. Sama grla ids nisu u rezultatu."""
        ids = {x for x in ids if x in self.A}
        deca = {}
        for d, (o, m) in self.P.items():
            for r in (o, m):
                if r:
                    deca.setdefault(r, []).append(d)
        koreni = set(ids)
        for x in ids:
            koreni |= self.preci(x)
        rez, stek = set(koreni), list(koreni)
        while stek:
            for d in deca.get(stek.pop(), ()):
                if d not in rez:
                    rez.add(d)
                    stek.append(d)
        return rez - ids

    def gen(self, x):
        if x is None:
            return -1
        if x not in self._gen:
            o, m = self.P.get(x, (None, None))
            self._gen[x] = 1 + max(self.gen(o), self.gen(m))
        return self._gen[x]

    def kinship(self, a, b):
        if a is None or b is None:
            return 0.0
        if a == b:
            o, m = self.P.get(a, (None, None))
            return 0.5 * (1 + self.kinship(o, m))
        ga, gb = self.gen(a), self.gen(b)
        if ga > gb or (ga == gb and a > b):
            a, b = b, a
        k = (a, b)
        if k not in self._kin:
            o, m = self.P.get(b, (None, None))
            self._kin[k] = 0.5 * (self.kinship(a, o) + self.kinship(a, m))
        return self._kin[k]

    def doprinos(self, x, predak):
        """Koliki deo gena grlo x u proseku nosi od pretka (50% od roditelja, 25% od dede...)."""
        if x is None:
            return 0.0
        if x == predak:
            return 1.0
        if not hasattr(self, "_dop"):
            self._dop = {}
        k = (x, predak)
        if k not in self._dop:
            o, m = self.P.get(x, (None, None))
            self._dop[k] = 0.5 * (self.doprinos(o, predak) + self.doprinos(m, predak))
        return self._dop[k]

    def putanje(self, x):
        """Svi preci grla kroz SVE generacije: {predak: {generacija: broj puteva}}."""
        if not hasattr(self, "_put"):
            self._put = {}
        if x in self._put:
            return self._put[x]
        rez = {}
        for p in self.P.get(x, (None, None)):
            if not p:
                continue
            rez.setdefault(p, {})
            rez[p][1] = rez[p].get(1, 0) + 1
            for a, gens in self.putanje(p).items():
                d = rez.setdefault(a, {})
                for g, n in gens.items():
                    d[g + 1] = d.get(g + 1, 0) + n
        self._put[x] = rez
        return rez

    def kompletnost(self, x, do_gen):
        """Za svaku generaciju: koliko predaka je poznato od mogucih (2, 4, 8...)."""
        nivo, rez = [x], []
        for g in range(1, do_gen + 1):
            nivo = [p for y in nivo for p in self.P.get(y, (None, None)) if p]
            rez.append((g, len(nivo), 2 ** g))
            if not nivo:
                break
        return rez

    def udeli_predaka(self, x):
        return sorted(((self.doprinos(x, p), p) for p in self.preci(x)), key=lambda t: (-t[0], sort_key(t[1])))

    def inbr(self, x):
        if x not in self._inbr:
            o, m = self.P.get(x, (None, None))
            self._inbr[x] = self.kinship(o, m)
        return self._inbr[x]

    def r(self, a, b):
        return 2 * self.kinship(a, b) / ((1 + self.inbr(a)) * (1 + self.inbr(b))) ** 0.5

    def muzjaci_u_stadu(self, x, min_meseci=6):
        """Mužjaci iste vrste koji su u zapatu u istom stadu kao grlo x (pušteni sa ženkama) – oni je pare.
        Mladi mužjaci (manje od 6 meseci) se ne računaju."""
        a = self.A.get(x)
        if not a or not a.get("stado"):
            return []
        danas = date.today()
        rez = []
        for b in self.A.values():
            if b is a or b["osnivac"] or b.get("obrisano") or not b["aktivno"] or b["pol"] != "m":
                continue
            if b["stado"] != a["stado"] or b["vrsta"] != a["vrsta"]:
                continue
            if b["datum"] and (danas.year - b["datum"].year) * 12 + danas.month - b["datum"].month < min_meseci:
                continue
            rez.append(b["id"])
        return sorted(rez, key=sort_key)

    def odnos(self, a, b):
        oa, ma = self.P.get(a, (None, None))
        ob, mb = self.P.get(b, (None, None))
        if a in (ob, mb) or b in (oa, ma):
            return (T("roditelj i potomak", "parent–offspring"))
        if oa and ma and oa == ob and ma == mb:
            return (T("puni brat / sestra", "full sibling"))
        if (oa and oa == ob) or (ma and ma == mb):
            return (T("polubrat / polusestra", "half sibling"))
        if a in self.preci(b) or b in self.preci(a):
            return (T("predak i potomak", "ancestor and descendant"))
        r = self.r(a, b)
        return ((T("blisko srodni", "closely related")) if r >= 0.2 else (T("dalji rod", "distant relatives")) if r >= 0.06
                else (T("daleko srodni", "very distantly related")) if r > 0 else (T("nesrodni", "unrelated")))

    # ---------------------------------------------------------- udeo krvi (razvoj nove rase)
    def sastav(self, x):
        """Udeo krvi grla po rasama {rasa: deo od 1}; "?" = nepoznato. Čistokrvno grlo bez roditelja = 100 % svoje rase;
        potomak = prosek roditelja; ručno upisan udeo (osnivač) ima prednost. Nepoznat deo popunjava sopstvena čista rasa."""
        if x is None:
            return {NEPOZNATO: 1.0}
        if not hasattr(self, "_sast"):
            self._sast = {}
        if x in self._sast:
            return self._sast[x]
        a = self.A.get(x) or {}
        if a.get("udeo"):
            rez = dict(a["udeo"])
        else:
            o, m = self.P.get(x, (None, None))
            rez = {}
            if o or m:
                for p in (o, m):
                    for k, v in self.sastav(p).items():
                        rez[k] = rez.get(k, 0.0) + v / 2
            cista = cista_rasa(a.get("rasa", ""))
            nep = rez.pop(NEPOZNATO, 0.0) if rez else 1.0
            if nep > 1e-9:
                if cista:
                    rez[cista] = rez.get(cista, 0.0) + nep
                else:
                    rez[NEPOZNATO] = nep
        self._sast[x] = rez
        return rez

    def generacija_ukrstanja(self, x):
        """(oznaka, broj): čistokrvno (0), F1, F2…, povratno ukrštanje, ukršteno (osnivač) ili nepoznato."""
        if not hasattr(self, "_gu"):
            self._gu = {}
        if x in self._gu:
            return self._gu[x]
        s = self.sastav(x)
        if s.get(NEPOZNATO, 0) >= 0.5:
            rez = (T("nepoznato", "unknown"), None)
        elif max(s.values()) >= 0.999:
            rez = (T("čistokrvno", "purebred"), 0)
        else:
            o, m = self.P.get(x, (None, None))
            go = self.generacija_ukrstanja(o)[1] if o else None
            gm = self.generacija_ukrstanja(m)[1] if m else None
            if go is None or gm is None:
                rez = (T("ukršteno", "crossbred"), None)
            elif go == 0 and gm == 0:
                rez = ("F1", 1)
            elif go == 0 or gm == 0:
                rez = (T("povratno ukrštanje", "backcross"), max(go, gm) + 1)
            else:
                rez = (f"F{max(go, gm) + 1}", max(go, gm) + 1)
        self._gu[x] = rez
        return rez

    def pol_naziv(self, x):
        a = self.A[x]
        n = nazivi(a["vrsta"])
        return {"m": n[0], "z": n[1]}.get(a["pol"], (T("pol nepoznat", "sex unknown")))


NEPOZNATO = "?"


def _je_melez(rasa):
    r = " ".join(str(rasa or "").split()).lower()
    return (not r or r.startswith(("hibrid", "hybrid", "melez", "crossbred", "mešanac", "mesanac")) or "×" in r
            or " x " in f" {r} ")


def cista_rasa(rasa):
    """Naziv rase malim slovima ako je to čista rasa (ne hibrid / melez / prazno), inače ""."""
    return "" if _je_melez(rasa) else " ".join(str(rasa).split()).lower()


def procitaj_udeo(tekst):
    """'romanovska=50;pramenka=50' (ili 'romanovska 50%, pramenka 50') -> {rasa: deo od 1}. Neispravno -> {}."""
    import re
    rez = {}
    for deo in re.split(r";|\n|,(?=\s*[^\d\s])", str(tekst or "")):
        mt = re.match(r"^\s*(.+?)\s*[=:]?\s*(\d+(?:[.,]\d+)?)\s*%?\s*$", deo)
        if not mt:
            continue
        ime = " ".join(mt.group(1).strip(" =:").split()).lower()
        broj = float(mt.group(2).replace(",", "."))
        if ime and broj > 0:
            rez[ime] = rez.get(ime, 0.0) + broj
    ukupno = sum(rez.values())
    if not rez or ukupno > 100.5:
        return {}
    rez = {k: v / 100 for k, v in rez.items()}
    if ukupno < 99.5:
        rez[NEPOZNATO] = (100 - ukupno) / 100
    return rez


def zapisi_udeo(sastav):
    """{rasa: deo} -> 'rasa=50;rasa2=50' (bez nepoznatog dela)."""
    return ";".join(f"{k}={round(v * 100, 2):g}" for k, v in sorted(sastav.items(), key=lambda t: -t[1]) if k != NEPOZNATO)


def sastav_potomka(a, b):
    rez = {}
    for s in (a, b):
        for k, v in s.items():
            rez[k] = rez.get(k, 0.0) + v / 2
    return rez


def odstupanje(sastav, cilj):
    """Koliko se udeo krvi razlikuje od cilja (0 = isto, 1 = potpuno drugačije); nepoznat deo se računa kao razlika."""
    if not cilj:
        return None
    kljucevi = set(sastav) | set(cilj)
    return sum(abs(sastav.get(k, 0.0) - (cilj.get(k, 0.0) if k != NEPOZNATO else 0.0)) for k in kljucevi) / 2


def tekst_udela(sastav, pct_f, najvise=4):
    """'romanovska 62,5% · pramenka 37,5%' (najveći udeli prvi)."""
    redom = sorted(((v, k) for k, v in sastav.items() if v > 1e-9), key=lambda t: (t[1] == NEPOZNATO, -t[0], t[1]))
    delovi = [f"{(T('nepoznato', 'unknown') if k == NEPOZNATO else k)} {pct_f(v)}" for v, k in redom[:najvise]]
    if len(redom) > najvise:
        delovi.append(T("ostalo", "other") + " " + pct_f(sum(v for v, _ in redom[najvise:])))
    return " · ".join(delovi)


def procena(f, prag):
    if f == 0:
        return (T("odlično", "excellent")), OK
    if f < prag / 2:
        return (T("dobro", "good")), OK
    if f <= prag:
        return (T("prihvatljivo", "acceptable")), WARN
    if f < 0.125:
        return (T("rizično", "risky")), BAD
    return (T("ne preporučuje se", "not recommended")), BAD
