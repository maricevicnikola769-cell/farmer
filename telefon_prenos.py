"""Telefon: slanje podataka na telefon (Farmer za Android) i vraćanje onoga što je upisano u štali.
Spajanje radi zapis po zapis: šta je menjao samo telefon – uzima se sa telefona; šta je menjao samo računar – ostaje
sa računara; ako su oba menjala isti zapis – uzima se verzija sa telefona i to se prijavi."""
import json
import os
import tkinter as tk
import uuid
from tkinter import filedialog, messagebox

from osnova import APP_DIR, EN, JEZIK, prevedi_vrednost
from jezik import GRAVIDNOST_PROFILI, T
from podaci import IST_KOLONE, KOLONE, Podsetnici, norm_rasa, sada, vrsta_norm
from izgled import BG, BRAND, INK2, OK, SURF, ScrollFrame
from rodoslov import Model

TELEFON_URL = "https://maricevicnikola769-cell.github.io/farmer/telefon/"
QR_PNG = "iVBORw0KGgoAAAANSUhEUgAAALkAAAC5AQMAAABOYwwfAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAGUExURf///xgiHPREO9kAAAABYktHRACIBR1IAAAAB3RJTUUH6goUFhU3eWPW9AAAAaJJREFUWMPllzGugzAQRBeloOQI3AQuFgmkXMzcxEegdIHYzKxxlP97pomlrAgvxco7M3bMfnfN7l7MnmbT4N4nFD9VYMKndL5af9ojmw1rfacBg+cy709DL4v35/DyogUs/QZaTA/Q1ehcmIcUcB7zjoKHsfwb1M0glDgNr9zKH4neDKztC0rbDVMBtoHdeHjpKIbrqwysIwaweLTmaTjGppL7AbwfT1Diztb8BSoDu7ErFIuGMJQqBglA6sUTunqyIIKSDMB+/YZ9ibxHOZjAIoCsowSgg5MepCXrPDQAvWyO3E3wAp4wFFOBqY5i4buVIUhDqAC9D/sdCMHQwceDCjBzDzqHBMKDNQVUII6YaOisKbC08BWA7jP9yN32Ew1g7sbxDhtE7q5fgXw/uAKvhmCEUZIBWzLngTMemvQNVAi4G4nBEw1h5XatvR/Y5QWKIXTwyEUGPv8m4ADEf4SvqUDcLCP/4sQ5ednRgbjQM/86joJNNg+KAJVYz1rkXxYDyjHeRfx/b8nNgPO4rlYelzvXgVDizK/0AsvYJxX41fUGNmq3seBVPlgAAAAASUVORK5CYII="

_PREVOD = ("dogadjaj", "ishod", "ter", "tip", "poreklo")


def _normalizuj(k, v):
    """Vrednost na trenutnom jeziku računara (telefon je mogao da piše na drugom)."""
    v = "" if v is None else str(v)
    if k in _PREVOD:
        return prevedi_vrednost(v)
    if k == "rasa":
        return norm_rasa(prevedi_vrednost(v))
    if k == "vrsta":
        return vrsta_norm(v)
    return v


def _indeksiraj(lista, kljuc):
    """{ključ#n: zapis} i redosled ključeva; #n razlikuje zapise sa istim ključem (npr. dva u istoj sekundi)."""
    brojac, rez, red = {}, {}, []
    for x in lista:
        k = kljuc(x)
        n = brojac.get(k, 0)
        brojac[k] = n + 1
        kk = f"{k}#{n}"
        rez[kk] = x
        red.append(kk)
    return rez, red


def spoji(baza, telefon, racunar, kljuc, kolone):
    """Spajanje u tri smera. Vraća (spojena lista, {'sa_telefona', 'novo', 'sukob'})."""
    B, _ = _indeksiraj(baza, kljuc)
    Tl, red_t = _indeksiraj(telefon, kljuc)
    R, red_r = _indeksiraj(racunar, kljuc)

    def poredi(x):
        return None if x is None else tuple(_normalizuj(k, x.get(k, "")) for k in kolone)
    rez, stat = [], dict(sa_telefona=0, novo=0, sukob=0)
    for k in red_r + [k for k in red_t if k not in R]:
        b, t, r = B.get(k), Tl.get(k), R.get(k)
        cb, ct, cr = poredi(b), poredi(t), poredi(r)
        if ct == cb:                  # telefon nije menjao
            izbor = r
        elif cr == cb:                # menjao samo telefon
            izbor = t
            stat["sa_telefona"] += 1
            if b is None and r is None:
                stat["novo"] += 1
        elif ct == cr:                # oba isto
            izbor = r
        else:                         # oba menjala različito -> telefon (upisano u štali)
            izbor = t
            stat["sukob"] += 1
        if izbor is not None:
            if izbor is t:
                izbor = {k_: _normalizuj(k_, v) for k_, v in t.items()}
            rez.append(izbor)
    return rez, stat


def spoji_razlike(stavke, racunar, kljuc, kolone):
    """Spajanje paketa sa telefona koji nosi samo promenjene zapise: [{n, b (kakav je bio), t (kakav je sad)}].
    n = koji po redu zapis sa istim ključem (npr. dva događaja u istoj sekundi). Ostali zapisi računara ostaju."""
    R, red = _indeksiraj(racunar, kljuc)
    rez = dict(R)

    def poredi(x):
        return None if x is None else tuple(_normalizuj(k, x.get(k, "")) for k in kolone)
    stat = dict(sa_telefona=0, novo=0, sukob=0)
    for s in stavke:
        b, t = s.get("b"), s.get("t")
        osnovni = t or b
        if not osnovni:
            continue
        k = f"{kljuc(osnovni)}#{int(s.get('n') or 0)}"
        r = rez.get(k)
        cb, ct, cr = poredi(b), poredi(t), poredi(r)
        if ct == cb or ct == cr:              # telefon nije menjao, ili računar već ima isto
            continue
        if cr == cb:
            stat["sa_telefona"] += 1
            if b is None and r is None:
                stat["novo"] += 1
        else:
            stat["sukob"] += 1
        if t is None:
            rez.pop(k, None)
            continue
        if k not in rez:
            red.append(k)
        rez[k] = {k_: _normalizuj(k_, v) for k_, v in t.items()}
    return [rez[k] for k in red if k in rez], stat


def _kljuc_ist(z):
    return f"{z.get('grlo', '')}|{z.get('uneto', '')}|{_normalizuj('dogadjaj', z.get('dogadjaj', ''))}"


def _kljuc_pod(z):
    return f"{z.get('grlo', '')}|{z.get('uneto', '')}|{_normalizuj('tip', z.get('tip', ''))}"


def spoji_sve(obj, grla, istorija, podsetnici):
    """Spaja paket sa telefona sa podacima računara. Vraća (grla, istorija, podsetnici, izveštaj)."""
    osn = obj.get("osnova") or {}
    kol_g = list(dict.fromkeys(KOLONE + [k for r in grla + obj.get("grla", []) for k in r]))
    g, sg = spoji(osn.get("grla", []), obj.get("grla", []), grla, lambda r: r.get("id", ""), kol_g)
    i, si = spoji(osn.get("istorija", []), obj.get("istorija", []), istorija, _kljuc_ist, IST_KOLONE)
    p, sp = spoji(osn.get("podsetnici", []), obj.get("podsetnici", []), podsetnici, _kljuc_pod, Podsetnici.KOLONE)
    return g, i, p, dict(grla=sg, istorija=si, podsetnici=sp)


class TelefonDeo:
    """Strana 'Telefon': slanje na telefon i učitavanje sa telefona."""

    def paket_za_telefon(self):
        grav = {}
        for k, (naziv, vr, prep, mn, mx, pr) in GRAVIDNOST_PROFILI.items():
            pod = self.pod.get("gravidnost2", {}).get(k)
            if pod:
                mn, mx, pr = (int(x) for x in pod)
            grav[k] = [naziv, vr, list(prep), mn, mx, pr]
        return dict(format="farmer-telefon", verzija=1, jezik=JEZIK, id=uuid.uuid4().hex, izvezeno=sada(),
                    prag=self.prag, gravidnost=grav, stada=self.sva_stada(),
                    grla=[dict(r) for r in self.tab.redovi], istorija=[dict(z) for z in self.ist.zapisi],
                    podsetnici=[dict(z) for z in self.pods.zapisi])

    def posalji_na_telefon(self):
        pocetni = self.pod.get("kopija2") if self.pod.get("kopija2") and os.path.isdir(self.pod.get("kopija2")) else APP_DIR
        put = filedialog.asksaveasfilename(
            title=T("Sačuvaj fajl za telefon (npr. u Google Drive ili OneDrive)", "Save the file for the phone (e.g. in Google Drive or OneDrive)"),
            initialdir=pocetni, initialfile="farmer-za-telefon.json", defaultextension=".json",
            filetypes=[(T("Farmer za telefon", "Farmer for phone"), "*.json")])
        if not put:
            return
        try:
            with open(put, "w", encoding="utf-8") as f:
                json.dump(self.paket_za_telefon(), f, ensure_ascii=False)
        except OSError as e:
            messagebox.showerror("Farmer", str(e))
            return
        self.pod["telefon_poslato"] = sada()
        self.sacuvaj_podesavanja()
        messagebox.showinfo(T("Fajl za telefon je napravljen", "File for the phone is ready"),
                            T(f"Sačuvano:\n{put}\n\nPrebaci ga na telefon (Google Drive, Viber, kabl…), pa u aplikaciji Farmer "
                              "na telefonu klikni „Učitaj sa računara“.",
                              f"Saved:\n{put}\n\nMove it to the phone (Google Drive, Viber, cable…), then in the Farmer app "
                              "on the phone tap \"Load from computer\"."))
        if self.strana == "telefon":
            self.prikazi("telefon")

    def ucitaj_sa_telefona(self):
        put = filedialog.askopenfilename(title=T("Izaberi fajl sa telefona", "Choose the file from the phone"), initialdir=APP_DIR,
                                         filetypes=[(T("Fajl sa telefona", "File from phone"), "*.txt *.json"), (T("Svi fajlovi", "All files"), "*.*")])
        if not put:
            return
        try:
            with open(put, encoding="utf-8-sig") as f:
                obj = json.load(f)
        except (OSError, ValueError) as e:
            messagebox.showerror("Farmer", T("Fajl ne može da se pročita:\n", "The file cannot be read:\n") + str(e))
            return
        if obj.get("format") == "farmer-telefon":
            messagebox.showwarning("Farmer", T("Ovo je fajl koji je računar napravio za telefon. Učitaj ga na telefonu.",
                                               "This is the file the computer made for the phone. Load it on the phone."))
            return
        if obj.get("format") != "farmer-telefon-povratak":
            messagebox.showerror("Farmer", T("Ovo nije fajl sa Farmer telefona.", "This is not a file from the Farmer phone app."))
            return
        promene = obj.get("promene", [])
        if not promene:
            messagebox.showinfo("Farmer", T("Na telefonu nije bilo novih promena.", "There were no new changes on the phone."))
            return
        spisak = "\n".join("• " + p.get("tekst", "") for p in promene[:15]) + (T(f"\n… i još {len(promene) - 15}", f"\n… and {len(promene) - 15} more") if len(promene) > 15 else "")
        if not messagebox.askyesno(T("Učitaj sa telefona", "Load from phone"),
                                   T(f"Na telefonu je urađeno {len(promene)} promena:\n\n{spisak}\n\nPreneti ih u računar? "
                                     "Pre toga se pravi rezervna kopija.",
                                     f"{len(promene)} changes were made on the phone:\n\n{spisak}\n\nTransfer them to the computer? "
                                     "A backup is made first.")):
            return
        self.napravi_kopiju("manual" if EN else "rucne", sada().replace(":", "-").replace(" ", "_") + T("_pre_telefona", "_before_phone"), tiho=False)
        try:
            g, i, p, izv = spoji_sve(obj, self.tab.redovi, self.ist.zapisi, self.pods.zapisi)
            Model(g)   # provera da se rodoslov može izračunati
        except Exception as e:
            messagebox.showerror("Farmer", T("Spajanje nije uspelo – ništa nije promenjeno.\n\n", "Merging failed – nothing was changed.\n\n") + str(e))
            return
        self.tab.dodatne = list(dict.fromkeys(self.tab.dodatne + [k for r in g for k in r if k not in KOLONE]))
        self.tab.redovi, self.ist.zapisi, self.pods.zapisi = g, i, p
        self.pod["telefon_ucitano"] = sada()
        self.sacuvaj_podesavanja()
        self.promena(T("Podaci sa telefona su preneti.", "Data from the phone has been transferred."))
        sukob = sum(s["sukob"] for s in izv.values())
        messagebox.showinfo(T("Preneto sa telefona", "Transferred from phone"),
                            T(f"Novih grla: {izv['grla']['novo']}\nNovih događaja: {izv['istorija']['novo']}\n"
                              f"Izmena (parenja, porođaji, podsetnici…): {izv['grla']['sa_telefona'] + izv['istorija']['sa_telefona'] + izv['podsetnici']['sa_telefona'] - izv['grla']['novo'] - izv['istorija']['novo']}"
                              + (f"\n\n{sukob} zapisa je menjano i na računaru i na telefonu – uzeta je verzija sa telefona." if sukob else "")
                              + "\n\nSada pošalji telefonu novi fajl („Pošalji na telefon“), da i on ima sve podatke.",
                              f"New animals: {izv['grla']['novo']}\nNew events: {izv['istorija']['novo']}\n"
                              f"Changes (matings, births, reminders…): {izv['grla']['sa_telefona'] + izv['istorija']['sa_telefona'] + izv['podsetnici']['sa_telefona'] - izv['grla']['novo'] - izv['istorija']['novo']}"
                              + (f"\n\n{sukob} records were changed on both the computer and the phone – the phone version was used." if sukob else "")
                              + "\n\nNow send the phone a new file (\"Send to phone\") so it has all the data too."))

    def s_telefon(self):
        sf = ScrollFrame(self.main, bg=BG)
        sf.pack(fill="both", expand=True)
        body = tk.Frame(sf.inner, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=28)
        self.zaglavlje(body, T("Telefon", "Phone"), T("Farmer na Android telefonu – gledanje i upis u štali, radi i bez interneta.",
                                                     "Farmer on an Android phone – view and record in the barn, works offline."))
        self.kartica_sinhronizacije(body)
        o, c = self.card(body)
        o.pack(fill="x", pady=(0, 12))
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        lev = tk.Frame(red, bg=SURF)
        lev.pack(side="left", fill="both", expand=True)
        self.lbl(lev, T("1. Instaliraj aplikaciju na telefon (samo prvi put)", "1. Install the app on the phone (first time only)"), 12, "bold").pack(anchor="w")
        self.lbl(lev, T("Skeniraj kod kamerom telefona (ili otvori adresu u Chrome-u). U Chrome-u otvori meni ⋮ i izaberi "
                        "„Dodaj na početni ekran“ / „Instaliraj aplikaciju“. Dobićeš ikonicu Farmer.",
                        "Scan the code with the phone camera (or open the address in Chrome). In Chrome open the ⋮ menu and choose "
                        "\"Add to Home screen\" / \"Install app\". You get a Farmer icon."), 9, fg=INK2, justify="left", wraplength=520).pack(anchor="w", pady=(4, 8))
        adr = self.lbl(lev, TELEFON_URL, 10, "bold", fg=BRAND, cursor="hand2")
        adr.pack(anchor="w")
        adr.bind("<Button-1>", lambda e: (self.root.clipboard_clear(), self.root.clipboard_append(TELEFON_URL),
                                          self.toast(T("Adresa je kopirana.", "Address copied."))))
        self.lbl(lev, T("(klik kopira adresu)", "(click copies the address)"), 8, fg=INK2).pack(anchor="w")
        try:
            self._qr = tk.PhotoImage(data=QR_PNG)
            tk.Label(red, image=self._qr, bg=SURF).pack(side="right", padx=(16, 0))
        except tk.TclError:
            pass

        for naslov, opis, dugme, cmd, kad in (
                (T("2. Pošalji podatke na telefon", "2. Send data to the phone"),
                 T("Napravi fajl sa svim grlima i istorijom. Sačuvaj ga u Google Drive / OneDrive ili ga pošalji sebi preko Vibera, "
                   "pa ga na telefonu otvori sa „Učitaj sa računara“.",
                   "Makes a file with all animals and history. Save it in Google Drive / OneDrive or send it to yourself via Viber, "
                   "then open it on the phone with \"Load from computer\"."),
                 T("📲 Pošalji na telefon", "📲 Send to phone"), self.posalji_na_telefon, self.pod.get("telefon_poslato")),
                (T("3. Vrati na računar šta je upisano u štali", "3. Bring back to the computer what was recorded in the barn"),
                 T("Na telefonu: Više → Prenos → „Pošalji računaru“. Ovde izaberi taj fajl. Pre prenosa se pravi rezervna kopija, "
                   "a promene sa računara se ne gube.",
                   "On the phone: More → Transfer → \"Send to computer\". Choose that file here. A backup is made first, "
                   "and changes made on the computer are kept."),
                 T("💻 Učitaj sa telefona", "💻 Load from phone"), self.ucitaj_sa_telefona, self.pod.get("telefon_ucitano"))):
            o, c = self.card(body)
            o.pack(fill="x", pady=(0, 12))
            red = tk.Frame(c, bg=SURF)
            red.pack(fill="x")
            lev = tk.Frame(red, bg=SURF)
            lev.pack(side="left", fill="x", expand=True)
            self.lbl(lev, naslov, 12, "bold").pack(anchor="w")
            self.lbl(lev, opis, 9, fg=INK2, justify="left", wraplength=520).pack(anchor="w", pady=(2, 0))
            if kad:
                self.lbl(lev, T("Poslednji put: ", "Last time: ") + kad[:16], 9, fg=OK).pack(anchor="w", pady=(4, 0))
            self.btn(red, dugme, cmd, "Primary").pack(side="right", padx=(16, 0))
