"""Ko radi u programu: svaki radnik ima svoje ime i šifru. Program se otvara tek posle prijave,
a svaki zapis u istoriji pamti ko ga je uneo.

- prvi nalog je VLASNIK: on dodaje i uklanja radnike i menja im šifre;
- šifre se ne čuvaju, čuva se samo njihov otisak (PBKDF2), pa se ne mogu pročitati iz podešavanja;
- ako vlasnik zaboravi šifru, ulazi KODOM ZA VRAĆANJE koji dobije kad pravi nalog (zapiše ga na papir)."""
import hashlib
import secrets
import tkinter as tk
from tkinter import messagebox, ttk

import podaci
from izgled import BAD, BRAND, INK2, SURF
from jezik import T
from ocene import cisto_ime

PONAVLJANJA = 120_000
NAJKRACA_SIFRA = 4
KOD_ZNACI = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def otisak(sifra, so):
    return hashlib.pbkdf2_hmac("sha256", str(sifra).encode("utf-8"), bytes.fromhex(so), PONAVLJANJA).hex()


def novi_nalog(ime, sifra, vlasnik=False):
    so = secrets.token_hex(16)
    return dict(ime=cisto_ime(ime), so=so, otisak=otisak(sifra, so), vlasnik=bool(vlasnik))


def sifra_valja(nalog, sifra):
    try:
        return secrets.compare_digest(otisak(sifra, nalog["so"]), nalog["otisak"])
    except (KeyError, ValueError, TypeError):
        return False


def novi_kod_za_vracanje():
    k = "".join(secrets.choice(KOD_ZNACI) for _ in range(12))
    return f"{k[:4]}-{k[4:8]}-{k[8:]}"


def _cist_kod(k):
    return "".join(c for c in str(k).upper() if c.isalnum())


def isto_ime(a, b):
    return cisto_ime(a).casefold() == cisto_ime(b).casefold()


class KorisnikDeo:
    # ------------------------------------------------------------ nalozi
    def nalozi(self):
        return [n for n in self.pod.get("korisnici", []) if isinstance(n, dict) and n.get("ime")]

    def nalog(self, ime):
        return next((n for n in self.nalozi() if isto_ime(n["ime"], ime)), None)

    def nalozi_za_telefon(self):
        """Isti radnici i šifre i u aplikaciji (samo otisci šifri; ceo snimak je i tako zaključan ključem farme)."""
        return [dict(ime=n["ime"], so=n["so"], otisak=n["otisak"], vlasnik=bool(n.get("vlasnik"))) for n in self.nalozi()
                if n.get("so") and n.get("otisak")]

    def ja_sam_vlasnik(self):
        n = self.nalog(podaci.KORISNIK)
        return bool(n and n.get("vlasnik"))

    def postavi_korisnika(self, ime):
        podaci.KORISNIK = cisto_ime(ime)
        if podaci.KORISNIK:
            self.pod["korisnik"] = podaci.KORISNIK
        lb = getattr(self, "lbl_korisnik", None)
        try:
            if lb is not None and lb.winfo_exists():
                lb.config(text="👤 " + (podaci.KORISNIK or T("Prijavi se…", "Sign in…")) + "  ▾")
        except tk.TclError:
            pass

    def oznaka_korisnika(self, foot):
        self.lbl_korisnik = tk.Label(foot, text="", bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2", anchor="w")
        self.lbl_korisnik.pack(anchor="w", pady=(6, 0))
        self.lbl_korisnik.bind("<Button-1>", lambda e: self.meni_korisnika())
        odj = tk.Label(foot, text=T("🔒 Odjavi se", "🔒 Sign out"), bg=SURF, fg=INK2, font=self.f(9), cursor="hand2", anchor="w")
        odj.pack(anchor="w", pady=(2, 0))
        odj.bind("<Button-1>", lambda e: self.zakljucaj())
        self.postavi_korisnika(podaci.KORISNIK)

    # ------------------------------------------------------------ start: bez prijave nema programa
    def korisnik_na_startu(self):
        podaci.KORISNIK = ""
        try:
            self.root.withdraw()                     # podaci se ne vide dok se neko ne prijavi
        except tk.TclError:
            return
        if self.nalozi():
            self.prozor_prijave(na_startu=True)
        else:
            self.prozor_vlasnika()

    def _prijavljen(self, ime, na_startu):
        self.postavi_korisnika(ime)
        self.sacuvaj_podesavanja()
        if na_startu:
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                return
            if not getattr(self, "_posle_prijave_bilo", False):
                self._posle_prijave_bilo = True
                self.root.after(300, self.obavestenja_na_startu)
        self.toast(T(f"Prijavljen: {podaci.KORISNIK}", f"Signed in: {podaci.KORISNIK}"))

    def _prozor(self, naslov, na_startu):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(naslov)
        win.resizable(False, False)
        try:
            vidljiv = bool(self.root.winfo_viewable())
        except tk.TclError:
            vidljiv = False
        if not na_startu and vidljiv:                    # uz sakriven glavni prozor ne sme „transient“ (ne bi se video)
            win.transient(self.root)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=28, pady=24)
        if na_startu:                                    # zatvaranje prozora prijave = izlaz iz programa
            win.protocol("WM_DELETE_WINDOW", lambda: (win.destroy(), self.zatvori()))
            if getattr(self, "logo", None) and 32 in self.logo:
                tk.Label(b, image=self.logo[32], bg=SURF).pack(anchor="w", pady=(0, 6))
        return win, b

    def _na_sredinu(self, win):
        win.update_idletasks()
        try:
            if self.root.winfo_viewable():
                x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
                y = self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 3)
            else:
                x = (win.winfo_screenwidth() - win.winfo_width()) // 2
                y = (win.winfo_screenheight() - win.winfo_height()) // 3
            win.geometry(f"+{max(0, x)}+{max(0, y)}")
            win.lift()
            win.focus_force()
            win.grab_set()
        except tk.TclError:
            pass

    def _polje(self, f, red, naziv, sakrij=False, vrednost=""):
        self.lbl(f, naziv, 10).grid(row=red, column=0, sticky="w", pady=4)
        v = tk.StringVar(value=vrednost)
        e = tk.Entry(f, textvariable=v, width=26, font=self.f(11), show="•" if sakrij else "")
        e.grid(row=red, column=1, padx=(12, 0), pady=4, sticky="w")
        return v, e

    # ------------------------------------------------------------ prijava
    def prozor_prijave(self, na_startu=False):
        win, b = self._prozor(T("Prijava", "Sign in"), na_startu)
        self.lbl(b, T("Prijava u HerdDoc", "Sign in to HerdDoc"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Izaberi svoje ime i upiši šifru.", "Choose your name and enter your password."), 9, fg=INK2).pack(anchor="w", pady=(2, 12))
        f = tk.Frame(b, bg=SURF)
        f.pack(anchor="w")
        imena = [n["ime"] for n in self.nalozi()]
        pocetno = podaci.KORISNIK or self.pod.get("korisnik", "")
        self.lbl(f, T("Korisnik", "User"), 10).grid(row=0, column=0, sticky="w", pady=4)
        v_ime = tk.StringVar(value=next((i for i in imena if isto_ime(i, pocetno)), imena[0] if imena else ""))
        ttk.Combobox(f, textvariable=v_ime, values=imena, state="readonly", width=26, font=self.f(11)).grid(row=0, column=1, padx=(12, 0), pady=4)
        v_sif, e_sif = self._polje(f, 1, T("Šifra", "Password"), sakrij=True)
        greska = self.lbl(b, "", 9, fg=BAD)
        greska.pack(anchor="w", pady=(6, 0))
        pokusaji = [0]

        def prijavi(*_):
            n = self.nalog(v_ime.get())
            if n is None or not sifra_valja(n, v_sif.get()):
                pokusaji[0] += 1
                v_sif.set("")
                greska.config(text=T("Pogrešna šifra.", "Wrong password."))
                if pokusaji[0] >= 5:                    # usporava pogađanje
                    dug.configure(state="disabled")
                    win.after(5000 * (pokusaji[0] - 4), lambda: dug.configure(state="normal"))
                return
            win.grab_release()
            win.destroy()
            self._prijavljen(n["ime"], na_startu)

        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(14, 0))
        dug = self.btn(dno, T("Prijavi se", "Sign in"), prijavi, "Primary")
        dug.pack(side="right")
        if na_startu:
            self.btn(dno, T("Izađi", "Exit"), lambda: (win.destroy(), self.zatvori())).pack(side="right", padx=(0, 8))
        else:
            self.btn(dno, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=(0, 8))
            win.bind("<Escape>", lambda e: win.destroy())
        zab = tk.Label(b, text=T("Zaboravljena šifra?", "Forgot password?"), bg=SURF, fg=BRAND, font=self.f(9), cursor="hand2")
        zab.pack(anchor="w", pady=(12, 0))
        zab.bind("<Button-1>", lambda e: self.zaboravljena_sifra(win, na_startu))
        win.bind("<Return>", prijavi)
        self._na_sredinu(win)
        e_sif.focus_set()

    def zaboravljena_sifra(self, roditelj, na_startu):
        if not messagebox.askyesno(T("Zaboravljena šifra", "Forgot password"), T(
                "Radnik koji je zaboravio šifru: neka vlasnik farme upiše novu (👤 → Radnici).\n\n"
                "Vlasnik koji je zaboravio šifru ulazi kodom za vraćanje koji je zapisao kad je pravio nalog.\n\nUpisati kod za vraćanje?",
                "A worker who forgot the password: the farm owner sets a new one (👤 → Workers).\n\n"
                "An owner who forgot the password signs in with the recovery code written down when the account was made.\n\nEnter the recovery code?"),
                parent=roditelj):
            return
        win, b = self._prozor(T("Kod za vraćanje", "Recovery code"), False)
        win.transient(roditelj)
        self.lbl(b, T("Kod za vraćanje", "Recovery code"), 14, "bold").pack(anchor="w")
        f = tk.Frame(b, bg=SURF)
        f.pack(anchor="w", pady=(10, 0))
        v_kod, e_kod = self._polje(f, 0, T("Kod", "Code"))
        v_s1, _ = self._polje(f, 1, T("Nova šifra", "New password"), sakrij=True)
        v_s2, _ = self._polje(f, 2, T("Ponovi šifru", "Repeat password"), sakrij=True)
        greska = self.lbl(b, "", 9, fg=BAD)
        greska.pack(anchor="w", pady=(6, 0))

        def potvrdi(*_):
            vr = self.pod.get("vracanje") or {}
            if not vr or not secrets.compare_digest(otisak(_cist_kod(v_kod.get()), vr.get("so", "00")), vr.get("otisak", "")):
                greska.config(text=T("Kod nije tačan.", "The code is not correct."))
                return
            g = self._greska_sifre(v_s1.get(), v_s2.get())
            if g:
                greska.config(text=g)
                return
            vl = next((n for n in self.nalozi() if n.get("vlasnik")), None)
            if vl is None:
                return
            vl.update(novi_nalog(vl["ime"], v_s1.get(), True))
            self.sacuvaj_podesavanja()
            win.destroy()
            try:
                roditelj.destroy()
            except tk.TclError:
                pass
            messagebox.showinfo("HerdDoc", T(f"Nova šifra je postavljena za: {vl['ime']}", f"New password set for: {vl['ime']}"))
            self._prijavljen(vl["ime"], na_startu)

        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(14, 0))
        self.btn(dno, T("Postavi šifru", "Set password"), potvrdi, "Primary").pack(side="right")
        self.btn(dno, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=(0, 8))
        win.bind("<Return>", potvrdi)
        win.bind("<Escape>", lambda e: win.destroy())
        self._na_sredinu(win)
        e_kod.focus_set()

    @staticmethod
    def _greska_sifre(s1, s2):
        if len(s1) < NAJKRACA_SIFRA:
            return T(f"Šifra mora imati bar {NAJKRACA_SIFRA} znaka.", f"The password must have at least {NAJKRACA_SIFRA} characters.")
        if s1 != s2:
            return T("Šifre se ne poklapaju.", "The passwords do not match.")
        return ""

    # ------------------------------------------------------------ prvi nalog (vlasnik)
    def prozor_vlasnika(self):
        win, b = self._prozor(T("Vlasnik farme", "Farm owner"), True)
        self.lbl(b, T("Nalog vlasnika farme", "Farm owner account"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("HerdDoc se otvara samo sa šifrom. Uz svaku promenu piše ko ju je uneo. "
                      "Vlasnik posle može da doda radnike, svakog sa svojom šifrom.",
                      "HerdDoc opens only with a password. Every change shows who entered it. "
                      "The owner can later add workers, each with their own password."),
                 9, fg=INK2, wraplength=400, justify="left").pack(anchor="w", pady=(2, 12))
        delovi = cisto_ime(self.pod.get("korisnik", "")).split(" ", 1)
        f = tk.Frame(b, bg=SURF)
        f.pack(anchor="w")
        v_ime, e_ime = self._polje(f, 0, T("Ime", "First name"), vrednost=delovi[0] if delovi and delovi[0] else "")
        v_prez, _ = self._polje(f, 1, T("Prezime", "Last name"), vrednost=delovi[1] if len(delovi) > 1 else "")
        v_s1, _ = self._polje(f, 2, T("Šifra", "Password"), sakrij=True)
        v_s2, _ = self._polje(f, 3, T("Ponovi šifru", "Repeat password"), sakrij=True)
        greska = self.lbl(b, "", 9, fg=BAD)
        greska.pack(anchor="w", pady=(6, 0))

        def sacuvaj(*_):
            ime, prez = cisto_ime(v_ime.get()), cisto_ime(v_prez.get())
            if not ime or not prez:
                greska.config(text=T("Upiši i ime i prezime.", "Enter both first and last name."))
                return
            g = self._greska_sifre(v_s1.get(), v_s2.get())
            if g:
                greska.config(text=g)
                return
            kod = novi_kod_za_vracanje()
            so = secrets.token_hex(16)
            self.pod["korisnici"] = [novi_nalog(f"{ime} {prez}", v_s1.get(), vlasnik=True)]
            self.pod["vracanje"] = dict(so=so, otisak=otisak(_cist_kod(kod), so))
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            self.prikazi_kod_za_vracanje(kod, lambda: self._prijavljen(f"{ime} {prez}", True))

        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(14, 0))
        self.btn(dno, T("Sačuvaj", "Save"), sacuvaj, "Primary").pack(side="right")
        self.btn(dno, T("Izađi", "Exit"), lambda: (win.destroy(), self.zatvori())).pack(side="right", padx=(0, 8))
        win.bind("<Return>", sacuvaj)
        self._na_sredinu(win)
        e_ime.focus_set()

    def prikazi_kod_za_vracanje(self, kod, dalje):
        win, b = self._prozor(T("Kod za vraćanje", "Recovery code"), False)
        self.lbl(b, T("Zapiši ovaj kod na papir", "Write this code down on paper"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Ako zaboraviš šifru, ovim kodom ulaziš u program i postavljaš novu. Prikazuje se samo sada.",
                      "If you forget your password, this code lets you in to set a new one. It is shown only now."),
                 9, fg=INK2, wraplength=400, justify="left").pack(anchor="w", pady=(2, 12))
        tk.Label(b, text=kod, bg=SURF, fg=BRAND, font=self.f(20, "bold")).pack(pady=(4, 8))

        def kopiraj():
            self.root.clipboard_clear()
            self.root.clipboard_append(kod)

        def gotovo(*_):
            win.grab_release()
            win.destroy()
            dalje()

        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(10, 0))
        self.btn(dno, T("Zapisao sam – dalje", "Written down – continue"), gotovo, "Primary").pack(side="right")
        self.btn(dno, T("Kopiraj", "Copy"), kopiraj).pack(side="right", padx=(0, 8))
        win.protocol("WM_DELETE_WINDOW", gotovo)
        self._na_sredinu(win)

    # ------------------------------------------------------------ meni 👤
    def meni_korisnika(self):
        mn = tk.Menu(self.root, tearoff=0)
        mn.add_command(label=T("🔒 Odjavi se (drugi radnik se prijavljuje)", "🔒 Sign out (another worker signs in)"), command=self.zakljucaj)
        mn.add_command(label=T("Promeni svoju šifru…", "Change my password…"), command=self.promena_sifre)
        if self.ja_sam_vlasnik():
            mn.add_separator()
            mn.add_command(label=T("Radnici (dodaj, ukloni, šifre)…", "Workers (add, remove, passwords)…"), command=self.prozor_radnika)
        lb = self.lbl_korisnik
        try:
            mn.tk_popup(lb.winfo_rootx(), lb.winfo_rooty() - 10 - 24 * (4 if self.ja_sam_vlasnik() else 2))
        finally:
            mn.grab_release()

    def zakljucaj(self):
        """Odjava: program se sakrije dok se neko ne prijavi (svako svojom šifrom)."""
        podaci.KORISNIK = ""
        self.postavi_korisnika("")
        for w in self.root.winfo_children():
            if isinstance(w, tk.Toplevel):
                try:
                    w.destroy()
                except tk.TclError:
                    pass
        self.root.withdraw()
        self.prozor_prijave(na_startu=True)

    def promena_sifre(self):
        n = self.nalog(podaci.KORISNIK)
        if n is None:
            return
        win, b = self._prozor(T("Promena šifre", "Change password"), False)
        self.lbl(b, T(f"Šifra za: {n['ime']}", f"Password for: {n['ime']}"), 14, "bold").pack(anchor="w")
        f = tk.Frame(b, bg=SURF)
        f.pack(anchor="w", pady=(10, 0))
        v_st, e_st = self._polje(f, 0, T("Sadašnja šifra", "Current password"), sakrij=True)
        v_s1, _ = self._polje(f, 1, T("Nova šifra", "New password"), sakrij=True)
        v_s2, _ = self._polje(f, 2, T("Ponovi šifru", "Repeat password"), sakrij=True)
        greska = self.lbl(b, "", 9, fg=BAD)
        greska.pack(anchor="w", pady=(6, 0))

        def sacuvaj(*_):
            if not sifra_valja(n, v_st.get()):
                greska.config(text=T("Sadašnja šifra nije tačna.", "The current password is not correct."))
                return
            g = self._greska_sifre(v_s1.get(), v_s2.get())
            if g:
                greska.config(text=g)
                return
            n.update(novi_nalog(n["ime"], v_s1.get(), n.get("vlasnik")))
            self.sacuvaj_podesavanja()
            win.destroy()
            self.toast(T("Šifra je promenjena.", "The password was changed."))

        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(14, 0))
        self.btn(dno, T("Sačuvaj", "Save"), sacuvaj, "Primary").pack(side="right")
        self.btn(dno, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=(0, 8))
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        self._na_sredinu(win)
        e_st.focus_set()

    # ------------------------------------------------------------ radnici (samo vlasnik)
    def prozor_radnika(self):
        if not self.ja_sam_vlasnik():
            return
        win, b = self._prozor(T("Radnici", "Workers"), False)
        self.lbl(b, T("Radnici na ovom računaru", "Workers on this computer"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Svako se prijavljuje svojim imenom i šifrom; uz svaku promenu piše ko ju je uneo.",
                      "Everyone signs in with their own name and password; every change shows who entered it."),
                 9, fg=INK2, wraplength=440, justify="left").pack(anchor="w", pady=(2, 10))
        spisak = tk.Frame(b, bg=SURF)
        spisak.pack(fill="x")

        def crtaj():
            for w in spisak.winfo_children():
                w.destroy()
            for i, n in enumerate(self.nalozi()):
                self.lbl(spisak, n["ime"] + (T("  (vlasnik)", "  (owner)") if n.get("vlasnik") else ""), 10,
                         "bold" if n.get("vlasnik") else "normal").grid(row=i, column=0, sticky="w", pady=3)
                if not n.get("vlasnik"):
                    self.btn(spisak, T("Nova šifra", "New password"), lambda n=n: nova_sifra(n)).grid(row=i, column=1, padx=(16, 6), pady=3)
                    self.btn(spisak, T("Ukloni", "Remove"), lambda n=n: ukloni(n), "Danger").grid(row=i, column=2, pady=3)

        def nova_sifra(n):
            prozor_sifre(T(f"Nova šifra za: {n['ime']}", f"New password for: {n['ime']}"),
                         lambda s: n.update(novi_nalog(n["ime"], s, False)))

        def ukloni(n):
            if messagebox.askyesno("HerdDoc", T(f"Ukloniti radnika {n['ime']}?\n\nNjegovi upisi ostaju, samo više ne može da se prijavi.",
                                                f"Remove worker {n['ime']}?\n\nTheir entries stay; they just can no longer sign in."), parent=win):
                self.pod["korisnici"] = [x for x in self.nalozi() if x is not n]
                self.sacuvaj_podesavanja()
                crtaj()

        def prozor_sifre(naslov, primeni, ime_polje=False):
            w2, b2 = self._prozor(naslov, False)
            w2.transient(win)
            self.lbl(b2, naslov, 13, "bold").pack(anchor="w")
            f = tk.Frame(b2, bg=SURF)
            f.pack(anchor="w", pady=(10, 0))
            r = 0
            if ime_polje:
                v_ime, e1 = self._polje(f, 0, T("Ime", "First name"))
                v_prez, _ = self._polje(f, 1, T("Prezime", "Last name"))
                r = 2
            v_s1, e_s = self._polje(f, r, T("Šifra", "Password"), sakrij=True)
            v_s2, _ = self._polje(f, r + 1, T("Ponovi šifru", "Repeat password"), sakrij=True)
            gr = self.lbl(b2, "", 9, fg=BAD)
            gr.pack(anchor="w", pady=(6, 0))

            def ok(*_):
                if ime_polje:
                    ime, prez = cisto_ime(v_ime.get()), cisto_ime(v_prez.get())
                    if not ime or not prez:
                        gr.config(text=T("Upiši i ime i prezime.", "Enter both first and last name."))
                        return
                    if self.nalog(f"{ime} {prez}"):
                        gr.config(text=T("Taj radnik već postoji.", "That worker already exists."))
                        return
                g = self._greska_sifre(v_s1.get(), v_s2.get())
                if g:
                    gr.config(text=g)
                    return
                if ime_polje:
                    self.pod.setdefault("korisnici", []).append(novi_nalog(f"{ime} {prez}", v_s1.get()))
                else:
                    primeni(v_s1.get())
                self.sacuvaj_podesavanja()
                w2.destroy()
                crtaj()
                try:
                    win.grab_set()
                except tk.TclError:
                    pass

            d2 = tk.Frame(b2, bg=SURF)
            d2.pack(fill="x", pady=(14, 0))
            self.btn(d2, T("Sačuvaj", "Save"), ok, "Primary").pack(side="right")
            self.btn(d2, T("Otkaži", "Cancel"), w2.destroy).pack(side="right", padx=(0, 8))
            w2.bind("<Return>", ok)
            w2.bind("<Escape>", lambda e: w2.destroy())
            self._na_sredinu(w2)
            (e1 if ime_polje else e_s).focus_set()

        crtaj()
        dno = tk.Frame(b, bg=SURF)
        dno.pack(fill="x", pady=(16, 0))
        self.btn(dno, T("+ Dodaj radnika", "+ Add worker"), lambda: prozor_sifre(T("Novi radnik", "New worker"), None, True), "Primary").pack(side="left")
        self.btn(dno, T("Zatvori", "Close"), win.destroy).pack(side="right")
        win.bind("<Escape>", lambda e: win.destroy())
        self._na_sredinu(win)
