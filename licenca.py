"""Licenca (paketi) – ključ se kupuje na sajtu preko Lemon Squeezy-ja i stiže kupcu mejlom automatski.

Program proverava ključ preko interneta (Lemon Squeezy License API) i od odgovora zna koji je paket kupljen
i do kada važi. Novac i podatke o kartici program nikad ne vidi.

- Prvih PROBA_DANA dana posle instalacije: sve otključano (proba).
- Posle probe, bez ključa: besplatno do 20 aktivnih grla. Podaci se nikad ne brišu i sve može da se gleda.
- Ključ se ponovo proverava svakih PROVERA_DANA dana; bez interneta program radi normalno još BEZ_INTERNETA_DANA dana.
"""
import hashlib
import hmac
import json
import os
import platform
import re
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

import jezik
from jezik import T
from osnova import PODESAVANJA
from izgled import BAD, BRAND, INK, INK2, OK, SURF, SURF2, WARN

# ---------------- podešavanja prodaje (posle otvaranja prodavnice na Lemon Squeezy-ju upisati ID-jeve) ----------------
KUPI_URL = "https://getherddoc.com/#cene"
LS_API = "https://api.lemonsqueezy.com/v1/licenses/"
LS_STORE_ID = None            # broj prodavnice (Settings → Stores); dok je None, prodavnica se ne proverava
LS_VARIJANTE = {}             # {variant_id: "osnovni" | "pro" | "farma"}; dok je prazno, paket se prepoznaje po imenu
PROBA_DANA = 30
PROVERA_DANA = 7
BEZ_INTERNETA_DANA = 30

# paket -> (najviše aktivnih grla, cena godišnje); None = bez ograničenja
PAKETI = {"probni": (20, 0), "osnovni": (100, 49), "pro": (500, 99), "farma": (None, 199)}
PRODAJNI = ("osnovni", "pro", "farma")

_TAJNA = b"HerdDoc-licenca-2027"


def naziv_paketa(p):
    return {"probni": T("Besplatni", "Free"), "osnovni": T("Osnovni", "Basic"), "pro": "Pro",
            "farma": T("Farma", "Farm"), "proba": T("Proba", "Trial")}.get(p, p)


def opis_limita(limit):
    return T("bez ograničenja broja grla", "unlimited animals") if limit is None else T(f"do {limit} grla", f"up to {limit} animals")


# ---------------- čuvanje (potpisano, da se paket ne može samo prepisati u fajlu) ----------------
def putanja_licence():
    return os.path.join(os.path.dirname(os.path.abspath(PODESAVANJA)), "herddoc_licenca.json")


def _racunar():
    return f"{uuid.getnode():x}|{platform.node()}"


def _potpis(podaci):
    telo = json.dumps({k: podaci.get(k) for k in sorted(podaci) if k != "potpis"}, sort_keys=True, ensure_ascii=False)
    return hmac.new(_TAJNA + _racunar().encode(), telo.encode(), hashlib.sha256).hexdigest()


def ucitaj(put=None, danas=None):
    """Licenca sa diska. Nema fajla -> počinje proba. Prepravljen fajl -> bez ključa i bez probe."""
    put = put or putanja_licence()
    danas = danas or date.today()
    try:
        with open(put, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and hmac.compare_digest(str(d.get("potpis", "")), _potpis(d)):
            return d
        return {"prvi_start": "2000-01-01"}             # menjan ručno ili prenet sa drugog računara
    except (OSError, ValueError):
        pass
    d = {"prvi_start": danas.isoformat()}
    sacuvaj(d, put)
    return d


def sacuvaj(d, put=None):
    d = dict(d)
    d["potpis"] = _potpis(d)
    try:
        with open(put or putanja_licence(), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return d


def _dan(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


# ---------------- stanje ----------------
def stanje(d, danas=None):
    """Šta licenca trenutno dozvoljava.
    Vraća dict: paket (osnovni/pro/farma/proba/probni), limit (None = bez ograničenja), do (date|None),
    razlog (""|"isteklo"|"bez_provere"), proba_dana (preostali dani probe)."""
    danas = danas or date.today()
    s = dict(paket="probni", limit=PAKETI["probni"][0], do=None, razlog="", proba_dana=0, kupljen=d.get("paket"))
    if d.get("kljuc") and d.get("paket") in PRODAJNI:
        istice, provereno = _dan(d.get("istice")), _dan(d.get("provereno"))
        if istice and istice < danas:
            s["razlog"] = "isteklo"
        elif not provereno or (danas - provereno).days > BEZ_INTERNETA_DANA:
            s["razlog"] = "bez_provere"
        else:
            s.update(paket=d["paket"], limit=PAKETI[d["paket"]][0], do=istice)
            return s
    pocetak = _dan(d.get("prvi_start")) or danas
    ost = PROBA_DANA - (danas - pocetak).days
    if ost > 0 and not s["razlog"]:
        s.update(paket="proba", limit=None, proba_dana=ost, do=pocetak + timedelta(days=PROBA_DANA))
    return s


def ima_mesta(s, aktivnih, novih=1):
    return s["limit"] is None or aktivnih + novih <= s["limit"]


def aktivnih_grla(redovi):
    return sum(1 for r in redovi if (r.get("status") or "aktivno") == "aktivno")


# ---------------- Lemon Squeezy ----------------
class GreskaLicence(Exception):
    """kod: mreza | nema | limit | iskljucen | istekao | prodavnica | paket | drugo"""
    def __init__(self, kod, tekst=""):
        super().__init__(tekst or kod)
        self.kod = kod


def _post(akcija, polja, vreme=15):
    zahtev = urllib.request.Request(LS_API + akcija, data=urllib.parse.urlencode(polja).encode(),
                                    headers={"Accept": "application/json", "User-Agent": "HerdDoc"})
    try:
        with urllib.request.urlopen(zahtev, timeout=vreme) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:            # 400/404: Lemon Squeezy vraća JSON sa opisom greške
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            raise GreskaLicence("drugo", str(e))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise GreskaLicence("mreza", str(e))


def paket_iz_odgovora(meta):
    """Koji paket nosi ključ (po ID-ju varijante, a dok ID-jevi nisu upisani – po imenu proizvoda)."""
    meta = meta or {}
    if LS_STORE_ID is not None and meta.get("store_id") != LS_STORE_ID:
        raise GreskaLicence("prodavnica")
    if LS_VARIJANTE:
        p = LS_VARIJANTE.get(meta.get("variant_id"))
        if not p:
            raise GreskaLicence("paket")
        return p
    ime = f" {meta.get('product_name', '')} {meta.get('variant_name', '')} ".lower()
    if re.search(r"farm|fazenda|granja|ferme|betrieb", ime):
        return "farma"
    if re.search(r"\bpro\b", ime):
        return "pro"
    if re.search(r"osnov|basic|basis|básico|basico|base|standard", ime):
        return "osnovni"
    raise GreskaLicence("paket")


def _greska(odg):
    poruka = str(odg.get("error") or "").lower()
    if "activation limit" in poruka:
        return GreskaLicence("limit", poruka)
    if "not found" in poruka or "invalid" in poruka:
        return GreskaLicence("nema", poruka)
    if "disabled" in poruka:
        return GreskaLicence("iskljucen", poruka)
    if "expired" in poruka:
        return GreskaLicence("istekao", poruka)
    return GreskaLicence("drugo", poruka)


def _iz_kljuca(d, odg, danas):
    lk, meta = odg.get("license_key") or {}, odg.get("meta") or {}
    status = lk.get("status")
    if status == "disabled":
        raise GreskaLicence("iskljucen")
    paket = paket_iz_odgovora(meta)
    d.update(paket=paket, istice=(lk.get("expires_at") or "")[:10] or None, provereno=danas.isoformat(),
             email=meta.get("customer_email", ""), status=status)
    if status == "expired":
        d["istice"] = d["istice"] or (danas - timedelta(days=1)).isoformat()
    return d


def aktiviraj(d, kljuc, danas=None, post=None):
    """Aktivira ključ na ovom računaru. Vraća novu licencu (nesačuvanu) ili baca GreskaLicence."""
    danas, post = danas or date.today(), post or _post
    kljuc = "".join(kljuc.split())
    if len(kljuc) < 8:
        raise GreskaLicence("nema")
    odg = post("activate", {"license_key": kljuc, "instance_name": f"{platform.node() or 'PC'} – HerdDoc"})
    if not odg.get("activated"):
        raise _greska(odg)
    nova = {k: v for k, v in d.items() if k in ("prvi_start",)}
    nova.update(kljuc=kljuc, instanca=(odg.get("instance") or {}).get("id", ""))
    return _iz_kljuca(nova, odg, danas)


def proveri(d, danas=None, post=None):
    """Ponovna provera ključa (da li je pretplata obnovljena, istekla ili isključena)."""
    danas, post = danas or date.today(), post or _post
    odg = post("validate", {"license_key": d["kljuc"], "instance_id": d.get("instanca", "")})
    if not odg.get("valid"):
        lk = odg.get("license_key") or {}
        if lk.get("status") == "expired":
            return _iz_kljuca(dict(d), odg, danas)
        raise _greska(odg) if odg.get("error") else GreskaLicence("iskljucen")
    return _iz_kljuca(dict(d), odg, danas)


def deaktiviraj(d, post=None):
    """Oslobađa ključ sa ovog računara (da se aktivira na drugom)."""
    post = post or _post
    odg = post("deactivate", {"license_key": d["kljuc"], "instance_id": d.get("instanca", "")})
    if not odg.get("deactivated"):
        raise _greska(odg)
    return {k: v for k, v in d.items() if k == "prvi_start"}


def poruka_greske(g):
    return {
        "mreza": T("Nema veze sa internetom. Proveri internet i pokušaj ponovo.", "No internet connection. Check the internet and try again."),
        "nema": T("Ključ nije pronađen. Proveri da li je prepisan tačno kao u mejlu (najbolje kopiraj i nalepi).",
                  "The key was not found. Check that it is copied exactly as in the e-mail (best: copy and paste)."),
        "limit": T("Ovaj ključ je već aktiviran na drugom računaru. Na tom računaru otvori Licencu i klikni „Prebaci na drugi računar“, "
                   "ili nam piši na herddoc7@gmail.com.",
                   "This key is already activated on another computer. On that computer open Licence and click “Move to another computer”, "
                   "or write to herddoc7@gmail.com."),
        "iskljucen": T("Ovaj ključ je isključen (na primer posle povraćaja novca). Piši nam na herddoc7@gmail.com.",
                       "This key has been disabled (for example after a refund). Write to herddoc7@gmail.com."),
        "istekao": T("Pretplata za ovaj ključ je istekla. Obnovi je na sajtu.", "The subscription for this key has expired. Renew it on the website."),
        "prodavnica": T("Ovo nije ključ za HerdDoc.", "This is not a HerdDoc key."),
        "paket": T("Ključ je ispravan, ali nije prepoznat paket. Piši nam na herddoc7@gmail.com.",
                   "The key is valid, but the package was not recognised. Write to herddoc7@gmail.com."),
    }.get(g.kod, T("Ključ trenutno ne može da se proveri. Pokušaj ponovo kasnije.", "The key cannot be checked right now. Try again later."))


def kratko_stanje(s, aktivnih):
    """Tekst za levi meni."""
    if s["paket"] == "proba":
        return T(f"🔑 Proba: još {s['proba_dana']} dana", f"🔑 Trial: {s['proba_dana']} days left"), WARN
    if s["paket"] == "probni":
        boja = BAD if aktivnih >= s["limit"] else WARN
        if s["razlog"] == "isteklo":
            return T("🔑 Licenca istekla – obnovi", "🔑 Licence expired – renew"), BAD
        if s["razlog"] == "bez_provere":
            return T("🔑 Proveri licencu (internet)", "🔑 Check licence (internet)"), BAD
        return T(f"🔑 Besplatno: {aktivnih}/{s['limit']} grla – kupi", f"🔑 Free: {aktivnih}/{s['limit']} animals – buy"), boja
    do = f" – {T('do', 'until')} {s['do'].strftime('%d/%m/%Y' if jezik.EN else '%d.%m.%Y')}" if s["do"] else ""
    return f"🔑 {naziv_paketa(s['paket'])}{do}", OK


# ---------------- deo prozora ----------------
class LicencaDeo:
    def lic(self):
        if not hasattr(self, "_lic"):
            d = ucitaj()
            ps = self.pod.get("lic_start")               # početak probe zapamćen i u podešavanjima
            if ps and str(ps) < str(d.get("prvi_start", "")):
                d = sacuvaj(dict(d, prvi_start=ps))
            elif not ps and d.get("prvi_start"):
                self.pod["lic_start"] = d["prvi_start"]
                self.sacuvaj_podesavanja()
            self._lic = d
        return self._lic

    def lic_stanje(self):
        return stanje(self.lic())

    def osvezi_licenca_label(self):
        lb = getattr(self, "lbl_licenca", None)
        try:
            if lb and lb.winfo_exists():
                txt, boja = kratko_stanje(self.lic_stanje(), aktivnih_grla(self.tab.redovi))
                lb.config(text=txt, fg=boja)
        except tk.TclError:
            pass

    def licenca_na_startu(self):
        """Povremena provera ključa u pozadini (ne smeta radu; bez interneta – ništa)."""
        d = self.lic()
        pr = _dan(d.get("provereno"))
        if not d.get("kljuc") or (pr and (date.today() - pr).days < PROVERA_DANA):
            self.osvezi_licenca_label()
            return

        def posao():
            try:
                nova = proveri(d)
            except GreskaLicence as g:
                if g.kod in ("iskljucen", "nema"):
                    nova = dict(d, istice=(date.today() - timedelta(days=1)).isoformat())
                else:
                    return
            self.root.after(0, lambda: self._postavi_licencu(nova))
        threading.Thread(target=posao, daemon=True).start()

    def _postavi_licencu(self, d):
        self._lic = sacuvaj(d)
        self.osvezi_licenca_label()

    def ima_mesta_za_grla(self, novih=1, parent=None):
        """Pre dodavanja novih aktivnih grla. Ako je paket pun – objasni i ponudi kupovinu."""
        s, akt = self.lic_stanje(), aktivnih_grla(self.tab.redovi)
        if ima_mesta(s, akt, novih):
            return True
        razlog = {"isteklo": T("Pretplata je istekla, pa program radi kao besplatna verzija. ", "The subscription has expired, so the program works as the free version. "),
                  "bez_provere": T("Licenca nije proverena više od 30 dana (potreban je internet). ", "The licence has not been checked for over 30 days (internet needed). ")
                  }.get(s["razlog"], "")
        if messagebox.askyesno(T("Dostignut broj grla", "Animal limit reached"),
                               razlog + T(f"Paket „{naziv_paketa(s['paket'])}“ dozvoljava {s['limit']} aktivnih grla, a sada ih imaš {akt}.\n\n"
                                          "Sva grla i podaci ostaju i mogu da se gledaju i menjaju. Za nova grla izaberi veći paket.\n\n"
                                          "Otvori licencu?",
                                          f"The “{naziv_paketa(s['paket'])}” package allows {s['limit']} active animals, and you now have {akt}.\n\n"
                                          "All animals and data stay and can be viewed and changed. For new animals choose a larger package.\n\n"
                                          "Open the licence?"), parent=parent or self.root):
            self.prozor_licence(parent)
        return False

    def licenca_za_telefon(self):
        s = self.lic_stanje()
        return dict(paket=s["paket"], naziv=naziv_paketa(s["paket"]), limit=s["limit"])

    def prozor_licence(self, parent=None):
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(T("Licenca", "Licence"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, "🔑 " + T("Licenca", "Licence"), 17, "bold").pack(anchor="w")
        kartica = tk.Frame(b, bg=SURF2)
        kartica.pack(fill="x", pady=(12, 8))
        stanje_lbl = self.lbl(kartica, "", 11, "bold", bg=SURF2, justify="left", wraplength=470)
        stanje_lbl.pack(anchor="w", padx=14, pady=(12, 2))
        detalji = self.lbl(kartica, "", 9, fg=INK2, bg=SURF2, justify="left", wraplength=470)
        detalji.pack(anchor="w", padx=14, pady=(0, 12))

        def prikazi():
            d, s, akt = self.lic(), self.lic_stanje(), aktivnih_grla(self.tab.redovi)
            fmt = "%d/%m/%Y" if jezik.EN else "%d.%m.%Y"
            if s["paket"] == "proba":
                t = T(f"Proba – sve otključano još {s['proba_dana']} dana", f"Trial – everything unlocked for {s['proba_dana']} more days")
            elif s["paket"] == "probni":
                t = T(f"Besplatna verzija – {opis_limita(s['limit'])}", f"Free version – {opis_limita(s['limit'])}")
                if s["razlog"] == "isteklo":
                    t = T(f"Pretplata „{naziv_paketa(d.get('paket'))}“ je istekla – sada besplatna verzija ({opis_limita(s['limit'])})",
                          f"The “{naziv_paketa(d.get('paket'))}” subscription has expired – now the free version ({opis_limita(s['limit'])})")
                elif s["razlog"] == "bez_provere":
                    t = T("Licenca nije proverena više od 30 dana. Poveži računar na internet i klikni „Proveri sada“.",
                          "The licence has not been checked for over 30 days. Connect to the internet and click “Check now”.")
            else:
                t = T(f"Paket {naziv_paketa(s['paket'])} – {opis_limita(s['limit'])}", f"{naziv_paketa(s['paket'])} package – {opis_limita(s['limit'])}")
            stanje_lbl.config(text=t, fg=OK if s["paket"] in PRODAJNI else (BAD if s["razlog"] else INK))
            red = [T(f"Aktivnih grla: {akt}", f"Active animals: {akt}")]
            if s["paket"] in PRODAJNI and s["do"]:
                red.append(T(f"Važi do: {s['do'].strftime(fmt)} (obnavlja se sama ako pretplata nije otkazana)",
                             f"Valid until: {s['do'].strftime(fmt)} (renews automatically unless the subscription is cancelled)"))
            if d.get("kljuc"):
                red.append(T("Ključ: ", "Key: ") + d["kljuc"][:4] + "…" + d["kljuc"][-4:] + (f"   ·   {d['email']}" if d.get("email") else ""))
            detalji.config(text="\n".join(red))
            dug_prov.configure(state="normal" if d.get("kljuc") else "disabled")
            dug_preb.configure(state="normal" if d.get("kljuc") else "disabled")
            self.osvezi_licenca_label()

        # cene
        cf = tk.Frame(b, bg=SURF)
        cf.pack(fill="x", pady=(4, 6))
        for i, p in enumerate(PRODAJNI):
            lim, cena = PAKETI[p]
            k = tk.Frame(cf, bg=SURF, highlightthickness=1, highlightbackground="#D5DDD7")
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            self.lbl(k, naziv_paketa(p), 11, "bold").pack(anchor="w", padx=10, pady=(8, 0))
            self.lbl(k, T(f"{cena} € godišnje", f"€{cena} per year"), 10, fg=BRAND).pack(anchor="w", padx=10)
            self.lbl(k, opis_limita(lim), 9, fg=INK2).pack(anchor="w", padx=10, pady=(0, 8))

        def kupi():
            import webbrowser
            webbrowser.open(KUPI_URL)
        self.btn(b, T("🛒 Kupi paket na sajtu…", "🛒 Buy a package on the website…"), kupi, "Primary").pack(anchor="w", pady=(4, 12))

        self.lbl(b, T("Ključ licence (stiže mejlom posle kupovine)", "Licence key (arrives by e-mail after purchase)"), 9, "bold", fg=INK2).pack(anchor="w")
        kr = tk.Frame(b, bg=SURF)
        kr.pack(fill="x", pady=(4, 0))
        kv = tk.StringVar()
        e = ttk.Entry(kr, textvariable=kv, width=40, font=self.f(10))
        e.pack(side="left")
        poruka = self.lbl(b, "", 10, "bold", fg=INK2, wraplength=470, justify="left")

        def u_pozadini(posao, uspeh):
            poruka.config(text=T("Proveravam ključ…", "Checking the key…"), fg=INK2)
            for w in (dug_akt, dug_prov, dug_preb):
                w.configure(state="disabled")
            rez = {}

            def nit():
                try:
                    rez["d"] = posao()
                except GreskaLicence as g:
                    rez["g"] = g
            t = threading.Thread(target=nit, daemon=True)
            t.start()

            def cekaj():
                if t.is_alive():
                    win.after(150, cekaj)
                    return
                if not win.winfo_exists():
                    return
                dug_akt.configure(state="normal")
                if "g" in rez:
                    poruka.config(text=poruka_greske(rez["g"]), fg=BAD)
                    prikazi()
                    return
                self._postavi_licencu(rez["d"])
                poruka.config(text=uspeh(rez["d"]), fg=OK)
                prikazi()
            cekaj()

        def aktiviraj_k():
            k = kv.get()
            if not k.strip():
                poruka.config(text=T("Nalepi ključ iz mejla.", "Paste the key from the e-mail."), fg=BAD)
                return
            u_pozadini(lambda: aktiviraj(self.lic(), k),
                       lambda d: T(f"✓ Licenca aktivirana – paket {naziv_paketa(d['paket'])}. Hvala!",
                                   f"✓ Licence activated – {naziv_paketa(d['paket'])} package. Thank you!"))
            kv.set("")

        def proveri_k():
            u_pozadini(lambda: proveri(self.lic()), lambda d: T("✓ Licenca je proverena.", "✓ The licence has been checked."))

        def prebaci():
            if not messagebox.askyesno(T("Prebaci licencu", "Move licence"),
                                       T("Ključ će biti uklonjen sa ovog računara, pa ćeš moći da ga upišeš na drugom.\n\n"
                                         "Na ovom računaru program prelazi na besplatnu verziju (podaci ostaju). Nastavi?",
                                         "The key will be removed from this computer so you can enter it on another one.\n\n"
                                         "On this computer the program switches to the free version (the data stays). Continue?"), parent=win):
                return
            u_pozadini(lambda: deaktiviraj(self.lic()),
                       lambda d: T("✓ Ključ je oslobođen. Sada ga upiši na drugom računaru.", "✓ The key has been released. Now enter it on the other computer."))
        dug_akt = self.btn(kr, T("Aktiviraj", "Activate"), aktiviraj_k, "Primary")
        dug_akt.pack(side="left", padx=(8, 0))
        e.bind("<Return>", lambda ev: aktiviraj_k())
        poruka.pack(anchor="w", pady=(8, 0))
        dr = tk.Frame(b, bg=SURF)
        dr.pack(fill="x", pady=(12, 0))
        dug_prov = self.btn(dr, T("Proveri sada", "Check now"), proveri_k)
        dug_prov.pack(side="left")
        dug_preb = self.btn(dr, T("Prebaci na drugi računar", "Move to another computer"), prebaci)
        dug_preb.pack(side="left", padx=(8, 0))
        self.btn(dr, T("Zatvori", "Close"), lambda: (win.grab_release(), win.destroy())).pack(side="right")
        self.lbl(b, T("Bez interneta program radi normalno; ključ se proverava kad ima interneta. Podaci se nikad ne brišu.",
                      "Without internet the program works normally; the key is checked when there is internet. Data is never deleted."),
                 8, fg="#8A968D", wraplength=470, justify="left").pack(anchor="w", pady=(12, 0))
        prikazi()
        e.focus_set()
