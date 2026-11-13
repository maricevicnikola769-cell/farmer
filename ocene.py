"""Ocena grla (1–5 ★): ručne ocene (karakter, građa, noge, vime, majčinska svojstva) i automatske
(prirast iz merenja težine, plodnost iz upisanih mladih, zdravlje iz lečenja) – i rang lista za izbor priplodnih grla.

Ručne ocene se čuvaju u koloni "ocena" tablice: "karakter=4;gradja=3;noge=5@2026-11-11" (ide i na telefon).
Automatske se računaju u odnosu na ostala grla iste vrste u zapatu (najboljih 20 % = 5 ★).
"""
import re
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

import jezik
from jezik import T
from izgled import BAD, BRAND, INK2, SURF, WARN
from podaci import parsiraj_datum, sort_key
import prirast as prirast_mod
from namena_rase import vime_se_ocenjuje


def rucne_osobine():
    """(ključ, naziv, opis, samo_zenke)"""
    return [("karakter", T("Karakter (ćud)", "Temperament"), T("5 = mirno i lako za rad · 1 = agresivno ili plašljivo", "5 = calm and easy to handle · 1 = aggressive or nervous"), False),
            ("gradja", T("Građa (eksterijer)", "Conformation"), T("5 = odlična građa za rasu · 1 = loša", "5 = excellent for the breed · 1 = poor"), False),
            ("noge", T("Noge i papci", "Legs and feet"), T("5 = zdrave, pravilne · 1 = česti problemi", "5 = sound, correct · 1 = frequent problems"), False),
            ("vime", T("Vime", "Udder"), T("5 = pravilno, zdravo · 1 = loše", "5 = well formed, healthy · 1 = poor"), True),
            ("majka", T("Majčinska svojstva", "Mothering ability"), T("5 = brine o mladima, lako se porađa · 1 = odbacuje mlade", "5 = cares for young, easy births · 1 = rejects young"), True)]


def kratki_nazivi():
    return {"karakter": T("Karakter", "Temper"), "gradja": T("Građa", "Conform."), "noge": T("Noge", "Legs"), "vime": T("Vime", "Udder"),
            "majka": T("Majka", "Mothering"), "prirast": T("Prirast", "Gain"), "plodnost": T("Plodnost", "Fertility"), "zdravlje": T("Zdravlje", "Health")}


def auto_osobine():
    return [("prirast", T("Prirast", "Weight gain")), ("plodnost", T("Plodnost", "Fertility")), ("zdravlje", T("Zdravlje", "Health"))]


def _jedna_ocena(tekst):
    """'karakter=4;gradja=3@2026-11-11' -> ({'karakter': 4, 'gradja': 3}, '2026-11-11')."""
    tekst = str(tekst or "")
    dat = ""
    if "@" in tekst:
        tekst, dat = tekst.rsplit("@", 1)
    rez = {}
    for deo in tekst.split(";"):
        if "=" in deo:
            k, v = deo.split("=", 1)
            try:
                v = int(v)
            except ValueError:
                continue
            if 1 <= v <= 5:
                rez[k.strip()] = v
    return rez, dat.strip()


def cisto_ime(ime):
    """Ime ocenjivača bez znakova koji se koriste u zapisu ocene."""
    return " ".join(re.sub(r"[|:;=@]", " ", str(ime or "")).split())[:60]


def procitaj_ocene(tekst):
    """Ocene svih ocenjivača: 'Marko Marković:karakter=4@2026-11-12|Jovan Jović:karakter=5@…' -> {ime: (ocene, datum)}.
    Stari zapis bez imena ('karakter=4@…') ima ime ''."""
    rez = {}
    for seg in str(tekst or "").split("|"):
        seg = seg.strip()
        if not seg:
            continue
        ime, dv, jed = "", seg.find(":"), seg.find("=")
        if dv != -1 and (jed == -1 or dv < jed):
            ime, seg = cisto_ime(seg[:dv]), seg[dv + 1:]
        oc, dat = _jedna_ocena(seg)
        if oc:
            rez[ime] = (oc, dat)
    return rez


def zapisi_ocene(mapa):
    return "|".join((f"{cisto_ime(ime)}:" if cisto_ime(ime) else "") + zapisi_ocenu(oc, dat)
                    for ime, (oc, dat) in mapa.items() if oc)


def procitaj_ocenu(tekst):
    """Prosek svih ocenjivača: ({'karakter': 4.5, …}, poslednji datum)."""
    sve = procitaj_ocene(tekst)
    zbir = {}
    for oc, _ in sve.values():
        for k, v in oc.items():
            zbir.setdefault(k, []).append(v)
    dat = max((d for _, d in sve.values() if d), default="")
    return {k: round(sum(v) / len(v), 2) for k, v in zbir.items()}, dat


def spoji_ocene(baza, moja, njihova):
    """Spajanje ocena kad su ocenjivali na dva mesta: od 'njihova' se uzima sve, a od 'moja' ono što je
    taj ocenjivač promenio u odnosu na 'baza' (svako menja samo svoju ocenu)."""
    B, Mo, rez = procitaj_ocene(baza), procitaj_ocene(moja), procitaj_ocene(njihova)
    for ime in set(B) | set(Mo):
        if Mo.get(ime) != B.get(ime):
            if ime in Mo:
                rez[ime] = Mo[ime]
            else:
                rez.pop(ime, None)
    return zapisi_ocene(rez)


def zapisi_ocenu(ocene, dat=None):
    if not ocene:
        return ""
    return ";".join(f"{k}={v}" for k, v in ocene.items()) + "@" + (dat or date.today().isoformat())


def zvezdice(n):
    if n is None:
        return "–"
    p = int(round(n))
    return "★" * p + "☆" * (5 - p)


def _rang_ocena(vrednost, sve, vise_bolje=True):
    """1–5 prema mestu među svim vrednostima iste vrste (najboljih 20 % = 5). Premalo podataka -> None."""
    if vrednost is None or len(sve) < 3:
        return None
    bolji = sum(1 for v in sve if (v > vrednost if vise_bolje else v < vrednost))
    udeo = bolji / len(sve)                 # 0 = najbolji
    return 5 - min(4, int(udeo * 5))


def broj_lecenja(istorija, x, dana=365):
    od = date.today() - timedelta(days=dana)
    leci = jezik.DOGADJAJI[4]
    return sum(1 for z in istorija.zapisi if z["grlo"] == x and z["dogadjaj"] == leci
               and (parsiraj_datum(z.get("datum")) or date.today()) >= od)


def zdravlje_ocena(n):
    return max(1, 5 - n)                    # 0 lečenja = 5, 1 = 4 … 4 i više = 1


def velicina_legla(m, x):
    """Prosečan broj mladih po porođaju (iz upisanih mladih) ili None."""
    po_danu = {}
    for y, (o, mj) in m.P.items():
        if mj == x and y in m.A and not m.A[y]["osnivac"] and m.A[y].get("datum"):
            po_danu[m.A[y]["datum"]] = po_danu.get(m.A[y]["datum"], 0) + 1
    return sum(po_danu.values()) / len(po_danu) if po_danu else None


class OceneDeo:
    """Ocene grla: na kartonu, prozor za ocenjivanje i rang lista."""

    def _vrednosti_vrste(self, vrsta):
        """Prirast i veličina legla za sva aktivna grla iste vrste (za poređenje)."""
        kes = getattr(self, "_oc_kes", None)
        kljuc = (id(self.model), len(self.ist.zapisi), vrsta)
        if kes and kes[0] == kljuc:
            return kes[1]
        m = self.model
        pr, le = {}, {}
        for a in m.grla(True):
            if a["vrsta"] != vrsta:
                continue
            s = prirast_mod.stat(self.ist, a["id"])
            if s["prosek"] is not None:
                pr[a["id"]] = s["prosek"]
            if a["pol"] == "z":
                v = velicina_legla(m, a["id"])
                if v is not None:
                    le[a["id"]] = v
        self._oc_kes = (kljuc, (pr, le))
        return pr, le

    def ocene_grla(self, x):
        """{'rucne': {...}, 'datum': str, 'auto': {kljuc: (ocena|None, opis)}, 'ukupno': float|None}"""
        m = self.model
        a = m.A[x]
        red = self.red_za(x) or {}
        rucne, dat = procitaj_ocenu(red.get("ocena"))
        if not vime_se_ocenjuje(a):                 # vime: samo ženke koje nisu mlečne rase
            rucne.pop("vime", None)
        pr, le = self._vrednosti_vrste(a["vrsta"])
        auto = {}
        p = pr.get(x)
        auto["prirast"] = (_rang_ocena(p, list(pr.values())), prirast_mod.fmt_g(p) if p is not None else T("nema merenja", "no weighings"))
        if a["pol"] == "z":
            v = le.get(x)
            auto["plodnost"] = (_rang_ocena(v, list(le.values())),
                                (f"{v:.1f}".replace(".", "," if not jezik.EN else ".") + T(" mladih po porođaju", " young per birth")) if v is not None
                                else T("nema upisanih mladih", "no recorded young"))
        n = broj_lecenja(self.ist, x)
        auto["zdravlje"] = (zdravlje_ocena(n), T(f"{n} lečenja za 12 meseci", f"{n} treatments in 12 months"))
        # ukupna ocena: ručne + prirast/plodnost; zdravlje se uračunava samo uz njih (samo "nije lečeno" nije razlog za vrh liste)
        sve = list(rucne.values()) + [o for k, (o, _) in auto.items() if o is not None and k != "zdravlje"]
        if sve and auto["zdravlje"][0] is not None:
            sve.append(auto["zdravlje"][0])
        return dict(rucne=rucne, datum=dat, auto=auto, ukupno=(sum(sve) / len(sve)) if sve else None)

    # ---------------------------------------------------------- karton
    def ocene_na_kartonu(self, parent, x):
        o = self.ocene_grla(x)
        gl = tk.Frame(parent, bg=SURF)
        gl.pack(anchor="w", fill="x", pady=(18, 6))
        self.lbl(gl, T("Ocena grla", "Animal score"), 10, "bold").pack(side="left")
        if o["ukupno"] is not None:
            self.lbl(gl, f"  {zvezdice(o['ukupno'])}  {o['ukupno']:.1f}".replace(".", "," if not jezik.EN else "."), 11, "bold",
                     fg=WARN).pack(side="left")
        lk = self.lbl(gl, T("Oceni  ›", "Score  ›"), 9, "bold", fg=BRAND, cursor="hand2")
        lk.pack(side="left", padx=14)
        lk.bind("<Button-1>", lambda e: self.oceni_prozor(x))
        n_oc = len(procitaj_ocene((self.red_za(x) or {}).get("ocena")))
        if n_oc > 1:
            self.lbl(gl, T(f"prosek {n_oc} ocenjivača", f"average of {n_oc} scorers"), 9, fg=INK2).pack(side="left")
        fr = tk.Frame(parent, bg=SURF)
        fr.pack(anchor="w", fill="x")
        r = 0
        for k, naziv, _, samo_z in rucne_osobine():
            if k in o["rucne"]:
                self.lbl(fr, naziv, 9, fg=INK2).grid(row=r, column=0, sticky="w", pady=1)
                self.lbl(fr, zvezdice(o["rucne"][k]) + (f"  {o['rucne'][k]:g}".replace(".", "," if not jezik.EN else ".")
                                                         if o["rucne"][k] != int(o["rucne"][k]) else ""), 10, fg=WARN).grid(row=r, column=1, sticky="w", padx=(14, 0))
                r += 1
        for k, naziv in auto_osobine():
            if k in o["auto"]:
                oc, opis = o["auto"][k]
                self.lbl(fr, naziv, 9, fg=INK2).grid(row=r, column=0, sticky="w", pady=1)
                self.lbl(fr, zvezdice(oc), 10, fg=WARN).grid(row=r, column=1, sticky="w", padx=(14, 0))
                self.lbl(fr, opis, 9, fg=INK2).grid(row=r, column=2, sticky="w", padx=(10, 0))
                r += 1
        if not o["rucne"]:
            self.lbl(parent, T("Karakter, građa, noge… još nisu ocenjeni – klikni „Oceni“.", "Temperament, conformation, legs… not scored yet – click “Score”."),
                     9, fg=INK2).pack(anchor="w", pady=(4, 0))

    # ---------------------------------------------------------- ocenjivanje
    def oceni_prozor(self, x, parent=None):
        m = self.model
        a = m.A[x]
        red = self.red_za(x)
        if red is None:
            return
        sve = procitaj_ocene(red.get("ocena"))
        v_ime = tk.StringVar(value=self.pod.get("korisnik", ""))
        stare = sve.get(cisto_ime(v_ime.get()), ({}, ""))[0]
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(T("Ocena grla", "Animal score"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T(f"Ocena – {x}", f"Score – {x}"), 15, "bold").grid(row=0, column=0, columnspan=3, sticky="w")
        self.lbl(b, T("Klikni na zvezdice (1 = loše, 5 = odlično). Klik na istu zvezdicu briše ocenu.",
                      "Click the stars (1 = poor, 5 = excellent). Clicking the same star clears the score."),
                 9, fg=INK2).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 6))
        fi = tk.Frame(b, bg=SURF)
        fi.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self.lbl(fi, T("Ocenjuje (ime i prezime) *", "Scored by (first and last name) *"), 9, "bold", fg=INK2).pack(side="left")
        ttk.Entry(fi, textvariable=v_ime, width=26, font=self.f(10)).pack(side="left", padx=(8, 0))
        drugi = {i: oc for i, (oc, _) in sve.items() if i != cisto_ime(v_ime.get())}
        if drugi:
            self.lbl(b, T("Ocenili su i: ", "Also scored by: ") + "; ".join(
                f"{i or T('ranije', 'earlier')} ({', '.join(f'{kratki_nazivi().get(k, k)} {v}' for k, v in oc.items())})" for i, oc in drugi.items()),
                9, fg=INK2, wraplength=460, justify="left").grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self.lbl(b, T("Svako ocenjuje za sebe – na kraju se računa prosek svih ocena.", "Everyone scores for themselves – the average of all scores counts."),
                 8, fg=INK2).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 6))
        greska = self.lbl(b, "", 9, "bold", fg=BAD)
        vr = {}
        r = 5
        for k, naziv, opis, samo_z in rucne_osobine():
            if samo_z and a["pol"] != "z":
                continue
            if k == "vime" and not vime_se_ocenjuje(a):
                continue
            vr[k] = tk.IntVar(value=stare.get(k, 0))
            self.lbl(b, naziv, 10, "bold").grid(row=r, column=0, sticky="w", pady=(6, 0))
            zv = tk.Frame(b, bg=SURF)
            zv.grid(row=r, column=1, sticky="w", padx=(16, 0), pady=(6, 0))
            labele = []

            def crtaj(k=k, labele=labele):
                for i, l in enumerate(labele):
                    l.config(text="★" if i < vr[k].get() else "☆", fg=WARN if i < vr[k].get() else INK2)

            def klik(i, k=k, crtaj=crtaj):
                vr[k].set(0 if vr[k].get() == i else i)
                crtaj()
            for i in range(1, 6):
                l = tk.Label(zv, text="☆", bg=SURF, fg=INK2, font=self.f(16), cursor="hand2")
                l.pack(side="left")
                l.bind("<Button-1>", lambda e, i=i, klik=klik: klik(i))
                labele.append(l)
            crtaj()
            self.lbl(b, opis, 8, fg=INK2).grid(row=r + 1, column=0, columnspan=3, sticky="w")
            r += 2
        o = self.ocene_grla(x)
        self.lbl(b, T("Računa program sam", "Calculated by the program"), 10, "bold").grid(row=r, column=0, sticky="w", pady=(14, 2))
        r += 1
        for k, naziv in auto_osobine():
            if k in o["auto"]:
                oc, op = o["auto"][k]
                self.lbl(b, naziv, 9, fg=INK2).grid(row=r, column=0, sticky="w")
                self.lbl(b, zvezdice(oc) + "   " + op, 9, fg=INK2).grid(row=r, column=1, columnspan=2, sticky="w", padx=(16, 0))
                r += 1
        self.lbl(b, T("Prirast i plodnost se porede sa ostalim grlima iste vrste u zapatu (najboljih 20 % = 5 ★).",
                      "Gain and fertility are compared with other animals of the same species in the herd (top 20 % = 5 ★)."),
                 8, fg=INK2, wraplength=440, justify="left").grid(row=r, column=0, columnspan=3, sticky="w", pady=(6, 0))
        r += 1

        def sacuvaj():
            ime = cisto_ime(v_ime.get())
            if len(ime.split()) < 2:
                greska.config(text=T("Upiši ime i prezime onoga ko ocenjuje.", "Enter the first and last name of the person scoring."))
                return
            self.pod["korisnik"] = ime
            self.sacuvaj_podesavanja()
            if hasattr(self, "postavi_korisnika"):
                self.postavi_korisnika(ime)
            nove = {k: v.get() for k, v in vr.items() if v.get()}
            mapa = procitaj_ocene(red.get("ocena", ""))
            staro = mapa.get(ime, ({}, ""))[0]
            if nove:
                mapa[ime] = (nove, date.today().isoformat())
            else:
                mapa.pop(ime, None)
            red["ocena"] = zapisi_ocene(mapa)
            if staro != nove:
                opis = ", ".join(f"{n} {nove[k]}" for k, n, _, _ in rucne_osobine() if k in nove) or T("obrisana", "cleared")
                self.ist.dodaj(x, jezik.AUTO, T(f"Ocena grla ({ime}): {opis}", f"Animal score ({ime}): {opis}"), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena(T(f"Ocena je sačuvana: {x}", f"Score saved: {x}"))
        greska.grid(row=r, column=0, columnspan=3, sticky="w", pady=(8, 0))
        r += 1
        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        self.btn(fb, T("Sačuvaj", "Save"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, parent or self.root)

    # ---------------------------------------------------------- rang lista
    def rang_prozor(self):
        m = self.model
        sva = [a for a in m.grla(True) if not a["osnivac"]]
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Rang grla po oceni", "Animals ranked by score"))
        win.transient(self.root)
        win.geometry("1120x640")
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=22, pady=18)
        self.lbl(b, T("⭐ Rang grla po oceni", "⭐ Animals ranked by score"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Najbolje ocenjena grla su na vrhu – pomoć pri izboru grla za priplod. Dvoklik otvara karton.",
                      "The best-scored animals are at the top – a help in choosing breeding stock. Double-click opens the card."),
                 9, fg=INK2).pack(anchor="w", pady=(2, 10))
        fil = tk.Frame(b, bg=SURF)
        fil.pack(fill="x", pady=(0, 8))
        vrste = [T("Sve vrste", "All species")] + sorted({a["vrsta"] for a in sva if a["vrsta"]})
        v_vr = tk.StringVar(value=vrste[0])
        v_pol = tk.StringVar(value=T("Sva grla", "All animals"))
        ttk.Combobox(fil, textvariable=v_vr, values=vrste, state="readonly", width=16, font=self.f(10)).pack(side="left")
        ttk.Combobox(fil, textvariable=v_pol, values=[T("Sva grla", "All animals"), T("Ženska", "Females"), T("Muška", "Males")],
                     state="readonly", width=12, font=self.f(10)).pack(side="left", padx=8)
        kn = kratki_nazivi()
        kol = [("g", T("Grlo", "Animal"), 110), ("pol", T("Pol", "Sex"), 70), ("uk", T("Ukupno", "Total"), 110)]
        kol += [(k, kn[k], 82) for k, _, _, _ in rucne_osobine()] + [(k, kn[k], 82) for k, _ in auto_osobine()]
        wrap, tv = self.tabela(b, kol, visina=18)
        wrap.pack(fill="both", expand=True)

        def popuni(*_):
            tv.delete(*tv.get_children())
            red_ = []
            for a in sva:
                if v_vr.get() != vrste[0] and a["vrsta"] != v_vr.get():
                    continue
                if v_pol.get() == T("Ženska", "Females") and a["pol"] != "z":
                    continue
                if v_pol.get() == T("Muška", "Males") and a["pol"] != "m":
                    continue
                o = self.ocene_grla(a["id"])
                red_.append((-(o["ukupno"] or 0), sort_key(a["id"]), a, o))
            red_.sort(key=lambda t: t[:2])          # neocenjena grla na dnu
            for i, (_, _, a, o) in enumerate(red_):
                vals = [m.pol_naziv(a["id"]),
                        (zvezdice(o["ukupno"]) + f" {o['ukupno']:.1f}").replace(".", "," if not jezik.EN else ".") if o["ukupno"] else "–"]
                vals += [zvezdice(o["rucne"][k]) if k in o["rucne"] else "" for k, _, _, _ in rucne_osobine()]
                vals += [zvezdice(o["auto"][k][0]) if k in o["auto"] and o["auto"][k][0] else "" for k, _ in auto_osobine()]
                tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag, values=vals, tags=["odd"] if i % 2 else [])
        for v in (v_vr, v_pol):
            v.trace_add("write", popuni)
        popuni()
        tv.bind("<Double-1>", lambda e: tv.focus() and self.karton(tv.focus()))
        self.btn(b, T("Zatvori", "Close"), win.destroy).pack(anchor="e", pady=(10, 0))
