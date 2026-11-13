"""Glavni prozor: podešavanja, stil, meni levo, dugmad, tabele, menjanje strana i jezika."""
import json
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

from osnova import APP_DIR, EN, JEZICI, JEZIK, PODESAVANJA, _ime_stada
from jezik import AUTO, T, postavi_jezik
from podaci import Istorija, KOLONE, Podsetnici, Tablica, procitaj_csv, sada
from izgled import (BAD, BAD_BG, BG, BRAND, BRAND_H, INK, INK2, LINE, LOGO, OK, OK_BG, SURF, SURF2,
    ScrollFrame, TAG, TAG_INK, WARN, WARN_BG, ikonica_markice, izaberi_font, postavi_win_ikonicu)
from rodoslov import Model
import precica


def _app_meni_jezika(self, widget):
    """Mali meni sa svim jezicima programa (klik na 🌐 dole levo)."""
    m = tk.Menu(self.root, tearoff=0, font=self.f(10))
    for kod, naziv in JEZICI:
        m.add_command(label=("✓ " if kod == JEZIK else "    ") + naziv, command=lambda k=kod: self.promeni_jezik(k))
    try:
        m.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() - 6 * 26)
    finally:
        m.grab_release()


def _app_promeni_jezik(self, novi=None):
    """Promena jezika odmah, bez ponovnog pokretanja programa."""
    novi = novi or T("en", "sr")
    if novi == JEZIK:
        return
    strana = self.strana if self.strana != "obrisana" else "grla"
    for w in (self.karton_win, getattr(self, "ist_win", None), getattr(self, "stablo_win", None)):
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
    fin = getattr(self, "_fin", None)
    for sacuvaj in (self.ist.sacuvaj, self.pods.sacuvaj) + ((fin.sacuvaj,) if fin is not None else ()):
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
    self._fin = None            # finansije se ponovo čitaju (kategorije na novom jeziku)
    self.ui.update(q="", pol="", poreklo="", partner="", partner_upit="", partner_vise=[], sA="", sB="")
    self.karton_win = None
    for w in self.root.winfo_children():
        w.destroy()
    self.shell()
    self.prikazi(strana)
    try:
        self.toast("🌐 " + dict(JEZICI).get(novi, novi))
    except Exception:
        pass


class OsnovaProzora:
    """Glavni prozor: podešavanja, stil, meni levo, dugmad, tabele, menjanje strana i jezika."""

    def __init__(self, root):
        self.root = root
        self.pod = self.ucitaj_podesavanja()
        self.ucitaj_moje_vrste()                       # vrste koje je korisnik dodao (magarci, psi…)
        self.prag = self.pod.get("prag", 0.0625)
        self.F = izaberi_font()
        root.title("HerdDoc")
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
            messagebox.showerror((T("Tablica se ne može učitati", "The table cannot be loaded")), str(e))
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
        root.after(400, self.korisnik_na_startu)          # ime i prezime – jednom, obavezno (uz promene piše ko ih je uneo)
        if len(" ".join(str(self.pod.get("korisnik") or "").split()).split()) >= 2:
            root.after(700, self.obavestenja_na_startu)  # inače posle upisa imena (da se prozori ne preklapaju)
        root.after(10 * 60 * 1000, self.iskacuce_provera)   # zatim na svakih 30 min: nova hitna obaveštenja kao poruka u uglu ekrana
        root.after(1500, self.dnevna_kopija)
        root.after(2500, self.licenca_na_startu)
        root.after(4500, lambda: precica.ponudi(self))
        root.after(2 * 60 * 1000, self.mreza_petlja)    # udruženje: svoja grla šalje drugim farmama (samo kad ima promena)   # samo verzija iz prodavnice, samo jednom
        root.after(60000, self.dnevna_kopija_u_oblak)     # kopija u oblaku jednom dnevno (ako je telefon uparen)
        self.pokreni_sinhronizaciju()
        root.bind("<FocusIn>", self.proveri_promenu)
        root.bind("<F2>", lambda e: self.citac())          # F2 = čitač minđuša
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
        if not self.pod.get("korisnik"):              # drugi otvoren HerdDoc je možda upisao ime – ne briše se
            ime = self.ucitaj_podesavanja().get("korisnik")
            if ime:
                self.pod["korisnik"] = ime
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
        tk.Label(t, text="HerdDoc", bg=SURF, fg=INK, font=self.f(12, "bold")).pack(anchor="w")
        tk.Label(t, text=(T("srodstvo i parenje", "kinship & mating")), bg=SURF, fg=INK2, font=self.f(9),
                 wraplength=140, justify="left").pack(anchor="w")

        self.nav = {}
        for key, txt, ic in (("grla", (T("Grla", "Animals")), "☰"), ("parenje", (T("Parenje", "Mating")), "⚭"),
                             ("srodstvo", (T("Srodstvo", "Relationship")), "⑂"),
                             ("rasa", T("Nova rasa", "New breed"), "✦"), ("mreza", T("Udruženje", "Association"), "⌂"), ("istorija", (T("Istorija", "History")), "◷"),
                             ("mlecnost", (T("Mlečnost", "Milk")), "◔"), ("finansije", (T("Finansije", "Finances")), "¤"),
                             ("obavestenja", (T("Obaveštenja", "Notifications")), "◉"), ("pregled", (T("Pregled", "Overview")), "▥"),
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
        lnk = tk.Label(foot, text=(T("Promeni tablicu…", "Change table…")), bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2")
        lnk.pack(anchor="w", pady=(4, 0))
        lnk.bind("<Button-1>", lambda e: self.promeni_tablicu())
        jez = tk.Label(foot, text="🌐 " + dict(JEZICI).get(JEZIK, JEZIK) + "  ▾", bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2")
        jez.pack(anchor="w", pady=(6, 0))
        jez.bind("<Button-1>", lambda e: self.meni_jezika(jez))
        self.oznaka_korisnika(foot)
        self.lbl_licenca = tk.Label(foot, text="", bg=SURF, fg=INK2, font=self.f(9, "bold"), cursor="hand2", anchor="w",
                                    justify="left", wraplength=190)
        self.lbl_licenca.pack(anchor="w", pady=(6, 0))
        self.lbl_licenca.bind("<Button-1>", lambda e: self.prozor_licence())
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
        self.osvezi_licenca_label()

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.toast_lbl = None


    def osvezi_fajl_label(self):
        self.lbl_fajl.config(text=(T(f"Podaci: {os.path.basename(self.tab.putanja)}", f"Data: {os.path.basename(self.tab.putanja)}")))


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
        nap = self.napomena_grla(text)
        if nap:                                  # grlo ima napomenu: narandžasti znak „!“ i oblačić sa tekstom
            rz = 10 if big else 7
            c.configure(width=w + 2 * rz + 4)
            cx = w + rz + 2
            c.create_oval(cx - rz, h / 2 - rz, cx + rz, h / 2 + rz, fill="#E07B00", outline="#E07B00")
            c.create_text(cx, h / 2, text="!", font=self.f(12 if big else 9, "bold"), fill="#FFFFFF")
            self.savet(c, nap)
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
        # grlo sa napomenom: znak ⚠ pored oznake, a napomena se vidi kad se miš zadrži na redu
        upis = tv.insert

        def insert(parent_, index, iid=None, **kw):
            if iid is not None and kw.get("text") and self.napomena_grla(iid):
                kw["text"] = kw["text"] + "  ⚠"
            return upis(parent_, index, iid=iid, **kw)
        tv.insert = insert
        self.savet(tv, lambda e: self.napomena_grla(tv.identify_row(e.y)))
        return wrap, tv

    # ------------------------------------------------------------ napomena o grlu
    def napomena_grla(self, x):
        """Napomena upisana grlu (vidi se svuda gde se grlo pojavi) ili ""."""
        try:
            return self.model.A.get(x, {}).get("napomena", "") if x else ""
        except Exception:
            return ""

    def savet(self, w, tekst):
        """Mali žuti oblačić kad se miš zadrži na elementu. tekst: string ili funkcija(event) -> string."""
        stanje = {"win": None, "tekst": None}

        def sakrij(e=None):
            if stanje["win"] is not None:
                try:
                    stanje["win"].destroy()
                except Exception:
                    pass
            stanje["win"] = stanje["tekst"] = None

        def pokazi(e):
            t = tekst(e) if callable(tekst) else tekst
            if t == stanje["tekst"]:
                if stanje["win"] is not None:
                    stanje["win"].geometry(f"+{e.x_root + 14}+{e.y_root + 16}")
                return
            sakrij()
            if not t:
                return
            win = tk.Toplevel(w)
            win.wm_overrideredirect(True)
            try:
                win.attributes("-topmost", True)
            except Exception:
                pass
            tk.Label(win, text="⚠ " + t, bg="#FCEFD2", fg="#7A4D00", font=self.f(10, "bold"), padx=10, pady=6,
                     wraplength=360, justify="left", highlightthickness=1, highlightbackground="#E0B860").pack()
            win.geometry(f"+{e.x_root + 14}+{e.y_root + 16}")
            stanje["win"], stanje["tekst"] = win, t
        w.bind("<Motion>", pokazi, add="+")
        w.bind("<Leave>", sakrij, add="+")
        w.bind("<Destroy>", sakrij, add="+")
        w.bind("<ButtonPress>", sakrij, add="+")


    # ------------------------------------------------------------ podaci
    def promena(self, poruka=None):
        self._ver_podataka = getattr(self, "_ver_podataka", 0) + 1     # brišu se zapamćeni proračuni
        self.osvezi_licenca_label()
        try:
            self.ist.sacuvaj()
            self.pods.sacuvaj()
            if getattr(self, "_fin", None) is not None:
                self._fin.sacuvaj()
        except OSError:
            pass
        try:
            self.tab.sacuvaj()
        except PermissionError:
            messagebox.showerror((T("Nije sačuvano", "Not saved")),
                                 (T("Tablica je otvorena u Excelu ili drugom programu.\n"
                                 "Zatvori je pa pokušaj ponovo.", "The table is open in Excel or another program.\n"
                                 "Close it and try again.")))
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
                messagebox.showerror((T("Greška u tablici", "Error in table")), str(ex))
                return
            self.model = Model(self.tab.redovi)
            self.prikazi(self.strana)
            self.toast((T("Tablica je ponovo učitana (izmenjena u Excelu).", "The table was reloaded (changed in Excel).")))


    def promeni_tablicu(self):
        p = filedialog.askopenfilename(title=(T("Izaberi tablicu sa grlima", "Choose the animals table")), initialdir=APP_DIR,
                                       filetypes=[((T("CSV tablica", "CSV table")), "*.csv"), ((T("Svi fajlovi", "All files")), "*.*")])
        if not p:
            return
        if not self.sme_tablicu(p):
            return
        try:
            t = Tablica(p)
        except Exception as e:
            messagebox.showerror((T("Tablica se ne može učitati", "The table cannot be loaded")), str(e))
            return
        self.tab = t
        self.ist = Istorija(t.putanja)
        self.pods = Podsetnici(t.putanja)
        self.model = Model(t.redovi)
        self.sacuvaj_podesavanja()
        self.osvezi_fajl_label()
        self.prikazi(self.strana)
        self.toast((T(f"Učitano {len(t.redovi)} grla.", f"Loaded {len(t.redovi)} animals.")))


    def uvezi(self):
        p = filedialog.askopenfilename(title=(T("Uvezi tablicu iz Excela (CSV)", "Import table from Excel (CSV)")),
                                       filetypes=[((T("Excel ili CSV tablica", "Excel or CSV table")), "*.xlsx *.csv"),
                                                  ((T("Excel tabela", "Excel workbook")), "*.xlsx"),
                                                  ((T("CSV tablica", "CSV table")), "*.csv"), ((T("Svi fajlovi", "All files")), "*.*")])
        if not p:
            return
        try:
            redovi, _ = procitaj_csv(p)
        except Exception as e:
            messagebox.showerror((T("Uvoz nije uspeo", "Import failed")), str(e))
            return
        po_id = {r["id"]: r for r in self.tab.redovi}
        import licenca
        lic_s, lic_akt, preko = self.lic_stanje(), licenca.aktivnih_grla(self.tab.redovi), 0
        nov = izm = 0
        from izvoz import Identiteti, _ozn_markica
        # fajl sa drugog gazdinstva (HerdDoc izvoz sa kolonom gazdinstvo): isto ime ≠ isto grlo
        farme = {" ".join(str(r.get("gazdinstvo") or "").split()) for r in redovi} - {""}
        moja = " ".join(str(self.pod.get("gazdinstvo", "")).split())
        tudje = bool(farme) and not (moja and farme == {moja})
        ident = Identiteti(self.tab.redovi, next(iter(farme)) if len(farme) == 1 else "", tudje=tudje)
        listovi = None
        if p.lower().endswith((".xlsx", ".xlsm")):
            try:
                from podaci import procitaj_xlsx
                listovi = procitaj_xlsx(p)
                for _, sirovo in listovi[1:]:          # markice predaka iz lista Rodovnik
                    if sirovo and any(str(k).strip().lower() in ("otac_oca", "sire_of_sire") for k in sirovo[0]):
                        for red_ in sirovo[1:]:
                            for c in red_[1:]:
                                ime_, mk_ = _ozn_markica(c)
                                ident.zapamti_markicu(ime_, mk_)
            except Exception:
                listovi = None
        for r in redovi:
            farma = (r.get("gazdinstvo") or "").strip()
            r = {k: r.get(k, "") for k in KOLONE}
            ime_u_fajlu = r["id"]
            r["id"] = ident.id(r["id"], r.get("markica", ""), r.get("rfid", ""), r.get("stare_markice", ""))
            for k in ("otac", "majka"):
                if r.get(k):
                    r[k] = ident.id(r[k])
            if farma and r["id"] not in po_id and not r.get("poreklo_od"):
                r["poreklo_od"] = farma          # grlo sa drugog gazdinstva: zapamti odakle je
            if r["id"] in po_id and tudje:
                # isto grlo koje već imamo: dopunjava se samo ono što nedostaje (status, roditelji, stado ostaju naši)
                nase = po_id[r["id"]]
                for k, v in r.items():
                    if v and not nase.get(k) and k not in ("status", "uneto", "stado"):
                        nase[k] = v
                izm += 1
            elif r["id"] in po_id:
                if not r["uneto"]:
                    r.pop("uneto")
                po_id[r["id"]].update(r)
                izm += 1
            else:
                if (r.get("status") or "aktivno") == "aktivno":       # paket pun: grlo se uvozi kao neaktivno (podaci i rodoslov ostaju)
                    if licenca.ima_mesta(lic_s, lic_akt):
                        lic_akt += 1
                    else:
                        r["status"] = "neaktivno"
                        preko += 1
                r["uneto"] = r.get("uneto") or sada()
                self.tab.redovi.append(r)
                self.ist.dodaj(r["id"], AUTO, (T(f"Upisano uvozom iz tablice {os.path.basename(p)}", f"Added by import from table {os.path.basename(p)}"))
                               + (T(f" – na gazdinstvu {farma or '?'} se zove {ime_u_fajlu}", f" – called {ime_u_fajlu} on farm {farma or '?'}")
                                  if ime_u_fajlu != r["id"] else ""), automatski=True)
                po_id[r["id"]] = r
                nov += 1
        dod = ""
        if p.lower().endswith((".xlsx", ".xlsm")):   # Excel izvoz iz HerdDoc-a: i preci, istorija i podsetnici
            try:
                from izvoz import dopuni_iz_excela
                from podaci import procitaj_xlsx
                n_pr, n_ist, n_pod = dopuni_iz_excela(listovi or procitaj_xlsx(p), self.tab.redovi, self.ist, self.pods, p,
                                                      ident=ident if tudje else None)
                dod = "".join(t for t in (
                    (T(f", {n_pr} predaka", f", {n_pr} ancestors")) if n_pr else "",
                    (T(f", {n_ist} zapisa istorije", f", {n_ist} history entries")) if n_ist else "",
                    (T(f", {n_pod} podsetnika", f", {n_pod} reminders")) if n_pod else ""))
                if n_pod:
                    self.pods.sacuvaj()
            except Exception as e:
                messagebox.showwarning((T("Uvoz", "Import")), ((T("Grla su uvezena, ali ostali listovi nisu mogli da se pročitaju:\n", "Animals were imported, but the other sheets could not be read:\n")) + str(e)))
        self.promena((T(f"Uvezeno: {nov} novih", f"Imported: {nov} new")) + ((T(f", {izm} izmenjenih", f", {izm} changed")) if izm else "") + (T(" grla", " animals")) + dod + ".")
        if preko:
            messagebox.showinfo(T("Uvoz – broj grla", "Import – number of animals"),
                                T(f"Paket „{licenca.naziv_paketa(lic_s['paket'])}“ dozvoljava {lic_s['limit']} aktivnih grla. "
                                  f"{preko} grla je uvezeno kao neaktivno – podaci i rodoslov su sačuvani.\n\n"
                                  f"Za više aktivnih grla izaberi veći paket (levi meni → 🔑).",
                                  f"The “{licenca.naziv_paketa(lic_s['paket'])}” package allows {lic_s['limit']} active animals. "
                                  f"{preko} animals were imported as inactive – their data and pedigree are kept.\n\n"
                                  f"For more active animals choose a larger package (left menu → 🔑)."))
        self.osvezi_licenca_label()
        pre = ident.preimenovana()
        if pre:
            spisak = "\n".join(f"   {a}  →  {b}" for a, b in list(pre.items())[:15]) + (T(f"\n   … i još {len(pre) - 15}", f"\n   … and {len(pre) - 15} more") if len(pre) > 15 else "")
            messagebox.showinfo(T("Uvoz – ista imena", "Import – same names"),
                                T(f"Ova grla sa drugog gazdinstva se zovu isto kao vaša grla, a nisu ista grla (druga markica). "
                                  f"Upisana su pod novim imenom, da se vaša grla ne promene:\n\n{spisak}\n\n"
                                  f"Rodoslov je povezan ispravno. Ime možete promeniti u kartonu grla.",
                                  f"These animals from another farm have the same names as your animals, but are different animals (different ear tag). "
                                  f"They were entered under a new name so your animals are not changed:\n\n{spisak}\n\n"
                                  f"The pedigree is linked correctly. You can rename them in the animal card."))


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
            self.toast((T("Kad sačuvaš izmene u Excelu, program će ih sam učitati.", "When you save changes in Excel, the program will reload them.")))
        except OSError:
            messagebox.showinfo((T("Tablica", "Table")), self.tab.putanja)


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
        nl = self.lbl(levo, naslov, 24, "bold")
        nl.pack(anchor="w")
        pl = None
        if podnaslov:
            pl = self.lbl(levo, podnaslov, 10, fg=INK2, justify="left",
                          wraplength=620 if not akcije else 300)
            pl.pack(anchor="w", pady=(2, 0))
        if akcije:
            stanje = {"dole": False}

            def raspored(e=None):
                """Dugi nazivi dugmadi (npr. na nemačkom): dugmad idu u red ispod naslova, da se naslov vidi."""
                sirina = h.winfo_width()
                if sirina <= 1:
                    return
                dole = desno.winfo_reqwidth() + max(nl.winfo_reqwidth(), 260) + 24 > sirina
                if dole == stanje["dole"]:
                    return
                stanje["dole"] = dole
                desno.pack_forget()
                levo.pack_forget()
                if dole:
                    levo.pack(side="top", fill="x")
                    desno.pack(side="top", anchor="w", pady=(10, 0))
                    if pl is not None:
                        pl.configure(wraplength=900)
                else:
                    desno.pack(side="right", anchor="s")
                    levo.pack(side="left", fill="x", expand=True)
                    if pl is not None:
                        pl.configure(wraplength=300)
            h.bind("<Configure>", raspored, add="+")
            h.after_idle(raspored)
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
        self.lbl(b, (T("Stado je još prazno", "The herd is still empty")), 16, "bold").pack(pady=(14, 4))
        self.lbl(b, (T("Dodaj grla jedno po jedno ili uvezi postojeću tablicu iz Excela.\n"
                    "Za svako grlo upiši oca i majku ako ih znaš.", "Add animals one by one or import an existing table from Excel.\n"
                    "For each animal enter the sire and dam if you know them.")), 10, fg=INK2, justify="center").pack()
        r = tk.Frame(b, bg=SURF)
        r.pack(pady=(18, 0))
        self.btn(r, (T("+  Dodaj prvo grlo", "+  Add first animal")), lambda: self.forma(), "Primary").pack(side="left", padx=4)
        self.btn(r, (T("Uvezi tablicu iz Excela", "Import table from Excel")), self.uvezi).pack(side="left", padx=4)


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
    meni_jezika = _app_meni_jezika
