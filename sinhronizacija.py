"""Usklađivanje sa telefonom preko interneta: uparivanje QR kodom i automatsko slanje/primanje (na svaki minut).
Mreža radi u pozadini (program se ne zamrzava); podaci se menjaju samo u glavnom delu programa."""
import hashlib
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox

from osnova import EN
from jezik import T
from podaci import IST_KOLONE, KOLONE, Podsetnici
from izgled import BAD, INK2, OK, SURF, WARN
from rodoslov import Model
from oblak import Oblak, OblakGreska, link_za_uparivanje, novo_gazdinstvo
from oblak_konfig import FIREBASE
from telefon_prenos import _kljuc_ist, _kljuc_pod, spoji_razlike

INTERVAL_MS = 60_000


class SinhronizacijaDeo:
    """Uparivanje telefona QR kodom i automatsko usklađivanje."""

    # ---------------------------------------------------------- stanje
    def sinh_podeseno(self):
        return Oblak.podeseno(self.sinh_konfig())

    def sinh_konfig(self):
        return dict(FIREBASE, **self.pod.get("oblak_test", {}))    # oblak_test: samo za testove (lažni server)

    def sinh_upareno(self):
        return bool(self.pod.get("sinh", {}).get("farma"))

    def pokreni_sinhronizaciju(self):
        self._sinh_red = queue.Queue()
        self._sinh_radi = False
        self.sinh_stanje = dict(tekst="", boja=INK2, vreme="")
        self.root.after(200, self._sinh_red_proveri)
        self.root.after(1500, self._sinh_tik)

    def _sinh_red_proveri(self):
        try:
            while True:
                fn, args = self._sinh_red.get_nowait()
                try:
                    fn(*args)
                except Exception as e:           # greška ne sme da zaustavi program
                    self._sinh_kraj_greska(e)
        except queue.Empty:
            pass
        try:
            self.root.after(200, self._sinh_red_proveri)
        except tk.TclError:
            pass

    def _sinh_tik(self):
        self.usaglasi()
        try:
            self.root.after(INTERVAL_MS, self._sinh_tik)
        except tk.TclError:
            pass

    def sinh_status(self, tekst, boja=INK2):
        self.sinh_stanje = dict(tekst=tekst, boja=boja, vreme=time.strftime("%H:%M"))
        for w in (getattr(self, "lbl_sinh", None), getattr(self, "lbl_sinh_strana", None)):
            try:
                if w is not None and w.winfo_exists():
                    w.config(text=tekst, fg=boja)
            except tk.TclError:
                pass

    # ---------------------------------------------------------- jedan krug usklađivanja
    def usaglasi(self, rucno=False):
        if not self.sinh_podeseno() or not self.sinh_upareno():
            if rucno:
                messagebox.showinfo("Farmer", T("Prvo upari telefon (strana Telefon → Upari telefon).", "Pair a phone first (Phone page → Pair phone)."))
            return
        if self._sinh_radi:
            return
        self._sinh_radi = True
        self.sinh_status(T("☁ Usklađujem…", "☁ Syncing…"))
        s = dict(self.pod["sinh"])
        threading.Thread(target=self._sinh_preuzmi, args=(s,), daemon=True).start()

    def _sinh_preuzmi(self, s):                       # u pozadini
        try:
            o = Oblak(self.sinh_konfig(), s["farma"], s["kljuc"], s.get("token"))
            paketi = o.paketi()
            self._sinh_red.put((self._sinh_spoji, (o, s, paketi)))
        except Exception as e:
            self._sinh_red.put((self._sinh_kraj_greska, (e,)))

    def _sinh_hes(self):
        return hashlib.sha256(json.dumps([self.tab.redovi, self.ist.zapisi, self.pods.zapisi, self.prag, EN,
                                          self.pod.get("gravidnost2", {})], ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    def _primeni_paket(self, sadrzaj):
        r = sadrzaj.get("razlike", {})
        kol_g = list(dict.fromkeys(KOLONE + [k for x in r.get("grla", []) for k in (x.get("t") or {})]))
        g, sg = spoji_razlike(r.get("grla", []), self.tab.redovi, lambda x: x.get("id", ""), kol_g)
        i, si = spoji_razlike(r.get("istorija", []), self.ist.zapisi, _kljuc_ist, IST_KOLONE)
        p, sp = spoji_razlike(r.get("podsetnici", []), self.pods.zapisi, _kljuc_pod, Podsetnici.KOLONE)
        Model(g)                                     # provera pre nego što se išta promeni
        self.tab.dodatne = list(dict.fromkeys(self.tab.dodatne + [k for x in g for k in x if k not in KOLONE]))
        self.tab.redovi, self.ist.zapisi, self.pods.zapisi = g, i, p
        return len(sadrzaj.get("promene", [])) or sum(s["sa_telefona"] for s in (sg, si, sp))

    def _sinh_spoji(self, o, s, paketi):             # glavni deo programa
        primljeno, broj = [], 0
        if paketi:
            self.napravi_kopiju("automatic" if EN else "automatske", time.strftime("%Y-%m-%d_%H-%M-%S") + T("_pre_telefona", "_before_phone"))
        for pid, sadrzaj, dok in paketi:
            try:
                broj += self._primeni_paket(sadrzaj)
                primljeno.append(dok)
            except Exception as e:
                self.sinh_status(T(f"☁ Paket sa telefona nije mogao da se primeni: {e}", f"☁ A phone package could not be applied: {e}"), BAD)
        if primljeno:
            self.promena(T(f"Sa telefona: {broj} promena", f"From the phone: {broj} changes"))
        hes = self._sinh_hes()
        snimak = self.paket_za_telefon() if (hes != s.get("hes") or primljeno or not s.get("verzija")) else None
        threading.Thread(target=self._sinh_posalji, args=(o, s, snimak, hes, primljeno, broj), daemon=True).start()

    def _sinh_posalji(self, o, s, snimak, hes, primljeno, broj):   # u pozadini
        try:
            verzija = s.get("verzija")
            if snimak is not None:
                verzija = o.posalji_snimak(snimak, s.get("verzija"))
            for dok in primljeno:                    # paketi se brišu tek kad je snimak sa njima poslat
                o.obrisi_paket(dok)
            self._sinh_red.put((self._sinh_kraj, (o, verzija, hes, broj)))
        except Exception as e:
            self._sinh_red.put((self._sinh_kraj_greska, (e,)))

    def _sinh_kraj(self, o, verzija, hes, broj):
        self._sinh_radi = False
        sinh = self.pod.setdefault("sinh", {})
        sinh.update(verzija=verzija, hes=hes, token=o.token, poslednje=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.sacuvaj_podesavanja()
        self.sinh_status(T(f"☁ Usklađeno u {time.strftime('%H:%M')}", f"☁ Synced at {time.strftime('%H:%M')}"), OK)
        if broj and self.strana == "telefon":
            self.prikazi("telefon")

    def _sinh_kraj_greska(self, e):
        self._sinh_radi = False
        if isinstance(e, OblakGreska) and e.bez_mreze:
            self.sinh_status(T("☁ Nema interneta – pokušaću ponovo", "☁ No internet – will retry"), WARN)
        else:
            self.sinh_status(T("☁ Greška: ", "☁ Error: ") + str(e)[:120], BAD)

    # ---------------------------------------------------------- uparivanje
    def upari_telefon(self):
        if not self.sinh_podeseno():
            messagebox.showinfo("Farmer", T("Usklađivanje preko interneta još nije podešeno u ovoj verziji programa.",
                                            "Internet sync is not configured in this version of the program."))
            return
        sinh = self.pod.setdefault("sinh", {})
        if not sinh.get("farma"):
            sinh["farma"], sinh["kljuc"] = novo_gazdinstvo()
            sinh.pop("verzija", None)
            sinh.pop("hes", None)
        sinh.setdefault("naziv", self.pod.get("gazdinstvo", ""))
        self.sacuvaj_podesavanja()
        self.usaglasi()                              # da telefon odmah nađe podatke
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Upari telefon", "Pair phone"))
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Upari telefon", "Pair phone"), 16, "bold").pack(anchor="w")
        self.lbl(b, T("Na telefonu otvori Farmer → Više → Upari sa računarom i skeniraj ovaj kod.\n"
                      "(Može i običnom kamerom telefona – otvoriće se Farmer.) Uparuje se samo jednom.",
                      "On the phone open Farmer → More → Pair with computer and scan this code.\n"
                      "(The normal phone camera works too – Farmer opens.) You pair only once."),
                 9, fg=INK2, justify="left", wraplength=440).pack(anchor="w", pady=(4, 10))
        red = tk.Frame(b, bg=SURF)
        red.pack(fill="x", pady=(0, 8))
        self.lbl(red, T("Naziv gazdinstva:", "Farm name:"), 9, "bold", fg=INK2).pack(side="left")
        naziv = tk.StringVar(value=sinh.get("naziv", ""))
        e = tk.Entry(red, textvariable=naziv, font=self.f(10), width=28)
        e.pack(side="left", padx=8)
        platno = tk.Canvas(b, width=300, height=300, bg="white", highlightthickness=0)
        platno.pack(pady=6)

        def crtaj(*_):
            sinh["naziv"] = naziv.get().strip()
            self.pod["gazdinstvo"] = sinh["naziv"]
            link = link_za_uparivanje(sinh["farma"], sinh["kljuc"], sinh["naziv"])
            platno.delete("all")
            try:
                import qrcode
                q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
                q.add_data(link)
                q.make(fit=True)
                m = q.get_matrix()
                k = 300 // len(m)
                p0 = (300 - k * len(m)) // 2
                for y, r in enumerate(m):
                    for x, c in enumerate(r):
                        if c:
                            platno.create_rectangle(p0 + x * k, p0 + y * k, p0 + (x + 1) * k, p0 + (y + 1) * k, fill="#18221C", width=0)
            except ImportError:
                platno.create_text(150, 150, text=T("QR kod nije dostupan –\nkoristi „Kopiraj link“", "QR code unavailable –\nuse \"Copy link\""))
            win.link = link
        naziv.trace_add("write", crtaj)
        crtaj()
        self.lbl(b, T("Ovaj kod je ključ tvog gazdinstva – ne šalji ga drugima.", "This code is your farm's key – do not share it."),
                 8, fg=BAD).pack(anchor="w", pady=(4, 0))
        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(14, 0))

        def gotovo():
            self.sacuvaj_podesavanja()
            win.destroy()
            if self.strana == "telefon":
                self.prikazi("telefon")
        self.btn(fb, T("Gotovo", "Done"), gotovo, "Primary").pack(side="right")
        self.btn(fb, T("Kopiraj link", "Copy link"), lambda: (self.root.clipboard_clear(), self.root.clipboard_append(win.link),
                                                            self.toast(T("Link je kopiran – pošalji ga SAMO sebi (npr. Viber → Moje beleške).",
                                                                         "Link copied – send it ONLY to yourself.")))).pack(side="left")
        win.protocol("WM_DELETE_WINDOW", gotovo)
        self.postavi_prozor(win, None)

    def iskljuci_telefone(self):
        if not messagebox.askyesno(T("Isključi sve telefone", "Disconnect all phones"),
                                   T("Svi upareni telefoni prestaju da se usklađuju sa ovim računarom.\n"
                                     "Telefone koje i dalje koristiš moraš ponovo da upariš.\n\nNastaviti?",
                                     "All paired phones stop syncing with this computer.\nPhones you still use must be paired again.\n\nContinue?")):
            return
        self.pod["sinh"] = {"naziv": self.pod.get("sinh", {}).get("naziv", "")}
        self.sacuvaj_podesavanja()
        self.sinh_status(T("☁ Telefoni su isključeni", "☁ Phones disconnected"), WARN)
        if self.strana == "telefon":
            self.prikazi("telefon")

    def kartica_sinhronizacije(self, body):
        o, c = self.card(body)
        o.pack(fill="x", pady=(0, 12))
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        lev = tk.Frame(red, bg=SURF)
        lev.pack(side="left", fill="x", expand=True)
        self.lbl(lev, T("☁ Automatsko usklađivanje preko interneta", "☁ Automatic sync over the internet"), 12, "bold").pack(anchor="w")
        if not self.sinh_podeseno():
            self.lbl(lev, T("Biće dostupno u sledećoj verziji programa.", "Will be available in the next version."), 9, fg=INK2).pack(anchor="w")
            return
        if self.sinh_upareno():
            self.lbl(lev, T("Telefon i računar se sami usklađuju na svaki minut dok je program otvoren. "
                            "Telefon šalje promene čim uhvati internet.",
                            "Phone and computer sync by themselves every minute while the program is open. "
                            "The phone sends changes as soon as it has internet."), 9, fg=INK2, justify="left", wraplength=520).pack(anchor="w", pady=(2, 4))
            st = self.sinh_stanje if getattr(self, "sinh_stanje", None) else dict(tekst="", boja=INK2)
            self.lbl_sinh_strana = self.lbl(lev, st["tekst"] or T("☁ čeka prvo usklađivanje", "☁ waiting for first sync"), 10, "bold", fg=st["boja"])
            self.lbl_sinh_strana.pack(anchor="w")
            dd = tk.Frame(c, bg=SURF)
            dd.pack(fill="x", pady=(10, 0))
            self.btn(dd, T("🔄 Usaglasi sada", "🔄 Sync now"), lambda: self.usaglasi(True), "Primary").pack(side="left")
            self.btn(dd, T("📱 Upari još jedan telefon", "📱 Pair another phone"), self.upari_telefon).pack(side="left", padx=8)
            self.btn(dd, T("Isključi sve telefone", "Disconnect all phones"), self.iskljuci_telefone, "Danger").pack(side="right")
        else:
            self.lbl(lev, T("Upari telefon jednom (skeniraš QR kod) i posle se podaci sami šalju u oba smera – bez fajlova i Vibera. "
                            "Podaci su zaključani ključem koji znaju samo tvoj računar i tvoj telefon.",
                            "Pair a phone once (scan a QR code) and data then flows both ways by itself – no files. "
                            "Data is locked with a key known only to your computer and your phone."), 9, fg=INK2, justify="left", wraplength=520).pack(anchor="w", pady=(2, 0))
            self.btn(red, T("📱 Upari telefon", "📱 Pair phone"), self.upari_telefon, "Primary").pack(side="right", padx=(16, 0))
