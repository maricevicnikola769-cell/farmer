"""DNK test: provera porekla (otac i majka), genomska procena, genetske bolesti, A2 mleko… i nalaz iz laboratorije (PDF/slika).
Čuva se u istoriji grla kao događaj „DNK test“: vrednost = vrsta testa, opis = rezultat, lab, uzorak, fajl = priloženi nalaz."""
import os
import queue
import shutil
import threading
import sys
import tkinter as tk
from datetime import date
from tkinter import filedialog, ttk

import jezik
from jezik import T
from osnova import _srpski_kljuc, prevedi_vrednost
from podaci import parsiraj_datum
from izgled import BAD, BRAND, INK, INK2, OK, SURF, SURF2, WARN
import citanje

FOLDER_NALAZA = "dnk_nalazi"
# rezultat provere porekla (srpski ključ) -> (otac u redu, majka u redu); None = nije testirano
_POREKLO = {"Otac i majka potvrđeni": (True, True), "Otac potvrđen (majka nije testirana)": (True, None),
            "Otac isključen": (False, None), "Majka isključena": (None, False), "Otac i majka isključeni": (False, False)}


def dnk_zapisi(istorija, x):
    """DNK testovi grla, najnoviji prvi."""
    z = [z for z in istorija.zapisi if z["grlo"] == x and _srpski_kljuc(z["dogadjaj"]) == "DNK test"]
    return sorted(z, key=lambda z: (parsiraj_datum(z["datum"]) or date.min, z.get("uneto", "")), reverse=True)


def provera_porekla(istorija, x):
    """Poslednja provera porekla: (otac_ok, majka_ok, zapis) ili None. otac_ok/majka_ok: True, False ili None (nije testirano)."""
    for z in dnk_zapisi(istorija, x):
        if _srpski_kljuc(z.get("vrednost", "")) == "Provera porekla (otac i majka)":
            o, m = _POREKLO.get(_srpski_kljuc(z.get("opis", "")) or "", (None, None))
            return o, m, z
    return None


def je_slika(ime):
    return str(ime).lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"))


def sacuvaj_slike_sa_telefona(putanja_tablice, slike):
    """Slike DNK nalaza poslate sa telefona ({ime fajla: 'data:image/jpeg;base64,...'}) -> folder dnk_nalazi.
    Postojeći fajl se ne menja. Vraća broj sačuvanih."""
    import base64
    import re
    if not isinstance(slike, dict) or not slike:
        return 0
    fold = folder_nalaza(putanja_tablice)
    n = 0
    for ime, data in slike.items():
        ime = os.path.basename(str(ime))
        if not re.fullmatch(r"[\w.\- ]{1,150}", ime, re.U) or not isinstance(data, str) or "," not in data:
            continue
        put = os.path.join(fold, ime)
        if os.path.exists(put):
            continue
        try:
            sadrzaj = base64.b64decode(data.split(",", 1)[1], validate=False)
            if len(sadrzaj) > 15 * 1024 * 1024:
                continue
            os.makedirs(fold, exist_ok=True)
            with open(put, "wb") as f:
                f.write(sadrzaj)
            n += 1
        except (ValueError, OSError):
            continue
    return n


def folder_nalaza(putanja_tablice):
    return os.path.join(os.path.dirname(os.path.abspath(putanja_tablice)), FOLDER_NALAZA)


def otvori_fajl(put):
    try:
        if sys.platform.startswith("win"):
            os.startfile(put)
        elif sys.platform == "darwin":
            os.system(f'open "{put}"')
        else:
            os.system(f'xdg-open "{put}" &')
    except OSError:
        pass


class DnkDeo:
    """Upis DNK testa i prikaz na kartonu grla."""

    def dnk_forma(self, x, zapis=None, posle=None, parent=None):
        m = self.model
        a = m.A.get(x)
        if not a:
            return
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(T(f"DNK test – {x}", f"DNA test – {x}"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, "🧬 " + T("DNK test", "DNA test") + f" – {x}", 16, "bold").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        z = zapis or {}
        v = {k: tk.StringVar(value=prevedi_vrednost(z.get(k, "")) if k in ("vrednost", "opis", "uzorak") else z.get(k, ""))
             for k in ("datum", "vrednost", "opis", "lab", "uzorak", "fajl")}
        if not z:
            v["datum"].set(date.today().strftime("%d/%m/%Y" if jezik.EN else "%d.%m.%Y"))
            v["vrednost"].set(jezik.DNK_TESTOVI[0])

        def polje(r, c, naslov, var, vals=None, w=26, hint=""):
            f = tk.Frame(b, bg=SURF)
            f.grid(row=r, column=c, sticky="new", padx=(0 if c == 0 else 14, 0), pady=6)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            wd = ttk.Combobox(f, textvariable=var, values=vals, width=w, font=self.f(10)) if vals is not None \
                else ttk.Entry(f, textvariable=var, width=w + 2, font=self.f(10))
            wd.pack(fill="x", pady=(4, 0))
            if hint:
                self.lbl(f, hint, 8, fg="#8A968D", wraplength=260, justify="left").pack(anchor="w")
            return wd
        polje(1, 0, T("Datum uzorkovanja *", "Sampling date *"), v["datum"])
        polje(1, 1, T("Vrsta testa *", "Test type *"), v["vrednost"], jezik.DNK_TESTOVI)
        polje(2, 0, T("Laboratorija", "Laboratory"), v["lab"],
              sorted({z_.get("lab", "") for z_ in self.ist.zapisi if z_.get("lab")}))
        polje(2, 1, T("Uzorak", "Sample"), v["uzorak"], jezik.DNK_UZORCI)
        o, mj = m.P.get(x, (None, None))
        cb_rez = polje(3, 0, T("Rezultat *", "Result *"), v["opis"], [], w=50,
                       hint=T(f"Upisani roditelji: otac {o or '?'}, majka {mj or '?'}", f"Recorded parents: sire {o or '?'}, dam {mj or '?'}"))
        cb_rez.master.grid(columnspan=2)

        def tip_testa(*_):          # provera porekla: gotovi rezultati; ostali testovi: slobodan tekst
            cb_rez.configure(values=jezik.DNK_POREKLO if v["vrednost"].get() == jezik.DNK_PROVERA else [])
        v["vrednost"].trace_add("write", tip_testa)
        tip_testa()
        # tekst izveštaja (nalepi iz mejla/PDF-a) i priloženi nalazi (PDF, slike)
        tf = tk.Frame(b, bg=SURF)
        tf.grid(row=4, column=0, columnspan=2, sticky="we", pady=(8, 0))
        self.lbl(tf, T("Tekst izveštaja", "Report text"), 9, "bold", fg=INK2).pack(anchor="w")
        tekst = tk.Text(tf, height=6, width=54, font=self.f(10), wrap="word", relief="solid", bd=1, highlightthickness=0)
        tekst.pack(fill="x", pady=(4, 0))
        tekst.insert("1.0", z.get("izvestaj", ""))
        self.lbl(tf, T("nalepi tekst iz mejla (Ctrl+V) ili priloži nalaz pa „Prepiši tekst iz nalaza“",
                       "paste the text from the e-mail (Ctrl+V) or attach the report and use “Copy text from the report”"), 8, fg="#8A968D").pack(anchor="w")
        stanje = self.lbl(tf, "", 9, "bold", fg=WARN, wraplength=480, justify="left")
        stanje.pack(anchor="w")
        procitano = {"slika": False, "iz": False}
        fajlovi = [f for f in str(z.get("fajl", "")).split("|") if f]
        ff = tk.Frame(b, bg=SURF)
        ff.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.lbl(ff, T("Slike i nalazi iz laboratorije (PDF, slika)", "Pictures and lab reports (PDF, picture)"), 9, "bold", fg=INK2).pack(anchor="w")
        spisak = tk.Frame(ff, bg=SURF)
        spisak.pack(anchor="w", fill="x", pady=(4, 0))
        fold = folder_nalaza(self.tab.putanja)

        def prikazi_fajlove():
            for w in spisak.winfo_children():
                w.destroy()
            if not fajlovi:
                self.lbl(spisak, T("nije priložen", "not attached"), 10, fg=INK2).pack(anchor="w")
            for ime in fajlovi:
                r = tk.Frame(spisak, bg=SURF)
                r.pack(anchor="w")
                put = os.path.join(fold, ime)
                lk_ = self.lbl(r, ("🖼 " if je_slika(ime) else "📎 ") + ime, 10, fg=BRAND if os.path.isfile(put) else INK2, cursor="hand2")
                lk_.pack(side="left")
                lk_.bind("<Button-1>", lambda e, put=put: otvori_fajl(put) if os.path.isfile(put) else None)
                x_ = self.lbl(r, "✕", 10, "bold", fg=BAD, cursor="hand2")
                x_.pack(side="left", padx=10)
                x_.bind("<Button-1>", lambda e, ime=ime: (fajlovi.remove(ime), prikazi_fajlove()))
        prikazi_fajlove()

        def prilozi():
            pp = filedialog.askopenfilenames(parent=win, title=T("Izaberi nalaz", "Choose the report"),
                                             filetypes=[(T("PDF ili slika", "PDF or picture"), "*.pdf *.jpg *.jpeg *.png *.heic *.webp"),
                                                        (T("Svi fajlovi", "All files"), "*.*")])
            if not pp:
                return
            os.makedirs(fold, exist_ok=True)
            for p in (pp if isinstance(pp, (list, tuple)) else [pp]):
                ime = f"{x}_{(parsiraj_datum(v['datum'].get()) or date.today()).strftime('%Y-%m-%d')}_{os.path.basename(p)}"
                ime = "".join(c if c.isalnum() or c in "._- " else "_" for c in ime)
                try:
                    shutil.copy2(p, os.path.join(fold, ime))
                except OSError as e:
                    err.config(text=str(e))
                    return
                if ime not in fajlovi:
                    fajlovi.append(ime)
            prikazi_fajlove()
            if not tekst.get("1.0", "end").strip():      # prazan tekst izveštaja: odmah ga prepiši iz nalaza
                prepisi()

        def prepisi():
            puti = [os.path.join(fold, i) for i in fajlovi
                    if os.path.isfile(os.path.join(fold, i)) and (citanje.je_pdf(i) or citanje.je_slika(i))]
            if not puti:
                stanje.config(text=T("Prvo priloži PDF nalaz ili sliku nalaza.", "Attach the PDF report or a picture of it first."), fg=BAD)
                return
            stanje.config(text=T("Čitam tekst iz nalaza…", "Reading the text from the report…"), fg=INK2)
            dug_prep.configure(state="disabled")
            red = queue.Queue()

            def posao():
                rez = []
                for p in puti:
                    try:
                        rez.append((p,) + citanje.procitaj(p, jezik.JEZIK))
                    except citanje.GreskaCitanja as e:
                        rez.append((p, None, str(e)))
                red.put(rez)
            threading.Thread(target=posao, daemon=True).start()

            def cekaj():
                try:
                    rez = red.get_nowait()
                except queue.Empty:
                    if win.winfo_exists():
                        win.after(200, cekaj)
                    return
                if not win.winfo_exists():
                    return
                dug_prep.configure(state="normal")
                delovi, sa_slike, greske = [], False, []
                for p, txt, tacno in rez:
                    if txt is None:
                        greske.append(tacno)
                    elif txt.strip():
                        delovi.append(txt.strip())
                        sa_slike = sa_slike or not tacno
                    else:
                        greske.append("prazno")
                if delovi:
                    staro = tekst.get("1.0", "end").strip()
                    novo = "\n\n".join(delovi)
                    if novo not in staro:
                        tekst.insert("end", ("\n\n" if staro else "") + novo)
                    procitano["slika"] = procitano["slika"] or sa_slike
                    procitano["iz"] = True
                    stanje.config(fg=WARN if sa_slike else OK, text=
                        T("⚠ Tekst je prepoznat sa slike. Program može da pogreši slovo ili broj – proveri tekst i rezultat pre čuvanja.",
                          "⚠ The text was recognised from a picture. The program can misread a letter or a number – check the text and the result before saving.")
                        if sa_slike else T("✓ Tekst je prepisan iz PDF-a tačno kako piše u nalazu. Upiši rezultat.",
                                           "✓ The text was copied from the PDF exactly as it is in the report. Enter the result."))
                    return
                g = greske[0] if greske else "prazno"
                stanje.config(fg=BAD, text={
                    "nema-ocr": T("Na ovom računaru tekst sa slike ne može da se pročita (potreban je Windows 10 ili 11). Upiši ga ručno.",
                                  "Text from a picture cannot be read on this computer (Windows 10 or 11 is needed). Type it in."),
                    "nema-jezika": T("U Windows-u nije instaliran jezik za prepoznavanje teksta (Podešavanja → Vreme i jezik → Jezik). Upiši tekst ručno.",
                                     "No text-recognition language is installed in Windows (Settings → Time & language → Language). Type the text in."),
                }.get(g, T("Tekst iz nalaza nije mogao da se pročita (slika je možda mutna). Upiši ga ručno.",
                           "The text could not be read from the report (the picture may be blurry). Type it in.")))
            cekaj()
        dr = tk.Frame(ff, bg=SURF)
        dr.pack(anchor="w", pady=(6, 0))
        self.btn(dr, T("📎 Priloži sliku ili nalaz…", "📎 Attach picture or report…"), prilozi).pack(side="left")
        dug_prep = self.btn(dr, T("🔎 Prepiši tekst iz nalaza", "🔎 Copy text from the report"), prepisi)
        dug_prep.pack(side="left", padx=(8, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def sacuvaj():
            d = parsiraj_datum(v["datum"].get())
            if not d:
                err.config(text=T("Datum nije ispravan.", "The date is not valid."))
                return
            if not v["opis"].get().strip() and procitano["iz"]:
                err.config(text=T("Upiši rezultat – pogledaj ga u tekstu nalaza.", "Enter the result – find it in the report text."))
                return
            if not v["opis"].get().strip() and tekst.get("1.0", "end").strip():   # samo tekst izveštaja: rezultat = prvi red
                v["opis"].set(tekst.get("1.0", "end").strip().splitlines()[0][:120])
            if not v["vrednost"].get().strip() or not v["opis"].get().strip():
                err.config(text=T("Upiši vrstu testa i rezultat.", "Enter the test type and the result."))
                return
            nov = dict(datum=d.strftime("%d/%m/%Y" if jezik.EN else "%d.%m.%Y"), vrednost=" ".join(v["vrednost"].get().split()),
                       opis=" ".join(v["opis"].get().split()), lab=" ".join(v["lab"].get().split()),
                       uzorak=" ".join(v["uzorak"].get().split()), fajl="|".join(fajlovi),
                       izvestaj=tekst.get("1.0", "end").strip())
            if zapis:
                zapis.update(nov)
                poruka = T(f"DNK test izmenjen – {x}", f"DNA test changed – {x}")
            else:
                z_ = self.ist.dodaj(x, jezik.DNK, nov["opis"], datum=nov["datum"], vrednost=nov["vrednost"])
                z_.update(lab=nov["lab"], uzorak=nov["uzorak"], fajl=nov["fajl"], izvestaj=nov["izvestaj"])
                poruka = T(f"Upisan DNK test – {x}", f"DNA test recorded – {x}")
            win.grab_release()
            win.destroy()
            self.promena(poruka)
            if posle:
                posle()
            elif self.karton_win and self.karton_win.winfo_exists() and getattr(self.karton_win, "grlo", None) == x:
                self.karton(x)
        fb = tk.Frame(win, bg=SURF)
        fb.pack(fill="x", padx=26, pady=(0, 20))
        self.btn(fb, T("Sačuvaj", "Save"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        self.postavi_prozor(win, parent)

    def dnk_na_kartonu(self, parent, x):
        """DNK testovi na kartonu: provera porekla (zeleno potvrđeno / crveno isključeno) i ostali testovi."""
        zap = dnk_zapisi(self.ist, x)
        nas = tk.Frame(parent, bg=SURF)
        nas.pack(anchor="w", fill="x", pady=(18, 6))
        self.lbl(nas, "🧬 " + T("DNK testovi", "DNA tests"), 10, "bold").pack(side="left")
        lk = self.lbl(nas, T("+ dodaj", "+ add"), 9, "bold", fg=BRAND, cursor="hand2")
        lk.pack(side="left", padx=10)
        lk.bind("<Button-1>", lambda e: self.dnk_forma(x, parent=self.karton_win))
        if not zap:
            self.lbl(parent, T("nema upisanih", "none recorded"), 9, fg=INK2).pack(anchor="w")
            return
        pp = provera_porekla(self.ist, x)
        if pp:
            o_ok, m_ok, _ = pp
            o, mj = self.model.P.get(x, (None, None))
            delovi = []
            if o_ok is not None:
                delovi.append((T(f"otac {o or '?'} potvrđen", f"sire {o or '?'} confirmed") if o_ok else T(f"otac {o or '?'} ISKLJUČEN", f"sire {o or '?'} EXCLUDED"), o_ok))
            if m_ok is not None:
                delovi.append((T(f"majka {mj or '?'} potvrđena", f"dam {mj or '?'} confirmed") if m_ok else T(f"majka {mj or '?'} ISKLJUČENA", f"dam {mj or '?'} EXCLUDED"), m_ok))
            for txt, ok in delovi:
                self.lbl(parent, ("✓ " if ok else "⚠ ") + T("Poreklo po DNK: ", "Parentage by DNA: ") + txt, 10, "bold",
                         fg=OK if ok else BAD).pack(anchor="w", pady=1)
        tb = tk.Frame(parent, bg=SURF2)
        tb.pack(anchor="w", fill="x", pady=(6, 0))
        fold = folder_nalaza(self.tab.putanja)
        for i, z in enumerate(zap[:8]):
            r = tk.Frame(tb, bg=SURF2)
            r.pack(fill="x", padx=10, pady=(6 if i == 0 else 2, 2))
            self.lbl(r, z["datum"], 9, fg=INK2, bg=SURF2).pack(side="left")
            t = self.lbl(r, prevedi_vrednost(z.get("vrednost", "")) + ": " + prevedi_vrednost(z.get("opis", "")), 9, "bold",
                         bg=SURF2, wraplength=260, justify="left", cursor="hand2")
            t.pack(side="left", padx=(10, 0))
            t.bind("<Button-1>", lambda e, z=z: self.dnk_forma(x, zapis=z, parent=self.karton_win))
            for ime in [f for f in str(z.get("fajl", "")).split("|") if f][::-1]:
                put = os.path.join(fold, ime)
                pf = self.lbl(r, "🖼" if je_slika(ime) else "📎", 10, fg=BRAND if os.path.isfile(put) else INK2, bg=SURF2, cursor="hand2")
                pf.pack(side="right", padx=(4, 0))
                pf.bind("<Button-1>", lambda e, put=put: otvori_fajl(put) if os.path.isfile(put) else None)
                self.savet(pf, ime)
            detalji = " · ".join(v for v in (z.get("lab", ""), prevedi_vrednost(z.get("uzorak", ""))) if v)
            if detalji:
                self.lbl(tb, "      " + detalji, 8, fg=INK2, bg=SURF2).pack(anchor="w", padx=10)
            if z.get("izvestaj"):                      # početak teksta izveštaja; klik otvara ceo
                izv = " ".join(z["izvestaj"].split())
                li = self.lbl(tb, "      " + (izv[:160] + ("…" if len(izv) > 160 else "")), 8, fg=INK, bg=SURF2,
                              wraplength=380, justify="left", cursor="hand2")
                li.pack(anchor="w", padx=10)
                li.bind("<Button-1>", lambda e, z=z: self.dnk_forma(x, zapis=z, parent=self.karton_win))
        tk.Frame(tb, bg=SURF2, height=6).pack()
