"""Obaveštenja: ter, karenca, plodnost, podsetnici i obaveštenja na startu."""
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from osnova import EN
from jezik import AUTO, DOGADJAJI, PARENJE, TER, TER_CIKLUS
from podaci import nazivi, parsiraj_datum, vrsta_norm
from izgled import BAD, BAD_BG, BRAND, INK, INK2, SURF, SURF2, WARN, WARN_BG


class ObavestenjaDeo:
    """Obaveštenja: ter, karenca, plodnost, podsetnici i obaveštenja na startu."""


    # ================================================================ TER
    def ciklus_tera(self, vrsta):
        return TER_CIKLUS.get(vrsta_norm(vrsta or ""), 21)


    def tera_se(self, z):
        """Posle parenja ženka se ponovo tera – parenje nije uspelo; nudi se novo parenje."""
        majka, otac = self.roditelji_parenja(z)
        z["ter"] = "da"
        z["ishod"] = "neuspelo"
        if majka:
            self.ist.dodaj(majka, TER, (f"In heat again – mating of {z['datum']} failed" if EN else f"Ponovo se tera – parenje od {z['datum']} nije uspelo"))
        self.promena((f"{majka or '?'}: mating of {z['datum']} marked as failed (in heat again)." if EN else f"{majka or '?'}: parenje od {z['datum']} označeno kao neuspelo (ponovo se tera)."))
        self.posle_obavestenja()
        if majka and majka in self.model.A:
            self.dogadjaj_forma(majka, preset={"dogadjaj": PARENJE, "partner": otac or ""})


    def ne_tera_se(self, z):
        z["ter"] = "ne"
        self.promena(("Recorded: not in heat – probably pregnant." if EN else "Zabeleženo: ne tera se – verovatno je gravidna."))
        self.posle_obavestenja()


    def posle_novog_zapisa(self, nz):
        """Zajedničko posle svakog ručno upisanog događaja."""
        self.zatvori_stara_parenja(nz)
        if nz.get("dogadjaj") == TER:
            for z in self.cekaju_porodjaj(nz["grlo"]):
                majka, _ = self.roditelji_parenja(z)
                if majka == nz["grlo"] and (parsiraj_datum(z["datum"]) or date.min) < (parsiraj_datum(nz["datum"]) or date.max):
                    z["ishod"] = "neuspelo"
                    z["ter"] = "da"
                    self.ist.dodaj(majka, AUTO, (f"Mating of {z['datum']} marked as failed (the female is in heat again)" if EN else f"Parenje od {z['datum']} označeno kao neuspelo (ženka se ponovo tera)"),
                                   datum=nz["datum"], automatski=True)


    def obavestenja_ter(self, x=None):
        danas = date.today()
        rez = []
        # posle parenja: proveriti ter
        for z in self.cekaju_porodjaj():
            if z.get("ter"):
                continue
            majka, otac = self.roditelji_parenja(z)
            if x is not None and x != majka:
                continue
            dp = parsiraj_datum(z["datum"])
            if not dp or majka not in self.model.A:
                continue
            c = self.ciklus_tera(self.model.A[majka]["vrsta"])
            ds = (danas - dp).days
            if c - 3 <= ds <= c + 7:
                kad = dp + timedelta(days=c)
                rez.append(dict(nivo=1, grlo=majka, naslov=(f"Check for heat – day {ds} after mating" if EN else f"Proveri ter – {ds}. dan od parenja"),
                                opis=(f"Mated {z['datum']} with {otac or '?'}. If she is not in heat around {kad.strftime('%d/%m')} "
                                     f"(cycle {c} d.), she is probably pregnant." if EN else f"Pareno {z['datum']} sa {otac or '?'}. Ako se ne tera oko {kad.strftime('%d.%m.')} "
                                     f"(ciklus {c} d.), verovatno je gravidna."),
                                datum=kad, akcije=[(("Not in heat" if EN else "Ne tera se"), lambda z=z: self.ne_tera_se(z), "Primary"),
                                                   (("In heat" if EN else "Tera se"), lambda z=z: self.tera_se(z), "Secondary")]))
        # ženke koje nisu gravidne: sledeći ter iz poslednjeg zabeleženog tera
        poslednji = {}
        for z in self.ist.zapisi:
            if z["dogadjaj"] == TER and not z["automatski"]:
                d = parsiraj_datum(z["datum"])
                if d and (z["grlo"] not in poslednji or d > poslednji[z["grlo"]]):
                    poslednji[z["grlo"]] = d
        gravidne = {self.roditelji_parenja(z)[0] for z in self.cekaju_porodjaj()}
        for g, d in poslednji.items():
            if (x is not None and x != g) or g in gravidne or g not in self.model.A or not self.model.A[g]["aktivno"]:
                continue
            if any(z["dogadjaj"] == PARENJE and self.roditelji_parenja(z)[0] == g and
                   (parsiraj_datum(z["datum"]) or date.min) >= d for z in self.ist.zapisi):
                continue
            c = self.ciklus_tera(self.model.A[g]["vrsta"])
            sl = d + timedelta(days=c)
            while sl < danas - timedelta(days=2):
                sl += timedelta(days=c)
            if (sl - danas).days <= 3:
                rez.append(dict(nivo=2 if sl > danas else 1, grlo=g,
                                naslov=("Heat expected " if EN else "Očekuje se ter ") + (("today" if EN else "danas") if sl == danas else (f"around {sl.strftime('%d/%m')}" if EN else f"oko {sl.strftime('%d.%m.')}")),
                                opis=(f"Last heat {d.strftime('%d/%m/%Y')} · cycle {c} days. Watch whether she comes into heat." if EN else f"Poslednji ter {d.strftime('%d.%m.%Y')} · ciklus {c} dana. Prati da li se tera."),
                                datum=sl, akcije=[(("Record mating" if EN else "Upiši parenje"), lambda g=g: self.dogadjaj_forma(
                                    g, preset={"dogadjaj": PARENJE}), "Primary"),
                                                  (("In heat" if EN else "Tera se"), lambda g=g: self.dogadjaj_forma(
                                                      g, preset={"dogadjaj": TER}), "Secondary")]))
        return rez


    # ================================================================ KARENCA
    def karenca(self, x):
        """{'meso': (do_datum, zapis), 'mleko': (...)} – samo karence koje još traju."""
        return self.karence_sve().get(x, {})

    def karence_sve(self):
        """Karence koje traju, za sva grla odjednom (jedan prolaz kroz istoriju umesto jednog po grlu)."""
        z_ = self.ist.zapisi
        kljuc = (id(z_), len(z_), date.today(), getattr(self, "_ver_podataka", 0))
        kes = getattr(self, "_kes_karenca", None)
        if kes and kes[0] == kljuc:
            return kes[1]
        danas = date.today()
        sve = {}
        for z in z_:
            if not (z.get("karenca_meso") or z.get("karenca_mleko")):
                continue
            d = parsiraj_datum(z["datum"])
            if not d:
                continue
            for vrsta, kljuc in (("meso", "karenca_meso"), ("mleko", "karenca_mleko")):
                try:
                    n = int(z.get(kljuc) or 0)
                except ValueError:
                    n = 0
                if n > 0:
                    do = d + timedelta(days=n)
                    rez = sve.setdefault(z["grlo"], {})
                    if do >= danas and (vrsta not in rez or do > rez[vrsta][0]):
                        rez[vrsta] = (do, z)
        sve = {g: r for g, r in sve.items() if r}
        self._kes_karenca = (kljuc, sve)
        return sve


    def opis_karence(self, x, kratko=False):
        k = self.karenca(x)
        if not k:
            return ""
        delovi = []
        for vrsta in ("meso", "mleko"):
            if vrsta in k:
                do = k[vrsta][0]
                ost = (do - date.today()).days
                delovi.append((f"{dict(meso='meat', mleko='milk')[vrsta]} until {do.strftime('%d/%m')}" if EN else f"{vrsta} do {do.strftime('%d.%m.')}") + ("" if kratko else (f" ({ost} d. left)" if EN else f" (još {ost} d.)")))
        return ", ".join(delovi)


    def obavestenja_karenca(self, x=None):
        rez = []
        sve = self.karence_sve()
        for a in self.model.grla(True):
            if (x is not None and a["id"] != x) or a["id"] not in sve:
                continue
            k = self.karenca(a["id"])
            if not k:
                continue
            z = max(k.values(), key=lambda t: t[0])[1]
            rez.append(dict(nivo=2, grlo=a["id"], naslov=("Withdrawal – " if EN else "Karenca – ") + self.opis_karence(a["id"]),
                            opis=(f"After: {z['dogadjaj'].lower()} {z['datum']}" if EN else f"Posle: {z['dogadjaj'].lower()} {z['datum']}") + (f" ({z['vrednost']})" if z["vrednost"] else "")
                                 + (". Do not sell for slaughter / do not deliver milk while the withdrawal period lasts." if EN else ". Ne prodavati za klanje / ne isporučivati mleko dok karenca traje."),
                            datum=min(t[0] for t in k.values()), akcije=[]))
        return rez


    def okvir_karence(self, parent, vars_, vrednosti=("", "")):
        """Dva polja za karencu (meso, mleko) – za lečenje i vakcinaciju."""
        f = tk.Frame(parent, bg=SURF)
        for i, (naslov, kljuc, v0) in enumerate(((("Meat withdrawal (days)" if EN else "Karenca meso (dana)"), "karenca_meso", vrednosti[0]),
                                                (("milk (days)" if EN else "mleko (dana)"), "karenca_mleko", vrednosti[1]))):
            ff = tk.Frame(f, bg=SURF)
            ff.pack(side="left", padx=(0 if i == 0 else 8, 0))
            self.lbl(ff, naslov, 9, "bold", fg=BAD).pack(anchor="w")
            v = tk.StringVar(value=v0)
            ttk.Entry(ff, textvariable=v, width=7, font=self.f(10)).pack(anchor="w", pady=(3, 0))
            vars_[kljuc] = v
        return f


    @staticmethod
    def broj_dana(v):
        t = "".join(ch for ch in str(v or "") if ch.isdigit())
        return t if t and int(t) > 0 else ""


    # ================================================================ PLODNOST
    def _ix_plodnosti(self):
        """Porođaji po grlu, parenja po majci i broj potomaka – jednom za celo stado."""
        z_ = self.ist.zapisi
        kljuc = (id(z_), len(z_), id(self.model), getattr(self, "_ver_podataka", 0))
        kes = getattr(self, "_kes_plodnost", None)
        if kes and kes[0] == kljuc:
            return kes[1]
        por, par, pot = {}, {}, {}
        por_naziv = ("Birth" if EN else "Porođaj")
        for z in z_:
            if z["dogadjaj"] == por_naziv:
                por.setdefault(z["grlo"], []).append(z)
            elif z["dogadjaj"] == PARENJE and not z["automatski"]:
                par.setdefault(self.roditelji_parenja(z)[0], []).append(z)
        for pr in self.model.P.values():
            for r in set(pr):
                if r:
                    pot[r] = pot.get(r, 0) + 1
        ix = dict(por=por, par=par, pot=pot)
        self._kes_plodnost = (kljuc, ix)
        return ix

    def plodnost(self, x):
        import re
        ix = self._ix_plodnosti()
        por = sorted(ix["por"].get(x, []), key=lambda z: parsiraj_datum(z["datum"]) or date.min)
        zivih = mrtvih = 0
        for z in por:
            v = "".join(ch for ch in z.get("vrednost", "") if ch.isdigit())
            zivih += int(v) if v else 1
            mm = re.search((r"stillborn:\s*(\d+)" if EN else r"mrtvorođenih:\s*(\d+)"), z.get("opis", ""))
            mrtvih += int(mm.group(1)) if mm else 0
        datumi = [parsiraj_datum(z["datum"]) for z in por if parsiraj_datum(z["datum"])]
        razmaci = [(b - a).days for a, b in zip(datumi, datumi[1:]) if (b - a).days > 20]
        parenja = ix["par"].get(x, [])
        neuspela = sum(1 for z in parenja if z.get("ishod") == "neuspelo")
        a = self.model.A.get(x, {})
        prvi = None
        if datumi and a.get("datum"):
            prvi = (datumi[0].year - a["datum"].year) * 12 + datumi[0].month - a["datum"].month
        potomaka = ix["pot"].get(x, 0)
        return dict(porodjaja=len(por), zivih=zivih, mrtvih=mrtvih,
                    prosek=(zivih / len(por)) if por else 0,
                    razmak=(sum(razmaci) / len(razmaci)) if razmaci else None,
                    parenja=len(parenja), neuspela=neuspela,
                    po_gravidnosti=(len(parenja) / len(por)) if por and len(parenja) >= len(por) else None,
                    prvi_mes=prvi, potomaka=potomaka, poslednji=datumi[-1] if datumi else None)


    def kartica_plodnosti(self, body):
        m = self.model
        redovi = []
        for a in m.grla(True):
            if a["pol"] != "z":
                continue
            p = self.plodnost(a["id"])
            if p["porodjaja"] or p["parenja"]:
                redovi.append((a, p))
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, ("Female fertility" if EN else "Plodnost ženki"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("Sorted by young per birth. Helps you choose which females to keep for breeding." if EN else "Poređano po broju mladih po porođaju. Pomaže da izabereš koje ženke zadržati za priplod."), 9,
                 fg=INK2).pack(anchor="w", pady=(0, 10))
        if not redovi:
            self.lbl(c, ("No matings or births recorded yet." if EN else "Još nema upisanih parenja ni porođaja."), 10, fg=INK2).pack(anchor="w")
            return
        redovi.sort(key=lambda t: (-t[1]["prosek"], -t[1]["porodjaja"]))
        wrap, tv = self.tabela(c, [("id", ("Female" if EN else "Ženka"), 95), ("rasa", ("Breed" if EN else "Rasa"), 100), ("por", ("Births" if EN else "Porođaja"), 80, "e"),
                                   ("ziv", ("Alive" if EN else "Živih"), 60, "e"), ("pros", ("Average" if EN else "Prosek"), 70, "e"),
                                   ("mrt", ("Stillborn" if EN else "Mrtvih"), 65, "e"), ("raz", ("Interval (d.)" if EN else "Razmak (d.)"), 90, "e"),
                                   ("par", ("Matings/birth" if EN else "Parenja/porođ."), 105, "e"), ("pos", ("Last" if EN else "Poslednji"), 95)],
                               visina=min(10, len(redovi)))
        wrap.pack(fill="x")
        if EN:
            for i, (a, p) in enumerate(redovi):
                tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag, values=(
                    a["rasa"] or "–", p["porodjaja"], p["zivih"], f"{p['prosek']:.1f}" if p["porodjaja"] else "–",
                    p["mrtvih"] or "–", round(p["razmak"]) if p["razmak"] else "–",
                    f"{p['po_gravidnosti']:.1f}" if p["po_gravidnosti"] else "–",
                    p["poslednji"].strftime("%d/%m/%Y") if p["poslednji"] else "–"), tags=["odd"] if i % 2 else [])
        else:
            for i, (a, p) in enumerate(redovi):
                tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag, values=(
                    a["rasa"] or "–", p["porodjaja"], p["zivih"], f"{p['prosek']:.1f}".replace(".", ",") if p["porodjaja"] else "–",
                    p["mrtvih"] or "–", round(p["razmak"]) if p["razmak"] else "–",
                    f"{p['po_gravidnosti']:.1f}".replace(".", ",") if p["po_gravidnosti"] else "–",
                    p["poslednji"].strftime("%d.%m.%Y") if p["poslednji"] else "–"), tags=["odd"] if i % 2 else [])
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))


    # ---------- obaveštenja i podsetnici
    def obavestenja(self, x=None):
        """Sva obaveštenja: [{nivo, grlo, naslov, opis, kljuc, akcije:[(tekst, fn, stil)]}]. nivo: 0 hitno, 1 uskoro, 2 info, 3 zakazano."""
        m = self.model
        danas = date.today()
        rez = []
        # 1) porođaji
        for z in self.cekaju_porodjaj():
            majka, otac = self.roditelji_parenja(z)
            if x is not None and x not in (majka, otac, z["grlo"]):
                continue
            oc, od = self.ocekivani_porodjaj(z), self.upis_moguc_od(z)
            if not oc:
                continue
            dana = (oc - danas).days
            dk = self.najkasniji_porodjaj(z)
            par = (f"{majka or '?'} × {otac or '?'}, mated {z['datum']}" if EN else f"{majka or '?'} × {otac or '?'}, pareno {z['datum']}")
            akc = [(("Young born" if EN else "Dobijeni mladi"), lambda z=z: self.upis_podmlatka(z), "Primary"),
                   (("Failed" if EN else "Nije uspelo"), lambda z=z: self.oznaci_neuspelo(z), "Secondary")]
            if dk and danas > dk:
                rez.append(dict(nivo=0, grlo=majka, naslov=(f"Due date passed {(danas - dk).days} d. ago" if EN else f"Termin porođaja je prošao pre {(danas - dk).days} d."),
                                opis=(f"Latest {dk.strftime('%d/%m/%Y')} · {par}. Enter the young or mark the mating as failed." if EN else f"Najkasnije {dk.strftime('%d.%m.%Y')} · {par}. Upiši mlade ili označi da parenje nije uspelo."),
                                datum=dk, akcije=akc))
            elif od and danas >= od:
                rez.append(dict(nivo=1, grlo=majka, naslov=("Birth expected " if EN else "Porođaj se očekuje ") +
                                (("today" if EN else "danas") if dana == 0 else (f"in {dana} d." if EN else f"za {dana} d.") if dana > 0 else ("any day now" if EN else "svakog dana")),
                                opis=(f"Around {oc.strftime('%d/%m/%Y')}, latest {dk.strftime('%d/%m/%Y')} · {par}. "
                                     "Entering young is open." if EN else f"Oko {oc.strftime('%d.%m.%Y')}, najkasnije {dk.strftime('%d.%m.%Y')} · {par}. "
                                     "Upis mladih je otvoren."),
                                datum=oc, akcije=akc))
            elif dana <= 21:
                rez.append(dict(nivo=2, grlo=majka, naslov=(f"Birth in {dana} d." if EN else f"Porođaj za {dana} d."),
                                opis=(f"Due {oc.strftime('%d/%m/%Y')} · {par}. Prepare the birthing area." if EN else f"Termin {oc.strftime('%d.%m.%Y')} · {par}. Pripremi prostor za porođaj."),
                                datum=oc, akcije=[]))
        # 2) mladi čekaju minđušu
        for z in self.cekaju_mindjusu(x):
            uk, dd, vec = self.leglo(z)
            majka, otac = self.roditelji_parenja(z)
            dr = parsiraj_datum(dd)
            star = (danas - dr).days if dr else 0
            n_ = nazivi(self.vrsta_parenja(z))
            rez.append(dict(nivo=1 if star >= 14 else 2, grlo=majka,
                            naslov=(f"{uk - len(vec)} {n_[3]} waiting for ear tag ({star} d.)" if EN else f"{uk - len(vec)} {n_[3]} čeka minđušu ({star} d.)"),
                            opis=(f"Born {dd} · {majka or '?'} × {otac or '?'}. Enter them in the animal list when they get their ear tags." if EN else f"Rođeno {dd} · {majka or '?'} × {otac or '?'}. Upiši ih u listu grla kad dobiju minđušu."),
                            datum=dr, akcije=[(("Enter in list" if EN else "Upiši u listu"), lambda z=z: self.upis_u_listu(z), "Primary"),
                                              (("Remove…" if EN else "Ukloni…"), lambda z=z: self.ukloni_iz_legla(z), "Secondary")]))
        # 3) podsetnici
        for p in self.pods.aktivni(x):
            d = parsiraj_datum(p["datum"]) or danas
            dana = (d - danas).days
            nivo = 0 if dana < 0 else 1 if dana <= 3 else 3
            kad = ((f"{-dana} d. overdue" if EN else f"zakasnelo {-dana} d.") if dana < 0 else ("today" if EN else "danas") if dana == 0 else
                   ("tomorrow" if EN else "sutra") if dana == 1 else (f"in {dana} d." if EN else f"za {dana} d."))
            pon = int(p.get("ponavljanje") or 0)
            rez.append(dict(nivo=nivo, grlo=p["grlo"] or None, naslov=(f"{p['tip'] or 'Reminder'} – {kad}" if EN else f"{p['tip'] or 'Podsetnik'} – {kad}"),
                            opis=f"{p['datum']}" + (f" · {p['tekst']}" if p["tekst"] else "") +
                                 ((f" · repeats every {pon} d." if EN else f" · ponavlja se na {pon} d.") if pon else ""),
                            datum=d, podsetnik=p,
                            akcije=[(("Done" if EN else "Urađeno"), lambda p=p: self.podsetnik_uradjen(p), "Primary"),
                                    (("Postpone 7 d." if EN else "Odloži 7 d."), lambda p=p: self.podsetnik_odlozi(p, 7), "Secondary"),
                                    (("Edit" if EN else "Izmeni"), lambda p=p: self.podsetnik_forma(zapis=p), "Secondary")]))
        # 4) ter i karenca
        rez += self.obavestenja_ter(x)
        rez += self.obavestenja_karenca(x)
        # 5) greške u podacima
        if x is None and m.warn:
            rez.append(dict(nivo=2, grlo=None, naslov=(f"{len(m.warn)} warnings in the data" if EN else f"{len(m.warn)} upozorenja u podacima"),
                            opis=("The program found possible errors in the pedigree (e.g. wrong sex of a parent or a date)." if EN else "Program je našao moguće greške u rodoslovu (npr. pogrešan pol roditelja ili datum)."),
                            datum=None, akcije=[(("Show" if EN else "Prikaži"), lambda: self.prikazi("pregled"), "Secondary")]))
        rez.sort(key=lambda o: (o["nivo"], o["datum"] or date.max))
        return rez


    def broj_obavestenja(self):
        try:
            return sum(1 for o in self.obavestenja() if o["nivo"] <= 1)
        except Exception:
            return 0


    def osvezi_nav_brojac(self):
        if "obavestenja" not in self.nav:
            return
        n = self.broj_obavestenja()
        row, li, lt = self.nav["obavestenja"]
        lt.config(text=("Notifications" if EN else "Obaveštenja") + (f"  ({n})" if n else ""))
        li.config(fg=BAD if n else (BRAND if self.strana == "obavestenja" else INK2))


    def red_obavestenja(self, parent, o, bg=SURF, kompakt=False):
        boje = {0: (BAD, BAD_BG, ("Urgent" if EN else "Hitno")), 1: (WARN, WARN_BG, ("Soon" if EN else "Uskoro")), 2: (BRAND, SURF2, "Info"),
                3: (INK2, SURF2, ("Scheduled" if EN else "Zakazano"))}
        fg, bgb, txt = boje[o["nivo"]]
        r = tk.Frame(parent, bg=bg)
        r.pack(fill="x", pady=4)
        tk.Frame(r, bg=fg, width=4).pack(side="left", fill="y", padx=(0, 12))
        lev = tk.Frame(r, bg=bg)
        lev.pack(side="left", fill="x", expand=True)
        gornji = tk.Frame(lev, bg=bg)
        gornji.pack(anchor="w")
        if not kompakt:
            tk.Label(gornji, text=f" {txt} ", font=self.f(8, "bold"), bg=bgb, fg=fg).pack(side="left", padx=(0, 8))
        if o["grlo"] and not kompakt:
            self.cip(gornji, o["grlo"], lambda g=o["grlo"]: self.karton(g), bg=bg,
                     siv=o["grlo"] not in self.model.A or self.model.A[o["grlo"]]["osnivac"]).pack(side="left", padx=(0, 8))
        self.lbl(gornji, o["naslov"], 10, "bold", fg=fg if o["nivo"] == 0 else INK, bg=bg).pack(side="left")
        self.lbl(lev, o["opis"], 9, fg=INK2, bg=bg, wraplength=380 if kompakt else 560,
                 justify="left").pack(anchor="w", pady=(2, 0))
        if kompakt:
            if o["akcije"]:
                ak = tk.Frame(lev, bg=bg)
                ak.pack(anchor="w", pady=(3, 0))
                for t, fn, stil in o["akcije"][:2]:
                    lk = self.lbl(ak, t, 9, "bold", fg=BRAND, bg=bg, cursor="hand2")
                    lk.pack(side="left", padx=(0, 14))
                    lk.bind("<Button-1>", lambda e, fn=fn: fn())
            return r
        if o["akcije"]:
            dd = tk.Frame(r, bg=bg)
            dd.pack(side="right", padx=(10, 0))
            for t, fn, stil in reversed(o["akcije"] if not kompakt else o["akcije"][:1]):
                self.btn(dd, t, fn, stil).pack(side="right", padx=(6, 0))
        return r


    def s_obavestenja(self):
        body = self.strana_okvir()
        sva = self.obavestenja()
        aktivna = [o for o in sva if o["nivo"] <= 2]
        zakazano = [o for o in sva if o["nivo"] == 3]
        n = sum(1 for o in sva if o["nivo"] <= 1)
        self.zaglavlje(body, ("Notifications" if EN else "Obaveštenja"),
                       ((f"{n} {'thing needs' if n == 1 else 'things need'} attention." if EN else f"{n} {'stvar traži' if n == 1 else 'stvari traže'} pažnju.") if n else
                        ("Nothing urgent." if EN else "Nema ničeg hitnog.")) + (" The program tracks births, heat, withdrawal periods, untagged young and reminders." if EN else " Program sam prati porođaje, ter, karencu, mlade bez minđuše i podsetnike."),
                       [(("+  New reminder" if EN else "+  Novi podsetnik"), lambda: self.podsetnik_forma(), "Primary")])
        if not aktivna and not zakazano:
            self.napomena(body, ("All is well – no notifications. Add a reminder for an animal (vaccination, "
                                "treatment, sale…) with the \"New reminder\" button." if EN else "Sve je u redu – nema obaveštenja. Dodaj podsetnik za grlo (vakcinacija, "
                                "lečenje, prodaja…) dugmetom „Novi podsetnik“."), ok=True)
            return
        for nivo, naslov in ((0, ("Urgent" if EN else "Hitno")), (1, ("Soon" if EN else "Uskoro")), (2, ("For information" if EN else "Za informaciju"))):
            grupa = [o for o in aktivna if o["nivo"] == nivo]
            if not grupa:
                continue
            o_, c_ = self.card(body, 18, 12)
            o_.pack(fill="x", pady=(0, 14))
            self.lbl(c_, f"{naslov} ({len(grupa)})", 12, "bold", fg=BAD if nivo == 0 else INK).pack(anchor="w", pady=(0, 4))
            self._redovi_sa_vise(c_, grupa, nivo)
        if zakazano:
            o_, c_ = self.card(body, 18, 12)
            o_.pack(fill="x", pady=(0, 14))
            self.lbl(c_, (f"Scheduled reminders ({len(zakazano)})" if EN else f"Zakazani podsetnici ({len(zakazano)})"), 12, "bold").pack(anchor="w", pady=(0, 4))
            self._redovi_sa_vise(c_, zakazano, 3)


    def _redovi_sa_vise(self, c_, grupa, kljuc, korak=60):
        """Veliko stado ima i hiljadu obaveštenja – prikazuje se deo, ostalo na dugme (strana ostaje brza)."""
        lim = self.ui.setdefault("ob_lim", {}).get(kljuc, korak)
        for o in grupa[:lim]:
            self.red_obavestenja(c_, o)
        if len(grupa) > lim:
            def jos():
                self.ui["ob_lim"][kljuc] = lim + 200
                self.prikazi("obavestenja")
            self.btn(c_, (f"Show more ({len(grupa) - lim})" if EN else f"Prikaži još ({len(grupa) - lim})"), jos).pack(anchor="w", pady=(8, 0))

    def obavestenja_na_startu(self):
        sva = [o for o in self.obavestenja() if o["nivo"] <= 1]
        if not sva:
            return
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Notifications" if EN else "Obaveštenja"))
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        h = sum(1 for o in sva if o["nivo"] == 0)
        self.lbl(b, (f"You have {len(sva)} notifications" if EN else f"Imaš {len(sva)} obaveštenja"), 15, "bold").pack(anchor="w")
        self.lbl(b, ((f"{h} urgent · " if EN else f"{h} hitno · ") if h else "") + (f"{len(sva) - h} soon" if EN else f"{len(sva) - h} uskoro"), 9, fg=BAD if h else INK2).pack(anchor="w", pady=(2, 10))
        for o in sva[:5]:
            r = tk.Frame(b, bg=SURF)
            r.pack(fill="x", pady=3)
            tk.Frame(r, bg=BAD if o["nivo"] == 0 else WARN, width=4, height=34).pack(side="left", padx=(0, 10))
            if o["grlo"]:
                self.cip(r, o["grlo"]).pack(side="left", padx=(0, 8))
            self.lbl(r, o["naslov"], 10, "bold").pack(side="left")
        if len(sva) > 5:
            self.lbl(b, (f"… and {len(sva) - 5} more" if EN else f"… i još {len(sva) - 5}"), 9, fg=INK2).pack(anchor="w", pady=(4, 0))
        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Open notifications" if EN else "Otvori obaveštenja"), lambda: (win.destroy(), self.prikazi("obavestenja")), "Primary").pack(side="right")
        self.btn(fb, ("Later" if EN else "Kasnije"), win.destroy).pack(side="right", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, None)


    def podsetnik_uradjen(self, p):
        d = date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
        p["gotovo"] = d
        if p["grlo"]:
            tip = p["tip"] if p["tip"] in DOGADJAJI else ("Note" if EN else "Napomena")
            self.ist.dodaj(p["grlo"], tip, (p["tip"] + ": " if tip == ("Note" if EN else "Napomena") and p["tip"] not in ("", ("Note" if EN else "Napomena"))
                                            else "") + (p["tekst"] or ("done as reminded" if EN else "urađeno po podsetniku")), datum=d)
        pon = int(p.get("ponavljanje") or 0)
        if pon:
            sl = (parsiraj_datum(p["datum"]) or date.today()) + timedelta(days=pon)
            while sl <= date.today():
                sl += timedelta(days=pon)
            self.pods.dodaj(p["grlo"], sl.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), p["tip"], p["tekst"], pon)
        self.promena((f"Done: {p['tip'] or 'reminder'}" if EN else f"Urađeno: {p['tip'] or 'podsetnik'}") + (f" – {p['grlo']}" if p["grlo"] else "") +
                     ((" · the next one is scheduled" if EN else " · sledeći je zakazan") if pon else ""))
        self.posle_obavestenja()


    def podsetnik_odlozi(self, p, dana):
        d = max(parsiraj_datum(p["datum"]) or date.today(), date.today()) + timedelta(days=dana)
        p["datum"] = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
        self.promena((f"Reminder postponed to {p['datum']}" if EN else f"Podsetnik odložen za {p['datum']}"))
        self.posle_obavestenja()


    def posle_obavestenja(self):
        self.osvezi_nav_brojac()
        if getattr(self, "ist_win", None) and self.ist_win.winfo_exists() and getattr(self.ist_win, "grlo", None):
            self.istorija_prozor(self.ist_win.grlo)
        if self.karton_win and self.karton_win.winfo_exists() and getattr(self.karton_win, "grlo", None):
            self.karton(self.karton_win.grlo)


    def podsetnik_forma(self, grlo=None, zapis=None, parent=None):
        m = self.model
        z = zapis or {}
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Edit reminder" if EN else "Izmena podsetnika") if zapis else ("New reminder" if EN else "Novi podsetnik"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Edit reminder" if EN else "Izmena podsetnika") if zapis else ("New reminder" if EN else "Novi podsetnik"), 16, "bold").pack(anchor="w")
        self.lbl(b, ("The program will notify you when the day comes (and 3 days before)." if EN else "Program će te obavestiti kad dođe dan (i 3 dana pre toga)."), 9, fg=INK2).pack(anchor="w", pady=(2, 10))
        g = tk.Frame(b, bg=SURF)
        g.pack(fill="x")
        gv = tk.StringVar(value=z.get("grlo") or grlo or "")
        dv = tk.StringVar(value=z.get("datum") or (date.today() + timedelta(days=7)).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        f = tk.Frame(g, bg=SURF)
        f.grid(row=0, column=0, sticky="w", padx=(0, 16))
        self.lbl(f, ("Animal (empty = whole herd)" if EN else "Grlo (prazno = celo stado)"), 9, "bold", fg=INK2).pack(anchor="w")
        ttk.Combobox(f, textvariable=gv, values=[a["id"] for a in m.grla()], width=18, font=self.f(10)).pack(anchor="w", pady=(3, 0))
        f = tk.Frame(g, bg=SURF)
        f.grid(row=0, column=1, sticky="w")
        self.lbl(f, ("Date" if EN else "Datum"), 9, "bold", fg=INK2).pack(anchor="w")
        de = tk.Frame(f, bg=SURF)
        de.pack(anchor="w", pady=(3, 0))
        ttk.Entry(de, textvariable=dv, width=12, font=self.f(10)).pack(side="left")
        for t, dn in (("+7", 7), ("+30", 30), ("+90", 90)):
            lk = self.lbl(de, t, 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(side="left", padx=(8, 0))
            lk.bind("<Button-1>", lambda e, dn=dn: dv.set((date.today() + timedelta(days=dn)).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))))
        self.lbl(b, ("What needs to be done" if EN else "Šta treba uraditi"), 9, "bold", fg=INK2).pack(anchor="w", pady=(12, 4))
        tv = tk.StringVar(value=z.get("tip", ("Vaccination" if EN else "Vakcinacija")))
        self.izbor_dogadjaja(b, tv, po_redu=5).pack(anchor="w")
        self.lbl(b, ("Description" if EN else "Opis"), 9, "bold", fg=INK2).pack(anchor="w", pady=(10, 3))
        xv = tk.StringVar(value=z.get("tekst", ""))
        ttk.Entry(b, textvariable=xv, width=60, font=self.f(10)).pack(anchor="w", fill="x")
        self.lbl(b, ("e.g. foot-and-mouth vaccine, check after treatment, sale to a buyer…" if EN else "npr. vakcina protiv šapa i slinavke, kontrola posle lečenja, prodaja kupcu…"), 8, fg="#8A968D").pack(anchor="w")
        pf = tk.Frame(b, bg=SURF)
        pf.pack(anchor="w", pady=(10, 0))
        self.lbl(pf, ("Repeat" if EN else "Ponavljanje"), 9, "bold", fg=INK2).pack(side="left", padx=(0, 8))
        opc = {("does not repeat" if EN else "ne ponavlja se"): 0, ("every week" if EN else "svake nedelje"): 7, ("every month" if EN else "svakog meseca"): 30, ("every 3 months" if EN else "na 3 meseca"): 90,
               ("every 6 months" if EN else "na 6 meseci"): 182, ("every year" if EN else "svake godine"): 365}
        pon0 = int(z.get("ponavljanje") or 0)
        pv = tk.StringVar(value=next((k for k, v in opc.items() if v == pon0), (f"every {pon0} days" if EN else f"svakih {pon0} dana") if pon0 else ("does not repeat" if EN else "ne ponavlja se")))
        ttk.Combobox(pf, textvariable=pv, values=list(opc), width=16, font=self.f(10)).pack(side="left")
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            gr = gv.get().strip()
            if gr:
                g2 = m.nadji(gr)
                if not g2:
                    err.config(text=(f"Animal \"{gr}\" was not found." if EN else f"Grlo „{gr}“ nije pronađeno."))
                    return
                gr = g2
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            tip = tv.get().strip()
            if not tip:
                err.config(text=("Choose what needs to be done." if EN else "Izaberi šta treba uraditi."))
                return
            pt = pv.get().strip()
            if pt in opc:
                pon = opc[pt]
            else:
                cif = "".join(ch for ch in pt if ch.isdigit())
                pon = int(cif) if cif else 0
            if zapis:
                zapis.update(grlo=gr, datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), tip=tip, tekst=xv.get().strip(), ponavljanje=str(pon))
            else:
                self.pods.dodaj(gr, d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), tip, xv.get().strip(), pon)
            win.grab_release()
            win.destroy()
            self.promena((f"Reminder saved for {d.strftime('%d/%m/%Y')}" if EN else f"Podsetnik sačuvan za {d.strftime('%d.%m.%Y')}"))
            self.posle_obavestenja()

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        if zapis:
            def obrisi():
                if messagebox.askyesno(("Delete reminder" if EN else "Obriši podsetnik"), ("Delete this reminder?" if EN else "Obrisati ovaj podsetnik?"), parent=win):
                    self.pods.zapisi.remove(zapis)
                    win.grab_release()
                    win.destroy()
                    self.promena(("Reminder deleted." if EN else "Podsetnik obrisan."))
                    self.posle_obavestenja()
            self.btn(fb, ("Delete" if EN else "Obriši"), obrisi, "Danger").pack(side="left")
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, parent)
