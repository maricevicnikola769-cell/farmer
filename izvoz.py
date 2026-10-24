"""Izvoz podataka: Excel (.xlsx sa više listova) ili CSV za druge programe, udruženja i laboratorije.
Excel fajl se pravi bez dodatnih biblioteka (xlsx je zip sa XML fajlovima)."""
import csv
import os
import sys
import tkinter as tk
import zipfile
from datetime import date
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape

from osnova import EN
from jezik import T
from osnova import prevedi_vrednost
from podaci import (EN_IST, EN_KOL, EN_POD, IST_KOLONE, KOLONE, STATUS_EN, Podsetnici, _excel_datum, kolona, sada,
                    tabela_u_recnike)
from izgled import BAD, INK2, SURF


# =============================================================== Excel bez biblioteka

def _kol_slovo(n):
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _xml_tekst(v):
    t = "" if v is None else str(v)
    # XML ne dozvoljava kontrolne znakove (osim tab i novog reda)
    t = "".join(c for c in t if c in "\t\n\r" or ord(c) >= 32)
    return escape(t)


def _list_xml(redovi, sirine):
    """Jedan list: prvi red je zaglavlje (podebljano, zamrznuto, sa filterom)."""
    br_kol = max((len(r) for r in redovi), default=1)
    kols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(sirine))
    xr = []
    for ri, red in enumerate(redovi, 1):
        celije = []
        for ci, v in enumerate(red):
            ref = f"{_kol_slovo(ci)}{ri}"
            stil = ' s="1"' if ri == 1 else ""
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                celije.append(f'<c r="{ref}"{stil}><v>{v}</v></c>')
            elif v not in (None, ""):
                celije.append(f'<c r="{ref}" t="inlineStr"{stil}><is><t xml:space="preserve">{_xml_tekst(v)}</t></is></c>')
        xr.append(f'<row r="{ri}">{"".join(celije)}</row>')
    poslednja = f"{_kol_slovo(br_kol - 1)}{max(1, len(redovi))}"
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>'
            f'<cols>{kols}</cols><sheetData>{"".join(xr)}</sheetData>'
            f'<autoFilter ref="A1:{poslednja}"/></worksheet>') if kols else (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(xr)}</sheetData></worksheet>')


def sacuvaj_xlsx(putanja, listovi):
    """listovi = [(naziv, [zaglavlje, red, red...]), ...] -> .xlsx koji otvara Excel, LibreOffice i Google tabele."""
    imena = []
    for naziv, _ in listovi:   # naziv lista: najviše 31 znak, bez []:*?/\
        n = "".join(c for c in str(naziv) if c not in "[]:*?/\\")[:31] or "List"
        while n in imena:
            n = n[:28] + f"_{len(imena)}"
        imena.append(n)
    tmp = putanja + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                             'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(len(listovi)))
                   + '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(imena))
                   + '</sheets>'
                   + ("<definedNames>" + "".join(
                       f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i}" hidden="1">'
                       f"'{escape(n)}'!$A$1:${_kol_slovo(max(1, max((len(r) for r in listovi[i][1]), default=1)) - 1)}"
                       f"${max(1, len(listovi[i][1]))}</definedName>"
                       for i, n in enumerate(imena) if listovi[i][1]) + "</definedNames>"
                      if any(r for _, r in listovi) else "")
                   + '</workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                             f'Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(listovi)))
                   + f'<Relationship Id="rId{len(listovi) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   '</Relationships>')
        z.writestr("xl/styles.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
                   '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>'
                   '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
                   '<fill><patternFill patternType="solid"><fgColor rgb="FF2E5E45"/><bgColor indexed="64"/></patternFill></fill></fills>'
                   '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                   '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                   '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                   '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>'
                   '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                   '</styleSheet>')
        for i, (_, redovi) in enumerate(listovi):
            sirine = []
            for red in redovi[:500]:          # širina kolone po najdužem tekstu (prvih 500 redova je dovoljno)
                for ci, v in enumerate(red):
                    d = min(60, max(6, len(str(v if v is not None else "")) + 2))
                    if ci >= len(sirine):
                        sirine.append(d)
                    else:
                        sirine[ci] = max(sirine[ci], d)
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", _list_xml(redovi, sirine))
    os.replace(tmp, putanja)


def sacuvaj_csv(putanja, redovi):
    """CSV sa ; i UTF-8 BOM – Excel ga otvara sa ispravnim slovima (č, ć, ž, š, đ)."""
    tmp = putanja + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        for r in redovi:
            w.writerow(["" if v is None else v for v in r])
    os.replace(tmp, putanja)


# =============================================================== šta se izvozi

POL_SR = {"m": "m", "z": "ž"}
POL_EN = {"m": "m", "z": "f"}


def _naziv_kol(k, mapa):
    return mapa.get(k, k) if EN else k


def tabele_za_izvoz(redovi_tablice, model, istorija=None, podsetnici=None, samo_zapat=False,
                    sa_rodovnikom=True, sa_istorijom=True, sa_podsetnicima=True, dodatne=(), samo_ids=None):
    """Vraća [(naziv lista, [zaglavlje, redovi...])]. Ne zavisi od prozora, pa se može testirati."""
    ukljuceno = []
    for r in redovi_tablice:
        st = r.get("status", "aktivno") or "aktivno"
        if samo_ids is not None:                 # samo označena grla (bez obzira da li su u zapatu)
            if (model.nadji(r["id"]) or r["id"]) not in samo_ids:
                continue
        elif st == "obrisano" or (samo_zapat and st != "aktivno"):
            continue
        ukljuceno.append(r)
    ids = {r["id"] for r in ukljuceno}

    kol = list(KOLONE) + [k for k in dodatne if k not in KOLONE]
    zag = [_naziv_kol(k, EN_KOL) for k in kol] + [T("inbriding_%", "inbreeding_%")]
    grla = [zag]
    for r in ukljuceno:
        vr = dict(r)
        vr["pol"] = (POL_EN if EN else POL_SR).get(vr.get("pol", ""), vr.get("pol", ""))
        if EN:
            vr["status"] = STATUS_EN.get(vr.get("status", ""), vr.get("status", ""))
        jid = model.nadji(r["id"]) or r["id"]
        f = model.inbr(jid) if jid in model.A else 0.0
        grla.append([vr.get(k, "") for k in kol] + [round(f * 100, 2)])
    listovi = [(T("Grla", "Animals"), grla)]

    if sa_rodovnikom:
        nazivi = T(["oznaka", "markica", "otac", "majka",
                    "otac_oca", "majka_oca", "otac_majke", "majka_majke",
                    "otac_oca_oca", "majka_oca_oca", "otac_majke_oca", "majka_majke_oca",
                    "otac_oca_majke", "majka_oca_majke", "otac_majke_majke", "majka_majke_majke"],
                   ["id", "ear_tag", "sire", "dam",
                    "sire_of_sire", "dam_of_sire", "sire_of_dam", "dam_of_dam",
                    "sss", "dss", "sds", "dds", "ssd", "dsd", "sdd", "ddd"])
        rod = [nazivi]
        for r in ukljuceno:
            jid = model.nadji(r["id"]) or r["id"]
            nivo, red = [jid], []
            for _ in range(3):                   # 3 kolena: roditelji, dedovi/babe, pradedovi/prababe
                sled = []
                for x in nivo:
                    o, m = model.P.get(x, (None, None)) if x else (None, None)
                    sled += [o, m]
                red += sled
                nivo = sled
            def ozn(x):
                if not x:
                    return ""
                a = model.A.get(x) or {}
                return x + (f" ({a['markica']})" if a.get("markica") else "")
            rod.append([r["id"], r.get("markica", "")] + [ozn(x) for x in red])
        listovi.append((T("Rodovnik", "Pedigree"), rod))

    if sa_istorijom and istorija is not None:
        ist = [[_naziv_kol(k, EN_IST) for k in IST_KOLONE]]
        for z in istorija.zapisi:
            if z.get("grlo") in ids:
                ist.append([z.get(k, "") for k in IST_KOLONE])
        listovi.append((T("Istorija", "History"), ist))

    if sa_podsetnicima and podsetnici is not None:
        kp = Podsetnici.KOLONE
        pod = [[_naziv_kol(k, EN_POD) for k in kp]]
        for z in podsetnici.zapisi:
            if not z.get("grlo") or z.get("grlo") in ids:
                pod.append([z.get(k, "") for k in kp])
        listovi.append((T("Podsetnici", "Reminders"), pod))
    return listovi


def izvezi_u_fajl(putanja, listovi, format_):
    """Excel: jedan fajl sa listovima. CSV: glavni fajl (grla) + po jedan fajl za ostale listove."""
    if format_ == "xlsx":
        sacuvaj_xlsx(putanja, listovi)
        return [putanja]
    osnova, _ = os.path.splitext(putanja)
    fajlovi = []
    for i, (naziv, redovi) in enumerate(listovi):
        p = putanja if i == 0 else f"{osnova}_{naziv.lower()}.csv"
        sacuvaj_csv(p, redovi)
        fajlovi.append(p)
    return fajlovi


# =============================================================== uvoz Farmerovog Excel izvoza (drugi listovi)

def _ozn_markica(t):
    """'K12 (RS 1234)' -> ('K12', 'RS 1234')."""
    t = (t or "").strip()
    if t.endswith(")") and " (" in t:
        i = t.rindex(" (")
        return t[:i].strip(), t[i + 2:-1].strip()
    return t, ""


def _datum_txt(v):
    v = (v or "").strip()
    return _excel_datum(v) if v.replace(".", "", 1).isdigit() and 1000 < float(v) < 80000 else v


def dopuni_iz_excela(listovi, redovi_tablice, istorija, podsetnici, ime_fajla=""):
    """Posle uvoza grla iz Farmerovog Excel fajla: preci iz lista Rodovnik, istorija i podsetnici.
    Postojeći podaci se ne menjaju (samo se popunjava ono što nedostaje), a isti zapis se ne dodaje dvaput.
    Vraća (novih predaka, novih zapisa istorije, novih podsetnika)."""
    po_id = {r["id"]: r for r in redovi_tablice}
    vrsta_za = {}
    n_pr = n_ist = n_pod = 0
    for naziv, sirovo in listovi[1:]:
        if not sirovo:
            continue
        zagl = [kolona(k) for k in sirovo[0]]
        if "otac_oca" in zagl or "sire_of_sire" in zagl:                     # ---- rodovnik
            for red in sirovo[1:]:
                red = list(red) + [""] * (16 - len(red))
                grlo = (red[0] or "").strip()
                if not grlo:
                    continue
                cvorovi = [grlo] + [_ozn_markica(x) for x in red[2:16]]
                ids = [grlo] + [c[0] for c in cvorovi[1:]]
                vrsta = (po_id.get(grlo) or {}).get("vrsta", "")
                # položaj i: roditelji su na 2i+1 (otac) i 2i+2 (majka) – kao u listu Rodovnik
                for i in range(len(ids)):
                    x = ids[i]
                    if not x:
                        continue
                    if i > 0 and x not in po_id:
                        mark = cvorovi[i][1]
                        po_id[x] = dict({k: "" for k in KOLONE}, id=x, markica=mark, vrsta=vrsta,
                                        pol="m" if i % 2 == 1 else "z", status="neaktivno", uneto=sada(),
                                        poreklo_od=os.path.basename(ime_fajla))
                        redovi_tablice.append(po_id[x])
                        n_pr += 1
                    r = po_id.get(x)
                    for j, kljuc in ((2 * i + 1, "otac"), (2 * i + 2, "majka")):
                        if r is not None and j < len(ids) and ids[j] and not r.get(kljuc):
                            r[kljuc] = ids[j]
        elif ("dogadjaj" in zagl or "event" in zagl) and istorija is not None:  # ---- istorija
            zapisi, _ = tabela_u_recnike(sirovo, EN_IST)
            postoji = {(z["grlo"], z["datum"], z["dogadjaj"], z["opis"], z["uneto"]) for z in istorija.zapisi}
            for z in zapisi:
                z = {k: z.get(k, "") for k in IST_KOLONE}
                if not z["grlo"]:
                    continue
                z["datum"] = _datum_txt(z["datum"])
                for k in ("dogadjaj", "ishod", "ter"):
                    if z[k]:
                        z[k] = prevedi_vrednost(z[k])
                kljuc = (z["grlo"], z["datum"], z["dogadjaj"], z["opis"], z["uneto"])
                if kljuc in postoji:
                    continue
                postoji.add(kljuc)
                istorija.zapisi.append(z)
                n_ist += 1
        elif ("tekst" in zagl or "text" in zagl) and podsetnici is not None:   # ---- podsetnici
            zapisi, _ = tabela_u_recnike(sirovo, EN_POD)
            postoji = {(z["grlo"], z["datum"], z["tip"], z["tekst"]) for z in podsetnici.zapisi}
            for z in zapisi:
                z = {k: z.get(k, "") for k in Podsetnici.KOLONE}
                z["datum"] = _datum_txt(z["datum"])
                if z["tip"]:
                    z["tip"] = prevedi_vrednost(z["tip"])
                kljuc = (z["grlo"], z["datum"], z["tip"], z["tekst"])
                if not z["datum"] or kljuc in postoji:
                    continue
                postoji.add(kljuc)
                podsetnici.zapisi.append(z)
                n_pod += 1
    return n_pr, n_ist, n_pod


# =============================================================== prozor

class IzvozDeo:
    """Dugme 'Izvezi' na strani Grla i u Štampi: izbor formata i sadržaja, pa čuvanje fajla."""

    def izvezi(self, parent=None, oznacena=None):
        if oznacena is None:                     # dugme "Izvezi": grla označena u listi, ako ih ima
            tv = getattr(self, "tv_grla", None)
            try:
                oznacena = [i for i in tv.selection() if i in self.model.A] if tv is not None and tv.winfo_exists() else []
            except tk.TclError:
                oznacena = []
        if not self.tab.redovi:
            messagebox.showinfo("Farmer", T("U evidenciji još nema grla za izvoz.", "There are no animals to export yet."))
            return
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(T("Izvoz podataka", "Export data"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, T("Izvoz podataka", "Export data"), 16, "bold").pack(anchor="w")
        self.lbl(b, T("Za računovođu, veterinara, udruženje odgajivača, laboratoriju ili drugi program.",
                      "For your accountant, vet, breed association, laboratory or another program."),
                 9, fg=INK2, wraplength=430, justify="left").pack(anchor="w", pady=(2, 0))

        self.lbl(b, T("Format", "Format"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 2))
        fv = tk.StringVar(value="xlsx")
        ttk.Radiobutton(b, text=T("Excel (.xlsx) – sve u jednom fajlu, na posebnim listovima",
                                  "Excel (.xlsx) – everything in one file, on separate sheets"),
                        value="xlsx", variable=fv, style="Card.TRadiobutton").pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(b, text=T("CSV – za druge programe (poseban fajl za svaki deo)",
                                  "CSV – for other programs (a separate file for each part)"),
                        value="csv", variable=fv, style="Card.TRadiobutton").pack(anchor="w", pady=(4, 0))

        self.lbl(b, T("Grla", "Animals"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 2))
        gv = tk.StringVar(value="oznacena" if oznacena else "zapat")
        if oznacena:
            prikaz = ", ".join(oznacena[:5]) + (T(f" i još {len(oznacena) - 5}", f" and {len(oznacena) - 5} more") if len(oznacena) > 5 else "")
            ttk.Radiobutton(b, text=T(f"Samo označena grla ({len(oznacena)}): {prikaz}", f"Only selected animals ({len(oznacena)}): {prikaz}"),
                            value="oznacena", variable=gv, style="Card.TRadiobutton").pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(b, text=T("Samo grla u zapatu", "Only animals in the herd"), value="zapat", variable=gv,
                        style="Card.TRadiobutton").pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(b, text=T("Sva upisana grla (i prodata, uginula…)", "All recorded animals (also sold, dead…)"),
                        value="sva", variable=gv, style="Card.TRadiobutton").pack(anchor="w", pady=(4, 0))

        self.lbl(b, T("Uključi", "Include"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 2))
        rv, iv, pv = tk.BooleanVar(value=True), tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        for tekst, var in ((T("Rodovnik u 3 kolena (roditelji, dedovi, pradedovi)",
                              "3-generation pedigree (parents, grandparents, great-grandparents)"), rv),
                           (T("Istorija događaja (parenja, porođaji, lečenja…)",
                              "Event history (matings, births, treatments…)"), iv),
                           (T("Podsetnici", "Reminders"), pv)):
            ttk.Checkbutton(b, text=tekst, variable=var, style="Card.TCheckbutton").pack(anchor="w", pady=(4, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def izvezi_sad(ev=None):
            fmt = fv.get()
            ime = T("farmer_izvoz", "farmer_export") + "_" + date.today().strftime("%Y-%m-%d") + "." + fmt
            put = filedialog.asksaveasfilename(
                parent=win, title=T("Sačuvaj izvoz", "Save export"), initialfile=ime, defaultextension="." + fmt,
                filetypes=[(T("Excel tabela", "Excel workbook"), "*.xlsx")] if fmt == "xlsx"
                else [(T("CSV tablica", "CSV table"), "*.csv")])
            if not put:
                return
            try:
                listovi = tabele_za_izvoz(self.tab.redovi, self.model, self.ist, self.pods,
                                          samo_zapat=gv.get() == "zapat", sa_rodovnikom=rv.get(),
                                          sa_istorijom=iv.get(), sa_podsetnicima=pv.get(),
                                          dodatne=getattr(self.tab, "dodatne", ()),
                                          samo_ids=set(oznacena) if gv.get() == "oznacena" else None)
                fajlovi = izvezi_u_fajl(put, listovi, fmt)
            except OSError as e:
                err.config(text=T("Fajl nije sačuvan: ", "The file was not saved: ") + str(e)
                           + T("\nAko je otvoren u Excelu, zatvori ga i pokušaj ponovo.",
                               "\nIf it is open in Excel, close it and try again."))
                return
            win.grab_release()
            win.destroy()
            n = len(listovi[0][1]) - 1
            self.toast(T(f"Izvezeno {n} grla u {os.path.basename(fajlovi[0])}", f"Exported {n} animals to {os.path.basename(fajlovi[0])}")
                       + (T(f" (+{len(fajlovi) - 1} fajla)", f" (+{len(fajlovi) - 1} files)") if len(fajlovi) > 1 else ""))
            if messagebox.askyesno("Farmer", T("Izvoz je gotov. Da otvorim folder sa fajlom?",
                                               "Export finished. Open the folder with the file?")):
                folder = os.path.dirname(fajlovi[0])
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(folder)
                    elif sys.platform == "darwin":
                        os.system(f'open "{folder}"')
                    else:
                        os.system(f'xdg-open "{folder}" &')
                except OSError:
                    pass

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, T("Izvezi…", "Export…"), izvezi_sad, "Primary").pack(side="right")
        self.btn(fb, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", izvezi_sad)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
