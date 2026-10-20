"""Istorija: spisak događaja, upis događaja (parenje, lečenje, porođaj...), izmena grla."""
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from osnova import EN
from jezik import AUTO, DOGADJAJI, GRUPE, PARENJE, POREKLA, TER
from podaci import (fmt_starost, fmt_upis, nazivi, norm, norm_rasa, parsiraj_datum, pct, rasa_potomka,
    sort_key, starost_meseci)
from izgled import BAD, BG, BRAND, INK, INK2, LINE, SURF, SURF2, ScrollFrame, WARN
from rodoslov import procena


class IstorijaDeo:
    """Istorija: spisak događaja, upis događaja (parenje, lečenje, porođaj...), izmena grla."""


    # ---------- poreklo / rodoslovno stablo
    # ---------- istorija
    def opis_zapisa(self, z):
        dod = []
        if z["partner"]:
            dod.append(f"partner {z['partner']}")
        if z["vrednost"]:
            dod.append(z["vrednost"])
        kar = [(f"{n} {z.get(k)} days" if EN else f"{n} {z.get(k)} d.") for k, n in (("karenca_meso", ("meat" if EN else "meso")), ("karenca_mleko", ("milk" if EN else "mleko"))) if z.get(k)]
        if kar:
            dod.append(("withdrawal: " if EN else "karenca: ") + ", ".join(kar))
        return " · ".join(v for v in [z["opis"]] + dod if v)


    def tabela_istorije(self, parent, zapisi, sa_grlom, visina=14):
        kol = [("datum", ("Date" if EN else "Datum"), 100)] + ([("grlo", ("Animal" if EN else "Grlo"), 90)] if sa_grlom else []) + \
              [("dog", ("Event" if EN else "Događaj"), 160), ("opis", ("Description" if EN else "Opis"), 250), ("ishod", ("Young" if EN else "Mladi"), 185)]
        wrap, tv = self.tabela(parent, kol, visina=visina, tree=False)
        tv.tag_configure("auto", foreground=INK2)
        tv.tag_configure("ceka", foreground=BRAND)
        for i, z in enumerate(zapisi):
            vals = [z["datum"]] + ([z["grlo"]] if sa_grlom else []) + \
                   [z["dogadjaj"] if z["dogadjaj"] != AUTO else ("· record" if EN else "· evidencija"), self.opis_zapisa(z),
                    self.opis_ishoda(z)]
            tv.insert("", "end", iid=str(self.ist.zapisi.index(z)), values=vals,
                      tags=(["odd"] if i % 2 else []) + (["auto"] if z["automatski"] else []) +
                           (["ceka"] if self.ceka_porodjaj(z) else []))
        return wrap, tv


    def s_istorija(self):
        body = self.strana_okvir(scroll=False)
        self.zaglavlje(body, ("History" if EN else "Istorija"), ("All events in the herd – from newest to oldest." if EN else "Svi događaji u stadu – od najnovijeg ka starijim."),
                       [(("Gestation" if EN else "Nosivost"), self.podesavanje_gravidnosti, "Secondary"),
                        (("+  Add event" if EN else "+  Dodaj događaj"), lambda: self.dogadjaj_forma(None), "Primary")])
        self.istorija_lista(body, None)


    def istorija_lista(self, body, x, bez_dodaj=False):
        """Lista zapisa sa filterima (za jedno grlo ili celo stado)."""
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        key = "ist_" + (x or "_sve")
        st = self.ui.setdefault(key, {"vrsta": ("All events" if EN else "Svi događaji"), "auto": x is not None, "q": ""})
        qv = tk.StringVar(value=st["q"])
        if x is None:
            e = ttk.Entry(tb, textvariable=qv, width=22, font=self.f(10))
            e.pack(side="left", padx=(0, 10))
            ph = self.lbl(tb, ("⌕  Animal or ear tag…" if EN else "⌕  Grlo ili markica…"), 10, fg="#98A39B", bg=SURF)
            def ph_show(*_):
                ph.place_forget() if qv.get() else ph.place(in_=e, x=10, rely=0.5, anchor="w")
            ph.bind("<Button-1>", lambda ev: e.focus_set())
            ph_show()
            qv.trace_add("write", ph_show)
        vv = tk.StringVar(value=st["vrsta"])
        cb = ttk.Combobox(tb, textvariable=vv, values=[("All events" if EN else "Svi događaji")] + DOGADJAJI + [("Offspring" if EN else "Potomak")],
                          state="readonly", width=22, font=self.f(10))
        cb.pack(side="left")
        av = tk.BooleanVar(value=st["auto"])
        ttk.Checkbutton(tb, text=("Show record changes too" if EN else "Prikaži i promene u evidenciji"), variable=av).pack(side="left", padx=12)
        kartice = tk.Frame(body, bg=BG)
        kartice.pack(fill="x", pady=(0, 12))
        cekaju = self.cekaju_porodjaj(x)
        if cekaju:
            co, cc = self.card(body, 16, 10)
            co.pack(fill="x", pady=(0, 12))
            hr = tk.Frame(cc, bg=SURF)
            hr.pack(fill="x")
            self.lbl(hr, (f"Waiting for young ({len(cekaju)})" if EN else f"Čekaju mlade ({len(cekaju)})"), 11, "bold").pack(side="left")
            lg = self.lbl(hr, ("Gestation…" if EN else "Nosivost…"), 9, "bold", fg=BRAND, cursor="hand2")
            lg.pack(side="right")
            lg.bind("<Button-1>", lambda e: self.podesavanje_gravidnosti())
            self.lbl(cc, ("Tick \"Young born\" after the pregnancy time – enter date and number (sex and tag later)." if EN else "„Dobijeni mladi“ se može štiklirati tek kad prođe vreme gravidnosti – tada upisuješ datum i "
                         "broj rođenih (pol i oznaku kasnije)."), 9, fg=INK2).pack(anchor="w", pady=(0, 6))
            danas = date.today()
            for z in cekaju[:5]:
                majka, otac = self.roditelji_parenja(z)
                oc = self.ocekivani_porodjaj(z)
                r = tk.Frame(cc, bg=SURF)
                r.pack(fill="x", pady=2)
                od = self.upis_moguc_od(z)
                otvoreno = od is None or danas >= od
                cv = tk.BooleanVar(value=False)
                cb_ = ttk.Checkbutton(r, text=("Young born" if EN else "Dobijeni mladi"), variable=cv, style="Card.TCheckbutton",
                                      command=lambda z=z, cv=cv: (cv.set(False), self.upis_podmlatka(z)))
                cb_.pack(side="left")
                if not otvoreno:
                    cb_.state(["disabled"])
                self.lbl(r, f"{majka or '?'} × {otac or '?'}", 10, "bold").pack(side="left", padx=(14, 10))
                self.lbl(r, (f"mated {z['datum']}" if EN else f"pareno {z['datum']}"), 9, fg=INK2).pack(side="left")
                if oc:
                    dk = self.najkasniji_porodjaj(z)
                    if not otvoreno:
                        txt, boja = ((f"pregnant · birth {od.strftime('%d/%m')}–{dk.strftime('%d/%m/%Y')} "
                                     f"(in {(od - danas).days} d.)" if EN else f"gravidna · porođaj {od.strftime('%d.%m.')}–{dk.strftime('%d.%m.%Y')} "
                                     f"(za {(od - danas).days} d.)")), INK2
                    elif danas <= dk:
                        txt, boja = (f"birth ~{oc.strftime('%d/%m')} (latest {dk.strftime('%d/%m')}) – entry open" if EN else f"porođaj ~{oc.strftime('%d.%m.')} (najkasnije {dk.strftime('%d.%m.')}) – upis otvoren"), WARN
                    else:
                        txt, boja = (f"due date passed {dk.strftime('%d/%m/%Y')} ({(danas - dk).days} d.)" if EN else f"termin prošao {dk.strftime('%d.%m.%Y')} ({(danas - dk).days} d.)"), BAD
                    self.lbl(r, txt, 9, "bold", fg=boja).pack(side="left", padx=12)
                if not otvoreno:
                    lp = self.lbl(r, "prevremeni?", 9, fg=BRAND, cursor="hand2")
                    lp.pack(side="right", padx=(10, 0))
                    lp.bind("<Button-1>", lambda e, z=z: self.upis_podmlatka(z))
                lk = self.lbl(r, ("failed" if EN else "nije uspelo"), 9, fg=INK2, cursor="hand2")
                lk.pack(side="right")
                lk.bind("<Button-1>", lambda e, z=z: self.oznaci_neuspelo(z))
            if len(cekaju) > 5:
                self.lbl(cc, (f"… and {len(cekaju) - 5} more (see the \"Young\" column in the table)" if EN else f"… i još {len(cekaju) - 5} (vidi kolonu „Mladi“ u tabeli)"), 9, fg=INK2).pack(anchor="w")
        legla = self.cekaju_mindjusu(x)
        if legla:
            lo, lc = self.card(body, 16, 10)
            lo.pack(fill="x", pady=(0, 12))
            self.lbl(lc, (f"Waiting for ear tag – entry in animal list ({len(legla)})" if EN else f"Čekaju minđušu – upis u listu grla ({len(legla)})"), 11, "bold").pack(anchor="w")
            self.lbl(lc, ("Young born without tag and sex. When they get their ear tags, click \"Enter in list\"." if EN else "Rođeni mladi bez oznake i pola. Kad dobiju minđušu, klikni „Upiši u listu“."), 9,
                     fg=INK2).pack(anchor="w", pady=(0, 6))
            for z in legla:
                uk, dd, vec = self.leglo(z)
                majka, otac = self.roditelji_parenja(z)
                dr = parsiraj_datum(dd)
                star = (date.today() - dr).days if dr else None
                n_ = nazivi(self.vrsta_parenja(z))
                r = tk.Frame(lc, bg=SURF)
                r.pack(fill="x", pady=2)
                self.btn(r, ("Enter in list" if EN else "Upiši u listu"), lambda z=z: self.upis_u_listu(z), "Primary").pack(side="right")
                self.btn(r, ("Remove…" if EN else "Ukloni…"), lambda z=z: self.ukloni_iz_legla(z), "Danger").pack(side="right", padx=8)
                self.lbl(r, f"{majka or '?'} × {otac or '?'}", 10, "bold").pack(side="left")
                self.lbl(r, f"{uk - len(vec)} {n_[3]}" + ((f" (of {uk})" if EN else f" (od {uk})") if vec else ""), 10, "bold",
                         fg=BRAND).pack(side="left", padx=12)
                self.lbl(r, (f"born {dd}" if EN else f"rođeno {dd}") + ((f" · {star} d. old" if EN else f" · staro {star} d.") if star is not None else ""), 9,
                         fg=INK2).pack(side="left")
        dugmad = tk.Frame(body, bg=BG)
        dugmad.pack(fill="x", pady=(0, 10))
        holder = tk.Frame(body, bg=BG)
        holder.pack(fill="both", expand=True)
        stanje = {"tv": None}
        st.setdefault("grupa", "")

        def crtaj_kartice():
            for w in kartice.winfo_children():
                w.destroy()
            svi = self.ist.za(x)
            for i, (naziv, vrste) in enumerate([(("All" if EN else "Sve"), None)] + GRUPE):
                if x is None and vrste:      # za celo stado porođaj se broji jednom (kod majke)
                    vrste = tuple(v for v in vrste if v != ("Offspring" if EN else "Potomak"))
                zz = [z for z in svi if vrste is None or z["dogadjaj"] in vrste]
                if vrste is None:
                    zz = [z for z in zz if av.get() or not z["automatski"]]
                akt = st["grupa"] == ("" if vrste is None else naziv)
                bg = BRAND if akt else SURF
                fg, fg2 = ("#FFFFFF", "#D7E6DC") if akt else (INK, INK2)
                k = tk.Frame(kartice, bg=bg if akt else LINE, cursor="hand2")
                k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
                kartice.columnconfigure(i, weight=1, uniform="k")
                u = tk.Frame(k, bg=bg)
                u.pack(fill="both", expand=True, padx=1, pady=1)
                l1 = tk.Label(u, text=naziv, font=self.f(10, "bold"), bg=bg, fg=fg)
                l1.pack(anchor="w", padx=14, pady=(10, 0))
                l2 = tk.Label(u, text=str(len(zz)), font=self.f(20, "bold"), bg=bg, fg=fg)
                l2.pack(anchor="w", padx=14)
                if vrste is None:
                    pod = ("all records" if EN else "svih zapisa")
                elif zz:
                    z0 = zz[0]
                    pod = (f"last {z0['datum']}" if EN else f"poslednje {z0['datum']}")
                    if naziv == ("Matings" if EN else "Parenja") and z0["partner"]:
                        pod += (f"\nwith {z0['partner']}" if EN else f"\nsa {z0['partner']}")
                    elif naziv == ("Treatments" if EN else "Lečenja") and (z0["vrednost"] or z0["dogadjaj"] == ("Vaccination" if EN else "Vakcinacija")):
                        det = z0["vrednost"] or ("vaccination" if EN else "vakcinacija")
                        pod += "\n" + (det if len(det) <= 24 else det[:23] + "…")
                else:
                    pod = ("no records" if EN else "nema zapisa")
                l3 = tk.Label(u, text=pod, font=self.f(9), bg=bg, fg=fg2, justify="left")
                l3.pack(anchor="w", padx=14, pady=(0, 10))
                for w in (k, u, l1, l2, l3):
                    w.bind("<Button-1>", lambda e, n=("" if vrste is None else naziv): izaberi_grupu(n))

        def izaberi_grupu(n):
            st["grupa"] = n
            if n:
                vv.set(("All events" if EN else "Svi događaji"))
            osvezi()

        def osvezi(*_):
            st.update(vrsta=vv.get(), auto=av.get(), q=qv.get())
            for w in holder.winfo_children():
                w.destroy()
            crtaj_kartice()
            grupa = dict(GRUPE).get(st["grupa"])
            if grupa and x is None:
                grupa = tuple(v for v in grupa if v != ("Offspring" if EN else "Potomak"))
            zap = self.ist.za(x, auto=av.get() or bool(grupa))
            if grupa:
                zap = [z for z in zap if z["dogadjaj"] in grupa]
            if vv.get() != ("All events" if EN else "Svi događaji"):
                zap = [z for z in zap if z["dogadjaj"] == vv.get()]
            q = norm(qv.get())
            if q and x is None:
                ids = {g for g in self.model.A if q in norm(g) or q in norm(self.model.A[g]["markica"])}
                zap = [z for z in zap if z["grlo"] in ids or q in norm(z["grlo"])]
            if not zap:
                self.napomena(holder, ("No records for the selected filter." if EN else "Nema zapisa za izabrani filter.") if self.ist.za(x) else
                              ("No records yet. Add the first event with the \"Add event\" button." if EN else "Još nema zapisa. Dodaj prvi događaj dugmetom „Dodaj događaj“."), ok=True)
                stanje["tv"] = None
                return
            wrap, tv = self.tabela_istorije(holder, zap, x is None)
            wrap.pack(fill="both", expand=True)
            stanje["tv"] = tv
            tv.bind("<Double-1>", lambda e: izmeni())
            tv.bind("<Delete>", lambda e: obrisi())

            def klik_mladi(e, tv=tv):
                if tv.identify_region(e.x, e.y) != "cell":
                    return
                kol = tv.identify_column(e.x)
                if tv.heading(kol, "text") != ("Young" if EN else "Mladi"):
                    return
                iid = tv.identify_row(e.y)
                if iid:
                    z = self.ist.zapisi[int(iid)]
                    if z["dogadjaj"] == PARENJE and not z["automatski"]:
                        self.upis_podmlatka(z)
                        return "break"
            tv.bind("<Button-1>", klik_mladi, add="+")

        def izabran():
            tv = stanje["tv"]
            sel = tv.selection() if tv else ()
            if not sel:
                self.toast(("First select a record in the table." if EN else "Prvo označi zapis u tabeli."))
                return None
            return self.ist.zapisi[int(sel[0])]

        def izmeni():
            z = izabran()
            if not z:
                return
            if z["automatski"]:
                self.toast(("Automatic records cannot be changed." if EN else "Automatski zapisi se ne menjaju."))
                return
            self.dogadjaj_forma(z["grlo"], zapis=z, posle=osvezi)

        def obrisi():
            z = izabran()
            if not z:
                return
            if z["automatski"]:
                self.toast(("Automatic records cannot be deleted." if EN else "Automatski zapisi se ne brišu."))
                return
            if messagebox.askyesno(("Delete record" if EN else "Obriši zapis"), (f"Delete the record \"{z['dogadjaj']}\" of {z['datum']}?" if EN else f"Obrisati zapis „{z['dogadjaj']}“ od {z['datum']}?")):
                self.ist.zapisi.remove(z)
                self.ist.sacuvaj()
                osvezi()

        if x and not bez_dodaj:
            self.btn(dugmad, ("+  Add event" if EN else "+  Dodaj događaj"), lambda: self.dogadjaj_forma(x, posle=osvezi), "Primary").pack(
                side="left", padx=(0, 8))
        self.btn(dugmad, ("Edit record" if EN else "Izmeni zapis"), izmeni).pack(side="left")
        self.btn(dugmad, ("Delete record" if EN else "Obriši zapis"), obrisi, "Danger").pack(side="left", padx=8)
        self.lbl(dugmad, ("Double-click edits a record. Grey = automatic changes." if EN else "Dvoklik menja zapis. Sivo = automatske promene."), 9,
                 fg=INK2).pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda e: (st.update(grupa=""), osvezi()))
        av.trace_add("write", osvezi)
        qv.trace_add("write", osvezi)
        osvezi()
        return osvezi


    def azuriraj_grlo(self, red, novi):
        """Primeni izmene podataka grla (bez promene oznake) i zapiši ih u istoriju. Vrati poruku greške ili None."""
        mk = (novi.get("markica") or "").strip()
        if mk and norm(mk) != norm(red.get("markica")):
            poruka = self.markica_zauzeta(mk, red)
            if poruka:
                return poruka
        d = (novi.get("datum_rodjenja") or "").strip()
        if d:
            pd = parsiraj_datum(d)
            if not pd:
                return ("The date of birth is not valid. Enter it as 15/03/2022." if EN else "Datum rođenja nije ispravan. Upiši ga kao 15.03.2022.")
            if pd == parsiraj_datum(red.get("datum_rodjenja")):
                novi["datum_rodjenja"] = red.get("datum_rodjenja", "")   # isti datum, drugi zapis – ne menjaj
            else:
                novi["datum_rodjenja"] = pd.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
        for p in ("otac", "majka"):
            v = (novi.get(p) or "").strip()
            if v and (v == red["id"] or self.model.nadji(v) == red["id"]):
                return ("An animal cannot be its own parent." if EN else "Grlo ne može biti sopstveni roditelj.")
            novi[p] = self.model.nadji(v) or v if v else ""
        if norm(mk) != norm(red.get("markica")):
            self.primeni_markicu(red, mk, zapamti=True)
        novi.pop("markica", None)
        nazivi_polja = dict(rasa=("breed" if EN else "rasa"), pol=("sex" if EN else "pol"), datum_rodjenja=("date of birth" if EN else "datum rođenja"), otac=("sire" if EN else "otac"), majka=("dam" if EN else "majka"),
                            status="status", stado="stado", poreklo="poreklo", poreklo_od=("origin from" if EN else "poreklo od"))
        promene = [f"{n}: {red.get(k) or '–'} → {novi.get(k) or '–'}" for k, n in nazivi_polja.items()
                   if k in novi and (red.get(k) or "") != (novi.get(k) or "")]
        if promene:
            self.ist.dodaj(red["id"], AUTO, ("Details changed – " if EN else "Izmena podataka – ") + "; ".join(promene), automatski=True)
        red.update(novi)
        return None


    def izbor_dogadjaja(self, parent, var, bg=SURF, po_redu=5):
        """Dugmad za izbor vrste događaja (+ 'Drugo…' za sopstveni naziv). Vraća okvir."""
        okvir = tk.Frame(parent, bg=bg)
        cipovi = {}
        drugo_v = tk.StringVar(value=var.get() if var.get() and var.get() not in DOGADJAJI else "")
        drugo_e = ttk.Entry(okvir, textvariable=drugo_v, width=26, font=self.f(10))
        stanje = {"drugo": bool(drugo_v.get())}

        def stil(*_):
            izbor = var.get()
            for naziv, lb in cipovi.items():
                akt = (naziv == izbor) if naziv != ("Other…" if EN else "Drugo…") else stanje["drugo"]
                lb.config(bg=BRAND if akt else SURF2, fg="#FFFFFF" if akt else INK)
            if stanje["drugo"]:
                drugo_e.grid(row=99, column=0, columnspan=po_redu, sticky="w", pady=(6, 0))
            else:
                drugo_e.grid_remove()

        def klik(naziv):
            if naziv == ("Other…" if EN else "Drugo…"):
                stanje["drugo"] = True
                var.set(drugo_v.get().strip())
                stil()
                drugo_e.focus_set()
            else:
                stanje["drugo"] = False
                var.set(naziv)
                stil()

        for i, naziv in enumerate(DOGADJAJI + [("Other…" if EN else "Drugo…")]):
            lb = tk.Label(okvir, text=naziv, font=self.f(9, "bold"), padx=10, pady=5, cursor="hand2", bg=SURF2, fg=INK)
            lb.grid(row=i // po_redu, column=i % po_redu, sticky="ew", padx=(0, 6), pady=(0, 6))
            lb.bind("<Button-1>", lambda e, n=naziv: klik(n))
            cipovi[naziv] = lb
        drugo_v.trace_add("write", lambda *_: stanje["drugo"] and var.set(drugo_v.get().strip()))
        var.trace_add("write", stil)
        ph = self.lbl(okvir, ("e.g. Castration, Weaning…" if EN else "npr. Kastracija, Odbijanje…"), 9, fg="#98A39B", bg=SURF)
        def ph_show(*_):
            if stanje["drugo"] and not drugo_v.get():
                ph.place(in_=drugo_e, x=8, rely=0.5, anchor="w")
            else:
                ph.place_forget()
        drugo_v.trace_add("write", ph_show)
        var.trace_add("write", ph_show)
        ph.bind("<Button-1>", lambda e: drugo_e.focus_set())
        stil()
        ph_show()
        return okvir


    def istorija_prozor(self, x):
        """Prozor grla: levo podaci (čitanje i izmena), desno unos novog zapisa i cela istorija."""
        m = self.model
        if x not in m.A or m.A[x]["osnivac"]:
            if x in m.A:
                self.karton(x)
            return
        if getattr(self, "ist_win", None) and self.ist_win.winfo_exists():
            win = self.ist_win
            for w in win.winfo_children():
                w.destroy()
        else:
            win = tk.Toplevel(self.root, bg=BG)
            win.geometry(f"1200x780+{self.root.winfo_rootx() + 20}+{max(0, self.root.winfo_rooty() - 10)}")
            win.minsize(1000, 640)
            win.transient(self.root)
            win.bind("<Escape>", lambda e: win.destroy())
            self.ist_win = win
        win.title((f"Animal {x} – details and history" if EN else f"Grlo {x} – podaci i istorija"))
        win.grlo = x
        a = m.A[x]
        red = self.red_za(x)

        # ---------- zaglavlje
        h = tk.Frame(win, bg=BG)
        h.pack(fill="x", padx=24, pady=(18, 12))
        self.cip(h, x, lambda: self.karton(x), big=True, bg=BG).pack(side="left")
        t = tk.Frame(h, bg=BG)
        t.pack(side="left", padx=14)
        self.lbl(t, f"{m.pol_naziv(x).capitalize()}{', ' + a['rasa'] if a['rasa'] else ''}", 15, "bold").pack(anchor="w")
        st = starost_meseci(a["datum"])
        self.lbl(t, "   ·   ".join(v for v in (
            (f"ear tag {a['markica'] or '–'}" if EN else f"markica {a['markica'] or '–'}"),
            f"{fmt_starost(st)}" if st is not None else "",
            ("in herd" if EN else "u zapatu") if a["aktivno"] else ("deleted" if EN else "obrisano") if a.get("obrisano") else ("out of herd" if EN else "van zapata"),
            (f"inbreeding {pct(m.inbr(x))}" if EN else f"inbriding {pct(m.inbr(x))}")) if v), 10, fg=INK2).pack(anchor="w")
        dd = tk.Frame(h, bg=BG)
        dd.pack(side="right")
        self.btn(dd, ("Card" if EN else "Karton"), lambda: self.karton(x)).pack(side="left", padx=(0, 8))
        self.btn(dd, ("Pedigree – tree" if EN else "Poreklo – stablo"), lambda: self.stablo(x)).pack(side="left", padx=(0, 8))
        self.btn(dd, ("Partner search" if EN else "Pretraga partnera"), lambda: (win.destroy(), self.idi_na_pretragu(x))).pack(side="left")

        telo = tk.Frame(win, bg=BG)
        telo.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # ---------- levo: podaci o grlu
        lo, lc = self.card(telo, 18, 16)
        lo.pack(side="left", fill="y", padx=(0, 16))
        self.lbl(lc, ("Animal details" if EN else "Podaci o grlu"), 13, "bold").grid(row=0, column=0, columnspan=2, sticky="w")
        self.lbl(lc, ("Edit a field and click \"Save details\"." if EN else "Izmeni polje i klikni „Sačuvaj podatke“."), 9, fg=INK2).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        sva = m.grla()
        pv = {}

        def polje(r, c, naslov, key, vrednost, vals=None, state="normal", span=1):
            f = tk.Frame(lc, bg=SURF)
            f.grid(row=r, column=c, columnspan=span, sticky="new", padx=(0 if c == 0 else 10, 0), pady=4)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            v = tk.StringVar(value=vrednost or "")
            w = (ttk.Combobox(f, textvariable=v, values=vals, state=state, width=16, font=self.f(10))
                 if vals is not None else ttk.Entry(f, textvariable=v, width=18, font=self.f(10)))
            w.pack(fill="x", pady=(3, 0))
            pv[key] = v
            return w

        n = nazivi(a["vrsta"])
        pol_opcije = {n[1].capitalize(): "z", n[0].capitalize(): "m"}
        dat = parsiraj_datum(red.get("datum_rodjenja"))
        polje(2, 0, ("Ear tag" if EN else "Ušna markica"), "markica", red.get("markica"))
        polje(2, 1, ("Breed" if EN else "Rasa"), "rasa", red.get("rasa"), sorted({g["rasa"] for g in sva if g["rasa"]}))
        polje(3, 0, ("Sex" if EN else "Pol"), "pol", next((k for k, v in pol_opcije.items() if v == red.get("pol")), ""),
              list(pol_opcije), "readonly")
        polje(3, 1, ("Date of birth" if EN else "Datum rođenja"), "datum_rodjenja", dat.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if dat else red.get("datum_rodjenja"))
        polje(4, 0, ("Sire" if EN else "Otac"), "otac", red.get("otac"),
              sorted((g["id"] for g in m.A.values() if g["pol"] == "m" and g["id"] != x), key=sort_key))
        polje(4, 1, ("Dam" if EN else "Majka"), "majka", red.get("majka"),
              sorted((g["id"] for g in m.A.values() if g["pol"] == "z" and g["id"] != x), key=sort_key))
        polje(5, 0, ("Herd" if EN else "Stado"), "stado", red.get("stado"), self.sva_stada())
        polje(5, 1, ("Origin" if EN else "Poreklo"), "poreklo", red.get("poreklo"), POREKLA)
        polje(6, 0, ("From whom / where" if EN else "Od koga / odakle"), "poreklo_od", red.get("poreklo_od"),
              sorted({g["poreklo_od"] for g in sva if g["poreklo_od"]}), span=2)
        akt = tk.BooleanVar(value=red.get("status", "aktivno") == "aktivno")
        if red.get("status") != "obrisano":
            ttk.Checkbutton(lc, text=("In herd (not sold or dead)" if EN else "U zapatu (nije prodato ni uginulo)"), variable=akt,
                            style="Card.TCheckbutton").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        # informacije samo za čitanje
        info = tk.Frame(lc, bg=SURF2)
        info.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        o, mj = m.P[x]
        pot = [k for k, pr in m.P.items() if x in pr]
        for i, (k, v) in enumerate(((("Parents" if EN else "Roditelji"), f"{o or '?'} × {mj or '?'}"),
                                    (("Offspring" if EN else "Potomaka"), str(len(pot))),
                                    (("Known ancestors" if EN else "Poznatih predaka"), str(len(m.putanje(x)))),
                                    (("Inbreeding" if EN else "Inbriding"), pct(m.inbr(x))),
                                    (("Added" if EN else "Upisano"), fmt_upis(a["uneto"])),
                                    (("Previous ear tags" if EN else "Ranije markice"), ", ".join(a["stare"]) or "–"))):
            self.lbl(info, k, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 8), pady=2)
            self.lbl(info, v, 9, "bold", bg=SURF2, wraplength=180, justify="left").grid(
                row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        err_p = self.lbl(lc, "", 9, "bold", fg=BAD, wraplength=330, justify="left")
        err_p.grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def sacuvaj_podatke():
            novi = {k: v.get().strip() for k, v in pv.items()}
            novi["pol"] = pol_opcije.get(novi["pol"], red.get("pol", ""))
            novi["rasa"] = norm_rasa(novi["rasa"])
            o_, m_ = self.model.nadji(novi.get("otac")), self.model.nadji(novi.get("majka"))
            if o_ and m_ and (not novi["rasa"] or novi["rasa"].startswith(("hybrid" if EN else "hibrid")) or novi["rasa"] == ("crossbred" if EN else "melez")):
                novi["rasa"] = rasa_potomka(self.model.A[o_]["rasa"], self.model.A[m_]["rasa"]) or novi["rasa"]
            if red.get("status") != "obrisano":
                novi["status"] = "aktivno" if akt.get() else "neaktivno"
            greska = self.azuriraj_grlo(red, novi)
            if greska:
                err_p.config(text=greska)
                return
            self.promena((f"Details saved: {x}" if EN else f"Sačuvani podaci: {x}"))
            self.istorija_prozor(x)

        self.btn(lc, ("Save details" if EN else "Sačuvaj podatke"), sacuvaj_podatke, "Primary").grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # ---------- desno: novi zapis + istorija
        dsf = ScrollFrame(telo)
        dsf.pack(side="left", fill="both", expand=True)
        desno = tk.Frame(dsf.inner, bg=BG)
        desno.pack(fill="both", expand=True, padx=(0, 10))
        no, nc = self.card(desno, 18, 14)
        no.pack(fill="x", pady=(0, 14))
        self.lbl(nc, ("New history record" if EN else "Novi zapis u istoriju"), 13, "bold").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        ev = {}

        def ep(r, c, naslov, key, vrednost="", vals=None, width=16, span=1, state="normal"):
            f = tk.Frame(nc, bg=SURF)
            f.grid(row=r, column=c, columnspan=span, sticky="new", padx=(0 if c == 0 else 10, 0), pady=3)
            lab = self.lbl(f, naslov, 9, "bold", fg=INK2)
            lab.pack(anchor="w")
            v = tk.StringVar(value=vrednost)
            w = (ttk.Combobox(f, textvariable=v, values=vals, width=width, font=self.f(10), state=state)
                 if vals is not None else ttk.Entry(f, textvariable=v, width=width, font=self.f(10)))
            w.pack(fill="x", pady=(3, 0))
            ev[key] = v
            return lab

        for c in range(4):
            nc.columnconfigure(c, weight=1)
        # vrsta događaja – dugmad; podrazumevano prema izabranoj kartici
        grupa = self.ui.get("ist_" + x, {}).get("grupa", "")
        pocetni = {("Matings" if EN else "Parenja"): ("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("Treatments" if EN else "Lečenja"): ("Treatment" if EN else "Lečenje"), ("Births" if EN else "Porođaji"): ("Birth" if EN else "Porođaj")}.get(grupa, "")
        ev["dogadjaj"] = tk.StringVar(value=pocetni)
        self.lbl(nc, ("Event – click a type" if EN else "Događaj – klikni na vrstu"), 9, "bold", fg=INK2).grid(row=1, column=0, columnspan=4, sticky="w")
        self.izbor_dogadjaja(nc, ev["dogadjaj"]).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 2))
        ep(3, 0, ("Date" if EN else "Datum"), "datum", date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), width=12)
        suprotni = [k["id"] for k in m.grla() if k["vrsta"] == a["vrsta"] and k["pol"] and k["pol"] != a["pol"]]
        lab_par = ep(3, 1, "Partner", "partner", "", suprotni, width=12)
        f_par_ = lab_par.master
        f_kar = self.okvir_karence(nc, ev)
        lab_vr = ep(3, 2, ("Value" if EN else "Vrednost"), "vrednost", "", width=16, span=2)
        ep(4, 0, ("Description / note" if EN else "Opis / napomena"), "opis", "", width=60, span=4)
        poruka = self.lbl(nc, "", 9, fg=INK2, wraplength=620, justify="left")
        poruka.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))
        nazivi_vr = {("Weighing" if EN else "Merenje težine"): ("Weight (kg)" if EN else "Težina (kg)"), ("Vaccination" if EN else "Vakcinacija"): ("Vaccine / product" if EN else "Vakcina / preparat"),
                     ("Treatment" if EN else "Lečenje"): ("Drug / diagnosis" if EN else "Lek / dijagnoza"), ("Sale" if EN else "Prodaja"): ("Buyer / price" if EN else "Kupac / cena"), ("Move" if EN else "Premeštanje"): ("New herd" if EN else "Novo stado"),
                     ("Birth" if EN else "Porođaj"): ("Number of young" if EN else "Broj mladunaca"), ("Mating / insemination" if EN else "Parenje / osemenjavanje"): ("Natural / AI" if EN else "Prirodno / VO")}

        def prilagodi(*_):
            d = ev["dogadjaj"].get()
            lab_vr.config(text=nazivi_vr.get(d, ("Value" if EN else "Vrednost")))
            if d in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija")):
                f_par_.grid_remove()
                f_kar.grid(row=3, column=1, sticky="nw", padx=(10, 0), pady=3)
            else:
                f_kar.grid_remove()
                f_par_.grid()
            lab_par.config(text=("Partner (bull / ram…)" if EN else "Partner (bik / ovan…)") if d in (("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("Birth" if EN else "Porođaj")) else "Partner")
            p_ = m.nadji(ev["partner"].get())
            if not d:
                poruka.config(text=("Choose the event type by clicking one of the buttons." if EN else "Izaberi vrstu događaja klikom na jedno od dugmadi."), fg=INK2)
            elif d == ("Mating / insemination" if EN else "Parenje / osemenjavanje") and p_ and p_ != x:
                f = m.kinship(x, p_)
                t_, boja = procena(f, self.prag)
                dp = parsiraj_datum(ev["datum"].get())
                zenka = x if a["pol"] == "z" else p_
                _, nz_, mn_, mx_, pr_ = self.profil_gravidnosti(a["vrsta"], m.A[zenka]["rasa"] if zenka in m.A else "")
                oc = ((f"  Expected birth: {(dp + timedelta(days=pr_)).strftime('%d/%m/%Y')} "
                      f"(between {(dp + timedelta(days=mn_)).strftime('%d/%m')} and "
                      f"{(dp + timedelta(days=mx_)).strftime('%d/%m/%Y')}) – gestation: {nz_.lower()}, "
                      f"by the dam's breed." if EN else f"  Očekivani porođaj: {(dp + timedelta(days=pr_)).strftime('%d.%m.%Y')} "
                      f"(između {(dp + timedelta(days=mn_)).strftime('%d.%m.')} i "
                      f"{(dp + timedelta(days=mx_)).strftime('%d.%m.%Y')}) – nosivost: {nz_.lower()}, "
                      f"po rasi majke.") if dp and pr_ else "")
                poruka.config(text=(f"Expected inbreeding of offspring: {pct(f)} ({t_}), shared genes "
                                   f"{pct(m.r(x, p_))}.{oc}" if EN else f"Očekivani inbriding potomka: {pct(f)} ({t_}), zajednički geni "
                                   f"{pct(m.r(x, p_))}.{oc}"), fg=boja)
            elif d == ("Sale" if EN else "Prodaja") and "meso" in self.karenca(x):
                poruka.config(text=(f"WARNING: meat withdrawal lasts until {self.karenca(x)['meso'][0].strftime('%d/%m/%Y')}! "
                                   "The animal will be marked as out of herd." if EN else f"PAŽNJA: karenca za meso traje do {self.karenca(x)['meso'][0].strftime('%d.%m.%Y')}! "
                                   "Grlo će biti označeno kao van zapata."), fg=BAD)
            elif d in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and a["aktivno"]:
                poruka.config(text=("The animal will be marked as out of herd." if EN else "Grlo će biti označeno kao van zapata."), fg=WARN)
            elif d in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija")):
                poruka.config(text=("Enter the withdrawal period from the drug leaflet – the program will warn you while it lasts." if EN else "Upiši karencu iz uputstva leka – program će upozoravati dok traje."), fg=INK2)
            elif d == TER:
                poruka.config(text=("If the female has been mated, that mating will be marked as failed." if EN else "Ako je ženka sparena, to parenje će biti označeno kao neuspelo."), fg=INK2)
            elif d == ("Move" if EN else "Premeštanje"):
                poruka.config(text=("Enter the new herd in the \"New herd\" field – the animal's herd will change." if EN else "Upiši novo stado u polje „Novo stado“ – stado grla će se promeniti."), fg=INK2)
            else:
                poruka.config(text="")
        for k in ("dogadjaj", "partner", "datum"):
            ev[k].trace_add("write", prilagodi)
        prilagodi()

        def dodaj_zapis(e=None):
            d = parsiraj_datum(ev["datum"].get())
            if not d:
                poruka.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."), fg=BAD)
                return
            dog = ev["dogadjaj"].get().strip()
            if not dog:
                poruka.config(text=("Choose the event type (mating, treatment, birth…)." if EN else "Izaberi vrstu događaja (parenje, lečenje, porođaj…)."), fg=BAD)
                return
            par = ev["partner"].get().strip()
            par = m.nadji(par) or par
            vr = ev["vrednost"].get().strip()
            leci = dog in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))
            nz = self.ist.dodaj(x, dog, opis=ev["opis"].get().strip(), datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")),
                                partner="" if leci else par, vrednost=vr,
                                karenca_meso=self.broj_dana(ev["karenca_meso"].get()) if leci else "",
                                karenca_mleko=self.broj_dana(ev["karenca_mleko"].get()) if leci else "")
            self.posle_novog_zapisa(nz)
            if dog in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and red.get("status") == "aktivno":
                red["status"] = "neaktivno"
                self.ist.dodaj(x, AUTO, (f"Status: out of herd ({dog.lower()})" if EN else f"Status: van zapata ({dog.lower()})"), automatski=True)
            if dog == ("Move" if EN else "Premeštanje") and vr and vr != red.get("stado"):
                staro = red.get("stado") or "–"
                vr = next((s_ for s_ in self.sva_stada() if s_.lower() == vr.lower()), vr)
                red["stado"] = vr
                self.ist.dodaj(x, AUTO, (f"Herd: {staro} → {vr}" if EN else f"Stado: {staro} → {vr}"), automatski=True)
            self.promena((f"Recorded: {x} – {dog}" if EN else f"Zapisano: {x} – {dog}"))
            self.istorija_prozor(x)

        self.btn(nc, ("+  Add record" if EN else "+  Dodaj zapis"), dodaj_zapis, "Primary").grid(row=5, column=3, sticky="e", pady=(8, 0))

        lista = tk.Frame(desno, bg=BG)
        lista.pack(fill="both", expand=True)
        self.lbl(lista, ("History" if EN else "Istorija"), 13, "bold").pack(anchor="w", pady=(0, 8))
        win.osvezi = self.istorija_lista(lista, x, bez_dodaj=True)
        win.lift()


    def dogadjaj_forma(self, x=None, zapis=None, parent=None, posle=None, preset=None):
        m = self.model
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Edit event" if EN else "Izmena događaja") if zapis else ("New event" if EN else "Novi događaj"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Edit event" if EN else "Izmena događaja") if zapis else ("New event" if EN else "Novi događaj"), 16, "bold").grid(row=0, column=0, columnspan=2,
                                                                                 sticky="w", pady=(0, 12))
        sva = m.grla()
        vars_ = {}

        def polje(r, c, naslov, key, vrednost="", vals=None, state="normal", width=26, span=1):
            f = tk.Frame(b, bg=SURF)
            f.grid(row=r, column=c, columnspan=span, sticky="new", padx=(0 if c == 0 else 14, 0), pady=6)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            v = tk.StringVar(value=vrednost)
            w = (ttk.Combobox(f, textvariable=v, values=vals, state=state, width=width, font=self.f(10))
                 if vals is not None else ttk.Entry(f, textvariable=v, width=width, font=self.f(10)))
            w.pack(fill="x", pady=(4, 0))
            vars_[key] = v
            return w, f

        z = zapis or preset or {}
        w_grlo, _ = polje(1, 0, ("Animal *" if EN else "Grlo *"), "grlo", z.get("grlo") or x or "", [g["id"] for g in sva])
        polje(1, 1, ("Date *" if EN else "Datum *"), "datum", z.get("datum") or date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        fd = tk.Frame(b, bg=SURF)
        fd.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)
        self.lbl(fd, ("Event * – click a type" if EN else "Događaj * – klikni na vrstu"), 9, "bold", fg=INK2).pack(anchor="w")
        vars_["dogadjaj"] = tk.StringVar(value=z.get("dogadjaj", ""))
        self.izbor_dogadjaja(fd, vars_["dogadjaj"], po_redu=4).pack(anchor="w", pady=(4, 0))
        w_dog = fd
        w_vr, f_vr = polje(3, 0, ("Value" if EN else "Vrednost"), "vrednost", z.get("vrednost", ""))
        w_par, f_par = polje(3, 1, ("Partner (bull / ram…)" if EN else "Partner (bik / ovan…)"), "partner", z.get("partner", ""), [])
        f_kar = self.okvir_karence(b, vars_, (z.get("karenca_meso", ""), z.get("karenca_mleko", "")))
        self.lbl(b, ("Description / note" if EN else "Opis / napomena"), 9, "bold", fg=INK2).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 4))
        opis = tk.Text(b, width=58, height=4, font=self.f(10), relief="flat", highlightthickness=1,
                       highlightbackground=LINE, highlightcolor=BRAND, wrap="word", padx=8, pady=6)
        opis.grid(row=5, column=0, columnspan=2, sticky="ew")
        opis.insert("1.0", z.get("opis", ""))
        info = self.lbl(b, "", 9, fg=INK2, wraplength=520, justify="left")
        info.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        vz = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(b, text=("Mark the animal as out of herd" if EN else "Označi grlo kao van zapata"), variable=vz, style="Card.TCheckbutton")
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))
        nazivi_vr = {("Weighing" if EN else "Merenje težine"): ("Weight (kg)" if EN else "Težina (kg)"), ("Vaccination" if EN else "Vakcinacija"): ("Vaccine / product" if EN else "Vakcina / preparat"),
                     ("Treatment" if EN else "Lečenje"): ("Drug / diagnosis" if EN else "Lek / dijagnoza"), ("Sale" if EN else "Prodaja"): ("Buyer / price" if EN else "Kupac / cena"), ("Move" if EN else "Premeštanje"): ("New herd / location" if EN else "Novo stado / lokacija"),
                     ("Birth" if EN else "Porođaj"): ("Number of young" if EN else "Broj mladunaca"), ("Mating / insemination" if EN else "Parenje / osemenjavanje"): ("Method (natural / AI)" if EN else "Način (prirodno / VO)")}

        def prilagodi(*_):
            d = vars_["dogadjaj"].get()
            g = m.nadji(vars_["grlo"].get())
            if d in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija")):
                f_par.grid_remove()
                f_kar.grid(row=3, column=1, sticky="nw", padx=(14, 0), pady=6)
            else:
                f_kar.grid_remove()
                f_par.grid()
            for w_ in f_vr.winfo_children():
                if isinstance(w_, tk.Label):
                    w_.config(text=nazivi_vr.get(d, ("Value" if EN else "Vrednost")))
            if g:
                a_ = m.A[g]
                suprotni = [k["id"] for k in m.grla() if k["vrsta"] == a_["vrsta"] and k["pol"] and k["pol"] != a_["pol"]]
                w_par.configure(values=suprotni)
            if d in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and not zapis:
                chk.grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
            else:
                chk.grid_remove()
            # ocekivani inbriding za parenje
            p_ = m.nadji(vars_["partner"].get())
            if d == ("Mating / insemination" if EN else "Parenje / osemenjavanje") and g and p_ and g != p_:
                f = m.kinship(g, p_)
                t_, boja = procena(f, self.prag)
                info.config(text=(f"Expected inbreeding of offspring: {pct(f)} ({t_}), shared genes {pct(m.r(g, p_))}." if EN else f"Očekivani inbriding potomka: {pct(f)} ({t_}), zajednički geni {pct(m.r(g, p_))}."),
                            fg=boja)
            else:
                info.config(text="")
        for k in ("dogadjaj", "grlo", "partner"):
            vars_[k].trace_add("write", prilagodi)
        prilagodi()

        def sacuvaj(ev=None):
            g = m.nadji(vars_["grlo"].get())
            if not g or m.A[g]["osnivac"]:
                err.config(text=("Choose an animal from the list (tag or ear tag)." if EN else "Izaberi grlo sa spiska (oznaka ili markica)."))
                return
            d = parsiraj_datum(vars_["datum"].get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            dog = vars_["dogadjaj"].get().strip()
            if not dog:
                err.config(text=("Choose an event." if EN else "Izaberi događaj."))
                return
            par = vars_["partner"].get().strip()
            par = m.nadji(par) or par
            leci = dog in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))
            podaci = dict(grlo=g, datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), dogadjaj=dog, opis=opis.get("1.0", "end").strip(),
                          partner="" if leci else par, vrednost=vars_["vrednost"].get().strip(),
                          karenca_meso=self.broj_dana(vars_["karenca_meso"].get()) if leci else "",
                          karenca_mleko=self.broj_dana(vars_["karenca_mleko"].get()) if leci else "")
            if zapis:
                zapis.update(podaci)
            else:
                self.posle_novog_zapisa(self.ist.dodaj(**podaci))
                if dog in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and vz.get():
                    r = self.red_za(g)
                    if r and r.get("status") == "aktivno":
                        r["status"] = "neaktivno"
                        self.ist.dodaj(g, AUTO, (f"Status: out of herd ({dog.lower()})" if EN else f"Status: van zapata ({dog.lower()})"), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Recorded in history: {g} – {dog}" if EN else f"Zapisano u istoriju: {g} – {dog}"))
            if posle:
                try:
                    posle()
                except tk.TclError:
                    pass
            if getattr(self, "ist_win", None) and self.ist_win.winfo_exists() and hasattr(self.ist_win, "osvezi"):
                try:
                    self.ist_win.osvezi()
                except tk.TclError:
                    pass

        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
        (w_dog if (x or zapis) else w_grlo).focus_set()
