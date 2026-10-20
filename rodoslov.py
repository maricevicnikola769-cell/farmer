"""Rodoslov: račun srodstva, inbridinga i udela gena (Model) i procena rizika parenja."""
from datetime import date

from osnova import EN
from podaci import nazivi, norm, parsiraj_datum, sort_key, stare_lista
from izgled import BAD, OK, WARN


# =============================================================== racunanje

class Model:
    def __init__(self, redovi):
        self.A, self.P, self.by_mark, self.warn = {}, {}, {}, []
        self._gen, self._kin = {}, {}
        for rb, r in enumerate(redovi):
            jid = r["id"].strip()
            if jid in self.A:
                self.warn.append((f"Tag {jid} is entered more than once." if EN else f"Oznaka {jid} je upisana više puta."))
                continue
            self.A[jid] = dict(id=jid, markica=r.get("markica", ""), vrsta=r.get("vrsta") or ("other" if EN else "drugo"),
                               rasa=r.get("rasa", ""), pol=r.get("pol") or None,
                               datum=parsiraj_datum(r.get("datum_rodjenja")),
                               aktivno=r.get("status", "aktivno") == "aktivno", stado=r.get("stado", ""),
                               obrisano=r.get("status") == "obrisano",
                               osnivac=False, _otac=r.get("otac", ""), _majka=r.get("majka", ""),
                               stare=stare_lista(r), poreklo=r.get("poreklo", "").strip(),
                               poreklo_od=r.get("poreklo_od", "").strip(), rb=rb, uneto=r.get("uneto", ""))
            if r.get("markica"):
                n = norm(r["markica"])
                if n in self.by_mark and self.by_mark[n] != jid:
                    self.warn.append((f"Ear tag {r['markica']} is entered for both {self.by_mark[n]} and {jid}." if EN else f"Markica {r['markica']} je upisana i za {self.by_mark[n]} i za {jid}."))
                self.by_mark[n] = jid
        for a in list(self.A.values()):   # stari brojevi markica i dalje nalaze grlo
            for st in a.get("stare", []):
                self.by_mark.setdefault(norm(st), a["id"])
        for a in list(self.A.values()):
            self.P[a["id"]] = (self.nadji(a["_otac"]) or (a["_otac"] or None),
                               self.nadji(a["_majka"]) or (a["_majka"] or None))
        for jid, par in list(self.P.items()):
            for i, r in enumerate(par):
                if r and r not in self.A:
                    self.A[r] = dict(id=r, markica="", vrsta=self.A[jid]["vrsta"], rasa="",
                                     pol="m" if i == 0 else "z", datum=None, aktivno=False, stado="",
                                     osnivac=True, obrisano=False, stare=[], poreklo="", poreklo_od="",
                                     rb=-1, uneto="")
                    self.P[r] = (None, None)
        for o, m in list(self.P.values()):
            if o and not self.A[o]["pol"]:
                self.A[o]["pol"] = "m"
            if m and not self.A[m]["pol"]:
                self.A[m]["pol"] = "z"
        # provere
        for jid, (o, m) in list(self.P.items()):
            if jid in (o, m):
                self.warn.append((f"{jid} is entered as its own parent." if EN else f"{jid} je upisan kao sopstveni roditelj."))
                self.P[jid] = (None, None)
        for jid in list(self.P):
            if jid in self.preci(jid):
                self.warn.append((f"{jid} is its own ancestor – check the parents "
                                 "(this animal's pedigree is temporarily ignored)." if EN else f"{jid} je sam sebi predak – proveri roditelje "
                                 "(rodoslov ovog grla je privremeno zanemaren)."))
                self.P[jid] = (None, None)
        for jid, (o, m) in self.P.items():
            a = self.A[jid]
            for r in (o, m):
                if not r:
                    continue
                p = self.A[r]
                if p["vrsta"] != a["vrsta"] and not p["osnivac"]:
                    self.warn.append((f"{jid} ({a['vrsta']}) has parent {r} ({p['vrsta']}) – different species." if EN else f"{jid} ({a['vrsta']}) ima roditelja {r} ({p['vrsta']}) – različite vrste."))
                if p["datum"] and a["datum"] and p["datum"] >= a["datum"]:
                    self.warn.append((f"{r} was born after its offspring {jid} – check the dates." if EN else f"{r} je rođen posle svog potomka {jid} – proveri datume."))
            if o and self.A[o]["pol"] == "z":
                self.warn.append((f"{o} is entered as sire of {jid}, but is marked as female." if EN else f"{o} je upisan kao otac grla {jid}, a označen je kao žensko."))
            if m and self.A[m]["pol"] == "m":
                self.warn.append((f"{m} is entered as dam of {jid}, but is marked as male." if EN else f"{m} je upisana kao majka grla {jid}, a označena je kao muško."))

    def nadji(self, t):
        t = str(t or "").strip()
        if not t:
            return None
        if t in self.A:
            return t
        n = norm(t)
        if n in self.by_mark:
            return self.by_mark[n]
        for k in self.A:
            if norm(k) == n:
                return k
        return None

    def grla(self, samo_aktivna=False, redosled="Poslednje upisana prvo"):
        """Grla za liste i pretragu (obrisana se ne prikazuju, ali ostaju u rodoslovu).
        Podrazumevano: poslednje upisano grlo je prvo, pa sve starija."""
        g = [a for a in self.A.values() if not a["osnivac"] and not a["obrisano"]
             and (a["aktivno"] or not samo_aktivna)]
        return self.poredaj(g, redosled)

    @staticmethod
    def poredaj(g, redosled="Poslednje upisana prvo"):
        if redosled == ("By tag" if EN else "Po oznaci"):
            return sorted(g, key=lambda a: sort_key(a["id"]))
        if redosled == ("Youngest first" if EN else "Najmlađa prvo"):
            return sorted(g, key=lambda a: (a["datum"] or date.min, a["rb"]), reverse=True)
        kljuc = lambda a: (a["uneto"] or "", a["rb"])     # bez datuma upisa -> mesto u tablici
        return sorted(g, key=kljuc, reverse=redosled != ("First added first" if EN else "Prvo upisana prvo"))

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
        o, m = self.P.get(x, (None, None))
        return self.kinship(o, m)

    def r(self, a, b):
        return 2 * self.kinship(a, b) / ((1 + self.inbr(a)) * (1 + self.inbr(b))) ** 0.5

    def odnos(self, a, b):
        oa, ma = self.P.get(a, (None, None))
        ob, mb = self.P.get(b, (None, None))
        if a in (ob, mb) or b in (oa, ma):
            return ("parent–offspring" if EN else "roditelj i potomak")
        if oa and ma and oa == ob and ma == mb:
            return ("full sibling" if EN else "puni brat / sestra")
        if (oa and oa == ob) or (ma and ma == mb):
            return ("half sibling" if EN else "polubrat / polusestra")
        if a in self.preci(b) or b in self.preci(a):
            return ("ancestor and descendant" if EN else "predak i potomak")
        r = self.r(a, b)
        return (("closely related" if EN else "blisko srodni") if r >= 0.2 else ("distant relatives" if EN else "dalji rod") if r >= 0.06
                else ("very distantly related" if EN else "daleko srodni") if r > 0 else ("unrelated" if EN else "nesrodni"))

    def pol_naziv(self, x):
        a = self.A[x]
        n = nazivi(a["vrsta"])
        return {"m": n[0], "z": n[1]}.get(a["pol"], ("sex unknown" if EN else "pol nepoznat"))


def procena(f, prag):
    if f == 0:
        return ("excellent" if EN else "odlično"), OK
    if f < prag / 2:
        return ("good" if EN else "dobro"), OK
    if f <= prag:
        return ("acceptable" if EN else "prihvatljivo"), WARN
    if f < 0.125:
        return ("risky" if EN else "rizično"), BAD
    return ("not recommended" if EN else "ne preporučuje se"), BAD
