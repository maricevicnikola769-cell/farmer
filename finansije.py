"""Finansije: prihodi i troškovi farme (po kategoriji, po grlu i stadu), pregled po periodu i trošak po litru mleka.
Čuvaju se u <tablica>_finansije.csv pored tablice grla, ulaze u rezervne kopije i u izvoz u Excel."""
import csv
import os
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from osnova import EN, _uz_tablicu, prevedi_vrednost
from jezik import T
from podaci import kolona, parsiraj_datum, sada, sort_key
from izgled import BAD, BG, BRAND, INK, INK2, LINE, OK, SURF, WARN

PRIHOD, TROSAK = "prihod", "trosak"      # unutrašnje oznake (ne zavise od jezika)
FIN_KOLONE = ["datum", "vrsta", "kategorija", "iznos", "grlo", "stado", "opis", "uneto"]
EN_FIN = {"datum": "date", "vrsta": "type", "kategorija": "category", "iznos": "amount", "grlo": "animal",
          "stado": "herd", "opis": "description", "uneto": "added"}


def kategorije(vrsta):
    """Predlog kategorija (može se upisati i svoja)."""
    if vrsta == PRIHOD:
        return [T("Prodaja mleka", "Milk sales"), T("Prodaja grla", "Animal sales"), T("Prodaja mesa", "Meat sales"),
                T("Subvencije", "Subsidies"), T("Ostali prihodi", "Other income")]
    return [T("Hrana (koncentrat, seno, silaža)", "Feed (concentrate, hay, silage)"), T("Veterinar i lekovi", "Vet and medicines"),
            T("Osemenjavanje", "Insemination"), T("Kupovina grla", "Animal purchases"), T("Radnici", "Labour"),
            T("Gorivo i struja", "Fuel and electricity"), T("Oprema i popravke", "Equipment and repairs"),
            T("Zakup zemlje", "Land rent"), T("Ostali troškovi", "Other costs")]


def broj(v):
    t = str(v if v is not None else "").strip().replace(" ", "").replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:                    # 1.234,50 ili 1,234.50
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    else:
        t = t.replace(",", ".")
    try:
        x = float(t)
    except ValueError:
        return None
    return x if abs(x) != float("inf") and x == x else None


def fmt_novac(x, valuta=""):
    t = f"{x:,.2f}".rstrip("0").rstrip(".") if abs(x - round(x)) > 0.004 else f"{x:,.0f}"
    if not EN:
        t = t.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{t} {valuta}".strip()


class Finansije:
    """Zapisi prihoda i troškova, u <tablica>_finansije.csv."""

    def __init__(self, putanja_tablice):
        self.tablica = putanja_tablice
        self.putanja = _uz_tablicu(putanja_tablice, "_finansije.csv", "_finances.csv")
        self.zapisi = []
        if os.path.isfile(self.putanja):
            kod = "utf-8-sig"
            try:
                open(self.putanja, encoding=kod).read()
            except UnicodeDecodeError:
                kod = "cp1250"
            with open(self.putanja, newline="", encoding=kod) as f:
                nazad = {v: k for k, v in EN_FIN.items()}
                for r in csv.DictReader(f, delimiter=";"):
                    r = {nazad.get(kolona(k), kolona(k)): (v or "").strip() for k, v in r.items() if k}
                    v = (r.get("vrsta") or "").lower()
                    r["vrsta"] = PRIHOD if v.startswith(("prih", "inc", "+")) else TROSAK
                    r["kategorija"] = prevedi_vrednost(r.get("kategorija", ""))
                    if parsiraj_datum(r.get("datum")) and broj(r.get("iznos")) is not None:
                        self.zapisi.append({k: r.get(k, "") for k in FIN_KOLONE})

    def sacuvaj(self):
        if not self.zapisi and not os.path.isfile(self.putanja):
            return
        tmp = self.putanja + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([EN_FIN[k] for k in FIN_KOLONE] if EN else FIN_KOLONE)
            for z in self.zapisi:
                vr = dict(z)
                if EN:
                    vr["vrsta"] = "income" if z["vrsta"] == PRIHOD else "cost"
                w.writerow([vr.get(k, "") for k in FIN_KOLONE])
        os.replace(tmp, self.putanja)

    def dodaj(self, datum, vrsta, kategorija, iznos, grlo="", stado="", opis=""):
        z = dict(datum=datum, vrsta=vrsta, kategorija=kategorija, iznos=("%.2f" % iznos).rstrip("0").rstrip("."),
                 grlo=grlo, stado=stado, opis=opis, uneto=sada())
        self.zapisi.append(z)
        return z

    def u_periodu(self, od=None, do=None):
        rez = []
        for z in self.zapisi:
            d = parsiraj_datum(z["datum"])
            if d and (od is None or d >= od) and (do is None or d <= do):
                rez.append(z)
        return sorted(rez, key=lambda z: (parsiraj_datum(z["datum"]), z["uneto"]), reverse=True)


def zbir(zapisi):
    """(prihodi, troškovi, po kategoriji {(vrsta, kat): iznos}, po grlu {grlo: [prihod, trošak]})."""
    pr = tr = 0.0
    kat, grla = {}, {}
    for z in zapisi:
        x = broj(z["iznos"]) or 0.0
        if z["vrsta"] == PRIHOD:
            pr += x
        else:
            tr += x
        k = (z["vrsta"], z["kategorija"] or T("bez kategorije", "uncategorised"))
        kat[k] = kat.get(k, 0.0) + x
        if z.get("grlo"):
            g = grla.setdefault(z["grlo"], [0.0, 0.0])
            g[0 if z["vrsta"] == PRIHOD else 1] += x
    return pr, tr, kat, grla


def period(izbor, danas=None):
    """(od, do) za izbor perioda: mesec, prošli mesec, godina, prošla godina, sve."""
    d = danas or date.today()
    if izbor == "mesec":
        return d.replace(day=1), d
    if izbor == "prosli_mesec":
        kraj = d.replace(day=1) - timedelta(days=1)
        return kraj.replace(day=1), kraj
    if izbor == "godina":
        return d.replace(month=1, day=1), d
    if izbor == "prosla_godina":
        return date(d.year - 1, 1, 1), date(d.year - 1, 12, 31)
    return None, None


class FinansijeDeo:
    """Strana „Finansije“."""

    @property
    def fin(self):
        """Finansije za trenutnu tablicu (učitavaju se po potrebi; posle promene tablice ili vraćanja kopije ponovo)."""
        f = getattr(self, "_fin", None)
        if f is None or f.tablica != self.tab.putanja:
            f = self._fin = Finansije(self.tab.putanja)
        return f

    def valuta(self):
        return self.pod.get("valuta") or T("RSD", "EUR")

    def s_finansije(self):
        st = self.ui.setdefault("fin", {"period": "mesec"})
        body = self.strana_okvir(scroll=True)
        self.zaglavlje(body, T("Finansije", "Finances"),
                       T("Prihodi i troškovi farme – po kategoriji, po grlu i po mesecima. Iznos se može vezati za grlo ili stado.",
                         "Farm income and costs – by category, by animal and by month. An amount can be linked to an animal or a herd."))
        val = self.valuta()

        # ---- unos
        o, c = self.card(body, 18, 14)
        o.pack(fill="x", pady=(0, 14))
        self.lbl(c, T("Novi upis", "New entry"), 11, "bold").grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))
        vrsta = tk.StringVar(value=st.get("vrsta", TROSAK))
        vf = tk.Frame(c, bg=SURF)
        vf.grid(row=1, column=0, sticky="w", padx=(0, 14))
        dv = tk.StringVar(value=date.today().strftime("%d/%m/%Y" if EN else "%d.%m.%Y"))
        kv, iv, gv, ov = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()

        def polje(col, naslov, var, w=14, vals=None, row=1, span=1):
            f = tk.Frame(c, bg=SURF)
            f.grid(row=row, column=col, columnspan=span, sticky="w", padx=(0, 14), pady=(0, 8))
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            e = (ttk.Combobox(f, textvariable=var, values=vals, width=w, font=self.f(10)) if vals is not None
                 else ttk.Entry(f, textvariable=var, width=w, font=self.f(10)))
            e.pack(anchor="w", pady=(4, 0))
            return e
        self.lbl(vf, T("Vrsta", "Type"), 9, "bold", fg=INK2).pack(anchor="w")
        rf = tk.Frame(vf, bg=SURF)
        rf.pack(anchor="w", pady=(4, 0))
        polje(1, T("Datum", "Date"), dv, 11)
        cb_kat = polje(2, T("Kategorija", "Category"), kv, 26, kategorije(vrsta.get()))
        e_iz = polje(3, T(f"Iznos ({val})", f"Amount ({val})"), iv, 12)
        ids = sorted((a["id"] for a in self.model.grla()), key=sort_key)
        polje(0, T("Grlo (nije obavezno)", "Animal (optional)"), gv, 12, ids, row=2)
        polje(1, T("Opis", "Description"), ov, 48, row=2, span=3)

        def promeni_vrstu():
            st["vrsta"] = vrsta.get()
            cb_kat.config(values=kategorije(vrsta.get()))
            if kv.get() not in kategorije(vrsta.get()):
                kv.set("")
        for k_, tekst in ((TROSAK, T("Trošak", "Cost")), (PRIHOD, T("Prihod", "Income"))):
            ttk.Radiobutton(rf, text=tekst, value=k_, variable=vrsta, style="Card.TRadiobutton",
                            command=promeni_vrstu).pack(side="left", padx=(0, 8))
        err = self.lbl(c, "", 9, "bold", fg=BAD)
        err.grid(row=3, column=0, columnspan=4, sticky="w")

        def dodaj(ev=None):
            d = parsiraj_datum(dv.get())
            x = broj(iv.get())
            if not d:
                err.config(text=T("Datum nije ispravan (npr. 15.03.2026).", "The date is not valid (e.g. 15/03/2026)."))
                return
            if x is None or x <= 0:
                err.config(text=T("Upiši iznos (npr. 12500 ili 12.500,50).", "Enter the amount (e.g. 12500 or 12,500.50)."))
                e_iz.focus_set()
                return
            if not kv.get().strip():
                err.config(text=T("Izaberi ili upiši kategoriju.", "Choose or type a category."))
                return
            g = self.model.nadji(gv.get()) if gv.get().strip() else ""
            if gv.get().strip() and not g:
                err.config(text=T("Grlo nije pronađeno.", "Animal not found."))
                return
            stado = self.model.A[g]["stado"] if g else ""
            self.fin.dodaj(d.strftime("%d/%m/%Y" if EN else "%d.%m.%Y"), vrsta.get(), " ".join(kv.get().split()), x, g or "", stado,
                           ov.get().strip())
            self.promena(T(f"Upisano: {fmt_novac(x, val)}", f"Saved: {fmt_novac(x, val)}"))
        self.btn(c, T("Dodaj", "Add"), dodaj, "Primary").grid(row=2, column=4, sticky="sw", pady=(0, 8))
        e_iz.bind("<Return>", dodaj)

        # ---- period i valuta
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        periodi = [("mesec", T("Ovaj mesec", "This month")), ("prosli_mesec", T("Prošli mesec", "Last month")),
                   ("godina", T("Ova godina", "This year")), ("prosla_godina", T("Prošla godina", "Last year")), ("sve", T("Sve", "All"))]
        self.lbl(tb, T("Period:", "Period:"), 10, "bold", fg=INK2).pack(side="left")
        pv = tk.StringVar(value=dict(periodi).get(st["period"], periodi[0][1]))
        cbp = ttk.Combobox(tb, textvariable=pv, values=[p[1] for p in periodi], state="readonly", width=16, font=self.f(10))
        cbp.pack(side="left", padx=(8, 20))
        cbp.bind("<<ComboboxSelected>>", lambda e: (st.update(period=next(k for k, n in periodi if n == pv.get())), self.prikazi("finansije")))
        self.lbl(tb, T("Valuta:", "Currency:"), 10, "bold", fg=INK2).pack(side="left")
        vv = tk.StringVar(value=val)
        cbv = ttk.Combobox(tb, textvariable=vv, values=["RSD", "EUR", "USD", "GBP", "CHF", "BAM", "MKD", "HRK"], width=6, font=self.f(10))
        cbv.pack(side="left", padx=8)

        def promeni_valutu(ev=None):
            self.pod["valuta"] = vv.get().strip().upper()[:4] or T("RSD", "EUR")
            self.sacuvaj_podesavanja()
            self.prikazi("finansije")
        cbv.bind("<<ComboboxSelected>>", promeni_valutu)
        cbv.bind("<Return>", promeni_valutu)

        od, do = period(st["period"])
        zap = self.fin.u_periodu(od, do)
        pr, tr, kat, po_grlu = zbir(zap)

        # ---- sažetak
        kr = tk.Frame(body, bg=BG)
        kr.pack(fill="x", pady=(0, 14))
        kartice = [(T("Prihodi", "Income"), fmt_novac(pr, val), OK), (T("Troškovi", "Costs"), fmt_novac(tr, val), BAD),
                   (T("Razlika (dobit)", "Balance (profit)"), fmt_novac(pr - tr, val), OK if pr >= tr else BAD)]
        litara = self.litara_u_periodu(od, do)
        if litara:
            kartice.append((T("Trošak po litru mleka", "Cost per litre of milk"), fmt_novac(tr / litara, val),
                            T(f"{fmt_novac(litara)} L u periodu", f"{fmt_novac(litara)} L in period")))
        for i, k_ in enumerate(kartice):
            naslov, vr, boja = k_[0], k_[1], k_[2]
            o, c = self.card(kr, 16, 12)
            o.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            kr.columnconfigure(i, weight=1, uniform="f")
            self.lbl(c, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            self.lbl(c, vr, 14, "bold", fg=boja if boja in (OK, BAD) else INK, wraplength=220, justify="left").pack(anchor="w")
            if boja not in (OK, BAD):
                self.lbl(c, boja, 8, fg=INK2).pack(anchor="w")

        self.grafikon_meseci(body, val)

        if not zap:
            self.napomena(body, T("Za izabrani period nema upisa. Dodaj prvi trošak ili prihod gore.",
                                  "No entries for the selected period. Add the first cost or income above."), ok=True)
            return

        # ---- po kategoriji i po grlu
        red = tk.Frame(body, bg=BG)
        red.pack(fill="x", pady=(0, 14))
        red.columnconfigure(0, weight=1, uniform="k")
        red.columnconfigure(1, weight=1, uniform="k")
        o, c = self.card(red, 18, 14)
        o.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.lbl(c, T("Po kategoriji", "By category"), 11, "bold").pack(anchor="w", pady=(0, 6))
        for (vr_, k_), x in sorted(kat.items(), key=lambda t: (t[0][0] != PRIHOD, -t[1])):
            r = tk.Frame(c, bg=SURF)
            r.pack(fill="x", pady=1)
            self.lbl(r, ("+ " if vr_ == PRIHOD else "− ") + k_, 10, fg=OK if vr_ == PRIHOD else INK).pack(side="left")
            ukupno = pr if vr_ == PRIHOD else tr
            self.lbl(r, f"{fmt_novac(x, val)}  ({x / ukupno * 100:.0f}%)" if ukupno else fmt_novac(x, val), 10, "bold").pack(side="right")
        o, c = self.card(red, 18, 14)
        o.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.lbl(c, T("Po grlu", "By animal"), 11, "bold").pack(anchor="w", pady=(0, 6))
        if not po_grlu:
            self.lbl(c, T("Nijedan upis nije vezan za grlo.", "No entry is linked to an animal."), 9, fg=INK2).pack(anchor="w")
        for g, (p_, t_) in sorted(po_grlu.items(), key=lambda t: -(t[1][0] + t[1][1]))[:12]:
            r = tk.Frame(c, bg=SURF)
            r.pack(fill="x", pady=1)
            self.cip(r, g, (lambda g=g: self.karton(g)) if g in self.model.A else None).pack(side="left")
            self.lbl(r, fmt_novac(p_ - t_, val), 10, "bold", fg=OK if p_ >= t_ else BAD).pack(side="right")
            self.lbl(r, T(f"prihod {fmt_novac(p_)} · trošak {fmt_novac(t_)}", f"income {fmt_novac(p_)} · cost {fmt_novac(t_)}"),
                     9, fg=INK2).pack(side="right", padx=10)

        # ---- spisak upisa
        o, c = self.card(body, 18, 14)
        o.pack(fill="both", expand=True)
        self.lbl(c, T(f"Upisi ({len(zap)})", f"Entries ({len(zap)})"), 11, "bold").pack(anchor="w", pady=(0, 6))
        kol = [("datum", T("Datum", "Date"), 95), ("vrsta", T("Vrsta", "Type"), 80), ("kat", T("Kategorija", "Category"), 220),
               ("iznos", T("Iznos", "Amount"), 120, "e"), ("grlo", T("Grlo", "Animal"), 90), ("opis", T("Opis", "Description"), 260)]
        wrap, tv = self.tabela(c, kol, visina=min(14, max(4, len(zap))), tree=False)
        wrap.pack(fill="both", expand=True)
        po_iid = {}
        for i, z in enumerate(zap):
            iid = str(i)
            po_iid[iid] = z
            x = broj(z["iznos"]) or 0
            tv.insert("", "end", iid=iid, values=(z["datum"], T("prihod", "income") if z["vrsta"] == PRIHOD else T("trošak", "cost"),
                                                  z["kategorija"], ("+ " if z["vrsta"] == PRIHOD else "− ") + fmt_novac(x, val),
                                                  z["grlo"] or "–", z["opis"]))

        def obrisi(ev=None):
            sel = [po_iid[i] for i in tv.selection() if i in po_iid]
            if not sel:
                return
            if messagebox.askyesno(T("Brisanje", "Delete"), T(f"Obrisati izabrane upise ({len(sel)})?", f"Delete the selected entries ({len(sel)})?")):
                for z in sel:
                    if z in self.fin.zapisi:
                        self.fin.zapisi.remove(z)
                self.promena(T(f"Obrisano upisa: {len(sel)}", f"Entries deleted: {len(sel)}"))
        tv.bind("<Delete>", obrisi)
        self.lbl(c, T("Za brisanje označi upis i pritisni Delete.", "To delete, select an entry and press Delete."), 8, fg=INK2).pack(anchor="w", pady=(6, 0))

    def litara_u_periodu(self, od, do):
        """Ukupno izmereno mleko u periodu (strana Mlečnost) – za trošak po litru."""
        from jezik import MUZNJA
        from mlecnost import broj as br_mleka
        uk = 0.0
        for z in self.ist.zapisi:
            if z["dogadjaj"] != MUZNJA:
                continue
            d = parsiraj_datum(z["datum"])
            if d and (od is None or d >= od) and (do is None or d <= do):
                uk += br_mleka(z.get("vrednost")) or 0.0
        return uk

    def grafikon_meseci(self, body, val):
        """Prihodi i troškovi za poslednjih 12 meseci (dva stubića po mesecu)."""
        danas = date.today()
        meseci = []
        g, m_ = danas.year, danas.month
        for _ in range(12):
            meseci.append((g, m_))
            g, m_ = (g, m_ - 1) if m_ > 1 else (g - 1, 12)
        meseci.reverse()
        sume = {k: [0.0, 0.0] for k in meseci}
        for z in self.fin.zapisi:
            d = parsiraj_datum(z["datum"])
            if d and (d.year, d.month) in sume:
                sume[(d.year, d.month)][0 if z["vrsta"] == PRIHOD else 1] += broj(z["iznos"]) or 0
        if not any(p or t for p, t in sume.values()):
            return
        o, c = self.card(body, 18, 14)
        o.pack(fill="x", pady=(0, 14))
        nf = tk.Frame(c, bg=SURF)
        nf.pack(fill="x")
        self.lbl(nf, T("Poslednjih 12 meseci", "Last 12 months"), 11, "bold").pack(side="left")
        self.lbl(nf, T("■ troškovi", "■ costs"), 9, "bold", fg=BAD).pack(side="right")
        self.lbl(nf, T("■ prihodi", "■ income"), 9, "bold", fg=OK).pack(side="right", padx=10)
        H = 170
        cv = tk.Canvas(c, height=H, bg=SURF, highlightthickness=0)
        cv.pack(fill="x", pady=(8, 0))

        def crtaj(e=None):
            cv.delete("all")
            W = max(300, cv.winfo_width())
            mx = max(max(p, t) for p, t in sume.values()) or 1
            kor = (W - 16) / len(meseci)
            bw = min(16, kor * 0.3)
            dno = H - 22
            cv.create_line(8, dno, W - 8, dno, fill=LINE)
            for i, k in enumerate(meseci):
                x = 8 + kor * i + kor / 2
                p, t = sume[k]
                for dx, v, boja in ((-bw / 2 - 1, p, OK), (bw / 2 + 1, t, BAD)):
                    h = (dno - 12) * v / mx
                    if v:
                        cv.create_rectangle(x + dx - bw / 2, dno - h, x + dx + bw / 2, dno, fill=boja, outline="")
                cv.create_text(x, dno + 11, text=f"{k[1]:02d}.{str(k[0])[2:]}" if not EN else f"{k[1]:02d}/{str(k[0])[2:]}",
                               fill=INK2, font=self.f(8))
        cv.bind("<Configure>", crtaj)
        crtaj()
