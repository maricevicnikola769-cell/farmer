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
        p.write_bytes("id;pol\nA;z\nB;m\n".encode("utf-8"))          # bajtovi: Windows ne dodaje \r
        (tmp_path / "stado_finansije.csv").write_bytes("datum;vrsta;kategorija;iznos\n01.10.2026;trosak;Hrana;100\n".encode("utf-8"))
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


# ---------------------------------------------------------------- više jezika (fr, de, es, pt)
STRANI = ("fr", "de", "es", "pt")


@pytest.mark.parametrize("j", STRANI)
def test_strani_jezik_prevodi_i_sabloni(j):
    """Tekst se prevodi; tekst sa brojem/oznakom (šablon) dobija vrednosti na pravo mesto."""
    try:
        jezik.postavi_jezik(j)
        T = jezik.T
        assert T("Grla", "Animals") not in ("Grla", "Animals")
        poruka = T("Markica RS-77 je već upisana za grlo K12.", "Ear tag RS-77 is already entered for animal K12.")
        assert "RS-77" in poruka and "K12" in poruka and "already" not in poruka
        assert T("nešto novo", "something new") == "something new"          # nepoznat tekst ostaje engleski
        assert len(jezik.VRSTE) == 5 and len(set(jezik.VRSTE)) == 5
        for v in jezik.VRSTE:
            assert jezik.vrsta_kanon(v) and podaci.vrsta_norm(v) == v
        assert podaci.nazivi(jezik.VRSTE[0])[0] == T("bik", "bull")
        assert jezik.namene_za(jezik.VRSTE[3]) == jezik.NAMENE_SVINJE
    finally:
        jezik.postavi_jezik("sr")


def test_isti_brojevi_u_prevodima():
    """Svaki prevod šablona ima iste {0}, {1}… kao engleski tekst (inače bi poruka izgubila broj ili oznaku)."""
    import re
    import prevodi
    for j, recnik in prevodi.PREVODI.items():
        for en in prevodi.SABLONI:
            if en in recnik:
                assert sorted(re.findall(r"(?<!\{)\{\d+\}(?!\})", en)) == sorted(re.findall(r"(?<!\{)\{\d+\}(?!\})", recnik[en])), (j, en)


def test_podaci_prelaze_iz_jezika_u_jezik():
    """Događaj upisan na francuskom računaru čita se ispravno na srpskom, nemačkom… (i nazad)."""
    import osnova
    try:
        jezik.postavi_jezik("fr")
        fr = list(jezik.DOGADJAJI)
        for j in ("sr", "en", "de", "es", "pt", "fr"):
            jezik.postavi_jezik(j)
            assert [osnova.prevedi_vrednost(v) for v in fr] == list(jezik.DOGADJAJI), j
            assert podaci.vrsta_norm("Schweine") == jezik.VRSTE[3]
    finally:
        jezik.postavi_jezik("sr")


def test_mlecnost_samo_za_mlecne_vrste():
    """Mlečnost: ženke goveda, ovaca i koza (mlečne, kombinovane ili bez upisane namene); tovne rase, svinje, konji i mužjaci – ne."""
    import mlecnost
    jezik.postavi_jezik("sr")
    z = lambda vrsta, namena="", pol="z": dict(id="A", pol=pol, vrsta=vrsta, namena=namena, osnivac=False)
    assert mlecnost.muzna_vrsta(z("goveda", "mlečna")) and mlecnost.muzna_vrsta(z("koze", "kombinovana")) and mlecnost.muzna_vrsta(z("ovce"))
    assert not mlecnost.muzna_vrsta(z("goveda", "tovna")) and not mlecnost.muzna_vrsta(z("ovce", "tovna"))
    assert not mlecnost.muzna_vrsta(z("svinje", "mesnata")) and not mlecnost.muzna_vrsta(z("konji"))
    assert not mlecnost.muzna_vrsta(z("goveda", "mlečna", pol="m"))


def test_prirast_i_napomena(tmp_path):
    """Prirast iz merenja težine (g/dan) i napomena o grlu koja se čuva u tablici."""
    import prirast
    jezik.postavi_jezik("sr")
    ist = podaci.Istorija(str(tmp_path / "stado.csv"))
    for d, kg in (("01.01.2026", "200"), ("31.01.2026", "230,5"), ("02.03.2026", "248 kg")):
        ist.dodaj("T1", jezik.DOGADJAJI[5], "", vrednost=kg, datum=d)
    s = prirast.stat(ist, "T1")
    assert s["poslednje"][1] == 248 and s["od_prethodnog"] == 583 and s["prosek"] == 800 and s["dana_prethodno"] == 30
    assert prirast.stat(ist, "nema")["poslednje"] is None
    put = str(tmp_path / "stado.csv")
    t = podaci.Tablica(put, ucitaj=False)
    t.redovi = [dict(red("T1"), napomena="Agresivna – oprez")]
    t.sacuvaj()
    t2 = podaci.Tablica(put)
    assert t2.redovi[0]["napomena"] == "Agresivna – oprez"
    assert rodoslov.Model(t2.redovi).A["T1"]["napomena"] == "Agresivna – oprez"


def test_muzjak_iz_istog_stada():
    """Ženku pari mužjak iz njenog stada (iste vrste, u zapatu, stariji od 6 meseci)."""
    jezik.postavi_jezik("sr")
    r = lambda i, pol, stado, vrsta="goveda", dat="", status="aktivno": dict(red(i, pol=pol, vrsta=vrsta), stado=stado, datum_rodjenja=dat, status=status)
    m = rodoslov.Model([r("K1", "z", "Pašnjak"), r("B1", "m", "Pašnjak", dat="01.01.2020"), r("B2", "m", "Štala"),
                        r("T1", "m", "Pašnjak", dat=podaci.date.today().strftime("%d.%m.%Y")),     # tek rođeno muško tele
                        r("O1", "m", "Pašnjak", vrsta="ovce"), r("B3", "m", "Pašnjak", status="neaktivno")])
    assert m.muzjaci_u_stadu("K1") == ["B1"]
    assert rodoslov.Model([r("K2", "z", "")]).muzjaci_u_stadu("K2") == []


def test_izvoz_sa_srodnicima():
    """Izvoz označenog grla sa svim srodnicima: srodna grla idu kao neaktivna, nesrodna (O2) ne idu."""
    import izvoz
    jezik.postavi_jezik("sr")
    stado = [dict(r) for r in STADO]
    m = rodoslov.Model(stado)
    assert m.srodnici({"X"}) == {"B", "S", "O", "M", "H", "Y", "Z", "N"}
    sve = izvoz.tabele_za_izvoz(stado, m, samo_ids={"X"}, sa_srodnicima=True, sa_istorijom=False, sa_podsetnicima=False)
    zag, *redovi = sve[0][1]
    st = {r[0]: r[zag.index("status")] for r in redovi}
    assert st["X"] == "aktivno" and set(st) == {"X", "B", "S", "O", "M", "H", "Y", "Z", "N"}
    assert all(v == "neaktivno" for k, v in st.items() if k != "X")
    bez = izvoz.tabele_za_izvoz(stado, m, samo_ids={"X"}, sa_istorijom=False, sa_podsetnicima=False)
    assert [r[0] for r in bez[0][1][1:]] == ["X"]


def test_uvoz_sa_drugog_gazdinstva_isto_ime():
    """Isto ime sa drugog gazdinstva nije isto grlo: ista markica = isto grlo, inače novo ime (Bela 2)."""
    import izvoz
    nasa = [dict(red("Bela"), markica="SR-1"), dict(red("Bik", pol="m"), markica="RS-9"), dict(red("Mira"), poreklo_od="Farma A")]
    i = izvoz.Identiteti(nasa, "Farma A")
    assert i.id("Bela", "RS-5") == "Bela 2"            # druga markica -> drugo grlo
    assert i.id("Bela") == "Bela 2"                    # isto ime u istom fajlu -> isto (novo) grlo
    assert i.id("Bik", "RS-9") == "Bik"                # ista markica -> naše grlo
    assert i.id("Drugi", "SR-1") == "Bela"             # ista markica, drugo ime -> naše grlo
    assert i.id("Mira") == "Mira"                      # ranije uvezena sa te farme
    assert i.id("Nova") == "Nova" and i.preimenovana() == {"Bela": "Bela 2"}
    svoje = izvoz.Identiteti(nasa, "", tudje=False)    # svoja tablica iz Excela: isto ime = isto grlo
    assert svoje.id("Bela", "RS-5") == "Bela"


def test_uvoz_grlo_sa_promenjenom_markicom():
    """Grlo je na jednoj farmi dobilo novu minđušu: prepoznaje se po staroj markici (u oba smera) i po elektronskom broju."""
    import izvoz
    nasa = [dict(red("Bela"), markica="NOVA-2", stare_markice="STARA-1"), dict(red("Zora"), markica="Z-1", rfid="688000123")]
    i = izvoz.Identiteti(nasa, "Farma A")
    assert i.id("Bela", "STARA-1") == "Bela"                            # mi smo promenili markicu, oni imaju staru
    assert i.id("Belka", "NOVA-3", stare="NOVA-2") == "Bela"            # oni su promenili markicu (i ime)
    assert i.id("Zora", "DRUGA", rfid="688 000 123") == "Zora"          # elektronski broj se ne menja


def test_dnk_test_i_provera_porekla(tmp_path):
    """DNK test se čuva u istoriji; provera porekla se prepoznaje i kad je upisana na drugom jeziku."""
    import dnk
    try:
        jezik.postavi_jezik("fr")
        ist = podaci.Istorija(str(tmp_path / "herd.csv"))
        z = ist.dodaj("K1", jezik.DNK, jezik.DNK_POREKLO[2], datum="01/10/2026", vrednost=jezik.DNK_PROVERA)
        z.update(lab="Lab X", uzorak=jezik.DNK_UZORCI[0], fajl="K1_nalaz.pdf")
        ist.dodaj("K1", jezik.DNK, "A2/A2", datum="05/10/2026", vrednost=jezik.DNK_TESTOVI[6])
        ist.sacuvaj()
        jezik.postavi_jezik("sr")
        ist2 = podaci.Istorija(str(tmp_path / "herd.csv"))
        import osnova
        assert [osnova.prevedi_vrednost(z["vrednost"]) for z in dnk.dnk_zapisi(ist2, "K1")] == ["Beta-kazein A1/A2", "Provera porekla (otac i majka)"]
        o_ok, m_ok, zap = dnk.provera_porekla(ist2, "K1")
        assert (o_ok, m_ok) == (False, None) and zap["lab"] == "Lab X" and osnova.prevedi_vrednost(zap["uzorak"]) == "Dlaka" and zap["fajl"] == "K1_nalaz.pdf"
        assert dnk.provera_porekla(ist2, "nema") is None
    finally:
        jezik.postavi_jezik("sr")


def test_slike_dnk_sa_telefona(tmp_path):
    """Slika DNK nalaza poslata sa telefona se sačuva u folder dnk_nalazi; loše ime ili postojeći fajl se ne diraju."""
    import base64
    import dnk
    put = str(tmp_path / "stado.csv")
    slika = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff slika").decode()
    assert dnk.sacuvaj_slike_sa_telefona(put, {"K1_2026-11-02_a.jpg": slika, "../zlo.jpg": slika, "x.jpg": "nije slika"}) == 2
    f = tmp_path / "dnk_nalazi"
    assert sorted(os.listdir(f)) == ["K1_2026-11-02_a.jpg", "zlo.jpg"]
    assert (f / "K1_2026-11-02_a.jpg").read_bytes() == b"\xff\xd8\xff slika"
    assert dnk.sacuvaj_slike_sa_telefona(put, {"K1_2026-11-02_a.jpg": slika}) == 0      # već postoji


def _pdf_sa_tekstom(put, redovi):
    """Mali pravi PDF sa tekstom (kao nalaz koji laboratorija pošalje mejlom)."""
    sadrzaj = "BT /F1 12 Tf 50 750 Td 16 TL " + " ".join(f"({r}) Tj T*" for r in redovi) + " ET"
    obj = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
           "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
           f"<< /Length {len(sadrzaj)} >>\nstream\n{sadrzaj}\nendstream",
           "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    b, ofs = b"%PDF-1.4\n", []
    for i, o in enumerate(obj, 1):
        ofs.append(len(b))
        b += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(b)
    b += f"xref\n0 {len(obj) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in ofs).encode()
    b += f"trailer\n<< /Size {len(obj) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(put, "wb") as f:
        f.write(b)


def test_citanje_teksta_iz_nalaza(tmp_path):
    """PDF iz laboratorije se prepisuje tačno; slika ide na prepoznavanje (OCR) i označi se za proveru."""
    import citanje
    pdf = str(tmp_path / "nalaz.pdf")
    _pdf_sa_tekstom(pdf, ["Laboratorija Genetika", "Grlo: K1   Uzorak: dlaka", "Beta-kazein: A2/A2", "Otac: potvrdjen"])
    tekst, tacno = citanje.procitaj(pdf, "sr", ocr=lambda p, j: pytest.fail("PDF sa tekstom ne ide na OCR"))
    assert tacno and "Beta-kazein: A2/A2" in tekst and "Grlo: K1 Uzorak: dlaka" in tekst
    # skeniran PDF (bez teksta) i slika -> OCR, rezultat nije "tačan" dok ga korisnik ne proveri
    sken = str(tmp_path / "sken.pdf")
    _pdf_sa_tekstom(sken, [])
    pozivi = []
    ocr = lambda p, j: (pozivi.append((os.path.basename(p), j)), "  Rezultat:   A1/A2  \n\n\n kraj ")[1]
    assert citanje.procitaj(sken, "de", ocr=ocr) == ("Rezultat: A1/A2\n\nkraj", False)
    slika = tmp_path / "nalaz.JPG"
    slika.write_bytes(b"\xff\xd8\xff")
    assert citanje.procitaj(str(slika), "sr", ocr=ocr)[1] is False
    assert pozivi == [("sken.pdf", "de"), ("nalaz.JPG", "sr")]
    with pytest.raises(citanje.GreskaCitanja):
        citanje.procitaj(str(tmp_path / "nalaz.docx"), "sr", ocr=ocr)
    if sys.platform != "win32":       # OCR postoji samo u Windows-u; drugde jasna greška umesto pada
        with pytest.raises(citanje.GreskaCitanja):
            citanje.ocr_windows(str(slika))
    assert citanje.tekst_iz_pdf(str(slika)) == ""        # pokvaren / pogrešan fajl ne ruši program


def test_licenca(tmp_path, monkeypatch):
    """Proba 30 dana, besplatno 20 grla, aktivacija ključa (Lemon Squeezy), istek, rad bez interneta, zaštita fajla."""
    import licenca
    monkeypatch.setattr(licenca, "LS_STORE_ID", None)          # prava prodavnica se proverava u test_licenca_prodavnica
    from datetime import date
    put = str(tmp_path / "lic.json")
    d0 = date(2027, 1, 1)
    d = licenca.ucitaj(put, danas=d0)
    s = licenca.stanje(d, d0)
    assert s["paket"] == "proba" and s["limit"] is None and s["proba_dana"] == 30
    s = licenca.stanje(d, date(2027, 2, 1))                     # proba istekla -> besplatno do 20 grla
    assert s["paket"] == "probni" and s["limit"] == 20
    assert licenca.ima_mesta(s, 19) and not licenca.ima_mesta(s, 20) and not licenca.ima_mesta(s, 18, novih=3)
    assert licenca.aktivnih_grla([{"status": "aktivno"}, {"status": ""}, {"status": "neaktivno"}, {}]) == 3

    odgovor = {"activated": True, "valid": True, "error": None, "instance": {"id": "inst-1"},
               "license_key": {"status": "active", "expires_at": "2028-02-01T10:00:00.000000Z"},
               "meta": {"store_id": 1, "variant_id": 9, "product_name": "HerdDoc", "variant_name": "Pro – godišnje",
                        "customer_email": "farma@example.com"}}
    pozivi = []
    post = lambda akcija, polja: (pozivi.append((akcija, dict(polja))), odgovor)[1]
    nova = licenca.aktiviraj(d, " HD-7K2F-91QX\n-ZP4M ", danas=date(2027, 2, 1), post=post)
    assert pozivi[0][0] == "activate" and pozivi[0][1]["license_key"] == "HD-7K2F-91QX-ZP4M"
    assert nova["paket"] == "pro" and nova["instanca"] == "inst-1" and nova["istice"] == "2028-02-01" and nova["email"] == "farma@example.com"
    licenca.sacuvaj(nova, put)
    d = licenca.ucitaj(put)
    s = licenca.stanje(d, date(2027, 2, 10))
    assert s["paket"] == "pro" and s["limit"] == 500 and s["do"] == date(2028, 2, 1)
    assert licenca.stanje(d, date(2027, 5, 20))["razlog"] == "bez_provere"          # 90+ dana bez interneta
    assert licenca.stanje(d, date(2028, 2, 2))["razlog"] == "isteklo"
    # ručno prepravljen fajl ne važi (ni ključ ni proba)
    import json as _j
    sirovo = _j.load(open(put, encoding="utf-8"))
    sirovo["paket"] = "farma"
    _j.dump(sirovo, open(put, "w", encoding="utf-8"))
    assert licenca.stanje(licenca.ucitaj(put), date(2027, 2, 10))["paket"] == "probni"

    # paket po imenu proizvoda, tuđa prodavnica, greške
    assert licenca.paket_iz_odgovora({"product_name": "HerdDoc Farma"}) == "farma"
    assert licenca.paket_iz_odgovora({"product_name": "HerdDoc", "variant_name": "Osnovni"}) == "osnovni"
    with pytest.raises(licenca.GreskaLicence):
        licenca.paket_iz_odgovora({"product_name": "HerdDoc Probni"})
    stari = licenca.LS_STORE_ID
    try:
        licenca.LS_STORE_ID = 77
        with pytest.raises(licenca.GreskaLicence) as g:
            licenca.aktiviraj({}, "AAAA-BBBB-CCCC", post=post)
        assert g.value.kod == "prodavnica"
    finally:
        licenca.LS_STORE_ID = stari
    with pytest.raises(licenca.GreskaLicence) as g:
        licenca.aktiviraj({}, "AAAA-BBBB-CCCC", post=lambda a, p: {"activated": False, "error": "This license key has reached the activation limit."})
    assert g.value.kod == "limit"
    with pytest.raises(licenca.GreskaLicence) as g:
        licenca.aktiviraj({}, "AAAA-BBBB-CCCC", post=lambda a, p: {"activated": False, "error": "license_key not found."})
    assert g.value.kod == "nema"
    # provera: pretplata istekla; prebacivanje na drugi računar
    ist = dict(odgovor, valid=False, license_key={"status": "expired", "expires_at": "2027-05-01T00:00:00Z"})
    assert licenca.proveri(nova, danas=date(2027, 6, 1), post=lambda a, p: ist)["istice"] == "2027-05-01"
    assert licenca.deaktiviraj(dict(nova, prvi_start="2027-01-01"), post=lambda a, p: {"deactivated": True}) == {"prvi_start": "2027-01-01"}


def test_licenca_udruzenje_i_tablica(tmp_path, monkeypatch):
    """Paket Udruženje (bez ograničenja), 90 dana bez interneta, besplatna verzija pamti jednu tablicu."""
    import licenca
    monkeypatch.setattr(licenca, "LS_STORE_ID", None)
    from datetime import date
    assert licenca.paket_iz_odgovora({"product_name": "HerdDoc", "variant_name": "Udruženje"}) == "udruzenje"
    assert licenca.paket_iz_odgovora({"product_name": "HerdDoc Association"}) == "udruzenje"
    assert licenca.paket_iz_odgovora({"product_name": "HerdDoc Farma"}) == "farma"
    d = {"prvi_start": "2026-01-01", "tablica": "/x/stado.csv", "kljuc": "AAAA-BBBB", "paket": "udruzenje",
         "istice": "2027-12-31", "provereno": "2027-01-01"}
    s = licenca.stanje(d, date(2027, 3, 31))                 # 89 dana bez provere – i dalje radi
    assert s["paket"] == "udruzenje" and s["limit"] is None
    assert licenca.stanje(d, date(2027, 4, 2))["razlog"] == "bez_provere"
    odg = {"activated": True, "instance": {"id": "i"}, "license_key": {"status": "active", "expires_at": None},
           "meta": {"product_name": "HerdDoc", "variant_name": "Pro"}}
    nova = licenca.aktiviraj({"prvi_start": "2026-01-01", "tablica": "/x/stado.csv"}, "KEY-12345678", post=lambda a, p: odg)
    assert nova["tablica"] == "/x/stado.csv" and nova["paket"] == "pro"     # zapamćena tablica ostaje
    assert licenca.deaktiviraj(nova, post=lambda a, p: {"deactivated": True}) == {"prvi_start": "2026-01-01", "tablica": "/x/stado.csv"}


def test_precica_van_prodavnice():
    """Van Microsoft prodavnice (Setup.exe, Linux) program ne pita za ikonicu i ništa ne pamti."""
    import precica

    class A:
        pod = {}
        def sacuvaj_podesavanja(self):
            raise AssertionError("ne treba čuvati")

    a = A()
    assert precica.ime_paketa() is None
    precica.ponudi(a)
    assert "precica_pitano" not in a.pod
    assert precica._ps_tekst("it's") == "'it''s'"


def test_moje_vrste():
    """Korisnik doda vrstu (magarci): nazivi, gravidnost, teranje i filter rade; posle promene jezika vrsta ostaje."""
    import jezik
    import podaci
    jezik.postavi_jezik("sr")
    try:
        cist = jezik.postavi_moje_vrste([
            dict(ime="  Magarci ", m="magarac", z="magarica", ml="magare", mlm="magarad", gmin=355, gmax=380, gpr=365, ciklus=23),
            dict(ime="ovčarski psi", m="pas", z="kuja", ml="štene", mlm="štenad", gmin="58", gmax="68", gpr="63", ciklus=""),
            dict(ime="loše", gmin=200, gmax=100, gpr=150, ciklus=0),          # neispravno – ne ulazi
            dict(ime="ovce", gmin=145, gmax=152, gpr=150, ciklus=17),         # već postoji – ne duplira se
        ])
        assert [v["ime"] for v in cist] == ["magarci", "ovčarski psi", "ovce"]
        assert jezik.vrsta_kanon("Magarci") == "magarci"
        assert jezik.vrsta_kanon("ovčarski psi") == "ovčarski psi"           # ne meša se sa "ovce" (isti početak)
        assert podaci.nazivi("magarci") == ("magarac", "magarica", "magare", "magarad")
        assert jezik.VRSTE.count("ovce") == 1 and "magarci" in jezik.VRSTE
        assert jezik.TER_CIKLUS["magarci"] == 23 and "ovčarski psi" not in jezik.TER_CIKLUS
        assert jezik.GRAVIDNOST_PROFILI["moja:magarci"][3:] == (355, 380, 365)
        jezik.postavi_jezik("en")
        assert "magarci" in jezik.VRSTE and jezik.GRAVIDNOST_PROFILI["moja:magarci"][1] == "magarci"
        jezik.postavi_jezik("sr")
        jezik.postavi_moje_vrste([])
        assert "magarci" not in jezik.VRSTE and "moja:magarci" not in jezik.GRAVIDNOST_PROFILI
        assert jezik.vrsta_kanon("magarci") == ""
    finally:
        jezik.postavi_moje_vrste([])
        jezik.postavi_jezik("sr")


def test_licenca_prodavnica():
    """Prihvataju se samo ključevi iz HerdDoc prodavnice (516191); naziv varijante sa dvotačkom se prepoznaje."""
    import licenca
    import pytest
    assert licenca.LS_STORE_ID == 516191
    assert licenca.paket_iz_odgovora({"store_id": 516191, "product_name": "HerdDoc", "variant_name": "Osnovni / Basic:"}) == "osnovni"
    assert licenca.paket_iz_odgovora({"store_id": 516191, "product_name": "HerdDoc", "variant_name": "Udruženje / Association :"}) == "udruzenje"
    assert licenca.paket_iz_odgovora({"store_id": 516191, "product_name": "HerdDoc", "variant_name": "Farma / Farm:"}) == "farma"
    assert licenca.paket_iz_odgovora({"store_id": 516191, "product_name": "HerdDoc", "variant_name": "Pro:"}) == "pro"
    with pytest.raises(licenca.GreskaLicence) as g:
        licenca.paket_iz_odgovora({"store_id": 12345, "product_name": "HerdDoc", "variant_name": "Pro"})
    assert g.value.kod == "prodavnica"


def test_udeo_krvi_nova_rasa():
    """Udeo krvi kroz generacije (F1, povratno, F2), ručni udeo osnivača, razlika od cilja i kolona u tablici."""
    import podaci
    import rodoslov as r
    assert "udeo_krvi" in podaci.KOLONE
    assert r.procitaj_udeo("Romanovska 62,5%, pramenka 37,5") == {"romanovska": 0.625, "pramenka": 0.375}
    assert r.procitaj_udeo("a=60;b=50") == {} and r.procitaj_udeo("") == {}
    assert r.procitaj_udeo("a 75")[r.NEPOZNATO] == 0.25
    redovi = [dict(id="RO", rasa="romanovska", pol="m"), dict(id="PR", rasa="pramenka", pol="z"),
              dict(id="F1", otac="RO", majka="PR", pol="z", rasa="hibrid romanovska×pramenka"),
              dict(id="F1m", otac="RO", majka="PR", pol="m"),
              dict(id="BC", otac="RO", majka="F1", pol="z"),
              dict(id="F2", otac="F1m", majka="F1", pol="z"),
              dict(id="KUP", pol="m", rasa="melez", udeo_krvi="romanovska=75;pramenka=25"),
              dict(id="NN", pol="z")]
    m = r.Model(redovi)
    assert m.sastav("F1") == {"romanovska": 0.5, "pramenka": 0.5} and m.generacija_ukrstanja("F1")[1] == 1
    assert m.sastav("BC") == {"romanovska": 0.75, "pramenka": 0.25} and m.generacija_ukrstanja("BC")[1] == 2
    assert m.generacija_ukrstanja("F2")[0] == "F2"
    assert m.generacija_ukrstanja("RO")[1] == 0 and m.generacija_ukrstanja("NN")[1] is None
    assert m.sastav("KUP") == {"romanovska": 0.75, "pramenka": 0.25}
    cilj = {"romanovska": 0.625, "pramenka": 0.375}
    assert r.odstupanje(m.sastav("BC"), cilj) == 0.125
    pot = r.sastav_potomka(m.sastav("KUP"), m.sastav("F1"))          # 62,5 / 37,5 – tačno cilj
    assert abs(r.odstupanje(pot, cilj)) < 1e-9
    assert r.odstupanje({r.NEPOZNATO: 1.0}, cilj) == 1.0
    assert r.zapisi_udeo({"romanovska": 0.625, "pramenka": 0.375}) == "romanovska=62.5;pramenka=37.5"


def test_neodredjena_rasa():
    """Mladunče dve rase može da ostane 'neodređena – čeka DNK test'; udeo krvi se i dalje računa iz roditelja."""
    import podaci
    import rodoslov as r
    n = podaci.neodredjena_rasa()
    assert podaci.je_neodredjena(n) and podaci.je_neodredjena("Undetermined – awaiting DNA test")
    assert podaci.norm_rasa("  NEODREĐENA – čeka DNK test ") == n
    assert r.cista_rasa(n) == ""
    m = r.Model([dict(id="B", rasa="angus", pol="m"), dict(id="K", rasa="holštajn", pol="z"),
                 dict(id="T", otac="B", majka="K", rasa=n), dict(id="X", rasa=n)])
    assert m.sastav("T") == {"angus": 0.5, "holštajn": 0.5} and m.generacija_ukrstanja("T")[0] == "F1"
    assert m.sastav("X") == {r.NEPOZNATO: 1.0}


def test_iskacuca_poruka_jednom_dnevno():
    """Hitno obaveštenje iskoči kao poruka najviše jednom dnevno; isključeno – ne iskače."""
    import iskacuce

    class A(iskacuce.IskacuceDeo):
        def __init__(self):
            self.pod, self.prikazano = {}, []
        def obavestenja(self):
            return [dict(nivo=0, grlo="K1", naslov="Termin porođaja je prošao"), dict(nivo=3, grlo="K2", naslov="Vakcinacija za 20 d.")]
        def sacuvaj_podesavanja(self):
            pass
    a = A()
    nova = a.nova_za_poruku()
    assert [o["grlo"] for o in nova] == ["K1"]                      # samo hitno/skoro, ne zakazano
    a.zapamti_prikazana(nova)
    assert a.nova_za_poruku() == []                                 # isti dan – ne ponavlja se
    a.pod["iskaceno"]["datum"] = "2000-01-01"
    assert len(a.nova_za_poruku()) == 1                             # novi dan – ponovo
    assert a.iskacuce_ukljuceno() and not (a.pod.update(iskacuce=False) or a.iskacuce_ukljuceno())


def test_dogadjaj_zatvara_podsetnik(tmp_path):
    """Upis vakcinacije zatvara podsetnik 'Vakcinacija' tog grla; ponavljajući dobija sledeći termin; drugi ostaju."""
    from datetime import date, timedelta
    import obavestenja
    import podaci

    class A(obavestenja.ObavestenjaDeo):
        pass
    a = A()
    a.pods = podaci.Podsetnici(str(tmp_path / "stado.csv"))
    f = lambda d: d.strftime("%d.%m.%Y")
    d0 = date.today()
    a.pods.dodaj("Mina", f(d0 - timedelta(days=3)), "Vakcinacija", "bruceloza", 180)
    a.pods.dodaj("Mina", f(d0 + timedelta(days=60)), "Vakcinacija", "", 0)          # daleko u budućnosti – ostaje
    a.pods.dodaj("Mina", f(d0), "Lečenje", "", 0)                                    # druga vrsta – ostaje
    a.pods.dodaj("Lola", f(d0), "Vakcinacija", "", 0)                                # drugo grlo – ostaje
    n = a.zatvori_podsetnike(dict(grlo="Mina", dogadjaj="Vakcinacija", datum=f(d0)))
    assert n == 1
    akt = a.pods.aktivni()
    assert len(akt) == 4                                                             # 3 ostala + novi za 180 d.
    assert any(p["grlo"] == "Mina" and p["tip"] == "Vakcinacija" and podaci.parsiraj_datum(p["datum"]) > d0 + timedelta(days=170) for p in akt)


def test_rodoslovni_list_neograniceno(tmp_path, monkeypatch):
    """Rodoslovni list: na 'velikoj' strani sva kolena u tabeli; na A4 najviše 5, ostala se navode ispod tabele."""
    import stampa
    from rodoslov import Model
    redovi = []

    def napravi(i, d):
        r = dict(id=f"G{i}", vrsta="ovce", pol="m" if i % 2 == 0 else "z", status="aktivno")
        if d < 8:
            r["otac"], r["majka"] = f"G{2 * i}", f"G{2 * i + 1}"
            napravi(2 * i, d + 1)
            napravi(2 * i + 1, d + 1)
        redovi.append(r)
    napravi(1, 0)
    html = {}
    monkeypatch.setattr(stampa, "_otvori_html", lambda naziv, naslov, pod, telo, stil="": html.update(telo=telo, stil=stil) or naziv)

    class A:
        model = Model(redovi)
        prag = 0.0625
        tab = type("t", (), {"putanja": str(tmp_path / "stado.csv")})()
        ist = type("i", (), {"za": lambda self, x, auto=False: []})()
    stampa._napravi_rodoslov(A(), "G1", 8, "velika")
    assert "8. koleno" in html["telo"] and "Preci u daljim kolenima" not in html["telo"] and "mm;margin" in html["stil"]
    stampa._napravi_rodoslov(A(), "G1", 8, "A4")
    assert "5. koleno" in html["telo"] and "6. koleno" not in html["telo"]
    assert "Preci u daljim kolenima" in html["telo"] and "G256" in html["telo"] and "A4 landscape" in html["stil"]



def test_ocene_grla():
    """Ručne ocene se čuvaju/čitaju; zdravlje i rangiranje prirasta među grlima iste vrste."""
    import ocene
    import podaci
    assert "ocena" in podaci.KOLONE
    o, d = ocene.procitaj_ocenu("karakter=4;gradja=9;noge=x;vime=2@2026-11-11")
    assert o == {"karakter": 4, "vime": 2} and d == "2026-11-11"
    t = ocene.zapisi_ocenu({"karakter": 5}, "2026-01-02")
    assert t == "karakter=5@2026-01-02" and ocene.procitaj_ocenu(t)[0] == {"karakter": 5}
    assert ocene.zapisi_ocenu({}) == ""
    assert [ocene.zdravlje_ocena(n) for n in (0, 1, 3, 7)] == [5, 4, 2, 1]
    sve = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    assert ocene._rang_ocena(1000, sve) == 5 and ocene._rang_ocena(100, sve) == 1 and ocene._rang_ocena(500, [500, 1]) is None
    assert ocene.zvezdice(3.6) == "★★★★☆" and ocene.zvezdice(None) == "–"


def test_namena_za_celu_rasu():
    """Namena se zadaje za rasu: čita se iz grla te rase, menja kod svih; melezi biraju po grlu; vime samo kod nemlečnih ženki."""
    import namena_rase as nr
    red = [dict(id="A", vrsta="goveda", rasa="simentalska", namena="kombinovana", pol="z"),
           dict(id="B", vrsta="goveda", rasa="Simentalska", namena="kombinovana", pol="z"),
           dict(id="C", vrsta="goveda", rasa="simentalska", namena="mlečna", pol="m"),
           dict(id="D", vrsta="ovce", rasa="simentalska", namena="tovna", pol="z"),
           dict(id="E", vrsta="goveda", rasa="hibrid S×H", namena="mlečna", pol="z"),
           dict(id="F", vrsta="goveda", rasa="holštajn", namena="mlečna", pol="z")]
    assert nr.namena_rase(red, "goveda", "simentalska") == "kombinovana"
    assert nr.namena_rase(red, "goveda", "hibrid S×H") == "" and not nr.rasa_sa_namenom("hibrid S×H")
    prom = nr.postavi_namenu_rase(red, "goveda", "simentalska", "tovna")
    assert [r["id"] for r, _ in prom] == ["A", "B", "C"] and red[3]["namena"] == "tovna" and red[4]["namena"] == "mlečna"
    assert nr.vime_se_ocenjuje(red[0]) and not nr.vime_se_ocenjuje(red[5]) and not nr.vime_se_ocenjuje(red[2])


def test_moje_rase():
    """Rasa se upiše jednom: spisak se napravi od postojećih grla, nova rasa se pamti, melez ne ide na spisak."""
    import rase
    assert rase.ocisti_rasu(dict(vrsta="goveda", ime="hibrid S×H", namena="mlečna")) is None
    c = rase.ocisti_rasu(dict(vrsta="goveda", ime="  Holštajn ", namena="mlečna", autohtona=True))
    assert c == dict(vrsta="goveda", ime="holštajn", namena="mlečna", autohtona="1")
    assert rase.ocisti_rasu(dict(vrsta="goveda", ime="angus", namena="masna"))["namena"] == ""

    class Lazni(rase.RaseDeo):
        def __init__(self, redovi):
            self.pod = {}
            self.tab = type("T", (), {"redovi": redovi})()
    a = Lazni([dict(id="A", vrsta="goveda", rasa="angus", namena="tovna"), dict(id="B", vrsta="goveda", rasa="hibrid A×H"),
               dict(id="C", vrsta="ovce", rasa="pramenka", namena="kombinovana")])
    assert sorted((r["vrsta"], r["ime"], r["namena"]) for r in a.moje_rase()) == [("goveda", "angus", "tovna"), ("ovce", "pramenka", "kombinovana")]
    assert a.zapamti_rasu("goveda", "Holštajn", "mlečna") and a.nadji_rasu("goveda", "holštajn")["namena"] == "mlečna"
    assert not a.zapamti_rasu("goveda", "holštajn", "mlečna")
    assert a.rase_za_vrstu("goveda") == ["angus", "holštajn"] and a.rase_za_vrstu("ovce") == ["pramenka"]


def test_udruzenje_samo_pregled():
    """Udruženje: farme se upišu kodom; svaka šalje svoj potpisan pregled; tuđi (podmetnut) pregled se odbacuje."""
    import lazni_firebase
    import mreza as M
    from oblak import zakljucaj
    srv, st, konfig = lazni_firebase.napravi_server()
    try:
        m = M.nova_mreza("Udruženje odgajivača")
        a, a_t = M.novi_clan("Farma A", "Čačak")
        m["clanovi"].append(a)
        m.update(clan=a["id"], clan_tajni=a_t, naziv_farme="Farma A")
        o = M.oblak_mreze(konfig, m)
        M.objavi_spisak(o, m)
        # upis farme B i njen kod
        b = M.novi_clan("Farma B")[0]
        b_t, b["javni"] = M.novi_potpisni_kljuc()
        m["clanovi"].append(b)
        M.objavi_spisak(o, m)
        M.objavi_poziv(konfig, "K7M2-9XQP", dict(udr=m["udr"], kljuc=m["kljuc"], naziv=m["naziv"], admin_javni=m["admin_javni"],
                                                 clan=b["id"], clan_tajni=b_t, naziv_farme="Farma B"))
        p = M.preuzmi_poziv(konfig, "k7m2 9xqp")
        assert p["clan"] == b["id"] and M.preuzmi_poziv(konfig, "K7M2-9XQP") is None      # kod važi samo jednom
        mb = dict(udr=p["udr"], kljuc=p["kljuc"], naziv=p["naziv"], admin_javni=p["admin_javni"], uloga="clan",
                  clan=p["clan"], clan_tajni=p["clan_tajni"], naziv_farme="Farma B")
        ob = M.oblak_mreze(konfig, mb)
        redovi = [dict(id="Mina", pol="z", vrsta="ovce", rasa="pramenka", napomena="tajna beleška", stado="Gornje", status="aktivno"),
                  dict(id="X", pol="m", status="obrisano")]
        M.objavi_pregled(ob, mb, M.pregled_farme(redovi, "Farma B"))
        M.objavi_pregled(o, m, M.pregled_farme([dict(id="Bik", pol="m")], "Farma A", M.procitaj_lokaciju("43,8912 20,3456")))
        spisak = M.procitaj_spisak(ob, mb)
        assert [c["naziv"] for c in spisak["clanovi"]] == ["Farma A", "Farma B"]
        pr = M.procitaj_preglede(ob, mb, spisak)
        assert [g["id"] for g in pr[b["id"]]["grla"]] == ["Mina"] and "napomena" not in pr[b["id"]]["grla"][0]
        assert "stado" not in pr[b["id"]]["grla"][0] and [g["id"] for g in pr[a["id"]]["grla"]] == ["Bik"]
        assert pr[a["id"]]["lokacija"] == {"lat": 43.8912, "lon": 20.3456} and "lokacija" not in pr[b["id"]]
        assert M.procitaj_lokaciju("https://www.google.com/maps/place/X/@43.8,20.3,15z/data=!3m1!8m2!3d43.8912!4d20.3456") == {"lat": 43.8912, "lon": 20.3456}
        assert M.procitaj_lokaciju("100.5, 20.1") is None and M.procitaj_lokaciju("Čačak") is None
        assert M.lokacija_iz_teksta("  Prijevor,   Čačak ") == {"adresa": "Prijevor, Čačak"} and M.lokacija_iz_teksta("12") is None
        assert "query=Prijevor%2C%20%C4%8Ca%C4%8Dak" in M.mapa_url({"adresa": "Prijevor, Čačak"})
        assert "Prijevor" not in M.mapa_html([("A", "", 1, {"adresa": "Prijevor"})], "U")    # bez brojeva nije na zajedničkoj mapi
        assert "43.8912" in M.mapa_html([("A", "Čačak", 1, {"lat": 43.8912, "lon": 20.3456}), ("B", "", 0, None)], "U")
        # telefon dobija samo ključ za čitanje – bez tajnih ključeva za potpis
        class Lazni(M.MrezaDeo):
            pod = {"mreza": dict(m)}
            def mreza_dozvoljena(self): return True
        za_tel = Lazni().mreza_za_telefon()
        assert za_tel["udr"] == m["udr"] and "clan_tajni" not in za_tel and "admin_tajni" not in za_tel
        # farma B pokuša da pošalje podatke u ime farme A -> odbačeno (nema A-in ključ za potpis)
        lazno = dict(mb, clan=a["id"])
        M.objavi_pregled(ob, lazno, M.pregled_farme([dict(id="Lažno")], "Farma A"))
        pr = M.procitaj_preglede(o, m, M.procitaj_spisak(o, m))
        assert pr[a["id"]]["grla"] == [] and pr[a["id"]].get("greska")
        # i spisak farmi može da menja samo računar koji je napravio udruženje
        tekst = zakljucaj(dict(naziv="x", clanovi=[]), mb["kljuc"])
        ob.upisi("spisak", "glavni", dict(podaci=tekst, potpis=M.potpisi(mb["clan_tajni"], tekst)))
        try:
            M.procitaj_spisak(ob, mb)
            assert False, "podmetnut spisak je prihvaćen"
        except M.OblakGreska:
            pass
    finally:
        srv.shutdown()


def test_obavestenja_sat_i_unapred(monkeypatch):
    """Poruka ne iskače pre izabranog sata (a sledeća provera je tačno u taj sat); broj dana unapred se čuva u granicama."""
    from datetime import datetime as DT
    import iskacuce

    class A(iskacuce.IskacuceDeo):
        def __init__(self):
            self.pod, self.iskocilo, self.zakazano = {"obav_sat": 8}, [], []
            self.root = type("R", (), {"after": lambda _s, ms, fn: self.zakazano.append(ms)})()
        def obavestenja(self):
            return [dict(nivo=0, grlo="K1", naslov="Termin porođaja je prošao")]
        def sacuvaj_podesavanja(self):
            pass
        def iskacuca_poruka(self, stavke):
            self.iskocilo.append(stavke)

    class Sat(DT):
        trenutno = DT(2026, 11, 12, 6, 30)
        @classmethod
        def now(cls, tz=None):
            return cls.trenutno
    monkeypatch.setattr(iskacuce, "datetime", Sat)
    a = A()
    a.iskacuce_provera()
    assert a.iskocilo == [] and abs(a.zakazano[-1] - 30 * 60 * 1000) < 2000          # 6:30 – ćuti, proverava u 7:00
    Sat.trenutno = DT(2026, 11, 12, 7, 45)
    a.iskacuce_provera()
    assert a.iskocilo == [] and abs(a.zakazano[-1] - (15 * 60 + 5) * 1000) < 2000    # 7:45 – sledeća provera tačno u 8:00
    Sat.trenutno = DT(2026, 11, 12, 8, 0, 5)
    a.iskacuce_provera()
    assert len(a.iskocilo) == 1                                                      # 8:00 – iskoči
    assert a.dana_unapred() == 3 and a.obav_za_telefon() == {"sat": 8, "unapred": 3}
    a.pod["obav_unapred"] = 99
    assert a.dana_unapred() == 30
    a.pod["obav_unapred"] = "x"
    assert a.dana_unapred() == 3
