"""Mlečnost: dnevni upis mleka (litri, mlečna mast, proteini) za mlečna grla, laktacija i procena za 305 dana.
Zapisi se čuvaju u istoriji kao događaj „Mužnja“ (vrednost = litara, kolone mast i proteini), pa se
usklađuju sa telefonom kao i svi drugi zapisi, a u običnoj istoriji se ne prikazuju."""
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from osnova import EN
from jezik import DOGADJAJI, MUZNJA, NAMENE_MALI, T, namene_za
from podaci import parsiraj_datum, sada, sort_key
from izgled import BAD, BG, BRAND, INK, INK2, LINE, OK, SURF, SURF2, WARN


# =============================================================== brojevi

def broj(v):
    """'18,5' / '18.5' / ' 18 ' -> 18.5; prazno ili neispravno -> None."""
    t = str(v if v is not None else "").strip().replace(" ", "").replace(",", ".")
    if not t:
        return None
    try:
        x = float(t)
    except ValueError:
        return None
    return x if x == x and abs(x) != float("inf") else None


def fmt_broj(v, dec=1):
    """Broj za prikaz: 18.5 -> '18,5' (srpski) / '18.5' (engleski); celi brojevi bez decimala."""
    x = float(v) if isinstance(v, (int, float)) else broj(v)
    if x is None:
        return str(v or "")
    t = f"{x:,.{dec}f}"
    if dec and "." in t:
        t = t.rstrip("0").rstrip(".")
    return t if EN else t.replace(",", "§").replace(".", ",").replace("§", ".")


def zapis_broja(x):
    """Broj za čuvanje u tablici: tačka kao decimalni znak, bez suvišnih nula."""
    return ("%.2f" % x).rstrip("0").rstrip(".")


def mlecno_grlo(a):
    """Ženka goveda, ovce ili koze mlečne ili kombinovane namene."""
    if not a or a.get("pol") != "z" or a.get("osnivac"):
        return False
    izbori = namene_za(a.get("vrsta"))
    return izbori == list(NAMENE_MALI) and a.get("namena") in (NAMENE_MALI[0], NAMENE_MALI[2])


def muzna_vrsta(a):
    """Ženka vrste koja se muze (goveda, ovce, koze) – bez obzira na namenu."""
    return bool(a) and a.get("pol") == "z" and not a.get("osnivac") and namene_za(a.get("vrsta")) == list(NAMENE_MALI)


# =============================================================== indeks mužnje i telenja

class MlekoIndeks:
    """Brzi pregled mužnje i telenja za celo stado (pravi se jednom po prikazu strane)."""

    def __init__(self, istorija, model):
        self.model = model
        porod = DOGADJAJI[2]
        self.po_grlu = {}          # grlo -> {datum: zapis}
        self.tel = {}              # majka -> {datumi telenja}
        for z in istorija.zapisi:
            d = parsiraj_datum(z.get("datum"))
            if not d:
                continue
            if z["dogadjaj"] == MUZNJA:
                dani = self.po_grlu.setdefault(z["grlo"], {})
                st = dani.get(d)
                if st is None or (z.get("uneto") or "") >= (st.get("uneto") or ""):
                    dani[d] = z               # isti dan upisan dvaput (računar i telefon) -> važi poslednji
            elif z["dogadjaj"] == porod:
                self.tel.setdefault(z["grlo"], set()).add(d)
        for x, (o, m) in model.P.items():   # rođenje potomka je i telenje majke
            if m and model.A.get(x, {}).get("datum"):
                self.tel.setdefault(m, set()).add(model.A[x]["datum"])

    def zapis(self, x, d):
        return self.po_grlu.get(x, {}).get(d)

    def merenja(self, x, od=None, do=None):
        """[(datum, litara, mast, proteini)] sortirano po datumu."""
        rez = []
        for d, z in self.po_grlu.get(x, {}).items():
            if (od and d < od) or (do and d > do):
                continue
            lit = broj(z.get("vrednost"))
            if lit is not None:
                rez.append((d, lit, broj(z.get("mast")), broj(z.get("proteini"))))
        return sorted(rez)

    def telenja(self, x):
        return sorted(self.tel.get(x, ()))

    def laktacija(self, x, d):
        """(redni broj laktacije, početak, dan laktacije) na dan d; bez poznatog telenja (0, None, None)."""
        pre = [t for t in self.telenja(x) if t <= d]
        if not pre:
            return 0, None, None
        return len(pre), pre[-1], (d - pre[-1]).days + 1

    def stat(self, x, d=None):
        """Sažetak tekuće laktacije na dan d (podrazumevano danas)."""
        d = d or date.today()
        br, poc, dan = self.laktacija(x, d)
        od = poc if poc else d - timedelta(days=304)
        mer = self.merenja(x, od, d)
        rez = dict(br=br, pocetak=poc, dan=dan, merenja=mer, poslednje=mer[-1] if mer else None,
                   ukupno=sum(m[1] for m in mer), prosek7=None, procena305=None, mast=None, proteini=None)
        if not mer:
            return rez
        sedam = [m[1] for m in mer if (d - m[0]).days < 7]
        rez["prosek7"] = sum(sedam) / len(sedam) if sedam else None
        ma = [m[2] for m in mer if m[2]]
        pr = [m[3] for m in mer if m[3]]
        rez["mast"] = sum(ma) / len(ma) if ma else None
        rez["proteini"] = sum(pr) / len(pr) if pr else None
        if poc:
            rez["procena305"] = procena_305(poc, mer)
        return rez

    def stado_po_danu(self, grla, dana=30, do=None):
        """[(datum, ukupno litara, broj grla)] za poslednjih `dana` dana."""
        do = do or date.today()
        rez = []
        for i in range(dana - 1, -1, -1):
            d = do - timedelta(days=i)
            vr = [broj(self.zapis(x, d).get("vrednost")) for x in grla if self.zapis(x, d)]
            vr = [v for v in vr if v is not None]
            rez.append((d, sum(vr), len(vr)))
        return rez


def procena_305(pocetak, merenja):
    """Procena mleka za 305 dana laktacije iz merenja [(datum, litara, …)]:
    između merenja linearno (trapez), pre prvog merenja kao prvo, posle poslednjeg kao prosek poslednjih 7 merenja."""
    tacke = [((m[0] - pocetak).days + 1, m[1]) for m in merenja if 1 <= (m[0] - pocetak).days + 1 <= 305]
    if not tacke:
        return None
    tacke.sort()
    ukupno = tacke[0][1] * tacke[0][0]                     # dani 1..prvo merenje
    for (t1, v1), (t2, v2) in zip(tacke, tacke[1:]):
        ukupno += (v1 + v2) / 2 * (t2 - t1)
    if tacke[-1][0] < 305:
        poslednjih = [v for _, v in tacke[-7:]]
        ukupno += sum(poslednjih) / len(poslednjih) * (305 - tacke[-1][0])
    return ukupno


def upisi_muznju(istorija, ix, x, d, litara, mast=None, proteini=None):
    """Upis (ili izmena) mužnje grla x za dan d. litara=None briše upis za taj dan. Vraća 'novo'/'izmena'/'brisanje'/None."""
    dstr = d.strftime("%d/%m/%Y" if EN else "%d.%m.%Y")
    stari = [z for z in istorija.zapisi if z["grlo"] == x and z["dogadjaj"] == MUZNJA and parsiraj_datum(z.get("datum")) == d]
    if litara is None:
        if not stari:
            return None
        for z in stari:
            istorija.zapisi.remove(z)
        ix.po_grlu.get(x, {}).pop(d, None)
        return "brisanje"
    vr = dict(vrednost=zapis_broja(litara), mast=zapis_broja(mast) if mast else "", proteini=zapis_broja(proteini) if proteini else "")
    if stari:
        z = max(stari, key=lambda s: s.get("uneto") or "")
        for s in stari:                     # duplikat istog dana se uklanja
            if s is not z:
                istorija.zapisi.remove(s)
        if all((z.get(k) or "") == v for k, v in vr.items()):
            return None
        z.update(vr)
        ix.po_grlu.setdefault(x, {})[d] = z
        return "izmena"
    z = dict(grlo=x, datum=dstr, dogadjaj=MUZNJA, opis="", partner="", automatski="", uneto=sada(), ishod="", ter="",
             karenca_meso="", karenca_mleko="", upisao="", **vr)
    istorija.zapisi.append(z)
    ix.po_grlu.setdefault(x, {})[d] = z
    return "novo"


# =============================================================== prozor

class MlecnostDeo:
    """Strana „Mlečnost“ (dnevni upis za celo stado) i odeljak na kartonu grla."""

    def s_mlecnost(self):
        m = self.model
        st = self.ui.setdefault("mleko", {"datum": "", "sve": False})
        d = parsiraj_datum(st.get("datum")) or date.today()
        body = self.strana_okvir(scroll=True)
        self.zaglavlje(body, T("Mlečnost", "Milk recording"),
                       T("Upiši koliko je mleka dalo svako grlo. Mast i proteini se upisuju samo kad ih imaš (npr. posle kontrole). Program računa laktaciju i procenu za 305 dana.",
                         "Enter how much milk each animal gave. Fat and protein only when you have them (e.g. after a test). The program works out the lactation and a 305-day estimate."))
        ix = MlekoIndeks(self.ist, m)
        sva = [a for a in m.grla(True) if muzna_vrsta(a)]
        if st.get("sve"):
            grla = sva
        else:
            grla = [a for a in sva if mlecno_grlo(a) and (ix.telenja(a["id"]) or ix.po_grlu.get(a["id"]))] + \
                   [a for a in sva if not mlecno_grlo(a) and ix.po_grlu.get(a["id"])]
        grla.sort(key=lambda a: sort_key(a["id"]))

        # ---- traka: datum, sve ženke
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        self.lbl(tb, T("Datum:", "Date:"), 10, "bold", fg=INK2).pack(side="left")
        dv = tk.StringVar(value=d.strftime("%d/%m/%Y" if EN else "%d.%m.%Y"))

        def na_dan(nd):
            st["datum"] = nd.strftime("%d/%m/%Y" if EN else "%d.%m.%Y") if nd else ""
            self.prikazi("mlecnost")
        b1 = self.btn(tb, "◀", lambda: na_dan(d - timedelta(days=1)))
        b1.configure(width=3)
        b1.pack(side="left", padx=(8, 0))
        de = ttk.Entry(tb, textvariable=dv, width=12, font=self.f(10), justify="center")
        de.pack(side="left", padx=4)
        de.bind("<Return>", lambda e: na_dan(parsiraj_datum(dv.get()) or d))
        b2 = self.btn(tb, "▶", lambda: na_dan(d + timedelta(days=1)))
        b2.configure(width=3)
        b2.pack(side="left")
        if d != date.today():
            ld = self.lbl(tb, T("danas", "today"), 9, "bold", fg=BRAND, cursor="hand2")
            ld.pack(side="left", padx=10)
            ld.bind("<Button-1>", lambda e: na_dan(None))
        sv = tk.BooleanVar(value=bool(st.get("sve")))
        ttk.Checkbutton(tb, text=T("Prikaži sve ženke", "Show all females"),
                        variable=sv, command=lambda: (st.update(sve=sv.get()), self.prikazi("mlecnost"))).pack(side="left", padx=16)
        # mast i proteini nisu za svaki dan – polja se prikazuju samo kad se uključe (ili kad za taj dan već postoje)
        mp = tk.BooleanVar(value=bool(self.pod.get("mleko_mast")))

        def prebaci_mast():
            self.pod["mleko_mast"] = mp.get()
            try:
                self.sacuvaj_podesavanja()
            except Exception:
                pass
            self.prikazi("mlecnost")
        ttk.Checkbutton(tb, text=T("Upisujem i mast i proteine", "Also enter fat and protein"), variable=mp,
                        command=prebaci_mast).pack(side="left")

        if not grla:
            self.napomena(body, T("Nema muznih grla. Na listi su ženke goveda, ovaca i koza mlečne ili kombinovane namene koje su se telile "
                                  "(ili već imaju upisanu mužnju). Namenu upiši u „Izmeni podatke“, ili uključi „Prikaži sve ženke“.",
                                  "No animals to milk. The list shows female cattle, sheep and goats of dairy or dual-purpose breeds that have "
                                  "given birth (or already have milk records). Set the purpose in “Edit details”, or tick “Show all females”."))
            return

        # ---- sažetak dana i grafikon stada
        ids = [a["id"] for a in grla]
        dan = [(x, ix.zapis(x, d)) for x in ids]
        dan = [(x, z) for x, z in dan if z and broj(z.get("vrednost")) is not None]
        ukupno = sum(broj(z["vrednost"]) for _, z in dan)
        ma = [broj(z.get("mast")) for _, z in dan if broj(z.get("mast"))]
        pr = [broj(z.get("proteini")) for _, z in dan if broj(z.get("proteini"))]
        kr = tk.Frame(body, bg=BG)
        kr.pack(fill="x", pady=(0, 14))
        for i, (naslov, vr, pod) in enumerate((
                (T("Pomuženo grla", "Animals milked"), f"{len(dan)} / {len(grla)}", T("upisano za ovaj dan", "recorded for this day")),
                (T("Ukupno mleka", "Total milk"), f"{fmt_broj(ukupno)} L", d.strftime("%d/%m/%Y" if EN else "%d.%m.%Y")),
                (T("Prosek po grlu", "Average per animal"), f"{fmt_broj(ukupno / len(dan))} L" if dan else "–", T("od pomuženih", "of milked")),
                (T("Mast / proteini", "Fat / protein"), (f"{fmt_broj(sum(ma) / len(ma), 2)}% / " if ma else "– / ") +
                 (f"{fmt_broj(sum(pr) / len(pr), 2)}%" if pr else "–"), T("prosek dana", "day average")))):
            o, c = self.card(kr, 16, 12)
            o.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            kr.columnconfigure(i, weight=1, uniform="m")
            self.lbl(c, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            self.lbl(c, vr, 18, "bold").pack(anchor="w")
            self.lbl(c, pod, 8, fg=INK2).pack(anchor="w")
        niz = ix.stado_po_danu(ids, 30, d)
        if any(v for _, v, _ in niz):
            from stampa import _crtaj_stubice
            _crtaj_stubice(self, body, T("Mleko stada – poslednjih 30 dana (L)", "Herd milk – last 30 days (L)"),
                           [(dd.strftime("%d.") if not EN else dd.strftime("%d"), v) for dd, v, _ in niz],
                           sirina=900, visina=170, fmt=lambda v: fmt_broj(v, 0) if v else "")

        # ---- tabela za upis
        sa_mast = mp.get() or any((ix.zapis(x, d) or {}).get(k) for x in ids for k in ("mast", "proteini"))
        o, c = self.card(body, 18, 14)
        o.pack(fill="x", pady=(0, 14))
        zag = [T("Grlo", "Animal"), T("Laktacija", "Lactation"), T("Dan lakt.", "Day"), T("Prethodni dan", "Previous day"),
               T("Prosek 7 d.", "7-day avg."), T("Litara *", "Litres *")] + ([T("Mast %", "Fat %"), T("Proteini %", "Protein %")] if sa_mast else [])
        for j, z_ in enumerate(zag):
            self.lbl(c, z_, 9, "bold", fg=INK2).grid(row=0, column=j, sticky="w", padx=(0, 14), pady=(0, 6))
        unosi = []
        juce = d - timedelta(days=1)
        for i, a in enumerate(grla, 1):
            x = a["id"]
            s = ix.stat(x, d)
            zj = ix.zapis(x, juce)
            zd = ix.zapis(x, d) or {}
            red_bg = SURF if i % 2 else "#FAFBF9"
            self.cip(c, x, lambda x=x: self.karton(x), bg=red_bg).grid(row=i, column=0, sticky="w", padx=(0, 14), pady=2)
            self.lbl(c, f"{s['br']}." if s["br"] else "–", 10).grid(row=i, column=1, sticky="w", padx=(0, 14))
            self.lbl(c, str(s["dan"]) if s["dan"] else "–", 10, fg=WARN if (s["dan"] or 0) > 305 else INK).grid(row=i, column=2, sticky="w", padx=(0, 14))
            self.lbl(c, f"{fmt_broj(zj['vrednost'])} L" if zj and zj.get("vrednost") else "–", 10, fg=INK2).grid(row=i, column=3, sticky="w", padx=(0, 14))
            self.lbl(c, f"{fmt_broj(s['prosek7'])} L" if s["prosek7"] else "–", 10, fg=INK2).grid(row=i, column=4, sticky="w", padx=(0, 14))
            vv = [tk.StringVar(value=fmt_broj(zd.get(k)) if zd.get(k) else "") for k in ("vrednost", "mast", "proteini")]
            ee = []
            for j, var in enumerate(vv if sa_mast else vv[:1]):     # skrivena mast/proteini ostaju kakvi su bili
                e = ttk.Entry(c, textvariable=var, width=8 if j == 0 else 6, font=self.f(10), justify="right")
                e.grid(row=i, column=5 + j, sticky="w", padx=(0, 14), pady=2)
                ee.append(e)
            unosi.append((x, vv, ee))
        for k, (_, _, ee) in enumerate(unosi):          # Enter -> litri sledećeg grla
            for e in ee:
                e.bind("<Return>", lambda ev, k=k: unosi[k + 1][2][0].focus_set() if k + 1 < len(unosi) else sacuvaj())
        err = self.lbl(body, "", 10, "bold", fg=BAD, wraplength=900, justify="left")
        err.pack(anchor="w")

        def sacuvaj():
            greske, plan = [], []
            for x, vv, ee in unosi:
                t = [v.get().strip() for v in vv]
                if not t[0]:                     # bez litara = nije muženo tog dana
                    plan.append((x, None, None, None))
                    continue
                lit, mas, pro = (broj(v) for v in t)
                if lit is None or not 0 < lit < 150:
                    greske.append(T(f"{x}: litri nisu ispravni", f"{x}: litres are not valid"))
                    continue
                if t[1] and (mas is None or not 0 < mas < 20):
                    greske.append(T(f"{x}: mast nije ispravna (npr. 3,8)", f"{x}: fat is not valid (e.g. 3.8)"))
                    continue
                if t[2] and (pro is None or not 0 < pro < 15):
                    greske.append(T(f"{x}: proteini nisu ispravni (npr. 3,3)", f"{x}: protein is not valid (e.g. 3.3)"))
                    continue
                plan.append((x, lit, mas, pro))
            if greske:
                err.config(text="  ·  ".join(greske[:6]) + (" …" if len(greske) > 6 else ""))
                return
            promene = [upisi_muznju(self.ist, ix, x, d, lit, mas, pro) for x, lit, mas, pro in plan]
            n = sum(1 for _, lit, _, _ in plan if lit)
            nb = promene.count("brisanje")
            uk = sum(lit for _, lit, _, _ in plan if lit)
            self.promena(T(f"Mužnja sačuvana: {n} grla, ukupno {fmt_broj(uk)} L", f"Milking saved: {n} animals, total {fmt_broj(uk)} L")
                         + (T(f" (obrisano {nb})", f" ({nb} removed)") if nb else ""))

        fb = tk.Frame(body, bg=BG)
        fb.pack(fill="x", pady=(8, 0))
        self.btn(fb, T("Sačuvaj mužnju", "Save milking"), sacuvaj, "Primary").pack(side="left")
        self.lbl(fb, T("Prazno polje = nije muženo tog dana (postojeći upis se briše). Enter prelazi na sledeće grlo.",
                       "Empty field = not milked that day (an existing entry is removed). Enter moves to the next animal."),
                 9, fg=INK2).pack(side="left", padx=14)
        if unosi:
            unosi[0][2][0].focus_set()

    # ---------------------------------------------------------------- karton
    def mlecnost_na_kartonu(self, parent, x):
        """Kratak pregled laktacije na kartonu grla (samo za mlečne ženke ili grla sa upisanom mužnjom)."""
        a = self.model.A.get(x)
        ix = MlekoIndeks(self.ist, self.model)
        if not a or not (mlecno_grlo(a) or ix.po_grlu.get(x)):
            return
        s = ix.stat(x)
        self.lbl(parent, T("Mlečnost", "Milk"), 10, "bold").pack(anchor="w", pady=(18, 6))
        fr = tk.Frame(parent, bg=SURF)
        fr.pack(anchor="w", fill="x")
        redovi = [(T("Laktacija", "Lactation"), (f"{s['br']}." + (T(f"  ·  dan {s['dan']}", f"  ·  day {s['dan']}") if s["dan"] else ""))
                   if s["br"] else T("telenje nije upisano", "no calving recorded"))]
        if s["poslednje"]:
            p = s["poslednje"]
            redovi.append((T("Poslednja mužnja", "Last milking"), f"{fmt_broj(p[1])} L  ({p[0].strftime('%d/%m' if EN else '%d.%m.')})"))
        if s["prosek7"]:
            redovi.append((T("Prosek 7 dana", "7-day average"), f"{fmt_broj(s['prosek7'])} L"))
        if s["merenja"]:
            redovi.append((T("Izmereno u laktaciji", "Recorded this lactation"), f"{fmt_broj(s['ukupno'], 0)} L"))
        if s["procena305"]:
            redovi.append((T("Procena za 305 dana", "305-day estimate"), f"≈ {fmt_broj(s['procena305'], 0)} L"))
        if s["mast"] or s["proteini"]:
            redovi.append((T("Mast / proteini", "Fat / protein"), (f"{fmt_broj(s['mast'], 2)}%" if s["mast"] else "–") + " / " +
                           (f"{fmt_broj(s['proteini'], 2)}%" if s["proteini"] else "–")))
        for i, (k, v) in enumerate(redovi):
            self.lbl(fr, k, 10, fg=INK2).grid(row=i, column=0, sticky="w", pady=2)
            self.lbl(fr, v, 10, "bold").grid(row=i, column=1, sticky="w", padx=16, pady=2)
        kriva = [(m[0], m[1]) for m in s["merenja"]][-60:]
        if len(kriva) >= 2:                  # mala kriva laktacije (poslednjih do 60 merenja)
            W, H = 420, 70
            cv = tk.Canvas(parent, width=W, height=H, bg=SURF, highlightthickness=0)
            cv.pack(anchor="w", pady=(6, 0))
            mx = max(v for _, v in kriva) or 1
            mn = min(v for _, v in kriva) * 0.8
            mx = mx if mx > mn else mn + 1
            d0, d1 = kriva[0][0], kriva[-1][0]
            raspon = max(1, (d1 - d0).days)
            tacke = []
            for dd, v in kriva:
                tacke += [4 + (W - 8) * (dd - d0).days / raspon, H - 6 - (H - 14) * (v - mn) / (mx - mn)]
            cv.create_line(4, H - 6, W - 4, H - 6, fill=LINE)
            cv.create_line(*tacke, fill=BRAND, width=2, smooth=True)
        lk = self.lbl(parent, T("Upiši mužnju  ›", "Record milking  ›"), 9, "bold", fg=BRAND, cursor="hand2")
        lk.pack(anchor="w", pady=(6, 0))
        lk.bind("<Button-1>", lambda e: self.prikazi("mlecnost"))
