"""Moje rase – rasa se upiše jednom (vrsta, naziv, namena, autohtona), pa se posle samo izabere kod novog grla.

Čuva se u podešavanjima ("rase_moje") i šalje telefonu. Rasa koja se prvi put upiše u formi grla
sama se doda na spisak. Namena rase važi za sva grla te rase (vidi namena_rase.py)."""
import tkinter as tk
from tkinter import messagebox, ttk

import jezik
from jezik import AUTO, T, namene_za, vrsta_kanon, vrsta_na_jeziku
from izgled import BAD, INK2, SURF
from namena_rase import grla_rase, namena_rase, postavi_namenu_rase, rasa_sa_namenom
from osnova import prevedi_vrednost
from podaci import autohtona_rasa, norm_rasa


def _ime(r):
    return " ".join(str(r or "").split()).lower()


def ocisti_rasu(v):
    """{'vrsta': kanonski naziv vrste, 'ime', 'namena', 'autohtona': '1'|''} ili None."""
    ime = norm_rasa(v.get("ime"))
    vrsta = vrsta_kanon(v.get("vrsta"))
    if not ime or not vrsta or not rasa_sa_namenom(ime):
        return None
    nam = prevedi_vrednost(v.get("namena") or "")
    return dict(vrsta=vrsta, ime=ime, namena=nam if nam in namene_za(vrsta) else "",
                autohtona="1" if v.get("autohtona") else "")


class RaseDeo:
    """Spisak „Moje rase“ i prozor za njega."""

    def moje_rase(self):
        lista = self.pod.get("rase_moje")
        if not isinstance(lista, list):               # prvi put: spisak se napravi od rasa koje već postoje u tablici
            lista, vidjeno = [], set()
            for r in self.tab.redovi:
                c = ocisti_rasu(dict(vrsta=r.get("vrsta"), ime=r.get("rasa"), autohtona=r.get("autohtona")))
                if c and (c["vrsta"], _ime(c["ime"])) not in vidjeno and r.get("status") != "obrisano":
                    vidjeno.add((c["vrsta"], _ime(c["ime"])))
                    c["namena"] = namena_rase(self.tab.redovi, r.get("vrsta"), c["ime"])
                    lista.append(c)
            self.pod["rase_moje"] = lista
        for r in lista:                               # posle promene jezika programa namena se prevede
            if r.get("namena"):
                r["namena"] = prevedi_vrednost(r["namena"])
        return lista

    def nadji_rasu(self, vrsta, ime):
        k, i = vrsta_kanon(vrsta), _ime(ime)
        return next((r for r in self.moje_rase() if r["vrsta"] == k and _ime(r["ime"]) == i), None)

    def rase_za_vrstu(self, vrsta):
        """Nazivi rasa za izbor u formi: moje rase te vrste + rase koje grla te vrste već imaju."""
        k = vrsta_kanon(vrsta)
        imena = {_ime(r["ime"]): r["ime"] for r in self.moje_rase() if r["vrsta"] == k}
        for a in self.tab.redovi:
            if vrsta_kanon(a.get("vrsta")) == k and rasa_sa_namenom(a.get("rasa")) and a.get("status") != "obrisano":
                imena.setdefault(_ime(a["rasa"]), a["rasa"])
        return sorted(imena.values(), key=str.lower)

    def zapamti_rasu(self, vrsta, ime, namena=None, autohtona=None):
        """Doda rasu na spisak ili joj osveži namenu. Vraća True ako je nešto promenjeno."""
        c = ocisti_rasu(dict(vrsta=vrsta, ime=ime, namena=namena, autohtona=autohtona))
        if not c:
            return False
        r = self.nadji_rasu(vrsta, ime)
        if r is None:
            self.moje_rase().append(c)
            return True
        staro = dict(r)
        if namena is not None and c["namena"]:
            r["namena"] = c["namena"]
        if autohtona is not None and c["autohtona"]:
            r["autohtona"] = "1"
        return r != staro

    # ---------------------------------------------------------- prozor
    def prozor_rasa(self, parent=None):
        win = tk.Toplevel(parent or self.root)
        win.title(T("Moje rase", "My breeds"))
        win.configure(bg=SURF)
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Moje rase", "My breeds"), 16, "bold").grid(row=0, column=0, columnspan=4, sticky="w")
        self.lbl(b, T("Rasu upišeš jednom, sa namenom. Posle je kod novog grla samo izabereš sa spiska, a namena se sama popuni.",
                      "Enter a breed once, with its purpose. Then just pick it from the list for a new animal and the purpose fills in."),
                 9, fg=INK2, wraplength=600, justify="left").grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 10))

        okvir = tk.Frame(b, bg=SURF)
        okvir.grid(row=2, column=0, columnspan=4, sticky="ew")
        kol = [("vrsta", T("Vrsta", "Species"), 120), ("ime", T("Rasa", "Breed"), 190), ("namena", T("Namena", "Purpose"), 130),
               ("grla", T("Grla", "Animals"), 60)]
        tv = ttk.Treeview(okvir, columns=[k for k, _, _ in kol], show="headings", height=9, selectmode="browse")
        for k, n, s in kol:
            tv.heading(k, text=n)
            tv.column(k, width=s, anchor="e" if k == "grla" else "w")
        sb = ttk.Scrollbar(okvir, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        sve_vrste = list(jezik.VRSTE) + [v["ime"] for v in self.pod.get("vrste_moje", [])]
        v_vrsta = tk.StringVar(value=sve_vrste[0] if sve_vrste else "")
        v_ime, v_nam, v_aut = tk.StringVar(), tk.StringVar(), tk.BooleanVar()
        menjam = {"r": None}

        def osvezi():
            tv.delete(*tv.get_children())
            for i, r in enumerate(sorted(self.moje_rase(), key=lambda r: (r["vrsta"], r["ime"].lower()))):
                vr = vrsta_na_jeziku(r["vrsta"])
                n = len(grla_rase(self.tab.redovi, vr, r["ime"]))
                tv.insert("", "end", iid=str(id(r)), values=(vr, r["ime"] + ("  ★" if r.get("autohtona") else ""),
                                                            r["namena"] or "–", n))

        def izabrana():
            s = tv.selection()
            return next((r for r in self.moje_rase() if str(id(r)) == s[0]), None) if s else None

        ob = tk.Frame(b, bg=SURF)
        ob.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        naslov = self.lbl(ob, T("Nova rasa", "New breed"), 12, "bold")
        naslov.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        def kutija(c, tekst):
            f = tk.Frame(ob, bg=SURF)
            f.grid(row=1, column=c, sticky="nw", padx=(0, 12))
            self.lbl(f, tekst, 9, "bold", fg=INK2).pack(anchor="w")
            return f
        cb_vr = ttk.Combobox(kutija(0, T("Vrsta *", "Species *")), textvariable=v_vrsta, values=sve_vrste, width=14,
                             state="readonly", font=self.f(10))
        cb_vr.pack(anchor="w")
        e_ime = ttk.Entry(kutija(1, T("Naziv rase *", "Breed name *")), textvariable=v_ime, width=22, font=self.f(10))
        e_ime.pack(anchor="w")
        f_nam = kutija(2, T("Namena", "Purpose"))
        cb_nam = ttk.Combobox(f_nam, textvariable=v_nam, width=16, state="readonly", font=self.f(10))
        cb_nam.pack(anchor="w")
        ttk.Checkbutton(ob, text=T("Autohtona rasa", "Native breed"), variable=v_aut).grid(row=2, column=0, columnspan=2,
                                                                                         sticky="w", pady=(8, 0))
        err = self.lbl(ob, "", 10, "bold", fg=BAD, wraplength=600, justify="left")
        err.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        def namene(*_):
            izb = namene_za(v_vrsta.get())
            cb_nam.config(values=izb, state="readonly" if izb else "disabled")
            if v_nam.get() not in izb:
                v_nam.set("")
        v_vrsta.trace_add("write", namene)
        namene()
        v_ime.trace_add("write", lambda *_: v_aut.set(True) if autohtona_rasa(v_ime.get()) and not menjam["r"] else None)

        def prazno():
            menjam["r"] = None
            v_ime.set("")
            v_nam.set("")
            v_aut.set(False)
            err.config(text="")
            naslov.config(text=T("Nova rasa", "New breed"))
            tv.selection_remove(*tv.selection())
            e_ime.focus_set()

        def izmeni(ev=None):
            r = izabrana()
            if not r:
                return
            menjam["r"] = r
            v_vrsta.set(vrsta_na_jeziku(r["vrsta"]))
            v_ime.set(r["ime"])
            v_nam.set(r["namena"])
            v_aut.set(bool(r.get("autohtona")))
            err.config(text="")
            naslov.config(text=T(f"Izmena: {r['ime']}", f"Editing: {r['ime']}"))
        tv.bind("<<TreeviewSelect>>", izmeni)

        def zapamti(poruka):
            self.sacuvaj_podesavanja()
            try:
                self.sinh_uskoro()
            except Exception:
                pass
            osvezi()
            prazno()
            self.toast(poruka)

        def sacuvaj(ev=None):
            c = ocisti_rasu(dict(vrsta=v_vrsta.get(), ime=v_ime.get(), namena=v_nam.get(), autohtona=v_aut.get()))
            if not c:
                err.config(text=T("Upiši naziv rase (ne melez ni hibrid – oni se ne upisuju kao rasa).",
                                  "Enter the breed name (not a crossbred or hybrid – those are not entered as a breed)."))
                return
            if namene_za(c["vrsta"]) and not c["namena"]:
                err.config(text=T("Izaberi namenu rase (", "Choose the breed purpose (") + " / ".join(namene_za(c["vrsta"])) + ").")
                return
            stara = menjam["r"]
            dupla = self.nadji_rasu(c["vrsta"], c["ime"])
            if dupla is not None and dupla is not stara:
                err.config(text=T(f"Rasa „{c['ime']}“ već postoji na spisku.", f"The breed “{c['ime']}” is already on the list."))
                return
            vr = vrsta_na_jeziku(c["vrsta"])
            # promena naziva: grla te rase dobijaju novi naziv
            preimenuj = []
            if stara and (stara["vrsta"], _ime(stara["ime"])) != (c["vrsta"], _ime(c["ime"])):
                preimenuj = grla_rase(self.tab.redovi, vrsta_na_jeziku(stara["vrsta"]), stara["ime"])
            menja_namenu = [r for r in grla_rase(self.tab.redovi, vr, c["ime"]) + preimenuj
                            if c["namena"] and (r.get("namena") or "") != c["namena"]]
            pitanje = []
            if preimenuj:
                pitanje.append(T(f"{len(preimenuj)} grla ima rasu „{stara['ime']}“ – i njima će rasa biti „{c['ime']}“.",
                                 f"{len(preimenuj)} animals have the breed “{stara['ime']}” – they will get “{c['ime']}” too."))
            if menja_namenu:
                pitanje.append(T(f"Namena „{c['namena']}“ biće upisana kod {len(menja_namenu)} grla te rase.",
                                 f"The purpose “{c['namena']}” will be set for {len(menja_namenu)} animals of this breed."))
            if pitanje and not messagebox.askyesno(T("Moje rase", "My breeds"), "\n\n".join(pitanje + [T("Nastaviti?", "Continue?")]),
                                                   parent=win):
                return
            for r in preimenuj:
                staro_ime = r.get("rasa")
                r["rasa"], r["vrsta"] = c["ime"], vr
                self.ist.dodaj(r["id"], AUTO, T(f"Rasa: {staro_ime} → {c['ime']}", f"Breed: {staro_ime} → {c['ime']}"), automatski=True)
            if c["namena"]:
                for r, st in postavi_namenu_rase(self.tab.redovi, vr, c["ime"], c["namena"]):
                    self.ist.dodaj(r["id"], AUTO, T(f"Namena rase: {st or '–'} → {c['namena']}",
                                                    f"Breed purpose: {st or '–'} → {c['namena']}"), automatski=True)
            if preimenuj or menja_namenu:
                self.promena(T(f"Rasa „{c['ime']}“ je sačuvana.", f"Breed “{c['ime']}” saved."))
            if stara is not None:
                stara.clear()
                stara.update(c)
            else:
                self.moje_rase().append(c)
            zapamti(T(f"Rasa „{c['ime']}“ je sačuvana.", f"Breed “{c['ime']}” saved."))

        def obrisi():
            r = izabrana()
            if not r:
                err.config(text=T("Izaberi rasu na spisku.", "Select a breed in the list."))
                return
            n = len(grla_rase(self.tab.redovi, vrsta_na_jeziku(r["vrsta"]), r["ime"]))
            pitanje = T(f"Skloniti rasu „{r['ime']}“ sa spiska?", f"Remove the breed “{r['ime']}” from the list?")
            if n:
                pitanje += "\n\n" + T(f"{n} grla ima ovu rasu – ona ostaju kakva jesu.", f"{n} animals have this breed – they stay as they are.")
            if messagebox.askyesno(T("Moje rase", "My breeds"), pitanje, parent=win):
                self.pod["rase_moje"] = [x for x in self.moje_rase() if x is not r]
                zapamti(T("Rasa je sklonjena sa spiska.", "Breed removed from the list."))

        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(16, 0))
        self.btn(fb, T("Sačuvaj rasu", "Save breed"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, T("Nova", "New"), prazno).pack(side="right", padx=8)
        self.btn(fb, T("Skloni sa spiska", "Remove from list"), obrisi, "Danger").pack(side="right")
        self.btn(fb, T("Zatvori", "Close"), win.destroy).pack(side="left")
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        osvezi()
        e_ime.focus_set()
        self.postavi_prozor(win, parent)
        return win
