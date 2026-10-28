"""Štampa i PDF (rodoslovni list, plan parenja, spisak stada) i strana 'Statistika'."""
import os
import sys
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from osnova import EN, JEZIK, VERZIJA
from jezik import DOGADJAJI, PARENJE, T
from podaci import fmt_datum, fmt_starost, parsiraj_datum, pct, sort_key, starost_meseci
from izgled import BAD, BG, BRAND, INK, INK2, LINE, LOGO, OK, SURF, ScrollFrame, WARN
from rodoslov import procena


def _html_esc(t):
    return (str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


_HTML_STIL = """
*{box-sizing:border-box} body{font-family:'Segoe UI',Arial,sans-serif;color:#18221C;margin:0;background:#F3F5F1}
.list{max-width:900px;margin:24px auto;background:#fff;padding:34px 40px;border-radius:10px;box-shadow:0 2px 14px rgba(0,0,0,.08)}
.zag{display:flex;align-items:center;gap:16px;border-bottom:3px solid #2E5E45;padding-bottom:14px;margin-bottom:18px}
.zag img{width:56px;height:56px} .zag h1{margin:0;font-size:26px;color:#2E5E45} .zag .pod{color:#56645A;font-size:13px}
.zag .desno{margin-left:auto;text-align:right;color:#56645A;font-size:12px}
h2{font-size:15px;color:#2E5E45;margin:22px 0 8px;text-transform:uppercase;letter-spacing:.04em}
table{border-collapse:collapse;width:100%;font-size:12.5px} th,td{border:1px solid #D6DDD3;padding:5px 7px;text-align:left;vertical-align:middle}
th{background:#E9EDE6;font-weight:600} tr:nth-child(even) td{background:#FAFBF9}
.podaci td{border:none;padding:3px 10px 3px 0} .podaci td:first-child{color:#56645A;width:150px}
.rod td{border:1px solid #C9D3C6;height:34px;font-size:11.5px;background:#fff !important}
.rod .m{border-left:4px solid #3B6FB6} .rod .z{border-left:4px solid #C2577A} .rod .n{color:#9AA59D;border-left:4px solid #D6DDD3}
.rod b{font-size:12.5px} .rod small{color:#56645A}
.znak{display:inline-block;padding:2px 9px;border-radius:10px;font-weight:600;font-size:12px}
.ok{background:#DDF1E3;color:#23804A} .warn{background:#FBEBCB;color:#9A5C00} .bad{background:#F8DEDA;color:#B3322B}
.dno{margin-top:26px;border-top:1px solid #D6DDD3;padding-top:8px;color:#56645A;font-size:11px;display:flex;justify-content:space-between}
.potpis{margin-top:40px;display:flex;gap:60px} .potpis div{flex:1;border-top:1px solid #18221C;padding-top:4px;font-size:11px;color:#56645A}
.dugme{position:fixed;top:14px;right:14px;background:#2E5E45;color:#fff;border:none;padding:11px 18px;border-radius:8px;font-size:14px;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,.2)}
.sazetak{display:flex;gap:10px;flex-wrap:wrap} .sazetak div{background:#F3F5F1;border-radius:8px;padding:8px 14px;font-size:12px}
.sazetak b{display:block;font-size:18px;color:#2E5E45}
@media print{body{background:#fff}.list{box-shadow:none;margin:0;max-width:none;padding:0}.dugme{display:none}
 h2{break-after:avoid} tr{break-inside:avoid} @page{size:A4;margin:14mm}}
"""


def _otvori_html(naziv, naslov, podnaslov, telo):
    import tempfile
    logo = LOGO.get(64, "")
    if isinstance(logo, (tuple, list)):
        logo = "".join(logo)
    html = (f"<!doctype html><html lang='{JEZIK}'><head><meta charset='utf-8'><title>{_html_esc(naslov)}</title>"
            f"<style>{_HTML_STIL}</style></head><body>"
            f"<button class='dugme' onclick='window.print()'>{T('🖨 Štampaj / Sačuvaj kao PDF', '🖨 Print / Save as PDF')}</button>"
            f"<div class='list'><div class='zag'><img src='data:image/png;base64,{logo}' alt=''>"
            f"<div><h1>{_html_esc(naslov)}</h1><div class='pod'>{_html_esc(podnaslov)}</div></div>"
            f"<div class='desno'>HerdDoc {VERZIJA}<br>{fmt_datum(date.today())}</div></div>{telo}"
            f"<div class='dno'><span>{T('Napravljeno u programu HerdDoc', 'Made with HerdDoc')}</span>"
            f"<span>{_html_esc(os.path.basename(getattr(_html_esc, 'tablica', '') or ''))}</span></div></div></body></html>")
    folder = os.path.join(tempfile.gettempdir(), "HerdDoc-stampa")
    os.makedirs(folder, exist_ok=True)
    put = os.path.join(folder, naziv + ".html")
    with open(put, "w", encoding="utf-8") as f:
        f.write(html)
    try:
        if sys.platform.startswith("win"):
            os.startfile(put)
        else:
            import webbrowser
            webbrowser.open("file://" + put)
    except Exception:
        messagebox.showinfo("HerdDoc", T("Dokument je sačuvan ovde:\n", "The document was saved here:\n") + put)
    return put


def _znak(f, prag):
    t, boja = procena(f, prag)
    k = "ok" if boja == OK else "warn" if boja == WARN else "bad"
    return f"<span class='znak {k}'>{pct(f)} · {_html_esc(t)}</span>"


def _deca(m, x):
    return [y for y, (o, mm) in m.P.items() if x in (o, mm) and y in m.A and not m.A[y]["osnivac"]]


def _app_stampaj_rodoslov(self, x):
    m = self.model
    if x not in m.A:
        return
    _html_esc.tablica = self.tab.putanja
    a = m.A[x]
    f = m.inbr(x)
    red = lambda k, v: f"<tr><td>{_html_esc(k)}</td><td><b>{_html_esc(v)}</b></td></tr>" if v else ""
    o, mj = m.P.get(x, (None, None))
    podaci = ("<table class='podaci'>" + red(T("Oznaka", "ID"), x) + red(T("Ušna markica", "Ear tag"), a.get("markica"))
              + red(T("Vrsta", "Species"), a.get("vrsta")) + red(T("Rasa", "Breed"), a.get("rasa"))
              + red(T("Pol", "Sex"), m.pol_naziv(x)) + red(T("Datum rođenja", "Date of birth"), fmt_datum(a.get("datum")))
              + red(T("Starost", "Age"), fmt_starost(starost_meseci(a.get("datum"))))
              + red(T("Otac", "Sire"), o) + red(T("Majka", "Dam"), mj)
              + red(T("Stado", "Herd"), a.get("stado")) + red(T("Poreklo", "Origin"), a.get("poreklo"))
              + f"<tr><td>{T('Inbriding (F)', 'Inbreeding (F)')}</td><td>{_znak(f, self.prag)}</td></tr></table>")
    # rodoslov u 4 generacije
    niz = [[x]]
    for g in range(4):
        sl = []
        for y in niz[-1]:
            sl.extend(m.P.get(y, (None, None)) if y else (None, None))
        niz.append(sl)
    gens = max([2] + [g for g in range(1, 5) if any(niz[g])])   # prazna kolena se ne prikazuju
    redovi = 2 ** gens
    tab = "<table class='rod'><tr>" + "".join(f"<th>{T(n_sr, n_en)}</th>" for n_sr, n_en in
                                             (("Roditelji", "Parents"), ("Babe i dede", "Grandparents"),
                                              ("Prababe i pradede", "Great-grandparents"),
                                              ("4. koleno", "4th generation"))[:gens]) + "</tr>"
    for r in range(redovi):
        tab += "<tr>"
        for g in range(1, gens + 1):
            span = redovi // (2 ** g)
            if r % span:
                continue
            y = niz[g][r // span]
            if y and y in m.A:
                b = m.A[y]
                kl = "m" if b.get("pol") == "m" else "z"
                det = " · ".join(t for t in (b.get("markica"), b.get("rasa"),
                                              str(b["datum"].year) if b.get("datum") else "") if t)
                fy = m.inbr(y)
                tab += (f"<td rowspan='{span}' class='{kl}'><b>{_html_esc(y)}</b>"
                        + (f"<br><small>{_html_esc(det)}</small>" if det else "")
                        + (f"<br><small>F {pct(fy)}</small>" if fy > 0 else "") + "</td>")
            else:
                tab += f"<td rowspan='{span}' class='n'>{T('nepoznat', 'unknown')}</td>"
        tab += "</tr>"
    tab += "</table>"
    komp = m.kompletnost(x, gens)
    komp_t = " · ".join(f"{g}. {T('koleno', 'gen.')}: {n}/{u}" for g, n, u in komp)
    preci = [(d, p) for d, p in m.udeli_predaka(x) if d > 0][:8]
    preci_t = ""
    if preci:
        preci_t = (f"<h2>{T('Najveći udeo gena', 'Largest gene contributions')}</h2><table><tr><th>{T('Predak', 'Ancestor')}</th>"
                   f"<th>{T('Rasa', 'Breed')}</th><th>{T('Udeo gena', 'Gene share')}</th></tr>"
                   + "".join(f"<tr><td>{_html_esc(p)}</td><td>{_html_esc(m.A[p].get('rasa', ''))}</td><td>{pct(d)}</td></tr>"
                             for d, p in preci) + "</table>")
    deca = _deca(m, x)
    deca_t = ""
    if deca:
        deca_t = (f"<h2>{T('Potomci', 'Offspring')} ({len(deca)})</h2><table><tr><th>{T('Oznaka', 'ID')}</th>"
                  f"<th>{T('Pol', 'Sex')}</th><th>{T('Datum rođenja', 'Date of birth')}</th><th>{T('Drugi roditelj', 'Other parent')}</th></tr>"
                  + "".join(f"<tr><td>{_html_esc(y)}</td><td>{_html_esc(m.pol_naziv(y))}</td>"
                            f"<td>{fmt_datum(m.A[y].get('datum'))}</td>"
                            f"<td>{_html_esc(next((p for p in m.P.get(y, (None, None)) if p and p != x), ''))}</td></tr>"
                            for y in sorted(deca, key=sort_key)[:40]) + "</table>")
    ist = [z for z in self.ist.za(x, auto=False)][:20]
    ist_t = ""
    if ist:
        ist_t = (f"<h2>{T('Istorija', 'History')}</h2><table><tr><th>{T('Datum', 'Date')}</th><th>{T('Događaj', 'Event')}</th>"
                 f"<th>{T('Opis', 'Description')}</th></tr>"
                 + "".join(f"<tr><td>{_html_esc(z.get('datum'))}</td><td>{_html_esc(z.get('dogadjaj'))}</td>"
                           f"<td>{_html_esc(' '.join(t for t in (z.get('partner'), z.get('vrednost'), z.get('opis')) if t))}</td></tr>"
                           for z in ist) + "</table>")
    telo = (podaci + f"<h2>{T('Rodoslov', 'Pedigree')}</h2>" + tab
            + f"<div style='font-size:11.5px;color:#56645A;margin-top:6px'>{T('Poznati preci', 'Known ancestors')}: {komp_t}</div>"
            + preci_t + deca_t + ist_t
            + f"<div class='potpis'><div>{T('Odgajivač', 'Breeder')}</div><div>{T('Datum i potpis', 'Date and signature')}</div></div>")
    _otvori_html(f"rodoslov-{x}", T("Rodoslovni list", "Pedigree certificate"), f"{x} · {m.pol_naziv(x)}"
                 + (f" · {a['rasa']}" if a.get("rasa") else ""), telo)


def _app_stampaj_plan(self):
    m = self.model
    _html_esc.tablica = self.tab.putanja
    akt = m.grla(True)
    zenke = [a for a in akt if a["pol"] == "z"]
    muz = [a for a in akt if a["pol"] == "m"]
    ista = self.ui.get("ista_rasa")
    redovi = ""
    for z in sorted(zenke, key=lambda a: sort_key(a["id"])):
        opc = sorted((m.kinship(z["id"], x["id"]), x["id"]) for x in muz
                     if x["vrsta"] == z["vrsta"] and (not ista or x["rasa"] == z["rasa"]))
        if not opc:
            redovi += f"<tr><td><b>{_html_esc(z['id'])}</b></td><td>{_html_esc(z['rasa'])}</td><td colspan='3'>{T('nema odgovarajućeg mužjaka', 'no suitable male')}</td></tr>"
            continue
        celije = "".join(f"<td>{_html_esc(i)}<br>{_znak(f, self.prag)}</td>" for f, i in opc[:3])
        celije += "<td></td>" * (3 - min(3, len(opc)))
        redovi += f"<tr><td><b>{_html_esc(z['id'])}</b><br><small>{_html_esc(z.get('markica', ''))}</small></td><td>{_html_esc(z['rasa'])}</td>{celije}</tr>"
    telo = (f"<div class='sazetak'><div><b>{len(zenke)}</b>{T('ženskih grla', 'females')}</div><div><b>{len(muz)}</b>"
            f"{T('muških grla', 'males')}</div><div><b>{pct(self.prag)}</b>{T('granica rizika', 'risk limit')}</div></div>"
            f"<h2>{T('Predlog parenja (najmanje srodni mužjaci prvi)', 'Mating suggestions (least related males first)')}</h2>"
            f"<table><tr><th>{T('Ženka', 'Female')}</th><th>{T('Rasa', 'Breed')}</th><th>{T('1. izbor', '1st choice')}</th>"
            f"<th>{T('2. izbor', '2nd choice')}</th><th>{T('3. izbor', '3rd choice')}</th></tr>{redovi}</table>"
            f"<div style='font-size:11.5px;color:#56645A;margin-top:8px'>"
            f"{T('Procenat je očekivani inbriding potomka (F).', 'The percentage is the expected inbreeding of the offspring (F).')}</div>")
    _otvori_html("plan-parenja", T("Plan parenja", "Mating plan"), T("Predlog za celo stado", "Suggestions for the whole herd"), telo)


def _app_stampaj_spisak(self):
    m = self.model
    _html_esc.tablica = self.tab.putanja
    akt = sorted(m.grla(True), key=lambda a: (a.get("stado", ""), a.get("vrsta", ""), sort_key(a["id"])))
    po_vrsti = {}
    for a in akt:
        k = (a.get("vrsta", ""), a.get("pol"))
        po_vrsti[k] = po_vrsti.get(k, 0) + 1
    vrste = sorted({k[0] for k in po_vrsti})
    saz = "".join(f"<div><b>{po_vrsti.get((v, 'z'), 0) + po_vrsti.get((v, 'm'), 0) + po_vrsti.get((v, None), 0)}</b>"
                  f"{_html_esc(v)} ({po_vrsti.get((v, 'z'), 0)} {T('ž', 'f')} / {po_vrsti.get((v, 'm'), 0)} {T('m', 'm')})</div>"
                  for v in vrste)
    redovi = ""
    stado = None
    for a in akt:
        if a.get("stado", "") != stado:
            stado = a.get("stado", "")
            redovi += f"<tr><th colspan='9'>{T('Stado', 'Herd')}: {_html_esc(stado or T('bez naziva', 'unnamed'))}</th></tr>"
        o, mj = m.P.get(a["id"], (None, None))
        redovi += (f"<tr><td><b>{_html_esc(a['id'])}</b></td><td>{_html_esc(a.get('markica'))}</td><td>{_html_esc(a.get('vrsta'))}</td>"
                   f"<td>{_html_esc(a.get('rasa'))}</td><td>{_html_esc(m.pol_naziv(a['id']))}</td><td>{fmt_datum(a.get('datum'))}</td>"
                   f"<td>{_html_esc(o or '')}</td><td>{_html_esc(mj or '')}</td><td>{pct(m.inbr(a['id']))}</td></tr>")
    telo = (f"<div class='sazetak'><div><b>{len(akt)}</b>{T('grla u zapatu', 'animals in herd')}</div>{saz}</div>"
            f"<h2>{T('Spisak grla', 'Animal list')}</h2><table><tr><th>{T('Oznaka', 'ID')}</th><th>{T('Markica', 'Ear tag')}</th>"
            f"<th>{T('Vrsta', 'Species')}</th><th>{T('Rasa', 'Breed')}</th><th>{T('Pol', 'Sex')}</th><th>{T('Rođeno', 'Born')}</th>"
            f"<th>{T('Otac', 'Sire')}</th><th>{T('Majka', 'Dam')}</th><th>F</th></tr>{redovi}</table>")
    _otvori_html("spisak-stada", T("Spisak stada", "Herd list"), T("Sva grla u zapatu", "All animals in the herd"), telo)


# ---------------------------------------------------------------- izveštaji za veterinara i udruženje
IZVESTAJ_PERIODI = (("30", ("Poslednjih 30 dana", "Last 30 days")), ("mesec", ("Ovaj mesec", "This month")),
                    ("prosli_mesec", ("Prošli mesec", "Last month")), ("godina", ("Ova godina", "This year")),
                    ("prosla_godina", ("Prošla godina", "Last year")), ("12", ("Poslednjih 12 meseci", "Last 12 months")))


def period_izvestaja(kljuc, danas=None):
    from datetime import timedelta
    d = danas or date.today()
    if kljuc == "30":
        return d - timedelta(days=29), d
    if kljuc == "12":
        return d - timedelta(days=364), d
    from finansije import period
    return period(kljuc, d)


def _u_periodu(z, od, do):
    d = parsiraj_datum(z.get("datum"))
    return d is not None and od <= d <= do


def _ozn(m, x):
    """Oznaka grla sa markicom: 'Bela (RS 4021-01536)'."""
    if not x:
        return "–"
    a = m.A.get(x) or {}
    return _html_esc(x) + (f" <small>({_html_esc(a['markica'])})</small>" if a.get("markica") else "")


def _period_txt(od, do):
    return f"{fmt_datum(od)} – {fmt_datum(do)}"


def _app_izvestaj_lekova(self, kljuc="12"):
    """Evidencija upotrebe lekova i vakcina sa karencom – za veterinara i inspekciju."""
    from datetime import timedelta
    m = self.model
    _html_esc.tablica = self.tab.putanja
    od, do = period_izvestaja(kljuc)
    leci, vak = DOGADJAJI[4], DOGADJAJI[3]
    zap = sorted((z for z in self.ist.zapisi if z["dogadjaj"] in (leci, vak) and not z["automatski"] and _u_periodu(z, od, do)),
                 key=lambda z: (parsiraj_datum(z["datum"]), z["uneto"]))
    redovi = ""
    for z in zap:
        d = parsiraj_datum(z["datum"])
        kar = []
        for k, n in (("karenca_meso", T("meso", "meat")), ("karenca_mleko", T("mleko", "milk"))):
            try:
                dani = int(float(str(z.get(k) or "0").replace(",", ".")))
            except ValueError:
                dani = 0
            if dani:
                kar.append(f"{n}: {dani} {T('d.', 'd')} ({T('do', 'until')} {fmt_datum(d + timedelta(days=dani))})")
        redovi += (f"<tr><td>{fmt_datum(d)}</td><td>{_ozn(m, z['grlo'])}</td><td>{_html_esc(z['dogadjaj'])}</td>"
                   f"<td><b>{_html_esc(z['vrednost'] or '–')}</b></td><td>{_html_esc(z['opis'])}</td>"
                   f"<td>{'<br>'.join(kar) or '–'}</td><td>{_html_esc(z.get('upisao') or '')}</td></tr>")
    gaz = self.pod.get("gazdinstvo", "")
    telo = (f"<table class='podaci'><tr><td>{T('Gazdinstvo', 'Farm')}</td><td><b>{_html_esc(gaz or '–')}</b></td></tr>"
            f"<tr><td>{T('Period', 'Period')}</td><td><b>{_period_txt(od, do)}</b></td></tr>"
            f"<tr><td>{T('Broj upisa', 'Entries')}</td><td><b>{len(zap)}</b></td></tr></table>"
            f"<h2>{T('Upotreba lekova i vakcina', 'Use of medicines and vaccines')}</h2>"
            + (f"<table><tr><th>{T('Datum', 'Date')}</th><th>{T('Grlo', 'Animal')}</th><th>{T('Vrsta', 'Type')}</th>"
               f"<th>{T('Lek / vakcina', 'Medicine / vaccine')}</th><th>{T('Opis (dijagnoza, doza)', 'Description (diagnosis, dose)')}</th>"
               f"<th>{T('Karenca', 'Withdrawal')}</th><th>{T('Upisao', 'Entered by')}</th></tr>{redovi}</table>"
               if zap else f"<p>{T('U ovom periodu nema upisanih lečenja ni vakcinacija.', 'No treatments or vaccinations in this period.')}</p>")
            + f"<div class='potpis'><div>{T('Vlasnik gazdinstva', 'Farm owner')}</div><div>{T('Veterinar', 'Veterinarian')}</div></div>")
    _otvori_html("lekovi", T("Evidencija lekova i karence", "Medicine and withdrawal register"), _period_txt(od, do), telo)


def _app_izvestaj_rodjenja(self, kljuc="12"):
    """Spisak rođene teladi/jagnjadi… u periodu sa roditeljima – za prijavu udruženju odgajivača."""
    m = self.model
    _html_esc.tablica = self.tab.putanja
    od, do = period_izvestaja(kljuc)
    rodj = sorted((a for a in m.A.values() if not a["osnivac"] and not a.get("obrisano") and a["datum"] and od <= a["datum"] <= do),
                  key=lambda a: (a["datum"], sort_key(a["id"])))
    redovi = ""
    for a in rodj:
        o, mj = m.P.get(a["id"], (None, None))
        redovi += (f"<tr><td>{fmt_datum(a['datum'])}</td><td><b>{_html_esc(a['id'])}</b></td><td>{_html_esc(a['markica'] or '–')}</td>"
                   f"<td>{_html_esc(m.pol_naziv(a['id']))}</td><td>{_html_esc(a['vrsta'])}</td><td>{_html_esc(a['rasa'] or '–')}</td>"
                   f"<td>{_ozn(m, o)}</td><td>{_ozn(m, mj)}</td><td>{pct(m.inbr(a['id']))}</td></tr>")
    po_polu = {}
    for a in rodj:
        po_polu[a["pol"]] = po_polu.get(a["pol"], 0) + 1
    gaz = self.pod.get("gazdinstvo", "")
    telo = (f"<table class='podaci'><tr><td>{T('Gazdinstvo', 'Farm')}</td><td><b>{_html_esc(gaz or '–')}</b></td></tr>"
            f"<tr><td>{T('Period', 'Period')}</td><td><b>{_period_txt(od, do)}</b></td></tr></table>"
            f"<div class='sazetak'><div><b>{len(rodj)}</b>{T('rođeno', 'born')}</div>"
            f"<div><b>{po_polu.get('z', 0)}</b>{T('ženskih', 'female')}</div><div><b>{po_polu.get('m', 0)}</b>{T('muških', 'male')}</div></div>"
            f"<h2>{T('Rođena grla', 'Animals born')}</h2>"
            + (f"<table><tr><th>{T('Rođeno', 'Born')}</th><th>{T('Oznaka', 'ID')}</th><th>{T('Markica', 'Ear tag')}</th><th>{T('Pol', 'Sex')}</th>"
               f"<th>{T('Vrsta', 'Species')}</th><th>{T('Rasa', 'Breed')}</th><th>{T('Otac', 'Sire')}</th><th>{T('Majka', 'Dam')}</th><th>F</th></tr>"
               f"{redovi}</table>" if rodj else f"<p>{T('U ovom periodu nema upisanih rođenja.', 'No births recorded in this period.')}</p>")
            + f"<div class='potpis'><div>{T('Vlasnik gazdinstva', 'Farm owner')}</div><div>{T('Udruženje / selekcijska služba', 'Breed association')}</div></div>")
    _otvori_html("rodjenja", T("Prijava rođenih grla", "Birth report"), _period_txt(od, do), telo)


def _app_izvestaj_parenja(self, kljuc="12"):
    """Parenja i osemenjavanja u periodu sa ishodom i očekivanim porođajem – za udruženje i selekcijsku službu."""
    m = self.model
    _html_esc.tablica = self.tab.putanja
    od, do = period_izvestaja(kljuc)
    zap = sorted((z for z in self.ist.zapisi if z["dogadjaj"] == PARENJE and not z["automatski"] and _u_periodu(z, od, do)),
                 key=lambda z: (parsiraj_datum(z["datum"]), z["uneto"]))
    redovi = ""
    for z in zap:
        majka, otac = self.roditelji_parenja(z)
        oc = self.ocekivani_porodjaj(z)
        redovi += (f"<tr><td>{fmt_datum(parsiraj_datum(z['datum']))}</td><td>{_ozn(m, majka)}</td><td>{_ozn(m, otac)}</td>"
                   f"<td>{_html_esc(z['opis'])}</td><td>{fmt_datum(oc) if oc else '–'}</td>"
                   f"<td>{_html_esc(self.opis_ishoda(z))}</td>"
                   f"<td>{pct(m.kinship(majka, otac)) if majka in m.A and otac in m.A else '–'}</td></tr>")
    gaz = self.pod.get("gazdinstvo", "")
    telo = (f"<table class='podaci'><tr><td>{T('Gazdinstvo', 'Farm')}</td><td><b>{_html_esc(gaz or '–')}</b></td></tr>"
            f"<tr><td>{T('Period', 'Period')}</td><td><b>{_period_txt(od, do)}</b></td></tr>"
            f"<tr><td>{T('Broj parenja', 'Matings')}</td><td><b>{len(zap)}</b></td></tr></table>"
            f"<h2>{T('Parenja i osemenjavanja', 'Matings and inseminations')}</h2>"
            + (f"<table><tr><th>{T('Datum', 'Date')}</th><th>{T('Ženka', 'Female')}</th><th>{T('Mužjak / bik', 'Male / sire')}</th>"
               f"<th>{T('Opis (VO, prirodno…)', 'Description (AI, natural…)')}</th><th>{T('Očekivani porođaj', 'Expected birth')}</th>"
               f"<th>{T('Ishod', 'Outcome')}</th><th>{T('Inbriding potomka', 'Offspring inbreeding')}</th></tr>{redovi}</table>"
               if zap else f"<p>{T('U ovom periodu nema upisanih parenja.', 'No matings recorded in this period.')}</p>")
            + f"<div class='potpis'><div>{T('Vlasnik gazdinstva', 'Farm owner')}</div><div>{T('Osemenjivač / udruženje', 'Inseminator / association')}</div></div>")
    _otvori_html("parenja", T("Izveštaj o parenjima i osemenjavanju", "Mating and insemination report"), _period_txt(od, do), telo)


# ---------------------------------------------------------------- statistika
def _crtaj_stubice(self, parent, naslov, podaci, boja=BRAND, sirina=520, visina=200, fmt=str):
    o, c = self.card(parent)
    o.pack(fill="x", pady=(0, 14))
    self.lbl(c, naslov, 11, "bold").pack(anchor="w")
    if not podaci:
        self.lbl(c, T("Još nema podataka.", "No data yet."), 9, fg=INK2).pack(anchor="w", pady=6)
        return
    cv = tk.Canvas(c, width=sirina, height=visina, bg=SURF, highlightthickness=0)
    cv.pack(anchor="w", pady=(8, 0), fill="x")
    def nacrtaj(e=None):
        cv.delete("all")
        W = max(200, cv.winfo_width() or sirina)
        H = visina
        lev, dno, vrh = 8, 34, 18
        mx = max(v for _, v in podaci) or 1
        n = len(podaci)
        kor = (W - lev * 2) / n
        bw = min(46, kor * 0.68)
        cv.create_line(lev, H - dno, W - lev, H - dno, fill=LINE)
        for i, (k, v) in enumerate(podaci):
            x = lev + kor * i + kor / 2
            h = (H - dno - vrh) * (v / mx)
            cv.create_rectangle(x - bw / 2, H - dno - h, x + bw / 2, H - dno, fill=boja, outline="")
            cv.create_text(x, H - dno - h - 8, text=fmt(v), fill=INK, font=self.f(9, "bold"))
            cv.create_text(x, H - dno + 12, text=str(k)[:12], fill=INK2, font=self.f(8))
    cv.bind("<Configure>", nacrtaj)
    nacrtaj()


def _app_s_statistika(self):
    m = self.model
    sf = ScrollFrame(self.main, bg=BG)
    sf.pack(fill="both", expand=True)
    body = tk.Frame(sf.inner, bg=BG)
    body.pack(fill="both", expand=True, padx=32, pady=28)
    self.zaglavlje(body, T("Statistika", "Statistics"), T("Pregled stada u brojevima i grafikonima.",
                                                          "Your herd in numbers and charts."),
                   akcije=((T("🖨 Spisak stada", "🖨 Herd list"), self.stampaj_spisak, "Secondary"),))
    akt = m.grla(True)
    if not akt:
        self.napomena(body, T("U zapatu još nema grla.", "There are no animals in the herd yet."))
        return
    fs = [m.inbr(a["id"]) for a in akt]
    zen = sum(1 for a in akt if a["pol"] == "z")
    muz = sum(1 for a in akt if a["pol"] == "m")
    iznad = sum(1 for f in fs if f > self.prag)
    red = tk.Frame(body, bg=BG)
    red.pack(fill="x", pady=(0, 14))
    for vr, opis, boja in ((len(akt), T("grla u zapatu", "animals in herd"), BRAND),
                           (f"{zen} / {muz}", T("ženska / muška", "female / male"), INK),
                           (pct(sum(fs) / len(fs)), T("prosečan inbriding", "average inbreeding"), INK),
                           (iznad, T("iznad granice rizika", "above the risk limit"), BAD if iznad else OK)):
        o, c = self.card(red, padx=16, pady=12)
        o.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl(c, str(vr), 20, "bold", fg=boja).pack(anchor="w")
        self.lbl(c, opis, 9, fg=INK2).pack(anchor="w")
    # po rasi
    rase = {}
    for a in akt:
        k = a.get("rasa") or T("bez rase", "no breed")
        rase[k] = rase.get(k, 0) + 1
    _crtaj_stubice(self, body, T("Grla po rasi", "Animals by breed"), sorted(rase.items(), key=lambda t: -t[1])[:10])
    # rođenja po godinama
    god = {}
    for a in m.grla(False):
        if a.get("datum"):
            god[a["datum"].year] = god.get(a["datum"].year, 0) + 1
    _crtaj_stubice(self, body, T("Rođena grla po godinama", "Animals born per year"), sorted(god.items())[-10:], boja="#3B6FB6")
    # inbriding
    klase = [(T("0%", "0%"), 0), ("<3,1%" if not EN else "<3.1%", 0), ("<6,25%" if not EN else "<6.25%", 0),
             ("<12,5%" if not EN else "<12.5%", 0), ("≥12,5%" if not EN else "≥12.5%", 0)]
    cnt = [0] * 5
    for f in fs:
        cnt[0 if f == 0 else 1 if f < 0.03125 else 2 if f < 0.0625 else 3 if f < 0.125 else 4] += 1
    _crtaj_stubice(self, body, T("Inbriding grla u zapatu", "Inbreeding of animals in the herd"),
                   [(klase[i][0], cnt[i]) for i in range(5)], boja=WARN)
    # porođaji po mesecima (poslednjih 12)
    porod = DOGADJAJI[2]
    danas = date.today()
    meseci = []
    for i in range(11, -1, -1):
        y, mm = danas.year, danas.month - i
        while mm <= 0:
            mm += 12
            y -= 1
        meseci.append((y, mm))
    br = {k: 0 for k in meseci}
    for z in self.ist.zapisi:
        if z.get("dogadjaj") == porod:
            d = parsiraj_datum(z.get("datum"))
            if d and (d.year, d.month) in br:
                br[(d.year, d.month)] += 1
    if any(br.values()):
        _crtaj_stubice(self, body, T("Porođaji u poslednjih 12 meseci", "Births in the last 12 months"),
                       [(f"{mm:02d}/{str(y)[2:]}", br[(y, mm)]) for y, mm in meseci], boja=OK)


def _app_s_stampa(self):
    sf = ScrollFrame(self.main, bg=BG)
    sf.pack(fill="both", expand=True)
    body = tk.Frame(sf.inner, bg=BG)
    body.pack(fill="both", expand=True, padx=32, pady=28)
    self.zaglavlje(body, T("Štampa i PDF", "Print and PDF"),
                   T("Dokument se otvara u pregledaču. Tamo klikni „Štampaj / Sačuvaj kao PDF“.",
                     "The document opens in your browser. Click “Print / Save as PDF” there."))
    def stavka(naslov, opis, dugme, cmd, dodatak=None):
        o, c = self.card(body)
        o.pack(fill="x", pady=(0, 12))
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        lev = tk.Frame(red, bg=SURF)
        lev.pack(side="left", fill="x", expand=True)
        self.lbl(lev, naslov, 12, "bold").pack(anchor="w")
        self.lbl(lev, opis, 9, fg=INK2, justify="left", wraplength=520).pack(anchor="w", pady=(2, 0))
        self.btn(red, dugme, cmd, "Primary").pack(side="right")
        if dodatak:
            dodatak(red)
    izbor = tk.StringVar()
    def birac(red):
        ids = [a["id"] for a in self.model.grla(False)]
        cb = ttk.Combobox(red, textvariable=izbor, values=ids, width=16, font=self.f(10))
        cb.pack(side="right", padx=10)
        if ids:
            izbor.set(ids[0])
    def rodoslov():
        x = self.model.nadji(izbor.get()) if izbor.get() else None
        if not x:
            messagebox.showwarning("HerdDoc", T("Izaberi ili upiši oznaku grla.", "Choose or type an animal ID."))
            return
        self.stampaj_rodoslov(x)
    stavka(T("Rodoslovni list grla", "Pedigree certificate"),
           T("Podaci o grlu, rodoslov u 4 kolena, inbriding, potomci i istorija. Za prodaju, sajmove i matičnu evidenciju.",
             "Animal data, 4-generation pedigree, inbreeding, offspring and history. For sales, shows and registries."),
           T("🖨 Napravi", "🖨 Create"), rodoslov, birac)
    stavka(T("Plan parenja", "Mating plan"),
           T("Za svaku ženku tri najmanje srodna mužjaka i očekivani inbriding potomka.",
             "For each female the three least related males and the expected inbreeding of the offspring."),
           T("🖨 Napravi", "🖨 Create"), self.stampaj_plan)
    stavka(T("Spisak stada", "Herd list"),
           T("Sva grla u zapatu po stadima, sa markicama, roditeljima i inbridingom. Za veterinara ili inspekciju.",
             "All animals in the herd by herd group, with ear tags, parents and inbreeding. For the vet or inspection."),
           T("🖨 Napravi", "🖨 Create"), self.stampaj_spisak)
    st_iz = self.ui.setdefault("izvestaj", {"period": "12"})
    pv = tk.StringVar(value=T(*dict(IZVESTAJ_PERIODI)[st_iz["period"]]))

    def birac_perioda(red):
        cb = ttk.Combobox(red, textvariable=pv, values=[T(*n) for _, n in IZVESTAJ_PERIODI], state="readonly", width=19, font=self.f(10))
        cb.pack(side="right", padx=10)
        cb.bind("<<ComboboxSelected>>", lambda e: st_iz.update(period=next(k for k, n in IZVESTAJ_PERIODI if T(*n) == pv.get())))
    self.lbl(body, T("Izveštaji za veterinara i udruženje", "Reports for the vet and breed association"), 13, "bold").pack(anchor="w", pady=(10, 8))
    stavka(T("Evidencija lekova i karence", "Medicine and withdrawal register"),
           T("Sva lečenja i vakcinacije u periodu: grlo, lek, doza, karenca za meso i mleko (do kog datuma). Za veterinara i inspekciju.",
             "All treatments and vaccinations in the period: animal, medicine, dose, meat and milk withdrawal (until which date). For the vet and inspection."),
           T("🖨 Napravi", "🖨 Create"), lambda: self.izvestaj_lekova(st_iz["period"]), birac_perioda)
    stavka(T("Prijava rođenih grla", "Birth report"),
           T("Grla rođena u periodu sa markicom, polom, rasom, ocem i majkom. Za udruženje odgajivača i matičnu evidenciju.",
             "Animals born in the period with ear tag, sex, breed, sire and dam. For the breed association and herd book."),
           T("🖨 Napravi", "🖨 Create"), lambda: self.izvestaj_rodjenja(st_iz["period"]))
    stavka(T("Parenja i osemenjavanja", "Matings and inseminations"),
           T("Parenja u periodu: ženka, bik, način (VO, prirodno), očekivani porođaj, ishod i inbriding potomka.",
             "Matings in the period: female, sire, method (AI, natural), expected birth, outcome and offspring inbreeding."),
           T("🖨 Napravi", "🖨 Create"), lambda: self.izvestaj_parenja(st_iz["period"]))
    self.lbl(body, T("Period za izveštaje biraš kod prvog izveštaja i važi za sva tri.",
                     "The report period is chosen at the first report and applies to all three."), 8, fg=INK2).pack(anchor="w", pady=(0, 14))
    stavka(T("Izvoz podataka (Excel / CSV)", "Export data (Excel / CSV)"),
           T("Grla, rodovnik u 3 kolena, istorija i podsetnici u Excel ili CSV fajl. Za udruženje odgajivača, laboratoriju, veterinara ili drugi program.",
             "Animals, 3-generation pedigree, history and reminders to an Excel or CSV file. For a breed association, laboratory, vet or another program."),
           T("⇩ Izvezi", "⇩ Export"), self.izvezi)


class StampaDeo:
    """Štampa, PDF i statistika kao delovi glavnog prozora."""
    izvestaj_lekova = _app_izvestaj_lekova
    izvestaj_rodjenja = _app_izvestaj_rodjenja
    izvestaj_parenja = _app_izvestaj_parenja
    stampaj_rodoslov = _app_stampaj_rodoslov
    stampaj_plan = _app_stampaj_plan
    stampaj_spisak = _app_stampaj_spisak
    s_statistika = _app_s_statistika
    s_stampa = _app_s_stampa
