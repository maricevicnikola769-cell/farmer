"""Namena rase (mlečna / tovna / kombinovana, kod svinja mesnata / masna / kombinovana) važi za celu rasu,
a ne za svako grlo posebno. Čuva se i dalje u koloni "namena" svakog grla (zbog telefona i starih tablica),
ali se bira jednom: kad se promeni kod jednog grla čiste rase, menja se kod svih grla te rase.
Meleze, hibride i grla neodređene rase namena se bira po grlu (najčešće je ista kao kod majke)."""
from collections import Counter

import jezik
from jezik import namene_za, vrsta_kanon
from rodoslov import _je_melez


def rasa_sa_namenom(rasa):
    """Čista (imenovana) rasa – namena joj se zadaje jednom za sva grla."""
    return not _je_melez(rasa)


def _ista_rasa(r, vrsta, rasa):
    return (r.get("status") != "obrisano" and vrsta_kanon(r.get("vrsta")) == vrsta_kanon(vrsta)
            and " ".join(str(r.get("rasa") or "").split()).lower() == " ".join(str(rasa or "").split()).lower())


def grla_rase(redovi, vrsta, rasa):
    if not rasa_sa_namenom(rasa):
        return []
    return [r for r in redovi if _ista_rasa(r, vrsta, rasa)]


def namena_rase(redovi, vrsta, rasa, osim=None):
    """Namena koja je upisana za rasu (najčešća među njenim grlima), ili "" ako još nije zadata."""
    izbori = namene_za(vrsta)
    c = Counter(r.get("namena") for r in grla_rase(redovi, vrsta, rasa)
                if r is not osim and r.get("namena") in izbori)
    return c.most_common(1)[0][0] if c else ""


def postavi_namenu_rase(redovi, vrsta, rasa, namena):
    """Upiše namenu svim grlima rase. Vraća listu (grlo, stara namena) koja su promenjena."""
    promenjeno = []
    for r in grla_rase(redovi, vrsta, rasa):
        if (r.get("namena") or "") != namena:
            promenjeno.append((r, r.get("namena") or ""))
            r["namena"] = namena
    return promenjeno


def mlecna_namena(a):
    """Grlo mlečne rase (samo 'mlečna'; kombinovana i tovna nisu)."""
    return bool(a) and namene_za(a.get("vrsta")) == list(jezik.NAMENE_MALI) and a.get("namena") == jezik.NAMENE_MALI[0]


def vime_se_ocenjuje(a):
    """Vime se ocenjuje kod ženki koje nisu mlečne rase (kod mlečnih se prati mlečnost)."""
    return bool(a) and a.get("pol") == "z" and not mlecna_namena(a)
