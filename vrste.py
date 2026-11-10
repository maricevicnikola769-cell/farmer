"""Moje vrste – korisnik sam dodaje vrstu koje nema u programu (magarci, bivoli, alpake, kunići, psi, jeleni…).

Za svaku vrstu se pamti: naziv, kako se zovu mužjak / ženka / mladunče, trajanje gravidnosti i ciklus teranja.
Sve ostalo (rodoslov, srodstvo, parenje, istorija, telefon) radi isto kao za ugrađene vrste.
"""
import tkinter as tk
from tkinter import messagebox, ttk

import jezik
from jezik import T
from izgled import BAD, INK2, SURF, SURF2

# brzi primeri: (naziv, mužjak, ženka, mladunče, mladunčad, gravidnost od, do, prosek, ciklus teranja; 0 = bez podsetnika)
def primeri():
    return [
        (T("magarci", "donkeys"), T("magarac", "jack"), T("magarica", "jenny"), T("magare", "foal"), T("magarad", "foals"), 355, 380, 365, 23),
        (T("bivoli", "buffalo"), T("bivo", "bull"), T("bivolica", "cow"), T("bivolče", "calf"), T("bivolčad", "calves"), 300, 320, 310, 21),
        (T("alpake", "alpacas"), T("mužjak", "male"), T("ženka", "female"), T("mladunče", "cria"), T("mladunčad", "crias"), 330, 350, 340, 0),
        (T("kunići", "rabbits"), T("mužjak", "buck"), T("ženka", "doe"), T("kunić", "kit"), T("kunići", "kits"), 29, 34, 31, 0),
        (T("psi", "dogs"), T("pas", "dog"), T("kuja", "bitch"), T("štene", "puppy"), T("štenad", "puppies"), 58, 68, 63, 0),
        (T("jeleni", "deer"), T("jelen", "stag"), T("košuta", "hind"), T("lane", "fawn"), T("lanad", "fawns"), 225, 240, 233, 18),
    ]


class VrsteDeo:
    """Prozor „Moje vrste“ i učitavanje vrsta iz podešavanja."""

    def ucitaj_moje_vrste(self):
        self.pod["vrste_moje"] = jezik.postavi_moje_vrste(self.pod.get("vrste_moje", []))

    def prozor_vrsta(self, parent=None):
        win = tk.Toplevel(parent or self.root)
        win.title(T("Moje vrste", "My species"))
        win.configure(bg=SURF)
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Moje vrste", "My species"), 16, "bold").grid(row=0, column=0, columnspan=4, sticky="w")
        self.lbl(b, T("Dodaj vrstu koje nema u programu. Rodoslov, srodstvo, parenje i istorija rade isto kao za goveda, "
                      "ovce, koze, svinje i konje.",
                      "Add a species the program does not have. Pedigree, relationship, mating and history work the same as "
                      "for cattle, sheep, goats, pigs and horses."), 9, fg=INK2, wraplength=560,
                 justify="left").grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 10))

        spisak = tk.Frame(b, bg=SURF)
        spisak.grid(row=2, column=0, columnspan=4, sticky="ew")

        polja = {k: tk.StringVar() for k in ("ime", "m", "z", "ml", "mlm", "gmin", "gmax", "gpr", "ciklus")}
        menjam = {"ime": None}

        def popuni(v):
            for k, var in polja.items():
                var.set(str(v.get(k, "")))

        def prazno():
            popuni({})
            menjam["ime"] = None
            naslov.config(text=T("Nova vrsta", "New species"))
            err.config(text="")

        def osvezi_spisak():
            for w in spisak.winfo_children():
                w.destroy()
            moje = self.pod.get("vrste_moje", [])
            if not moje:
                self.lbl(spisak, T("Još nema dodatih vrsta.", "No species added yet."), 10, fg=INK2).pack(anchor="w")
            for v in moje:
                red = tk.Frame(spisak, bg=SURF2, padx=10, pady=6)
                red.pack(fill="x", pady=2)
                opis = (f"{v['ime'].capitalize()}  ·  {v['m']} / {v['z']} / {v['ml']}  ·  "
                        + T(f"gravidnost {v['gmin']}–{v['gmax']} (~{v['gpr']}) dana",
                            f"gestation {v['gmin']}–{v['gmax']} (~{v['gpr']}) days")
                        + (T(f"  ·  teranje na {v['ciklus']} dana", f"  ·  heat every {v['ciklus']} days") if v["ciklus"] else ""))
                self.lbl(red, opis, 10).pack(side="left")
                ob = self.lbl(red, T("obriši", "delete"), 9, "bold", fg=BAD, cursor="hand2")
                ob.pack(side="right", padx=(10, 0))
                ob.bind("<Button-1>", lambda e, v=v: obrisi(v))
                iz = self.lbl(red, T("izmeni", "edit"), 9, "bold", cursor="hand2")
                iz.pack(side="right")
                iz.bind("<Button-1>", lambda e, v=v: izmeni(v))

        def izmeni(v):
            popuni(v)
            menjam["ime"] = v["ime"]
            naslov.config(text=T(f"Izmena: {v['ime']}", f"Editing: {v['ime']}"))
            err.config(text="")

        def zapamti(lista, poruka):
            self.pod["vrste_moje"] = jezik.postavi_moje_vrste(lista)
            self.sacuvaj_podesavanja()
            try:
                self.sinh_uskoro()                       # telefoni dobijaju novu vrstu za par sekundi
            except Exception:
                pass
            osvezi_spisak()
            prazno()
            self.toast(poruka)
            try:
                self.prikazi(self.strana)
            except Exception:
                pass

        def obrisi(v):
            u_upotrebi = sum(1 for a in self.tab.redovi if jezik.vrsta_kanon(a.get("vrsta")) == v["ime"])
            pitanje = T(f"Obrisati vrstu „{v['ime']}“?", f"Delete the species “{v['ime']}”?")
            if u_upotrebi:
                pitanje += "\n\n" + T(f"{u_upotrebi} grla ima ovu vrstu. Grla ostaju, ali bez naziva i gravidnosti za ovu vrstu.",
                                      f"{u_upotrebi} animals have this species. They stay, but without names and gestation for it.")
            if messagebox.askyesno(T("Moje vrste", "My species"), pitanje, parent=win):
                zapamti([x for x in self.pod.get("vrste_moje", []) if x["ime"] != v["ime"]],
                        T("Vrsta je obrisana.", "Species deleted."))

        # ---------- obrazac
        ob = tk.Frame(b, bg=SURF)
        ob.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        naslov = self.lbl(ob, T("Nova vrsta", "New species"), 12, "bold")
        naslov.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        pr = tk.Frame(ob, bg=SURF)
        pr.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self.lbl(pr, T("Primeri:", "Examples:"), 9, "bold", fg=INK2).pack(side="left", padx=(0, 6))
        for p in primeri():
            l = self.lbl(pr, p[0], 9, "bold", cursor="hand2")
            l.pack(side="left", padx=4)
            l.bind("<Button-1>", lambda e, p=p: (popuni(dict(zip(("ime", "m", "z", "ml", "mlm", "gmin", "gmax", "gpr", "ciklus"), p))),
                                                 err.config(text="")))

        def unos(r, c, tekst, k, sirina=16):
            f = tk.Frame(ob, bg=SURF)
            f.grid(row=r, column=c, sticky="w", padx=(0, 12), pady=4)
            self.lbl(f, tekst, 9, "bold", fg=INK2).pack(anchor="w")
            ttk.Entry(f, textvariable=polja[k], width=sirina, font=self.f(10)).pack(anchor="w")

        unos(2, 0, T("Naziv vrste *", "Species name *"), "ime", 18)
        unos(3, 0, T("Mužjak", "Male"), "m")
        unos(3, 1, T("Ženka", "Female"), "z")
        unos(3, 2, T("Mladunče", "Young (one)"), "ml")
        unos(3, 3, T("Mladunčad", "Young (many)"), "mlm")
        unos(4, 0, T("Gravidnost najmanje (dana) *", "Gestation minimum (days) *"), "gmin", 8)
        unos(4, 1, T("Najviše *", "Maximum *"), "gmax", 8)
        unos(4, 2, T("Prosek *", "Average *"), "gpr", 8)
        unos(4, 3, T("Teranje na (dana)", "Heat every (days)"), "ciklus", 8)
        self.lbl(ob, T("Teranje: 0 ili prazno = bez podsetnika (npr. kunići, alpake, psi).",
                       "Heat: 0 or empty = no reminder (e.g. rabbits, alpacas, dogs)."), 8, fg="#8A968D").grid(
            row=5, column=0, columnspan=4, sticky="w")
        err = self.lbl(ob, "", 10, "bold", fg=BAD, wraplength=560, justify="left")
        err.grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 0))

        def sacuvaj(ev=None):
            v = {k: var.get().strip() for k, var in polja.items()}
            v["ciklus"] = v["ciklus"] or "0"
            ime = " ".join(v["ime"].split()).lower()
            if not ime:
                err.config(text=T("Upiši naziv vrste.", "Enter the species name."))
                return
            if jezik.vrsta_kanon(ime) in jezik._VRSTE_SR:
                err.config(text=T(f"„{ime}“ već postoji u programu.", f"“{ime}” already exists in the program."))
                return
            c = jezik.ocisti_vrstu(v)
            if not c:
                err.config(text=T("Gravidnost: cele brojeve dana, najmanje ≤ prosek ≤ najviše (10–500). Teranje: 0–120 dana.",
                                  "Gestation: whole days, minimum ≤ average ≤ maximum (10–500). Heat: 0–120 days."))
                return
            lista = [x for x in self.pod.get("vrste_moje", []) if x["ime"] not in (menjam["ime"], c["ime"])]
            for staro in (menjam["ime"], c["ime"]):          # stara ručna izmena nosivosti više ne važi
                if staro:
                    self.pod.get("gravidnost2", {}).pop("moja:" + staro, None)
            zapamti(lista + [c], T(f"Vrsta „{c['ime']}“ je sačuvana.", f"Species “{c['ime']}” saved."))

        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(16, 0))
        self.btn(fb, T("Sačuvaj vrstu", "Save species"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, T("Očisti", "Clear"), prazno).pack(side="right", padx=8)
        self.btn(fb, T("Zatvori", "Close"), win.destroy).pack(side="left")
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        osvezi_spisak()
        self.postavi_prozor(win, parent)
