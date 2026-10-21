"""Automatski testovi za Farmer: račun srodstva, čitanje i čuvanje tablica, oba jezika.
GitHub ih pokreće pre svake izgradnje; ako neki padne, nova verzija se ne objavljuje."""
import os
import sys

import pytest

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

import jezik      # noqa: E402  (fajlovi programa su u korenu repozitorijuma)
import podaci     # noqa: E402
import rodoslov   # noqa: E402
import app        # noqa: E402,F401  (proverava da se ceo program učitava bez greške)


class Program:
    """Pristup imenima programa bez obzira u kom fajlu su (Model, DOGADJAJI, procitaj_csv...)."""
    def __getattr__(self, ime):
        for m in (jezik, podaci, rodoslov):
            if ime in vars(m):
                return getattr(m, ime)
        raise AttributeError(ime)


def na_jeziku(j):
    jezik.postavi_jezik(j)
    return Program()


def red(i, o="", m="", pol="z", vrsta="ovce"):
    return dict(id=i, otac=o, majka=m, pol=pol, vrsta=vrsta, status="aktivno", markica="", rasa="")


STADO = [red("O", pol="m"), red("M"), red("B", "O", "M", "m"), red("S", "O", "M"), red("X", "B", "S"),
         red("O2", pol="m"), red("H", "O2", "M", "m"), red("Y", "H", "S"), red("Z", "B", "X"), red("N", "O2", "Y")]


@pytest.fixture(params=["sr", "en"])
def F(request):
    yield na_jeziku(request.param)
    jezik.postavi_jezik("sr")


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
    en = na_jeziku("en")
    put = str(tmp_path / "herd.csv")
    t = en.Tablica(put, ucitaj=False)
    t.redovi = [dict(r, vrsta="ovce") for r in STADO]
    t.sacuvaj()
    sr = na_jeziku("sr")
    redovi, _ = sr.procitaj_csv(put)
    assert len(redovi) == len(STADO)
    assert all(r["vrsta"] == "ovce" for r in redovi)
    assert sr.Model(redovi).inbr("Z") == pytest.approx(0.375)


def test_prevod_vrednosti():
    sr_dogadjaji = list(na_jeziku("sr").DOGADJAJI)
    en = na_jeziku("en")
    assert en.prevedi_vrednost(sr_dogadjaji[0]) == en.DOGADJAJI[0]
    en_dogadjaji = list(en.DOGADJAJI)
    sr = na_jeziku("sr")
    assert sr.prevedi_vrednost(en_dogadjaji[2]) == sr.DOGADJAJI[2]
    assert sr.prevedi_vrednost("neki moj tekst") == "neki moj tekst"


def test_promena_jezika_stize_do_svih_fajlova():
    """Posle promene jezika svaki fajl programa vidi nove nazive (bez ponovnog pokretanja)."""
    import kopije
    import istorija
    na_jeziku("en")
    assert kopije.EN and istorija.EN and podaci.EN
    assert istorija.DOGADJAJI[0] == "Mating / insemination"
    na_jeziku("sr")
    assert not kopije.EN and not istorija.EN
    assert istorija.DOGADJAJI[0] == "Parenje / osemenjavanje"


def test_vrsta(F):
    assert F.vrsta_norm("Ovce") == F.VRSTE[1]
    assert F.vrsta_norm("sheep") == F.VRSTE[1]
    assert F.vrsta_norm("Goveda") == F.VRSTE[0]


def test_procenat(F):
    assert F.pct(0.25) in ("25,0%", "25.0%")
    assert F.pct(0.0625) in ("6,25%", "6.25%")


# ---------------------------------------------------------------- telefon: spajanje podataka
def _z(grlo, uneto, dog, **kw):
    z = dict(grlo=grlo, datum="01.10.2026", dogadjaj=dog, opis="", partner="", vrednost="", automatski="", uneto=uneto,
             ishod="", ter="", karenca_meso="", karenca_mleko="")
    z.update(kw)
    return z


def test_telefon_spajanje_obe_strane():
    import telefon_prenos as telefon
    na_jeziku("sr")
    baza = [_z("M1", "2026-10-01 10:00:00", "Parenje / osemenjavanje", partner="O2")]
    tel = [dict(baza[0], ishod="leglo:2:21.10.2026:"), _z("M1", "2026-10-21 08:00:00", "Porođaj", vrednost="2")]
    rac = [dict(baza[0]), _z("O1", "2026-10-20 09:00:00", "Merenje težine", vrednost="78")]
    rez, st = telefon.spoji(baza, tel, rac, telefon._kljuc_ist, podaci.IST_KOLONE)
    assert len(rez) == 3
    assert rez[0]["ishod"] == "leglo:2:21.10.2026:"           # izmena sa telefona
    assert {z["dogadjaj"] for z in rez} == {"Parenje / osemenjavanje", "Merenje težine", "Porođaj"}
    assert st == dict(sa_telefona=2, novo=1, sukob=0)


def test_telefon_brisanje_na_racunaru_i_sukob():
    import telefon_prenos as telefon
    na_jeziku("sr")
    a, b = _z("A", "2026-10-01 10:00:00", "Napomena", opis="x"), _z("B", "2026-10-01 10:00:00", "Napomena", opis="y")
    rez, st = telefon.spoji([a, b], [a, dict(b, opis="telefon")], [dict(b, opis="racunar")], telefon._kljuc_ist, podaci.IST_KOLONE)
    assert [z["grlo"] for z in rez] == ["B"]                   # A obrisan na računaru ostaje obrisan
    assert rez[0]["opis"] == "telefon" and st["sukob"] == 1     # oba menjala -> telefon


def test_telefon_drugi_jezik_nije_sukob():
    """Računar je u međuvremenu prebačen na engleski: isti zapis na dva jezika nije promena."""
    import telefon_prenos as telefon
    try:
        na_jeziku("en")
        baza = [_z("M1", "2026-10-01 10:00:00", "Parenje / osemenjavanje", partner="O2")]
        rac = [dict(baza[0], dogadjaj="Mating / insemination")]
        tel = [dict(baza[0]), _z("S1", "2026-10-21 08:00:00", "Tera se")]
        rez, st = telefon.spoji(baza, tel, rac, telefon._kljuc_ist, podaci.IST_KOLONE)
        assert [z["dogadjaj"] for z in rez] == ["Mating / insemination", "In heat"]
        assert st == dict(sa_telefona=1, novo=1, sukob=0)
    finally:
        na_jeziku("sr")
