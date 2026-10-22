"""Karton grla, rodoslovno stablo, potomci, bočni srodnici i forma za upis/izmenu grla."""
import tkinter as tk
from datetime import date
from tkinter import ttk

from osnova import EN
from jezik import AUTO, GRUPE, POREKLA, T, VRSTE
from podaci import (fmt_datum, fmt_starost, nazivi, norm, norm_rasa, parsiraj_datum, pct, rasa_potomka, sada,
    sort_key, starost_meseci, vrsta_norm)
from izgled import BAD, BAD_BG, BG, BRAND, INK, INK2, LINE, OK, SURF, SURF2, ScrollFrame, TAG, WARN
from rodoslov import procena


class KartonEkran:
    """Karton grla, rodoslovno stablo, potomci, bočni srodnici i forma za upis/izmenu grla."""


    # ---------- karton
    def karton(self, x):
        m = self.model
        if x not in m.A:
            return
        if self.karton_win and self.karton_win.winfo_exists():
            win = self.karton_win
            for w in win.winfo_children():
                w.destroy()
        else:
            win = tk.Toplevel(self.root, bg=SURF)
            win.geometry(f"480x{min(760, self.root.winfo_height())}+"
                         f"{self.root.winfo_rootx() + max(0, self.root.winfo_width() - 500)}+{self.root.winfo_rooty() + 20}")
            win.transient(self.root)
            win.bind("<Escape>", lambda e: win.destroy())
            self.karton_win = win
        win.grlo = x
        a = m.A[x]
        win.title((f"Animal card {x}" if EN else f"Karton grla {x}"))
        pt = tk.Frame(win, bg=SURF)
        pt.pack(fill="x", padx=24, pady=(12, 0))
        self.btn(pt, T("🖨 Rodoslovni list / PDF", "🖨 Pedigree certificate / PDF"), lambda: self.stampaj_rodoslov(x)).pack(side="right")
        sf = ScrollFrame(win, bg=SURF)
        sf.pack(fill="both", expand=True)
        b = tk.Frame(sf.inner, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=22)
        top = tk.Frame(b, bg=SURF)
        top.pack(fill="x")
        self.cip(top, x, big=True, siv=a["osnivac"]).pack(side="left")
        t = tk.Frame(top, bg=SURF)
        t.pack(side="left", padx=14)
        self.lbl(t, m.pol_naziv(x) + (", " + a["rasa"] if a["rasa"] else ""), 12, "bold").pack(anchor="w")
        if a["rasa"].startswith(("hybrid" if EN else "hibrid")):
            o_h, m_h = m.P.get(x, (None, None))
            ro_ = m.A[o_h]["rasa"] if o_h in m.A else ""
            rm_ = m.A[m_h]["rasa"] if m_h in m.A else ""
            if ro_ or rm_:
                self.lbl(t, (f"sire {ro_ or '?'} × dam {rm_ or '?'}" if EN else f"otac {ro_ or '?'} × majka {rm_ or '?'}"), 9, fg=INK2).pack(anchor="w")
        self.lbl(t, ("known only as a parent" if EN else "poznat samo kao roditelj") if a["osnivac"] else ("deleted (kept in the pedigree)" if EN else "obrisano (čuva se u rodoslovu)")
                 if a.get("obrisano") else ("in herd" if EN else "u zapatu") if a["aktivno"] else ("not in herd" if EN else "nije u zapatu"),
                 9, fg=BAD if a.get("obrisano") else INK2).pack(anchor="w")

        def sekcija(naslov):
            self.lbl(b, naslov, 10, "bold").pack(anchor="w", pady=(18, 6))
            fr = tk.Frame(b, bg=SURF)
            fr.pack(anchor="w", fill="x")
            return fr

        if a["osnivac"]:
            self.lbl(b, ("This animal is entered only as a parent. Add it as an animal if you want to enter\n"
                        "its details and ancestors." if EN else "Ovo grlo je upisano samo kao roditelj. Dodaj ga kao grlo ako želiš da upišeš\n"
                        "njegove podatke i pretke."), 10, fg=INK2, justify="left").pack(anchor="w", pady=(14, 8))
            self.btn(b, (f"Add {x} as an animal" if EN else f"Dodaj {x} kao grlo"), lambda: (win.destroy(), self.forma(preset=dict(
                id=x, pol=a["pol"], vrsta=a["vrsta"]))), "Primary").pack(anchor="w")
        else:
            kv = tk.Frame(b, bg=SURF)
            kv.pack(fill="x", pady=(16, 0))
            st = starost_meseci(a["datum"])
            mr = tk.Frame(kv, bg=SURF)
            mr.grid(row=0, column=1, sticky="w", padx=16, pady=3)
            self.lbl(mr, a["markica"] or "–", 10, "bold").pack(side="left")
            lnk = self.lbl(mr, ("change" if EN else "promeni"), 9, "bold", fg=BRAND, cursor="hand2")
            lnk.pack(side="left", padx=10)
            lnk.bind("<Button-1>", lambda e: self.promena_markice(x, parent=win))
            por = a["poreklo"] + (f" – {a['poreklo_od']}" if a["poreklo_od"] else "") if a["poreklo"] else a["poreklo_od"]
            self.lbl(kv, ("Origin" if EN else "Poreklo"), 10, fg=INK2).grid(row=6, column=0, sticky="nw", pady=3)
            self.lbl(kv, por or ("not entered" if EN else "nije upisano"), 10, "bold" if por else "normal", fg=INK if por else INK2,
                     wraplength=260, justify="left").grid(row=6, column=1, sticky="w", padx=16, pady=3)
            if a["stare"]:
                self.lbl(kv, ("Previous ear tags" if EN else "Ranije markice"), 10, fg=INK2).grid(row=5, column=0, sticky="nw", pady=3)
                self.lbl(kv, ", ".join(a["stare"]), 10, fg=INK2, wraplength=260, justify="left").grid(
                    row=5, column=1, sticky="w", padx=16, pady=3)
            for i, (k, v) in enumerate(((("Ear tag" if EN else "Ušna markica"), None), (("Species" if EN else "Vrsta"), a["vrsta"]),
                                        (("Born" if EN else "Rođeno"), (fmt_datum(a["datum"]) + (f"  ({fmt_starost(st)})" if st is not None else ""))
                                         if a["datum"] else "–"),
                                        (("Herd" if EN else "Stado"), a["stado"] or "–"))):
                self.lbl(kv, k, 10, fg=INK2).grid(row=i, column=0, sticky="w", pady=3)
                if v is not None and k != ("Herd" if EN else "Stado"):
                    self.lbl(kv, v, 10, "bold").grid(row=i, column=1, sticky="w", padx=16, pady=3)
            sr = tk.Frame(kv, bg=SURF)
            sr.grid(row=3, column=1, sticky="w", padx=16, pady=3)
            self.lbl(sr, a["stado"] or "–", 10, "bold").pack(side="left")
            lns = self.lbl(sr, ("change" if EN else "promeni"), 9, "bold", fg=BRAND, cursor="hand2")
            lns.pack(side="left", padx=10)
            lns.bind("<Button-1>", lambda e: self.promena_stada([x], parent=win))
            f = m.inbr(x)
            self.lbl(kv, ("Inbreeding" if EN else "Inbriding"), 10, fg=INK2).grid(row=4, column=0, sticky="w", pady=3)
            self.badge(kv, pct(f), BAD if f > self.prag else WARN if f > self.prag / 2 else OK if f else INK2).grid(
                row=4, column=1, sticky="w", padx=16, pady=3)
            kar = self.opis_karence(x)
            if kar:
                self.lbl(kv, ("Withdrawal" if EN else "Karenca"), 10, fg=BAD).grid(row=7, column=0, sticky="nw", pady=3)
                self.lbl(kv, kar, 10, "bold", fg=BAD, wraplength=260, justify="left").grid(
                    row=7, column=1, sticky="w", padx=16, pady=3)

        o, mj = m.P[x]
        fr = sekcija(("Parents" if EN else "Roditelji"))
        for p, t in ((o, ("sire unknown" if EN else "otac nepoznat")), (mj, ("dam unknown" if EN else "majka nepoznata"))):
            if p:
                self.cip(fr, p, lambda p=p: self.karton(p), siv=m.A[p]["osnivac"]).pack(side="left", padx=(0, 6))
            else:
                self.lbl(fr, f" {t} ", 9, fg=INK2, bg=SURF2).pack(side="left", padx=(0, 6))
        dede = [r for p in (o, mj) if p for r in m.P.get(p, ()) if r]
        if dede:
            fr = sekcija(("Grandparents" if EN else "Dede i babe"))
            for d in dede:
                self.cip(fr, d, lambda d=d: self.karton(d), siv=m.A[d]["osnivac"]).pack(side="left", padx=(0, 6))
        if EN:
            if a["pol"] == "z" and not a["osnivac"]:
                pl = self.plodnost(x)
                if pl["porodjaja"] or pl["parenja"]:
                    fr = sekcija("Fertility")
                    tab_ = tk.Frame(fr, bg=SURF2)
                    tab_.pack(fill="x")
                    for i, (k_, v_) in enumerate((
                            ("Births", pl["porodjaja"]),
                            ("Born alive", f"{pl['zivih']}" + (f"  (average {pl['prosek']:.1f} per birth)"
                                                                  if pl["porodjaja"] else "")),
                            ("Stillborn", pl["mrtvih"] or "–"),
                            ("Interval between births", f"{round(pl['razmak'])} days" if pl["razmak"] else "–"),
                            ("Matings / failed", f"{pl['parenja']} / {pl['neuspela']}"),
                            ("First birth at", f"{pl['prvi_mes']} months" if pl["prvi_mes"] is not None else "–"))):
                        self.lbl(tab_, k_, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 10), pady=2)
                        self.lbl(tab_, str(v_), 9, "bold", bg=SURF2).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        else:
            if a["pol"] == "z" and not a["osnivac"]:
                pl = self.plodnost(x)
                if pl["porodjaja"] or pl["parenja"]:
                    fr = sekcija("Plodnost")
                    tab_ = tk.Frame(fr, bg=SURF2)
                    tab_.pack(fill="x")
                    for i, (k_, v_) in enumerate((
                            ("Porođaja", pl["porodjaja"]),
                            ("Rođeno živih", f"{pl['zivih']}" + (f"  (prosek {pl['prosek']:.1f} po porođaju)".replace(".", ",")
                                                                  if pl["porodjaja"] else "")),
                            ("Mrtvorođenih", pl["mrtvih"] or "–"),
                            ("Razmak između porođaja", f"{round(pl['razmak'])} dana" if pl["razmak"] else "–"),
                            ("Parenja / neuspela", f"{pl['parenja']} / {pl['neuspela']}"),
                            ("Prvi porođaj sa", f"{pl['prvi_mes']} meseci" if pl["prvi_mes"] is not None else "–"))):
                        self.lbl(tab_, k_, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 10), pady=2)
                        self.lbl(tab_, str(v_), 9, "bold", bg=SURF2).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        udeli = [(d, p) for d, p in m.udeli_predaka(x) if p not in (o, mj)][:6]
        if udeli:
            fr = sekcija(("Share of genes from ancestors" if EN else "Udeo gena od predaka"))
            for d, p in udeli:
                r = tk.Frame(fr, bg=SURF)
                r.pack(fill="x", pady=2)
                self.cip(r, p, lambda p=p: self.karton(p), siv=m.A[p]["osnivac"]).pack(side="left")
                self.lbl(r, pct(d), 10, "bold", width=7, anchor="e").pack(side="right")
                ttk.Progressbar(r, style="Green.Horizontal.TProgressbar", maximum=100, value=d * 100).pack(
                    side="left", fill="x", expand=True, padx=10)
        if m.putanje(x):
            lk = self.lbl(b, (f"Show all ancestors ({len(m.putanje(x))})  ›" if EN else f"Prikaži sve pretke ({len(m.putanje(x))})  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(anchor="w", pady=(6, 0))
            lk.bind("<Button-1>", lambda e: self.stablo(x, 4, "svi"))
        n_boc = len(self.bocni_srodnici(x))
        if n_boc:
            lb_ = self.lbl(b, (f"Collateral relatives – siblings, cousins ({n_boc})  ›" if EN else f"Bočni srodnici – braća, sestre, rođaci ({n_boc})  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            lb_.pack(anchor="w", pady=(4, 0))
            lb_.bind("<Button-1>", lambda e: self.stablo(x, 4, "bocni"))
        pot = sorted((k for k, pr in m.P.items() if x in pr), key=sort_key)
        fr = sekcija((f"Offspring ({len(pot)})" if EN else f"Potomci ({len(pot)})"))
        if not pot:
            self.lbl(fr, ("none recorded" if EN else "nema upisanih"), 10, fg=INK2).pack(side="left")
        red = None
        for i, p in enumerate(pot[:40]):
            if i % 6 == 0:
                red = tk.Frame(fr, bg=SURF)
                red.pack(anchor="w", pady=2)
            self.cip(red, p, lambda p=p: self.karton(p)).pack(side="left", padx=(0, 6))

        n_svih = sum(len(v) for v in self.potomci_po_kolenima(x).values())
        if n_svih > len(pot):
            lpo = self.lbl(b, (f"All descendants – children, grandchildren ({n_svih})  ›" if EN else f"Svi potomci – deca, unuci, praunuci ({n_svih})  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            lpo.pack(anchor="w", pady=(4, 0))
            lpo.bind("<Button-1>", lambda e: self.stablo(x, 4, "potomci"))
        if a["aktivno"] and a["pol"] and not a["osnivac"]:
            kand = sorted((m.kinship(x, k["id"]), k["id"]) for k in m.grla(True)
                          if k["id"] != x and k["vrsta"] == a["vrsta"] and k["pol"] != a["pol"])[:5]
            if kand:
                fr = sekcija(("Best partners" if EN else "Najbolji partneri"))
                for f, k in kand:
                    r = tk.Frame(fr, bg=SURF)
                    r.pack(fill="x", pady=3)
                    self.cip(r, k, lambda k=k: self.karton(k)).pack(side="left")
                    self.lbl(r, (f"genes {pct(m.r(x, k))}" if EN else f"geni {pct(m.r(x, k))}"), 9, fg=INK2).pack(side="left", padx=8)
                    t, boja = procena(f, self.prag)
                    self.badge(r, t, boja).pack(side="right")
                    self.lbl(r, pct(f), 10, "bold").pack(side="right", padx=10)

        if not a["osnivac"]:
            obv = [o for o in self.obavestenja(x) if o["grlo"] == x or o.get("podsetnik")]
            fr = sekcija((f"Notifications ({len(obv)})" if EN else f"Obaveštenja ({len(obv)})"))
            if not obv:
                self.lbl(fr, ("none" if EN else "nema"), 10, fg=INK2).pack(anchor="w")
            for o in obv[:5]:
                self.red_obavestenja(fr, o, kompakt=True)
            lp = self.lbl(b, ("+ Add reminder" if EN else "+ Dodaj podsetnik"), 9, "bold", fg=BRAND, cursor="hand2")
            lp.pack(anchor="w", pady=(4, 0))
            lp.bind("<Button-1>", lambda e: self.podsetnik_forma(x, parent=win))
            zap = self.ist.za(x)
            fr = sekcija((f"History ({len(zap)})" if EN else f"Istorija ({len(zap)})"))
            sz = tk.Frame(fr, bg=SURF)
            sz.pack(fill="x", pady=(0, 6))
            for i, (naziv, vrste) in enumerate(GRUPE):
                zz = [z for z in zap if z["dogadjaj"] in vrste]
                k = tk.Frame(sz, bg=SURF2, cursor="hand2")
                k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
                sz.columnconfigure(i, weight=1, uniform="g")
                a1 = tk.Label(k, text=f"{naziv}: {len(zz)}", font=self.f(9, "bold"), bg=SURF2, fg=INK)
                a1.pack(anchor="w", padx=8, pady=(5, 0))
                a2 = tk.Label(k, text=zz[0]["datum"] if zz else "–", font=self.f(8), bg=SURF2, fg=INK2)
                a2.pack(anchor="w", padx=8, pady=(0, 5))
                for w in (k, a1, a2):
                    w.bind("<Button-1>", lambda e, n=naziv: (self.ui.setdefault("ist_" + x, {"vrsta": ("All events" if EN else "Svi događaji"),
                           "auto": True, "q": ""}).update(grupa=n, vrsta=("All events" if EN else "Svi događaji")), self.istorija_prozor(x)))
            if not zap:
                self.lbl(fr, ("no records" if EN else "nema zapisa"), 10, fg=INK2).pack(anchor="w")
            for z in zap[:5]:
                r = tk.Frame(fr, bg=SURF)
                r.pack(fill="x", pady=2)
                self.lbl(r, z["datum"], 9, "bold", fg=INK2, width=11, anchor="w").pack(side="left", anchor="n")
                tekst = (z["dogadjaj"] if z["dogadjaj"] != AUTO else "") + \
                        (" – " if z["dogadjaj"] != AUTO and (z["opis"] or z["partner"] or z["vrednost"]) else "") + \
                        ", ".join(v for v in (z["opis"], (f"partner {z['partner']}" if z["partner"] else ""),
                                              z["vrednost"], ("📱 " + z["upisao"]) if z.get("upisao") else "") if v)
                self.lbl(r, tekst, 9, fg=INK2 if z["automatski"] else INK, wraplength=330,
                         justify="left").pack(side="left", anchor="w")
            lr = tk.Frame(b, bg=SURF)
            lr.pack(anchor="w", pady=(6, 0))
            l1 = self.lbl(lr, ("+ Add event" if EN else "+ Dodaj događaj"), 9, "bold", fg=BRAND, cursor="hand2")
            l1.pack(side="left")
            l1.bind("<Button-1>", lambda e: self.dogadjaj_forma(x, parent=win))
            l2 = self.lbl(lr, ("Full history  ›" if EN else "Cela istorija  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            l2.pack(side="left", padx=16)
            l2.bind("<Button-1>", lambda e: self.istorija_prozor(x))

        act1 = tk.Frame(b, bg=SURF)
        act1.pack(anchor="w", pady=(24, 0))
        if not a["osnivac"]:
            self.btn(act1, ("Edit details" if EN else "Izmeni podatke"), lambda: (win.destroy(), self.forma(x)), "Primary").pack(side="left", padx=(0, 8))
        self.btn(act1, ("Pedigree – tree" if EN else "Poreklo – stablo"), lambda: self.stablo(x)).pack(side="left")
        if not a["osnivac"]:
            act = tk.Frame(b, bg=SURF)
            act.pack(anchor="w", pady=(8, 0))
            dete = dict(vrsta=a["vrsta"], rasa=a["rasa"], stado=a["stado"])
            dete["otac" if a["pol"] == "m" else "majka"] = x
            self.btn(act, ("Add offspring" if EN else "Upiši potomka"), lambda: (win.destroy(), self.forma(preset=dete))).pack(side="left", padx=(0, 8))
            if a.get("obrisano"):
                self.btn(act, ("Restore to herd" if EN else "Vrati u stado"), lambda: self.vrati_grla([x])).pack(side="left")
            else:
                if a["pol"]:
                    self.btn(act, ("All partners" if EN else "Svi partneri"), lambda: (win.destroy(), self.idi_na_pretragu(x))).pack(side="left")
                self.btn(act, ("Delete" if EN else "Obriši"), lambda: self.obrisi_grla([x], parent=win), "Danger").pack(side="left", padx=8)
        win.lift()


    @staticmethod
    def naziv_gen(g):
        return {1: ("parent" if EN else "roditelj"), 2: ("grandparent" if EN else "deda / baba"), 3: ("great-grandparent" if EN else "pradeda / prababa"), 4: ("great-great-grandparent" if EN else "čukundeda / čukunbaba")}.get(
            g, (f"generation {g}" if EN else f"{g}. koleno"))


    def stablo(self, x, gen=4, tab="stablo"):
        m = self.model
        if x not in m.A:
            return
        if getattr(self, "stablo_win", None) and self.stablo_win.winfo_exists():
            win = self.stablo_win
            for w in win.winfo_children():
                w.destroy()
        else:
            win = tk.Toplevel(self.root, bg=BG)
            win.geometry(f"1040x700+{self.root.winfo_rootx() + 30}+{self.root.winfo_rooty() + 20}")
            win.transient(self.root)
            win.bind("<Escape>", lambda e: win.destroy())
            self.stablo_win = win
        win.title((f"Pedigree of animal {x}" if EN else f"Poreklo grla {x}"))
        a = m.A[x]
        put = m.putanje(x)                       # SVI preci, sve generacije
        dubina = max((max(gs) for gs in put.values()), default=0)
        ponavlja = {y: gs for y, gs in put.items() if sum(gs.values()) > 1}
        gen = max(2, min(gen, min(7, dubina) + 1))

        # zaglavlje
        h = tk.Frame(win, bg=BG)
        h.pack(fill="x", padx=24, pady=(18, 6))
        self.cip(h, x, lambda: self.karton(x), big=True, bg=BG, siv=a["osnivac"]).pack(side="left")
        t = tk.Frame(h, bg=BG)
        t.pack(side="left", padx=14)
        self.lbl(t, (f"Pedigree – {m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}" if EN else f"Poreklo – {m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}"), 14, "bold").pack(anchor="w")
        por = a["poreklo"] + (f" – {a['poreklo_od']}" if a["poreklo_od"] else "") if a["poreklo"] else a["poreklo_od"]
        info = (f"{len(put)} known ancestors in {dubina} generations   ·   inbreeding {pct(m.inbr(x))}" if EN else f"{len(put)} poznatih predaka u {dubina} generacija   ·   inbriding {pct(m.inbr(x))}")
        self.lbl(t, (f"{por}   ·   " if por else "") + info, 10, fg=INK2).pack(anchor="w")

        seg = tk.Frame(win, bg=BG)
        seg.pack(fill="x", padx=24, pady=(4, 8))
        sg = tk.Frame(seg, bg=SURF2)
        sg.pack(side="left")
        n_boc = len(self.bocni_srodnici(x))
        n_pot = sum(len(v) for v in self.potomci_po_kolenima(x).values())
        for k, tx in (("stablo", ("Tree" if EN else "Stablo")), ("svi", (f"All ancestors ({len(put)})" if EN else f"Svi preci ({len(put)})")),
                      ("potomci", (f"Descendants ({n_pot})" if EN else f"Potomci ({n_pot})")), ("bocni", (f"Collateral relatives ({n_boc})" if EN else f"Bočni srodnici ({n_boc})"))):
            akt = tab == k
            lb = tk.Label(sg, text=tx, font=self.f(10, "bold"), bg=SURF if akt else SURF2, fg=INK if akt else INK2,
                          padx=14, pady=6, cursor="hand2")
            lb.pack(side="left", padx=3, pady=3)
            lb.bind("<Button-1>", lambda e, k=k: self.stablo(x, gen, k))
        if tab == "stablo" and dubina >= 2:
            desno = tk.Frame(seg, bg=BG)
            desno.pack(side="right")
            self.lbl(desno, ("Generations shown:" if EN else "Prikaži generacija:"), 9, "bold", fg=INK2).pack(side="left", padx=(0, 6))
            gv = tk.StringVar(value=str(gen - 1))
            cg = ttk.Combobox(desno, textvariable=gv, values=[str(i) for i in range(1, min(7, dubina) + 1)],
                              state="readonly", width=4, font=self.f(10))
            cg.pack(side="left")
            cg.bind("<<ComboboxSelected>>", lambda e: self.stablo(x, int(gv.get()) + 1, "stablo"))

        # preci koji se ponavljaju – kroz CEO rodoslov, ne samo prikazane generacije
        leg = tk.Frame(win, bg=BG)
        leg.pack(fill="x", padx=24, pady=(0, 6))
        if not put:
            self.lbl(leg, ("No parents are entered for this animal." if EN else "Za ovo grlo nisu upisani roditelji."), 10, fg=INK2).pack(anchor="w")
        elif ponavlja:
            opis = ", ".join((f"{y} ({sum(gs.values())}×, gen. {' and '.join(str(g) for g in sorted(gs))})" if EN else f"{y} ({sum(gs.values())}×, gen. {' i '.join(str(g) for g in sorted(gs))})")
                             for y, gs in sorted(ponavlja.items(), key=lambda t: (min(t[1]), sort_key(t[0]))))
            self.lbl(leg, ("Ancestors repeated in the whole pedigree (cause of inbreeding): " if EN else "Preci koji se ponavljaju u celom rodoslovu (uzrok inbridinga): ") + opis, 9, fg=BAD,
                     wraplength=980, justify="left").pack(anchor="w")
            dalji = [y for y, gs in ponavlja.items() if min(gs) >= gen]
            if tab == "stablo" and dalji:
                self.lbl(leg, (f"Some of them are beyond the generations shown ({', '.join(sorted(dalji, key=sort_key))})"
                              " – increase the number of generations or open the \"All ancestors\" tab." if EN else f"Neki od njih su dalje od prikazanih generacija ({', '.join(sorted(dalji, key=sort_key))})"
                              " – povećaj broj generacija ili otvori karticu „Svi preci“."), 9, fg=WARN,
                         wraplength=980, justify="left").pack(anchor="w")
        else:
            self.lbl(leg, ("No ancestor is repeated in the whole known pedigree." if EN else "Nijedan predak se ne ponavlja u celom poznatom rodoslovu."), 9, fg=OK).pack(anchor="w")

        if tab == "svi":
            self.svi_preci(win, x, put, ponavlja, dubina)
        elif tab == "bocni":
            self.tab_bocni(win, x)
        elif tab == "potomci":
            self.tab_potomci(win, x)
        else:
            self.crtaj_stablo(win, x, gen, ponavlja)
        win.lift()


    def potomci_po_kolenima(self, x):
        """{koleno: [potomak, ...]} – 1 deca, 2 unuci, 3 praunuci…"""
        m = self.model
        deca = {}
        for k, (o, mj) in m.P.items():
            for p in (o, mj):
                if p:
                    deca.setdefault(p, set()).add(k)
        rez, vidjeni, nivo, g = {}, {x}, {x}, 1
        while nivo and g <= 10:
            sl = set()
            for y in nivo:
                sl |= deca.get(y, set())
            sl -= vidjeni
            if not sl:
                break
            rez[g] = sorted(sl, key=lambda y: (m.A[y]["datum"] or date.max, sort_key(y)))
            vidjeni |= sl
            nivo, g = sl, g + 1
        return rez


    def tab_potomci(self, win, x):
        m = self.model
        po = self.potomci_po_kolenima(x)
        ukupno = sum(len(v) for v in po.values())
        legla = [z for z in self.cekaju_mindjusu(x)]
        nazivi_k = {1: ("Children" if EN else "Deca"), 2: ("Grandchildren" if EN else "Unuci"), 3: ("Great-grandchildren" if EN else "Praunuci"), 4: ("Great-great-grandchildren" if EN else "Čukununuci")}
        opis = " · ".join((f"{nazivi_k.get(k, f'generation {k}')}: {len(v)}" if EN else f"{nazivi_k.get(k, f'{k}. koleno')}: {len(v)}") for k, v in po.items())
        self.lbl(win, ((f"In total {ukupno} descendants – {opis}." if EN else f"Ukupno {ukupno} potomaka – {opis}.") if ukupno else ("No descendants recorded." if EN else "Nema upisanih potomaka.")) +
                 (" Share of genes = how many genes the descendant carries from this animal." if EN else " Udeo gena = koliko gena potomak nosi od ovog grla."), 9, fg=INK2, wraplength=980,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not ukupno and not legla:
            self.napomena(body, ("This animal has no recorded descendants yet." if EN else "Ovo grlo još nema upisanih potomaka."), ok=True)
            return
        wrap, tv = self.tabela(body, [("id", ("Offspring" if EN else "Potomak"), 200), ("odnos", ("Other parent" if EN else "Drugi roditelj"), 200),
                                      ("pol", ("Sex" if EN else "Pol"), 80), ("geni", ("Share of genes" if EN else "Udeo gena"), 95, "e"), ("rasa", ("Breed" if EN else "Rasa"), 120),
                                      ("rod", ("Born" if EN else "Rođen"), 95), ("st", "Status", 140)], visina=16)
        wrap.pack(fill="both", expand=True)
        tv.tag_configure("grupa", font=self.f(10, "bold"), background=SURF2)
        for k, lst in po.items():
            gr = tv.insert("", "end", text=(f"  {nazivi_k.get(k, f'generation {k}')} ({len(lst)})" if EN else f"  {nazivi_k.get(k, f'{k}. koleno')} ({len(lst)})"), open=k <= 2,
                           tags=["grupa"])
            for y in lst:
                p = m.A[y]
                o, mj = m.P.get(y, (None, None))
                if k == 1:
                    drugi = mj if o == x else o
                    dr = (f"{'dam' if o == x else 'sire'} {drugi}" if EN else f"{'majka' if o == x else 'otac'} {drugi}") if drugi else ("unknown" if EN else "nepoznat")
                else:
                    preko = [r for r in (o, mj) if r and (r in po.get(k - 1, []))]
                    dr = (f"through {', '.join(preko)}" if EN else f"preko {', '.join(preko)}") if preko else "–"
                st = (("deleted" if EN else "obrisano") if p.get("obrisano") else ("in herd" if EN else "u zapatu") if p["aktivno"] else ("out of herd" if EN else "van zapata"))
                tv.insert(gr, "end", iid=y, text="  " + y, image=self.img_tag, values=(
                    dr, m.pol_naziv(y), pct(m.doprinos(y, x)), p["rasa"] or "–",
                    fmt_datum(p["datum"]) or "–", st), tags=[] if p["aktivno"] else ["off"])
        if legla:
            gr = tv.insert("", "end", text=("  Born, no ear tag yet" if EN else "  Rođeni, još bez minđuše"), open=True, tags=["grupa"])
            for z in legla:
                uk, dd, vec = self.leglo(z)
                majka, otac = self.roditelji_parenja(z)
                tv.insert(gr, "end", text=(f"  {uk - len(vec)} young" if EN else f"  {uk - len(vec)} mladih"), values=(
                    f"{majka or '?'} × {otac or '?'}", "–", "50,0%", "–", dd, ("waiting for entry in the list" if EN else "čeka upis u listu")))
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Double-click a descendant to open its card." if EN else "Dvoklik na potomka otvara njegov karton."), 9, fg=INK2).pack(anchor="w", pady=(8, 0))


    def bocni_srodnici(self, x):
        """Bočni (kolateralni) srodnici: braća/sestre, braća/sestre roditelja, nećaci, prvi rođaci.
        Vraća [(grupa, srodnik, opis odnosa)]."""
        m = self.model
        deca = {}
        for k, (o, mj) in m.P.items():
            for p in (o, mj):
                if p:
                    deca.setdefault(p, set()).add(k)

        def braca(y):
            o, mj = m.P.get(y, (None, None))
            rez = {}
            for s in (deca.get(o, set()) | deca.get(mj, set())) - {y}:
                so, sm = m.P.get(s, (None, None))
                if o and mj and so == o and sm == mj:
                    rez[s] = "pun"
                elif o and so == o:
                    rez[s] = ("paternal" if EN else "po ocu")
                elif mj and sm == mj:
                    rez[s] = ("maternal" if EN else "po majci")
            return rez

        def naziv(s, z_, m_):
            return m_ if m.A.get(s, {}).get("pol") == "m" else z_ if m.A.get(s, {}).get("pol") == "z" else f"{m_} / {z_}"

        rez, vidjeni = [], {x}
        predci = m.preci(x)
        # 1) braća i sestre
        for s, tip in sorted(braca(x).items(), key=lambda t: (t[1] != "pun", sort_key(t[0]))):
            ime = naziv(s, ("sister" if EN else "sestra"), ("brother" if EN else "brat"))
            rez.append((("Siblings" if EN else "Braća i sestre"), s, (("full " if EN else "pun ") if tip == "pun" else ("half-" if EN else "polu")) + ime +
                        ("" if tip == "pun" else f" ({tip})")))
            vidjeni.add(s)
        # dvostruki odnos: brat/sestra koji je ujedno i dete brata/sestre
        sib = set(braca(x))
        for i, (g, y, op) in enumerate(rez):
            if any(p_ in sib for p_ in m.P.get(y, (None, None)) if p_):
                rez[i] = (g, y, op + (f", also {naziv(y, 'niece', 'nephew')}" if EN else f", ujedno {naziv(y, 'nećaka', 'nećak')}"))
        # 2) deca braće i sestara
        for s in list(braca(x)):
            for d in sorted(deca.get(s, set()) - vidjeni, key=sort_key):
                rez.append((("Nephews and nieces (children of siblings)" if EN else "Nećaci (deca braće i sestara)"), d, (f"child of {s}" if EN else f"dete od {s}")))
                vidjeni.add(d)
        # 3) braća i sestre roditelja
        o, mj = m.P.get(x, (None, None))
        strane = []
        for rod, strana, (mz, zz) in ((o, ("paternal" if EN else "po ocu"), (("uncle" if EN else "stric"), ("aunt" if EN else "tetka"))), (mj, ("maternal" if EN else "po majci"), (("uncle" if EN else "ujak"), ("aunt" if EN else "tetka")))):
            if not rod:
                continue
            for s, tip in sorted(braca(rod).items(), key=lambda t: sort_key(t[0])):
                if s in vidjeni or s in predci:
                    continue
                rez.append((("Siblings of parents" if EN else "Braća i sestre roditelja"), s, (f"{strana} {naziv(s, zz, mz)}" if EN else f"{naziv(s, zz, mz)} {strana}") +
                            ("" if tip == "pun" else (" (half)" if EN else " (polu)"))))
                vidjeni.add(s)
                strane.append((s, strana))
        # 4) prvi rođaci (deca braće i sestara roditelja)
        for s, strana in strane:
            for d in sorted(deca.get(s, set()) - vidjeni, key=sort_key):
                if d in predci:
                    continue
                rez.append((("First cousins" if EN else "Prvi rođaci"), d, (f"child of {s} ({strana})" if EN else f"dete od {s} ({strana})")))
                vidjeni.add(d)
        return rez


    def tab_bocni(self, win, x):
        m = self.model
        sr = self.bocni_srodnici(x)
        self.lbl(win, ("Collateral relatives are neither ancestors nor descendants, but share ancestors with this animal. "
                      "Be careful when mating – a high share of genes also means higher inbreeding of the young." if EN else "Bočni srodnici nisu ni preci ni potomci, ali imaju zajedničke pretke sa ovim grlom. "
                      "Pazi pri parenju – visok procenat zajedničkih gena znači i veći inbriding mladih."), 9,
                 fg=INK2, wraplength=980, justify="left").pack(anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not sr:
            self.napomena(body, ("No known collateral relatives (siblings, cousins…) according to the recorded pedigree." if EN else "Nema poznatih bočnih srodnika (braće, sestara, rođaka…) prema upisanom rodoslovu."),
                          ok=True)
            return
        wrap, tv = self.tabela(body, [("id", ("Relative" if EN else "Srodnik"), 240), ("odnos", ("Relation" if EN else "Odnos"), 260), ("geni", ("Shared genes" if EN else "Zajednički geni"), 120, "e"),
                                      ("f", ("Inbreeding of young" if EN else "Inbriding mladih"), 120, "e"), ("rasa", ("Breed" if EN else "Rasa"), 110),
                                      ("rod", ("Born" if EN else "Rođen"), 70), ("st", "Status", 140)], visina=16)
        wrap.pack(fill="both", expand=True)
        tv.tag_configure("grupa", font=self.f(10, "bold"), background=SURF2)
        grupe = {}
        for g, y, opis in sr:
            if g not in grupe:
                grupe[g] = tv.insert("", "end", text="  " + g, open=True, tags=["grupa"])
        brojac = {}
        for g, y, opis in sr:
            brojac[g] = brojac.get(g, 0) + 1
            p = m.A.get(y, {})
            r = m.r(x, y)
            suprotan = p.get("pol") and m.A[x]["pol"] and p.get("pol") != m.A[x]["pol"]
            f = m.kinship(x, y) if suprotan else None
            st = (("known only as a parent" if EN else "poznat samo kao roditelj") if p.get("osnivac") else ("deleted" if EN else "obrisano") if p.get("obrisano")
                  else ("in herd" if EN else "u zapatu") if p.get("aktivno") else ("out of herd" if EN else "van zapata"))
            tagovi = []
            if f is not None and f > self.prag and p.get("aktivno"):
                tagovi.append("bad")
            elif not p.get("aktivno"):
                tagovi.append("off")
            tv.insert(grupe[g], "end", iid=y, text="  " + y, image=self.img_tag_siv if p.get("osnivac") else self.img_tag,
                      values=(opis, pct(r), pct(f) if f is not None else "–", p.get("rasa") or "–",
                              p["datum"].year if p.get("datum") else "–", st), tags=tagovi)
        for g, iid in grupe.items():
            tv.item(iid, text=f"  {g} ({brojac[g]})")
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Red = opposite sex in the herd with which the young would have inbreeding above the limit. "
                       "Double-click opens the card." if EN else "Crveno = suprotan pol u zapatu sa kojim bi mladi imali inbriding iznad granice. "
                       "Dvoklik otvara karton."), 9, fg=INK2).pack(anchor="w", pady=(8, 0))


    def svi_preci(self, win, x, put, ponavlja, dubina):
        m = self.model
        kom = m.kompletnost(x, dubina)
        if kom:
            self.lbl(win, ("Pedigree completeness:  " if EN else "Kompletnost rodoslova:  ") + "   ".join(
                (f"gen. {g}: {n}/{od}" if EN else f"{g}. gen {n}/{od}") for g, n, od in kom), 9, fg=INK2, wraplength=980, justify="left").pack(
                anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not put:
            return
        wrap, tv = self.tabela(body, [("id", ("Ancestor" if EN else "Predak"), 110), ("gen", ("Generation" if EN else "Generacija"), 220), ("put", ("Times" if EN else "Puta"), 60, "e"),
                                      ("udeo", ("Share of genes" if EN else "Udeo gena"), 95, "e"), ("pol", ("Sex" if EN else "Pol"), 75), ("mk", ("Ear tag" if EN else "Markica"), 115),
                                      ("rasa", ("Breed" if EN else "Rasa"), 95), ("st", "Status", 160)], visina=16)
        wrap.pack(fill="both", expand=True)
        redovi = sorted(put.items(), key=lambda t: (-m.doprinos(x, t[0]), min(t[1]), sort_key(t[0])))
        for i, (y, gs) in enumerate(redovi):
            p = m.A[y]
            n = sum(gs.values())
            gen_txt = (f"{min(gs)}.  {self.naziv_gen(min(gs))}" if len(gs) == 1
                       else ", ".join(str(g) for g in sorted(gs)) + (" generations" if EN else ". generacija"))
            st = (("known only as a parent" if EN else "poznat samo kao roditelj") if p["osnivac"] else ("deleted" if EN else "obrisano") if p.get("obrisano")
                  else ("in herd" if EN else "u zapatu") if p["aktivno"] else ("out of herd" if EN else "van zapata"))
            tags = (["odd"] if i % 2 else []) + (["bad"] if y in ponavlja else []) + (["off"] if p["osnivac"] else [])
            tv.insert("", "end", iid=y, text="  " + y, image=self.img_tag_siv if p["osnivac"] else self.img_tag,
                      values=(gen_txt, f"{n}×", pct(m.doprinos(x, y)), m.pol_naziv(y), p["markica"] or "–",
                              p["rasa"] or "–", st), tags=tags)
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Red = the ancestor appears more than once.  Double-click opens the ancestor's card." if EN else "Crveno = predak se pojavljuje više puta.  Dvoklik otvara karton pretka."), 9, fg=INK2).pack(
            anchor="w", pady=(8, 0))


    def crtaj_stablo(self, win, x, gen, ponavlja):
        m = self.model
        sloti = {}
        def skupi(y, g, i):
            if g >= gen:
                return
            sloti[(g, i)] = y
            o, mj = m.P.get(y, (None, None)) if y else (None, None)
            skupi(o, g + 1, 2 * i)
            skupi(mj, g + 1, 2 * i + 1)
        skupi(x, 0, 0)
        self.lbl(win, ("Each ancestor shows what share of genes the animal carries from it (sum of all paths). "
                      "Click an ancestor to show its pedigree, double-click opens its card." if EN else "Uz svakog pretka piše koliki deo gena grlo nosi od njega (zbir svih puteva). "
                      "Klik na pretka prikazuje njegovo poreklo, dvoklik otvara karton."), 9, fg=INK2,
                 wraplength=980, justify="left").pack(anchor="w", padx=24)

        wrap = tk.Frame(win, bg=LINE)
        wrap.pack(fill="both", expand=True, padx=24, pady=(4, 20))
        c = tk.Canvas(wrap, bg=SURF, highlightthickness=0)
        sy = ttk.Scrollbar(wrap, orient="vertical", command=c.yview)
        sx = ttk.Scrollbar(wrap, orient="horizontal", command=c.xview)
        c.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        c.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        BW, BH, GAP = 196, 50, 34
        listova = 2 ** (gen - 1)
        visina = max(480, listova * (BH + 12) + 40)
        for g in range(gen):
            nz = ("Animal" if EN else "Grlo") if g == 0 else {1: ("Parents" if EN else "Roditelji"), 2: ("Grandparents" if EN else "Dede i babe"), 3: ("Great-grandparents" if EN else "Pradede i prababe"),
                                         4: ("Great-great-grandparents" if EN else "Čukundede i čukunbabe")}.get(g, (f"generation {g}" if EN else f"{g}. koleno"))
            c.create_text(20 + g * (BW + GAP) + BW / 2, 16, text=nz, font=self.f(9, "bold"), fill=INK2)
        pos = {}
        for (g, i) in sloti:
            pos[(g, i)] = (20 + g * (BW + GAP), 30 + (i + 0.5) * (visina - 40) / (2 ** g))
        for (g, i), (cx, cy) in pos.items():
            for k in (0, 1):
                ch = (g + 1, 2 * i + k)
                if ch in pos:
                    px, py = pos[ch]
                    mx = cx + BW + GAP / 2
                    c.create_line(cx + BW, cy, mx, cy, mx, py, px, py, fill=LINE, width=2)
        for (g, i), y in sloti.items():
            cx, cy = pos[(g, i)]
            x1, y1, x2, y2 = cx, cy - BH / 2, cx + BW, cy + BH / 2
            uloga = "" if g == 0 else (("sire" if EN else "otac") if i % 2 == 0 else ("dam" if EN else "majka"))
            if not y:
                c.create_polygon(self.zaobljeno(x1, y1, x2, y2, 8), smooth=True, fill=BG, outline="#C3CBC4", dash=(4, 3))
                c.create_text(x1 + 14, cy, text=(f"{uloga} unknown" if EN else f"{uloga} nepoznat{'a' if uloga == 'majka' else ''}") if uloga else "",
                              anchor="w", font=self.f(9), fill="#98A39B")
                continue
            p = m.A[y]
            rep_ = y in ponavlja
            tag = f"b{g}_{i}"
            c.create_polygon(self.zaobljeno(x1, y1, x2, y2, 8), smooth=True,
                             fill=SURF2 if p["osnivac"] else (BAD_BG if rep_ else SURF),
                             outline=BAD if rep_ else (BRAND if g == 0 else LINE), width=2 if (rep_ or g == 0) else 1,
                             tags=tag)
            c.create_rectangle(x1 + 1, y1 + 8, x1 + 6, y2 - 8, fill=TAG if not p["osnivac"] else "#C9D0CA",
                               outline="", tags=tag)
            c.create_text(x1 + 16, cy - 9, text=y, anchor="w", font=self.f(10, "bold"), fill=INK, tags=tag)
            if uloga:
                c.create_text(x2 - 10, cy - 9, text=(f"{uloga} · {pct(m.doprinos(x, y))} genes" if EN else f"{uloga} · {pct(m.doprinos(x, y))} gena"), anchor="e",
                              font=self.f(8), fill=BAD if rep_ else INK2, tags=tag)
            sub = " · ".join(v for v in (p["markica"], p["rasa"]) if v)
            if p["datum"] and len(sub) + 7 <= 30:
                sub = (sub + " · " if sub else "") + str(p["datum"].year)
            sub = sub or (("known only as a parent" if EN else "poznat samo kao roditelj") if p["osnivac"] else "")
            if len(sub) > 30:
                sub = sub[:29] + "…"
            c.create_text(x1 + 16, cy + 10, text=sub, anchor="w", font=self.f(8), fill=INK2, tags=tag)
            if g > 0:
                c.tag_bind(tag, "<Button-1>", lambda e, y=y: self.stablo(y, gen))
            c.tag_bind(tag, "<Double-1>", lambda e, y=y: self.karton(y))
            c.tag_bind(tag, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.config(cursor=""))
            # oznaka da ovaj predak ima jos predaka iza ivice prikaza
            if g == gen - 1 and any(m.P.get(y, (None, None))):
                c.create_text(x2 + 6, cy, text="›", anchor="w", font=self.f(14, "bold"), fill=INK2)
        c.configure(scrollregion=(0, 0, 40 + gen * (BW + GAP), visina + 10))
        c.bind("<MouseWheel>", lambda e: c.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units"))
        c.bind("<Button-4>", lambda e: c.yview_scroll(-1, "units"))
        c.bind("<Button-5>", lambda e: c.yview_scroll(1, "units"))


    # ---------- forma
    def forma(self, jid=None, preset=None):
        red = next((r for r in self.tab.redovi if r["id"] == jid), None) if jid else None
        posl = self.pod.get("poslednje", {})
        v = dict(red) if red else {"vrsta": posl.get("vrsta", ("cattle" if EN else "goveda")), "rasa": posl.get("rasa", ""),
                                   "stado": posl.get("stado", ""), "status": "aktivno", **(preset or {})}
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Edit animal" if EN else "Izmena grla") if red else ("New animal" if EN else "Novo grlo"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Edit animal" if EN else "Izmena grla") if red else ("New animal" if EN else "Novo grlo"), 17, "bold").grid(row=0, column=0, columnspan=2,
                                                                          sticky="w", pady=(0, 14))
        m = self.model
        sva = m.grla()
        vars_ = {}

        def polje(r, c, naslov, key, widget="entry", values=(), hint=""):
            f = tk.Frame(b, bg=SURF)
            f.grid(row=r, column=c, sticky="new", padx=(0 if c == 0 else 14, 0), pady=6)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            var = tk.StringVar(value=v.get(key, ""))
            if widget == "entry":
                w = ttk.Entry(f, textvariable=var, width=28, font=self.f(10))
            else:
                w = ttk.Combobox(f, textvariable=var, values=list(values), width=26, font=self.f(10),
                                 state="readonly" if widget == "select" else "normal")
            w.pack(fill="x", pady=(4, 0))
            if hint:
                self.lbl(f, hint, 8, fg="#8A968D").pack(anchor="w")
            vars_[key] = var
            return w

        e_id = polje(1, 0, ("Animal tag *" if EN else "Oznaka grla *"), "id", hint=("e.g. K12 or a name" if EN else "npr. K12 ili ime"))
        polje(1, 1, ("Ear tag" if EN else "Ušna markica"), "markica", hint=("e.g. UK 123456 700123" if EN else "npr. RS 1234-5678"))
        vr = polje(2, 0, ("Species" if EN else "Vrsta"), "vrsta", "combo", VRSTE)
        polje(2, 1, ("Breed" if EN else "Rasa"), "rasa", "combo", sorted({a["rasa"] for a in sva if a["rasa"]}))

        pf = tk.Frame(b, bg=SURF)
        pf.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
        self.lbl(pf, ("Sex *" if EN else "Pol *"), 9, "bold", fg=INK2).pack(anchor="w")
        segf = tk.Frame(pf, bg=SURF2)
        segf.pack(anchor="w", pady=(4, 0))
        pol = tk.StringVar(value=v.get("pol", ""))
        seg_btns = {}

        def crtaj_seg(*_):
            n = nazivi(vrsta_norm(vars_["vrsta"].get()))
            for k, lb in seg_btns.items():
                akt = pol.get() == k
                lb.config(text=(n[1] if k == "z" else n[0]).capitalize(), bg=SURF if akt else SURF2,
                          fg=INK if akt else INK2)
        for k in ("z", "m"):
            lb = tk.Label(segf, font=self.f(10, "bold"), padx=20, pady=6, cursor="hand2")
            lb.pack(side="left", padx=3, pady=3)
            lb.bind("<Button-1>", lambda e, k=k: (pol.set(k), crtaj_seg()))
            seg_btns[k] = lb
        crtaj_seg()
        vars_["vrsta"].trace_add("write", crtaj_seg)

        d = parsiraj_datum(v.get("datum_rodjenja"))
        v["datum_rodjenja"] = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if d else v.get("datum_rodjenja", "")
        polje(4, 0, ("Date of birth" if EN else "Datum rođenja"), "datum_rodjenja", hint=("day/month/year, e.g. 15/03/2022" if EN else "dan.mesec.godina, npr. 15.03.2022"))
        polje(4, 1, ("Herd / location" if EN else "Stado / lokacija"), "stado", "combo", sorted({a["stado"] for a in sva if a["stado"]}))
        polje(5, 0, ("Sire" if EN else "Otac"), "otac", "combo", sorted((a["id"] for a in m.A.values() if a["pol"] == "m"), key=sort_key),
              hint=("tag or ear tag; empty if unknown" if EN else "oznaka ili markica; prazno ako je nepoznat"))
        polje(5, 1, ("Dam" if EN else "Majka"), "majka", "combo", sorted((a["id"] for a in m.A.values() if a["pol"] == "z"), key=sort_key),
              hint=("tag or ear tag; empty if unknown" if EN else "oznaka ili markica; prazno ako je nepoznata"))
        polje(6, 0, ("Origin" if EN else "Poreklo"), "poreklo", "combo", POREKLA)
        polje(6, 1, ("From whom / where" if EN else "Od koga / odakle"), "poreklo_od", "combo",
              sorted({a["poreklo_od"] for a in sva if a["poreklo_od"]}))

        def auto_rasa(*_):
            """Kad su upisani otac i majka različitih rasa, rasa postaje 'hibrid O×M'."""
            o_, m_ = m.nadji(vars_["otac"].get()), m.nadji(vars_["majka"].get())
            if not o_ or not m_:
                return
            predlog = rasa_potomka(m.A[o_]["rasa"], m.A[m_]["rasa"])
            sad = vars_["rasa"].get().strip().lower()
            if predlog and (not sad or sad.startswith(("hybrid" if EN else "hibrid")) or sad == ("crossbred" if EN else "melez")):
                vars_["rasa"].set(predlog)
        vars_["otac"].trace_add("write", auto_rasa)
        vars_["majka"].trace_add("write", auto_rasa)
        akt = tk.BooleanVar(value=v.get("status", "aktivno") != "neaktivno")
        ttk.Checkbutton(b, text=("The animal is in the herd (not sold or dead)" if EN else "Grlo je u zapatu (nije prodato ni uginulo)"), variable=akt,
                        style="Card.TCheckbutton").grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def sacuvaj(dalje=False):
            nid = vars_["id"].get().strip()
            if not nid:
                err.config(text=("Enter the animal's tag." if EN else "Upiši oznaku grla."))
                e_id.focus_set()
                return
            dup = next((r for r in self.tab.redovi if r["id"] == nid and r is not red), None)
            if dup:
                err.config(text=(f"Animal {nid} already exists." if EN else f"Grlo {nid} već postoji.") + ((" It is deleted – restore it from the \"Deleted animals\" list." if EN else " Obrisano je – vrati ga iz liste „Obrisana grla“.")
                                                             if dup.get("status") == "obrisano" else ""))
                return
            mk = vars_["markica"].get().strip()
            if mk:
                zauzeto = self.markica_zauzeta(mk, red)
                if zauzeto:
                    err.config(text=zauzeto)
                    return
            if pol.get() not in ("m", "z"):
                err.config(text=("Choose the sex." if EN else "Izaberi pol."))
                return
            dat = vars_["datum_rodjenja"].get().strip()
            if dat and not parsiraj_datum(dat):
                err.config(text=("The date is not valid. Enter it as 15/03/2022." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2022."))
                return
            o, mj = vars_["otac"].get().strip(), vars_["majka"].get().strip()
            if nid in (o, mj):
                err.config(text=("An animal cannot be its own parent." if EN else "Grlo ne može biti sopstveni roditelj."))
                return
            novi = dict(id=nid, markica=mk, vrsta=vrsta_norm(vars_["vrsta"].get()) or ("cattle" if EN else "goveda"),
                        rasa=norm_rasa(vars_["rasa"].get()), pol=pol.get(),
                        datum_rodjenja=parsiraj_datum(dat).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if dat else "",
                        otac=o, majka=mj, status=("obrisano" if red and red.get("status") == "obrisano"
                                                  else "aktivno" if akt.get() else "neaktivno"),
                        stado=vars_["stado"].get().strip(), poreklo=vars_["poreklo"].get().strip(),
                        poreklo_od=vars_["poreklo_od"].get().strip())
            if red:
                staro = red["id"]
                if staro != nid:
                    self.ist.preimenuj(staro, nid)
                    self.pods.preimenuj(staro, nid)
                    self.ist.dodaj(nid, AUTO, (f"Tag changed: {staro} → {nid}" if EN else f"Oznaka promenjena: {staro} → {nid}"), automatski=True)
                red["id"] = nid
                if norm(red.get("markica")) != norm(mk):
                    self.primeni_markicu(red, mk, zapamti=True)
                nazivi_polja = dict(vrsta="vrsta", rasa="rasa", pol="pol", datum_rodjenja=("date of birth" if EN else "datum rođenja"),
                                    otac=("sire" if EN else "otac"), majka=("dam" if EN else "majka"), status="status", stado=("herd" if EN else "stado"),
                                    poreklo="poreklo", poreklo_od=("origin from" if EN else "poreklo od"))
                promene = [f"{n}: {red.get(k) or '–'} → {novi.get(k) or '–'}" for k, n in nazivi_polja.items()
                           if (red.get(k) or "") != (novi.get(k) or "")]
                if promene:
                    self.ist.dodaj(nid, AUTO, ("Details changed – " if EN else "Izmena podataka – ") + "; ".join(promene), automatski=True)
                red.update(novi)
                if staro != nid:
                    for r in self.tab.redovi:
                        if r.get("otac") == staro:
                            r["otac"] = nid
                        if r.get("majka") == staro:
                            r["majka"] = nid
            else:
                novi["uneto"] = sada()
                self.tab.redovi.append(novi)
                self.ist.dodaj(nid, AUTO, ("Animal added to the records" if EN else "Grlo upisano u evidenciju") +
                               (f" ({novi['poreklo']}{' – ' + novi['poreklo_od'] if novi['poreklo_od'] else ''})"
                                if novi["poreklo"] else ""), automatski=True)
                if dat:     # rodjenje se upisuje i u istoriju roditelja
                    for rod, drugi in ((mj, o), (o, mj)):
                        rid = self.model.nadji(rod) if rod else None
                        if rid and not self.model.A[rid]["osnivac"]:
                            self.ist.dodaj(rid, ("Birth" if EN else "Porođaj") if rod == mj else ("Offspring" if EN else "Potomak"),
                                           (f"Offspring born {nid} ({'male' if pol.get() == 'm' else 'female'})" if EN else f"Rođen potomak {nid} ({'muško' if pol.get() == 'm' else 'žensko'})"),
                                           datum=parsiraj_datum(dat).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")),
                                           partner=self.model.nadji(drugi) or drugi or "", automatski=True)
            self.pod["poslednje"] = dict(vrsta=novi["vrsta"], rasa=novi["rasa"], stado=novi["stado"])
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            self.promena((f"Saved: {nid}" if EN else f"Sačuvano: {nid}"))
            if dalje:
                self.forma()

        def obrisi():
            if self.obrisi_grla([red["id"]], parent=win):
                win.destroy()

        fb = tk.Frame(win, bg=SURF)
        fb.pack(fill="x", padx=26, pady=(0, 20))
        tk.Frame(win, bg=LINE, height=1).place(in_=fb, relx=0, y=-10, relwidth=1)
        if red and red.get("status") != "obrisano":
            self.btn(fb, ("Delete animal" if EN else "Obriši grlo"), obrisi, "Danger").pack(side="left")
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        if not red:
            self.btn(fb, ("Save and add another" if EN else "Sačuvaj i dodaj još"), lambda: sacuvaj(True)).pack(side="right", padx=8)
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=(0, 8) if red else 0)
        win.bind("<Return>", lambda e: sacuvaj())
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 2)
        win.geometry(f"+{x}+{y}")
        (e_id if not v.get("id") else vr).focus_set()
