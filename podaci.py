"""Podaci: kolone tablice, čitanje i čuvanje CSV tablice, istorija i podsetnici, pomoćne funkcije za datume."""
import csv
import os
from datetime import date, datetime

from osnova import EN, _uz_tablicu, prevedi_vrednost
from jezik import NAZIVI


KOLONE = ["id", "markica", "rfid", "vrsta", "rasa", "namena", "autohtona", "pol", "datum_rodjenja", "otac", "majka", "status", "stado",
          "poreklo", "poreklo_od", "stare_markice", "uneto"]


def sada():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def nazivi(vrsta):
    return NAZIVI.get((vrsta or "")[:3], (("male" if EN else "mužjak"), ("female" if EN else "ženka"), ("young" if EN else "mladunče"), ("young" if EN else "mladunčad")))


def norm(t):
    return "".join(c for c in str(t or "").upper() if c.isalnum())


def kolona(k):
    k = (k or "").strip().lower()
    for a, b in (("đ", "dj"), ("č", "c"), ("ć", "c"), ("š", "s"), ("ž", "z")):
        k = k.replace(a, b)
    return "_".join(k.split())


def stare_lista(r):
    """Ranije usne markice grla (kolona stare_markice, razdvojene zarezom)."""
    return [x.strip() for x in str(r.get("stare_markice", "") or "").split(",") if x.strip()]


def sort_key(s):
    """K2 < K10 (prirodno sortiranje)."""
    import re
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", str(s))]


def parsiraj_datum(t):
    t = str(t or "").strip().rstrip(".")
    if not t:
        return None
    try:
        t = t.split(" ")[0]
        if "-" in t:
            g, m, d = t.split("-")[:3]
            return date(int(g), int(m), int(d))
        for s in (".", "/"):
            if s in t:
                d, m, g = t.split(s)[:3]
                return date(int(g), int(m), int(d))
        if len(t) == 4 and t.isdigit():
            return date(int(t), 7, 1)
    except (ValueError, TypeError):
        pass
    return None


def fmt_datum(d):
    return d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y.")) if d else ""


def starost_meseci(d):
    if not d:
        return None
    n = date.today()
    return (n.year - d.year) * 12 + n.month - d.month - (n.day < d.day)


def fmt_starost(m):
    if m is None:
        return ""
    if m < 24:
        return (f"{m} mo." if EN else f"{m} mes.")
    g = m // 12
    if EN:
        return f"{g} " + ("year" if g == 1 else "years")
    else:
        return f"{g} " + ("godine" if 2 <= g % 10 <= 4 and not 12 <= g % 100 <= 14 else "godina")


def fmt_upis(t):
    """'2026-10-05 14:30:00' -> '05.10.2026.'"""
    try:
        return datetime.strptime(t[:10], "%Y-%m-%d").strftime(("%d/%m/%Y" if EN else "%d.%m.%Y."))
    except (ValueError, TypeError):
        return "–"


def pct(f):
    if EN:
        return (f"{f * 100:.2f}" if 0 < f < 0.1 else f"{f * 100:.1f}") + "%"
    else:
        return (f"{f * 100:.2f}" if 0 < f < 0.1 else f"{f * 100:.1f}").replace(".", ",") + "%"


# =============================================================== podaci (CSV)

class Tablica:
    def __init__(self, putanja, ucitaj=True):
        self.putanja = putanja
        self.redovi = []          # lista dict-ova sa kljucevima iz KOLONE (+ dodatne kolone)
        self.dodatne = []
        self.mtime = None
        if ucitaj:
            self.ucitaj()

    def ucitaj(self):
        self.redovi, self.dodatne = [], []
        if not os.path.isfile(self.putanja):
            self.mtime = None
            return
        redovi, zaglavlje = procitaj_csv(self.putanja)
        self.dodatne = [k for k in zaglavlje if k not in KOLONE and k not in ALIAS]
        self.redovi = redovi
        self.mtime = os.path.getmtime(self.putanja)

    def sacuvaj(self):
        zagl = KOLONE + self.dodatne
        tmp = self.putanja + ".tmp"
        if EN:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([EN_KOL.get(k, k) for k in zagl])
                for r in self.redovi:            # redosled upisa se cuva
                    vr = dict(r)
                    vr["status"] = STATUS_EN.get(vr.get("status", ""), vr.get("status", ""))
                    vr["pol"] = {"z": "f"}.get(vr.get("pol", ""), vr.get("pol", ""))
                    w.writerow([vr.get(k, "") for k in zagl])
        else:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(zagl)
                for r in self.redovi:            # redosled upisa se cuva
                    w.writerow([r.get(k, "") for k in zagl])
        os.replace(tmp, self.putanja)
        self.mtime = os.path.getmtime(self.putanja)


EN_KOL = {"id": "id", "markica": "ear_tag", "rfid": "rfid", "vrsta": "species", "rasa": "breed", "namena": "purpose", "autohtona": "native_breed", "pol": "sex",
          "datum_rodjenja": "birth_date", "otac": "sire", "majka": "dam", "status": "status", "stado": "herd",
          "poreklo": "origin", "poreklo_od": "origin_from", "stare_markice": "old_ear_tags", "uneto": "added"}


EN_IST = {"grlo": "animal", "datum": "date", "dogadjaj": "event", "opis": "description", "partner": "partner",
          "vrednost": "value", "automatski": "automatic", "uneto": "added", "ishod": "outcome", "ter": "heat",
          "karenca_meso": "withdrawal_meat_days", "karenca_mleko": "withdrawal_milk_days", "upisao": "entered_by",
          "mast": "fat_pct", "proteini": "protein_pct"}


EN_POD = {"grlo": "animal", "datum": "date", "tip": "type", "tekst": "text", "ponavljanje": "repeat_days",
          "gotovo": "done", "uneto": "added"}


STATUS_EN = {"aktivno": "active", "neaktivno": "inactive", "obrisano": "deleted"}


ALIAS = {"oznaka": "id", "grlo": "id", "usna_markica": "markica", "usni_broj": "markica",
         "broj_markice": "markica", "rodjen": "datum_rodjenja", "rodjeno": "datum_rodjenja",
         "datum": "datum_rodjenja", "tag": "id", "animal": "id", "name": "id", "eartag": "markica",
         "ear_tag_number": "markica", "father": "otac", "mother": "majka", "date_of_birth": "datum_rodjenja",
         "dob": "datum_rodjenja", "birthdate": "datum_rodjenja", "born": "datum_rodjenja", "gender": "pol",
         "farm": "gazdinstvo", "farma": "gazdinstvo", "namena_rase": "namena", "tip": "namena",
         "eid": "rfid", "rfid_broj": "rfid", "elektronski_broj": "rfid", "electronic_id": "rfid", "e_markica": "rfid",
         "autohtona_rasa": "autohtona", "autohtono": "autohtona", "native": "autohtona", "indigenous": "autohtona",
         **{v: k for k, v in EN_KOL.items()}}


POL_MAP = {"m": "m", "z": "z", "ž": "z", "f": "z", "b": "m", "k": "z"}


def da_ne(v):
    """Kolona 'autohtona': '1' = da, '' = ne (prihvata da/yes/x/1/true iz Excela)."""
    return "1" if str(v or "").strip().lower() in ("1", "da", "d", "yes", "y", "x", "true", "✓", "autohtona", "native") else ""


# poznate autohtone rase u Srbiji – kad se upiše takva rasa, kvačica „autohtona“ se predloži sama
AUTOHTONE_RASE = ("buša", "busa", "podolsk", "pramenka", "sjenič", "sjenic", "svrlji", "pirotsk", "krivovir", "karakačan",
                  "karakacan", "lipsk", "bardoka", "vlaška vitoroga", "vlaska vitoroga", "cigaja", "balkansk", "mangulic",
                  "mangalic", "moravk", "resavk", "brdski konj", "domaći brdski", "domaci brdski")


def autohtona_rasa(rasa):
    r = str(rasa or "").lower()
    return any(k in r for k in AUTOHTONE_RASE)


def cifre(t):
    return "".join(c for c in str(t or "") if c.isdigit())


def isti_broj_citaca(procitano, broj):
    """Da li broj sa čitača (npr. 688 000123456789) odgovara upisanom broju (RFID ili markica).
    Isto kad se poklapa ceo broj; inače kad se upisani broj (bar 8 cifara) nalazi na kraju pročitanog."""
    a, b = norm(procitano), norm(broj)
    if not a or not b:
        return False
    if a == b:
        return True
    ca, cb = cifre(procitano), cifre(broj)
    return len(cb) >= 8 and ca.endswith(cb)


def slobodna_oznaka(nid, postojece):
    """Ako oznaka/ime već postoji, novo grlo dobija sledeći broj po redu: Bela, Bela 2, Bela 3…
    Poređenje ne gleda velika/mala slova ni razmake (Bela = bela)."""
    nid = " ".join(str(nid or "").split())
    zauzeto = {norm(x) for x in postojece if x}
    if norm(nid) not in zauzeto:
        return nid
    osnova, n = nid, 2
    delovi = nid.rsplit(" ", 1)
    if len(delovi) == 2 and delovi[1].isdigit() and int(delovi[1]) >= 2:
        osnova, n = delovi[0], int(delovi[1]) + 1
    while norm(f"{osnova} {n}") in zauzeto:
        n += 1
    return f"{osnova} {n}"


def norm_rasa(r):
    """Rase se pišu malim slovima, osim oznake hibrida: 'hibrid L×J'."""
    r = " ".join(str(r or "").split())
    if r.lower().startswith(("hybrid" if EN else "hibrid")):
        kod = r[6:].strip().upper().replace("X", "×").replace("*", "×").replace(" ", "")
        return (f"hybrid {kod}" if EN else f"hibrid {kod}") if kod else ("hybrid" if EN else "hibrid")
    return r.lower()


def kod_rase(rasa, druga=""):
    """Oznaka rase u nazivu hibrida: prvo slovo (dva, ako obe rase počinju istim slovom).
    Hibrid kao roditelj ulazi u zagradi: D×(L×J)."""
    rasa = norm_rasa(rasa)
    if rasa.startswith(("hybrid " if EN else "hibrid ")):
        return f"({rasa[7:]})"
    if not rasa:
        return "?"
    d = norm_rasa(druga)
    if d and not d.startswith(("hybrid" if EN else "hibrid")) and d[0] == rasa[0] and d != rasa:
        return rasa[:2].capitalize()
    return rasa[0].upper()


def rasa_potomka(rasa_oca, rasa_majke):
    """Ista rasa -> ta rasa; različite -> 'hibrid O×M' (prvo otac, pa majka); jedna nepoznata -> poznata."""
    ro, rm = norm_rasa(rasa_oca), norm_rasa(rasa_majke)
    if not ro or ro == rm:
        return rm
    if not rm:
        return ro
    return (f"hybrid {kod_rase(ro, rm)}×{kod_rase(rm, ro)}" if EN else f"hibrid {kod_rase(ro, rm)}×{kod_rase(rm, ro)}")


def vrsta_norm(v):
    v = (v or "").strip().lower()
    return {"gov": "goveda", "bik": "goveda", "kra": "goveda", "ovc": "ovce", "ova": "ovce",
            "koz": "koze", "svi": "svinje", "kon": "konji",
            "cat": "goveda", "cow": "goveda", "bul": "goveda", "she": "ovce", "ewe": "ovce", "ram": "ovce",
            "goa": "koze", "pig": "svinje", "swi": "svinje", "sow": "svinje", "boa": "svinje",
            "hor": "konji", "mar": "konji"}.get(v[:3], v) if not EN else {"cat": "cattle", "cow": "cattle", "bul": "cattle", "gov": "cattle", "bik": "cattle", "kra": "cattle",
            "she": "sheep", "ewe": "sheep", "ram": "sheep", "ovc": "sheep", "ova": "sheep",
            "goa": "goats", "koz": "goats", "pig": "pigs", "swi": "pigs", "sow": "pigs", "boa": "pigs",
            "svi": "pigs", "hor": "horses", "mar": "horses", "kon": "horses"}.get(v[:3], v)


def _excel_datum(v):
    """Excel čuva izmenjene datume kao broj dana od 30.12.1899."""
    try:
        d = date.fromordinal(date(1899, 12, 30).toordinal() + int(float(v)))
        return d.strftime("%d/%m/%Y" if EN else "%d.%m.%Y")
    except (ValueError, OverflowError):
        return v


def procitaj_xlsx(putanja):
    """Excel (.xlsx) bez dodatnih biblioteka -> [(naziv lista, [[ćelije reda kao tekst], ...]), ...].
    Čita i fajlove koje je HerdDoc izvezao i one koje je Excel ponovo sačuvao (deljeni tekstovi, brojevi)."""
    import re
    import zipfile
    from xml.etree import ElementTree as ET
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    def tekst(el):
        return "".join(t.text or "" for t in el.iter("{%s}t" % ns["m"]))
    with zipfile.ZipFile(putanja) as z:
        imena = set(z.namelist())
        deljeni = []
        if "xl/sharedStrings.xml" in imena:
            deljeni = [tekst(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns)]
        veze = {}
        if "xl/_rels/workbook.xml.rels" in imena:
            for v in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
                veze[v.get("Id")] = v.get("Target", "").lstrip("/")
        listovi = []
        for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", ns):
            cilj = veze.get(sh.get("{%s}id" % ns["r"]), "")
            cilj = cilj if cilj.startswith("xl/") else "xl/" + cilj
            if cilj not in imena:
                continue
            redovi = []
            for row in ET.fromstring(z.read(cilj)).iter("{%s}row" % ns["m"]):
                red = []
                for c in row.findall("m:c", ns):
                    ref = re.match(r"([A-Z]+)", c.get("r", "")) if c.get("r") else None
                    if ref:                                    # prazne ćelije Excel preskače -> pozicija iz adrese
                        kol = 0
                        for ch in ref.group(1):
                            kol = kol * 26 + ord(ch) - 64
                        while len(red) < kol - 1:
                            red.append("")
                    t, v = c.get("t"), c.find("m:v", ns)
                    if t == "inlineStr":
                        val = tekst(c)
                    elif t == "s" and v is not None:
                        val = deljeni[int(v.text)] if v.text and int(v.text) < len(deljeni) else ""
                    elif v is not None and v.text is not None:
                        val = v.text
                        if t not in ("str", "e", "b"):
                            try:                                 # 123.0 -> 123
                                f = float(val)
                                val = str(int(f)) if f == int(f) and abs(f) < 1e15 else str(f)
                            except ValueError:
                                pass
                    else:
                        val = ""
                    red.append(val.strip())
                redovi.append(red)
            listovi.append((sh.get("name", ""), redovi))
    return listovi


def tabela_u_recnike(redovi, mapa_naziva=None):
    """Prvi red je zaglavlje -> lista dict-ova (nazivi kolona normalizovani, prevod sa engleskog)."""
    if not redovi:
        return [], []
    nazad = {v: k for k, v in (mapa_naziva or {}).items()}
    zagl = [nazad.get(kolona(k), kolona(k)) for k in redovi[0]]
    rez = []
    for red in redovi[1:]:
        if not any((x or "").strip() for x in red):
            continue
        rez.append({k: ((red[i] or "").strip() if i < len(red) else "") for i, k in enumerate(zagl) if k})
    return rez, zagl


def procitaj_csv(putanja):
    """Tablica grla iz CSV-a ili Excela (.xlsx: prvi list)."""
    if putanja.lower().endswith((".xlsx", ".xlsm")):
        listovi = procitaj_xlsx(putanja)
        return _obradi_tablicu(listovi[0][1] if listovi else [], excel=True)
    kod = "latin-1"
    for k in ("utf-8-sig", "cp1250"):
        try:
            with open(putanja, encoding=k) as f:
                f.read()
            kod = k
            break
        except UnicodeDecodeError:
            continue
    with open(putanja, newline="", encoding=kod) as f:
        prvi = f.readline()
        f.seek(0)
        sep = ";" if prvi.count(";") >= prvi.count(",") else ","
        return _obradi_tablicu(list(csv.reader(f, delimiter=sep)))


def _obradi_tablicu(sirovo, excel=False):
    citac = iter(sirovo)
    try:
        zaglavlje = [kolona(k) for k in next(citac)]
    except StopIteration:
        return [], []
    zaglavlje = [ALIAS.get(k, k) if ALIAS.get(k, k) not in zaglavlje else k for k in zaglavlje]
    if "id" not in zaglavlje and "markica" not in zaglavlje:
        raise ValueError(("The table must have an 'id' (tag) or 'ear_tag' column.\n" if EN else
                          "Tablica mora imati kolonu 'id' (oznaka) ili 'markica'.\n") +
                         (f"Columns found: {', '.join(zaglavlje)}" if EN else f"Pronađene kolone: {', '.join(zaglavlje)}"))
    redovi = []
    for red in citac:
        if not any((x or "").strip() for x in red):
            continue
        r = {k: ((red[i] or "").strip() if i < len(red) else "") for i, k in enumerate(zaglavlje)}
        if excel and r.get("datum_rodjenja", "").replace(".", "", 1).isdigit() and 1000 < float(r["datum_rodjenja"]) < 80000:
            r["datum_rodjenja"] = _excel_datum(r["datum_rodjenja"])
        r["id"] = r.get("id") or r.get("markica", "")
        if not r["id"]:
            continue
        r["pol"] = POL_MAP.get(r.get("pol", "").lower()[:1], "")
        r["vrsta"] = vrsta_norm(r.get("vrsta", ""))
        r["rasa"] = norm_rasa(r.get("rasa", ""))
        for p in ("otac", "majka"):
            if r.get(p, "") == "0":
                r[p] = ""
        st = r.get("status", "").lower()
        r["status"] = ("aktivno" if st == "" or st.startswith(("akt", "act")) else
                       "obrisano" if st.startswith(("obr", "del")) else "neaktivno")
        for p in ("poreklo", "rasa", "namena"):
            r[p] = prevedi_vrednost(r.get(p, ""))
        r["autohtona"] = da_ne(r.get("autohtona", ""))
        redovi.append(r)
    return redovi, zaglavlje


# =============================================================== istorija grla

IST_KOLONE = ["grlo", "datum", "dogadjaj", "opis", "partner", "vrednost", "automatski", "uneto", "ishod",
              "ter", "karenca_meso", "karenca_mleko", "upisao", "mast", "proteini"]


class Istorija:
    """Dnevnik dogadjaja za svako grlo, cuva se u <tablica>_istorija.csv."""

    def __init__(self, putanja_tablice):
        self.putanja = _uz_tablicu(putanja_tablice, "_istorija.csv", "_history.csv")
        self.zapisi = []
        if os.path.isfile(self.putanja):
            try:
                kod = "utf-8-sig"
                try:
                    open(self.putanja, encoding=kod).read()
                except UnicodeDecodeError:
                    kod = "cp1250"
                with open(self.putanja, newline="", encoding=kod) as f:
                    prvi = f.readline()
                    f.seek(0)
                    sep = ";" if prvi.count(";") >= prvi.count(",") else ","
                    nazad, imena = {v_: k_ for k_, v_ in EN_IST.items()}, {}
                    for r in csv.DictReader(f, delimiter=sep):
                        for k in r:                      # naziv kolone se prevodi jednom, ne za svaki red
                            if k and k not in imena:
                                imena[k] = nazad.get(kolona(k), kolona(k))
                        r = {imena[k]: (v or "").strip() for k, v in r.items() if k}
                        for p in ("dogadjaj", "ishod", "ter"):
                            if r.get(p):
                                r[p] = prevedi_vrednost(r[p])
                        if r.get("grlo"):
                            self.zapisi.append({k: r.get(k, "") for k in IST_KOLONE})
            except OSError:
                pass

    def sacuvaj(self):
        tmp = self.putanja + ".tmp"
        if EN:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([EN_IST.get(k, k) for k in IST_KOLONE])
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in IST_KOLONE])
        else:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(IST_KOLONE)
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in IST_KOLONE])
        os.replace(tmp, self.putanja)

    def dodaj(self, grlo, dogadjaj, opis="", datum=None, partner="", vrednost="", automatski=False,
              karenca_meso="", karenca_mleko=""):
        z = dict(grlo=grlo, datum=datum or date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), dogadjaj=dogadjaj, opis=opis,
                 partner=partner, vrednost=vrednost, automatski="1" if automatski else "", uneto=sada(),
                 ishod="", ter="", karenca_meso=karenca_meso, karenca_mleko=karenca_mleko, upisao="")
        self.zapisi.append(z)
        return z

    def za(self, grlo=None, auto=True, mleko=False):
        """Zapisi za grlo (ili celo stado). Dnevna mužnja se ne prikazuje u običnoj istoriji (ima svoju stranu
        „Mlečnost“) – osim kad se traži (mleko=True)."""
        from jezik import MUZNJA
        z = [x for x in self.zapisi if (grlo is None or x["grlo"] == grlo) and (auto or not x["automatski"])
             and (mleko or x["dogadjaj"] != MUZNJA)]
        return sorted(z, key=lambda x: (parsiraj_datum(x["datum"]) or date.min, x["uneto"]), reverse=True)

    def preimenuj(self, staro, novo):
        for z in self.zapisi:
            if z["grlo"] == staro:
                z["grlo"] = novo
            if z["partner"] == staro:
                z["partner"] = novo


class Podsetnici:
    """Podsetnici za grla (vakcinacija, lečenje…), čuvaju se u <tablica>_podsetnici.csv."""
    KOLONE = ["grlo", "datum", "tip", "tekst", "ponavljanje", "gotovo", "uneto"]

    def __init__(self, putanja_tablice):
        self.putanja = _uz_tablicu(putanja_tablice, "_podsetnici.csv", "_reminders.csv")
        self.zapisi = []
        if os.path.isfile(self.putanja):
            try:
                kod = "utf-8-sig"
                try:
                    open(self.putanja, encoding=kod).read()
                except UnicodeDecodeError:
                    kod = "cp1250"
                with open(self.putanja, newline="", encoding=kod) as f:
                    for r in csv.DictReader(f, delimiter=";"):
                        r = {({v_: k_ for k_, v_ in EN_POD.items()}.get(kolona(k), kolona(k))): (v or "").strip()
                             for k, v in r.items() if k}
                        if r.get("tip"):
                            r["tip"] = prevedi_vrednost(r["tip"])
                        if r.get("datum"):
                            self.zapisi.append({k: r.get(k, "") for k in self.KOLONE})
            except OSError:
                pass

    def sacuvaj(self):
        if not self.zapisi and not os.path.isfile(self.putanja):
            return
        tmp = self.putanja + ".tmp"
        if EN:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([EN_POD.get(k, k) for k in self.KOLONE])
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in self.KOLONE])
        else:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(self.KOLONE)
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in self.KOLONE])
        os.replace(tmp, self.putanja)

    def dodaj(self, grlo, datum, tip, tekst="", ponavljanje=0):
        z = dict(grlo=grlo or "", datum=datum, tip=tip, tekst=tekst, ponavljanje=str(ponavljanje or ""),
                 gotovo="", uneto=sada())
        self.zapisi.append(z)
        return z

    def aktivni(self, grlo=None):
        return [z for z in self.zapisi if not z["gotovo"] and (grlo is None or z["grlo"] == grlo)]

    def preimenuj(self, staro, novo):
        for z in self.zapisi:
            if z["grlo"] == staro:
                z["grlo"] = novo
