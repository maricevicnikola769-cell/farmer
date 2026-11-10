"""Iskačuća poruka u uglu ekrana: hitni i skori podsetnici (porođaj, ter, karenca, podsetnici…) se pojave
iznad svih prozora – i kad je HerdDoc umanjen ili iza drugog programa. Svako obaveštenje iskoči najviše jednom dnevno."""
import tkinter as tk
from datetime import date

from jezik import T
from izgled import BAD, BRAND, INK, INK2, LINE, SURF, WARN

PROVERA_MIN = 30            # koliko često program proverava (minuta)
OSTAJE_SEK = 180            # poruka se sama skloni posle 3 minuta


def kljuc_obavestenja(o):
    return f"{o.get('grlo') or ''}|{o.get('naslov', '')}"


class IskacuceDeo:
    """Poruke na ekranu za obaveštenja koja traže pažnju."""

    def iskacuce_ukljuceno(self):
        return self.pod.get("iskacuce", True)

    def _vec_prikazano(self):
        danas = date.today().isoformat()
        z = self.pod.get("iskaceno")
        if not isinstance(z, dict) or z.get("datum") != danas:
            z = {"datum": danas, "kljucevi": []}
            self.pod["iskaceno"] = z
        return z

    def zapamti_prikazana(self, obavestenja):
        z = self._vec_prikazano()
        z["kljucevi"] = list(dict.fromkeys(z["kljucevi"] + [kljuc_obavestenja(o) for o in obavestenja]))[-300:]

    def nova_za_poruku(self):
        """Hitna i skora obaveštenja koja danas još nisu iskočila."""
        vec = set(self._vec_prikazano()["kljucevi"])
        return [o for o in self.obavestenja() if o["nivo"] <= 1 and kljuc_obavestenja(o) not in vec]

    def iskacuce_provera(self):
        try:
            if self.iskacuce_ukljuceno():
                nova = self.nova_za_poruku()
                if nova:
                    self.zapamti_prikazana(nova)
                    self.sacuvaj_podesavanja()
                    self.iskacuca_poruka(nova)
        except Exception:
            pass
        self.root.after(PROVERA_MIN * 60 * 1000, self.iskacuce_provera)

    def iskacuca_poruka(self, stavke):
        stari = getattr(self, "_iskacuca", None)
        if stari is not None and stari.winfo_exists():
            stari.destroy()
        win = tk.Toplevel(self.root, bg=LINE)
        self._iskacuca = win
        win.overrideredirect(True)                       # bez okvira – mali prozorčić u uglu
        try:
            win.attributes("-topmost", True)             # iznad svih programa
        except tk.TclError:
            pass
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=1, pady=1)
        u = tk.Frame(b, bg=SURF)
        u.pack(fill="both", expand=True, padx=16, pady=12)
        gore = tk.Frame(u, bg=SURF)
        gore.pack(fill="x")
        hitno = any(o["nivo"] == 0 for o in stavke)
        tk.Label(gore, text="🔔  HerdDoc", bg=SURF, fg=BAD if hitno else BRAND, font=self.f(11, "bold")).pack(side="left")
        x_ = tk.Label(gore, text="✕", bg=SURF, fg=INK2, font=self.f(11, "bold"), cursor="hand2")
        x_.pack(side="right")
        x_.bind("<Button-1>", lambda e: win.destroy())
        for o in stavke[:4]:
            r = tk.Frame(u, bg=SURF)
            r.pack(fill="x", pady=(8, 0))
            tk.Frame(r, bg=BAD if o["nivo"] == 0 else WARN, width=4, height=30).pack(side="left", fill="y", padx=(0, 8))
            t = tk.Frame(r, bg=SURF)
            t.pack(side="left", fill="x", expand=True)
            tk.Label(t, text=((o["grlo"] + " – ") if o.get("grlo") else "") + o["naslov"], bg=SURF, fg=INK,
                     font=self.f(10, "bold"), wraplength=300, justify="left", anchor="w").pack(anchor="w")
            if o.get("opis"):
                tk.Label(t, text=o["opis"], bg=SURF, fg=INK2, font=self.f(9), wraplength=300, justify="left",
                         anchor="w").pack(anchor="w")
        if len(stavke) > 4:
            tk.Label(u, text=T(f"… i još {len(stavke) - 4}", f"… and {len(stavke) - 4} more"), bg=SURF, fg=INK2,
                     font=self.f(9)).pack(anchor="w", pady=(6, 0))

        def otvori():
            win.destroy()
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
            except tk.TclError:
                pass
            self.prikazi("obavestenja")
        dole = tk.Frame(u, bg=SURF)
        dole.pack(fill="x", pady=(12, 0))
        self.btn(dole, T("Otvori obaveštenja", "Open notifications"), otvori, "Primary").pack(side="right")
        self.btn(dole, T("Kasnije", "Later"), win.destroy).pack(side="right", padx=8)
        win.update_idletasks()
        sir, vis = max(win.winfo_reqwidth(), 360), win.winfo_reqheight()
        win.geometry(f"{sir}x{vis}+{win.winfo_screenwidth() - sir - 18}+{win.winfo_screenheight() - vis - 64}")
        try:
            self.root.bell()
        except tk.TclError:
            pass
        win.after(OSTAJE_SEK * 1000, lambda: win.winfo_exists() and win.destroy())
        return win
