"""Strana 'Nova rasa' – praćenje udela krvi kroz generacije i parenja koja vode ka ciljnom sastavu nove rase.

- Udeo krvi svakog grla se računa iz rodoslova (potomak = pola oca + pola majke).
- Osnivači (grla bez upisanih roditelja) mogu dobiti ručno upisan udeo, npr. "romanovska 50, pramenka 50".
- Cilj programa (npr. 62,5 % romanovska, 37,5 % pramenka): grla se ređaju po tome koliko su blizu cilja,
  a predlažu se parovi čiji bi potomak bio najbliži cilju, uz što manji inbriding.
"""
import tkinter as tk
from tkinter import ttk

import jezik
from jezik import T
from podaci import pct, sort_key, starost_meseci
from izgled import BAD, BG, INK2, SURF
from rodoslov import (NEPOZNATO, odstupanje, procena, procitaj_udeo, sastav_potomka, tekst_udela, zapisi_udeo)

BLIZU = 0.0625          # do 6,25 % razlike (1/16) grlo se smatra da odgovara cilju
MAKS_PAROVA = 60000     # zaštita od sporog računanja u ogromnim stadima


def _kanon(v):
    return jezik.vrsta_kanon(v) or " ".join(str(v or "").split()).lower()


class NovaRasaDeo:
    """Strana 'Nova rasa' (levi meni)."""

    def _program(self):
        p = self.pod.get("nova_rasa")
        return p if isinstance(p, dict) else {}

    def s_rasa(self):
        body = self.strana_okvir()
        self.zaglavlje(body, T("Nova rasa", "New breed"),
                       T("Udeo krvi svakog grla kroz generacije i parenja koja vode ka ciljnom sastavu nove rase.",
                         "The breed share of every animal across generations, and matings that lead to the target make-up of a new breed."))
        m = self.model
        sva = [a for a in m.grla(True) if not a["osnivac"]]
        if not sva:
            self.prazno(body)
            return
        prog = self._program()
        vrste = sorted({a["vrsta"] for a in sva}, key=lambda v: (jezik.VRSTE.index(v) if v in jezik.VRSTE else 99, v))
        izabrana = next((v for v in vrste if _kanon(v) == _kanon(prog.get("vrsta"))), vrste[0])
        grla = [a for a in sva if _kanon(a["vrsta"]) == _kanon(izabrana)]
        isti = _kanon(prog.get("vrsta")) == _kanon(izabrana)
        cilj = {k: v / 100 for k, v in (prog.get("cilj") or {}).items()} if isti else {}
        rase = sorted({k for a in grla for k in m.sastav(a["id"]) if k != NEPOZNATO} | set(cilj))

        # ---------------------------------------------------------- cilj programa
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, T("Cilj programa", "Breeding goal"), 13, "bold").pack(anchor="w")
        self.lbl(c, T("Upiši koje rase i u kom odnosu treba da ima nova rasa. Zbir mora biti 100 %.",
                      "Enter which breeds the new breed should have and in what share. The total must be 100 %."),
                 9, fg=INK2).pack(anchor="w", pady=(0, 10))
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        self.lbl(red, T("Vrsta", "Species"), 9, "bold", fg=INK2).grid(row=0, column=0, sticky="w")
        v_vrsta = tk.StringVar(value=izabrana)
        cb = ttk.Combobox(red, textvariable=v_vrsta, values=vrste, state="readonly", width=16, font=self.f(10))
        cb.grid(row=1, column=0, sticky="w", padx=(0, 16))
        self.lbl(red, T("Naziv nove rase", "Name of the new breed"), 9, "bold", fg=INK2).grid(row=0, column=1, sticky="w")
        v_ime = tk.StringVar(value=prog.get("ime", "") if isti else "")
        ttk.Entry(red, textvariable=v_ime, width=28, font=self.f(10)).grid(row=1, column=1, sticky="w")

        def promena_vrste(e=None):
            p = dict(self._program())
            if _kanon(p.get("vrsta")) != _kanon(v_vrsta.get()):
                p = {"vrsta": v_vrsta.get(), "ime": "", "cilj": {}}
            self.pod["nova_rasa"] = p
            self.sacuvaj_podesavanja()
            self.prikazi("rasa")
        cb.bind("<<ComboboxSelected>>", promena_vrste)

        tab = tk.Frame(c, bg=SURF)
        tab.pack(fill="x", pady=(12, 0))
        self.lbl(tab, T("Rasa", "Breed"), 9, "bold", fg=INK2).grid(row=0, column=0, sticky="w")
        self.lbl(tab, T("Udeo %", "Share %"), 9, "bold", fg=INK2).grid(row=0, column=1, sticky="w", padx=(10, 0))
        stari = sorted((prog.get("cilj") or {}).items(), key=lambda t: -t[1]) if cilj else []
        redovi = []
        for i in range(4):
            vr = tk.StringVar(value=stari[i][0] if i < len(stari) else "")
            vp = tk.StringVar(value=(f"{stari[i][1]:g}".replace(".", ",") if i < len(stari) else ""))
            ttk.Combobox(tab, textvariable=vr, values=rase, width=24, font=self.f(10)).grid(row=i + 1, column=0, sticky="w", pady=2)
            ttk.Entry(tab, textvariable=vp, width=8, font=self.f(10)).grid(row=i + 1, column=1, sticky="w", padx=(10, 0), pady=2)
            redovi.append((vr, vp))
        err = self.lbl(c, "", 10, "bold", fg=BAD, wraplength=640, justify="left")
        err.pack(anchor="w", pady=(6, 0))

        def sacuvaj_cilj():
            novi = {}
            for vr, vp in redovi:
                ime, br = " ".join(vr.get().split()).lower(), vp.get().strip().replace(",", ".").rstrip("%")
                if not ime and not br:
                    continue
                try:
                    broj = float(br)
                except ValueError:
                    broj = 0
                if not ime or broj <= 0:
                    err.config(text=T("Za svaku rasu upiši naziv i udeo veći od nule.", "For each breed enter a name and a share above zero."))
                    return
                novi[ime] = novi.get(ime, 0) + broj
            if novi and abs(sum(novi.values()) - 100) > 0.5:
                err.config(text=T(f"Zbir udela je {sum(novi.values()):g} %, a mora biti 100 %.".replace(".", ","),
                                  f"The shares add up to {sum(novi.values()):g} %, but must be 100 %."))
                return
            self.pod["nova_rasa"] = {"vrsta": v_vrsta.get(), "ime": " ".join(v_ime.get().split()), "cilj": novi}
            self.sacuvaj_podesavanja()
            self.prikazi("rasa")
            self.toast(T("Cilj je sačuvan.", "Goal saved."))

        dug = tk.Frame(c, bg=SURF)
        dug.pack(fill="x", pady=(8, 0))
        self.btn(dug, T("Sačuvaj cilj", "Save goal"), sacuvaj_cilj, "Primary").pack(side="left")
        if cilj:
            self.lbl(dug, T(f"Grlo „odgovara cilju“ kad je razlika do {pct(BLIZU)}.", f"An animal “matches the goal” when the difference is up to {pct(BLIZU)}."),
                     9, fg=INK2).pack(side="left", padx=14)

        # ---------------------------------------------------------- grla po udelu krvi
        tk.Frame(body, bg=BG, height=16).pack()
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, T("Grla po udelu krvi", "Animals by breed share"), 13, "bold").pack(anchor="w")
        self.lbl(c, T("Računa se iz rodoslova. Grla najbliža cilju su na vrhu. Dvoklik otvara karton.",
                      "Calculated from the pedigree. Animals closest to the goal are at the top. Double-click opens the card."),
                 9, fg=INK2).pack(anchor="w", pady=(0, 10))
        podaci = []
        for a in grla:
            s = m.sastav(a["id"])
            d = odstupanje(s, cilj)
            podaci.append((d if d is not None else 9, s.get(NEPOZNATO, 0), sort_key(a["id"]), a, s, d))
        podaci.sort(key=lambda t: t[:3])
        u_cilju = sum(1 for t in podaci if t[5] is not None and t[5] <= BLIZU + 1e-9)
        if cilj:
            self.napomena(c, T(f"Cilju odgovara {u_cilju} od {len(podaci)} grla u zapatu.",
                               f"{u_cilju} of {len(podaci)} animals in the herd match the goal."), ok=u_cilju > 0)
        wrap, tv = self.tabela(c, [("g", T("Grlo", "Animal"), 120), ("pol", T("Pol", "Sex"), 80),
                                   ("gen", T("Generacija", "Generation"), 170), ("s", T("Udeo krvi", "Breed share"), 330),
                                   ("d", T("Razlika od cilja", "Difference from goal"), 130, "e"),
                                   ("f", T("Inbriding", "Inbreeding"), 90, "e")], visina=min(max(len(podaci), 3), 14))
        wrap.pack(fill="x")
        for i, (_, _, _, a, s, d) in enumerate(podaci):
            tag = ["ok"] if d is not None and d <= BLIZU + 1e-9 else ["off"] if s.get(NEPOZNATO, 0) >= 0.5 else []
            if i % 2:
                tag.append("odd")
            tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag,
                      values=(m.pol_naziv(a["id"]), m.generacija_ukrstanja(a["id"])[0], tekst_udela(s, pct),
                              pct(d) if d is not None else "–", pct(m.inbr(a["id"]))), tags=tag)
        tv.bind("<Double-1>", lambda e: tv.focus() and self.karton(tv.focus()))

        # ---------------------------------------------------------- najbolji parovi
        if cilj:
            tk.Frame(body, bg=BG, height=16).pack()
            o, c = self.card(body)
            o.pack(fill="x")
            self.lbl(c, T("Parenja koja vode ka cilju", "Matings that lead to the goal"), 13, "bold").pack(anchor="w")
            self.lbl(c, T("Potomak dobija pola krvi od oca i pola od majke. Na vrhu su parovi čiji je potomak najbliži cilju, "
                          "a među jednako dobrim – oni sa manjim inbridingom. Rizični parovi (visok inbriding) su na dnu.",
                          "The offspring gets half its blood from the sire and half from the dam. At the top are pairs whose offspring "
                          "is closest to the goal and, among equally good ones, those with lower inbreeding. Risky pairs (high inbreeding) are at the bottom."),
                     9, fg=INK2, wraplength=820, justify="left").pack(anchor="w", pady=(0, 10))
            parovi = self._parovi_za_cilj(m, grla, cilj, prag=self.prag)
            if not parovi:
                self.lbl(c, T("Nema dovoljno mužjaka i ženki sa poznatim udelom krvi.",
                              "Not enough males and females with a known breed share."), 10, fg=INK2).pack(anchor="w")
            else:
                wrap, tv2 = self.tabela(c, [("z", T("Ženka", "Female"), 100), ("mu", T("Mužjak", "Male"), 100),
                                            ("s", T("Udeo krvi potomka", "Offspring breed share"), 310),
                                            ("d", T("Razlika", "Difference"), 110, "e"),
                                            ("f", T("Inbriding", "Inbreeding"), 130, "e"),
                                            ("p", T("Procena", "Assessment"), 140)], visina=min(len(parovi), 14))
                wrap.pack(fill="x")
                for i, (d, f, z, mu, s) in enumerate(parovi):
                    t_, boja = procena(f, self.prag)
                    tag = ["bad"] if boja == BAD else ["ok"] if d <= BLIZU + 1e-9 else []
                    if i % 2:
                        tag.append("odd")
                    tv2.insert("", "end", text="  " + z, image=self.img_tag,
                               values=(mu, tekst_udela(s, pct), pct(d), pct(f), t_), tags=tag)

        # ---------------------------------------------------------- udeo krvi osnivača
        tk.Frame(body, bg=BG, height=16).pack()
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, T("Udeo krvi osnivača", "Breed share of founders"), 13, "bold").pack(anchor="w")
        self.lbl(c, T("Za grla bez upisanih roditelja (npr. kupljeni meleze) upiši poznat udeo krvi, npr. „romanovska 50, pramenka 50“. "
                      "Grla čiste rase ne treba upisivati – dovoljno je da im je upisana rasa.",
                      "For animals without recorded parents (e.g. purchased crossbreds) enter the known breed share, e.g. “romanov 50, pramenka 50”. "
                      "Purebred animals need nothing here – their breed is enough."),
                 9, fg=INK2, wraplength=820, justify="left").pack(anchor="w", pady=(0, 10))
        osnivaci = [a for a in grla if m.P.get(a["id"], (None, None)) == (None, None)]
        if not osnivaci:
            self.lbl(c, T("Sva grla ove vrste imaju upisane roditelje.", "All animals of this species have recorded parents."), 10, fg=INK2).pack(anchor="w")
            return
        opisi = [self.opis_grla(a) for a in osnivaci]
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        self.lbl(red, T("Grlo", "Animal"), 9, "bold", fg=INK2).grid(row=0, column=0, sticky="w")
        self.lbl(red, T("Udeo krvi", "Breed share"), 9, "bold", fg=INK2).grid(row=0, column=1, sticky="w", padx=(12, 0))
        v_g = tk.StringVar()
        v_u = tk.StringVar()
        cbg = ttk.Combobox(red, textvariable=v_g, values=opisi, state="readonly", width=34, font=self.f(10))
        cbg.grid(row=1, column=0, sticky="w")
        ttk.Entry(red, textvariable=v_u, width=40, font=self.f(10)).grid(row=1, column=1, sticky="w", padx=(12, 0))
        err2 = self.lbl(c, "", 10, "bold", fg=BAD, wraplength=640, justify="left")
        err2.pack(anchor="w", pady=(6, 0))

        def izabrano(e=None):
            a = osnivaci[opisi.index(v_g.get())]
            v_u.set(", ".join(f"{k} {round(v * 100, 2):g}".replace(".", ",")
                              for k, v in sorted(a["udeo"].items(), key=lambda t: -t[1]) if k != NEPOZNATO))
            err2.config(text="")
        cbg.bind("<<ComboboxSelected>>", izabrano)

        def sacuvaj_udeo():
            if v_g.get() not in opisi:
                err2.config(text=T("Izaberi grlo.", "Choose an animal."))
                return
            x = osnivaci[opisi.index(v_g.get())]["id"]
            tekst = v_u.get().strip()
            s = procitaj_udeo(tekst) if tekst else {}
            if tekst and not s:
                err2.config(text=T("Upiši rase i procente, npr. „romanovska 50, pramenka 50“ (ukupno najviše 100).",
                                   "Enter breeds and percentages, e.g. “romanov 50, pramenka 50” (at most 100 in total)."))
                return
            novo = zapisi_udeo(s)
            r = next((r for r in self.tab.redovi if r.get("id", "").strip() == x), None)
            if r is None:
                return
            staro = r.get("udeo_krvi", "")
            if novo == staro:
                return
            r["udeo_krvi"] = novo
            self.ist.dodaj(x, jezik.AUTO, T(f"Izmena podataka – udeo krvi: {staro or '–'} → {novo or '–'}",
                                            f"Details changed – breed share: {staro or '–'} → {novo or '–'}"), automatski=True)
            self.promena(T("Udeo krvi je sačuvan.", "Breed share saved."))
        self.btn(c, T("Sačuvaj udeo krvi", "Save breed share"), sacuvaj_udeo, "Primary").pack(anchor="w", pady=(8, 0))

    def _parovi_za_cilj(self, m, grla, cilj, koliko=40, prag=0.0625):
        """[(razlika od cilja, inbriding potomka, ženka, mužjak, sastav potomka)] – najbolji prvi."""
        zenke = [a["id"] for a in grla if a["pol"] == "z" and m.sastav(a["id"]).get(NEPOZNATO, 0) < 0.5]
        muski = [a["id"] for a in grla if a["pol"] == "m" and m.sastav(a["id"]).get(NEPOZNATO, 0) < 0.5
                 and (starost_meseci(a["datum"]) is None or starost_meseci(a["datum"]) >= 6)]
        if len(zenke) * len(muski) > MAKS_PAROVA:
            zenke.sort(key=lambda x: odstupanje(m.sastav(x), cilj))
            zenke = zenke[:max(1, MAKS_PAROVA // max(1, len(muski)))]
        rez = []
        for z in zenke:
            sz = m.sastav(z)
            for mu in muski:
                s = sastav_potomka(sz, m.sastav(mu))
                rez.append((round(odstupanje(s, cilj), 6), m.kinship(z, mu), z, mu, s))
        rez.sort(key=lambda t: (procena(t[1], prag)[1] == BAD, t[0], t[1], sort_key(t[2]), sort_key(t[3])))
        return rez[:koliko]
