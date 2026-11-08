"""Jezik: T(srpski, engleski), nazivi koji zavise od jezika i promena jezika bez ponovnog pokretanja.
Francuski, nemački, španski i portugalski se dobijaju iz engleskog teksta preko prevodi.py."""
import re
import sys

from osnova import EN, JEZICI, JEZIK, KODOVI_JEZIKA


# =============================================================== FARMER PRO
# Promena jezika, štampa i PDF (rodoslovni list, plan parenja, spisak stada) i statistika.

def T(sr, en):
    if not EN:
        return sr
    if JEZIK == "en" or not isinstance(en, str):
        return en
    return prevedi(en)


_SABLONI = {}      # jezik -> [(početak, regex, prevod)]
_KES = {}          # (jezik, tekst) -> prevod


def _sabloni(j):
    """Tekstovi sa promenljivim delovima ({0}, {1}…) kao regularni izrazi."""
    if j not in _SABLONI:
        import prevodi
        lista = []
        recnik = prevodi.PREVODI.get(j, {})
        for en in prevodi.SABLONI:
            if en not in recnik:
                continue
            delovi = re.split(r"(\{\d+\})", en.replace("{{", "\x00").replace("}}", "\x01"))
            izraz = "".join("(.*?)" if re.fullmatch(r"\{\d+\}", d) else
                            re.escape(d.replace("\x00", "{").replace("\x01", "}")) for d in delovi)
            pocetak = delovi[0].replace("\x00", "{").replace("\x01", "}")
            redosled = [int(d[1:-1]) for d in delovi if re.fullmatch(r"\{\d+\}", d)]
            stalno = len(re.sub(r"\{\d+\}", "", en))
            lista.append((pocetak, re.compile(izraz, re.S), redosled, recnik[en], stalno))
        lista.sort(key=lambda x: (-x[4], -len(x[0])))      # najviše stalnog teksta prvo (najtačniji šablon)
        lista = [x[:4] for x in lista]
        _SABLONI[j] = lista
    return _SABLONI[j]


def prevedi(en, j=None):
    """Engleski tekst programa -> na jezik j (podrazumevano trenutni). Nepoznat tekst ostaje na engleskom."""
    j = j or JEZIK
    if j in ("en", "sr") or not en:
        return en
    kljuc = (j, en)
    if kljuc in _KES:
        return _KES[kljuc]
    import prevodi
    rez = prevodi.PREVODI.get(j, {}).get(en)
    if rez is None or en in prevodi.SABLONI:
        rez = en
        for pocetak, izraz, redosled, prevod in _sabloni(j):
            if not en.startswith(pocetak):
                continue
            m = izraz.fullmatch(en)
            if m:
                vrednosti = [None] * (max(redosled) + 1 if redosled else 0)
                for i, g in zip(redosled, m.groups()):
                    vrednosti[i] = g
                try:
                    rez = prevod.format(*vrednosti)
                except (IndexError, KeyError, ValueError):
                    rez = en
                break
    if len(_KES) > 20000:
        _KES.clear()
    _KES[kljuc] = rez
    return rez


def _jezicke_konstante():
    """Ponovo postavi nazive koji zavise od jezika (posle promene jezika)."""
    global AUTO, DNK, DNK_POREKLO, DNK_PROVERA, DNK_TESTOVI, DNK_UZORCI, DOGADJAJI, GRAVIDNOST_PROFILI, GRUPE, MUZNJA, NAMENE_MALI, NAMENE_SVINJE, NAZIVI, PARENJE, POREKLA, REDOSLEDI, STADO_PODMLADAK, TER, TER_CIKLUS, VRSTE
    REDOSLEDI = [(T("Poslednje upisana prvo", "Last added first")), (T("Prvo upisana prvo", "First added first")), (T("Po oznaci", "By tag")), (T("Najmlađa prvo", "Youngest first"))]
    POREKLA = [(T("Sopstveni odgoj", "Home bred")), (T("Kupljeno", "Purchased")), (T("Uvoz", "Imported"))]
    VRSTE = [(T("goveda", "cattle")), (T("ovce", "sheep")), (T("koze", "goats")), (T("svinje", "pigs")), (T("konji", "horses"))]
    NAZIVI = {   # vrsta (srpski ključ) -> (mužjak, ženka, mladunče, mladunčad) na trenutnom jeziku
        "goveda": (T("bik", "bull"), T("krava", "cow"), T("tele", "calf"), T("telad", "calves")),
        "ovce": (T("ovan", "ram"), T("ovca", "ewe"), T("jagnje", "lamb"), T("jagnjad", "lambs")),
        "koze": (T("jarac", "buck"), T("koza", "doe"), T("jare", "kid"), T("jarad", "kids")),
        "svinje": (T("nerast", "boar"), T("krmača", "sow"), T("prase", "piglet"), T("prasad", "piglets")),
        "konji": (T("pastuv", "stallion"), T("kobila", "mare"), T("ždrebe", "foal"), T("ždrebad", "foals")),
    }
    TER = (T("Tera se", "In heat"))
    TER_CIKLUS = {(T("goveda", "cattle")): 21, (T("ovce", "sheep")): 17, (T("koze", "goats")): 21, (T("svinje", "pigs")): 21, (T("konji", "horses")): 21}
    PARENJE = (T("Parenje / osemenjavanje", "Mating / insemination"))
    STADO_PODMLADAK = (T("Podmladak", "Young stock"))
    GRAVIDNOST_PROFILI = {
        (T("romanovska", "romanov")): ((T("Romanovska ovca", "Romanov sheep")), (T("ovce", "sheep")), ("romanov",), 138, 143, 140),
        (T("ovce", "sheep")): ((T("Obična ovca", "Common sheep")), (T("ovce", "sheep")), (), 145, 152, 150),
        (T("koze", "goats")): ((T("Koza", "Goat")), (T("koze", "goats")), (), 145, 151, 150),
        (T("svinje", "pigs")): ((T("Svinja", "Pig")), (T("svinje", "pigs")), (), 110, 120, 114),
        (T("goveda", "cattle")): ((T("Krava", "Cow")), (T("goveda", "cattle")), (), 275, 290, 283),
        (T("konji", "horses")): ((T("Kobila", "Mare")), (T("konji", "horses")), (), 320, 360, 340),
    }
    DOGADJAJI = [(T("Parenje / osemenjavanje", "Mating / insemination")), (T("Tera se", "In heat")), (T("Porođaj", "Birth")), (T("Vakcinacija", "Vaccination")), (T("Lečenje", "Treatment")), (T("Merenje težine", "Weighing")),
                 (T("Premeštanje", "Move")), (T("Prodaja", "Sale")), (T("Uginuće", "Death")), (T("Napomena", "Note"))]
    AUTO = (T("Promena u evidenciji", "Record change"))
    DNK = T("DNK test", "DNA test")
    # najvažniji prvi: mesnatost, mlečnost, prenos na potomstvo
    DNK_TESTOVI = [T("Mesnatost (prirast, kvalitet mesa)", "Meat traits (growth, meat quality)"),
                   T("Mlečnost (mleko, mast, proteini)", "Milk traits (milk, fat, protein)"),
                   T("Prenos na potomstvo (priplodna vrednost)", "Transmission to offspring (breeding value)"),
                   T("Provera porekla (otac i majka)", "Parentage verification (sire and dam)"), T("Genomska procena", "Genomic evaluation"),
                   T("Genetske bolesti (nosioci)", "Genetic diseases (carriers)"), T("Beta-kazein A1/A2", "Beta-casein A1/A2"),
                   T("Kapa-kazein", "Kappa-casein"), T("Rogatost (šuto / rogato)", "Polled / horned"), T("Boja dlake", "Coat colour"),
                   T("Drugi test", "Other test")]
    DNK_PROVERA = DNK_TESTOVI[3]
    DNK_UZORCI = [T("Dlaka", "Hair"), T("Krv", "Blood"), T("Tkivo (ušni isečak)", "Tissue (ear punch)"), T("Seme", "Semen")]
    # rezultat provere porekla: 0 oba potvrđena, 1 otac potvrđen, 2 otac isključen, 3 majka isključena, 4 oba isključena
    DNK_POREKLO = [T("Otac i majka potvrđeni", "Sire and dam confirmed"), T("Otac potvrđen (majka nije testirana)", "Sire confirmed (dam not tested)"),
                   T("Otac isključen", "Sire excluded"), T("Majka isključena", "Dam excluded"), T("Otac i majka isključeni", "Sire and dam excluded")]
    MUZNJA = (T("Mužnja", "Milking"))        # dnevna količina mleka (vrednost = litara), mast i proteini
    # namena rase: goveda, ovce i koze / svinje
    NAMENE_MALI = [(T("mlečna", "dairy")), (T("tovna", "meat breed")), (T("kombinovana", "dual-purpose"))]
    NAMENE_SVINJE = [(T("mesnata", "meat type")), (T("masna", "lard type")), (T("kombinovana", "dual-purpose"))]
    GRUPE = [((T("Parenja", "Matings")), ((T("Parenje / osemenjavanje", "Mating / insemination")), (T("Tera se", "In heat")))),
             ((T("Lečenja", "Treatments")), ((T("Lečenje", "Treatment")), (T("Vakcinacija", "Vaccination")))),
             ((T("Porođaji", "Births")), ((T("Porođaj", "Birth")), (T("Potomak", "Offspring"))))]
    _primeni_moje_vrste()


# ---------------- vrste koje korisnik sam doda (magarci, bivoli, psi…) ----------------
# čuvaju se u podešavanjima ("vrste_moje"); naziv vrste se ne prevodi – piše se kako ga je korisnik upisao
MOJE_VRSTE = []            # [{"ime", "m", "z", "ml", "mlm", "gmin", "gmax", "gpr", "ciklus"}]
_DODATE = []               # imena koja su trenutno ubačena u VRSTE / NAZIVI / TER_CIKLUS / GRAVIDNOST_PROFILI


def ocisti_vrstu(v):
    """Proverena vrsta iz podešavanja ili None. Brojevi: gravidnost 10–500 dana, ciklus 0–120 (0 = bez podsetnika za teranje)."""
    try:
        ime = " ".join(str(v.get("ime", "")).split()).lower()[:30]
        gmin, gmax, gpr, cik = (int(v.get(x) or 0) for x in ("gmin", "gmax", "gpr", "ciklus"))
    except (AttributeError, TypeError, ValueError):
        return None
    if not ime or not (10 <= gmin <= gpr <= gmax <= 500) or not (0 <= cik <= 120):
        return None
    tekst = lambda k, d: " ".join(str(v.get(k) or "").split())[:30] or d
    return dict(ime=ime, m=tekst("m", T("mužjak", "male")), z=tekst("z", T("ženka", "female")),
                ml=tekst("ml", T("mladunče", "young")), mlm=tekst("mlm", T("mladunčad", "young")),
                gmin=gmin, gmax=gmax, gpr=gpr, ciklus=cik)


def _primeni_moje_vrste():
    g = globals()
    for ime in _DODATE:
        if ime in g["VRSTE"]:
            g["VRSTE"].remove(ime)
        g["NAZIVI"].pop(ime, None)
        g["TER_CIKLUS"].pop(ime, None)
        g["GRAVIDNOST_PROFILI"].pop("moja:" + ime, None)
    _DODATE.clear()
    for v in MOJE_VRSTE:
        ime = v["ime"]
        if ime in _VRSTE_SR or ime in g["VRSTE"]:
            continue                                    # već postoji (npr. "ovce") – ne dupliraj
        g["VRSTE"].append(ime)
        g["NAZIVI"][ime] = (v["m"], v["z"], v["ml"], v["mlm"])
        if v["ciklus"]:
            g["TER_CIKLUS"][ime] = v["ciklus"]
        g["GRAVIDNOST_PROFILI"]["moja:" + ime] = (ime.capitalize(), ime, (), v["gmin"], v["gmax"], v["gpr"])
        _DODATE.append(ime)


def postavi_moje_vrste(lista):
    """Upisuje vrste korisnika (iz podešavanja) u spiskove programa. Vraća očišćen spisak."""
    cist, vidjeno = [], set()
    for v in lista or []:
        c = ocisti_vrstu(v) if isinstance(v, dict) else None
        if c and c["ime"] not in vidjeno:
            vidjeno.add(c["ime"])
            cist.append(c)
    MOJE_VRSTE[:] = cist
    _primeni_moje_vrste()
    return cist


def je_moja_vrsta(v):
    v = " ".join(str(v or "").split()).lower()
    return any(x["ime"] == v for x in MOJE_VRSTE)


_jezicke_konstante()

# imena koja zavise od jezika; posle promene jezika svaki fajl programa dobija nove vrednosti
JEZICKA_IMENA = ("JEZIK", "EN", 'REDOSLEDI', 'POREKLA', 'VRSTE', 'NAZIVI', 'TER', 'TER_CIKLUS', 'PARENJE', 'STADO_PODMLADAK', 'GRAVIDNOST_PROFILI', 'DOGADJAJI', 'AUTO', 'GRUPE', 'MUZNJA', 'DNK', 'DNK_PROVERA', 'DNK_TESTOVI', 'DNK_UZORCI', 'DNK_POREKLO', 'NAMENE_MALI', 'NAMENE_SVINJE')
MODULI = ('osnova', 'jezik', 'podaci', 'izgled', 'rodoslov', 'ekran_osnova', 'ekran_grla', 'ekran_parenje', 'karton', 'gravidnost', 'istorija', 'kopije', 'obavestenja', 'stampa', 'izvoz', 'mlecnost', 'citac', 'finansije', 'oblak_kopija', 'prirast', 'dnk', 'telefon_prenos', 'sinhronizacija', 'app')


_VRSTE_SR = ("goveda", "ovce", "koze", "svinje", "konji")
_VRSTE_EN = ("cattle", "sheep", "goats", "pigs", "horses")
_PREFIKSI_VRSTA = {"gov": "goveda", "bik": "goveda", "kra": "goveda", "cat": "goveda", "cow": "goveda", "bul": "goveda",
                   "ovc": "ovce", "ova": "ovce", "she": "ovce", "ewe": "ovce", "ram": "ovce",
                   "koz": "koze", "jar": "koze", "goa": "koze",
                   "svi": "svinje", "pig": "svinje", "swi": "svinje", "sow": "svinje", "boa": "svinje", "ner": "svinje",
                   "kon": "konji", "hor": "konji", "mar": "konji"}
_RECI_VRSTA = {}


def vrsta_kanon(vrsta):
    """Vrsta upisana na bilo kom jeziku programa -> srpski ključ (goveda, ovce, koze, svinje, konji) ili ""."""
    v = " ".join(str(vrsta or "").split()).lower()
    if not v:
        return ""
    if any(x["ime"] == v for x in MOJE_VRSTE):
        return v                                         # vrsta koju je korisnik dodao: ključ je njen naziv
    if not _RECI_VRSTA:
        for sr, en in zip(_VRSTE_SR, _VRSTE_EN):
            _RECI_VRSTA[sr] = _RECI_VRSTA[en] = sr
            for j in KODOVI_JEZIKA[2:]:
                _RECI_VRSTA.setdefault(prevedi(en, j).lower(), sr)
        for sr, en in zip(_VRSTE_SR, ("cow", "sheep", "goat", "pig", "horse")):      # i jednina
            for j in KODOVI_JEZIKA[2:]:
                _RECI_VRSTA.setdefault(prevedi(en, j).lower(), sr)
    if v in _RECI_VRSTA:
        return _RECI_VRSTA[v]
    return _PREFIKSI_VRSTA.get(v[:3], "")


def vrsta_na_jeziku(sr):
    """Srpski ključ vrste -> naziv vrste na trenutnom jeziku (kako se čuva u tablici)."""
    return VRSTE[_VRSTE_SR.index(sr)] if sr in _VRSTE_SR else sr


def namene_za(vrsta):
    """Izbor namene rase za vrstu: goveda, ovce i koze (mlečna/tovna/kombinovana), svinje (mesnata/masna/kombinovana);
    ostale vrste (konji) nemaju."""
    k = vrsta_kanon(vrsta)
    if k in ("goveda", "ovce", "koze"):
        return list(NAMENE_MALI)
    if k == "svinje":
        return list(NAMENE_SVINJE)
    return []


def postavi_jezik(novi):
    """Promeni jezik celog programa odmah (sr, en, fr, de, es, pt), bez ponovnog pokretanja."""
    global JEZIK, EN
    if novi not in KODOVI_JEZIKA:
        novi = "en"
    JEZIK, EN = novi, novi != "sr"
    _jezicke_konstante()
    vrednosti = {k: globals()[k] for k in JEZICKA_IMENA}
    for ime in MODULI:
        modul = sys.modules.get(ime)
        if modul is None:
            continue
        for k, v in vrednosti.items():
            if k in vars(modul):
                setattr(modul, k, v)
