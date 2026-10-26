"""Automatski testovi za HerdDoc (ranije Farmer): račun srodstva, čitanje i čuvanje tablica, oba jezika.
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


# ---------------------------------------------------------------- usklađivanje preko interneta (lažni server)
def test_oblak_zakljucavanje():
    pytest.importorskip("cryptography")
    import oblak
    farma, kljuc = oblak.novo_gazdinstvo()
    assert len(farma) >= 40
    tekst = oblak.zakljucaj({"grla": [{"id": "Ž1", "rasa": "romanovska"}]}, kljuc)
    assert "romanovska" not in tekst                       # server vidi samo nečitljiv tekst
    assert oblak.otkljucaj(tekst, kljuc)["grla"][0]["id"] == "Ž1"
    with pytest.raises(oblak.OblakGreska):
        oblak.otkljucaj(tekst, oblak.novo_gazdinstvo()[1])  # tuđi ključ ne otvara


def test_oblak_snimak_i_paketi():
    pytest.importorskip("cryptography")
    import secrets
    import oblak
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lazni_firebase
    srv, st, konfig = lazni_firebase.napravi_server()
    try:
        farma, kljuc = oblak.novo_gazdinstvo()
        o = oblak.Oblak(konfig, farma, kljuc)
        v = o.posalji_snimak({"x": secrets.token_hex(700_000)})          # ne sažima se -> više delova
        pz = o.citaj("stanje", "poslednji")
        assert pz["verzija"] == v and int(pz["ukupno"]) >= 2
        assert len(oblak.otkljucaj(o.procitaj_veliko("snimci", v, pz["ukupno"]), kljuc)["x"]) == 1_400_000
        # paket sa telefona u dva dela; nekompletan se ne uzima
        tekst = oblak.zakljucaj({"razlike": {}, "promene": [{"tekst": "probа"}]}, kljuc)
        o.upisi("paketi", "p1_000", dict(pid="p1", n=0, ukupno=2, deo=tekst[:10]))
        assert o.paketi() == []
        o.upisi("paketi", "p1_001", dict(pid="p1", n=1, ukupno=2, deo=tekst[10:]))
        (pid, sadrzaj, dok), = o.paketi()
        assert pid == "p1" and sadrzaj["promene"][0]["tekst"] == "probа"
        o.obrisi_paket(dok)
        assert o.lista("paketi") == []
        # drugo gazdinstvo ne vidi ove podatke
        assert oblak.Oblak(konfig, *oblak.novo_gazdinstvo()).citaj("stanje", "poslednji") is None
    finally:
        srv.shutdown()


def test_telefon_paket_razlike():
    import telefon_prenos as telefon
    na_jeziku("sr")
    rac = [_z("M1", "2026-10-01 10:00:00", "Parenje / osemenjavanje", partner="O2"),
           _z("O1", "2026-10-20 09:00:00", "Merenje težine", vrednost="78")]
    b = dict(rac[0])
    stavke = [dict(n=0, b=b, t=dict(b, ishod="leglo:2:21.10.2026:")),          # telefon zatvorio parenje
              dict(n=0, b=None, t=_z("M1", "2026-10-21 08:00:00", "Porođaj", vrednost="2"))]
    rez, st = telefon.spoji_razlike(stavke, rac, telefon._kljuc_ist, podaci.IST_KOLONE)
    assert [z["dogadjaj"] for z in rez] == ["Parenje / osemenjavanje", "Merenje težine", "Porođaj"]
    assert rez[0]["ishod"] == "leglo:2:21.10.2026:" and st == dict(sa_telefona=2, novo=1, sukob=0)
    rez2, st2 = telefon.spoji_razlike(stavke, rez, telefon._kljuc_ist, podaci.IST_KOLONE)   # isti paket dva puta
    assert len(rez2) == 3 and st2["sa_telefona"] == 0


def test_novi_kljuc_samo_za_odredjeni_telefon():
    """Isključivanje jednog telefona: novi ključ otvara samo telefon kome je namenjen."""
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives.asymmetric import ec
    import oblak
    marko, jovan = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    dok = oblak.omotaj_za(oblak._javni_od(marko), {"farma": "f2", "kljuc": "k2"})
    assert oblak.odmotaj(marko, dok) == {"farma": "f2", "kljuc": "k2"}
    with pytest.raises(oblak.OblakGreska):
        oblak.odmotaj(jovan, dok)


def test_kolona_upisao_cuva_se(tmp_path):
    na_jeziku("sr")
    put = str(tmp_path / "stado.csv")
    ist = podaci.Istorija(put)
    z = ist.dodaj("A", "Napomena", opis="x")
    z["upisao"] = "Marko"
    ist.sacuvaj()
    assert podaci.Istorija(put).zapisi[0]["upisao"] == "Marko"


def test_najsrodniji_parovi_veliko_stado_isto_kao_svaki_par():
    """Brzi način (samo bliski rod) daje iste parove mužjak–ženka sa r >= 0,25 kao proveravanje svakog para."""
    import random
    import ekran_parenje
    na_jeziku("sr")
    random.seed(3)
    redovi = [red(f"O{i}", pol="m") for i in range(4)] + [red(f"Z{i}") for i in range(8)]
    for n in range(300):
        o = random.choice([r["id"] for r in redovi if r["pol"] == "m"])
        m = random.choice([r["id"] for r in redovi if r["pol"] == "z"])
        redovi.append(red(f"X{n}", o, m, random.choice("mz")))
    mo = podaci.Model(redovi) if hasattr(podaci, "Model") else rodoslov.Model(redovi)
    ids = [a["id"] for a in mo.grla(True)]
    brzo = {(o, z) for r, o, z in ekran_parenje.najsrodniji_parovi(mo, ids, 0.25)}
    sporo = {(o, z) for o in ids for z in ids if mo.A[o]["pol"] == "m" and mo.A[z]["pol"] == "z" and mo.r(o, z) >= 0.25}
    assert brzo and brzo <= sporo
    assert len(brzo) >= 0.97 * len(sporo)          # izuzeci su samo jako inbredni daleki rođaci


def test_dnevnik_gresaka(tmp_path):
    import dnevnik
    dnevnik.LOG = str(tmp_path / "farmer-greske.log")
    try:
        1 / 0
    except ZeroDivisionError:
        dnevnik.zapisi_izuzetak(*sys.exc_info(), gde="proba")
    assert any("ZeroDivisionError" in l for l in dnevnik.poslednje_linije())


def test_izvoz_excel_i_csv(F, tmp_path):
    """Izvoz: Excel sa listovima (grla, rodovnik, istorija, podsetnici) i CSV fajlovi; obrisana grla se ne izvoze."""
    import zipfile
    import xml.dom.minidom
    import izvoz
    stado = [dict(r) for r in STADO] + [dict(red("P", "O", "M"), status="neaktivno"), dict(red("D"), status="obrisano")]
    stado[0]["markica"] = "RS 1234-5678"
    m = F.Model(stado)
    ist = F.Istorija(str(tmp_path / "stado.csv"))
    ist.dodaj("X", "Lečenje", "šćžđč <&> \"test\"")
    ist.dodaj("D", "Napomena", "obrisano grlo")
    pods = F.Podsetnici(str(tmp_path / "stado.csv"))
    pods.dodaj("X", "01.01.2027", "Vakcinacija")
    sve = izvoz.tabele_za_izvoz(stado, m, ist, pods)
    zapat = izvoz.tabele_za_izvoz(stado, m, ist, pods, samo_zapat=True)
    assert len(sve[0][1]) - 1 == 11 and len(zapat[0][1]) - 1 == 10      # P je van zapata, D je obrisano
    assert [len(l[1]) for l in sve[2:]] == [2, 2]                          # istorija obrisanog grla se ne izvozi
    rod = {r[0]: r for r in sve[1][1][1:]}
    assert rod["X"][2:4] == ["B", "S"] and rod["X"][4:8] == ["O (RS 1234-5678)", "M", "O (RS 1234-5678)", "M"]
    inb = {r[0]: r[-1] for r in sve[0][1][1:]}
    assert inb["X"] == 25.0 and inb["O"] == 0.0

    p = str(tmp_path / "izvoz.xlsx")
    assert izvoz.izvezi_u_fajl(p, sve, "xlsx") == [p]
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        for ime in z.namelist():
            if ime.endswith((".xml", ".rels")):
                xml.dom.minidom.parseString(z.read(ime))                   # svaki deo je ispravan XML
        assert len([n for n in z.namelist() if n.startswith("xl/worksheets/")]) == 4
        assert "šćžđč &lt;&amp;&gt;" in z.read("xl/worksheets/sheet3.xml").decode("utf-8")

    c = str(tmp_path / "izvoz.csv")
    fajlovi = izvoz.izvezi_u_fajl(c, sve, "csv")
    assert len(fajlovi) == 4 and all(os.path.isfile(f) for f in fajlovi)
    procitano, _ = F.procitaj_csv(c)                                       # izvezeni CSV program može ponovo da uveze
    assert {r["id"] for r in procitano} == {r["id"] for r in stado} - {"D"}


def test_uvoz_farmerovog_excela(F, tmp_path):
    """Kupac grla uvozi HerdDoc Excel: grla, preci iz lista Rodovnik (i kad nisu u listi grla), istorija i podsetnici."""
    import izvoz
    stado = [dict(r) for r in STADO]
    for r in stado:
        if r["id"] not in ("Z", "N"):
            r["status"] = "neaktivno"                    # u zapatu samo Z i N -> preci su samo u listu Rodovnik
    stado[0]["markica"] = "RS 1"
    m = F.Model(stado)
    ist = F.Istorija(str(tmp_path / "a.csv"))
    ist.dodaj("Z", "Lečenje", "test")
    pods = F.Podsetnici(str(tmp_path / "a.csv"))
    pods.dodaj("N", "01.01.2027", "Vakcinacija")
    p = str(tmp_path / "prodaja.xlsx")
    izvoz.izvezi_u_fajl(p, izvoz.tabele_za_izvoz(stado, m, ist, pods, samo_zapat=True), "xlsx")

    redovi, _ = F.procitaj_csv(p)
    assert sorted(r["id"] for r in redovi) == ["N", "Z"]
    tab = [{k: r.get(k, "") for k in F.KOLONE} for r in redovi]
    ist2 = F.Istorija(str(tmp_path / "b.csv"))
    pods2 = F.Podsetnici(str(tmp_path / "b.csv"))
    n_pr, n_ist, n_pod = izvoz.dopuni_iz_excela(F.procitaj_xlsx(p), tab, ist2, pods2, p)
    assert (n_ist, n_pod) == (1, 1) and n_pr >= 6
    m2 = F.Model(tab)
    assert m2.inbr("Z") == pytest.approx(m.inbr("Z")) and m2.inbr("N") == pytest.approx(m.inbr("N"))
    assert m2.A["O"]["markica"] == "RS 1" and m2.A["O"]["pol"] == "m"
    assert izvoz.dopuni_iz_excela(F.procitaj_xlsx(p), tab, ist2, pods2, p) == (0, 0, 0)   # drugi uvoz ne duplira


def test_izvoz_samo_oznacenih(F):
    """Izvoz samo označenih grla: i van zapata; istorija samo za njih; preci su u listu Rodovnik."""
    import izvoz
    stado = [dict(r) for r in STADO]
    stado[2]["status"] = "neaktivno"                      # B je van zapata, ali je označen
    m = F.Model(stado)
    l = izvoz.tabele_za_izvoz(stado, m, None, None, samo_ids={"B", "Z"})
    assert sorted(r[0] for r in l[0][1][1:]) == ["B", "Z"]
    assert {r[0]: r[2:4] for r in l[1][1][1:]}["Z"] == ["B", "X"]
