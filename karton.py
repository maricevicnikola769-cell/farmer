"""Karton grla, rodoslovno stablo, potomci, bočni srodnici i forma za upis/izmenu grla."""
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from osnova import EN
from jezik import AUTO, GRUPE, POREKLA, T, VRSTE, namene_za
from podaci import (fmt_datum, fmt_starost, nazivi, norm, norm_rasa, parsiraj_datum, pct, rasa_potomka, sada,
    autohtona_rasa, slobodna_oznaka, sort_key, starost_meseci, vrsta_norm)
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
        win.title((T(f"Karton grla {x}", f"Animal card {x}")))
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
                self.lbl(t, (T(f"otac {ro_ or '?'} × majka {rm_ or '?'}", f"sire {ro_ or '?'} × dam {rm_ or '?'}")), 9, fg=INK2).pack(anchor="w")
        sast = m.sastav(x)
        if not a["osnivac"] and (len(sast) > 1 or a.get("udeo")):     # melez: udeo krvi po rasama i generacija ukrštanja
            from rodoslov import tekst_udela
            self.lbl(t, T("Udeo krvi: ", "Breed share: ") + tekst_udela(sast, pct) + f" · {m.generacija_ukrstanja(x)[0]}",
                     9, fg=INK2, wraplength=280, justify="left").pack(anchor="w")
        self.lbl(t, (T("poznat samo kao roditelj", "known only as a parent")) if a["osnivac"] else (T("obrisano (čuva se u rodoslovu)", "deleted (kept in the pedigree)"))
                 if a.get("obrisano") else (T("u zapatu", "in herd")) if a["aktivno"] else (T("nije u zapatu", "not in herd")),
                 9, fg=BAD if a.get("obrisano") else INK2).pack(anchor="w")
        if a.get("napomena"):                   # napomena o grlu – uvek na vrhu kartona
            nf = tk.Frame(b, bg="#FCEFD2", highlightthickness=1, highlightbackground="#E0B860")
            nf.pack(fill="x", pady=(14, 0))
            self.lbl(nf, "⚠  " + a["napomena"], 11, "bold", fg="#7A4D00", bg="#FCEFD2", wraplength=330,
                     justify="left").pack(side="left", anchor="w", padx=12, pady=8)
            if not a["osnivac"]:
                lk = self.lbl(nf, T("izmeni", "edit"), 9, "bold", fg=BRAND, bg="#FCEFD2", cursor="hand2")
                lk.pack(side="right", padx=12)
                lk.bind("<Button-1>", lambda e: self.forma(x))
        from dnk import provera_porekla
        pp = provera_porekla(self.ist, x)
        if pp and (pp[0] is False or pp[1] is False):      # DNK test isključio upisanog oca ili majku – odmah na vrhu
            o_, m_ = m.P.get(x, (None, None))
            delovi = ([T(f"otac {o_ or '?'}", f"sire {o_ or '?'}")] if pp[0] is False else []) + \
                     ([T(f"majka {m_ or '?'}", f"dam {m_ or '?'}")] if pp[1] is False else [])
            df = tk.Frame(b, bg=BAD_BG, highlightthickness=1, highlightbackground=BAD)
            df.pack(fill="x", pady=(10, 0))
            self.lbl(df, "🧬 " + T("DNK test isključio: ", "DNA test excluded: ") + ", ".join(delovi) + T(" – proveri roditelje.", " – check the parents."),
                     10, "bold", fg=BAD, bg=BAD_BG, wraplength=380, justify="left").pack(anchor="w", padx=12, pady=8)

        def sekcija(naslov):
            self.lbl(b, naslov, 10, "bold").pack(anchor="w", pady=(18, 6))
            fr = tk.Frame(b, bg=SURF)
            fr.pack(anchor="w", fill="x")
            return fr

        if a["osnivac"]:
            self.lbl(b, (T("Ovo grlo je upisano samo kao roditelj. Dodaj ga kao grlo ako želiš da upišeš\n"
                        "njegove podatke i pretke.", "This animal is entered only as a parent. Add it as an animal if you want to enter\n"
                        "its details and ancestors.")), 10, fg=INK2, justify="left").pack(anchor="w", pady=(14, 8))
            self.btn(b, (T(f"Dodaj {x} kao grlo", f"Add {x} as an animal")), lambda: (win.destroy(), self.forma(preset=dict(
                id=x, pol=a["pol"], vrsta=a["vrsta"]))), "Primary").pack(anchor="w")
        else:
            kv = tk.Frame(b, bg=SURF)
            kv.pack(fill="x", pady=(16, 0))
            st = starost_meseci(a["datum"])
            mr = tk.Frame(kv, bg=SURF)
            mr.grid(row=0, column=1, sticky="w", padx=16, pady=3)
            self.lbl(mr, a["markica"] or "–", 10, "bold").pack(side="left")
            lnk = self.lbl(mr, (T("promeni", "change")), 9, "bold", fg=BRAND, cursor="hand2")
            lnk.pack(side="left", padx=10)
            lnk.bind("<Button-1>", lambda e: self.promena_markice(x, parent=win))
            if a.get("rfid"):                     # elektronski broj ispod markice (manjim slovima)
                self.lbl(kv, "RFID " + a["rfid"], 8, fg=INK2).grid(row=0, column=1, sticky="sw", padx=16, pady=(22, 0))
            por = a["poreklo"] + (f" – {a['poreklo_od']}" if a["poreklo_od"] else "") if a["poreklo"] else a["poreklo_od"]
            self.lbl(kv, (T("Poreklo", "Origin")), 10, fg=INK2).grid(row=6, column=0, sticky="nw", pady=3)
            self.lbl(kv, por or (T("nije upisano", "not entered")), 10, "bold" if por else "normal", fg=INK if por else INK2,
                     wraplength=260, justify="left").grid(row=6, column=1, sticky="w", padx=16, pady=3)
            if a["stare"]:
                self.lbl(kv, (T("Ranije markice", "Previous ear tags")), 10, fg=INK2).grid(row=5, column=0, sticky="nw", pady=3)
                self.lbl(kv, ", ".join(a["stare"]), 10, fg=INK2, wraplength=260, justify="left").grid(
                    row=5, column=1, sticky="w", padx=16, pady=3)
            for i, (k, v) in enumerate((((T("Ušna markica", "Ear tag")), None), ((T("Vrsta", "Species")), a["vrsta"] + (f"  ·  {a['namena']}" if a.get("namena") else "")
                                         + ((T("  ·  autohtona rasa", "  ·  native breed")) if a.get("autohtona") else "")),
                                        ((T("Rođeno", "Born")), (fmt_datum(a["datum"]) + (f"  ({fmt_starost(st)})" if st is not None else ""))
                                         if a["datum"] else "–"),
                                        ((T("Stado", "Herd")), a["stado"] or "–"))):
                self.lbl(kv, k, 10, fg=INK2).grid(row=i, column=0, sticky="w", pady=3)
                if v is not None and k != (T("Stado", "Herd")):
                    self.lbl(kv, v, 10, "bold").grid(row=i, column=1, sticky="w", padx=16, pady=3)
            sr = tk.Frame(kv, bg=SURF)
            sr.grid(row=3, column=1, sticky="w", padx=16, pady=3)
            self.lbl(sr, a["stado"] or "–", 10, "bold").pack(side="left")
            lns = self.lbl(sr, (T("promeni", "change")), 9, "bold", fg=BRAND, cursor="hand2")
            lns.pack(side="left", padx=10)
            lns.bind("<Button-1>", lambda e: self.promena_stada([x], parent=win))
            f = m.inbr(x)
            self.lbl(kv, (T("Inbriding", "Inbreeding")), 10, fg=INK2).grid(row=4, column=0, sticky="w", pady=3)
            self.badge(kv, pct(f), BAD if f > self.prag else WARN if f > self.prag / 2 else OK if f else INK2).grid(
                row=4, column=1, sticky="w", padx=16, pady=3)
            kar = self.opis_karence(x)
            if kar:
                self.lbl(kv, (T("Karenca", "Withdrawal")), 10, fg=BAD).grid(row=7, column=0, sticky="nw", pady=3)
                self.lbl(kv, kar, 10, "bold", fg=BAD, wraplength=260, justify="left").grid(
                    row=7, column=1, sticky="w", padx=16, pady=3)

        o, mj = m.P[x]
        fr = sekcija((T("Roditelji", "Parents")))
        for p, t in ((o, (T("otac nepoznat", "sire unknown"))), (mj, (T("majka nepoznata", "dam unknown")))):
            if p:
                self.cip(fr, p, lambda p=p: self.karton(p), siv=m.A[p]["osnivac"]).pack(side="left", padx=(0, 6))
            else:
                self.lbl(fr, f" {t} ", 9, fg=INK2, bg=SURF2).pack(side="left", padx=(0, 6))
        dede = [r for p in (o, mj) if p for r in m.P.get(p, ()) if r]
        if dede:
            fr = sekcija((T("Dede i babe", "Grandparents")))
            for d in dede:
                self.cip(fr, d, lambda d=d: self.karton(d), siv=m.A[d]["osnivac"]).pack(side="left", padx=(0, 6))
        if a["pol"] == "z" and not a["osnivac"]:
            pl = self.plodnost(x)
            if pl["porodjaja"] or pl["parenja"]:
                fr = sekcija(T("Plodnost", "Fertility"))
                tab_ = tk.Frame(fr, bg=SURF2)
                tab_.pack(fill="x")
                for i, (k_, v_) in enumerate((
                        (T("Porođaja", "Births"), pl["porodjaja"]),
                        (T("Rođeno živih", "Born alive"), f"{pl['zivih']}" + (T(f"  (prosek {pl['prosek']:.1f} po porođaju)".replace(".", ","),
                                                                                  f"  (average {pl['prosek']:.1f} per birth)") if pl["porodjaja"] else "")),
                        (T("Mrtvorođenih", "Stillborn"), pl["mrtvih"] or "–"),
                        (T("Razmak između porođaja", "Interval between births"), T(f"{round(pl['razmak'])} dana", f"{round(pl['razmak'])} days") if pl["razmak"] else "–"),
                        (T("Parenja / neuspela", "Matings / failed"), f"{pl['parenja']} / {pl['neuspela']}"),
                        (T("Prvi porođaj sa", "First birth at"), T(f"{pl['prvi_mes']} meseci", f"{pl['prvi_mes']} months") if pl["prvi_mes"] is not None else "–"))):
                    self.lbl(tab_, k_, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 10), pady=2)
                    self.lbl(tab_, str(v_), 9, "bold", bg=SURF2).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        udeli = [(d, p) for d, p in m.udeli_predaka(x) if p not in (o, mj)][:6]
        if udeli:
            fr = sekcija((T("Udeo gena od predaka", "Share of genes from ancestors")))
            for d, p in udeli:
                r = tk.Frame(fr, bg=SURF)
                r.pack(fill="x", pady=2)
                self.cip(r, p, lambda p=p: self.karton(p), siv=m.A[p]["osnivac"]).pack(side="left")
                self.lbl(r, pct(d), 10, "bold", width=7, anchor="e").pack(side="right")
                ttk.Progressbar(r, style="Green.Horizontal.TProgressbar", maximum=100, value=d * 100).pack(
                    side="left", fill="x", expand=True, padx=10)
        if m.putanje(x):
            lk = self.lbl(b, (T(f"Prikaži sve pretke ({len(m.putanje(x))})  ›", f"Show all ancestors ({len(m.putanje(x))})  ›")), 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(anchor="w", pady=(6, 0))
            lk.bind("<Button-1>", lambda e: self.stablo(x, 4, "svi"))
        n_boc = len(self.bocni_srodnici(x))
        if n_boc:
            lb_ = self.lbl(b, (T(f"Bočni srodnici – braća, sestre, rođaci ({n_boc})  ›", f"Collateral relatives – siblings, cousins ({n_boc})  ›")), 9, "bold", fg=BRAND, cursor="hand2")
            lb_.pack(anchor="w", pady=(4, 0))
            lb_.bind("<Button-1>", lambda e: self.stablo(x, 4, "bocni"))
        pot = sorted((k for k, pr in m.P.items() if x in pr), key=sort_key)
        fr = sekcija((T(f"Potomci ({len(pot)})", f"Offspring ({len(pot)})")))
        if not pot:
            self.lbl(fr, (T("nema upisanih", "none recorded")), 10, fg=INK2).pack(side="left")
        red = None
        for i, p in enumerate(pot[:40]):
            if i % 6 == 0:
                red = tk.Frame(fr, bg=SURF)
                red.pack(anchor="w", pady=2)
            self.cip(red, p, lambda p=p: self.karton(p)).pack(side="left", padx=(0, 6))

        n_svih = sum(len(v) for v in self.potomci_po_kolenima(x).values())
        if n_svih > len(pot):
            lpo = self.lbl(b, (T(f"Svi potomci – deca, unuci, praunuci ({n_svih})  ›", f"All descendants – children, grandchildren ({n_svih})  ›")), 9, "bold", fg=BRAND, cursor="hand2")
            lpo.pack(anchor="w", pady=(4, 0))
            lpo.bind("<Button-1>", lambda e: self.stablo(x, 4, "potomci"))
        if a["aktivno"] and a["pol"] and not a["osnivac"]:
            kand = sorted((m.kinship(x, k["id"]), k["id"]) for k in m.grla(True)
                          if k["id"] != x and k["vrsta"] == a["vrsta"] and k["pol"] != a["pol"])[:5]
            if kand:
                fr = sekcija((T("Najbolji partneri", "Best partners")))
                for f, k in kand:
                    r = tk.Frame(fr, bg=SURF)
                    r.pack(fill="x", pady=3)
                    self.cip(r, k, lambda k=k: self.karton(k)).pack(side="left")
                    self.lbl(r, (T(f"geni {pct(m.r(x, k))}", f"genes {pct(m.r(x, k))}")), 9, fg=INK2).pack(side="left", padx=8)
                    t, boja = procena(f, self.prag)
                    self.badge(r, t, boja).pack(side="right")
                    self.lbl(r, pct(f), 10, "bold").pack(side="right", padx=10)

        if not a["osnivac"]:
            obv = [o for o in self.obavestenja(x) if o["grlo"] == x or o.get("podsetnik")]
            fr = sekcija((T(f"Obaveštenja ({len(obv)})", f"Notifications ({len(obv)})")))
            if not obv:
                self.lbl(fr, (T("nema", "none")), 10, fg=INK2).pack(anchor="w")
            for o in obv[:5]:
                self.red_obavestenja(fr, o, kompakt=True)
            lp = self.lbl(b, (T("+ Dodaj podsetnik", "+ Add reminder")), 9, "bold", fg=BRAND, cursor="hand2")
            lp.pack(anchor="w", pady=(4, 0))
            lp.bind("<Button-1>", lambda e: self.podsetnik_forma(x, parent=win))
            zap = self.ist.za(x)
            fr = sekcija((T(f"Istorija ({len(zap)})", f"History ({len(zap)})")))
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
                    w.bind("<Button-1>", lambda e, n=naziv: (self.ui.setdefault("ist_" + x, {"vrsta": (T("Svi događaji", "All events")),
                           "auto": True, "q": ""}).update(grupa=n, vrsta=(T("Svi događaji", "All events"))), self.istorija_prozor(x)))
            if not zap:
                self.lbl(fr, (T("nema zapisa", "no records")), 10, fg=INK2).pack(anchor="w")
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
            l1 = self.lbl(lr, (T("+ Dodaj događaj", "+ Add event")), 9, "bold", fg=BRAND, cursor="hand2")
            l1.pack(side="left")
            l1.bind("<Button-1>", lambda e: self.dogadjaj_forma(x, parent=win))
            l2 = self.lbl(lr, (T("Cela istorija  ›", "Full history  ›")), 9, "bold", fg=BRAND, cursor="hand2")
            l2.pack(side="left", padx=16)
            l2.bind("<Button-1>", lambda e: self.istorija_prozor(x))

        if not a["osnivac"]:
            self.prirast_na_kartonu(b, x)
            self.mlecnost_na_kartonu(b, x)
            self.dnk_na_kartonu(b, x)
        act1 = tk.Frame(b, bg=SURF)
        act1.pack(anchor="w", pady=(24, 0))
        if not a["osnivac"]:
            self.btn(act1, (T("Izmeni podatke", "Edit details")), lambda: (win.destroy(), self.forma(x)), "Primary").pack(side="left", padx=(0, 8))
        self.btn(act1, (T("Poreklo – stablo", "Pedigree – tree")), lambda: self.stablo(x)).pack(side="left")
        if not a["osnivac"]:
            act = tk.Frame(b, bg=SURF)
            act.pack(anchor="w", pady=(8, 0))
            dete = dict(vrsta=a["vrsta"], rasa=a["rasa"], namena=a.get("namena", ""), autohtona=a.get("autohtona", ""),
                        stado=a["stado"], status="aktivno")
            dete["otac" if a["pol"] == "m" else "majka"] = x
            self.btn(act, (T("Upiši potomka", "Add offspring")), lambda: (win.destroy(), self.forma(preset=dete))).pack(side="left", padx=(0, 8))
            if a.get("obrisano"):
                self.btn(act, (T("Vrati u stado", "Restore to herd")), lambda: self.vrati_grla([x])).pack(side="left")
            else:
                if a["pol"]:
                    self.btn(act, (T("Svi partneri", "All partners")), lambda: (win.destroy(), self.idi_na_pretragu(x))).pack(side="left")
                self.btn(act, (T("Obriši", "Delete")), lambda: self.obrisi_grla([x], parent=win), "Danger").pack(side="left", padx=8)
        win.lift()


    @staticmethod
    def naziv_gen(g):
        return {1: (T("roditelj", "parent")), 2: (T("deda / baba", "grandparent")), 3: (T("pradeda / prababa", "great-grandparent")), 4: (T("čukundeda / čukunbaba", "great-great-grandparent"))}.get(
            g, (T(f"{g}. koleno", f"generation {g}")))


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
        win.title((T(f"Poreklo grla {x}", f"Pedigree of animal {x}")))
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
        self.lbl(t, (T(f"Poreklo – {m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}", f"Pedigree – {m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}")), 14, "bold").pack(anchor="w")
        por = a["poreklo"] + (f" – {a['poreklo_od']}" if a["poreklo_od"] else "") if a["poreklo"] else a["poreklo_od"]
        info = (T(f"{len(put)} poznatih predaka u {dubina} generacija   ·   inbriding {pct(m.inbr(x))}", f"{len(put)} known ancestors in {dubina} generations   ·   inbreeding {pct(m.inbr(x))}"))
        self.lbl(t, (f"{por}   ·   " if por else "") + info, 10, fg=INK2).pack(anchor="w")

        seg = tk.Frame(win, bg=BG)
        seg.pack(fill="x", padx=24, pady=(4, 8))
        sg = tk.Frame(seg, bg=SURF2)
        sg.pack(side="left")
        n_boc = len(self.bocni_srodnici(x))
        n_pot = sum(len(v) for v in self.potomci_po_kolenima(x).values())
        for k, tx in (("stablo", (T("Stablo", "Tree"))), ("svi", (T(f"Svi preci ({len(put)})", f"All ancestors ({len(put)})"))),
                      ("potomci", (T(f"Potomci ({n_pot})", f"Descendants ({n_pot})"))), ("bocni", (T(f"Bočni srodnici ({n_boc})", f"Collateral relatives ({n_boc})")))):
            akt = tab == k
            lb = tk.Label(sg, text=tx, font=self.f(10, "bold"), bg=SURF if akt else SURF2, fg=INK if akt else INK2,
                          padx=14, pady=6, cursor="hand2")
            lb.pack(side="left", padx=3, pady=3)
            lb.bind("<Button-1>", lambda e, k=k: self.stablo(x, gen, k))
        if tab == "stablo" and dubina >= 2:
            desno = tk.Frame(seg, bg=BG)
            desno.pack(side="right")
            self.lbl(desno, (T("Prikaži generacija:", "Generations shown:")), 9, "bold", fg=INK2).pack(side="left", padx=(0, 6))
            gv = tk.StringVar(value=str(gen - 1))
            cg = ttk.Combobox(desno, textvariable=gv, values=[str(i) for i in range(1, min(7, dubina) + 1)],
                              state="readonly", width=4, font=self.f(10))
            cg.pack(side="left")
            cg.bind("<<ComboboxSelected>>", lambda e: self.stablo(x, int(gv.get()) + 1, "stablo"))

        # preci koji se ponavljaju – kroz CEO rodoslov, ne samo prikazane generacije
        leg = tk.Frame(win, bg=BG)
        leg.pack(fill="x", padx=24, pady=(0, 6))
        if not put:
            self.lbl(leg, (T("Za ovo grlo nisu upisani roditelji.", "No parents are entered for this animal.")), 10, fg=INK2).pack(anchor="w")
        elif ponavlja:
            opis = ", ".join((T(f"{y} ({sum(gs.values())}×, gen. {' i '.join(str(g) for g in sorted(gs))})", f"{y} ({sum(gs.values())}×, gen. {' and '.join(str(g) for g in sorted(gs))})"))
                             for y, gs in sorted(ponavlja.items(), key=lambda t: (min(t[1]), sort_key(t[0]))))
            self.lbl(leg, (T("Preci koji se ponavljaju u celom rodoslovu (uzrok inbridinga): ", "Ancestors repeated in the whole pedigree (cause of inbreeding): ")) + opis, 9, fg=BAD,
                     wraplength=980, justify="left").pack(anchor="w")
            dalji = [y for y, gs in ponavlja.items() if min(gs) >= gen]
            if tab == "stablo" and dalji:
                self.lbl(leg, (T(f"Neki od njih su dalje od prikazanih generacija ({', '.join(sorted(dalji, key=sort_key))})"
                              " – povećaj broj generacija ili otvori karticu „Svi preci“.", f"Some of them are beyond the generations shown ({', '.join(sorted(dalji, key=sort_key))})"
                              " – increase the number of generations or open the \"All ancestors\" tab.")), 9, fg=WARN,
                         wraplength=980, justify="left").pack(anchor="w")
        else:
            self.lbl(leg, (T("Nijedan predak se ne ponavlja u celom poznatom rodoslovu.", "No ancestor is repeated in the whole known pedigree.")), 9, fg=OK).pack(anchor="w")

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
        nazivi_k = {1: (T("Deca", "Children")), 2: (T("Unuci", "Grandchildren")), 3: (T("Praunuci", "Great-grandchildren")), 4: (T("Čukununuci", "Great-great-grandchildren"))}
        opis = " · ".join((T(f"{nazivi_k.get(k, f'{k}. koleno')}: {len(v)}", f"{nazivi_k.get(k, f'generation {k}')}: {len(v)}")) for k, v in po.items())
        self.lbl(win, ((T(f"Ukupno {ukupno} potomaka – {opis}.", f"In total {ukupno} descendants – {opis}.")) if ukupno else (T("Nema upisanih potomaka.", "No descendants recorded."))) +
                 (T(" Udeo gena = koliko gena potomak nosi od ovog grla.", " Share of genes = how many genes the descendant carries from this animal.")), 9, fg=INK2, wraplength=980,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not ukupno and not legla:
            self.napomena(body, (T("Ovo grlo još nema upisanih potomaka.", "This animal has no recorded descendants yet.")), ok=True)
            return
        wrap, tv = self.tabela(body, [("id", (T("Potomak", "Offspring")), 200), ("odnos", (T("Drugi roditelj", "Other parent")), 200),
                                      ("pol", (T("Pol", "Sex")), 80), ("geni", (T("Udeo gena", "Share of genes")), 95, "e"), ("rasa", (T("Rasa", "Breed")), 120),
                                      ("rod", (T("Rođen", "Born")), 95), ("st", "Status", 140)], visina=16)
        wrap.pack(fill="both", expand=True)
        tv.tag_configure("grupa", font=self.f(10, "bold"), background=SURF2)
        for k, lst in po.items():
            gr = tv.insert("", "end", text=(T(f"  {nazivi_k.get(k, f'{k}. koleno')} ({len(lst)})", f"  {nazivi_k.get(k, f'generation {k}')} ({len(lst)})")), open=k <= 2,
                           tags=["grupa"])
            for y in lst:
                p = m.A[y]
                o, mj = m.P.get(y, (None, None))
                if k == 1:
                    drugi = mj if o == x else o
                    dr = (T(f"{'majka' if o == x else 'otac'} {drugi}", f"{'dam' if o == x else 'sire'} {drugi}")) if drugi else (T("nepoznat", "unknown"))
                else:
                    preko = [r for r in (o, mj) if r and (r in po.get(k - 1, []))]
                    dr = (T(f"preko {', '.join(preko)}", f"through {', '.join(preko)}")) if preko else "–"
                st = ((T("obrisano", "deleted")) if p.get("obrisano") else (T("u zapatu", "in herd")) if p["aktivno"] else (T("van zapata", "out of herd")))
                tv.insert(gr, "end", iid=y, text="  " + y, image=self.img_tag, values=(
                    dr, m.pol_naziv(y), pct(m.doprinos(y, x)), p["rasa"] or "–",
                    fmt_datum(p["datum"]) or "–", st), tags=[] if p["aktivno"] else ["off"])
        if legla:
            gr = tv.insert("", "end", text=(T("  Rođeni, još bez minđuše", "  Born, no ear tag yet")), open=True, tags=["grupa"])
            for z in legla:
                uk, dd, vec = self.leglo(z)
                majka, otac = self.roditelji_parenja(z)
                tv.insert(gr, "end", text=(T(f"  {uk - len(vec)} mladih", f"  {uk - len(vec)} young")), values=(
                    f"{majka or '?'} × {otac or '?'}", "–", "50,0%", "–", dd, (T("čeka upis u listu", "waiting for entry in the list"))))
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, (T("Dvoklik na potomka otvara njegov karton.", "Double-click a descendant to open its card.")), 9, fg=INK2).pack(anchor="w", pady=(8, 0))


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
                    rez[s] = (T("po ocu", "paternal"))
                elif mj and sm == mj:
                    rez[s] = (T("po majci", "maternal"))
            return rez

        def naziv(s, z_, m_):
            return m_ if m.A.get(s, {}).get("pol") == "m" else z_ if m.A.get(s, {}).get("pol") == "z" else f"{m_} / {z_}"

        rez, vidjeni = [], {x}
        predci = m.preci(x)
        # 1) braća i sestre
        for s, tip in sorted(braca(x).items(), key=lambda t: (t[1] != "pun", sort_key(t[0]))):
            if tip == "pun":
                ime = naziv(s, T("puna sestra", "full sister"), T("pun brat", "full brother"))
            else:
                ime = naziv(s, T("polusestra", "half-sister"), T("polubrat", "half-brother"))
            rez.append((T("Braća i sestre", "Siblings"), s, ime))
            vidjeni.add(s)
        # dvostruki odnos: brat/sestra koji je ujedno i dete brata/sestre
        sib = set(braca(x))
        for i, (g, y, op) in enumerate(rez):
            if any(p_ in sib for p_ in m.P.get(y, (None, None)) if p_):
                rez[i] = (g, y, op + (T(f", ujedno {naziv(y, 'nećaka', 'nećak')}", f", also {naziv(y, 'niece', 'nephew')}")))
        # 2) deca braće i sestara
        for s in list(braca(x)):
            for d in sorted(deca.get(s, set()) - vidjeni, key=sort_key):
                rez.append(((T("Nećaci (deca braće i sestara)", "Nephews and nieces (children of siblings)")), d, (T(f"dete od {s}", f"child of {s}"))))
                vidjeni.add(d)
        # 3) braća i sestre roditelja
        o, mj = m.P.get(x, (None, None))
        strane = []
        for rod, strana, (mz, zz) in ((o, (T("po ocu", "paternal")), ((T("stric", "uncle")), (T("tetka", "aunt")))), (mj, (T("po majci", "maternal")), ((T("ujak", "uncle")), (T("tetka", "aunt"))))):
            if not rod:
                continue
            for s, tip in sorted(braca(rod).items(), key=lambda t: sort_key(t[0])):
                if s in vidjeni or s in predci:
                    continue
                rez.append(((T("Braća i sestre roditelja", "Siblings of parents")), s, (T(f"{naziv(s, zz, mz)} {strana}", f"{naziv(s, zz, mz)} ({strana})")) +
                            ("" if tip == "pun" else (T(" (polu)", " (half)")))))
                vidjeni.add(s)
                strane.append((s, strana))
        # 4) prvi rođaci (deca braće i sestara roditelja)
        for s, strana in strane:
            for d in sorted(deca.get(s, set()) - vidjeni, key=sort_key):
                if d in predci:
                    continue
                rez.append(((T("Prvi rođaci", "First cousins")), d, (T(f"dete od {s} ({strana})", f"child of {s} ({strana})"))))
                vidjeni.add(d)
        return rez


    def tab_bocni(self, win, x):
        m = self.model
        sr = self.bocni_srodnici(x)
        self.lbl(win, (T("Bočni srodnici nisu ni preci ni potomci, ali imaju zajedničke pretke sa ovim grlom. "
                      "Pazi pri parenju – visok procenat zajedničkih gena znači i veći inbriding mladih.", "Collateral relatives are neither ancestors nor descendants, but share ancestors with this animal. "
                      "Be careful when mating – a high share of genes also means higher inbreeding of the young.")), 9,
                 fg=INK2, wraplength=980, justify="left").pack(anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not sr:
            self.napomena(body, (T("Nema poznatih bočnih srodnika (braće, sestara, rođaka…) prema upisanom rodoslovu.", "No known collateral relatives (siblings, cousins…) according to the recorded pedigree.")),
                          ok=True)
            return
        wrap, tv = self.tabela(body, [("id", (T("Srodnik", "Relative")), 240), ("odnos", (T("Odnos", "Relation")), 260), ("geni", (T("Zajednički geni", "Shared genes")), 120, "e"),
                                      ("f", (T("Inbriding mladih", "Inbreeding of young")), 120, "e"), ("rasa", (T("Rasa", "Breed")), 110),
                                      ("rod", (T("Rođen", "Born")), 70), ("st", "Status", 140)], visina=16)
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
            st = ((T("poznat samo kao roditelj", "known only as a parent")) if p.get("osnivac") else (T("obrisano", "deleted")) if p.get("obrisano")
                  else (T("u zapatu", "in herd")) if p.get("aktivno") else (T("van zapata", "out of herd")))
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
        self.lbl(body, (T("Crveno = suprotan pol u zapatu sa kojim bi mladi imali inbriding iznad granice. "
                       "Dvoklik otvara karton.", "Red = opposite sex in the herd with which the young would have inbreeding above the limit. "
                       "Double-click opens the card.")), 9, fg=INK2).pack(anchor="w", pady=(8, 0))


    def svi_preci(self, win, x, put, ponavlja, dubina):
        m = self.model
        kom = m.kompletnost(x, dubina)
        if kom:
            self.lbl(win, (T("Kompletnost rodoslova:  ", "Pedigree completeness:  ")) + "   ".join(
                (T(f"{g}. gen {n}/{od}", f"gen. {g}: {n}/{od}")) for g, n, od in kom), 9, fg=INK2, wraplength=980, justify="left").pack(
                anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not put:
            return
        wrap, tv = self.tabela(body, [("id", (T("Predak", "Ancestor")), 110), ("gen", (T("Generacija", "Generation")), 220), ("put", (T("Puta", "Times")), 60, "e"),
                                      ("udeo", (T("Udeo gena", "Share of genes")), 95, "e"), ("pol", (T("Pol", "Sex")), 75), ("mk", (T("Markica", "Ear tag")), 115),
                                      ("rasa", (T("Rasa", "Breed")), 95), ("st", "Status", 160)], visina=16)
        wrap.pack(fill="both", expand=True)
        redovi = sorted(put.items(), key=lambda t: (-m.doprinos(x, t[0]), min(t[1]), sort_key(t[0])))
        for i, (y, gs) in enumerate(redovi):
            p = m.A[y]
            n = sum(gs.values())
            gen_txt = (f"{min(gs)}.  {self.naziv_gen(min(gs))}" if len(gs) == 1
                       else ", ".join(str(g) for g in sorted(gs)) + (T(". generacija", " generations")))
            st = ((T("poznat samo kao roditelj", "known only as a parent")) if p["osnivac"] else (T("obrisano", "deleted")) if p.get("obrisano")
                  else (T("u zapatu", "in herd")) if p["aktivno"] else (T("van zapata", "out of herd")))
            tags = (["odd"] if i % 2 else []) + (["bad"] if y in ponavlja else []) + (["off"] if p["osnivac"] else [])
            tv.insert("", "end", iid=y, text="  " + y, image=self.img_tag_siv if p["osnivac"] else self.img_tag,
                      values=(gen_txt, f"{n}×", pct(m.doprinos(x, y)), m.pol_naziv(y), p["markica"] or "–",
                              p["rasa"] or "–", st), tags=tags)
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, (T("Crveno = predak se pojavljuje više puta.  Dvoklik otvara karton pretka.", "Red = the ancestor appears more than once.  Double-click opens the ancestor's card.")), 9, fg=INK2).pack(
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
        self.lbl(win, (T("Uz svakog pretka piše koliki deo gena grlo nosi od njega (zbir svih puteva). "
                      "Klik na pretka prikazuje njegovo poreklo, dvoklik otvara karton.", "Each ancestor shows what share of genes the animal carries from it (sum of all paths). "
                      "Click an ancestor to show its pedigree, double-click opens its card.")), 9, fg=INK2,
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
            nz = (T("Grlo", "Animal")) if g == 0 else {1: (T("Roditelji", "Parents")), 2: (T("Dede i babe", "Grandparents")), 3: (T("Pradede i prababe", "Great-grandparents")),
                                         4: (T("Čukundede i čukunbabe", "Great-great-grandparents"))}.get(g, (T(f"{g}. koleno", f"generation {g}")))
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
            uloga = "" if g == 0 else ((T("otac", "sire")) if i % 2 == 0 else (T("majka", "dam")))
            if not y:
                c.create_polygon(self.zaobljeno(x1, y1, x2, y2, 8), smooth=True, fill=BG, outline="#C3CBC4", dash=(4, 3))
                c.create_text(x1 + 14, cy, text=(T(f"{uloga} nepoznat{'a' if uloga == 'majka' else ''}", f"{uloga} unknown")) if uloga else "",
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
                c.create_text(x2 - 10, cy - 9, text=(T(f"{uloga} · {pct(m.doprinos(x, y))} gena", f"{uloga} · {pct(m.doprinos(x, y))} genes")), anchor="e",
                              font=self.f(8), fill=BAD if rep_ else INK2, tags=tag)
            sub = " · ".join(v for v in (p["markica"], p["rasa"]) if v)
            if p["datum"] and len(sub) + 7 <= 30:
                sub = (sub + " · " if sub else "") + str(p["datum"].year)
            sub = sub or ((T("poznat samo kao roditelj", "known only as a parent")) if p["osnivac"] else "")
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
        v = dict(red) if red else {"vrsta": posl.get("vrsta", (T("goveda", "cattle"))), "rasa": posl.get("rasa", ""),
                                   "stado": posl.get("stado", ""), "status": "", **(preset or {})}
        win = tk.Toplevel(self.root, bg=SURF)
        win.title((T("Izmena grla", "Edit animal")) if red else (T("Novo grlo", "New animal")))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, (T("Izmena grla", "Edit animal")) if red else (T("Novo grlo", "New animal")), 17, "bold").grid(row=0, column=0, columnspan=2,
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

        e_id = polje(1, 0, (T("Oznaka grla *", "Animal tag *")), "id", hint=(T("npr. K12 ili ime", "e.g. K12 or a name")))
        polje(1, 1, (T("Ušna markica", "Ear tag")), "markica", hint=(T("npr. RS 1234-5678", "e.g. UK 123456 700123")))
        vr = polje(2, 0, (T("Vrsta", "Species")), "vrsta", "combo", VRSTE)
        polje(2, 1, (T("Rasa", "Breed")), "rasa", "combo", sorted({a["rasa"] for a in sva if a["rasa"]}))

        pf = tk.Frame(b, bg=SURF)
        pf.grid(row=3, column=0, sticky="w", pady=6)
        self.lbl(pf, (T("Pol *", "Sex *")), 9, "bold", fg=INK2).pack(anchor="w")
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

        # namena rase (goveda, ovce, koze i svinje): mlečna / tovna / kombinovana, odnosno mesnata / masna / kombinovana
        nf = tk.Frame(b, bg=SURF)
        self.lbl(nf, (T("Namena rase *", "Breed purpose *")), 9, "bold", fg=INK2).pack(anchor="w")
        namena = tk.StringVar(value=v.get("namena", ""))
        cb_nam = ttk.Combobox(nf, textvariable=namena, width=26, font=self.f(10), state="readonly")
        cb_nam.pack(fill="x", pady=(4, 0))
        self.lbl(nf, (T("za goveda, ovce, koze i svinje", "cattle, sheep, goats and pigs")), 8, fg="#8A968D").pack(anchor="w")

        def crtaj_namenu(*_):
            izbori = namene_za(vrsta_norm(vars_["vrsta"].get()) or vars_["vrsta"].get())
            if izbori:
                cb_nam.config(values=izbori)
                if namena.get() and namena.get() not in izbori:
                    namena.set("")
                nf.grid(row=3, column=1, sticky="new", padx=(14, 0), pady=6)
            else:
                nf.grid_remove()
        crtaj_namenu()
        vars_["vrsta"].trace_add("write", crtaj_namenu)

        d = parsiraj_datum(v.get("datum_rodjenja"))
        v["datum_rodjenja"] = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if d else v.get("datum_rodjenja", "")
        polje(4, 0, (T("Datum rođenja", "Date of birth")), "datum_rodjenja", hint=(T("dan.mesec.godina, npr. 15.03.2022", "day/month/year, e.g. 15/03/2022")))
        polje(4, 1, (T("Stado / lokacija", "Herd / location")), "stado", "combo", sorted({a["stado"] for a in sva if a["stado"]}))
        w_otac = polje(5, 0, (T("Otac", "Sire")), "otac", "combo", sorted((a["id"] for a in m.A.values() if a["pol"] == "m"), key=sort_key),
              hint=(T("oznaka ili markica; prazno ako je nepoznat", "tag or ear tag; empty if unknown")))
        polje(5, 1, (T("Majka", "Dam")), "majka", "combo", sorted((a["id"] for a in m.A.values() if a["pol"] == "z"), key=sort_key),
              hint=(T("oznaka ili markica; prazno ako je nepoznata", "tag or ear tag; empty if unknown")))
        polje(6, 0, (T("Poreklo", "Origin")), "poreklo", "combo", POREKLA)
        polje(6, 1, (T("Od koga / odakle", "From whom / where")), "poreklo_od", "combo",
              sorted({a["poreklo_od"] for a in sva if a["poreklo_od"]}))

        def auto_rasa(*_):
            """Kad su upisani otac i majka različitih rasa, rasa postaje 'hibrid O×M'."""
            o_, m_ = m.nadji(vars_["otac"].get()), m.nadji(vars_["majka"].get())
            if not o_ or not m_:
                return
            predlog = rasa_potomka(m.A[o_]["rasa"], m.A[m_]["rasa"])
            sad = vars_["rasa"].get().strip().lower()
            if predlog and (not sad or sad.startswith(("hybrid" if EN else "hibrid")) or sad == (T("melez", "crossbred"))):
                vars_["rasa"].set(predlog)
        vars_["otac"].trace_add("write", auto_rasa)
        vars_["majka"].trace_add("write", auto_rasa)

        def namena_od_majke(*_):
            """Ako namena još nije izabrana, preuzmi je od majke."""
            mj_ = m.nadji(vars_["majka"].get())
            nm = m.A[mj_].get("namena", "") if mj_ else ""
            if nm and not namena.get() and nm in (cb_nam.cget("values") or ()):
                namena.set(nm)
        vars_["majka"].trace_add("write", namena_od_majke)
        hint_otac = self.lbl(w_otac.master, "", 8, "bold", fg=BRAND, wraplength=260, justify="left")
        hint_otac.pack(anchor="w")

        def otac_iz_stada(*_):
            """Otac nije upisan: mužjak iz stada majke (pušten sa ženkama) se predloži sam."""
            mj_ = m.nadji(vars_["majka"].get())
            k = m.muzjaci_u_stadu(mj_) if mj_ else []
            if not k or vars_["otac"].get().strip():
                hint_otac.config(text="")
                return
            if len(k) == 1:
                vars_["otac"].set(k[0])
                hint_otac.config(text=T(f"Otac: {k[0]} – mužjak iz stada majke ({m.A[mj_]['stado']})",
                                        f"Sire: {k[0]} – male in the dam's herd ({m.A[mj_]['stado']})"))
            else:
                w_otac.configure(values=k + [x_ for x_ in w_otac.cget("values") if x_ not in k])
                hint_otac.config(text=T(f"U stadu majke su mužjaci: {', '.join(k)} – izaberi oca",
                                        f"Males in the dam's herd: {', '.join(k)} – choose the sire"))
        vars_["majka"].trace_add("write", otac_iz_stada)
        stf = tk.Frame(b, bg=SURF)
        stf.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
        dva = tk.Frame(stf, bg=SURF)
        dva.pack(anchor="w", fill="x", pady=(0, 10))
        rf = tk.Frame(dva, bg=SURF)
        rf.grid(row=0, column=0, sticky="nw")
        self.lbl(rf, (T("Elektronski broj (RFID čitač)", "Electronic ID (RFID reader)")), 9, "bold", fg=INK2).pack(anchor="w")
        rfid_var = tk.StringVar(value=v.get("rfid", ""))
        ttk.Entry(rf, textvariable=rfid_var, width=28, font=self.f(10)).pack(anchor="w", pady=(4, 0))
        self.lbl(rf, (T("nije obavezno – klikni u polje i prisloni čitač", "optional – click in the field and hold the reader to the tag")),
                 8, fg="#8A968D", wraplength=230, justify="left").pack(anchor="w")
        nf = tk.Frame(dva, bg=SURF)
        nf.grid(row=0, column=1, sticky="nw", padx=(14, 0))
        self.lbl(nf, "⚠ " + T("Napomena o grlu", "Note about the animal"), 9, "bold", fg=INK2).pack(anchor="w")
        nap_var = tk.StringVar(value=v.get("napomena", ""))
        ttk.Entry(nf, textvariable=nap_var, width=28, font=self.f(10)).pack(anchor="w", pady=(4, 0))
        self.lbl(nf, T("vidi se svuda gde je grlo (npr. Agresivna, Ne muzi – lečenje)",
                       "shown wherever the animal appears (e.g. Aggressive, Do not milk – treatment)"),
                 8, fg="#8A968D", wraplength=230, justify="left").pack(anchor="w")
        autoh = tk.BooleanVar(value=bool(v.get("autohtona")))
        ttk.Checkbutton(stf, text=(T("Autohtona rasa", "Native (indigenous) breed")), variable=autoh,
                        style="Card.TCheckbutton").pack(anchor="w", pady=(0, 10))

        def predlozi_autohtonu(*_):
            if autohtona_rasa(vars_["rasa"].get()):
                autoh.set(True)
        vars_["rasa"].trace_add("write", predlozi_autohtonu)
        self.lbl(stf, (T("Status grla *", "Status *")), 9, "bold", fg=INK2).pack(anchor="w")
        pocetni = v.get("status", "")
        status = tk.StringVar(value="aktivno" if pocetni in ("aktivno", "obrisano") else "neaktivno" if pocetni else "")
        for vr_, tekst in (("aktivno", (T("Aktivno – grlo je na farmi", "Active – the animal is on the farm"))),
                           ("neaktivno", (T("Neaktivno – grlo nije na farmi (prodato, uginulo, pozajmljeno…)", "Inactive – not on the farm (sold, dead, on loan…)")))):
            ttk.Radiobutton(stf, text=tekst, value=vr_, variable=status, style="Card.TRadiobutton").pack(anchor="w", pady=(4, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def sacuvaj(dalje=False):
            nid = vars_["id"].get().strip()
            if not nid:
                err.config(text=(T("Upiši oznaku grla.", "Enter the animal's tag.")))
                e_id.focus_set()
                return
            prvobitno = nid
            if not red:                      # isto ime/oznaka već postoji -> sledeći broj po redu (Bela 2, Bela 3…)
                nid = slobodna_oznaka(nid, [r["id"] for r in self.tab.redovi])
            dup = next((r for r in self.tab.redovi if r["id"] == nid and r is not red), None)
            if dup:
                err.config(text=(T(f"Grlo {nid} već postoji.", f"Animal {nid} already exists.")) + ((T(" Obrisano je – vrati ga iz liste „Obrisana grla“.", " It is deleted – restore it from the \"Deleted animals\" list."))
                                                             if dup.get("status") == "obrisano" else ""))
                return
            mk = vars_["markica"].get().strip()
            if mk:
                zauzeto = self.markica_zauzeta(mk, red)
                if zauzeto:
                    err.config(text=zauzeto)
                    return
            rfid = " ".join(rfid_var.get().split())
            if rfid:
                zauzeto = self.rfid_zauzet(rfid, red)
                if zauzeto:
                    err.config(text=zauzeto)
                    return
            if pol.get() not in ("m", "z"):
                err.config(text=(T("Izaberi pol.", "Choose the sex.")))
                return
            izbori_nam = namene_za(vrsta_norm(vars_["vrsta"].get()) or vars_["vrsta"].get())
            if izbori_nam and not red and namena.get() not in izbori_nam:
                err.config(text=(T("Izaberi namenu rase (", "Choose the breed purpose (")) + " / ".join(izbori_nam) + ").")
                return
            if status.get() not in ("aktivno", "neaktivno"):
                err.config(text=(T("Izaberi da li je grlo aktivno (na farmi) ili neaktivno.", "Choose whether the animal is active (on the farm) or inactive.")))
                return
            dat = vars_["datum_rodjenja"].get().strip()
            if dat and not parsiraj_datum(dat):
                err.config(text=(T("Datum nije ispravan. Upiši ga kao 15.03.2022.", "The date is not valid. Enter it as 15/03/2022.")))
                return
            o, mj = vars_["otac"].get().strip(), vars_["majka"].get().strip()
            if nid in (o, mj):
                err.config(text=(T("Grlo ne može biti sopstveni roditelj.", "An animal cannot be its own parent.")))
                return
            novi = dict(id=nid, markica=mk, rfid=rfid, vrsta=vrsta_norm(vars_["vrsta"].get()) or (T("goveda", "cattle")),
                        rasa=norm_rasa(vars_["rasa"].get()), namena=namena.get() if izbori_nam else "",
                        autohtona="1" if autoh.get() else "", pol=pol.get(),
                        datum_rodjenja=parsiraj_datum(dat).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if dat else "",
                        otac=o, majka=mj, status=("obrisano" if red and red.get("status") == "obrisano"
                                                  else status.get()),
                        stado=vars_["stado"].get().strip(), poreklo=vars_["poreklo"].get().strip(),
                        poreklo_od=vars_["poreklo_od"].get().strip(), napomena=" ".join(nap_var.get().split()))
            if red and novi["status"] == "aktivno" and (red.get("status") or "aktivno") != "aktivno" \
                    and not self.ima_mesta_za_grla(1, win):            # neaktivno -> aktivno: računa se kao novo grlo u paketu
                return
            if red:
                staro = red["id"]
                if staro != nid:
                    self.ist.preimenuj(staro, nid)
                    self.pods.preimenuj(staro, nid)
                    self.ist.dodaj(nid, AUTO, (T(f"Oznaka promenjena: {staro} → {nid}", f"Tag changed: {staro} → {nid}")), automatski=True)
                red["id"] = nid
                if norm(red.get("markica")) != norm(mk):
                    self.primeni_markicu(red, mk, zapamti=True)
                nazivi_polja = dict(rfid=(T("elektronski broj", "electronic ID")), vrsta="vrsta", rasa="rasa", namena=(T("namena", "purpose")),
                                    autohtona=(T("autohtona", "native breed")), pol="pol", datum_rodjenja=(T("datum rođenja", "date of birth")),
                                    otac=(T("otac", "sire")), majka=(T("majka", "dam")), status="status", stado=(T("stado", "herd")),
                                    poreklo="poreklo", poreklo_od=(T("poreklo od", "origin from")), napomena=T("napomena", "note"))
                promene = [f"{n}: {red.get(k) or '–'} → {novi.get(k) or '–'}" for k, n in nazivi_polja.items()
                           if (red.get(k) or "") != (novi.get(k) or "")]
                if promene:
                    self.ist.dodaj(nid, AUTO, (T("Izmena podataka – ", "Details changed – ")) + "; ".join(promene), automatski=True)
                red.update(novi)
                if staro != nid:
                    for r in self.tab.redovi:
                        if r.get("otac") == staro:
                            r["otac"] = nid
                        if r.get("majka") == staro:
                            r["majka"] = nid
            else:
                if novi.get("status", "aktivno") == "aktivno" and not self.ima_mesta_za_grla(1, win):
                    return
                novi["uneto"] = sada()
                self.tab.redovi.append(novi)
                self.ist.dodaj(nid, AUTO, (T("Grlo upisano u evidenciju", "Animal added to the records")) +
                               (f" ({novi['poreklo']}{' – ' + novi['poreklo_od'] if novi['poreklo_od'] else ''})"
                                if novi["poreklo"] else ""), automatski=True)
                if dat:     # rodjenje se upisuje i u istoriju roditelja
                    for rod, drugi in ((mj, o), (o, mj)):
                        rid = self.model.nadji(rod) if rod else None
                        if rid and not self.model.A[rid]["osnivac"]:
                            self.ist.dodaj(rid, (T("Porođaj", "Birth")) if rod == mj else (T("Potomak", "Offspring")),
                                           (T(f"Rođen potomak {nid} ({'muško' if pol.get() == 'm' else 'žensko'})", f"Offspring born {nid} ({'male' if pol.get() == 'm' else 'female'})")),
                                           datum=parsiraj_datum(dat).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")),
                                           partner=self.model.nadji(drugi) or drugi or "", automatski=True)
            self.pod["poslednje"] = dict(vrsta=novi["vrsta"], rasa=novi["rasa"], stado=novi["stado"])
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            self.promena((T(f"Sačuvano: {nid}", f"Saved: {nid}")))
            if nid != prvobitno:
                messagebox.showinfo("HerdDoc", (T(f"{prvobitno} već postoji, pa je novo grlo upisano kao {nid}.", f"{prvobitno} already exists, so the new animal was saved as {nid}.")))
            if dalje:
                self.forma()

        def obrisi():
            if self.obrisi_grla([red["id"]], parent=win):
                win.destroy()

        fb = tk.Frame(win, bg=SURF)
        fb.pack(fill="x", padx=26, pady=(0, 20))
        tk.Frame(win, bg=LINE, height=1).place(in_=fb, relx=0, y=-10, relwidth=1)
        if red and red.get("status") != "obrisano":
            self.btn(fb, (T("Obriši grlo", "Delete animal")), obrisi, "Danger").pack(side="left")
        self.btn(fb, (T("Sačuvaj", "Save")), sacuvaj, "Primary").pack(side="right")
        if not red:
            self.btn(fb, (T("Sačuvaj i dodaj još", "Save and add another")), lambda: sacuvaj(True)).pack(side="right", padx=8)
        self.btn(fb, (T("Otkaži", "Cancel")), win.destroy).pack(side="right", padx=(0, 8) if red else 0)
        win.bind("<Return>", lambda e: sacuvaj())
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 2)
        win.geometry(f"+{x}+{y}")
        (e_id if not v.get("id") else vr).focus_set()
