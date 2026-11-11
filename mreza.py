"""Udruženje: više farmi (računara) pod jednim paketom „Udruženje“.

- Udruženje napravi jedan računar (kancelarija ili prva farma) i na njemu se UPIŠE svaka farma. Za svaku farmu dobije
  kod (važi 7 dana) koji se upiše na računaru te farme.
- Svaka farma menja SAMO svoje podatke (svoju tablicu). Grla drugih farmi se samo PREGLEDAJU – ne ulaze u tvoju tablicu
  i nigde nema dugmeta za izmenu.
- Svaka farma šalje udruženju pregled svojih grla (bez napomena, cena, stada, kupca…), zaključan ključem udruženja
  (server vidi samo nečitljiv tekst) i POTPISAN ključem te farme. Spisak farmi potpisuje računar koji je napravio
  udruženje. Zato niko ne može da promeni ili podmetne podatke druge farme – takav pregled se odbaci.
"""
import hashlib
import html
import json
import os
import re
import secrets
import tempfile
import time
import tkinter as tk
from tkinter import messagebox, ttk

from jezik import T
from izgled import BAD, BRAND, INK2, OK, SURF, WARN
from oblak import Oblak, OblakGreska, b64u, iz_b64u, mesto_koda, novi_kod, norm_kod, otkljucaj, zakljucaj
from podaci import fmt_datum, parsiraj_datum

POZIV_TRAJANJE = 7 * 24 * 3600          # kod za upis farme važi 7 dana
SLANJE_MIN = 15                         # svoje podatke šalje udruženju najviše na 15 minuta (samo kad ima promena)
DELJENE_KOLONE = ("id", "markica", "vrsta", "rasa", "namena", "autohtona", "pol", "datum_rodjenja", "otac", "majka",
                  "status", "poreklo", "udeo_krvi", "ocena")
PAKETI_MREZE = ("udruzenje", "proba")


# ---------------------------------------------------------------- potpisi (Ed25519)
def novi_potpisni_kljuc():
    """(tajni, javni) – tajni ostaje samo na jednom računaru, javni je na spisku farmi."""
    from cryptography.hazmat.primitives import serialization as s
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    k = Ed25519PrivateKey.generate()
    tajni = k.private_bytes(s.Encoding.Raw, s.PrivateFormat.Raw, s.NoEncryption())
    javni = k.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)
    return b64u(tajni), b64u(javni)


def potpisi(tajni, tekst):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return b64u(Ed25519PrivateKey.from_private_bytes(iz_b64u(tajni)).sign(tekst.encode()))


def potpis_vazi(javni, tekst, potpis):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(iz_b64u(javni)).verify(iz_b64u(potpis), tekst.encode())
        return True
    except Exception:
        return False


def nova_mreza(naziv):
    tajni, javni = novi_potpisni_kljuc()
    return dict(udr=secrets.token_hex(24), kljuc=b64u(secrets.token_bytes(32)), naziv=" ".join(str(naziv).split()),
                admin_javni=javni, admin_tajni=tajni, uloga="admin", clanovi=[])


def novi_clan(naziv, mesto=""):
    """Farma na spisku: (zapis za spisak, tajni potpisni ključ koji ide samo toj farmi)."""
    tajni, javni = novi_potpisni_kljuc()
    return dict(id=secrets.token_hex(8), naziv=" ".join(str(naziv).split()), mesto=" ".join(str(mesto or "").split()),
                javni=javni), tajni


def pregled_farme(redovi, naziv, lokacija=None):
    """Šta farma pokazuje drugima: grla (samo osnovni podaci), bez obrisanih, i lokacija farme (ako je upisana)."""
    grla = [{k: r.get(k, "") for k in DELJENE_KOLONE} for r in redovi if (r.get("status") or "aktivno") != "obrisano"]
    d = dict(naziv=naziv, grla=grla, vreme=time.strftime("%Y-%m-%d %H:%M"))
    if lokacija:
        d["lokacija"] = lokacija
    return d


# ---------------------------------------------------------------- lokacija farme
_BROJ = r"(-?\d{1,3}(?:[.,]\d+)?)"


def procitaj_lokaciju(tekst):
    """'44.0123, 20.4567', '44,0123 20,4567' ili link sa Google mapa -> {'lat': 44.0123, 'lon': 20.4567} ili None."""
    s = str(tekst or "").strip()
    if not s:
        return None
    for obrazac in (r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",                       # tačno mesto na Google mapama
                    r"[?&](?:q|query|ll|center|destination)=(-?\d+\.\d+)(?:,|%2C)\s*(-?\d+\.\d+)",
                    r"@(-?\d+\.\d+),(-?\d+\.\d+)",
                    r"^\s*(-?\d{1,3}\.\d+)\s*[,; ]\s*(-?\d{1,3}\.\d+)\s*$",
                    r"^\s*(-?\d{1,3},\d+)\s*[; ]\s*(-?\d{1,3},\d+)\s*$"):
        x = re.search(obrazac, s)
        if x:
            lat, lon = (float(v.replace(",", ".")) for v in x.groups())
            if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat, lon) != (0, 0):
                return dict(lat=round(lat, 6), lon=round(lon, 6))
    return None


def lokacija_iz_teksta(tekst):
    """Koordinate, link sa Google mapa ili samo naziv mesta / adresa ('Prijevor, Čačak')."""
    lok = procitaj_lokaciju(tekst)
    if lok:
        return lok
    s = " ".join(str(tekst or "").split())
    if len(s) >= 3 and re.search(r"[^\W\d_]", s) and not s.lower().startswith("http"):
        return dict(adresa=s[:120])
    return None


def ima_koordinate(lok):
    return bool(lok) and isinstance(lok.get("lat"), (int, float)) and isinstance(lok.get("lon"), (int, float))


def tekst_lokacije(lok):
    if not lok:
        return ""
    if lok.get("adresa"):
        return lok["adresa"]
    return f"{lok['lat']:.5f}, {lok['lon']:.5f}" if ima_koordinate(lok) else ""


def mapa_url(lok):
    from urllib.parse import quote
    if ima_koordinate(lok):
        return f"https://www.google.com/maps/search/?api=1&query={lok['lat']},{lok['lon']}"
    return "https://www.google.com/maps/search/?api=1&query=" + quote(lok.get("adresa", ""))


def nadji_koordinate(adresa):
    """Naziv mesta -> (lat, lon) preko OpenStreetMap pretrage (samo kad se lokacija sačuva). None ako ne nađe."""
    import urllib.request
    from urllib.parse import urlencode
    for upit in varijante_adrese(adresa):        # cela adresa, pa bez kućnog broja, pa samo mesto
        url = "https://nominatim.openstreetmap.org/search?" + urlencode(dict(q=upit, format="json", limit=1))
        zahtev = urllib.request.Request(url, headers={"User-Agent": "HerdDoc (https://herddoc.com)", "Accept-Language": "sr,en"})
        with urllib.request.urlopen(zahtev, timeout=10) as r:
            nadjeno = json.loads(r.read().decode("utf-8"))
        if nadjeno:
            return round(float(nadjeno[0]["lat"]), 6), round(float(nadjeno[0]["lon"]), 6)
        time.sleep(1.1)                            # OpenStreetMap traži najviše jednu pretragu u sekundi
    return None


def varijante_adrese(adresa):
    """Šta se traži na mapi, redom: cela adresa, bez kućnog broja, pa samo mesto
    ('Nabrđe Borisa Kidriča 6a' -> ['Nabrđe Borisa Kidriča 6a', 'Nabrđe Borisa Kidriča', 'Nabrđe'])."""
    a = " ".join(str(adresa).split())
    bez_broja = re.sub(r"\s+,", ",", " ".join(re.sub(r"\b\d+[a-zA-Z]?\b|\bbb\b", " ", a, flags=re.I).split())).strip(" ,")
    delovi = [d.strip() for d in bez_broja.split(",") if d.strip()]
    mesto = delovi[-1] if len(delovi) > 1 else (bez_broja.split() or [""])[0]
    rez = []
    for x in (a, bez_broja, mesto):
        if x and x not in rez:
            rez.append(x)
    return rez


def mapa_html(farme, naslov):
    """Stranica sa svim farmama na mapi (OpenStreetMap). farme: [(naziv, mesto, broj grla, lokacija)]."""
    tacke = [dict(n=n, m=m or "", g=g, lat=l["lat"], lon=l["lon"], url=mapa_url(l)) for n, m, g, l in farme if ima_koordinate(l)]
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(naslov)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body{{margin:0;height:100%;font-family:Segoe UI,Arial,sans-serif}}#mapa{{height:100%}}
.naslov{{position:absolute;z-index:999;top:10px;left:56px;background:#fff;padding:8px 14px;border-radius:10px;
box-shadow:0 2px 8px rgba(0,0,0,.2);font-weight:700;color:#2E5E4E}}</style></head><body>
<div class="naslov">{html.escape(naslov)}</div><div id="mapa"></div><script>
const T = {json.dumps(tacke, ensure_ascii=False)};
const esc = s => String(s).replace(/[&<>"]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}})[c]);
const map = L.map("mapa");
L.tileLayer("https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}}).addTo(map);
const g = T.map(t => L.marker([t.lat, t.lon]).addTo(map).bindPopup(`<b>${{esc(t.n)}}</b><br>${{esc(t.m)}}<br>${{t.g}} {html.escape(T("grla", "animals"))}<br><a href="${{t.url}}" target="_blank">Google {html.escape(T("mape", "Maps"))}</a>`));
if (g.length) map.fitBounds(L.featureGroup(g).getBounds().pad(0.3), {{maxZoom: 13}}); else map.setView([44.0, 20.9], 7);
</script></body></html>"""


# ---------------------------------------------------------------- oblak udruženja
def oblak_mreze(konfig, m):
    return Oblak(konfig, m["udr"], m["kljuc"])


def objavi_spisak(o, m):
    """Spisak farmi – potpisuje ga samo računar koji je napravio udruženje."""
    tekst = zakljucaj(dict(naziv=m["naziv"], clanovi=[{k: c[k] for k in ("id", "naziv", "mesto", "javni")}
                                                      for c in m.get("clanovi", [])]), m["kljuc"])
    o.upisi("spisak", "glavni", dict(podaci=tekst, potpis=potpisi(m["admin_tajni"], tekst)))


def procitaj_spisak(o, m):
    d = o.citaj("spisak", "glavni")
    if not d or not d.get("podaci"):
        return None
    if not potpis_vazi(m["admin_javni"], d["podaci"], d.get("potpis", "")):
        raise OblakGreska(T("Spisak farmi nije potpisan od udruženja – odbačen.", "The farm list is not signed by the association – rejected."))
    return otkljucaj(d["podaci"], m["kljuc"])


def objavi_pregled(o, m, sadrzaj):
    tekst = zakljucaj(sadrzaj, m["kljuc"])
    ukupno = o.upisi_veliko("pregledi", m["clan"], tekst)
    o.upisi("stanje", m["clan"], dict(ukupno=ukupno, potpis=potpisi(m["clan_tajni"], tekst), vreme=sadrzaj.get("vreme", "")))


def procitaj_preglede(o, m, spisak):
    """{id farme: pregled} – samo pregledi koje je potpisala baš ta farma (ključem sa spiska)."""
    rez = {}
    for c in spisak.get("clanovi", []):
        try:
            st = o.citaj("stanje", c["id"])
            if not st:
                rez[c["id"]] = dict(naziv=c["naziv"], grla=[], vreme="", greska=T("još nije poslala podatke", "has not sent data yet"))
                continue
            tekst = o.procitaj_veliko("pregledi", c["id"], st.get("ukupno") or 1)
            if not potpis_vazi(c["javni"], tekst, st.get("potpis", "")):
                rez[c["id"]] = dict(naziv=c["naziv"], grla=[], vreme="", greska=T("podaci nisu potpisani od ove farme", "data not signed by this farm"))
                continue
            p = otkljucaj(tekst, m["kljuc"])
            p["naziv"] = c["naziv"]                  # naziv uvek sa spiska udruženja
            rez[c["id"]] = p
        except OblakGreska as e:
            if e.bez_mreze:
                raise
            rez[c["id"]] = dict(naziv=c["naziv"], grla=[], vreme="", greska=str(e))
    return rez


def objavi_poziv(konfig, kod, poziv):
    mesto, k = mesto_koda(kod)
    istice = int(time.time()) + POZIV_TRAJANJE
    Oblak(konfig, mesto, k).upisi("poziv", "kod", dict(podaci=zakljucaj(dict(poziv, istice=istice), k), istice=istice))
    return istice


def preuzmi_poziv(konfig, kod):
    mesto, k = mesto_koda(kod)
    o = Oblak(konfig, mesto, k)
    d = o.citaj("poziv", "kod")
    if not d or not d.get("podaci"):
        return None
    p = otkljucaj(d["podaci"], k)
    if int(p.get("istice", 0)) < time.time():
        return None
    try:
        o.obrisi("poziv", "kod")                     # kod važi samo jednom
    except OblakGreska:
        pass
    return p


def dat(tekst):
    """'2026-11-11' -> '11.11.2026.' (po jeziku programa)."""
    return fmt_datum(parsiraj_datum(tekst)) or str(tekst or "")


def prosek_ocene(tekst):
    from ocene import procitaj_ocenu
    v = list(procitaj_ocenu(tekst)[0].values())
    return f"★ {sum(v) / len(v):.1f}" if v else ""


# ---------------------------------------------------------------- deo programa
class MrezaDeo:
    """Strana „Udruženje“: upis farmi, slanje svojih podataka i pregled grla drugih farmi (bez izmene)."""

    def mreza(self):
        m = self.pod.get("mreza")
        return m if isinstance(m, dict) and m.get("udr") else None

    def mreza_dozvoljena(self):
        try:
            return self.lic_stanje()["paket"] in PAKETI_MREZE
        except Exception:
            return False

    def mreza_za_telefon(self):
        """Telefonu (samo preko šifrovanog usklađivanja, nikad u fajlu) ide samo ono što treba za PREGLED drugih farmi –
        bez tajnih ključeva za potpis, pa telefon ne može ništa da pošalje u ime farme ni udruženja."""
        m = self.mreza()
        if not m or not self.mreza_dozvoljena():
            return None
        return {k: m.get(k, "") for k in ("udr", "kljuc", "naziv", "admin_javni", "clan", "naziv_farme")}

    def _mreza_konfig(self):
        return self.sinh_konfig()

    # ---------- slanje svojih podataka
    def mreza_posalji(self, odmah=False, kraj=None):
        m = self.mreza()
        if not m or not m.get("clan") or not self.mreza_dozvoljena() or not self.sinh_podeseno():
            return
        sadrzaj = pregled_farme(self.tab.redovi, m.get("naziv_farme", ""), self.pod.get("lokacija"))
        hes = hashlib.sha256(json.dumps([sadrzaj["grla"], sadrzaj.get("lokacija")], sort_keys=True,
                                        ensure_ascii=False).encode()).hexdigest()
        if hes == m.get("poslato_hes") and not odmah:
            return
        konfig = self._mreza_konfig()

        def gotovo(_, greska):
            if greska is None:
                m["poslato_hes"], m["poslato"] = hes, sadrzaj["vreme"]
                self.sacuvaj_podesavanja()
            if kraj:
                kraj(greska)
        self._u_pozadini(lambda: objavi_pregled(oblak_mreze(konfig, m), m, sadrzaj), gotovo)

    def mreza_petlja(self):
        try:
            self.mreza_posalji()
        except Exception:
            pass
        self.root.after(SLANJE_MIN * 60 * 1000, self.mreza_petlja)

    # ---------- strana
    def s_mreza(self):
        body = self.strana_okvir()
        m = self.mreza()
        if not self.mreza_dozvoljena():
            self.zaglavlje(body, T("Udruženje", "Association"),
                           T("Više farmi zajedno: svaka farma menja samo svoje podatke, a grla drugih farmi samo pregleda.",
                             "Several farms together: each farm changes only its own data and can only view the animals of other farms."))
            o, c = self.card(body)
            o.pack(fill="x")
            self.lbl(c, T("Dostupno u paketu Udruženje (do 5 računara).", "Available in the Association package (up to 5 computers)."),
                     12, "bold").pack(anchor="w")
            self.btn(c, T("Pogledaj pakete", "See packages"), self.prozor_licence, "Primary").pack(anchor="w", pady=(10, 0))
            return
        if not self.sinh_podeseno():
            self.zaglavlje(body, T("Udruženje", "Association"))
            self.lbl(body, T("Biće dostupno u sledećoj verziji programa.", "Will be available in the next version."), 11, fg=INK2).pack(anchor="w")
            return
        if not m:
            self._mreza_pocetak(body)
            return
        admin = m.get("uloga") == "admin"
        self.zaglavlje(body, T(f"Udruženje: {m['naziv']}", f"Association: {m['naziv']}"),
                       T("Svaka farma menja samo svoje podatke. Grla drugih farmi ovde možeš samo da pogledaš.",
                         "Each farm changes only its own data. Here you can only view the animals of other farms."),
                       [(T("⟳ Osveži", "⟳ Refresh"), lambda: self._mreza_ucitaj(True), "Secondary")])
        self._mreza_farme_kartica(body, m, admin)
        self._mreza_grla_kartica(body)
        self._mreza_moje_kartica(body, m)
        if getattr(self, "_mreza_podaci", None) is None:
            self._mreza_ucitaj(False)

    def _mreza_ucitaj(self, rucno):
        m = self.mreza()
        if not m:
            return
        konfig = self._mreza_konfig()
        self._mreza_status = T("⟳ učitavam podatke farmi…", "⟳ loading farm data…")
        if hasattr(self, "_mreza_lbl") and self._mreza_lbl.winfo_exists():
            self._mreza_lbl.config(text=self._mreza_status, fg=INK2)

        def posao():
            o = oblak_mreze(konfig, m)
            spisak = procitaj_spisak(o, m) or dict(naziv=m["naziv"], clanovi=[])
            return spisak, procitaj_preglede(o, m, spisak)

        def kraj(rez, greska):
            if greska is not None:
                self._mreza_status = T("Nema veze sa udruženjem: ", "No connection to the association: ") + str(greska)
                self._mreza_podaci = getattr(self, "_mreza_podaci", None) or ({}, {})
            else:
                spisak, pregledi = rez
                if m.get("uloga") != "admin":
                    m["clanovi"] = spisak.get("clanovi", [])
                    m["naziv"] = spisak.get("naziv", m["naziv"])
                self._mreza_podaci = (spisak, pregledi)
                self._mreza_status = T(f"Učitano {time.strftime('%H:%M')}", f"Loaded {time.strftime('%H:%M')}")
            if self.strana == "mreza":
                self.prikazi("mreza")
        self._u_pozadini(posao, kraj)
        if rucno:
            self.mreza_posalji(odmah=True)

    def _mreza_pocetak(self, body):
        self.zaglavlje(body, T("Udruženje", "Association"),
                       T("Više farmi zajedno. Udruženje se napravi na jednom računaru i tamo se upiše svaka farma. "
                         "Svaka farma menja samo svoje podatke, a grla drugih farmi samo pregleda.",
                         "Several farms together. The association is created on one computer, where every farm is registered. "
                         "Each farm changes only its own data and can only view the animals of other farms."))
        red = tk.Frame(body, bg=body.cget("bg"))
        red.pack(fill="x")
        o1, c1 = self.card(red)
        o1.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.lbl(c1, T("Napravi udruženje", "Create an association"), 13, "bold").pack(anchor="w")
        self.lbl(c1, T("Na ovom računaru upisuješ farme (kancelarija udruženja ili prva farma).",
                       "On this computer you register the farms (association office or the first farm)."),
                 9, fg=INK2, wraplength=330, justify="left").pack(anchor="w", pady=(2, 10))
        v_udr, v_farma, v_mesto = tk.StringVar(), tk.StringVar(), tk.StringVar()
        v_je_farma = tk.BooleanVar(value=True)
        for tekst, var in ((T("Naziv udruženja *", "Association name *"), v_udr), (T("Naziv ove farme", "This farm's name"), v_farma),
                           (T("Mesto", "Place"), v_mesto)):
            self.lbl(c1, tekst, 9, "bold", fg=INK2).pack(anchor="w")
            ttk.Entry(c1, textvariable=var, width=34, font=self.f(10)).pack(anchor="w", pady=(0, 8))
        ttk.Checkbutton(c1, text=T("Na ovom računaru je i farma (ima svoja grla)", "This computer is also a farm (has its own animals)"),
                        variable=v_je_farma).pack(anchor="w")
        e1 = self.lbl(c1, "", 9, "bold", fg=BAD, wraplength=330, justify="left")
        e1.pack(anchor="w")

        def napravi():
            if not v_udr.get().strip():
                e1.config(text=T("Upiši naziv udruženja.", "Enter the association name."))
                return
            if v_je_farma.get() and not v_farma.get().strip():
                e1.config(text=T("Upiši naziv ove farme.", "Enter this farm's name."))
                return
            m = nova_mreza(v_udr.get())
            if v_je_farma.get():
                c, tajni = novi_clan(v_farma.get(), v_mesto.get())
                m["clanovi"].append(c)
                m.update(clan=c["id"], clan_tajni=tajni, naziv_farme=c["naziv"])
            konfig = self._mreza_konfig()

            def kraj(_, greska):
                if greska is not None:
                    e1.config(text=str(greska))
                    return
                self.pod["mreza"] = m
                self.sacuvaj_podesavanja()
                self._mreza_podaci = None
                self.toast(T("Udruženje je napravljeno. Sada upiši farme.", "Association created. Now register the farms."))
                self.mreza_posalji(odmah=True)
                self.prikazi("mreza")
            self._u_pozadini(lambda: objavi_spisak(oblak_mreze(konfig, m), m), kraj)
        self.btn(c1, T("Napravi udruženje", "Create association"), napravi, "Primary").pack(anchor="w", pady=(10, 0))

        o2, c2 = self.card(red)
        o2.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.lbl(c2, T("Pridruži se udruženju", "Join an association"), 13, "bold").pack(anchor="w")
        self.lbl(c2, T("Upiši kod koji si dobio od udruženja (kad su upisali tvoju farmu).",
                       "Enter the code you got from the association (when they registered your farm)."),
                 9, fg=INK2, wraplength=330, justify="left").pack(anchor="w", pady=(2, 10))
        v_kod = tk.StringVar()
        self.lbl(c2, T("Kod *", "Code *"), 9, "bold", fg=INK2).pack(anchor="w")
        ttk.Entry(c2, textvariable=v_kod, width=16, font=self.f(14)).pack(anchor="w", pady=(0, 8))
        e2 = self.lbl(c2, "", 9, "bold", fg=BAD, wraplength=330, justify="left")
        e2.pack(anchor="w")

        def pridruzi():
            if len(norm_kod(v_kod.get())) != 8:
                e2.config(text=T("Kod ima 8 znakova, npr. K7M2-9XQP.", "The code has 8 characters, e.g. K7M2-9XQP."))
                return
            konfig = self._mreza_konfig()
            e2.config(text=T("⟳ proveravam kod…", "⟳ checking the code…"), fg=INK2)

            def kraj(p, greska):
                if greska is not None or not p:
                    e2.config(text=str(greska) if greska else T("Kod ne postoji, iskorišćen je ili je istekao. Traži novi od udruženja.",
                                                                "The code does not exist, was used or has expired. Ask the association for a new one."), fg=BAD)
                    return
                self.pod["mreza"] = dict(udr=p["udr"], kljuc=p["kljuc"], naziv=p["naziv"], admin_javni=p["admin_javni"],
                                         uloga="clan", clan=p["clan"], clan_tajni=p["clan_tajni"], naziv_farme=p["naziv_farme"],
                                         clanovi=[])
                self.sacuvaj_podesavanja()
                self._mreza_podaci = None
                self.toast(T(f"Farma „{p['naziv_farme']}“ je u udruženju {p['naziv']}.", f"Farm “{p['naziv_farme']}” joined {p['naziv']}."))
                self.mreza_posalji(odmah=True)
                self.prikazi("mreza")
            kod = v_kod.get()                          # Tk se čita samo u glavnom delu programa
            self._u_pozadini(lambda: preuzmi_poziv(konfig, kod), kraj)
        self.btn(c2, T("Pridruži se", "Join"), pridruzi, "Primary").pack(anchor="w", pady=(10, 0))

    def _mreza_farme_kartica(self, body, m, admin):
        o, c = self.card(body)
        o.pack(fill="x", pady=(0, 12))
        gore = tk.Frame(c, bg=SURF)
        gore.pack(fill="x")
        self.lbl(gore, T("Farme u udruženju", "Farms in the association"), 13, "bold").pack(side="left")
        _, pregledi = getattr(self, "_mreza_podaci", None) or ({}, {})

        def lok_farme(c_):
            return self.pod.get("lokacija") if c_["id"] == m.get("clan") else pregledi.get(c_["id"], {}).get("lokacija")
        self.btn(gore, T("🗺 Sve farme na mapi", "🗺 All farms on a map"), lambda: self.mreza_mapa(
            [(c_["naziv"], c_.get("mesto", ""), sum(1 for g in pregledi.get(c_["id"], {}).get("grla", [])
                                                 if (g.get("status") or "aktivno") == "aktivno"), lok_farme(c_))
             for c_ in m.get("clanovi", [])]), "Secondary").pack(side="right")
        wrap, tv = self.tabela(c, [("farma", T("Farma", "Farm"), 220), ("mesto", T("Mesto", "Place"), 150),
                                   ("lok", T("Lokacija", "Location"), 90),
                                   ("grla", T("Grla", "Animals"), 70, "e"), ("vreme", T("Poslednje slanje", "Last sent"), 200)],
                               visina=min(8, max(3, len(m.get("clanovi", [])))))
        wrap.pack(fill="x", pady=(8, 0))
        for c_ in m.get("clanovi", []):
            p = pregledi.get(c_["id"], {})
            akt = sum(1 for g in p.get("grla", []) if (g.get("status") or "aktivno") == "aktivno")
            ja = c_["id"] == m.get("clan")
            tv.insert("", "end", iid="f|" + c_["id"], text=c_["naziv"] + (T("  (ova farma)", "  (this farm)") if ja else ""),
                      values=(c_.get("mesto", ""), T("📍 mapa", "📍 map") if lok_farme(c_) else "–", akt if p else "",
                              p.get("greska") or p.get("vreme", "")),
                      tags=("bad",) if p.get("greska") and not ja else ())

        def na_mapi(e):
            c_ = next((x for x in m.get("clanovi", []) if "f|" + x["id"] == tv.identify_row(e.y)), None)
            if c_ and lok_farme(c_):
                self.otvori_link(mapa_url(lok_farme(c_)))
            elif c_:
                self.toast(T(f"Farma „{c_['naziv']}“ još nije upisala lokaciju.", f"The farm “{c_['naziv']}” has not set its location yet."))
        tv.bind("<Double-1>", na_mapi)
        self.lbl(c, T("Dvoklik na farmu otvara njenu lokaciju na Google mapama.", "Double-click a farm to open its location in Google Maps."),
                 9, fg=INK2).pack(anchor="w", pady=(4, 0))
        if not admin:
            return
        dug = tk.Frame(c, bg=SURF)
        dug.pack(fill="x", pady=(10, 0))

        def izabrana():
            s = tv.selection()
            return next((x for x in m["clanovi"] if "f|" + x["id"] == s[0]), None) if s else None

        def nov_kod_za(clan):
            """Novi ključ za farmu (stari kod/ključ više ne važi) i kod koji se upiše na njenom računaru."""
            tajni, clan["javni"] = novi_potpisni_kljuc()
            kod = novi_kod()
            poziv = dict(udr=m["udr"], kljuc=m["kljuc"], naziv=m["naziv"], admin_javni=m["admin_javni"], clan=clan["id"],
                         clan_tajni=tajni, naziv_farme=clan["naziv"])
            konfig = self._mreza_konfig()

            def posao():
                objavi_spisak(oblak_mreze(konfig, m), m)
                return objavi_poziv(konfig, kod, poziv)

            def kraj(istice, greska):
                if greska is not None:
                    messagebox.showerror("HerdDoc", str(greska), parent=self.root)
                    return
                self.sacuvaj_podesavanja()
                self._mreza_kod_prozor(clan, kod, istice)
                self.prikazi("mreza")
            self._u_pozadini(posao, kraj)

        def upisi():
            def gotovo(naziv, mesto):
                nova = novi_clan(naziv, mesto)[0]
                m["clanovi"].append(nova)
                nov_kod_za(nova)
            self._mreza_upis_farme(gotovo)

        def kod():
            x = izabrana()
            if not x:
                self.toast(T("Izaberi farmu na spisku.", "Select a farm in the list."))
                return
            if x["id"] == m.get("clan"):
                self.toast(T("To je ova farma – njoj ne treba kod.", "That is this farm – it does not need a code."))
                return
            if messagebox.askyesno("HerdDoc", T(f"Napraviti novi kod za farmu „{x['naziv']}“?\n\nStari kod i stari ključ te farme "
                                                "prestaju da važe – farma mora da upiše novi kod.",
                                                f"Make a new code for the farm “{x['naziv']}”?\n\nThe old code and key of that farm "
                                                "stop working – the farm has to enter the new code."), parent=self.root):
                nov_kod_za(x)

        def ukloni():
            x = izabrana()
            if not x:
                self.toast(T("Izaberi farmu na spisku.", "Select a farm in the list."))
                return
            if x["id"] == m.get("clan"):
                self.toast(T("Ova farma ne može da se ukloni.", "This farm cannot be removed."))
                return
            if not messagebox.askyesno("HerdDoc", T(f"Ukloniti farmu „{x['naziv']}“ iz udruženja?\n\nNjeni podaci se više neće videti.",
                                                    f"Remove the farm “{x['naziv']}” from the association?\n\nIts data will no longer be shown."),
                                       parent=self.root):
                return
            m["clanovi"] = [y for y in m["clanovi"] if y is not x]
            konfig = self._mreza_konfig()

            def posao():
                o_ = oblak_mreze(konfig, m)
                objavi_spisak(o_, m)
                for kol, dok in [("stanje", x["id"])] + [("pregledi", f"{x['id']}_{n:03d}") for n in range(5)]:
                    try:
                        o_.obrisi(kol, dok)
                    except OblakGreska:
                        pass

            def kraj(_, greska):
                if greska is not None:
                    messagebox.showerror("HerdDoc", str(greska), parent=self.root)
                self.sacuvaj_podesavanja()
                self.prikazi("mreza")
            self._u_pozadini(posao, kraj)
        self.btn(dug, T("+ Upiši farmu", "+ Register farm"), upisi, "Primary").pack(side="left")
        self.btn(dug, T("Novi kod", "New code"), kod).pack(side="left", padx=8)
        self.btn(dug, T("Ukloni farmu", "Remove farm"), ukloni, "Danger").pack(side="left")
        self.lbl(dug, T(f"{len(m['clanovi'])} farmi upisano", f"{len(m['clanovi'])} farms registered"), 9, fg=INK2).pack(side="right")

    def _mreza_upis_farme(self, gotovo):
        win = tk.Toplevel(self.root)
        win.title(T("Upiši farmu", "Register farm"))
        win.configure(bg=SURF)
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Upiši farmu", "Register farm"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Farma dobija kod koji upisuje na svom računaru (Udruženje → Pridruži se).",
                      "The farm gets a code to enter on its computer (Association → Join)."), 9, fg=INK2, wraplength=360,
                 justify="left").pack(anchor="w", pady=(2, 12))
        v_n, v_m = tk.StringVar(), tk.StringVar()
        for tekst, var in ((T("Naziv farme *", "Farm name *"), v_n), (T("Mesto", "Place"), v_m)):
            self.lbl(b, tekst, 9, "bold", fg=INK2).pack(anchor="w")
            e = ttk.Entry(b, textvariable=var, width=36, font=self.f(10))
            e.pack(anchor="w", pady=(0, 8))
            if var is v_n:
                e.focus_set()
        err = self.lbl(b, "", 9, "bold", fg=BAD)
        err.pack(anchor="w")
        m = self.mreza()

        def ok(e=None):
            n = " ".join(v_n.get().split())
            if not n:
                err.config(text=T("Upiši naziv farme.", "Enter the farm name."))
                return
            if any(c["naziv"].lower() == n.lower() for c in m.get("clanovi", [])):
                err.config(text=T("Farma sa tim nazivom je već upisana.", "A farm with that name is already registered."))
                return
            win.destroy()
            gotovo(n, v_m.get())
        f = tk.Frame(b, bg=SURF)
        f.pack(fill="x", pady=(12, 0))
        self.btn(f, T("Upiši i napravi kod", "Register and make code"), ok, "Primary").pack(side="right")
        self.btn(f, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", ok)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, self.root)

    def _mreza_kod_prozor(self, clan, kod, istice):
        win = tk.Toplevel(self.root)
        win.title(T("Kod za farmu", "Farm code"))
        win.configure(bg=SURF)
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=30, pady=24)
        self.lbl(b, T(f"Kod za farmu „{clan['naziv']}“", f"Code for the farm “{clan['naziv']}”"), 14, "bold").pack(anchor="w")
        self.lbl(b, kod, 30, "bold", fg=BRAND).pack(anchor="w", pady=(12, 6))
        self.lbl(b, T(f"Važi do {dat(time.strftime('%Y-%m-%d', time.localtime(istice)))} i samo jednom.",
                      f"Valid until {dat(time.strftime('%Y-%m-%d', time.localtime(istice)))}, once only."), 10, fg=INK2).pack(anchor="w")
        self.lbl(b, T("Na računaru te farme: HerdDoc → Udruženje → Pridruži se → upiši ovaj kod.\n"
                      "Kod daj samo toj farmi – sa njim se šalju podaci u ime te farme.",
                      "On that farm's computer: HerdDoc → Association → Join → enter this code.\n"
                      "Give the code only to that farm – it is used to send data on behalf of that farm."),
                 10, wraplength=420, justify="left").pack(anchor="w", pady=(12, 0))
        f = tk.Frame(b, bg=SURF)
        f.pack(fill="x", pady=(16, 0))
        self.btn(f, T("Zatvori", "Close"), win.destroy, "Primary").pack(side="right")
        self.btn(f, T("Kopiraj kod", "Copy code"), lambda: (self.root.clipboard_clear(), self.root.clipboard_append(kod),
                                                            self.toast(T("Kod je kopiran.", "Code copied.")))).pack(side="right", padx=8)
        self.postavi_prozor(win, self.root)
        return win

    def _mreza_grla_kartica(self, body):
        m = self.mreza()
        _, pregledi = getattr(self, "_mreza_podaci", None) or ({}, {})
        o, c = self.card(body)
        o.pack(fill="x", pady=(0, 12))
        gore = tk.Frame(c, bg=SURF)
        gore.pack(fill="x")
        self.lbl(gore, T("🔒 Grla drugih farmi – samo pregled", "🔒 Animals of other farms – view only"), 13, "bold").pack(side="left")
        self.lbl(c, T("Ove podatke menja samo farma kojoj grla pripadaju. Ne ulaze u tvoju tablicu.",
                      "Only the farm that owns the animals changes this data. They do not go into your table."),
                 9, fg=INK2).pack(anchor="w", pady=(2, 8))
        druge = {k: p for k, p in pregledi.items() if k != m.get("clan")}
        sva = [(p["naziv"], g) for p in druge.values() for g in p.get("grla", [])]
        filt = tk.Frame(c, bg=SURF)
        filt.pack(fill="x", pady=(0, 8))
        sve_f, sve_v = T("Sve farme", "All farms"), T("Sve vrste", "All species")
        v_f, v_v, v_p, v_q = tk.StringVar(value=sve_f), tk.StringVar(value=sve_v), tk.StringVar(value=T("Svi", "All")), tk.StringVar()
        v_akt = tk.BooleanVar(value=True)
        ttk.Combobox(filt, textvariable=v_f, values=[sve_f] + sorted({n for n, _ in sva}), state="readonly", width=20,
                     font=self.f(10)).pack(side="left")
        ttk.Combobox(filt, textvariable=v_v, values=[sve_v] + sorted({g.get("vrsta", "") for _, g in sva if g.get("vrsta")}),
                     state="readonly", width=12, font=self.f(10)).pack(side="left", padx=6)
        polovi = {T("Svi", "All"): None, T("Muški", "Male"): "m", T("Ženski", "Female"): "z"}
        ttk.Combobox(filt, textvariable=v_p, values=list(polovi), state="readonly", width=8, font=self.f(10)).pack(side="left")
        ttk.Entry(filt, textvariable=v_q, width=18, font=self.f(10)).pack(side="left", padx=6)
        ttk.Checkbutton(filt, text=T("samo aktivna", "active only"), variable=v_akt).pack(side="left")
        wrap, tv = self.tabela(c, [("oz", T("Grlo", "Animal"), 110), ("farma", T("Farma", "Farm"), 150), ("vrsta", T("Vrsta", "Species"), 80),
                                   ("rasa", T("Rasa", "Breed"), 120), ("pol", T("Pol", "Sex"), 50), ("rodj", T("Rođeno", "Born"), 90),
                                   ("otac", T("Otac", "Sire"), 90), ("majka", T("Majka", "Dam"), 90), ("ocena", T("Ocena", "Score"), 70)],
                               visina=12)
        wrap.pack(fill="both", expand=True)
        brojac = self.lbl(c, "", 9, fg=INK2)
        brojac.pack(anchor="w", pady=(6, 0))
        po_iid = {}

        def osvezi(*_):
            tv.delete(*tv.get_children())
            po_iid.clear()
            q = v_q.get().strip().lower()
            n = 0
            for i, (farma, g) in enumerate(sorted(sva, key=lambda x: (x[0].lower(), str(x[1].get("id", "")).lower()))):
                if v_f.get() != sve_f and farma != v_f.get():
                    continue
                if v_v.get() != sve_v and g.get("vrsta") != v_v.get():
                    continue
                if polovi.get(v_p.get()) and g.get("pol") != polovi[v_p.get()]:
                    continue
                if v_akt.get() and (g.get("status") or "aktivno") != "aktivno":
                    continue
                if q and q not in " ".join(str(g.get(k, "")) for k in ("id", "markica", "rasa", "otac", "majka")).lower() + " " + farma.lower():
                    continue
                iid = f"m|{i}"
                po_iid[iid] = (farma, g)
                tv.insert("", "end", iid=iid, text=g.get("id", ""), values=(
                    farma, g.get("vrsta", ""), g.get("rasa", ""), {"m": "♂", "z": "♀"}.get(g.get("pol"), ""),
                    dat(g.get("datum_rodjenja", "")), g.get("otac", ""), g.get("majka", ""), prosek_ocene(g.get("ocena"))),
                    tags=("odd",) if n % 2 else ())
                n += 1
            brojac.config(text=T(f"{n} grla", f"{n} animals") if sva else
                          (T("Druge farme još nisu poslale podatke.", "Other farms have not sent data yet.")))
        for v in (v_f, v_v, v_p, v_q, v_akt):
            v.trace_add("write", osvezi)
        osvezi()
        tv.bind("<Double-1>", lambda e: po_iid.get(tv.identify_row(e.y)) and self._mreza_grlo_prozor(*po_iid[tv.identify_row(e.y)]))

    def _mreza_grlo_prozor(self, farma, g):
        win = tk.Toplevel(self.root)
        win.title(str(g.get("id", "")))
        win.configure(bg=SURF)
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=28, pady=22)
        self.lbl(b, str(g.get("id", "")), 18, "bold").pack(anchor="w")
        self.lbl(b, T(f"🔒 Samo pregled – menja ga samo farma {farma}", f"🔒 View only – only the farm {farma} changes it"),
                 9, "bold", fg=WARN).pack(anchor="w", pady=(2, 12))
        mreza_ = tk.Frame(b, bg=SURF)
        mreza_.pack(fill="x")
        polja = [(T("Farma", "Farm"), farma), (T("Markica", "Ear tag"), g.get("markica")), (T("Vrsta", "Species"), g.get("vrsta")),
                 (T("Rasa", "Breed"), g.get("rasa")), (T("Namena", "Purpose"), g.get("namena")),
                 (T("Pol", "Sex"), {"m": T("muški", "male"), "z": T("ženski", "female")}.get(g.get("pol"), "")),
                 (T("Rođeno", "Born"), dat(g.get("datum_rodjenja", ""))), (T("Otac", "Sire"), g.get("otac")),
                 (T("Majka", "Dam"), g.get("majka")), (T("Status", "Status"), g.get("status")),
                 (T("Udeo krvi", "Breed share"), g.get("udeo_krvi")), (T("Ocena", "Score"), prosek_ocene(g.get("ocena"))),
                 (T("Autohtona rasa", "Native breed"), "✓" if g.get("autohtona") else "")]
        for i, (n, v) in enumerate(p for p in polja if p[1]):
            self.lbl(mreza_, n, 9, "bold", fg=INK2).grid(row=i, column=0, sticky="w", pady=2, padx=(0, 16))
            self.lbl(mreza_, str(v), 10).grid(row=i, column=1, sticky="w", pady=2)
        self.btn(b, T("Zatvori", "Close"), win.destroy, "Primary").pack(anchor="e", pady=(16, 0))
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, self.root)
        return win

    def otvori_link(self, url):
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("HerdDoc", str(e), parent=self.root)

    def mreza_mapa(self, farme):
        if not any(ima_koordinate(l) for *_, l in farme):
            self.toast(T("Nijedna farma još nije upisala lokaciju.", "No farm has set its location yet."))
            return
        m = self.mreza() or {}
        put = os.path.join(tempfile.gettempdir(), "herddoc-mapa-farmi.html")
        with open(put, "w", encoding="utf-8") as f:
            f.write(mapa_html(farme, m.get("naziv") or T("Farme", "Farms")))
        self.otvori_link("file:///" + put.replace("\\", "/").lstrip("/"))

    def prozor_lokacije(self, posle=None):
        """Lokacija farme: koordinate ili link sa Google mapa."""
        win = tk.Toplevel(self.root)
        win.title(T("Lokacija farme", "Farm location"))
        win.configure(bg=SURF)
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, "📍 " + T("Lokacija farme", "Farm location"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Upiši mesto ili adresu farme, npr. „Prijevor, Čačak“. Za tačno mesto: na Google mapama drži prst "
                      "(ili desni klik) na farmi, kopiraj brojeve (npr. 43.89123, 20.34567) i nalepi ih ovde.",
                      "Type the farm's place or address, e.g. “Prijevor, Čačak”. For the exact spot: in Google Maps hold your finger "
                      "(or right-click) on the farm, copy the numbers (e.g. 43.89123, 20.34567) and paste them here."),
                 9, fg=INK2, wraplength=420, justify="left").pack(anchor="w", pady=(4, 12))
        v = tk.StringVar(value=tekst_lokacije(self.pod.get("lokacija")))
        e = ttk.Entry(b, textvariable=v, width=46, font=self.f(11))
        e.pack(anchor="w")
        e.focus_set()
        info = self.lbl(b, "", 9, "bold", fg=INK2)
        info.pack(anchor="w", pady=(6, 0))

        def proveri(*_):
            lok = lokacija_iz_teksta(v.get())
            if lok and lok.get("adresa"):
                tekst = "✓ " + T("mesto: ", "place: ") + lok["adresa"]
            elif lok:
                tekst = "✓ " + T("tačno mesto: ", "exact spot: ") + tekst_lokacije(lok)
            else:
                tekst = T("Ne prepoznajem lokaciju.", "Location not recognised.") if v.get().strip() else ""
            info.config(text=tekst, fg=OK if lok else (BAD if v.get().strip() else INK2))
        v.trace_add("write", proveri)
        proveri()
        f = tk.Frame(b, bg=SURF)
        f.pack(fill="x", pady=(14, 0))

        def zavrsi(lok):
            if lok:
                self.pod["lokacija"] = lok
            else:
                self.pod.pop("lokacija", None)
            self.sacuvaj_podesavanja()
            if win.winfo_exists():
                win.destroy()
            self.toast(T("Lokacija farme je sačuvana.", "Farm location saved.") if lok else T("Lokacija je obrisana.", "Location removed."))
            if posle:
                posle()

        def sacuvaj(ev=None):
            lok = lokacija_iz_teksta(v.get())
            if v.get().strip() and not lok:
                return
            if not lok or ima_koordinate(lok):
                zavrsi(lok)
                return
            info.config(text="⟳ " + T("tražim mesto na mapi…", "looking up the place on the map…"), fg=INK2)

            def kraj(k, greska):                       # mesto se nađe na mapi; ako nema interneta, čuva se samo naziv
                if k:
                    lok.update(lat=k[0], lon=k[1])
                zavrsi(lok)
            self._u_pozadini(lambda: nadji_koordinate(lok["adresa"]), kraj)
        self.btn(f, T("Sačuvaj", "Save"), sacuvaj, "Primary").pack(side="right")
        self.btn(f, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        self.btn(f, T("Otvori Google mape", "Open Google Maps"), lambda: self.otvori_link(
            mapa_url(lokacija_iz_teksta(v.get())) if lokacija_iz_teksta(v.get()) else "https://www.google.com/maps")).pack(side="left")
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, self.root)
        return win

    def _mreza_moje_kartica(self, body, m):
        o, c = self.card(body)
        o.pack(fill="x")
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        lev = tk.Frame(red, bg=SURF)
        lev.pack(side="left", fill="x", expand=True)
        if m.get("clan"):
            self.lbl(lev, T(f"Moja farma: {m.get('naziv_farme', '')}", f"My farm: {m.get('naziv_farme', '')}"), 12, "bold").pack(anchor="w")
            self.lbl(lev, T("Udruženju se šalju osnovna polja grla (oznaka, rasa, pol, rođenje, roditelji, status, ocena). "
                            "Napomene, stado, cene i istorija se ne šalju. Šalje se samo kad ima promena.",
                            "Basic animal fields are sent to the association (ID, breed, sex, birth, parents, status, score). "
                            "Notes, herd, prices and history are not sent. Data is sent only when something changed."),
                     9, fg=INK2, wraplength=560, justify="left").pack(anchor="w", pady=(2, 4))
            self.lbl(lev, T("Poslednje slanje: ", "Last sent: ") + (m.get("poslato") or "–"), 10, "bold",
                     fg=OK if m.get("poslato") else INK2).pack(anchor="w")
            lr = tk.Frame(lev, bg=SURF)
            lr.pack(anchor="w", pady=(8, 0))
            lok = self.pod.get("lokacija")
            self.lbl(lr, "📍 " + T("Lokacija farme: ", "Farm location: ") + (tekst_lokacije(lok) or T("nije upisana", "not set")), 10,
                     "bold", fg=INK2 if not lok else OK).pack(side="left")
            self.btn(lr, T("Upiši lokaciju", "Set location") if not lok else T("Promeni", "Change"),
                     lambda: self.prozor_lokacije(lambda: (self.mreza_posalji(odmah=True), self.prikazi("mreza")))).pack(side="left", padx=(10, 0))
            if lok:
                self.btn(lr, T("Na mapi", "On map"), lambda: self.otvori_link(mapa_url(lok))).pack(side="left", padx=(6, 0))
        self._mreza_lbl = self.lbl(lev, getattr(self, "_mreza_status", ""), 9, fg=INK2)
        self._mreza_lbl.pack(anchor="w", pady=(4, 0))
        des = tk.Frame(red, bg=SURF)
        des.pack(side="right", anchor="n")
        if m.get("clan"):
            def posalji():
                self.mreza_posalji(odmah=True, kraj=lambda g: self.toast(
                    T("Podaci su poslati udruženju.", "Data sent to the association.") if g is None else str(g)))
            self.btn(des, T("Pošalji sada", "Send now"), posalji, "Primary").pack(anchor="e")

        def napusti():
            pit = (T("Ovaj računar je napravio udruženje. Ako ga napustiš, više niko neće moći da upisuje farme.\n\nNapustiti udruženje?",
                     "This computer created the association. If you leave, nobody will be able to register farms.\n\nLeave the association?")
                   if m.get("uloga") == "admin" else
                   T("Napustiti udruženje? Tvoji podaci na ovom računaru ostaju, ali više nećeš videti druge farme.",
                     "Leave the association? Your data on this computer stays, but you will no longer see the other farms."))
            if messagebox.askyesno("HerdDoc", pit, parent=self.root):
                self.pod.pop("mreza", None)
                self._mreza_podaci = None
                self.sacuvaj_podesavanja()
                self.prikazi("mreza")
        self.btn(des, T("Napusti udruženje", "Leave association"), napusti, "Danger").pack(anchor="e", pady=(8, 0))
