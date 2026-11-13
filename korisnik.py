"""Ko radi u programu: ime i prezime se upiše jednom (obavezno), a svaki zapis u istoriji pamti ko ga je uneo."""
import tkinter as tk

import podaci
from izgled import BAD, BRAND, INK2, SURF
from jezik import T
from ocene import cisto_ime


class KorisnikDeo:
    def postavi_korisnika(self, ime):
        podaci.KORISNIK = cisto_ime(ime)
        lb = getattr(self, "lbl_korisnik", None)
        try:
            if lb is not None and lb.winfo_exists():
                lb.config(text="👤 " + (podaci.KORISNIK or T("Upiši svoje ime…", "Enter your name…")))
        except tk.TclError:
            pass

    def korisnik_na_startu(self):
        self.postavi_korisnika(self.pod.get("korisnik", ""))
        if len(podaci.KORISNIK.split()) < 2:
            self.prozor_korisnika(obavezno=True)

    def prozor_korisnika(self, obavezno=False):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Ko radi u programu", "Who is working"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Ko radi na ovom računaru?", "Who is working on this computer?"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Upiši ime i prezime. Uz svaku promenu (događaj, izmenu podataka, ocenu) piše ko ju je uneo.",
                      "Enter your first and last name. Every change (event, edited details, score) shows who entered it."),
                 9, fg=INK2, wraplength=380, justify="left").pack(anchor="w", pady=(4, 12))
        delovi = podaci.KORISNIK.split(" ", 1)
        v_ime, v_prez = tk.StringVar(value=delovi[0] if delovi else ""), tk.StringVar(value=delovi[1] if len(delovi) > 1 else "")
        f = tk.Frame(b, bg=SURF)
        f.pack(anchor="w")
        for r, (naz, v) in enumerate(((T("Ime", "First name"), v_ime), (T("Prezime", "Last name"), v_prez))):
            self.lbl(f, naz, 10).grid(row=r, column=0, sticky="w", pady=3)
            e = tk.Entry(f, textvariable=v, width=28, font=self.f(11))
            e.grid(row=r, column=1, padx=(10, 0), pady=3)
            if r == 0:
                e.focus_set()
        greska = self.lbl(b, "", 9, fg=BAD)
        greska.pack(anchor="w", pady=(6, 0))

        def sacuvaj(*_):
            ime, prez = cisto_ime(v_ime.get()), cisto_ime(v_prez.get())
            if not ime or not prez:
                greska.config(text=T("Upiši i ime i prezime.", "Enter both first and last name."))
                return
            self.pod["korisnik"] = f"{ime} {prez}"
            self.sacuvaj_podesavanja()
            self.postavi_korisnika(self.pod["korisnik"])
            win.grab_release()
            win.destroy()
            if obavezno:
                self.root.after(300, self.obavestenja_na_startu)

        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(12, 0))
        self.btn(dno, T("Sačuvaj", "Save"), sacuvaj, "Primary").pack(side="right")
        if not obavezno:
            self.btn(dno, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=(0, 8))
            win.bind("<Escape>", lambda e: win.destroy())
        else:
            win.protocol("WM_DELETE_WINDOW", lambda: greska.config(text=T("Ime i prezime su obavezni.", "First and last name are required.")))
        win.bind("<Return>", sacuvaj)
        win.update_idletasks()
        win.geometry(f"+{self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2}"
                     f"+{self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 3)}")

    def oznaka_korisnika(self, foot):
        self.lbl_korisnik = tk.Label(foot, text="", bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2", anchor="w")
        self.lbl_korisnik.pack(anchor="w", pady=(6, 0))
        self.lbl_korisnik.bind("<Button-1>", lambda e: self.prozor_korisnika())
        self.postavi_korisnika(self.pod.get("korisnik", ""))
