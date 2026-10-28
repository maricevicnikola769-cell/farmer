"""Kopija u oblaku: kad je telefon uparen, program jednom dnevno pošalje šifrovanu kopiju svih podataka
(grla, istorija, podsetnici, finansije, podešavanja) – ključem koji postoji samo kod farmera.
Na novom računaru se podaci vraćaju „ključem za vraćanje“ (isti link kao QR kod za uparivanje)."""
import base64
import json
import os
import threading
import time
import tkinter as tk
import urllib.parse
from datetime import date
from tkinter import messagebox, ttk

import dnevnik
from osnova import EN
from jezik import T
from oblak import Oblak, OblakGreska, link_za_uparivanje, otkljucaj, zakljucaj
from podaci import Istorija, Podsetnici, Tablica, sada
from izgled import BAD, INK2, OK, SURF, WARN


def procitaj_kljuc(tekst):
    """Link/QR za uparivanje ('…#upari=FARMA.KLJUČ.naziv') -> (farma, ključ, naziv) ili None."""
    t = (tekst or "").strip()
    i = t.find("upari=")
    if i < 0:
        return None
    delovi = t[i + 6:].split(".")
    if len(delovi) < 2 or len(delovi[0]) < 16 or len(delovi[1]) < 20:
        return None
    return delovi[0], delovi[1], urllib.parse.unquote(delovi[2]) if len(delovi) > 2 else ""


def napravi_sadrzaj(fajlovi, podesavanja):
    """Sadržaj kopije: tekst svih fajlova podataka i podešavanja."""
    f = {}
    for p in fajlovi:
        with open(p, "rb") as fh:
            f[os.path.basename(p)] = base64.b64encode(fh.read()).decode()
    return dict(format="herddoc-kopija", verzija=1, vreme=sada(), fajlovi=f, podesavanja=podesavanja)


def posalji_kopiju(oblak, kljuc, sadrzaj):
    """Pošalji šifrovanu kopiju i obriši stariju. Vraća oznaku verzije."""
    verzija = f"{int(time.time() * 1000)}"
    ukupno = oblak.upisi_veliko("kopije", verzija, zakljucaj(sadrzaj, kljuc))
    oblak.upisi("stanje", "kopija", dict(verzija=verzija, ukupno=ukupno, vreme=sadrzaj.get("vreme", "")))
    for dok, polja in oblak.lista("kopije"):
        if polja.get("pid") != verzija:
            try:
                oblak.obrisi("kopije", dok)
            except OblakGreska:
                pass
    return verzija


def preuzmi_kopiju(oblak, kljuc):
    """Poslednja kopija iz oblaka; ako je nema, snimak koji računar šalje telefonima (bez finansija)."""
    meta = oblak.citaj("stanje", "kopija")
    if meta and meta.get("verzija"):
        return otkljucaj(oblak.procitaj_veliko("kopije", meta["verzija"], meta.get("ukupno") or 1), kljuc)
    meta = oblak.citaj("stanje", "poslednji")
    if meta and meta.get("verzija"):
        snimak = otkljucaj(oblak.procitaj_veliko("snimci", meta["verzija"], meta.get("ukupno") or 1), kljuc)
        snimak["format"] = "farmer-telefon"
        return snimak
    return None


class OblakKopijaDeo:
    """Kopija u oblaku (jednom dnevno) i vraćanje podataka na novom računaru."""

    def _u_pozadini(self, posao, kraj):
        """Pokreni posao u pozadini; kraj(rezultat, greška) se zove u glavnom delu programa (Tk nije za više niti)."""
        stanje = {}

        def nit():
            try:
                stanje["rez"] = posao()
            except Exception as e:
                dnevnik.zapisi_izuzetak(type(e), e, e.__traceback__, "oblak (kopija)")
                stanje["greska"] = e
            stanje["gotovo"] = True

        def proveri():
            if stanje.get("gotovo"):
                kraj(stanje.get("rez"), stanje.get("greska"))
            else:
                self.root.after(200, proveri)
        threading.Thread(target=nit, daemon=True).start()
        self.root.after(200, proveri)

    def kopija_u_oblak(self, rucno=False):
        if not (self.sinh_podeseno() and self.sinh_upareno()):
            if rucno:
                messagebox.showinfo("HerdDoc", T("Kopija u oblaku radi kad je telefon uparen (strana Telefon → Upari telefon).",
                                                 "The cloud backup works once a phone is paired (Phone page → Pair phone)."))
            return
        if getattr(self, "_oblak_kopija_radi", False):
            return
        try:
            for p in (self.tab, self.ist, self.pods):
                p.sacuvaj()
            if getattr(self, "_fin", None) is not None:
                self._fin.sacuvaj()
        except OSError:
            pass
        s = dict(self.pod["sinh"])
        pod = json.loads(json.dumps(self.pod, default=str))
        try:
            sadrzaj = napravi_sadrzaj(self.fajlovi_podataka(), pod)
        except OSError as e:
            if rucno:
                messagebox.showerror("HerdDoc", str(e))
            return
        self._oblak_kopija_radi = True
        if rucno:
            self.toast(T("☁ Šaljem kopiju u oblak…", "☁ Sending backup to the cloud…"))

        def posao():
            o = Oblak(self.sinh_konfig(), s["farma"], s["kljuc"], s.get("token"))
            return posalji_kopiju(o, s["kljuc"], sadrzaj)

        def kraj(_, greska):
            self._oblak_kopija_radi = False
            if greska is None:
                self.pod["kopija_oblak"] = sada()
                self.sacuvaj_podesavanja()
                if rucno:
                    self.toast(T("☁ Kopija u oblaku je napravljena.", "☁ Cloud backup made."))
            elif rucno:
                messagebox.showerror(T("Kopija u oblaku", "Cloud backup"),
                                     T("Kopija nije poslata:\n", "The backup was not sent:\n") + str(greska))
            if getattr(self, "strana", "") == "pregled" and rucno:
                self.prikazi("pregled")
        self._u_pozadini(posao, kraj)

    def dnevna_kopija_u_oblak(self):
        """Jednom dnevno (posle pokretanja), ako je telefon uparen."""
        if self.sinh_upareno() and self.pod.get("kopija_oblak", "")[:10] != date.today().strftime("%Y-%m-%d"):
            self.kopija_u_oblak()

    def kljuc_za_vracanje(self):
        """Štampa ključa za vraćanje (QR i link) – čuva se na sigurnom mestu."""
        s = self.pod.get("sinh", {})
        if not s.get("farma"):
            messagebox.showinfo("HerdDoc", T("Ključ postoji kad je telefon uparen.", "The key exists once a phone is paired."))
            return
        link = link_za_uparivanje(s["farma"], s["kljuc"], s.get("naziv", ""))
        try:
            import qrcode
            import qrcode.image.svg
            svg = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage, border=2).to_string(encoding="unicode")
        except Exception:
            svg = ""
        from stampa import _html_esc, _otvori_html
        telo = (f"<p><b>{T('Čuvaj ovaj papir na sigurnom mestu, odvojeno od računara.', 'Keep this sheet in a safe place, away from the computer.')}</b> "
                + T("Sa njim vraćaš sve podatke na novi računar (HerdDoc → Pregled → Vrati iz oblaka) ako se ovaj pokvari ili ukrade. "
                    "Ko ima ovaj ključ može da vidi podatke stada – ne pokazuj ga drugima.",
                    "With it you restore all data on a new computer (HerdDoc → Overview → Restore from cloud) if this one breaks or is stolen. "
                    "Anyone with this key can see the herd data – do not show it to others.") + "</p>"
                + (f"<div style='width:260px;margin:18px 0'>{svg}</div>" if svg else "")
                + f"<h2>{T('Ključ (link)', 'Key (link)')}</h2><p style='word-break:break-all;font-family:monospace;font-size:12px'>{_html_esc(link)}</p>"
                + f"<p style='color:#9A5C00'>{T('Ako isključiš neki telefon, ključ se menja – tada odštampaj novi.', 'If you disconnect a phone the key changes – print a new one then.')}</p>")
        _otvori_html("kljuc-za-vracanje", T("Ključ za vraćanje podataka", "Data recovery key"), s.get("naziv", "") or "HerdDoc", telo)

    def vrati_iz_oblaka(self):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Vraćanje iz oblaka", "Restore from cloud"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Vraćanje podataka iz oblaka", "Restore data from the cloud"), 16, "bold").pack(anchor="w")
        self.lbl(b, T("Nalepi ključ za vraćanje: link sa odštampanog ključa, ili sa telefona (HerdDoc na telefonu → Više → "
                      "Povezano sa računarom → Ključ za vraćanje).",
                      "Paste the recovery key: the link from the printed key, or from the phone (HerdDoc on the phone → More → "
                      "Connected to computer → Recovery key)."), 9, fg=INK2, wraplength=470, justify="left").pack(anchor="w", pady=(4, 10))
        kv = tk.StringVar()
        e = ttk.Entry(b, textvariable=kv, width=60, font=self.f(10))
        e.pack(fill="x")
        stanje = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=470, justify="left")
        stanje.pack(anchor="w", pady=(8, 0))
        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))

        def preuzmi():
            k = procitaj_kljuc(kv.get())
            if not k:
                stanje.config(text=T("Ovo nije ispravan ključ (treba da sadrži „upari=“).", "This is not a valid key (it should contain “upari=”)."), fg=BAD)
                return
            stanje.config(text=T("☁ Preuzimam…", "☁ Downloading…"), fg=INK2)
            farma, kljuc, naziv = k

            def posao():
                return preuzmi_kopiju(Oblak(self.sinh_konfig(), farma, kljuc), kljuc)

            def gotovo(sadrzaj, greska):
                if not win.winfo_exists():
                    return
                if greska is not None or not sadrzaj:
                    stanje.config(text=(T("Preuzimanje nije uspelo: ", "Download failed: ") + str(greska)) if greska
                                  else T("U oblaku nema kopije za ovaj ključ.", "There is no backup in the cloud for this key."), fg=BAD)
                    return
                self.primeni_kopiju_iz_oblaka(sadrzaj, farma, kljuc, naziv, win)
            self._u_pozadini(posao, gotovo)
        self.btn(fb, T("Preuzmi i vrati", "Download and restore"), preuzmi, "Primary").pack(side="right")
        self.btn(fb, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        self.postavi_prozor(win, self.root)
        e.focus_set()

    def primeni_kopiju_iz_oblaka(self, sadrzaj, farma, kljuc, naziv, win=None):
        """Upiši preuzetu kopiju u folder sa podacima (pre toga ručna kopija trenutnih podataka)."""
        puna = sadrzaj.get("format") == "herddoc-kopija"
        n = 0
        if puna:
            ime_tab = os.path.basename((sadrzaj.get("podesavanja") or {}).get("tablica", "")) or os.path.basename(self.tab.putanja)
            kad = sadrzaj.get("vreme", "")
        else:
            n = len(sadrzaj.get("grla", []))
            kad = sadrzaj.get("izvezeno", "")
        opis = T(f"Kopija iz oblaka od {kad}", f"Cloud backup of {kad}") + ("" if puna else
               T(f" ({n} grla, bez finansija – to je kopija koju dobijaju telefoni)", f" ({n} animals, without finances – the copy phones receive)"))
        if not messagebox.askyesno(T("Vraćanje iz oblaka", "Restore from cloud"),
                                   opis + T("\n\nVratiti ove podatke? Trenutni podaci na ovom računaru biće prvo sačuvani kao ručna kopija.",
                                            "\n\nRestore this data? The current data on this computer will first be saved as a manual backup."),
                                   parent=win):
            return
        if self.tab.redovi:
            self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0], time.strftime("%Y-%m-%d_%H-%M-%S") + T("_pre_oblaka", "_before_cloud"), tiho=False)
        folder = os.path.dirname(os.path.abspath(self.tab.putanja))
        try:
            if puna:
                for ime, b64 in sadrzaj.get("fajlovi", {}).items():
                    ime = os.path.basename(ime)
                    if not ime.lower().endswith(".csv"):
                        continue
                    with open(os.path.join(folder, ime), "wb") as f:
                        f.write(base64.b64decode(b64))
                staro = sadrzaj.get("podesavanja") or {}
                for k, v in staro.items():          # podešavanja sa starog računara, osim putanja
                    if k not in ("tablica", "kopija2", "poslednja_kopija", "poslednja_kopija2"):
                        self.pod[k] = v
                self.pod["tablica"] = os.path.join(folder, ime_tab)
                self.tab = Tablica(self.pod["tablica"])
            else:
                self.tab.redovi = [dict(r) for r in sadrzaj.get("grla", [])]
                self.tab.sacuvaj()
                self.ist = Istorija(self.tab.putanja)
                self.ist.zapisi = [dict(z) for z in sadrzaj.get("istorija", [])]
                self.ist.sacuvaj()
                self.pods = Podsetnici(self.tab.putanja)
                self.pods.zapisi = [dict(z) for z in sadrzaj.get("podsetnici", [])]
                self.pods.sacuvaj()
                sinh = dict(self.pod.get("sinh", {}))
                sinh.update(farma=farma, kljuc=kljuc, naziv=naziv or sinh.get("naziv", ""))
                self.pod["sinh"] = sinh
            self.ist = Istorija(self.tab.putanja)
            self.pods = Podsetnici(self.tab.putanja)
            self._fin = None
        except Exception as e:
            messagebox.showerror(T("Vraćanje nije uspelo", "Restore failed"), str(e), parent=win)
            return
        from rodoslov import Model
        self.model = Model(self.tab.redovi)
        self.sacuvaj_podesavanja()
        if win is not None and win.winfo_exists():
            win.grab_release()
            win.destroy()
        if hasattr(self, "osvezi_fajl_label"):
            self.osvezi_fajl_label()
        self.prikazi(self.strana)
        self.toast(T(f"Vraćeno iz oblaka: {len(self.tab.redovi)} grla.", f"Restored from the cloud: {len(self.tab.redovi)} animals."))

    def kartica_oblaka(self, c):
        """Odeljak „Kopija u oblaku“ u kartici rezervnih kopija (strana Pregled)."""
        tk.Frame(c, bg="#E3E8E1", height=1).pack(fill="x", pady=(14, 10))
        self.lbl(c, T("☁ Kopija u oblaku", "☁ Cloud backup"), 11, "bold").pack(anchor="w")
        if self.sinh_upareno():
            kad = self._kad(self.pod.get("kopija_oblak", "")) or T("još nije", "not yet")
            tekst, boja = T(f"✓ Jednom dnevno se šalje šifrovana kopija svih podataka. Poslednja: {kad}. Odštampaj ključ za vraćanje i čuvaj ga.",
                            f"✓ An encrypted copy of all data is sent once a day. Last: {kad}. Print the recovery key and keep it safe."), OK
        else:
            tekst, boja = T("Kopija u oblaku se uključuje sama kad upariš telefon (strana Telefon). Šifrovana je – niko osim tebe ne može da je pročita.",
                            "The cloud backup turns on by itself when you pair a phone (Phone page). It is encrypted – nobody but you can read it."), INK2
        self.lbl(c, tekst, 9, fg=boja, wraplength=620, justify="left").pack(anchor="w", pady=(2, 0))
        dd = tk.Frame(c, bg=SURF)
        dd.pack(fill="x", pady=(8, 0))
        if self.sinh_upareno():
            self.btn(dd, T("Pošalji kopiju sada", "Send backup now"), lambda: self.kopija_u_oblak(rucno=True)).pack(side="left")
            self.btn(dd, T("Ključ za vraćanje (štampa)", "Recovery key (print)"), self.kljuc_za_vracanje).pack(side="left", padx=8)
        self.btn(dd, T("Vrati iz oblaka…", "Restore from cloud…"), self.vrati_iz_oblaka).pack(side="left")
