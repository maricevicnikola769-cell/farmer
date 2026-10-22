"""Usklađivanje sa telefonom preko interneta: uparivanje QR kodom i automatsko slanje/primanje (na svaki minut).
Mreža radi u pozadini (program se ne zamrzava); podaci se menjaju samo u glavnom delu programa."""
import hashlib
import sys
import traceback
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
from oblak import Oblak, OblakGreska, link_za_uparivanje, novo_gazdinstvo, omotaj_za
from oblak_konfig import FIREBASE
import dnevnik
from telefon_prenos import _kljuc_ist, _kljuc_pod, spoji_razlike

INTERVAL_MS = 60_000          # dok se nešto dešava; kad je mirno, ređe (štedi besplatnu kvotu servera)


def razmak_ms(mirno):
    return INTERVAL_MS if mirno < 5 else 3 * INTERVAL_MS if mirno < 15 else 5 * INTERVAL_MS


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
        self._sinh_iskljuci = None                   # telefon koji treba isključiti u sledećem krugu
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
                    dnevnik.zapisi_izuzetak(*sys.exc_info(), gde="usklađivanje (glavni deo)")
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
            self.root.after(razmak_ms(getattr(self, "_sinh_mirno", 0)), self._sinh_tik)
        except tk.TclError:
            pass

    def sinh_uskoro(self):
        """Posle promene na računaru: pošalji za par sekundi (više izmena odjednom ide u jednom slanju)."""
        if not self.sinh_upareno():
            return
        self._sinh_mirno = 0
        if getattr(self, "_sinh_odlozeno", None):
            try:
                self.root.after_cancel(self._sinh_odlozeno)
            except tk.TclError:
                pass
        self._sinh_odlozeno = self.root.after(5000, lambda: (setattr(self, "_sinh_odlozeno", None), self.usaglasi()))

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
        if rucno:
            self._sinh_mirno = 0
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
                                          self.pod.get("gravidnost2", {}), self.spisak_telefona_za_snimak()],
                                         ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    # ---------------------------------------------------------- spisak uparenih telefona
    def telefoni(self):
        return self.pod.setdefault("sinh", {}).setdefault("telefoni", {})

    def spisak_telefona_za_snimak(self):
        return {tid: v.get("ime", "") for tid, v in self.pod.get("sinh", {}).get("telefoni", {}).items()}

    def _zapamti_telefon(self, sadrzaj):
        tel = sadrzaj.get("tel") or {}
        tid = str(tel.get("tid") or "")
        if not tid:
            return                                   # telefon sa starijom verzijom aplikacije
        j = tel.get("javni") or {}
        v = self.telefoni().setdefault(tid, {})
        v["ime"] = str(tel.get("ime") or v.get("ime") or T("Telefon", "Phone"))[:40]
        if j.get("x") and j.get("y"):
            v["javni"] = {"x": str(j["x"]), "y": str(j["y"])}
        v["vidjen"] = max(v.get("vidjen", ""), str(sadrzaj.get("napravljeno") or ""))

    def _primeni_paket(self, sadrzaj):
        tid = str((sadrzaj.get("tel") or {}).get("tid") or "")
        if tid and tid in self.pod.get("sinh", {}).get("iskljuceni", []):
            return 0                                 # isključen telefon – ne prima se ništa od njega
        r = sadrzaj.get("razlike", {})
        kol_g = list(dict.fromkeys(KOLONE + [k for x in r.get("grla", []) for k in (x.get("t") or {})]))
        g, sg = spoji_razlike(r.get("grla", []), self.tab.redovi, lambda x: x.get("id", ""), kol_g)
        i, si = spoji_razlike(r.get("istorija", []), self.ist.zapisi, _kljuc_ist, IST_KOLONE)
        p, sp = spoji_razlike(r.get("podsetnici", []), self.pods.zapisi, _kljuc_pod, Podsetnici.KOLONE)
        Model(g)                                     # provera pre nego što se išta promeni
        self.tab.dodatne = list(dict.fromkeys(self.tab.dodatne + [k for x in g for k in x if k not in KOLONE]))
        self.tab.redovi, self.ist.zapisi, self.pods.zapisi = g, i, p
        self._zapamti_telefon(sadrzaj)
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
        tid = self._sinh_iskljuci
        if tid:                                      # isključivanje jednog telefona: sve prelazi na novi ključ
            self._sinh_iskljuci = None
            ostali = {t: dict(v) for t, v in self.telefoni().items() if t != tid}
            snimak = dict(self.paket_za_telefon(), telefoni={t: v.get("ime", "") for t, v in ostali.items()})
            threading.Thread(target=self._sinh_rotiraj, args=(o, s, snimak, primljeno, broj, tid, ostali), daemon=True).start()
            return
        hes = self._sinh_hes()
        snimak = dict(self.paket_za_telefon(), telefoni=self.spisak_telefona_za_snimak()) \
            if (hes != s.get("hes") or primljeno or not s.get("verzija")) else None
        threading.Thread(target=self._sinh_posalji, args=(o, s, snimak, hes, primljeno, broj), daemon=True).start()

    def _sinh_posalji(self, o, s, snimak, hes, primljeno, broj):   # u pozadini
        try:
            verzija = s.get("verzija")
            if snimak is not None:
                verzija = o.posalji_snimak(snimak, s.get("verzija"))
            for dok in primljeno:                    # paketi se brišu tek kad je snimak sa njima poslat
                o.obrisi_paket(dok)
            self._sinh_red.put((self._sinh_kraj, (o, verzija, hes, broj, snimak is not None)))
        except Exception as e:
            self._sinh_red.put((self._sinh_kraj_greska, (e,)))

    def _sinh_rotiraj(self, o, s, snimak, primljeno, broj, tid, ostali):   # u pozadini
        """Novo gazdinstvo (nova oznaka i ključ); preostalim telefonima se javlja nova adresa, zaključana
        posebno za svaki telefon – isključeni telefon zna samo stari ključ i ne može da je pročita."""
        try:
            farma2, kljuc2 = novo_gazdinstvo()
            o2 = Oblak(self.sinh_konfig(), farma2, kljuc2, o.token)
            verzija = o2.posalji_snimak(snimak)
            nova = dict(farma=farma2, kljuc=kljuc2, naziv=s.get("naziv", ""))
            for t, v in ostali.items():
                if v.get("javni"):
                    o.upisi("rotacija", t, omotaj_za(v["javni"], nova))
            o.upisi("stanje", "poslednji", dict(premesteno="1", vreme=time.strftime("%Y-%m-%d %H:%M:%S")))
            for dok in primljeno:
                o.obrisi_paket(dok)
            for dok, _ in o.lista("snimci"):         # stari podaci se brišu sa servera
                try:
                    o.obrisi("snimci", dok)
                except OblakGreska:
                    pass
            self._sinh_red.put((self._sinh_kraj_rotacija, (o2, farma2, kljuc2, verzija, broj, tid)))
        except Exception as e:
            self._sinh_red.put((self._sinh_kraj_greska, (e,)))

    def _sinh_kraj_rotacija(self, o2, farma2, kljuc2, verzija, broj, tid):
        sinh = self.pod.setdefault("sinh", {})
        ime = self.telefoni().pop(tid, {}).get("ime", "")
        bez_kljuca = [v.get("ime", "") for v in self.telefoni().values() if not v.get("javni")]
        for t in [t for t, v in self.telefoni().items() if not v.get("javni")]:
            self.telefoni().pop(t)
        sinh["iskljuceni"] = (sinh.get("iskljuceni", []) + [tid])[-50:]
        sinh.update(farma=farma2, kljuc=kljuc2)
        self._sinh_kraj(o2, verzija, self._sinh_hes(), broj)
        self.toast(T(f"Telefon „{ime}“ je isključen. Ostali telefoni sami prelaze na novi ključ.",
                     f"Phone „{ime}“ disconnected. Other phones switch to the new key by themselves."))
        if bez_kljuca:
            messagebox.showinfo("Farmer", T("Ovi telefoni imaju stariju aplikaciju i moraju ponovo da se upare: ",
                                            "These phones have an older app and must be paired again: ") + ", ".join(bez_kljuca))
        if self.strana == "telefon":
            self.prikazi("telefon")

    def iskljuci_telefon(self, tid):
        ime = self.telefoni().get(tid, {}).get("ime", "?")
        if not messagebox.askyesno(T("Isključi telefon", "Disconnect phone"),
                                   T(f"Isključiti telefon „{ime}“?\n\nOn više neće moći da šalje ni prima podatke. Podaci koje je do sada "
                                     "poslao ostaju. Ostali telefoni sa spiska sami prelaze na novi ključ – ne moraš ništa da radiš na njima.\n\n"
                                     "(Telefon koji nije na spisku moraće ponovo da se upari.)",
                                     f"Disconnect phone „{ime}“?\n\nIt will no longer send or receive data. Data it already sent stays. "
                                     "Other listed phones switch to the new key by themselves.\n\n(A phone not on the list must be paired again.)")):
            return
        if self._sinh_radi:
            messagebox.showinfo("Farmer", T("Usklađivanje je u toku – pokušaj ponovo za par sekundi.", "Sync in progress – try again in a few seconds."))
            return
        self._sinh_iskljuci = tid
        self.usaglasi()

    def _sinh_kraj(self, o, verzija, hes, broj, poslato=True):
        self._sinh_radi = False
        self._sinh_mirno = 0 if (broj or poslato) else getattr(self, "_sinh_mirno", 0) + 1
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
            dnevnik.zapisi("usklađivanje", "".join(traceback.format_exception(type(e), e, e.__traceback__)))
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
        stari = dict(self.pod.get("sinh", {}))
        self.pod["sinh"] = {"naziv": stari.get("naziv", "")}
        self.sacuvaj_podesavanja()
        if stari.get("farma") and stari.get("kljuc"):          # telefonima javi da su isključeni, a podatke skloni sa servera
            def obavesti():
                try:
                    o = Oblak(self.sinh_konfig(), stari["farma"], stari["kljuc"], stari.get("token"))
                    o.upisi("stanje", "poslednji", dict(premesteno="1", vreme=time.strftime("%Y-%m-%d %H:%M:%S")))
                    for dok, _ in o.lista("snimci"):
                        o.obrisi("snimci", dok)
                except Exception:
                    pass
            threading.Thread(target=obavesti, daemon=True).start()
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
            self.spisak_telefona(c)
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

    def spisak_telefona(self, c):
        tel = self.pod.get("sinh", {}).get("telefoni", {})
        fr = tk.Frame(c, bg=SURF)
        fr.pack(fill="x", pady=(10, 0))
        self.lbl(fr, T("Upareni telefoni", "Paired phones"), 10, "bold").pack(anchor="w")
        if not tel:
            self.lbl(fr, T("Telefoni se pojavljuju ovde posle prvog usklađivanja (telefon sa starijom aplikacijom – osveži aplikaciju).",
                           "Phones appear here after their first sync (older phone app – refresh it)."), 9, fg=INK2,
                     wraplength=520, justify="left").pack(anchor="w")
            return
        for tid, v in sorted(tel.items(), key=lambda x: x[1].get("ime", "").lower()):
            r = tk.Frame(fr, bg=SURF)
            r.pack(fill="x", pady=2)
            self.lbl(r, "📱 " + (v.get("ime") or "?"), 10, "bold").pack(side="left")
            self.lbl(r, T("  poslednje slanje: ", "  last sent: ") + (v.get("vidjen") or "–")[:16], 9, fg=INK2).pack(side="left")
            self.btn(r, T("Isključi", "Disconnect"), lambda t=tid: self.iskljuci_telefon(t), "Danger").pack(side="right")
