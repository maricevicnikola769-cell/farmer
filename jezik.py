"""Jezik: T(srpski, engleski), nazivi koji zavise od jezika i promena jezika bez ponovnog pokretanja."""
import sys

from osnova import EN, JEZIK


# =============================================================== FARMER PRO
# Promena jezika, štampa i PDF (rodoslovni list, plan parenja, spisak stada) i statistika.

def T(sr, en):
    return en if EN else sr


def _jezicke_konstante():
    """Ponovo postavi nazive koji zavise od jezika (posle promene jezika)."""
    global AUTO, DOGADJAJI, GRAVIDNOST_PROFILI, GRUPE, NAZIVI, PARENJE, POREKLA, REDOSLEDI, STADO_PODMLADAK, TER, TER_CIKLUS, VRSTE
    REDOSLEDI = [("Last added first" if EN else "Poslednje upisana prvo"), ("First added first" if EN else "Prvo upisana prvo"), ("By tag" if EN else "Po oznaci"), ("Youngest first" if EN else "Najmlađa prvo")]
    POREKLA = [("Home bred" if EN else "Sopstveni odgoj"), ("Purchased" if EN else "Kupljeno"), ("Imported" if EN else "Uvoz")]
    VRSTE = [("cattle" if EN else "goveda"), ("sheep" if EN else "ovce"), ("goats" if EN else "koze"), ("pigs" if EN else "svinje"), ("horses" if EN else "konji")]
    if EN:
        NAZIVI = {   # species prefix (English and Serbian) -> (male, female, young, young plural)
            "cat": ("bull", "cow", "calf", "calves"), "cow": ("bull", "cow", "calf", "calves"),
            "bul": ("bull", "cow", "calf", "calves"), "gov": ("bull", "cow", "calf", "calves"),
            "she": ("ram", "ewe", "lamb", "lambs"), "ewe": ("ram", "ewe", "lamb", "lambs"), "ovc": ("ram", "ewe", "lamb", "lambs"),
            "goa": ("buck", "doe", "kid", "kids"), "koz": ("buck", "doe", "kid", "kids"),
            "pig": ("boar", "sow", "piglet", "piglets"), "sow": ("boar", "sow", "piglet", "piglets"),
            "svi": ("boar", "sow", "piglet", "piglets"),
            "hor": ("stallion", "mare", "foal", "foals"), "kon": ("stallion", "mare", "foal", "foals"),
        }
    else:
        NAZIVI = {
            "gov": ("bik", "krava", "tele", "telad"), "bik": ("bik", "krava", "tele", "telad"),
            "kra": ("bik", "krava", "tele", "telad"), "ovc": ("ovan", "ovca", "jagnje", "jagnjad"),
            "ova": ("ovan", "ovca", "jagnje", "jagnjad"), "koz": ("jarac", "koza", "jare", "jarad"),
            "svi": ("nerast", "krmača", "prase", "prasad"), "kon": ("pastuv", "kobila", "ždrebe", "ždrebad"),
        }
    TER = ("In heat" if EN else "Tera se")
    TER_CIKLUS = {("cattle" if EN else "goveda"): 21, ("sheep" if EN else "ovce"): 17, ("goats" if EN else "koze"): 21, ("pigs" if EN else "svinje"): 21, ("horses" if EN else "konji"): 21}
    PARENJE = ("Mating / insemination" if EN else "Parenje / osemenjavanje")
    STADO_PODMLADAK = ("Young stock" if EN else "Podmladak")
    GRAVIDNOST_PROFILI = {
        ("romanov" if EN else "romanovska"): (("Romanov sheep" if EN else "Romanovska ovca"), ("sheep" if EN else "ovce"), ("romanov",), 138, 143, 140),
        ("sheep" if EN else "ovce"): (("Common sheep" if EN else "Obična ovca"), ("sheep" if EN else "ovce"), (), 145, 152, 150),
        ("goats" if EN else "koze"): (("Goat" if EN else "Koza"), ("goats" if EN else "koze"), (), 145, 151, 150),
        ("pigs" if EN else "svinje"): (("Pig" if EN else "Svinja"), ("pigs" if EN else "svinje"), (), 110, 120, 114),
        ("cattle" if EN else "goveda"): (("Cow" if EN else "Krava"), ("cattle" if EN else "goveda"), (), 275, 290, 283),
        ("horses" if EN else "konji"): (("Mare" if EN else "Kobila"), ("horses" if EN else "konji"), (), 320, 360, 340),
    }
    DOGADJAJI = [("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("In heat" if EN else "Tera se"), ("Birth" if EN else "Porođaj"), ("Vaccination" if EN else "Vakcinacija"), ("Treatment" if EN else "Lečenje"), ("Weighing" if EN else "Merenje težine"),
                 ("Move" if EN else "Premeštanje"), ("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće"), ("Note" if EN else "Napomena")]
    AUTO = ("Record change" if EN else "Promena u evidenciji")
    GRUPE = [(("Matings" if EN else "Parenja"), (("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("In heat" if EN else "Tera se"))),
             (("Treatments" if EN else "Lečenja"), (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))),
             (("Births" if EN else "Porođaji"), (("Birth" if EN else "Porođaj"), ("Offspring" if EN else "Potomak")))]


_jezicke_konstante()

# imena koja zavise od jezika; posle promene jezika svaki fajl programa dobija nove vrednosti
JEZICKA_IMENA = ("JEZIK", "EN", 'REDOSLEDI', 'POREKLA', 'VRSTE', 'NAZIVI', 'TER', 'TER_CIKLUS', 'PARENJE', 'STADO_PODMLADAK', 'GRAVIDNOST_PROFILI', 'DOGADJAJI', 'AUTO', 'GRUPE')
MODULI = ('osnova', 'jezik', 'podaci', 'izgled', 'rodoslov', 'ekran_osnova', 'ekran_grla', 'ekran_parenje', 'karton', 'gravidnost', 'istorija', 'kopije', 'obavestenja', 'stampa', 'telefon_prenos', 'app')


def postavi_jezik(novi):
    """Promeni jezik celog programa odmah ("sr" ili "en"), bez ponovnog pokretanja."""
    global JEZIK, EN
    JEZIK, EN = novi, novi == "en"
    _jezicke_konstante()
    vrednosti = {k: globals()[k] for k in JEZICKA_IMENA}
    for ime in MODULI:
        modul = sys.modules.get(ime)
        if modul is None:
            continue
        for k, v in vrednosti.items():
            if k in vars(modul):
                setattr(modul, k, v)
