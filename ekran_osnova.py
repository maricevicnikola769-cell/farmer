"""Glavni prozor: podešavanja, stil, meni levo, dugmad, tabele, menjanje strana i jezika."""
import json
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

from osnova import APP_DIR, EN, PODESAVANJA, _ime_stada
from jezik import AUTO, T, postavi_jezik
from podaci import Istorija, KOLONE, Podsetnici, Tablica, procitaj_csv, sada
from izgled import (BAD, BAD_BG, BG, BRAND, BRAND_H, INK, INK2, LINE, LOGO, OK, OK_BG, SURF, SURF2,
    ScrollFrame, TAG, TAG_INK, WARN, WARN_BG, ikonica_markice, izaberi_font, postavi_win_ikonicu)
from rodoslov import Model


def _app_promeni_jezik(self):
    """Promena jezika odmah, bez ponovnog pokretanja programa."""
    novi = "sr" if EN else "en"
    strana = self.strana if self.strana != "obrisana" else "grla"
    for w in (self.karton_win, getattr(self, "ist_win", None), getattr(self, "stablo_win", None)):
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
    for sacuvaj in (self.ist.sacuvaj, self.pods.sacuvaj):
        try:
            sacuvaj()
        except Exception:
            pass
    self.pod["jezik"] = novi
    self.sacuvaj_podesavanja()
    postavi_jezik(novi)
    # podaci se ponovo čitaju - nazivi događaja, vrsta i porekla se prevode na novi jezik
    try:
        self.tab = Tablica(self.tab.putanja)
    except Exception:
        pass
    self.model = Model(self.tab.redovi)
    self.ist = Istorija(self.tab.putanja)
    self.pods = Podsetnici(self.tab.putanja)
    self.ui.update(q="", pol="", poreklo="", partner="", partner_upit="", partner_vise=[], sA="", sB="")
    self.karton_win = None
    for w in self.root.winfo_children():
        w.destroy()
    self.shell()
    self.prikazi(strana)
    try:
        self.toast(T("Jezik: srpski", "Language: English"))
    except Exception:
        pass


class OsnovaProzora:
    """Glavni prozor: podešavanja, stil, meni levo, dugmad, tabele, menjanje strana i jezika."""

    def __init__(self, root):
        self.root = root
        self.pod = self.ucitaj_podesavanja()
        self.prag = self.pod.get("prag", 0.0625)
        self.F = izaberi_font()
        root.title("Farmer")
        self.logo = {}
        try:
            self.logo = {k: tk.PhotoImage(data=v) for k, v in LOGO.items()}
        except tk.TclError:
            pass
        # ikonica prozora: prvo .ico (za stare prozore), pa logo iz programa PREKO nje -
        # tako je u naslovnoj traci i na traci zadataka uvek novi logo
        ico = os.path.join(APP_DIR, "farmer.ico")
        if not os.path.exists(ico): ico = os.path.join(getattr(sys, "_MEIPASS", APP_DIR), "farmer.ico")
        if sys.platform.startswith("win") and os.path.isfile(ico):
            try:
                root.iconbitmap(default=ico)
            except tk.TclError:
                pass
        if self.logo:
            try:
                root.iconphoto(True, self.logo[64], self.logo[32], self.logo[16])
            except tk.TclError:
                pass
        # Windows: ikonica u naslovnoj traci se postavlja i direktno preko sistema (najpouzdanije)
        if sys.platform.startswith("win") and os.path.isfile(ico):
            root.after(150, lambda: postavi_win_ikonicu(root, ico))
        root.configure(bg=BG)
        root.geometry(self.pod.get("prozor", "1240x800"))
        root.minsize(980, 620)
        self.stilovi()
        self.img_tag = ikonica_markice(TAG)
        self.img_tag_siv = ikonica_markice("#B9C2BB")

        putanja = self.pod.get("tablica") or os.path.join(APP_DIR, _ime_stada())
        if not os.path.isdir(os.path.dirname(putanja) or "."):
            putanja = os.path.join(APP_DIR, _ime_stada())
        try:
            self.tab = Tablica(putanja)
        except Exception as e:
            messagebox.showerror(("The table cannot be loaded" if EN else "Tablica se ne može učitati"), str(e))
            novi = os.path.join(APP_DIR, _ime_stada())
            if putanja != novi and os.path.isfile(novi):
                try:
                    self.tab = Tablica(novi)
                except Exception:
                    self.tab = Tablica(os.path.join(APP_DIR, ("herd_new.csv" if EN else "stado_novo.csv")), ucitaj=False)
            else:
                self.tab = Tablica(os.path.join(APP_DIR, ("herd_new.csv" if EN else "stado_novo.csv") if putanja == novi else _ime_stada()),
                                   ucitaj=False)
        self.model = Model(self.tab.redovi)
        self.ist = Istorija(self.tab.putanja)
        self.pods = Podsetnici(self.tab.putanja)
        self.strana = "grla"
        self.ui = {"q": "", "pol": "", "poreklo": "", "samo_akt": True, "par_tab": "partner", "partner": "", "ista_rasa": False,
                   "plan_max": 0, "sA": "", "sB": ""}
        self.karton_win = None

        self.shell()
        self.prikazi("grla")
        root.after(700, self.obavestenja_na_startu)
        root.after(1500, self.dnevna_kopija)
        self.pokreni_sinhronizaciju()
        root.bind("<FocusIn>", self.proveri_promenu)
        root.protocol("WM_DELETE_WINDOW", self.zatvori)


    # ------------------------------------------------------------ podesavanja
    def ucitaj_podesavanja(self):
        try:
            with open(PODESAVANJA, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}


    def sacuvaj_podesavanja(self):
        self.pod.update(prag=self.prag, tablica=self.tab.putanja)
        try:
            with open(PODESAVANJA, "w", encoding="utf-8") as f:
                json.dump(self.pod, f, ensure_ascii=False, indent=1)
        except OSError:
            pass


    def zatvori(self):
        try:
            self.zatvori_kopija()
        except Exception:
            pass
        if self.root.state() == "normal":
            self.pod["prozor"] = self.root.geometry()
        self.sacuvaj_podesavanja()
        self.root.destroy()


    # ------------------------------------------------------------ stil
    def f(self, size=11, weight="normal"):
        return (self.F, size, weight)


    def stilovi(self):
        s = ttk.Style()
        s.theme_use("clam")
        F = self.F
        s.configure(".", background=BG, foreground=INK, font=(F, 10), bordercolor=LINE,
                    lightcolor=LINE, darkcolor=LINE, troughcolor=SURF2, focuscolor=BRAND)
        for name, bg, fg, hov, bd in (("Primary", BRAND, "#FFFFFF", BRAND_H, BRAND),
                                      ("Secondary", SURF, INK, SURF2, LINE),
                                      ("Danger", SURF, BAD, BAD_BG, SURF)):
            s.configure(f"{name}.TButton", background=bg, foreground=fg, font=(F, 10, "bold"),
                        padding=(16, 8), borderwidth=1, bordercolor=bd, lightcolor=bg, darkcolor=bg,
                        focusthickness=0, relief="solid")
            s.map(f"{name}.TButton", background=[("active", hov), ("disabled", SURF2)],
                  lightcolor=[("active", hov)], darkcolor=[("active", hov)],
                  foreground=[("disabled", INK2)])
        s.configure("TEntry", fieldbackground=SURF, padding=(10, 7), bordercolor=LINE,
                    lightcolor=SURF, darkcolor=SURF, insertcolor=INK)
        s.map("TEntry", bordercolor=[("focus", BRAND)], lightcolor=[("focus", BRAND)])
        s.configure("TCombobox", fieldbackground=SURF, background=SURF, padding=(10, 6), arrowsize=14,
                    bordercolor=LINE, lightcolor=SURF, darkcolor=SURF, arrowcolor=INK2)
        s.map("TCombobox", fieldbackground=[("readonly", SURF)], bordercolor=[("focus", BRAND)],
              selectbackground=[("readonly", SURF)], selectforeground=[("readonly", INK)])
        self.root.option_add("*TCombobox*Listbox.font", (F, 10))
        self.root.option_add("*TCombobox*Listbox.selectBackground", BRAND)
        s.configure("TCheckbutton", background=BG, font=(F, 10), indicatorcolor=SURF,
                    indicatorbackground=SURF)
        s.map("TCheckbutton", indicatorcolor=[("selected", BRAND)], background=[("active", BG)])
        s.configure("Card.TCheckbutton", background=SURF)
        s.map("Card.TCheckbutton", background=[("active", SURF)])
        s.configure("Card.TRadiobutton", background=SURF, font=(F, 10), indicatorcolor=SURF)
        s.map("Card.TRadiobutton", indicatorcolor=[("selected", BRAND)], background=[("active", SURF)])
        s.configure("Treeview", background=SURF, fieldbackground=SURF, foreground=INK, rowheight=36,
                    borderwidth=0, font=(F, 10))
        s.map("Treeview", background=[("selected", "#D5E6DA")], foreground=[("selected", INK)])
        s.configure("Treeview.Heading", background=SURF2, foreground=INK2, font=(F, 9, "bold"),
                    relief="flat", padding=(8, 8), borderwidth=0)
        s.map("Treeview.Heading", background=[("active", SURF2)])
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.configure("Green.Horizontal.TProgressbar", troughcolor=SURF2, background=BRAND, thickness=8,
                    borderwidth=0, lightcolor=BRAND, darkcolor=BRAND)
        s.configure("Vertical.TScrollbar", background=SURF2, troughcolor=BG, bordercolor=BG, arrowcolor=INK2,
                    lightcolor=SURF2, darkcolor=SURF2, gripcount=0)


    # ------------------------------------------------------------ okvir
    def shell(self):
        side = tk.Frame(self.root, bg=SURF, width=230, highlightthickness=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(self.root, bg=LINE, width=1).pack(side="left", fill="y")

        brand = tk.Frame(side, bg=SURF)
        brand.pack(fill="x", padx=14, pady=(22, 26))
        if self.logo.get(36):
            tk.Label(brand, image=self.logo[36], bg=SURF, bd=0).pack(side="left")
        else:
            c = tk.Canvas(brand, width=34, height=38, bg=SURF, highlightthickness=0)
            c.pack(side="left")
            self.crtaj_markicu(c, 2, 2, 30, 34)
        t = tk.Frame(brand, bg=SURF)
        t.pack(side="left", padx=10)
        tk.Label(t, text="Farmer", bg=SURF, fg=INK, font=self.f(12, "bold")).pack(anchor="w")
        tk.Label(t, text=("kinship & mating" if EN else "srodstvo i parenje"), bg=SURF, fg=INK2, font=self.f(9)).pack(anchor="w")

        self.nav = {}
        for key, txt, ic in (("grla", ("Animals" if EN else "Grla"), "☰"), ("parenje", ("Mating" if EN else "Parenje"), "⚭"),
                             ("srodstvo", ("Relationship" if EN else "Srodstvo"), "⑂"), ("istorija", ("History" if EN else "Istorija"), "◷"),
                             ("obavestenja", ("Notifications" if EN else "Obaveštenja"), "◉"), ("pregled", ("Overview" if EN else "Pregled"), "▥"),
                             ("statistika", T("Statistika", "Statistics"), "▤"), ("stampa", T("Štampa i PDF", "Print and PDF"), "⎙"),
                             ("telefon", T("Telefon", "Phone"), "☏")):
            row = tk.Frame(side, bg=SURF, cursor="hand2")
            row.pack(fill="x", padx=12, pady=1)
            li = tk.Label(row, text=ic, bg=SURF, fg=INK2, font=self.f(12), width=2)
            li.pack(side="left", padx=(10, 4), pady=9)
            lt = tk.Label(row, text=txt, bg=SURF, fg=INK2, font=self.f(11, "bold"), anchor="w")
            lt.pack(side="left", fill="x", expand=True)
            for w in (row, li, lt):
                w.bind("<Button-1>", lambda e, k=key: self.prikazi(k))
                w.bind("<Enter>", lambda e, k=key: self.nav_hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self.nav_hover(k, False))
            self.nav[key] = (row, li, lt)

        foot = tk.Frame(side, bg=SURF)
        foot.pack(side="bottom", fill="x", padx=18, pady=18)
        self.lbl_fajl = tk.Label(foot, text="", bg=SURF, fg=INK2, font=self.f(9), anchor="w", justify="left",
                                 wraplength=190)
        self.lbl_fajl.pack(anchor="w")
        lnk = tk.Label(foot, text=("Change table…" if EN else "Promeni tablicu…"), bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2")
        lnk.pack(anchor="w", pady=(4, 0))
        lnk.bind("<Button-1>", lambda e: self.promeni_tablicu())
        jez = tk.Label(foot, text=T("🌐 English", "🌐 Srpski"), bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2")
        jez.pack(anchor="w", pady=(6, 0))
        jez.bind("<Button-1>", lambda e: self.promeni_jezik())
        prob = tk.Label(foot, text=T("⚠ Prijavi problem", "⚠ Report a problem"), bg=SURF, fg=INK2, font=self.f(9), cursor="hand2")
        prob.pack(anchor="w", pady=(4, 0))
        prob.bind("<Button-1>", lambda e: self.prijavi_problem())
        self.lbl_kopija = tk.Label(foot, text="", bg=SURF, fg=INK2, font=self.f(9), anchor="w", cursor="hand2")
        self.lbl_kopija.pack(anchor="w", pady=(8, 0))
        self.lbl_kopija.bind("<Button-1>", lambda e: self.prikazi("pregled"))
        self.lbl_sinh = tk.Label(foot, text=getattr(self, "sinh_stanje", {}).get("tekst", ""), bg=SURF, fg=getattr(self, "sinh_stanje", {}).get("boja", INK2),
                                 font=self.f(9), anchor="w", cursor="hand2", justify="left", wraplength=180)
        self.lbl_sinh.pack(anchor="w", pady=(4, 0))
        self.lbl_sinh.bind("<Button-1>", lambda e: self.prikazi("telefon"))
        self.osvezi_fajl_label()
        self.osvezi_kopija_label()

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.toast_lbl = None


    def osvezi_fajl_label(self):
        self.lbl_fajl.config(text=(f"Data: {os.path.basename(self.tab.putanja)}" if EN else f"Podaci: {os.path.basename(self.tab.putanja)}"))


    def nav_hover(self, k, on):
        row, li, lt = self.nav[k]
        bg = SURF2 if (on or k == self.strana) else SURF
        for w in (row, li, lt):
            w.config(bg=bg)


    def crtaj_markicu(self, c, x, y, w, h, boja=TAG, rupa=SURF):
        r = w * 0.18
        c.create_polygon(self.zaobljeno(x, y, x + w, y + h * 0.62, r) + [x + w, y + h * 0.62],
                         fill=boja, outline=boja, smooth=True)
        c.create_arc(x, y + h - w, x + w, y + h, start=180, extent=180, fill=boja, outline=boja)
        c.create_rectangle(x, y + h * 0.4, x + w, y + h - w / 2, fill=boja, outline=boja)
        cx, cy, rr = x + w / 2, y + h * 0.22, w * 0.1
        c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=rupa, outline="#B8A04A")
        c.create_line(x + w * 0.22, y + h * 0.52, x + w * 0.78, y + h * 0.52, fill=TAG_INK, width=2.4,
                      capstyle="round")
        c.create_line(x + w * 0.22, y + h * 0.7, x + w * 0.55, y + h * 0.7, fill=TAG_INK, width=2.4,
                      capstyle="round")


    @staticmethod
    def zaobljeno(x1, y1, x2, y2, r):
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


    def cip(self, parent, text, cmd=None, siv=False, bg=SURF, big=False):
        """Ciparska 'usna markica' sa oznakom grla."""
        fnt = self.f(16 if big else 10, "bold")
        fo = tkfont.Font(font=fnt)
        tw = fo.measure(text)
        h = 40 if big else 26
        pl, pr = (34, 16) if big else (22, 10)
        w = tw + pl + pr
        c = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0, cursor="hand2" if cmd else "")
        boja = "#DDE3DC" if siv else TAG
        r = 9 if big else 7
        c.create_polygon(self.zaobljeno(1, 1, w - 1, h - 1, r), fill=boja, outline=boja, smooth=True)
        hr = 5 if big else 3.5
        hx = 17 if big else 11
        c.create_oval(hx - hr, h / 2 - hr, hx + hr, h / 2 + hr, fill=bg, outline="#A8963F" if not siv else "#AAB3AC")
        c.create_text(pl, h / 2, text=text, anchor="w", font=fnt, fill=TAG_INK if not siv else INK2)
        if cmd:
            c.bind("<Button-1>", lambda e: cmd())
        return c


    def btn(self, parent, text, cmd, kind="Secondary"):
        return ttk.Button(parent, text=text, command=cmd, style=f"{kind}.TButton", cursor="hand2")


    def card(self, parent, padx=20, pady=18):
        outer = tk.Frame(parent, bg=LINE)
        inner = tk.Frame(outer, bg=SURF)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        body = tk.Frame(inner, bg=SURF)
        body.pack(fill="both", expand=True, padx=padx, pady=pady)
        return outer, body


    def lbl(self, parent, text, size=10, weight="normal", fg=INK, bg=None, **kw):
        return tk.Label(parent, text=text, font=self.f(size, weight), fg=fg,
                        bg=bg or parent.cget("bg"), **kw)


    def badge(self, parent, text, fg, bg=None):
        bgc = {OK: OK_BG, WARN: WARN_BG, BAD: BAD_BG}.get(fg, SURF2)
        return tk.Label(parent, text=f" {text} ", font=self.f(9, "bold"), fg=fg, bg=bgc, padx=6, pady=1)


    def toast(self, text):
        if self.toast_lbl and self.toast_lbl.winfo_exists():
            self.toast_lbl.destroy()
        t = tk.Label(self.main, text=text, bg=INK, fg="#FFFFFF", font=self.f(10, "bold"), padx=18, pady=10)
        t.place(relx=0.5, rely=1.0, y=-24, anchor="s")
        self.toast_lbl = t
        self.root.after(2600, lambda: t.winfo_exists() and t.destroy())


    def stat(self, parent, broj, tekst, boja=INK):
        o, b = self.card(parent, 16, 12)
        self.lbl(b, broj, 22, "bold", fg=boja).pack(anchor="w")
        self.lbl(b, tekst, 9, fg=INK2).pack(anchor="w")
        return o


    def tabela(self, parent, kolone, visina=10, tree=True):
        wrap = tk.Frame(parent, bg=LINE)
        inner = tk.Frame(wrap, bg=SURF)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        cols = [k for k, *_ in kolone[1:]] if tree else [k for k, *_ in kolone]
        tv = ttk.Treeview(inner, columns=cols, show="tree headings" if tree else "headings", height=visina,
                          selectmode="extended")
        sb = ttk.Scrollbar(inner, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        for i, (k, naslov, w, *anc) in enumerate(kolone):
            cid = "#0" if (tree and i == 0) else k
            tv.heading(cid, text=naslov, anchor=anc[0] if anc else "w")
            tv.column(cid, width=w, minwidth=40, anchor=anc[0] if anc else "w", stretch=True)
        tv.tag_configure("odd", background="#FAFBF9")
        tv.tag_configure("off", foreground="#98A39B")
        tv.tag_configure("bad", foreground=BAD)
        tv.tag_configure("warn", foreground=WARN)
        tv.tag_configure("ok", foreground=OK)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return wrap, tv


    # ------------------------------------------------------------ podaci
    def promena(self, poruka=None):
        self._ver_podataka = getattr(self, "_ver_podataka", 0) + 1     # brišu se zapamćeni proračuni
        try:
            self.ist.sacuvaj()
            self.pods.sacuvaj()
        except OSError:
            pass
        try:
            self.tab.sacuvaj()
        except PermissionError:
            messagebox.showerror(("Not saved" if EN else "Nije sačuvano"),
                                 ("The table is open in Excel or another program.\n"
                                 "Close it and try again." if EN else "Tablica je otvorena u Excelu ili drugom programu.\n"
                                 "Zatvori je pa pokušaj ponovo."))
            self.tab.ucitaj()
        self.model = Model(self.tab.redovi)
        self.prikazi(self.strana)
        if hasattr(self, "sinh_uskoro"):
            self.sinh_uskoro()                       # telefoni dobijaju promenu za par sekundi
        if self.karton_win and self.karton_win.winfo_exists():
            self.karton(self.karton_win.grlo)
        if poruka:
            self.toast(poruka)


    def proveri_promenu(self, e=None):
        if e is not None and e.widget is not self.root:
            return
        p = self.tab.putanja
        if os.path.isfile(p) and self.tab.mtime and os.path.getmtime(p) != self.tab.mtime:
            try:
                self.tab.ucitaj()
            except Exception as ex:
                messagebox.showerror(("Error in table" if EN else "Greška u tablici"), str(ex))
                return
            self.model = Model(self.tab.redovi)
            self.prikazi(self.strana)
            self.toast(("The table was reloaded (changed in Excel)." if EN else "Tablica je ponovo učitana (izmenjena u Excelu)."))


    def promeni_tablicu(self):
        p = filedialog.askopenfilename(title=("Choose the animals table" if EN else "Izaberi tablicu sa grlima"), initialdir=APP_DIR,
                                       filetypes=[(("CSV table" if EN else "CSV tablica"), "*.csv"), (("All files" if EN else "Svi fajlovi"), "*.*")])
        if not p:
            return
        try:
            t = Tablica(p)
        except Exception as e:
            messagebox.showerror(("The table cannot be loaded" if EN else "Tablica se ne može učitati"), str(e))
            return
        self.tab = t
        self.ist = Istorija(t.putanja)
        self.pods = Podsetnici(t.putanja)
        self.model = Model(t.redovi)
        self.sacuvaj_podesavanja()
        self.osvezi_fajl_label()
        self.prikazi(self.strana)
        self.toast((f"Loaded {len(t.redovi)} animals." if EN else f"Učitano {len(t.redovi)} grla."))


    def uvezi(self):
        p = filedialog.askopenfilename(title=("Import table from Excel (CSV)" if EN else "Uvezi tablicu iz Excela (CSV)"),
                                       filetypes=[(("Excel or CSV table" if EN else "Excel ili CSV tablica"), "*.xlsx *.csv"),
                                                  (("Excel workbook" if EN else "Excel tabela"), "*.xlsx"),
                                                  (("CSV table" if EN else "CSV tablica"), "*.csv"), (("All files" if EN else "Svi fajlovi"), "*.*")])
        if not p:
            return
        try:
            redovi, _ = procitaj_csv(p)
        except Exception as e:
            messagebox.showerror(("Import failed" if EN else "Uvoz nije uspeo"), str(e))
            return
        po_id = {r["id"]: r for r in self.tab.redovi}
        nov = izm = 0
        for r in redovi:
            r = {k: r.get(k, "") for k in KOLONE}
            if r["id"] in po_id:
                if not r["uneto"]:
                    r.pop("uneto")
                po_id[r["id"]].update(r)
                izm += 1
            else:
                r["uneto"] = r.get("uneto") or sada()
                self.tab.redovi.append(r)
                self.ist.dodaj(r["id"], AUTO, (f"Added by import from table {os.path.basename(p)}" if EN else f"Upisano uvozom iz tablice {os.path.basename(p)}"), automatski=True)
                po_id[r["id"]] = r
                nov += 1
        dod = ""
        if p.lower().endswith((".xlsx", ".xlsm")):   # Farmerov Excel izvoz: i preci, istorija i podsetnici
            try:
                from izvoz import dopuni_iz_excela
                from podaci import procitaj_xlsx
                n_pr, n_ist, n_pod = dopuni_iz_excela(procitaj_xlsx(p), self.tab.redovi, self.ist, self.pods, p)
                dod = "".join(t for t in (
                    (f", {n_pr} ancestors" if EN else f", {n_pr} predaka") if n_pr else "",
                    (f", {n_ist} history entries" if EN else f", {n_ist} zapisa istorije") if n_ist else "",
                    (f", {n_pod} reminders" if EN else f", {n_pod} podsetnika") if n_pod else ""))
                if n_pod:
                    self.pods.sacuvaj()
            except Exception as e:
                messagebox.showwarning(("Import" if EN else "Uvoz"), (("Animals were imported, but the other sheets could not be read:\n" if EN
                                       else "Grla su uvezena, ali ostali listovi nisu mogli da se pročitaju:\n") + str(e)))
        self.promena((f"Imported: {nov} new" if EN else f"Uvezeno: {nov} novih") + ((f", {izm} changed" if EN else f", {izm} izmenjenih") if izm else "") + (" animals" if EN else " grla") + dod + ".")


    def otvori_excel(self):
        if not os.path.isfile(self.tab.putanja):
            self.tab.sacuvaj()
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.tab.putanja)
            elif sys.platform == "darwin":
                os.system(f'open "{self.tab.putanja}"')
            else:
                os.system(f'xdg-open "{self.tab.putanja}" &')
            self.toast(("When you save changes in Excel, the program will reload them." if EN else "Kad sačuvaš izmene u Excelu, program će ih sam učitati."))
        except OSError:
            messagebox.showinfo(("Table" if EN else "Tablica"), self.tab.putanja)


    # ------------------------------------------------------------ strane
    def prikazi(self, strana):
        self.strana = strana
        for k in self.nav:
            row, li, lt = self.nav[k]
            akt = k == strana or (k == "grla" and strana == "obrisana")
            for w in (row, li, lt):
                w.config(bg=SURF2 if akt else SURF)
            lt.config(fg=INK if akt else INK2)
            li.config(fg=BRAND if akt else INK2)
        self.osvezi_nav_brojac()
        for w in self.main.winfo_children():
            if w is not self.toast_lbl:
                w.destroy()
        getattr(self, "s_" + strana)()


    def zaglavlje(self, parent, naslov, podnaslov="", akcije=()):
        h = tk.Frame(parent, bg=BG)
        h.pack(fill="x", pady=(0, 18))
        desno = tk.Frame(h, bg=BG)
        desno.pack(side="right", anchor="s")
        for txt, cmd, kind in reversed(akcije):
            b = self.btn(desno, txt, cmd, kind)
            if len(akcije) > 4:            # mnogo dugmadi: širina po tekstu, da podnaslov ostane vidljiv
                b.configure(width=0)
            b.pack(side="right", padx=(8, 0))
        levo = tk.Frame(h, bg=BG)
        levo.pack(side="left", fill="x", expand=True)
        self.lbl(levo, naslov, 24, "bold").pack(anchor="w")
        if podnaslov:
            self.lbl(levo, podnaslov, 10, fg=INK2, justify="left",
                     wraplength=620 if not akcije else 300).pack(anchor="w", pady=(2, 0))
        return h


    def prazno(self, parent):
        o, b = self.card(parent, 30, 50)
        o.pack(fill="x")
        if self.logo.get(64):
            tk.Label(b, image=self.logo[64], bg=SURF, bd=0).pack()
        else:
            c = tk.Canvas(b, width=56, height=64, bg=SURF, highlightthickness=0)
            c.pack()
            self.crtaj_markicu(c, 4, 2, 48, 58)
        self.lbl(b, ("The herd is still empty" if EN else "Stado je još prazno"), 16, "bold").pack(pady=(14, 4))
        self.lbl(b, ("Add animals one by one or import an existing table from Excel.\n"
                    "For each animal enter the sire and dam if you know them." if EN else "Dodaj grla jedno po jedno ili uvezi postojeću tablicu iz Excela.\n"
                    "Za svako grlo upiši oca i majku ako ih znaš."), 10, fg=INK2, justify="center").pack()
        r = tk.Frame(b, bg=SURF)
        r.pack(pady=(18, 0))
        self.btn(r, ("+  Add first animal" if EN else "+  Dodaj prvo grlo"), lambda: self.forma(), "Primary").pack(side="left", padx=4)
        self.btn(r, ("Import table from Excel" if EN else "Uvezi tablicu iz Excela"), self.uvezi).pack(side="left", padx=4)


    def strana_okvir(self, scroll=True):
        if scroll:
            sf = ScrollFrame(self.main)
            sf.pack(fill="both", expand=True)
            body = tk.Frame(sf.inner, bg=BG)
            body.pack(fill="both", expand=True, padx=36, pady=28)
            return body
        body = tk.Frame(self.main, bg=BG)
        body.pack(fill="both", expand=True, padx=36, pady=28)
        return body


    def napomena(self, parent, tekst, ok=False, wraplength=820):
        f = tk.Frame(parent, bg=OK_BG if ok else WARN_BG)
        f.pack(fill="x", pady=(0, 14))
        self.lbl(f, tekst, 10, fg=OK if ok else WARN, justify="left", wraplength=wraplength).pack(
            anchor="w", padx=14, pady=10)


    def postavi_prozor(self, win, parent):
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(10, (r.winfo_height() - win.winfo_height()) // 3)}")

    promeni_jezik = _app_promeni_jezik
