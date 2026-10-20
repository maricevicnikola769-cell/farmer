"""Automatski testovi za Farmer: račun srodstva, čitanje i čuvanje tablica, oba jezika.
GitHub ih pokreće pre svake izgradnje; ako neki padne, nova verzija se ne objavljuje."""
import importlib.util
import json
import os
import shutil
import sys

import pytest

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZVOR = next(os.path.join(KOREN, f) for f in ("Farmer.pyw", "Farmer_English.pyw", "farmer.pyw")
             if os.path.exists(os.path.join(KOREN, f)))


def ucitaj(folder, jezik):
    """Učita program kao modul, sa podacima u privremenom folderu i zadatim jezikom."""
    os.makedirs(folder, exist_ok=True)
    kopija = os.path.join(folder, "farmer_test.py")
    shutil.copy(IZVOR, kopija)
    with open(os.path.join(folder, "rodoslov_podesavanja.json"), "w", encoding="utf-8") as f:
        json.dump({"jezik": jezik}, f)
    ime = f"farmer_{jezik}_{abs(hash(folder))}"
    spec = importlib.util.spec_from_file_location(ime, kopija)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def red(i, o="", m="", pol="z", vrsta="ovce"):
    return dict(id=i, otac=o, majka=m, pol=pol, vrsta=vrsta, status="aktivno", markica="", rasa="")


STADO = [red("O", pol="m"), red("M"), red("B", "O", "M", "m"), red("S", "O", "M"), red("X", "B", "S"),
         red("O2", pol="m"), red("H", "O2", "M", "m"), red("Y", "H", "S"), red("Z", "B", "X"), red("N", "O2", "Y")]


@pytest.fixture(params=["sr", "en"])
def F(request, tmp_path):
    return ucitaj(str(tmp_path / request.param), request.param)


@pytest.mark.parametrize("grlo, ocekivano", [("X", 0.25), ("Y", 0.125), ("Z", 0.375), ("B", 0.0), ("O", 0.0)])
def test_inbriding(F, grlo, ocekivano):
    m = F.Model(STADO)
    assert m.inbr(grlo) == pytest.approx(ocekivano)


def test_srodstvo_brace(F):
    m = F.Model(STADO)
    assert m.kinship("B", "S") == pytest.approx(0.25)      # puni brat i sestra
    assert m.kinship("B", "H") == pytest.approx(0.125)     # polubraća
    assert m.r("B", "S") == pytest.approx(0.5)


def test_udeo_gena(F):
    m = F.Model(STADO)
    assert m.doprinos("X", "B") == pytest.approx(0.5)
    assert m.doprinos("X", "O") == pytest.approx(0.5)     # preko oba roditelja (inbriding)


def test_provere_gresaka(F):
    m = F.Model([red("A", "A")])                          # sam sebi roditelj
    assert m.warn
    m = F.Model([red("P", pol="z"), red("D", "P")])       # otac upisan kao žensko
    assert any("P" in w for w in m.warn)


def test_cuvanje_i_citanje_tablice(F, tmp_path):
    put = str(tmp_path / "test_stado.csv")
    t = F.Tablica(put, ucitaj=False)
    t.redovi = [dict(r, datum_rodjenja="01.02.2023") for r in STADO]
    t.sacuvaj()
    redovi, zag = F.procitaj_csv(put)
    assert len(redovi) == len(STADO)
    assert {r["id"] for r in redovi} == {r["id"] for r in STADO}
    assert F.Model(redovi).inbr("X") == pytest.approx(0.25)


def test_citanje_tablice_drugog_jezika(tmp_path):
    """Tablica sačuvana na engleskom mora da se pročita i na srpskom (i obrnuto)."""
    en = ucitaj(str(tmp_path / "en"), "en")
    put = str(tmp_path / "herd.csv")
    t = en.Tablica(put, ucitaj=False)
    t.redovi = [dict(r, vrsta="ovce") for r in STADO]
    t.sacuvaj()
    sr = ucitaj(str(tmp_path / "sr"), "sr")
    redovi, _ = sr.procitaj_csv(put)
    assert len(redovi) == len(STADO)
    assert all(r["vrsta"] == "ovce" for r in redovi)
    assert sr.Model(redovi).inbr("Z") == pytest.approx(0.375)


def test_prevod_vrednosti(tmp_path):
    sr = ucitaj(str(tmp_path / "sr"), "sr")
    en = ucitaj(str(tmp_path / "en"), "en")
    assert en.prevedi_vrednost(sr.DOGADJAJI[0]) == en.DOGADJAJI[0]
    assert sr.prevedi_vrednost(en.DOGADJAJI[2]) == sr.DOGADJAJI[2]
    assert sr.prevedi_vrednost("neki moj tekst") == "neki moj tekst"


def test_vrsta(F):
    assert F.vrsta_norm("Ovce") == F.VRSTE[1]
    assert F.vrsta_norm("sheep") == F.VRSTE[1]
    assert F.vrsta_norm("Goveda") == F.VRSTE[0]


def test_procenat(F):
    assert F.pct(0.25) in ("25,0%", "25.0%")
    assert F.pct(0.0625) in ("6,25%", "6.25%")
