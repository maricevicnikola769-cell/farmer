"""Rezervne kopije: dnevne kopije, druga lokacija (OneDrive, Google Drive, USB), vraćanje iz kopije."""
import os
import shutil
import sys
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox

from osnova import EN
from jezik import T
from podaci import Istorija, Podsetnici, Tablica, sada
from izgled import INK2, OK, SURF, WARN
from rodoslov import Model


class KopijeDeo:
    """Rezervne kopije: dnevne kopije, druga lokacija (OneDrive, Google Drive, USB), vraćanje iz kopije."""


    # ================================================================ REZERVNE KOPIJE
    # Imena foldera postoje na oba jezika: kopije napravljene na jednom jeziku vide se i na drugom.
    _KOREN = ("rezervne_kopije", "backups")

    _KOREN2 = ("Farmer – kopije", "Farmer – backups")

    _AUTO = ("automatske", "automatic")

    _RUCNE = ("rucne", "manual")

    _PRATECI = ("_istorija.csv", "_history.csv", "_podsetnici.csv", "_reminders.csv")


    @staticmethod
    def _postojeci(osnova, imena):
        """Postojeći podfolder na bilo kom jeziku, inače ime na trenutnom jeziku."""
        for ime in imena:
            if os.path.isdir(os.path.join(osnova, ime)):
                return os.path.join(osnova, ime)
        return os.path.join(osnova, imena[1] if EN else imena[0])


    # ---------------------------------------------- druga lokacija (USB, OneDrive, Google Drive)
    @staticmethod
    def _diskovi():
        """Windows: [(slovo, tip, oznaka, serijski)]; tip 2 = USB/prenosivi."""
        rez = []
        try:
            import ctypes
            k = ctypes.windll.kernel32
            maska = k.GetLogicalDrives()
            for i in range(26):
                if not maska >> i & 1:
                    continue
                d = f"{chr(65 + i)}:\\"
                tip = k.GetDriveTypeW(d)
                if tip not in (2, 3, 4):          # prenosivi, lokalni, mrežni
                    continue
                ime = ctypes.create_unicode_buffer(261)
                ser = ctypes.c_ulong(0)
                ok = k.GetVolumeInformationW(d, ime, 261, ctypes.byref(ser), None, None, None, 0)
                rez.append((d, tip, ime.value if ok else "", ser.value if ok else 0))
        except Exception:
            pass
        return rez


    def _serijski(self, putanja):
        d = os.path.splitdrive(os.path.abspath(putanja))[0].upper() + "\\"
        for slovo, _, _, ser in self._diskovi():
            if slovo == d:
                return ser
        return 0


    def predlozi_lokacije(self):
        """Pronađeni OneDrive, Google Drive, Dropbox i USB diskovi: [(naziv, folder)]."""
        rez, home = [], os.path.expanduser("~")

        def dodaj(naziv, p):
            if p and os.path.isdir(p) and os.path.normcase(p) not in [os.path.normcase(x[1]) for x in rez]:
                rez.append((naziv, p))
        for env in ("OneDriveConsumer", "OneDriveCommercial", "OneDrive"):
            dodaj("OneDrive", os.environ.get(env, ""))
        dodaj("OneDrive", os.path.join(home, "OneDrive"))
        diskovi = self._diskovi()
        for slovo, tip, oznaka, _ in diskovi:
            if "google" in oznaka.lower():
                try:
                    for ime in sorted(os.listdir(slovo)):
                        if os.path.isdir(os.path.join(slovo, ime)) and not ime.startswith((".", "$")):
                            dodaj("Google Drive", os.path.join(slovo, ime))
                            break
                except OSError:
                    pass
        for ime in ("Google Drive", "My Drive", "GoogleDrive"):
            dodaj("Google Drive", os.path.join(home, ime))
        dodaj("Dropbox", os.path.join(home, "Dropbox"))
        for slovo, tip, oznaka, _ in diskovi:
            if tip == 2:
                dodaj(f"USB {slovo[:2]}" + (f" ({oznaka})" if oznaka else ""), slovo)
        return rez


    def druga_lokacija_stanje(self):
        """'nema' (nije izabrana), 'ok', ili 'nedostupna' (USB izvađen, disk nije tu).
        Ako je USB dobio drugo slovo (E: -> F:), sam ga pronađe po serijskom broju."""
        d2 = self.pod.get("kopija2", "")
        if not d2:
            return "nema"
        if os.path.isdir(d2):
            return "ok"
        ser = self.pod.get("kopija2_disk", 0)
        if ser:
            ostatak = os.path.splitdrive(d2)[1]
            for slovo, _, _, s in self._diskovi():
                nova = os.path.join(slovo, ostatak.lstrip("\\/"))
                if s == ser and os.path.isdir(nova):
                    self.pod["kopija2"] = nova
                    self.sacuvaj_podesavanja()
                    return "ok"
        return "nedostupna"


    def postavi_drugu_lokaciju(self, d):
        self.pod["kopija2"] = d
        self.pod["kopija2_disk"] = self._serijski(d)
        self.sacuvaj_podesavanja()
        if self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0], tiho=False) and \
                self.pod.get("poslednja_kopija2", "")[:10] == date.today().strftime("%Y-%m-%d"):
            self.toast(T("Kopija je napravljena i na: ", "Backup also made on: ") + d)
        if self.strana == "pregled":
            self.prikazi("pregled")


    def izaberi_drugu_lokaciju(self, uvod=False):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Druga lokacija za kopije", "Second backup location"))
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        self.lbl(b, T("Zaštiti stado od kvara računara", "Protect your herd if the computer breaks") if uvod
                 else T("Druga lokacija za kopije", "Second backup location"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Kopije su sada samo na ovom računaru. Ako se disk pokvari, računar ukrade ili uđe virus, "
                      "rodoslov se gubi. Izaberi i drugo mesto – program će tamo sam kopirati podatke svaki dan i pri zatvaranju.\n\n"
                      "Najbolje je OneDrive ili Google Drive: kopija ode i na internet.",
                      "Backups are only on this computer now. If the disk fails, the computer is stolen or gets a virus, "
                      "the pedigree is lost. Choose a second place – the program will copy the data there every day and when closing.\n\n"
                      "OneDrive or Google Drive is best: the copy also goes online."),
                 9, fg=INK2, wraplength=520, justify="left").pack(anchor="w", pady=(4, 12))

        def izaberi(d):
            win.destroy()
            self.postavi_drugu_lokaciju(d)

        def drugi():
            d = filedialog.askdirectory(parent=win, title=T("Izaberi folder za kopije (USB, OneDrive, Google Drive…)",
                                                            "Choose a backup folder (USB, OneDrive, Google Drive…)"))
            if d:
                izaberi(os.path.normpath(d))
        predlozi = self.predlozi_lokacije()
        if predlozi:
            self.lbl(b, T("Pronađeno na ovom računaru:", "Found on this computer:"), 10, "bold").pack(anchor="w", pady=(0, 4))
        for naziv, p in predlozi:
            r = tk.Frame(b, bg=SURF)
            r.pack(fill="x", pady=2)
            self.btn(r, naziv, lambda p=p: izaberi(p), "Primary" if naziv in ("OneDrive", "Google Drive") else "Secondary").pack(side="left")
            self.lbl(r, p, 9, fg=INK2).pack(side="left", padx=10)
        if not predlozi:
            self.napomena(b, T("Nije pronađen ni OneDrive, ni Google Drive, ni USB. Uključi USB pa otvori ovaj prozor ponovo, "
                               "ili izaberi folder ručno.", "No OneDrive, Google Drive or USB found. Plug in a USB stick and open this "
                               "window again, or choose a folder yourself."), wraplength=520)
        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, T("Drugi folder…", "Other folder…"), drugi).pack(side="left")
        if self.pod.get("kopija2"):
            def ukloni():
                self.pod.pop("kopija2", None)
                self.pod.pop("kopija2_disk", None)
                self.sacuvaj_podesavanja()
                win.destroy()
                self.osvezi_kopija_label()
                if self.strana == "pregled":
                    self.prikazi("pregled")
            self.btn(fb, T("Ukloni drugu lokaciju", "Remove second location"), ukloni, "Danger").pack(side="left", padx=8)
        self.btn(fb, T("Kasnije", "Later") if uvod else T("Otkaži", "Cancel"), win.destroy).pack(side="right")
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, None)


    def folder_kopija(self, druga=False):
        if druga:
            if self.druga_lokacija_stanje() != "ok":
                return None
            return self._postojeci(self.pod["kopija2"], self._KOREN2)
        return self._postojeci(os.path.dirname(os.path.abspath(self.tab.putanja)), self._KOREN)


    def fajlovi_podataka(self):
        return [p for p in (self.tab.putanja, self.ist.putanja, self.pods.putanja) if os.path.isfile(p)]


    def napravi_kopiju(self, vrsta="automatske", naziv=None, tiho=True):
        """Kopira tablicu, istoriju i podsetnike pored programa i na drugu lokaciju. Vraća folder kopije ili None."""
        fajlovi = self.fajlovi_podataka()
        if not fajlovi:
            return None
        imena = self._RUCNE if vrsta in self._RUCNE else self._AUTO
        naziv = naziv or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        cilj = None
        for druga in (False, True):
            koren = self.folder_kopija(druga)
            if not koren:
                continue
            try:
                grupa = self._postojeci(koren, imena)
                f = os.path.join(grupa, naziv)
                os.makedirs(f, exist_ok=True)
                for p in fajlovi:
                    shutil.copy2(p, os.path.join(f, os.path.basename(p)))
                self.ocisti_stare_kopije(grupa)
                if druga:
                    self.pod["poslednja_kopija2"] = sada()
                else:
                    cilj = f
            except OSError as e:
                if not tiho:
                    messagebox.showerror(T("Rezervna kopija", "Backup"),
                                         (T("Kopija na drugoj lokaciji nije napravljena:\n", "Backup on the second location was not made:\n")
                                          if druga else T("Kopija nije napravljena:\n", "Backup was not made:\n")) + str(e))
        if cilj:
            self.pod["poslednja_kopija"] = sada()
        self.sacuvaj_podesavanja()
        self.osvezi_kopija_label()
        return cilj


    @staticmethod
    def ocisti_stare_kopije(folder, zadrzi=30):
        try:
            sve = sorted(d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d)))
            for d in sve[:-zadrzi]:
                shutil.rmtree(os.path.join(folder, d), ignore_errors=True)
        except OSError:
            pass


    def dnevna_kopija(self):
        """Jednom dnevno, pri pokretanju (i kad se USB uključi kasnije): automatske/GGGG-MM-DD."""
        dan = date.today().strftime("%Y-%m-%d")
        treba = not os.path.isdir(os.path.join(self._postojeci(self.folder_kopija(), self._AUTO), dan))
        if self.druga_lokacija_stanje() == "ok" and self.pod.get("poslednja_kopija2", "")[:10] != dan:
            treba = True
        if treba:
            self.napravi_kopiju(self._AUTO[1] if EN else self._AUTO[0], dan)
        self.podseti_na_drugu_lokaciju()


    def podseti_na_drugu_lokaciju(self):
        """Ako druga lokacija nije izabrana, jednom nedeljno ponudi da se izabere."""
        if self.druga_lokacija_stanje() != "nema" or not self.tab.redovi:
            return
        if self.pod.get("kopija2_podsetnik", "")[:10] > (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"):
            return
        if any(isinstance(w, tk.Toplevel) and w.winfo_exists() for w in self.root.winfo_children()):
            self.root.after(4000, self.podseti_na_drugu_lokaciju)   # sačeka da se zatvore obaveštenja
            return
        self.pod["kopija2_podsetnik"] = sada()
        self.sacuvaj_podesavanja()
        self.izaberi_drugu_lokaciju(uvod=True)


    def zatvori_kopija(self):
        """Pri zatvaranju: kopija; ako je USB izvađen, ponudi da se uključi."""
        dan = date.today().strftime("%Y-%m-%d")
        while (self.druga_lokacija_stanje() == "nedostupna" and self.pod.get("poslednja_kopija2", "")[:10] != dan and
               messagebox.askretrycancel(T("Druga lokacija nije dostupna", "Second location not available"),
                                         T(f"Kopija ne može da se napravi na:\n{self.pod.get('kopija2')}\n\n"
                                           "Ako je to USB, uključi ga i klikni „Pokušaj ponovo“.\n"
                                           "„Otkaži“ zatvara program bez te kopije (kopija pored programa se pravi svakako).",
                                           f"The backup cannot be made on:\n{self.pod.get('kopija2')}\n\n"
                                           "If it is a USB stick, plug it in and click \"Retry\".\n"
                                           "\"Cancel\" closes the program without that copy (the copy next to the program is made anyway)."))):
            pass
        self.napravi_kopiju(self._AUTO[1] if EN else self._AUTO[0], dan)


    @staticmethod
    def _kad(t):
        try:
            dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None
        kad = (T("danas", "today") if dt.date() == date.today() else T("juče", "yesterday") if dt.date() == date.today() - timedelta(days=1)
               else dt.strftime(T("%d.%m.%Y.", "%d/%m/%Y")))
        return f"{kad} {dt.strftime('%H:%M')}"


    def osvezi_kopija_label(self):
        if not getattr(self, "lbl_kopija", None):
            return
        try:
            if not self.lbl_kopija.winfo_exists():
                return
        except tk.TclError:
            return
        kad = self._kad(self.pod.get("poslednja_kopija", ""))
        if not kad:
            self.lbl_kopija.config(text=T("Kopija: još nije napravljena", "Backup: not made yet"), fg=WARN, wraplength=180)
            return
        st = self.druga_lokacija_stanje()
        if st == "ok":
            dodatak, boja = T("  ·  i na drugom mestu ✓", "  ·  also on 2nd location ✓"), INK2
        elif st == "nedostupna":
            kad2 = self._kad(self.pod.get("poslednja_kopija2", ""))
            dodatak, boja = T("\nDruga lokacija nije uključena", "\nSecond location not plugged in") + \
                (T(f" (poslednja: {kad2})", f" (last: {kad2})") if kad2 else ""), WARN
        else:
            dodatak, boja = T("\nSamo na ovom računaru", "\nOnly on this computer"), WARN
        self.lbl_kopija.config(text=T(f"Kopija: {kad}", f"Backup: {kad}") + dodatak, fg=boja, justify="left", wraplength=180)


    # ---------------------------------------------- spisak i vraćanje
    def _kopija_u_folderu(self, put):
        """Glavna tablica u folderu kopije (stado.csv, herd.csv ili druga .csv koja nije istorija/podsetnici)."""
        try:
            csvovi = sorted(f for f in os.listdir(put) if f.lower().endswith(".csv") and not f.lower().endswith(self._PRATECI))
        except OSError:
            return None
        ime = os.path.basename(self.tab.putanja)
        if ime in csvovi:
            return os.path.join(put, ime)
        return os.path.join(put, csvovi[0]) if csvovi else None


    @staticmethod
    def _broj_grla(tab):
        try:
            with open(tab, encoding="utf-8-sig", errors="ignore") as f:
                return max(0, sum(1 for l in f if l.strip()) - 1)
        except OSError:
            return 0


    def spisak_kopija(self, dodatni=None):
        """Sve kopije: pored programa, na drugoj lokaciji i (opciono) u folderu koji je korisnik izabrao."""
        rez, videno = [], set()

        def obradi(put, vrsta, gde):
            put = os.path.normpath(put)
            if os.path.normcase(put) in videno:
                return
            tab = self._kopija_u_folderu(put)
            if tab:
                videno.add(os.path.normcase(put))
                rez.append(dict(put=put, tab=tab, vrsta=vrsta, gde=gde, vreme=os.path.getmtime(tab), grla=self._broj_grla(tab)))
        mesta = [(self.folder_kopija(), T("pored programa", "next to the program"))]
        if self.folder_kopija(True):
            mesta.append((self.folder_kopija(True), T("druga lokacija", "second location")))
        for koren, gde in mesta:
            for imena in (self._AUTO, self._RUCNE):
                for ime in imena:
                    f = os.path.join(koren, ime)
                    if os.path.isdir(f):
                        for d in os.listdir(f):
                            obradi(os.path.join(f, d), "rucne" if imena is self._RUCNE else "automatske", gde)
        if dodatni:
            gde = os.path.basename(os.path.normpath(dodatni)) or dodatni
            for koren, dirs, _ in os.walk(dodatni):
                if koren[len(dodatni):].count(os.sep) >= 4:
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs if not d.startswith((".", "$"))]
                obradi(koren, "rucne" if os.path.basename(os.path.dirname(koren)) in self._RUCNE else "automatske", gde)
        return sorted(rez, key=lambda k: -k["vreme"])


    def otvori_folder(self, folder):
        try:
            os.makedirs(folder, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}" &')
        except OSError:
            messagebox.showinfo("Folder", folder)


    def vrati_iz_kopije(self):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Vraćanje iz rezervne kopije", "Restore from backup"))
        win.transient(self.root)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        self.lbl(b, T("Vraćanje iz rezervne kopije", "Restore from backup"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Izaberi kopiju. Trenutni podaci se pre vraćanja sami sačuvaju kao nova kopija, pa se ništa ne gubi.\n"
                      "Novi računar? Uključi USB (ili otvori OneDrive / Google Drive) i klikni „Potraži na USB-u…“.",
                      "Choose a backup. The current data is first saved as a new backup, so nothing is lost.\n"
                      "New computer? Plug in the USB stick (or open OneDrive / Google Drive) and click \"Search USB…\"."),
                 9, fg=INK2, wraplength=600, justify="left").pack(anchor="w", pady=(2, 10))
        wrap, tv = self.tabela(b, [("kad", T("Datum i vreme", "Date and time"), 150), ("vrsta", T("Vrsta", "Type"), 140),
                                   ("grla", T("Grla", "Animals"), 60, "e"), ("gde", T("Lokacija", "Location"), 200)], visina=12, tree=False)
        wrap.pack(fill="both", expand=True)
        prazno = self.lbl(b, "", 9, fg=WARN, wraplength=600, justify="left")
        prazno.pack(anchor="w", pady=(6, 0))
        st = {"kopije": []}

        def popuni(dodatni=None):
            st["kopije"] = self.spisak_kopija(dodatni)
            tv.delete(*tv.get_children())
            for i, k in enumerate(st["kopije"]):
                tv.insert("", "end", iid=str(i), values=(
                    datetime.fromtimestamp(k["vreme"]).strftime(T("%d.%m.%Y. %H:%M", "%d/%m/%Y %H:%M")),
                    T("ručna", "manual") if k["vrsta"] == "rucne" else T("automatska (dnevna)", "automatic (daily)"),
                    k["grla"], k["gde"]), tags=["odd"] if i % 2 else [])
            if st["kopije"]:
                tv.selection_set("0")
                prazno.config(text="")
            else:
                prazno.config(text=T("Nema pronađenih kopija.", "No backups found.") + (
                    "" if dodatni else T(" Ako su na USB-u ili OneDrive-u, klikni „Potraži na USB-u…“.",
                                         " If they are on a USB stick or OneDrive, click \"Search USB…\".")))

        def potrazi():
            d = filedialog.askdirectory(parent=win, title=T("Izaberi USB ili folder sa kopijama", "Choose the USB stick or folder with backups"))
            if d:
                popuni(os.path.normpath(d))
                if not st["kopije"]:
                    prazno.config(text=T(f"U folderu {d} nema kopija Farmera.", f"No Farmer backups in {d}."))

        def vrati():
            sel = tv.selection()
            if not sel:
                return
            k = st["kopije"][int(sel[0])]
            kad = datetime.fromtimestamp(k["vreme"]).strftime(T("%d.%m.%Y. %H:%M", "%d/%m/%Y %H:%M"))
            if not messagebox.askyesno(T("Vraćanje iz kopije", "Restore from backup"),
                                       T(f"Vratiti podatke iz kopije od {kad} ({k['grla']} grla)?\n\n"
                                         "Trenutni podaci biće prvo sačuvani kao nova ručna kopija.",
                                         f"Restore data from the backup of {kad} ({k['grla']} animals)?\n\n"
                                         "The current data will first be saved as a new manual backup."), parent=win):
                return
            self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0],
                                datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + T("_pre_vracanja", "_before_restore"), tiho=False)
            try:
                folder = os.path.dirname(os.path.abspath(self.tab.putanja))
                for ime in os.listdir(k["put"]):
                    izvor = os.path.join(k["put"], ime)
                    if os.path.isfile(izvor) and ime.lower().endswith(".csv"):
                        shutil.copy2(izvor, os.path.join(folder, ime))
                self.tab = Tablica(os.path.join(folder, os.path.basename(k["tab"])))
                self.ist = Istorija(self.tab.putanja)
                self.pods = Podsetnici(self.tab.putanja)
            except Exception as e:
                messagebox.showerror(T("Vraćanje nije uspelo", "Restore failed"), str(e), parent=win)
                return
            self.model = Model(self.tab.redovi)
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            if hasattr(self, "osvezi_fajl_label"):
                self.osvezi_fajl_label()
            self.prikazi(self.strana)
            self.toast(T(f"Vraćeni podaci iz kopije od {kad}.", f"Data restored from the backup of {kad}."))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(14, 0))
        self.btn(fb, T("Vrati izabranu kopiju", "Restore selected backup"), vrati, "Primary").pack(side="right")
        self.btn(fb, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        self.btn(fb, T("Potraži na USB-u…", "Search USB…"), potrazi).pack(side="left")
        self.btn(fb, T("Otvori folder", "Open folder"), lambda: self.otvori_folder(self.folder_kopija())).pack(side="left", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        popuni()
        self.postavi_prozor(win, None)


    def kartica_kopija(self, body):
        o, c = self.card(body)
        o.pack(fill="x")
        lev = tk.Frame(c, bg=SURF)
        lev.pack(fill="x")
        self.lbl(lev, T("Rezervne kopije", "Backups"), 13, "bold").pack(anchor="w")
        kad = self._kad(self.pod.get("poslednja_kopija", "")) or T("još nije napravljena", "not made yet")
        self.lbl(lev, T(f"Program svaki dan sam pravi kopiju i čuva poslednjih 30. Poslednja kopija: {kad}.",
                        f"The program makes a backup every day and keeps the last 30. Last backup: {kad}."), 9,
                 fg=INK2, wraplength=620, justify="left").pack(anchor="w")
        st = self.druga_lokacija_stanje()
        d2 = self.pod.get("kopija2", "")
        kad2 = self._kad(self.pod.get("poslednja_kopija2", "")) or T("još nije", "not yet")
        if st == "ok":
            tekst, boja = T(f"✓ Druga lokacija: {d2}  ·  poslednja kopija tamo: {kad2}", f"✓ Second location: {d2}  ·  last copy there: {kad2}"), OK
        elif st == "nedostupna":
            tekst, boja = T(f"Druga lokacija nije dostupna: {d2} (USB nije uključen?)  ·  poslednja kopija tamo: {kad2}",
                            f"Second location not available: {d2} (USB not plugged in?)  ·  last copy there: {kad2}"), WARN
        else:
            tekst, boja = T("Kopije su samo na ovom računaru. Izaberi drugu lokaciju (OneDrive, Google Drive ili USB) – ako se računar pokvari, kopija ostaje.",
                            "Backups are only on this computer. Choose a second location (OneDrive, Google Drive or USB) – if the computer breaks, the backup remains."), WARN
        self.lbl(lev, tekst, 9, "bold" if st != "ok" else "normal", fg=boja, wraplength=620, justify="left").pack(anchor="w", pady=(4, 0))
        dd = tk.Frame(c, bg=SURF)
        dd.pack(fill="x", pady=(10, 0))
        self.btn(dd, T("Napravi kopiju sada", "Make backup now"), lambda: (self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0], tiho=False),
                                                                          self.toast(T("Rezervna kopija je napravljena.", "Backup has been made.")),
                                                                          self.prikazi("pregled")), "Primary").pack(side="left")
        self.btn(dd, T("Vrati iz kopije…", "Restore from backup…"), self.vrati_iz_kopije).pack(side="left", padx=8)
        self.btn(dd, T("Druga lokacija…", "Second location…") if st != "nema" else T("Izaberi drugu lokaciju…", "Choose second location…"),
                 self.izaberi_drugu_lokaciju, "Secondary" if st != "nema" else "Primary").pack(side="left")
        self.btn(dd, T("Otvori folder", "Open folder"), lambda: self.otvori_folder(self.folder_kopija())).pack(side="left", padx=8)
