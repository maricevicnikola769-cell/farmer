"""Oblak: šifrovano usklađivanje telefona i računara preko Firebase-a (Firestore REST, bez dodatnih biblioteka za mrežu).

Kako radi:
- računar posle svake promene pošalje SNIMAK celog stada (stanje/poslednji + snimci/<verzija>_NNN),
- telefon šalje PAKETE sa onim što je promenio (paketi/<pid>_NNN), računar ih spoji i obriše,
- sve je pre slanja zaključano (AES-256-GCM) ključem iz QR koda; server vidi samo nečitljiv tekst.
"""
import base64
import gzip
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

DEO = 900_000                  # Firestore dokument može do 1 MB – veći podaci idu u više delova
AAD = b"farmer1"
TELEFON_URL = "https://maricevicnikola769-cell.github.io/farmer/telefon/"


class OblakGreska(Exception):
    def __init__(self, poruka, bez_mreze=False):
        super().__init__(poruka)
        self.bez_mreze = bez_mreze


# ---------------------------------------------------------------- ključevi i uparivanje
def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def iz_b64u(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def novo_gazdinstvo():
    """(oznaka gazdinstva, ključ) – oznaka je duga i nasumična, pa je niko ne može pogoditi."""
    return secrets.token_hex(24), b64u(secrets.token_bytes(32))


def link_za_uparivanje(farma, kljuc, naziv=""):
    return f"{TELEFON_URL}#upari={farma}.{kljuc}.{urllib.parse.quote(naziv or '', safe='')}"


# ---------------------------------------------------------------- novi ključ samo za određeni telefon
INFO_ROTACIJA = b"farmer-rotacija"


def _kljuc_za(privatni, javni):
    """Zajednički ključ (ECDH P-256 + HKDF-SHA256) – isti kao na telefonu (WebCrypto)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    pub = ec.EllipticCurvePublicNumbers(int.from_bytes(iz_b64u(javni["x"]), "big"), int.from_bytes(iz_b64u(javni["y"]), "big"),
                                        ec.SECP256R1()).public_key()
    tajna = privatni.exchange(ec.ECDH(), pub)
    return b64u(HKDF(algorithm=hashes.SHA256(), length=32, salt=b"", info=INFO_ROTACIJA).derive(tajna))


def _javni_od(privatni):
    n = privatni.public_key().public_numbers()
    return {"x": b64u(n.x.to_bytes(32, "big")), "y": b64u(n.y.to_bytes(32, "big"))}


def omotaj_za(javni, obj):
    """Zaključa obj tako da ga otvori SAMO telefon sa ovim javnim ključem (ni ostali upareni telefoni)."""
    from cryptography.hazmat.primitives.asymmetric import ec
    e = ec.generate_private_key(ec.SECP256R1())
    return {"epub": json.dumps(_javni_od(e)), "podaci": zakljucaj(obj, _kljuc_za(e, javni))}


def odmotaj(privatni, dok):
    """Suprotno od omotaj_za (koristi se u testovima umesto telefona)."""
    return otkljucaj(dok["podaci"], _kljuc_za(privatni, json.loads(dok["epub"])))


# ---------------------------------------------------------------- zaključavanje
def zakljucaj(obj, kljuc):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    podaci = gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
    iv = os.urandom(12)
    return base64.b64encode(b"\x01" + iv + AESGCM(iz_b64u(kljuc)).encrypt(iv, podaci, AAD)).decode()


def otkljucaj(tekst, kljuc):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        sirovo = base64.b64decode(tekst)
        podaci = AESGCM(iz_b64u(kljuc)).decrypt(sirovo[1:13], sirovo[13:], AAD)
    except Exception:
        raise OblakGreska("Podaci ne mogu da se otključaju (pogrešan ključ – telefon je uparen sa drugim računarom?)")
    if sirovo[0] == 1:
        podaci = gzip.decompress(podaci)
    return json.loads(podaci.decode("utf-8"))


# ---------------------------------------------------------------- Firestore preko REST-a
class Oblak:
    def __init__(self, konfig, farma, kljuc, token=None):
        self.kljuc_api = konfig.get("apiKey", "")
        self.projekat = konfig.get("projectId", "")
        self.auth_url = konfig.get("authUrl", "https://identitytoolkit.googleapis.com")
        self.token_url = konfig.get("tokenUrl", "https://securetoken.googleapis.com")
        self.fs_url = konfig.get("firestoreUrl", "https://firestore.googleapis.com")
        self.farma, self.kljuc = farma, kljuc
        self.token = dict(token or {})          # {id, osvezi, istice}

    @staticmethod
    def podeseno(konfig):
        return bool(konfig.get("apiKey") and konfig.get("projectId"))

    def _http(self, metod, url, telo=None, zaglavlja=None, forma=False):
        podaci = None
        z = dict(zaglavlja or {})
        if telo is not None:
            if forma:
                podaci = urllib.parse.urlencode(telo).encode()
                z["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                podaci = json.dumps(telo).encode()
                z["Content-Type"] = "application/json"
        zahtev = urllib.request.Request(url, data=podaci, method=metod, headers=z)
        try:
            with urllib.request.urlopen(zahtev, timeout=30) as o:
                sadrzaj = o.read()
                return json.loads(sadrzaj) if sadrzaj else {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            try:
                poruka = json.loads(e.read()).get("error", {})
                poruka = poruka.get("message", poruka) if isinstance(poruka, dict) else poruka
            except Exception:
                poruka = e.reason
            raise OblakGreska(f"Server je odbio zahtev ({e.code}): {poruka}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise OblakGreska(f"Nema veze sa internetom ({e})", bez_mreze=True)

    def _prijava(self):
        if self.token.get("id") and self.token.get("istice", 0) > time.time() + 120:
            return self.token["id"]
        if self.token.get("osvezi"):
            try:
                r = self._http("POST", f"{self.token_url}/v1/token?key={self.kljuc_api}",
                               {"grant_type": "refresh_token", "refresh_token": self.token["osvezi"]}, forma=True)
                if r and r.get("id_token"):
                    self.token = dict(id=r["id_token"], osvezi=r.get("refresh_token", self.token["osvezi"]),
                                      istice=time.time() + int(r.get("expires_in", 3600)))
                    return self.token["id"]
            except OblakGreska as e:
                if e.bez_mreze:
                    raise
        r = self._http("POST", f"{self.auth_url}/v1/accounts:signUp?key={self.kljuc_api}", {"returnSecureToken": True})
        if not r or not r.get("idToken"):
            raise OblakGreska("Prijava na server nije uspela (proveri Anonymous u Firebase Authentication).")
        self.token = dict(id=r["idToken"], osvezi=r.get("refreshToken", ""), istice=time.time() + int(r.get("expiresIn", 3600)))
        return self.token["id"]

    def _putanja(self, kol, dok=None):
        p = f"{self.fs_url}/v1/projects/{self.projekat}/databases/(default)/documents/farme/{self.farma}/{kol}"
        return p + (f"/{dok}" if dok else "")

    def _zaglavlja(self):
        return {"Authorization": "Bearer " + self._prijava()}

    def upisi(self, kol, dok, polja):
        self._http("PATCH", self._putanja(kol, dok), {"fields": {k: {"stringValue": str(v)} for k, v in polja.items()}},
                   self._zaglavlja())

    def citaj(self, kol, dok):
        r = self._http("GET", self._putanja(kol, dok), zaglavlja=self._zaglavlja())
        return None if r is None else {k: v.get("stringValue", "") for k, v in r.get("fields", {}).items()}

    def lista(self, kol):
        rez, strana = [], ""
        while True:
            r = self._http("GET", self._putanja(kol) + "?pageSize=300" + (f"&pageToken={urllib.parse.quote(strana)}" if strana else ""),
                           zaglavlja=self._zaglavlja()) or {}
            for d in r.get("documents", []):
                rez.append((d["name"].rsplit("/", 1)[1], {k: v.get("stringValue", "") for k, v in d.get("fields", {}).items()}))
            strana = r.get("nextPageToken")
            if not strana:
                return rez

    def obrisi(self, kol, dok):
        self._http("DELETE", self._putanja(kol, dok), zaglavlja=self._zaglavlja())

    # ---------- veliki podaci u delovima
    def upisi_veliko(self, kol, osnova, tekst):
        delovi = [tekst[i:i + DEO] for i in range(0, len(tekst), DEO)] or [""]
        for n, d in enumerate(delovi):
            self.upisi(kol, f"{osnova}_{n:03d}", dict(pid=osnova, n=n, ukupno=len(delovi), deo=d))
        return len(delovi)

    def procitaj_veliko(self, kol, osnova, ukupno):
        delovi = []
        for n in range(int(ukupno)):
            d = self.citaj(kol, f"{osnova}_{n:03d}")
            if d is None:
                raise OblakGreska("Deo podataka nedostaje na serveru (pokušaću ponovo).")
            delovi.append(d.get("deo", ""))
        return "".join(delovi)

    # ---------- snimak računara i paketi telefona
    def posalji_snimak(self, sadrzaj, stara_verzija=None):
        verzija = f"{int(time.time() * 1000)}{secrets.token_hex(3)}"
        ukupno = self.upisi_veliko("snimci", verzija, zakljucaj(sadrzaj, self.kljuc))
        self.upisi("stanje", "poslednji", dict(verzija=verzija, ukupno=ukupno, vreme=time.strftime("%Y-%m-%d %H:%M:%S")))
        if stara_verzija:                       # stari snimak više ne treba
            for dok, polja in self.lista("snimci"):
                if polja.get("pid") != verzija:
                    try:
                        self.obrisi("snimci", dok)
                    except OblakGreska:
                        pass
        return verzija

    def paketi(self):
        """Kompletni paketi sa telefona: [(pid, sadržaj, [dokumenti])], redom kako su poslati."""
        grupe = {}
        for dok, polja in self.lista("paketi"):
            g = grupe.setdefault(polja.get("pid", dok), dict(ukupno=int(polja.get("ukupno") or 1), delovi={}, dok=[]))
            g["delovi"][int(polja.get("n") or 0)] = polja.get("deo", "")
            g["dok"].append(dok)
        rez = []
        for pid in sorted(grupe):
            g = grupe[pid]
            if len(g["delovi"]) < g["ukupno"]:
                continue                        # telefon još šalje
            tekst = "".join(g["delovi"][n] for n in range(g["ukupno"]))
            rez.append((pid, otkljucaj(tekst, self.kljuc), g["dok"]))
        return rez

    def obrisi_paket(self, dokumenti):
        for d in dokumenti:
            self.obrisi("paketi", d)


# ---------------------------------------------------------------- uparivanje kodom (umesto QR koda)
# Računar napravi kratak kod (npr. K7M2-9XQP) koji važi 15 minuta. Ključ gazdinstva se šifrovan ostavi u oblaku na mestu
# koje se izračunava iz koda; telefon upiše kod, nađe to mesto i otključa ključ. Sam kod se nigde ne šalje.
KOD_ABECEDA = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"     # bez 0/O i 1/I/L da se ne mešaju
KOD_TRAJANJE = 15 * 60
KOD_PBKDF2 = 150_000


def novi_kod():
    k = "".join(secrets.choice(KOD_ABECEDA) for _ in range(8))
    return k[:4] + "-" + k[4:]


def norm_kod(kod):
    """'k7m2 9xqp' -> 'K7M29XQP' (velika slova, bez razmaka i crtica)."""
    return "".join(c for c in str(kod or "").upper() if c.isalnum())


def mesto_koda(kod):
    """(oznaka mesta u oblaku, ključ) izračunati iz koda – isto na računaru i telefonu."""
    import hashlib
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    k = norm_kod(kod)
    h = hashlib.sha256(("herddoc-par|" + k).encode()).hexdigest()
    kljuc = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=("herddoc-par|" + h).encode(),
                       iterations=KOD_PBKDF2).derive(k.encode())
    return h[:48], b64u(kljuc)


def objavi_kod(konfig, kod, farma, kljuc, naziv=""):
    mesto, k = mesto_koda(kod)
    istice = int(time.time()) + KOD_TRAJANJE
    o = Oblak(konfig, mesto, k)
    o.upisi("uparivanje", "kod", dict(podaci=zakljucaj(dict(farma=farma, kljuc=kljuc, naziv=naziv, istice=istice), k), istice=istice))
    return istice


def obrisi_kod(konfig, kod):
    mesto, k = mesto_koda(kod)
    try:
        Oblak(konfig, mesto, k).obrisi("uparivanje", "kod")
    except OblakGreska:
        pass


def preuzmi_kod(konfig, kod):
    """(farma, ključ, naziv) za kod, ili None ako kod ne postoji ili je istekao."""
    mesto, k = mesto_koda(kod)
    d = Oblak(konfig, mesto, k).citaj("uparivanje", "kod")
    if not d or not d.get("podaci"):
        return None
    p = otkljucaj(d["podaci"], k)
    if int(p.get("istice", 0)) < time.time():
        return None
    return p["farma"], p["kljuc"], p.get("naziv", "")
