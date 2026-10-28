"""Čitač elektronskih minđuša (RFID): USB ili Bluetooth čitač koji radi kao tastatura – „otkuca“ broj i Enter.
Prozor ostaje otvoren, pa se grla skeniraju jedno za drugim; nepoznat broj se može dodeliti grlu ili upisati novo grlo."""
import tkinter as tk
from tkinter import ttk

from osnova import EN
from jezik import AUTO, T
from podaci import cifre, norm, sort_key
from izgled import BAD, BRAND, INK, INK2, LINE, OK, SURF, SURF2, WARN


class CitacDeo:
    """Prozor „Čitač minđuša“ (F2) i pomoć za pretragu na strani Grla."""

    def rfid_zauzet(self, broj, red=None):
        """Poruka ako je elektronski broj već upisan kod drugog grla, inače None."""
        n = norm(broj)
        if not n:
            return None
        for r in self.tab.redovi:
            if r is red:
                continue
            if norm(r.get("rfid")) == n:
                return T(f"Elektronski broj {broj} je već upisan za grlo {r['id']}.", f"Electronic ID {broj} is already entered for animal {r['id']}.")
        return None

    def citac(self):
        if getattr(self, "citac_win", None) and self.citac_win.winfo_exists():
            self.citac_win.lift()
            self.citac_win.ulaz.focus_set()
            return
        win = tk.Toplevel(self.root, bg=SURF)
        self.citac_win = win
        win.title(T("Čitač minđuša", "Ear tag reader"))
        win.transient(self.root)
        r0 = self.root
        win.geometry(f"560x560+{r0.winfo_rootx() + max(0, (r0.winfo_width() - 560) // 2)}+{r0.winfo_rooty() + 40}")
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        self.lbl(b, T("📶 Čitač minđuša", "📶 Ear tag reader"), 16, "bold").pack(anchor="w")
        self.lbl(b, T("Prisloni čitač uz minđušu – broj se upiše sam. Radi sa USB i Bluetooth čitačima koji rade kao tastatura. "
                      "Broj možeš i da otkucaš pa pritisneš Enter.",
                      "Hold the reader to the ear tag – the number is entered by itself. Works with USB and Bluetooth readers that act "
                      "as a keyboard. You can also type the number and press Enter."),
                 9, fg=INK2, wraplength=500, justify="left").pack(anchor="w", pady=(2, 10))
        uv = tk.StringVar()
        ulaz = ttk.Entry(b, textvariable=uv, font=self.f(16), justify="center")
        ulaz.pack(fill="x", ipady=6)
        win.ulaz = ulaz
        rez = tk.Frame(b, bg=SURF)
        rez.pack(fill="x", pady=(14, 0))
        self.lbl(b, T("Skenirano u ovom prozoru:", "Scanned in this window:"), 9, "bold", fg=INK2).pack(anchor="w", pady=(16, 4))
        lista = tk.Frame(b, bg=SURF)
        lista.pack(fill="both", expand=True)
        istorija = []

        def osvezi_listu():
            for w in lista.winfo_children():
                w.destroy()
            for broj, x in istorija[-8:][::-1]:
                r = tk.Frame(lista, bg=SURF)
                r.pack(fill="x", pady=1)
                if x:
                    self.cip(r, x, lambda x=x: self.karton(x)).pack(side="left")
                else:
                    self.lbl(r, T("nepoznat", "unknown"), 9, "bold", fg=WARN).pack(side="left")
                self.lbl(r, broj, 9, fg=INK2).pack(side="left", padx=10)
            if istorija:
                nadj = len({x for _, x in istorija if x})
                self.lbl(lista, T(f"Ukupno: {len(istorija)} skeniranja, {nadj} različitih grla", f"Total: {len(istorija)} scans, {nadj} different animals"),
                         8, fg=INK2).pack(anchor="w", pady=(6, 0))

        def ocisti_rez():
            for w in rez.winfo_children():
                w.destroy()

        def obradi(ev=None):
            broj = " ".join(uv.get().split())
            uv.set("")
            if not broj:
                return
            ocisti_rez()
            m = self.model
            x = m.nadji_citac(broj)
            istorija.append((broj, x))
            osvezi_listu()
            o, c = self.card(rez, 16, 12)
            o.pack(fill="x")
            if x:
                a = m.A[x]
                red = tk.Frame(c, bg=SURF)
                red.pack(fill="x")
                self.cip(red, x, lambda: self.karton(x), big=True).pack(side="left")
                t = tk.Frame(red, bg=SURF)
                t.pack(side="left", padx=12)
                self.lbl(t, m.pol_naziv(x) + (", " + a["rasa"] if a["rasa"] else ""), 11, "bold").pack(anchor="w")
                stanje = T("u zapatu", "in herd") if a["aktivno"] else T("nije u zapatu", "not in herd")
                self.lbl(t, "  ·  ".join(v for v in (a["markica"], a.get("rfid"), a["stado"], stanje) if v), 9, fg=INK2,
                         wraplength=330, justify="left").pack(anchor="w")
                kar = self.karenca(x) if hasattr(self, "karenca") else None
                if kar:
                    self.lbl(c, "✚ " + T("karenca – ", "withdrawal – ") + str(self.opis_karence(x)), 9, "bold", fg=BAD,
                             wraplength=480, justify="left").pack(anchor="w", pady=(6, 0))
                dug = tk.Frame(c, bg=SURF)
                dug.pack(anchor="w", pady=(10, 0))
                self.btn(dug, T("Karton", "Card"), lambda: self.karton(x), "Primary").pack(side="left")
                self.btn(dug, T("Dodaj događaj…", "Add event…"), lambda: self.dogadjaj_forma(x, parent=win)).pack(side="left", padx=8)
            else:
                self.lbl(c, T(f"Nepoznat broj: {broj}", f"Unknown number: {broj}"), 11, "bold", fg=WARN).pack(anchor="w")
                self.lbl(c, T("Nijedno grlo nema ovaj broj. Upiši novo grlo ili dodeli broj grlu koje već postoji.",
                              "No animal has this number. Add a new animal or assign the number to an existing one."),
                         9, fg=INK2, wraplength=480, justify="left").pack(anchor="w", pady=(2, 8))
                dug = tk.Frame(c, bg=SURF)
                dug.pack(anchor="w")
                dugacak = len(cifre(broj)) >= 12          # elektronski broj (npr. 688 000123456789), a ne vidljiva markica
                preset = {"rfid": broj} if dugacak else {"markica": broj}
                self.btn(dug, T("+ Novo grlo", "+ New animal"), lambda: self.forma(preset=preset), "Primary").pack(side="left")
                izbor = tk.StringVar()
                bez = sorted((a["id"] for a in m.grla() if not a.get("rfid")), key=sort_key)
                cb = ttk.Combobox(dug, textvariable=izbor, values=bez, width=14, font=self.f(10))
                cb.pack(side="left", padx=(16, 6))
                poruka = self.lbl(c, "", 9, "bold", fg=BAD)
                poruka.pack(anchor="w", pady=(6, 0))

                def dodeli():
                    y = m.nadji(izbor.get())
                    red_ = next((r for r in self.tab.redovi if r["id"] == y), None) if y else None
                    if not red_:
                        poruka.config(text=T("Izaberi grlo iz liste.", "Choose an animal from the list."))
                        return
                    if dugacak:
                        zauzeto = self.rfid_zauzet(broj, red_)
                        if zauzeto:
                            poruka.config(text=zauzeto)
                            return
                        red_["rfid"] = broj
                        opis = T(f"Dodeljen elektronski broj {broj}", f"Electronic ID {broj} assigned")
                    else:
                        zauzeto = self.markica_zauzeta(broj, red_)
                        if zauzeto:
                            poruka.config(text=zauzeto)
                            return
                        self.primeni_markicu(red_, broj, zapamti=True)
                        opis = T(f"Upisana markica {broj} (čitač)", f"Ear tag {broj} entered (reader)")
                    self.ist.dodaj(y, AUTO, opis, automatski=True)
                    istorija[-1] = (broj, y)
                    self.promena(opis + " – " + y)
                    if win.winfo_exists():
                        osvezi_listu()
                        ocisti_rez()
                        ulaz.focus_set()
                self.btn(dug, T("Dodeli", "Assign"), dodeli).pack(side="left")
            ulaz.focus_set()

        ulaz.bind("<Return>", obradi)
        ulaz.bind("<KP_Enter>", obradi)
        win.bind("<Escape>", lambda e: win.destroy())
        ulaz.focus_set()
