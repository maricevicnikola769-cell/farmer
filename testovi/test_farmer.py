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


def test_isto_ime_dobija_broj_po_redu():
    """Isto ime/oznaka: novo grlo dobija sledeći broj (Bela, Bela 2, Bela 3…), bez obzira na velika slova i razmake."""
    from podaci import slobodna_oznaka as s
    assert s("Bela", ["K1"]) == "Bela"
    assert s("Bela", ["Bela"]) == "Bela 2"
    assert s("bela", ["Bela", "Bela 2"]) == "bela 3"
    assert s("Bela 2", ["Bela", "Bela 2"]) == "Bela 3"
    assert s("  Bela ", ["BELA", "Bela 3"]) == "Bela 2"


def test_namena_rase(F, tmp_path):
    """Namena rase postoji za goveda, ovce, koze i svinje (ne za konje); čuva se u tablici i prevodi pri promeni jezika."""
    import jezik
    sr = jezik.EN is False
    ovce, svinje, goveda, konji = F.VRSTE[1], F.VRSTE[3], F.VRSTE[0], F.VRSTE[4]
    assert jezik.namene_za(ovce) == jezik.NAMENE_MALI and len(jezik.NAMENE_MALI) == 3
    assert jezik.namene_za(F.VRSTE[2]) == jezik.NAMENE_MALI
    assert jezik.namene_za(svinje) == jezik.NAMENE_SVINJE and jezik.namene_za(konji) == []
    assert jezik.namene_za(goveda) == jezik.NAMENE_MALI
    t = F.Tablica(str(tmp_path / "t.csv"), ucitaj=False)
    t.redovi = [dict(red("O1", pol="z", vrsta=ovce), namena=jezik.NAMENE_MALI[1])]
    t.sacuvaj()
    assert F.Tablica(t.putanja).redovi[0]["namena"] == jezik.NAMENE_MALI[1]
    drugi = na_jeziku("en" if sr else "sr")                  # isti fajl na drugom jeziku: vrednost se prevodi
    assert drugi.Tablica(t.putanja).redovi[0]["namena"] == jezik.NAMENE_MALI[1]
    assert jezik.NAMENE_MALI[1] == ("meat breed" if sr else "tovna")


def test_izvoz_sa_nazivom_gazdinstva(F, tmp_path):
    """Naziv gazdinstva stoji odmah pored oznake grla (i u rodovniku); kupac pri uvozu zna odakle su preci."""
    import izvoz
    stado = [dict(r) for r in STADO]
    for r in stado:
        if r["id"] not in ("Z", "N"):
            r["status"] = "neaktivno"
    m = F.Model(stado)
    l = izvoz.tabele_za_izvoz(stado, m, None, None, samo_zapat=True, gazdinstvo="Farma  Marić")
    zag = l[0][1][0]
    assert zag[1] in ("gazdinstvo", "farm") and all(r[1] == "Farma Marić" for r in l[0][1][1:])
    assert l[1][1][0][1] in ("gazdinstvo", "farm") and l[1][1][1][1] == "Farma Marić"
    p = str(tmp_path / "farma.xlsx")
    izvoz.izvezi_u_fajl(p, l, "xlsx")
    redovi, _ = F.procitaj_csv(p)
    assert sorted(r["id"] for r in redovi) == ["N", "Z"] and redovi[0]["gazdinstvo"] == "Farma Marić"
    tab = [{k: r.get(k, "") for k in F.KOLONE} for r in redovi]
    izvoz.dopuni_iz_excela(F.procitaj_xlsx(p), tab, None, None, p)
    m2 = F.Model(tab)
    assert m2.inbr("Z") == pytest.approx(m.inbr("Z"))
    assert {r["poreklo_od"] for r in tab if r["id"] not in ("N", "Z")} == {"Farma Marić"}


def test_autohtona_rasa(F, tmp_path):
    """Kvačica 'autohtona' za sve vrste: čuva se kao 1, iz Excela prihvata da/yes/x, poznate rase se prepoznaju."""
    from podaci import autohtona_rasa, da_ne
    assert autohtona_rasa("Buša") and autohtona_rasa("sjenička pramenka") and autohtona_rasa("mangulica")
    assert not autohtona_rasa("simentalska") and not autohtona_rasa("")
    assert [da_ne(x) for x in ("da", "Yes", "x", "1", "", "ne", "0")] == ["1", "1", "1", "1", "", "", ""]
    p = tmp_path / "a.csv"
    p.write_text("id;vrsta;pol;autohtona\nB1;goveda;z;da\nB2;goveda;z;\n", encoding="utf-8")
    r, _ = F.procitaj_csv(str(p))
    assert [x["autohtona"] for x in r] == ["1", ""]
    m = F.Model(r)
    assert m.A["B1"]["autohtona"] == "1"


def test_mlecnost_laktacija_i_procena(F, tmp_path):
    """Mužnja: upis po danu (izmena i brisanje istog dana), laktacija od telenja, procena za 305 dana; ne meša se u istoriju."""
    from datetime import date, timedelta
    import jezik
    import mlecnost
    zenka = dict(red("K1", pol="z", vrsta=F.VRSTE[0]), namena=jezik.NAMENE_MALI[0])
    tele = dict(red("T1", "", "K1", vrsta=F.VRSTE[0]), datum_rodjenja=("01/01/2026" if jezik.EN else "01.01.2026"))
    m = F.Model([zenka, tele])
    assert mlecnost.mlecno_grlo(m.A["K1"]) and not mlecnost.mlecno_grlo(m.A["T1"])
    ist = F.Istorija(str(tmp_path / "a.csv"))
    ix = mlecnost.MlekoIndeks(ist, m)
    poc = date(2026, 1, 1)
    for i in range(10):                                     # dani 1..10 laktacije, 20 L dnevno
        assert mlecnost.upisi_muznju(ist, ix, "K1", poc + timedelta(days=i), 20.0, 3.8, 3.3) == "novo"
    assert mlecnost.upisi_muznju(ist, ix, "K1", poc, 22.5) == "izmena"
    assert mlecnost.upisi_muznju(ist, ix, "K1", poc + timedelta(days=9), None) == "brisanje"
    assert len([z for z in ist.zapisi if z["dogadjaj"] == jezik.MUZNJA]) == 9
    assert ist.za("K1") == [] and len(ist.za("K1", mleko=True)) == 9  # obična istorija bez mužnje
    ix = mlecnost.MlekoIndeks(ist, m)
    s = ix.stat("K1", poc + timedelta(days=8))
    assert (s["br"], s["dan"]) == (1, 9) and s["ukupno"] == pytest.approx(22.5 + 8 * 20)
    assert s["prosek7"] == pytest.approx(20) and s["mast"] == pytest.approx(3.8)
    assert s["procena305"] == pytest.approx(22.5 + (22.5 + 20) / 2 + 7 * 20 + 20 * (305 - 9))
    ist.sacuvaj()
    procitano = F.Istorija(str(tmp_path / "a.csv"))
    z = [z for z in procitano.zapisi if z["dogadjaj"] == jezik.MUZNJA and z["vrednost"] == "22.5"]
    assert z and z[0]["mast"] == "" and z[0]["proteini"] == ""


def test_citac_mindjusa(F):
    """Broj sa RFID čitača nalazi grlo: po upisanom elektronskom broju ili po markici na kraju pročitanog broja."""
    from podaci import isti_broj_citaca
    assert isti_broj_citaca("688 000123456789", "688000123456789")
    assert isti_broj_citaca("688 0004021 01536", "RS 4021-01536")
    assert not isti_broj_citaca("688 000123456789", "6789")            # prekratko za poređenje po kraju
    redovi = [dict(red("A", pol="z"), markica="RS 4021-01536"), dict(red("B", pol="z"), rfid="688 000111222333"),
              red("C", "OTAC", "A")]
    m = F.Model(redovi)
    assert m.nadji_citac("688000111222333") == "B" and m.nadji("688 000111222333") == "B"
    assert m.nadji_citac("688 000402101536") == "A"
    assert m.nadji_citac("688 000999999999") is None and m.nadji_citac("OTAC") is None   # roditelj bez upisa nije grlo


def test_finansije(F, tmp_path):
    """Prihodi i troškovi: čuvanje i čitanje (i na drugom jeziku), zbir po kategoriji i grlu, period, unos iznosa."""
    from datetime import date
    import finansije as fn
    assert fn.broj("12.500,50") == 12500.5 and fn.broj("12,500.50") == 12500.5 and fn.broj("300") == 300 and fn.broj("x") is None
    fin = fn.Finansije(str(tmp_path / "stado.csv"))
    d = lambda dd: dd.strftime("%d/%m/%Y" if F.EN else "%d.%m.%Y")
    hrana, mleko = fn.kategorije(fn.TROSAK)[0], fn.kategorije(fn.PRIHOD)[0]
    fin.dodaj(d(date(2026, 10, 1)), fn.TROSAK, hrana, 12000, "K1")
    fin.dodaj(d(date(2026, 10, 5)), fn.PRIHOD, mleko, 30000.5)
    fin.dodaj(d(date(2025, 3, 1)), fn.TROSAK, hrana, 500)
    fin.sacuvaj()
    procitano = fn.Finansije(str(tmp_path / "stado.csv"))
    assert len(procitano.zapisi) == 3
    od, do = fn.period("mesec", date(2026, 10, 20))
    pr, tr, kat, grla = fn.zbir(procitano.u_periodu(od, do))
    assert (pr, tr) == (30000.5, 12000) and kat[(fn.TROSAK, hrana)] == 12000 and grla == {"K1": [0.0, 12000.0]}
    assert len(procitano.u_periodu(*fn.period("prosla_godina", date(2026, 10, 20)))) == 1
    assert len(procitano.u_periodu(*fn.period("sve"))) == 3
    import jezik
    drugi = "en" if not F.EN else "sr"                      # isti fajl na drugom jeziku: kategorije se prevode
    jezik.postavi_jezik(drugi)
    procitano2 = fn.Finansije(str(tmp_path / "stado.csv"))
    assert fn.kategorije(fn.TROSAK)[0] in {z["kategorija"] for z in procitano2.zapisi}
    assert {z["vrsta"] for z in procitano2.zapisi} == {fn.PRIHOD, fn.TROSAK}


def test_kopija_u_oblaku(tmp_path):
    """Kopija u oblaku: svi fajlovi šifrovano gore, stara kopija se briše, vraćanje ključem; bez kopije – snimak za telefone."""
    pytest.importorskip("cryptography")
    import base64
    import oblak
    import oblak_kopija as ok
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lazni_firebase
    srv, st, konfig = lazni_firebase.napravi_server()
    try:
        farma, kljuc = oblak.novo_gazdinstvo()
        link = oblak.link_za_uparivanje(farma, kljuc, "Farma Marić")
        assert ok.procitaj_kljuc(link) == (farma, kljuc, "Farma Marić") and ok.procitaj_kljuc("nešto drugo") is None
        o = oblak.Oblak(konfig, farma, kljuc)
        assert ok.preuzmi_kopiju(o, kljuc) is None                     # još ništa nije poslato
        o.posalji_snimak({"grla": [{"id": "A"}], "istorija": [], "podsetnici": [], "izvezeno": "x"})
        assert ok.preuzmi_kopiju(o, kljuc)["format"] == "farmer-telefon"  # rezerva: snimak za telefone
        p = tmp_path / "stado.csv"
        p.write_text("id;pol\nA;z\nB;m\n", encoding="utf-8")
        (tmp_path / "stado_finansije.csv").write_text("datum;vrsta;kategorija;iznos\n01.10.2026;trosak;Hrana;100\n", encoding="utf-8")
        sad = ok.napravi_sadrzaj([str(p), str(tmp_path / "stado_finansije.csv")], {"tablica": str(p), "prag": 0.05})
        ok.posalji_kopiju(o, kljuc, sad)
        ok.posalji_kopiju(o, kljuc, sad)                               # druga kopija briše prvu
        assert len({polja["pid"] for _, polja in o.lista("kopije")}) == 1
        vraceno = ok.preuzmi_kopiju(oblak.Oblak(konfig, farma, kljuc), kljuc)
        assert vraceno["format"] == "herddoc-kopija" and vraceno["podesavanja"]["prag"] == 0.05
        assert base64.b64decode(vraceno["fajlovi"]["stado.csv"]).decode() == "id;pol\nA;z\nB;m\n"
        assert "stado_finansije.csv" in vraceno["fajlovi"]
        with pytest.raises(oblak.OblakGreska):                         # pogrešan ključ ne otključava
            ok.preuzmi_kopiju(oblak.Oblak(konfig, farma, oblak.novo_gazdinstvo()[1]), oblak.novo_gazdinstvo()[1])
    finally:
        srv.shutdown()


def test_uparivanje_kodom(monkeypatch):
    """Kod umesto QR koda: telefon iz koda nalazi ključ gazdinstva; pogrešan ili istekao kod ne radi."""
    pytest.importorskip("cryptography")
    import oblak
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lazni_firebase
    srv, st, konfig = lazni_firebase.napravi_server()
    try:
        farma, kljuc = oblak.novo_gazdinstvo()
        kod = oblak.novi_kod()
        assert len(kod) == 9 and kod[4] == "-" and all(c in oblak.KOD_ABECEDA for c in kod.replace("-", ""))
        oblak.objavi_kod(konfig, kod, farma, kljuc, "Farma")
        assert oblak.preuzmi_kod(konfig, kod.lower().replace("-", " ")) == (farma, kljuc, "Farma")
        assert oblak.preuzmi_kod(konfig, "2222-3333") is None
        assert oblak.mesto_koda(kod)[0] != farma                        # mesto koda ne otkriva gazdinstvo
        stvarno = oblak.time.time
        monkeypatch.setattr(oblak.time, "time", lambda: stvarno() + oblak.KOD_TRAJANJE + 5)
        assert oblak.preuzmi_kod(konfig, kod) is None                   # posle 15 minuta ne važi
        monkeypatch.setattr(oblak.time, "time", stvarno)
        oblak.obrisi_kod(konfig, kod)
        assert oblak.preuzmi_kod(konfig, kod) is None
    finally:
        srv.shutdown()
