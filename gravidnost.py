"""Gravidnost i porođaj: očekivani porođaj, leglo, upis podmlatka."""
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from osnova import EN
from jezik import AUTO, GRAVIDNOST_PROFILI, PARENJE, STADO_PODMLADAK
from podaci import nazivi, norm, norm_rasa, parsiraj_datum, pct, rasa_potomka, sada, slobodna_oznaka, vrsta_norm
from izgled import BAD, BRAND, INK, INK2, OK, OK_BG, SURF, SURF2


class GravidnostDeo:
    """Gravidnost i porođaj: očekivani porođaj, leglo, upis podmlatka."""


    # ---------- parenje -> porođaj -> podmladak
    def roditelji_parenja(self, z):
        """(majka, otac) iz zapisa o parenju, bez obzira kod koga je parenje upisano."""
        m = self.model
        g = z["grlo"]
        p = (m.nadji(z.get("partner")) or z.get("partner") or "").strip() or None
        if g in m.A and m.A[g]["pol"] == "m":
            return p, g
        return g, p


    def profil_gravidnosti(self, vrsta, rasa=""):
        """(ključ, naziv, najmanje, najviše, prosek) dana gravidnosti – po rasi majke, pa po vrsti."""
        v = vrsta_norm(vrsta or "")
        r = norm_rasa(rasa or "")
        kljuc = None
        for k, (naziv, vr, prepoznaj, *_d) in GRAVIDNOST_PROFILI.items():
            if prepoznaj and vr == v and any(p in r for p in prepoznaj):
                kljuc = k
                break
        if kljuc is None:
            kljuc = next((k for k, (naziv, vr, prepoznaj, *_d) in GRAVIDNOST_PROFILI.items()
                          if vr == v and not prepoznaj), None)
        if kljuc is None:
            return None, v, None, None, None
        naziv, _, _, mn, mx, pr = GRAVIDNOST_PROFILI[kljuc]
        pod = self.pod.get("gravidnost2", {}).get(kljuc)
        if pod:
            mn, mx, pr = (int(x) for x in pod)
        return kljuc, naziv, mn, mx, pr


    def gravidnost(self, vrsta, rasa=""):
        """(prosek, koliko dana ranije je dozvoljen upis) – zbog starijih delova programa."""
        _, _, mn, mx, pr = self.profil_gravidnosti(vrsta, rasa)
        return (pr, pr - mn) if pr else (None, 0)


    def vrsta_parenja(self, z):
        majka, _ = self.roditelji_parenja(z)
        g = majka if majka in self.model.A else z["grlo"]
        return self.model.A[g]["vrsta"] if g in self.model.A else ""


    def rasa_parenja(self, z):
        majka, _ = self.roditelji_parenja(z)
        return self.model.A[majka]["rasa"] if majka in self.model.A else ""


    def granice_porodjaja(self, z):
        """(najranije, očekivano, najkasnije) datum porođaja za parenje, ili (None, None, None)."""
        d = parsiraj_datum(z["datum"])
        _, _, mn, mx, pr = self.profil_gravidnosti(self.vrsta_parenja(z), self.rasa_parenja(z))
        if not (d and pr):
            return None, None, None
        return d + timedelta(days=mn), d + timedelta(days=pr), d + timedelta(days=mx)


    def ocekivani_porodjaj(self, z):
        return self.granice_porodjaja(z)[1]


    def upis_moguc_od(self, z):
        """Najraniji normalan dan porođaja – od tada je upis mladih otvoren."""
        return self.granice_porodjaja(z)[0]


    def najkasniji_porodjaj(self, z):
        return self.granice_porodjaja(z)[2]


    def podesavanje_gravidnosti(self, parent=None):
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Gestation length" if EN else "Nosivost (trajanje gravidnosti)"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Gestation length" if EN else "Nosivost – trajanje gravidnosti"), 16, "bold").grid(row=0, column=0, columnspan=5, sticky="w")
        self.lbl(b, ("Entering young opens from the minimum number of days. After the maximum number of days the program reports that the "
                    "due date has passed. The average is used for the expected date." if EN else "Upis mladih se otvara od najmanjeg broja dana. Posle najvećeg broja dana program javlja da je "
                    "termin prošao. Prosek se koristi za očekivani datum."), 9, fg=INK2, wraplength=520,
                 justify="left").grid(row=1, column=0, columnspan=5, sticky="w", pady=(4, 12))
        for c, t in enumerate((("Species / breed" if EN else "Vrsta / rasa"), ("Minimum" if EN else "Najmanje"), ("Maximum" if EN else "Najviše"), ("Average" if EN else "Prosek"), "")):
            self.lbl(b, t, 9, "bold", fg=INK2).grid(row=2, column=c, sticky="w", padx=(0, 14), pady=(0, 4))
        polja = {}
        for i, (k, (naziv, vr, prep, mn0, mx0, pr0)) in enumerate(GRAVIDNOST_PROFILI.items(), 3):
            _, _, mn, mx, pr = self.profil_gravidnosti(vr, prep[0] if prep else "")
            vs = [tk.StringVar(value=str(x)) for x in (mn, mx, pr)]
            self.lbl(b, naziv, 10, "bold").grid(row=i, column=0, sticky="w", padx=(0, 14), pady=3)
            for c, v in enumerate(vs, 1):
                ttk.Entry(b, textvariable=v, width=7, font=self.f(10)).grid(row=i, column=c, sticky="w", padx=(0, 14))
            self.lbl(b, (f"default {mn0}–{mx0}, ~{pr0}" if EN else f"podraz. {mn0}–{mx0}, ~{pr0}"), 8, fg="#8A968D").grid(row=i, column=4, sticky="w")
            polja[k] = vs
        self.lbl(b, ("Gestation is always determined by the breed of the DAM: Romanov ewe × any ram = 138–143 days; "
                    "other ewe × Romanov ram = as a common sheep." if EN else "Nosivost se uvek određuje po rasi MAJKE: romanovska ovca × bilo koji ovan = 138–143 dana; "
                    "druga ovca × romanovski ovan = kao obična ovca."), 8, fg="#8A968D").grid(
            row=19, column=0, columnspan=5, sticky="w", pady=(6, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=520, justify="left")
        err.grid(row=20, column=0, columnspan=5, sticky="w", pady=(8, 0))

        def sacuvaj(ev=None):
            novo = {}
            for k, vs in polja.items():
                naziv = GRAVIDNOST_PROFILI[k][0]
                try:
                    mn, mx, pr = (int(v.get()) for v in vs)
                except ValueError:
                    err.config(text=(f"{naziv}: enter whole numbers of days." if EN else f"{naziv}: upiši cele brojeve dana."))
                    return
                if not (30 <= mn <= pr <= mx <= 500):
                    err.config(text=(f"{naziv}: must be minimum ≤ average ≤ maximum (30–500 days)." if EN else f"{naziv}: mora biti najmanje ≤ prosek ≤ najviše (30–500 dana)."))
                    return
                novo[k] = [mn, mx, pr]
            self.pod["gravidnost2"] = novo
            self.pod.pop("gravidnost", None)
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            self.toast(("Gestation length saved." if EN else "Nosivost je sačuvana."))
            self.osvezi_istoriju()

        def vrati():
            for k, vs in polja.items():
                for v, x in zip(vs, GRAVIDNOST_PROFILI[k][3:]):
                    v.set(str(x))

        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=21, column=0, columnspan=5, sticky="ew", pady=(16, 0))
        self.btn(fb, ("Defaults" if EN else "Podrazumevano"), vrati).pack(side="left")
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, parent)


    def ceka_porodjaj(self, z):
        return z["dogadjaj"] == PARENJE and not z.get("ishod") and not z["automatski"]


    def opis_ishoda(self, z):
        if z["dogadjaj"] != PARENJE or z["automatski"]:
            return ""
        ish = z.get("ishod", "")
        if ish.startswith("rodjeno:"):
            return ("☑ born: " if EN else "☑ rođeno: ") + ish[8:].replace(",", ", ")
        lg = self.leglo(z)
        if lg:
            uk, dd, vec = lg
            return (f"🏷 {uk} born {dd} – waiting for ear tag" if EN else f"🏷 {uk} rođeno {dd} – čeka minđušu") + (f" ({len(vec)}/{uk})" if vec else "")
        if ish == "uklonjeno":
            return ("✕ young not entered in the list" if EN else "✕ mladi nisu upisani u listu")
        if ish == "neuspelo":
            return ("✕ failed" if EN else "✕ nije uspelo")
        if ish == "ponovljeno":
            return ("– repeated mating" if EN else "– ponovljeno parenje")
        oc = self.ocekivani_porodjaj(z)
        od = self.upis_moguc_od(z)
        if od and date.today() < od:
            return (f"⏳ pregnant until {oc.strftime('%d/%m/%Y')}" if EN else f"⏳ gravidna do {oc.strftime('%d.%m.%Y')}")
        return "☐ " + ((f"entry open (due {oc.strftime('%d/%m/%Y')})" if EN else f"upis otvoren (termin {oc.strftime('%d.%m.%Y')})") if oc else ("waiting for young" if EN else "čeka mlade"))


    def cekaju_porodjaj(self, x=None):
        """Parenja bez upisanih mladih – za svaku ženku samo poslednje parenje."""
        posl = {}
        for z in self.ist.zapisi:
            if z["dogadjaj"] != PARENJE or z["automatski"]:
                continue
            majka, _ = self.roditelji_parenja(z)
            if x is not None and x not in (z["grlo"], majka, self.model.nadji(z.get("partner"))):
                continue
            kljuc = majka or z["grlo"]
            d = parsiraj_datum(z["datum"]) or date.min
            if kljuc not in posl or d >= (parsiraj_datum(posl[kljuc]["datum"]) or date.min):
                posl[kljuc] = z
        lista = [z for z in posl.values() if self.ceka_porodjaj(z)]
        return sorted(lista, key=lambda z: self.ocekivani_porodjaj(z) or date.max)


    def zatvori_stara_parenja(self, nz):
        """Novo parenje iste ženke: ranija parenja bez mladih označi kao ponovljena."""
        if nz.get("dogadjaj") != PARENJE:
            return
        majka, _ = self.roditelji_parenja(nz)
        d = parsiraj_datum(nz["datum"]) or date.min
        for z in self.ist.zapisi:
            if z is not nz and self.ceka_porodjaj(z) and self.roditelji_parenja(z)[0] == majka \
                    and (parsiraj_datum(z["datum"]) or date.min) <= d:
                z["ishod"] = "ponovljeno"


    def oznaci_neuspelo(self, z):
        if messagebox.askyesno(("Mating failed" if EN else "Parenje nije uspelo"),
                               (f"Mark the mating of {z['datum']} ({z['grlo']}) as failed?\n"
                               "It will no longer be shown among expected births." if EN else f"Označiti parenje od {z['datum']} ({z['grlo']}) kao neuspelo?\n"
                               "Neće se više prikazivati među očekivanim porođajima.")):
            z["ishod"] = "neuspelo"
            self.promena(("Mating marked as failed." if EN else "Parenje označeno kao neuspelo."))
            self.osvezi_istoriju()


    def osvezi_istoriju(self):
        self.osvezi_nav_brojac()
        if getattr(self, "ist_win", None) and self.ist_win.winfo_exists() and getattr(self.ist_win, "grlo", None):
            self.istorija_prozor(self.ist_win.grlo)
        if self.strana == "istorija":
            self.prikazi("istorija")


    # ---------- leglo: rođenje se beleži odmah (broj mladih), a u listu grla se upisuju kasnije (minđuša)
    @staticmethod
    def leglo(z):
        """'leglo:N:dd.mm.gggg:id1,id2' -> (N, datum, [upisani]) ili None."""
        ish = z.get("ishod", "") or ""
        if not ish.startswith("leglo:"):
            return None
        delovi = (ish.split(":", 3) + ["", "", "", ""])[:4]
        try:
            n = int(delovi[1])
        except ValueError:
            n = 0
        return n, delovi[2], [i for i in delovi[3].split(",") if i]


    def cekaju_mindjusu(self, x=None):
        rez = []
        for z in self.ist.zapisi:
            if z["dogadjaj"] != PARENJE or not self.leglo(z):
                continue
            majka, otac = self.roditelji_parenja(z)
            if x is not None and x not in (z["grlo"], majka, otac):
                continue
            rez.append(z)
        return sorted(rez, key=lambda z: parsiraj_datum(self.leglo(z)[1]) or date.min)


    def upis_podmlatka(self, z, parent=None, prevremeni=False):
        """Štikliran 'Dobijeni mladi': ako mladi već čekaju minđušu – upis u listu, inače beleženje rođenja."""
        m = self.model
        if z.get("ishod", "").startswith("rodjeno:"):
            ids = [i for i in z["ishod"][8:].split(",") if i]
            messagebox.showinfo(("Young stock" if EN else "Podmladak"), ("Young have already been entered for this mating: " if EN else "Za ovo parenje mladi su već upisani: ") + ", ".join(ids),
                                parent=parent or self.root)
            if ids and ids[0] in m.A:
                self.karton(ids[0])
            return
        if self.leglo(z):
            self.upis_u_listu(z, parent)
            return
        od = self.upis_moguc_od(z)
        oc = self.ocekivani_porodjaj(z)
        if od and date.today() < od and not prevremeni:
            dana_ost = (od - date.today()).days
            if not messagebox.askyesno(
                    ("Pregnancy still in progress" if EN else "Gravidnost još traje"),
                    (f"Mating: {z['datum']}\nExpected birth: {oc.strftime('%d/%m/%Y')}\n"
                    f"Young can be entered from {od.strftime('%d/%m/%Y')} (in {dana_ost} days).\n\n"
                    "Was this a PREMATURE birth and do you still want to enter the young?" if EN else f"Parenje: {z['datum']}\nOčekivani porođaj: {oc.strftime('%d.%m.%Y')}\n"
                    f"Upis mladih je moguć od {od.strftime('%d.%m.%Y')} (za {dana_ost} dana).\n\n"
                    "Da li je bio PREVREMENI porođaj i želiš ipak da upišeš mlade?"),
                    icon="warning", parent=parent or self.root):
                return
            prevremeni = True
        self.rodjenje_dijalog(z, parent, prevremeni)


    def podaci_legla(self, z):
        m = self.model
        majka, otac = self.roditelji_parenja(z)
        ref = majka if majka in m.A else z["grlo"]
        vrsta = m.A.get(ref, {}).get("vrsta") or ("cattle" if EN else "goveda")
        rm = (m.A[majka]["rasa"] if majka in m.A else "") or ""
        ro = (m.A[otac]["rasa"] if otac in m.A else "") or ""
        rasa = rasa_potomka(ro, rm)
        return majka, otac, vrsta, rasa, nazivi(vrsta)


    def zaglavlje_legla(self, b, z, majka, otac):
        m = self.model
        top = tk.Frame(b, bg=SURF)
        top.pack(anchor="w", pady=(12, 2))
        for naslov, g, nep in ((("Dam" if EN else "Majka"), majka, ("unknown" if EN else "nepoznata")), (("Sire" if EN else "Otac"), otac, ("unknown" if EN else "nepoznat"))):
            self.lbl(top, naslov, 9, "bold", fg=INK2).pack(side="left")
            if g:
                self.cip(top, g, siv=g not in m.A or m.A[g]["osnivac"]).pack(side="left", padx=(6, 16))
            else:
                self.lbl(top, nep, 10, fg=INK2).pack(side="left", padx=(6, 16))


    def rodjenje_dijalog(self, z, parent=None, prevremeni=False):
        """Korak 1: beleži se samo da su mladi rođeni, datum i broj – bez pola i oznaka."""
        m = self.model
        majka, otac, vrsta, rasa, n = self.podaci_legla(z)
        od, oc = self.upis_moguc_od(z), self.ocekivani_porodjaj(z)
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Birth of young" if EN else "Rođenje mladih"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, (f"Young born ({n[3]})" if EN else f"Rođeni mladi ({n[3]})"), 16, "bold").pack(anchor="w")
        self.zaglavlje_legla(b, z, majka, otac)
        self.lbl(b, (f"Mating {z['datum']}" if EN else f"Parenje {z['datum']}") + ((f"   ·   due {oc.strftime('%d/%m/%Y')}" if EN else f"   ·   termin {oc.strftime('%d.%m.%Y')}") if oc else ""),
                 9, fg=INK2).pack(anchor="w", pady=(4, 0))

        g = tk.Frame(b, bg=SURF2)
        g.pack(fill="x", pady=(14, 4))
        gi = tk.Frame(g, bg=SURF2)
        gi.pack(fill="x", padx=14, pady=10)
        dv = tk.StringVar(value=date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        bv = tk.StringVar(value="1")
        mv = tk.StringVar(value="0")
        for i, (nasl, var, w) in enumerate(((("Date of birth" if EN else "Datum rođenja"), dv, 14), ((f"Number alive ({n[3]})" if EN else f"Broj živih ({n[3]})"), bv, 6),
                                            (("Stillborn" if EN else "Mrtvorođenih"), mv, 6))):
            f = tk.Frame(gi, bg=SURF2)
            f.grid(row=0, column=i, sticky="w", padx=(0, 22))
            self.lbl(f, nasl, 9, "bold", fg=INK2, bg=SURF2).pack(anchor="w")
            (ttk.Entry(f, textvariable=var, width=w, font=self.f(11)) if i == 0 else
             ttk.Spinbox(f, from_=0 if i == 2 else 1, to=30, textvariable=var, width=w,
                         font=self.f(11))).pack(anchor="w", pady=(3, 0))
        prev_v = tk.BooleanVar(value=prevremeni)
        if od:
            ttk.Checkbutton(b, text=(f"Premature birth (before {od.strftime('%d/%m/%Y')})" if EN else f"Prevremeni porođaj (pre {od.strftime('%d.%m.%Y')})"), variable=prev_v,
                            style="Card.TCheckbutton").pack(anchor="w", pady=(6, 0))
        info = tk.Frame(b, bg=OK_BG)
        info.pack(fill="x", pady=(12, 0))
        self.lbl(info, ("You don't need to know the sex, tag or ear tag now. The young will wait on the list "
                       "\"Waiting for ear tag\", and you move them to the animal list when they get their ear tags." if EN else "Pol, oznaku i ušnu markicu ne moraš sada da znaš. Mladi će čekati na spisku "
                       "„Čekaju minđušu“, a u listu grla ih prebacuješ kad dobiju minđušu."),
                 9, fg=OK, bg=OK_BG, wraplength=480, justify="left").pack(anchor="w", padx=12, pady=8)
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=500, justify="left")
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(odmah=False):
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date of birth is not valid. Enter it as 15/03/2026." if EN else "Datum rođenja nije ispravan. Upiši ga kao 15.03.2026."))
                return
            if d > date.today():
                err.config(text=("The date of birth cannot be in the future." if EN else "Datum rođenja ne može biti u budućnosti."))
                return
            dp = parsiraj_datum(z["datum"])
            if dp and d <= dp:
                err.config(text=(f"The date of birth must be after the mating date ({z['datum']})." if EN else f"Datum rođenja mora biti posle datuma parenja ({z['datum']})."))
                return
            if od and d < od and not prev_v.get():
                err.config(text=(f"Pregnancy lasts until {oc.strftime('%d/%m/%Y')} – the earliest date of birth is "
                                f"{od.strftime('%d/%m/%Y')}. For an earlier birth tick \"Premature birth\"." if EN else f"Gravidnost traje do {oc.strftime('%d.%m.%Y')} – najraniji datum rođenja je "
                                f"{od.strftime('%d.%m.%Y')}. Za raniji porođaj štikliraj „Prevremeni porođaj“."))
                return
            try:
                zivih, mrtvih = int(bv.get()), int(mv.get() or 0)
            except ValueError:
                err.config(text=("The number of young must be a whole number." if EN else "Broj mladih mora biti ceo broj."))
                return
            if zivih < 0 or mrtvih < 0 or zivih + mrtvih == 0:
                err.config(text=("Enter how many young were born." if EN else "Upiši koliko je mladih rođeno."))
                return
            dstr = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
            opis = (f"Born alive: {zivih}" if EN else f"Rođeno živih: {zivih}") + ((f", stillborn: {mrtvih}" if EN else f", mrtvorođenih: {mrtvih}") if mrtvih else "")
            if od and d < od:
                opis += (f" – premature birth ({(oc - d).days} days before due date)" if EN else f" – prevremeni porođaj ({(oc - d).days} dana pre termina)")
            if majka:
                self.ist.dodaj(majka, ("Birth" if EN else "Porođaj"), opis, datum=dstr, partner=otac or "", vrednost=str(zivih))
            if otac and otac in m.A and not m.A[otac]["osnivac"]:
                self.ist.dodaj(otac, ("Offspring" if EN else "Potomak"), opis, datum=dstr, partner=majka or "", automatski=True)
            z["ishod"] = f"leglo:{zivih}:{dstr}:" if zivih else "rodjeno:"
            win.grab_release()
            win.destroy()
            self.promena((f"Birth recorded: {zivih} {n[3]} ({majka or '?'} × {otac or '?'})" if EN else f"Zabeleženo rođenje: {zivih} {n[3]} ({majka or '?'} × {otac or '?'})"))
            self.osvezi_istoriju()
            if odmah and zivih:
                self.upis_u_listu(z, parent)

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Record birth" if EN else "Zabeleži rođenje"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Enter in list now" if EN else "Odmah upiši u listu"), lambda: sacuvaj(True)).pack(side="right", padx=8)
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="left")
        win.bind("<Escape>", lambda ev: win.destroy())
        self.postavi_prozor(win, parent)


    def ukloni_iz_legla(self, z, parent=None):
        """Mladi koji neće biti upisani u listu (uginuli, prodati…) – uklanjaju se sa spiska čekanja."""
        lg = self.leglo(z)
        if not lg:
            return
        ukupno, dstr, vec = lg
        ostalo = ukupno - len(vec)
        majka, otac, vrsta, rasa, n = self.podaci_legla(z)
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Removing young from the list" if EN else "Uklanjanje mladih sa spiska"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Remove young that will not be entered" if EN else "Ukloni mlade koji neće biti upisani"), 15, "bold").pack(anchor="w")
        self.zaglavlje_legla(b, z, majka, otac)
        self.lbl(b, (f"Born {dstr}   ·   still waiting on the list: {ostalo} {n[3]}" if EN else f"Rođeno {dstr}   ·   na spisku čeka još {ostalo} {n[3]}")
                    + ((f" (entered: {', '.join(vec)})" if EN else f" (upisano: {', '.join(vec)})") if vec else ""), 9, fg=INK2).pack(anchor="w", pady=(4, 12))
        g = tk.Frame(b, bg=SURF)
        g.pack(fill="x")
        kv = tk.StringVar(value="1")
        rv = tk.StringVar(value=("Died" if EN else "Uginulo"))
        dv = tk.StringVar(value=date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        for i, (nasl, w) in enumerate(((("How many to remove" if EN else "Koliko ukloniti"), None), (("Reason" if EN else "Razlog"), None), (("Date" if EN else "Datum"), None))):
            f = tk.Frame(g, bg=SURF)
            f.grid(row=0, column=i, sticky="w", padx=(0, 16))
            self.lbl(f, nasl, 9, "bold", fg=INK2).pack(anchor="w")
            if i == 0:
                ttk.Spinbox(f, from_=1, to=ostalo, textvariable=kv, width=6, font=self.f(11)).pack(anchor="w", pady=(3, 0))
            elif i == 1:
                ttk.Combobox(f, textvariable=rv, values=[("Died" if EN else "Uginulo"), ("Sold" if EN else "Prodato"), ("Slaughtered" if EN else "Zaklano"), ("Given away" if EN else "Poklonjeno"), ("Other" if EN else "Drugo")],
                             width=14, font=self.f(10)).pack(anchor="w", pady=(3, 0))
            else:
                ttk.Entry(f, textvariable=dv, width=12, font=self.f(10)).pack(anchor="w", pady=(3, 0))
        sv_ = tk.BooleanVar(value=False)
        ttk.Checkbutton(b, text=(f"Remove all remaining ({ostalo})" if EN else f"Ukloni sve preostale ({ostalo})"), variable=sv_, style="Card.TCheckbutton",
                        command=lambda: kv.set(str(ostalo)) if sv_.get() else None).pack(anchor="w", pady=(10, 0))
        self.lbl(b, ("Note" if EN else "Napomena"), 9, "bold", fg=INK2).pack(anchor="w", pady=(10, 3))
        nv = tk.StringVar()
        ttk.Entry(b, textvariable=nv, width=50, font=self.f(10)).pack(anchor="w", fill="x")
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=460, justify="left")
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            try:
                k = int(kv.get())
            except ValueError:
                err.config(text=("The number must be a whole number." if EN else "Broj mora biti ceo broj."))
                return
            if not 1 <= k <= ostalo:
                err.config(text=(f"You can remove from 1 to {ostalo}." if EN else f"Možeš ukloniti od 1 do {ostalo}."))
                return
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            razlog = rv.get().strip() or ("Other" if EN else "Drugo")
            novo_uk = ukupno - k
            if novo_uk <= len(vec):
                z["ishod"] = ("rodjeno:" + ",".join(vec)) if vec else "uklonjeno"
            else:
                z["ishod"] = f"leglo:{novo_uk}:{dstr}:{','.join(vec)}"
            opis = (f"From the litter of {dstr} removed {k} {n[3] if k > 1 else n[2]} – {razlog.lower()}" if EN else f"Iz legla od {dstr} uklonjeno {k} {n[3] if k > 1 else n[2]} – {razlog.lower()}")
            if nv.get().strip():
                opis += f" ({nv.get().strip()})"
            if majka:
                self.ist.dodaj(majka, AUTO, opis, datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Removed from the list: {k} {n[3] if k > 1 else n[2]} ({razlog.lower()})" if EN else f"Uklonjeno sa spiska: {k} {n[3] if k > 1 else n[2]} ({razlog.lower()})"))
            self.osvezi_istoriju()

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Remove from list" if EN else "Ukloni sa spiska"), sacuvaj, "Danger").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        self.postavi_prozor(win, parent)


    def upis_u_listu(self, z, parent=None):
        """Korak 2: mladi dobili minđušu – upis oznake, markice i pola; datum i stado su automatski."""
        m = self.model
        lg = self.leglo(z)
        if not lg:
            return
        ukupno, dstr, vec = lg
        d = parsiraj_datum(dstr) or date.today()
        majka, otac, vrsta, rasa, n = self.podaci_legla(z)
        ostalo = max(1, ukupno - len(vec))

        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title((f"Entry in animal list – {n[3]}" if EN else f"Upis u listu grla – {n[3]}"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, (f"Entry in animal list ({n[3]})" if EN else f"Upis u listu grla ({n[3]})"), 16, "bold").pack(anchor="w")
        self.zaglavlje_legla(b, z, majka, otac)
        star = (date.today() - d).days
        self.lbl(b, (f"Litter: {ukupno} {n[3]}" if EN else f"Leglo: {ukupno} {n[3]}") + ((f", already entered {len(vec)} ({', '.join(vec)})" if EN else f", već upisano {len(vec)} ({', '.join(vec)})") if vec else "")
                 + ((f"   ·   inbreeding of young {pct(m.kinship(majka, otac))}" if EN else f"   ·   inbriding mladih {pct(m.kinship(majka, otac))}") if majka in m.A and otac in m.A else ""),
                 9, fg=INK2).pack(anchor="w", pady=(4, 0))

        auto = tk.Frame(b, bg=SURF2)
        auto.pack(fill="x", pady=(14, 4))
        g1 = tk.Frame(auto, bg=SURF2)
        g1.pack(fill="x", padx=14, pady=10)
        sv = tk.StringVar(value=STADO_PODMLADAK)
        for i, (nasl, vr) in enumerate(((("Date of birth" if EN else "Datum rođenja"), (f"{dstr}  ({star} days)" if EN else f"{dstr}  ({star} dana)")),
                                        (("Species / breed" if EN else "Vrsta / rasa"), f"{vrsta}{', ' + rasa if rasa else ''}"))):
            f = tk.Frame(g1, bg=SURF2)
            f.grid(row=0, column=i if i == 0 else 2, sticky="w", padx=(0, 22))
            self.lbl(f, nasl, 9, "bold", fg=INK2, bg=SURF2).pack(anchor="w")
            self.lbl(f, vr, 10, "bold", bg=SURF2).pack(anchor="w", pady=(6, 0))
        f = tk.Frame(g1, bg=SURF2)
        f.grid(row=0, column=1, sticky="w", padx=(0, 22))
        self.lbl(f, ("Herd" if EN else "Stado"), 9, "bold", fg=INK2, bg=SURF2).pack(anchor="w")
        ttk.Combobox(f, textvariable=sv, values=[STADO_PODMLADAK] + [x for x in self.sva_stada()
                                                                    if x != STADO_PODMLADAK],
                     width=16, font=self.f(10)).pack(anchor="w", pady=(3, 0))
        self.lbl(b, ("Date of birth and herd are automatic." if EN else "Datum rođenja i stado su automatski."), 8, fg="#8A968D").pack(anchor="w")

        self.lbl(b, (f"Enter each {n[2]}" if EN else f"Upiši svako {n[2]}"), 11, "bold").pack(anchor="w", pady=(14, 4))
        zag = tk.Frame(b, bg=SURF)
        zag.pack(fill="x")
        for t, w in ((("Tag / name *" if EN else "Oznaka / ime *"), 17), (("Ear tag number" if EN else "Ušna markica (minđuša)"), 19), (("Sex *" if EN else "Pol *"), 20)):
            self.lbl(zag, t, 9, "bold", fg=INK2, width=w, anchor="w").pack(side="left")
        lista = tk.Frame(b, bg=SURF)
        lista.pack(fill="x")
        redovi = []

        def dodaj_red(fokus=True):
            r = tk.Frame(lista, bg=SURF)
            r.pack(fill="x", pady=3)
            iv, mv, pv = tk.StringVar(), tk.StringVar(), tk.StringVar()
            e = ttk.Entry(r, textvariable=iv, width=15, font=self.f(10))
            e.pack(side="left", padx=(0, 10))
            ttk.Entry(r, textvariable=mv, width=17, font=self.f(10)).pack(side="left", padx=(0, 10))
            seg = tk.Frame(r, bg=SURF2)
            seg.pack(side="left")
            dug = {}

            def postavi(k):
                pv.set(k)
                for kk, lb in dug.items():
                    lb.config(bg=SURF if kk == k else SURF2, fg=INK if kk == k else INK2)
            for k, t in (("z", ("Female" if EN else "Žensko")), ("m", ("Male" if EN else "Muško"))):
                lb = tk.Label(seg, text=t, font=self.f(9, "bold"), padx=12, pady=4, bg=SURF2, fg=INK2,
                              cursor="hand2")
                lb.pack(side="left", padx=2, pady=2)
                lb.bind("<Button-1>", lambda ev, k=k: postavi(k))
                dug[k] = lb
            red_ = {"okvir": r, "id": iv, "mk": mv, "pol": pv}
            x_ = self.lbl(r, "✕", 11, "bold", fg=INK2, cursor="hand2")
            x_.pack(side="left", padx=10)
            x_.bind("<Button-1>", lambda ev: ukloni(red_))
            redovi.append(red_)
            if fokus:
                e.focus_set()

        def ukloni(red_):
            if len(redovi) > 1:
                red_["okvir"].destroy()
                redovi.remove(red_)

        for i in range(ostalo):
            dodaj_red(fokus=i == 0)
        lk = self.lbl(b, (f"+ Add another {n[2]}" if EN else f"+ Dodaj još jedno {n[2]}"), 9, "bold", fg=BRAND, cursor="hand2")
        lk.pack(anchor="w", pady=(6, 0))
        lk.bind("<Button-1>", lambda e: dodaj_red())
        self.lbl(b, ("If a young animal has no ear tag yet, remove its row (✕) – you will enter it later." if EN else "Ako neko mladunče još nema minđušu, ukloni njegov red (✕) – upisaćeš ga kasnije."), 8,
                 fg="#8A968D").pack(anchor="w", pady=(2, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=560, justify="left")
        err.pack(anchor="w", pady=(10, 0))

        def sacuvaj(ev=None):
            stado = sv.get().strip() or STADO_PODMLADAK
            namena_majke = (m.A.get(majka) or {}).get("namena", "") if majka else ""
            autoh_majke = (m.A.get(majka) or {}).get("autohtona", "") if majka else ""
            novi, vidjeni = [], set()
            for i, r in enumerate(redovi, 1):
                nid, mk, pol = r["id"].get().strip(), r["mk"].get().strip(), r["pol"].get()
                if not nid:
                    err.config(text=(f"Enter a tag or name for {n[2]} no. {i} (or remove the row ✕)." if EN else f"Upiši oznaku ili ime za {i}. {n[2]} (ili ukloni red ✕)."))
                    return
                if nid in vidjeni or self.red_za(nid) or nid in m.A:     # isto ime -> sledeći broj po redu (Bela 2…)
                    nid = slobodna_oznaka(nid, [x["id"] for x in self.tab.redovi] + list(m.A) + list(vidjeni))
                if mk:
                    poruka = self.markica_zauzeta(mk, None)
                    if poruka or any(norm(mk) == norm(x["markica"]) for x in novi):
                        err.config(text=poruka or (f"Ear tag {mk} is entered twice." if EN else f"Markica {mk} je upisana dva puta."))
                        return
                if pol not in ("m", "z"):
                    err.config(text=(f"Choose the sex for {nid}." if EN else f"Izaberi pol za {nid}."))
                    return
                vidjeni.add(nid)
                novi.append(dict(id=nid, markica=mk, vrsta=vrsta, rasa=rasa, namena=namena_majke, autohtona=autoh_majke, pol=pol, datum_rodjenja=dstr,
                                 otac=otac or "", majka=majka or "", status="aktivno", stado=stado,
                                 poreklo=("Home bred" if EN else "Sopstveni odgoj"), poreklo_od="", stare_markice="", uneto=sada()))
            for x in novi:
                self.tab.redovi.append(x)
                self.ist.dodaj(x["id"], AUTO, (f"Born {dstr} from {majka or '?'} × {otac or '?'} – entered in the list "
                                              f"(herd {stado})" if EN else f"Rođeno {dstr} od {majka or '?'} × {otac or '?'} – upisano u listu "
                                              f"(stado {stado})"), automatski=True)
            sad = vec + [x["id"] for x in novi]
            opis = ", ".join((f"{x['id']} ({'male' if x['pol'] == 'm' else 'female'})" if EN else f"{x['id']} ({'muško' if x['pol'] == 'm' else 'žensko'})") for x in novi)
            if majka:
                self.ist.dodaj(majka, AUTO, (f"Young stock entered in the list: {opis}" if EN else f"Podmladak upisan u listu: {opis}"), automatski=True)
            if len(sad) >= ukupno:
                z["ishod"] = "rodjeno:" + ",".join(sad)
            else:
                ost = ukupno - len(sad)
                cekaj = messagebox.askyesno(
                    ("Remaining young" if EN else "Ostali mladi"), (f"Entered {len(sad)} of {ukupno}. {ost} remaining.\n\n"
                                    "Are the others still waiting for ear tags?\n\n"
                                    "Yes – they stay on the list for later\nNo – they are gone (died, sold…)" if EN else f"Upisano {len(sad)} od {ukupno}. Ostalo još {ost}.\n\n"
                                    "Da li ostali još čekaju minđušu?\n\n"
                                    "Da – ostaju na spisku za kasnije\nNe – nema ih više (uginuli, prodati…)"),
                    parent=win)
                if cekaj:
                    z["ishod"] = f"leglo:{ukupno}:{dstr}:{','.join(sad)}"
                else:
                    z["ishod"] = "rodjeno:" + ",".join(sad)
                    if majka:
                        self.ist.dodaj(majka, AUTO, (f"From the litter ({dstr}) {ost} not entered – died or sold" if EN else f"Od legla ({dstr}) nije upisano {ost} – uginuli ili prodati"),
                                       automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Entered in the list: {', '.join(x['id'] for x in novi)} (herd {stado})" if EN else f"Upisano u listu: {', '.join(x['id'] for x in novi)} (stado {stado})"))
            self.osvezi_istoriju()

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Enter in animal list" if EN else "Upiši u listu grla"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        self.btn(fb, ("Remove from list…" if EN else "Ukloni sa spiska…"), lambda: (win.grab_release(), win.destroy(),
                                                    self.ukloni_iz_legla(z, parent)), "Danger").pack(side="left")
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        self.postavi_prozor(win, parent)
