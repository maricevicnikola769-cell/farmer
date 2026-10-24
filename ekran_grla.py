"""Strana 'Grla': spisak, pretraga, markice, stada, brisanje i vraćanje grla."""
import os
import shutil
import sys
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from osnova import EN
from jezik import AUTO, POREKLA, REDOSLEDI
from podaci import (Istorija, Podsetnici, fmt_starost, fmt_upis, norm, parsiraj_datum, pct, sort_key,
    stare_lista, starost_meseci)
from izgled import BAD, BG, BRAND, INK, INK2, OK, SURF, SURF2, WARN
from rodoslov import Model


class GrlaEkran:
    """Strana 'Grla': spisak, pretraga, markice, stada, brisanje i vraćanje grla."""


    # ---------- Grla
    def s_grla(self):
        body = self.strana_okvir(scroll=False)
        sva = self.model.grla()
        akt = sum(a["aktivno"] for a in sva)
        self.zaglavlje(body, ("Animals" if EN else "Grla"), (f"{akt} in herd, {len(sva)} recorded in total." if EN else f"{akt} u zapatu, ukupno {len(sva)} upisanih.")
                       if sva else ("Records of all animals with their parents." if EN else "Evidencija svih grla sa roditeljima."),
                       [(("Partner search" if EN else "Pretraga partnera"), self.idi_na_pretragu, "Secondary"),
                        (("Import" if EN else "Uvezi"), self.uvezi, "Secondary"), (("Export" if EN else "Izvezi"), self.izvezi, "Secondary"), (("Open in Excel" if EN else "Otvori u Excelu"), self.otvori_excel, "Secondary"),
                        (("+  New animal" if EN else "+  Novo grlo"), lambda: self.forma(), "Primary")])
        if not sva:
            self.prazno(body)
            return
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        self.q_var = tk.StringVar(value=self.ui["q"])
        e = ttk.Entry(tb, textvariable=self.q_var, font=self.f(10), width=26)
        e.pack(side="left")
        ph = self.lbl(tb, ("⌕  Search by tag, ear tag, breed…" if EN else "⌕  Traži po oznaci, markici, rasi…"), 10, fg="#98A39B", bg=SURF)
        def ph_show(*_):
            if self.q_var.get():
                ph.place_forget()
            else:
                ph.place(in_=e, x=10, rely=0.5, anchor="w")
        ph.bind("<Button-1>", lambda ev: e.focus_set())
        ph_show()
        self.pol_var = tk.StringVar(value={"": ("All sexes" if EN else "Svi polovi"), "z": ("Females" if EN else "Ženska"), "m": ("Males" if EN else "Muška")}[self.ui["pol"]])
        cb = ttk.Combobox(tb, textvariable=self.pol_var, values=[("All sexes" if EN else "Svi polovi"), ("Females" if EN else "Ženska"), ("Males" if EN else "Muška")], width=10,
                          state="readonly", font=self.f(10))
        cb.pack(side="left", padx=10)
        self.por_var = tk.StringVar(value=self.ui.get("poreklo") or ("Any origin" if EN else "Svako poreklo"))
        cbp = ttk.Combobox(tb, textvariable=self.por_var, values=[("Any origin" if EN else "Svako poreklo")] + POREKLA, width=15,
                           state="readonly", font=self.f(10))
        cbp.pack(side="left", padx=(0, 10))
        cbp.bind("<<ComboboxSelected>>", lambda ev: self.grla_filter())
        self.akt_var = tk.BooleanVar(value=self.ui["samo_akt"])
        ttk.Checkbutton(tb, text=("Only in herd" if EN else "Samo u zapatu"), variable=self.akt_var,
                        command=lambda: self.grla_filter()).pack(side="left", padx=6)
        self.red_var = tk.StringVar(value=self.ui.get("redosled") or REDOSLEDI[0])
        cbr = ttk.Combobox(tb, textvariable=self.red_var, values=REDOSLEDI, state="readonly", width=21,
                           font=self.f(10))
        cbr.pack(side="right")
        cbr.bind("<<ComboboxSelected>>", lambda ev: self.grla_filter())
        self.lbl(tb, ("Order:" if EN else "Redosled:"), 9, "bold", fg=INK2).pack(side="right", padx=(0, 6))

        wrap, tv = self.tabela(body, [("id", ("Animal" if EN else "Grlo"), 105), ("markica", ("Ear tag" if EN else "Markica"), 125), ("pol", ("Sex" if EN else "Pol"), 70),
                                      ("rasa", ("Breed" if EN else "Rasa"), 130), ("starost", ("Age" if EN else "Starost"), 90), ("otac", ("Sire" if EN else "Otac"), 100),
                                      ("majka", ("Dam" if EN else "Majka"), 100), ("upis", ("Added" if EN else "Upisano"), 95), ("f", ("Inbreeding" if EN else "Inbriding"), 90, "e")],
                               visina=14)
        wrap.pack(fill="both", expand=True)
        self.tv_grla = tv
        tv.bind("<Double-1>", lambda ev: self.otvori_iz(tv))
        tv.bind("<Return>", lambda ev: self.otvori_iz(tv))
        tv.bind("<Delete>", lambda ev: self.obrisi_grla([i for i in tv.selection() if i in self.model.A]))
        tv.bind("<Button-3>", lambda ev: self.meni_grla(tv, ev))
        tv.bind("<Button-2>", lambda ev: self.meni_grla(tv, ev))
        dno = tk.Frame(body, bg=BG)
        dno.pack(fill="x", pady=(8, 0))
        self.lbl(dno, ("Double-click opens the card, right-click gives more options. Select animals (several with Ctrl): Delete removes them, Export exports only them." if EN else "Dvoklik otvara karton, desni klik daje više opcija. Označi grla (više uz Ctrl): Delete ih briše, Izvezi izvozi samo njih."),
                 9, fg=INK2).pack(side="left")
        n_obr = len(self.model.obrisana())
        if n_obr:
            lnk = self.lbl(dno, (f"Deleted animals ({n_obr})" if EN else f"Obrisana grla ({n_obr})"), 9, "bold", fg=BRAND, cursor="hand2")
            lnk.pack(side="right")
            lnk.bind("<Button-1>", lambda e: self.prikazi("obrisana"))
        self.q_var.trace_add("write", lambda *_: (ph_show(), self.grla_filter()))
        cb.bind("<<ComboboxSelected>>", lambda ev: self.grla_filter())
        self.grla_filter()


    def grla_filter(self):
        self.ui["q"] = self.q_var.get()
        self.ui["pol"] = {("Females" if EN else "Ženska"): "z", ("Males" if EN else "Muška"): "m"}.get(self.pol_var.get(), "")
        self.ui["poreklo"] = "" if self.por_var.get() == ("Any origin" if EN else "Svako poreklo") else self.por_var.get()
        self.ui["samo_akt"] = self.akt_var.get()
        self.ui["redosled"] = self.red_var.get()
        tv, m, q = self.tv_grla, self.model, norm(self.ui["q"])
        tv.delete(*tv.get_children())
        i = 0
        for a in m.grla(redosled=self.ui["redosled"]):
            if self.ui["samo_akt"] and not a["aktivno"]:
                continue
            if self.ui["poreklo"] and norm(a["poreklo"]) != norm(self.ui["poreklo"]):
                continue
            if self.ui["pol"] and a["pol"] != self.ui["pol"]:
                continue
            if q and not (any(q in norm(a[k]) for k in ("id", "markica", "rasa", "stado", "poreklo_od"))
                          or any(q in norm(x) for x in a["stare"])):
                continue
            o, mj = m.P[a["id"]]
            f = m.inbr(a["id"])
            tags = ["odd"] if i % 2 else []
            if not a["aktivno"]:
                tags.append("off")
            elif f > self.prag:
                tags.append("bad")
            if self.karenca(a["id"]):
                tags.append("kar")
            tv.tag_configure("kar", foreground=WARN)
            tv.insert("", "end", iid=a["id"], text="  " + a["id"] + ("  ✚" if "kar" in tags else ""), image=self.img_tag,
                      values=(a["markica"] or "–", m.pol_naziv(a["id"]), a["rasa"] or "–",
                              fmt_starost(starost_meseci(a["datum"])) or "–", o or "–", mj or "–",
                              fmt_upis(a["uneto"]), pct(f) + ("  ⚠" if f > self.prag else "")), tags=tags)
            i += 1
        if not i:
            tv.insert("", "end", text="", values=("", ("No animal matches the search." if EN else "Nijedno grlo ne odgovara pretrazi."), "", "", "", "", "", ""))


    def idi_na_pretragu(self, x=None):
        self.ui.update(par_tab="partner", partner_vise=[])
        if x:
            self.ui.update(partner=x, partner_upit=x)
        self.prikazi("parenje")


    def otvori_iz(self, tv):
        sel = tv.selection()
        if sel and sel[0] in self.model.A:
            self.karton(sel[0])


    # ---------- brisanje
    def red_za(self, jid):
        return next((r for r in self.tab.redovi if r["id"] == jid), None)


    # ---------- usne markice
    def markica_zauzeta(self, mk, red):
        """Vrati poruku ako je markica vec kod drugog grla, inace None."""
        n = norm(mk)
        for r in self.tab.redovi:
            if r is red:
                continue
            if r.get("markica") and norm(r["markica"]) == n:
                return (f"Ear tag {mk} is already entered for animal {r['id']}." if EN else f"Markica {mk} je već upisana za grlo {r['id']}.")
            if any(norm(x) == n for x in stare_lista(r)):
                return (f"Ear tag {mk} previously belonged to animal {r['id']}." if EN else f"Markica {mk} je ranije pripadala grlu {r['id']}.")
            if norm(r["id"]) == n:
                return (f"{mk} is already the tag of animal {r['id']}." if EN else f"{mk} je već oznaka grla {r['id']}.")
        return None


    def primeni_markicu(self, red, nova, zapamti=True):
        """Promeni markicu i popravi potomke koji su roditelja upisali preko stare markice."""
        stara = (red.get("markica") or "").strip()
        nova = nova.strip()
        if stara and norm(stara) != norm(nova):
            n = norm(stara)
            for r in self.tab.redovi:
                if r is red:
                    continue
                for p in ("otac", "majka"):
                    if r.get(p) and norm(r[p]) == n and r[p] != red["id"]:
                        r[p] = red["id"]
            if zapamti:
                st = stare_lista(red)
                if all(norm(x) != n for x in st):
                    st.append(stara)
                red["stare_markice"] = ", ".join(st)
        red["stare_markice"] = ", ".join(x for x in stare_lista(red) if norm(x) != norm(nova))
        if norm(stara) != norm(nova):
            self.ist.dodaj(red["id"], AUTO, (f"Ear tag changed: {stara or '–'} → {nova or '–'}" if EN else f"Ušna markica promenjena: {stara or '–'} → {nova or '–'}"), automatski=True)
        red["markica"] = nova


    def promena_markice(self, jid, parent=None):
        red = self.red_za(jid)
        if not red:
            return
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Change ear tag" if EN else "Promena ušne markice"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Change ear tag" if EN else "Promena ušne markice"), 16, "bold").pack(anchor="w")
        top = tk.Frame(b, bg=SURF)
        top.pack(anchor="w", pady=(14, 4))
        self.cip(top, jid).pack(side="left")
        self.lbl(top, (f"current ear tag:  {red.get('markica') or '–'}" if EN else f"sadašnja markica:  {red.get('markica') or '–'}"), 10, fg=INK2).pack(side="left", padx=12)
        stare = stare_lista(red)
        if stare:
            self.lbl(b, ("Previous ear tags: " if EN else "Ranije markice: ") + ", ".join(stare), 9, fg=INK2).pack(anchor="w")
        self.lbl(b, ("New ear tag" if EN else "Nova markica"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 4))
        var = tk.StringVar(value=red.get("markica", ""))
        e = ttk.Entry(b, textvariable=var, width=36, font=self.f(11))
        e.pack(anchor="w", fill="x")
        self.lbl(b, ("e.g. UK 123456 700123. Leave empty to remove the ear tag." if EN else "npr. RS 1234-5678. Ostavi prazno da ukloniš markicu."),
                 8, fg="#8A968D").pack(anchor="w")
        zap = tk.BooleanVar(value=True)
        ttk.Checkbutton(b, text=("Remember the old ear tag (search still finds the animal by its old number)" if EN else "Zapamti staru markicu (pretraga i dalje nalazi grlo po starom broju)"),
                        variable=zap, style="Card.TCheckbutton").pack(anchor="w", pady=(12, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            nova = var.get().strip()
            if norm(nova) == norm(red.get("markica")) and nova == (red.get("markica") or ""):
                win.destroy()
                return
            if nova:
                poruka = self.markica_zauzeta(nova, red)
                if poruka:
                    err.config(text=poruka)
                    return
            stara = red.get("markica") or "–"
            self.primeni_markicu(red, nova, zapamti=zap.get())
            win.grab_release()
            win.destroy()
            self.promena((f"{jid}: ear tag {stara} → {nova or '–'}" if EN else f"{jid}: markica {stara} → {nova or '–'}"))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
        e.focus_set()
        e.select_range(0, "end")


    # ---------- stado
    def sva_stada(self):
        return sorted({r.get("stado", "").strip() for r in self.tab.redovi if r.get("stado", "").strip()},
                      key=sort_key)


    def promena_stada(self, ids, parent=None):
        ids = [i for i in ids if self.red_za(i)]
        if not ids:
            return
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Move to another herd" if EN else "Premeštanje u drugo stado"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Move to another herd" if EN else "Premeštanje u drugo stado"), 16, "bold").pack(anchor="w")
        top = tk.Frame(b, bg=SURF)
        top.pack(anchor="w", pady=(12, 4))
        for i in ids[:8]:
            self.cip(top, i).pack(side="left", padx=(0, 6))
        if len(ids) > 8:
            self.lbl(top, (f"+ {len(ids) - 8} more" if EN else f"+ još {len(ids) - 8}"), 9, fg=INK2).pack(side="left")
        sada_st = sorted({self.red_za(i).get("stado") or "–" for i in ids})
        self.lbl(b, ("Current herd: " if EN else "Sadašnje stado: ") + ", ".join(sada_st), 10, fg=INK2).pack(anchor="w")
        self.lbl(b, ("New herd" if EN else "Novo stado"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 4))
        sv = tk.StringVar(value="")
        e = ttk.Combobox(b, textvariable=sv, values=self.sva_stada(), width=34, font=self.f(11))
        e.pack(anchor="w", fill="x")
        self.lbl(b, ("Choose an existing herd or type a new name." if EN else "Izaberi postojeće stado ili upiši novi naziv."), 8, fg="#8A968D").pack(anchor="w")
        self.lbl(b, ("Date of move" if EN else "Datum premeštanja"), 9, "bold", fg=INK2).pack(anchor="w", pady=(12, 4))
        dv = tk.StringVar(value=date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        ttk.Entry(b, textvariable=dv, width=16, font=self.f(10)).pack(anchor="w")
        zv = tk.BooleanVar(value=True)
        ttk.Checkbutton(b, text=("Record the move in the animal's history" if EN else "Zapiši premeštanje u istoriju grla"), variable=zv,
                        style="Card.TCheckbutton").pack(anchor="w", pady=(12, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            novo = sv.get().strip()
            if not novo:
                err.config(text=("Type or choose the new herd." if EN else "Upiši ili izaberi novo stado."))
                return
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            # isti naziv kao postojece stado (bez obzira na velika slova) -> koristi postojeci
            novo = next((x for x in self.sva_stada() if x.lower() == novo.lower()), novo)
            pomereno = 0
            for i in ids:
                r = self.red_za(i)
                staro = (r.get("stado") or "").strip()
                if staro == novo:
                    continue
                r["stado"] = novo
                pomereno += 1
                if zv.get():
                    self.ist.dodaj(i, ("Move" if EN else "Premeštanje"), (f"From herd {staro or '–'} to herd {novo}" if EN else f"Iz stada {staro or '–'} u stado {novo}"),
                                   datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), vrednost=novo)
            win.grab_release()
            win.destroy()
            self.promena((f"Moved to herd {novo}: {pomereno} animals" if EN else f"Premešteno u stado {novo}: {pomereno} grla") if pomereno else ("The animals are already in that herd." if EN else "Grla su već u tom stadu."))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, ("Move" if EN else "Premesti"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
        e.focus_set()


    def preimenuj_stado(self, staro):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Rename herd" if EN else "Preimenovanje stada"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        n = sum(1 for r in self.tab.redovi if (r.get("stado") or "").strip() == staro)
        self.lbl(b, ("Rename herd" if EN else "Preimenovanje stada"), 16, "bold").pack(anchor="w")
        self.lbl(b, (f"Herd \"{staro}\" has {n} animals. The new name applies to all of them." if EN else f"Stado „{staro}“ ima {n} grla. Novi naziv važi za sva ta grla."), 10, fg=INK2).pack(
            anchor="w", pady=(8, 0))
        self.lbl(b, ("New name" if EN else "Novi naziv"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 4))
        sv = tk.StringVar(value=staro)
        e = ttk.Entry(b, textvariable=sv, width=34, font=self.f(11))
        e.pack(anchor="w", fill="x")
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            novo = sv.get().strip()
            if not novo:
                err.config(text=("Type a new name." if EN else "Upiši novi naziv."))
                return
            if novo == staro:
                win.destroy()
                return
            for r in self.tab.redovi:
                if (r.get("stado") or "").strip() == staro:
                    r["stado"] = novo
                    self.ist.dodaj(r["id"], AUTO, (f"Herd renamed: {staro} → {novo}" if EN else f"Stado preimenovano: {staro} → {novo}"), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Herd \"{staro}\" is now \"{novo}\"" if EN else f"Stado „{staro}“ je sada „{novo}“"))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        win.geometry(f"+{self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2}"
                     f"+{self.root.winfo_rooty() + 120}")
        e.focus_set()
        e.select_range(0, "end")


    # ---------- brisanje svih grla (5 koraka)
    def brisanje_svih(self):
        n_grla = len(self.tab.redovi)
        if not n_grla:
            messagebox.showinfo(("Delete all animals" if EN else "Brisanje svih grla"), ("There are no animals in the records." if EN else "U evidenciji nema nijednog grla."))
            return
        n_ist = len(self.ist.zapisi)
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Delete all animals" if EN else "Brisanje svih grla"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        st = {"korak": 1, "istorija": tk.StringVar(value="sve"), "kopija": None, "tekst": tk.StringVar(),
              "odbrojavanje": 0, "gotovo": False}
        NASLOVI = [("Warning" if EN else "Upozorenje"), ("What is deleted" if EN else "Šta se briše"), ("Backup" if EN else "Rezervna kopija"), ("Confirmation" if EN else "Potvrda"), ("Deletion" if EN else "Brisanje")]

        glava = tk.Frame(win, bg=SURF)
        glava.pack(fill="x", padx=26, pady=(22, 0))
        sadrzaj = tk.Frame(win, bg=SURF, width=560, height=290)
        sadrzaj.pack(fill="both", expand=True, padx=26, pady=(14, 0))
        sadrzaj.pack_propagate(False)
        dno = tk.Frame(win, bg=SURF)
        dno.pack(fill="x", padx=26, pady=(10, 20))

        def nacrtaj():
            for w in glava.winfo_children() + sadrzaj.winfo_children() + dno.winfo_children():
                w.destroy()
            k = st["korak"]
            self.lbl(glava, (f"Step {k} of 5 – {NASLOVI[k - 1]}" if EN else f"Korak {k} od 5 – {NASLOVI[k - 1]}"), 16, "bold",
                     fg=BAD if k >= 4 else INK).pack(anchor="w")
            tr = tk.Frame(glava, bg=SURF)
            tr.pack(anchor="w", pady=(10, 0))
            for i in range(1, 6):
                boja = BAD if i <= k and k >= 4 else BRAND if i <= k else SURF2
                tk.Frame(tr, bg=boja, width=100, height=6).pack(side="left", padx=(0, 6))
            [k1, k2, k3, k4, k5][k - 1]()

        def dugmad(dalje_txt="Dalje  ›", dalje=None, dalje_stil="Primary", nazad=True, stanje="normal"):
            self.btn(dno, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="left")
            b = self.btn(dno, dalje_txt, dalje or sledeci, dalje_stil)
            b.pack(side="right")
            if stanje == "disabled":
                b.state(["disabled"])
            if nazad and st["korak"] > 1:
                self.btn(dno, ("‹  Back" if EN else "‹  Nazad"), prethodni).pack(side="right", padx=8)
            return b

        def sledeci():
            st["korak"] += 1
            nacrtaj()

        def prethodni():
            st["korak"] -= 1
            nacrtaj()

        def k1():
            self.napomena(sadrzaj, wraplength=520, tekst=("This action deletes ALL animals from the records. After that the animal list, mating plan, "
                                   "relationships and overview will be empty." if EN else "Ova radnja briše SVA grla iz evidencije. Posle toga lista grla, plan parenja, "
                                   "srodstvo i pregled biće prazni."))
            self.lbl(sadrzaj, ("Currently in the records:" if EN else "U evidenciji je sada:"), 10, "bold").pack(anchor="w", pady=(4, 6))
            for t in ((f"•  {n_grla} animals (including deleted and out of herd)" if EN else f"•  {n_grla} grla (uključujući obrisana i van zapata)"),
                      (f"•  {n_ist} history records" if EN else f"•  {n_ist} zapisa u istoriji"),
                      (f"•  table: {self.tab.putanja}" if EN else f"•  tablica: {self.tab.putanja}")):
                self.lbl(sadrzaj, t, 10, fg=INK2, wraplength=540, justify="left").pack(anchor="w", pady=1)
            self.lbl(sadrzaj, ("If you only want to remove some animals, cancel and use normal deletion "
                              "(select the animal and press Delete)." if EN else "Ako želiš da ukloniš samo neka grla, otkaži i koristi obično brisanje "
                              "(označi grlo i pritisni Delete)."), 9, fg=INK2, wraplength=540,
                     justify="left").pack(anchor="w", pady=(14, 0))
            dugmad(("I understand, next  ›" if EN else "Razumem, dalje  ›"))

        def k2():
            self.lbl(sadrzaj, ("Choose what is deleted:" if EN else "Izaberi šta se briše:"), 10, "bold").pack(anchor="w", pady=(0, 8))
            for val, t, opis in (("sve", ("All animals and the whole history" if EN else "Sva grla i cela istorija"),
                                  ("The records become completely empty, like a new program." if EN else "Evidencija postaje potpuno prazna, kao novi program.")),
                                 ("grla", ("Animals only, history is kept" if EN else "Samo grla, istorija ostaje sačuvana"),
                                  ("History records stay in the file but are not shown until the animals are entered again." if EN else "Zapisi iz istorije ostaju u fajlu, ali se ne vide dok se grla ponovo ne upišu."))):
                ttk.Radiobutton(sadrzaj, text=t, value=val, variable=st["istorija"],
                                style="Card.TRadiobutton").pack(anchor="w", pady=(6, 0))
                self.lbl(sadrzaj, opis, 9, fg=INK2).pack(anchor="w", padx=26)
            dugmad()

        def k3():
            self.lbl(sadrzaj, ("Before deleting, the program makes a backup of all data. Everything can be "
                              "restored from it if you change your mind." if EN else "Pre brisanja program pravi rezervnu kopiju svih podataka. Iz nje se sve može "
                              "vratiti ako se predomisliš."), 10, wraplength=540, justify="left").pack(anchor="w")
            if not st["kopija"]:
                try:
                    folder = self.folder_kopija()
                    os.makedirs(folder, exist_ok=True)
                    oznaka = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    kopije = []
                    for izvor in (self.tab.putanja, self.ist.putanja):
                        if os.path.isfile(izvor):
                            ime, ext = os.path.splitext(os.path.basename(izvor))
                            cilj = os.path.join(folder, (f"{ime}_before_delete_{oznaka}{ext}" if EN else f"{ime}_pre_brisanja_{oznaka}{ext}"))
                            shutil.copy2(izvor, cilj)
                            kopije.append((izvor, cilj))
                    st["kopija"] = (folder, kopije)
                except OSError as e:
                    self.napomena(sadrzaj, wraplength=520, tekst=(f"Backup was not made: {e}\nDeletion has been stopped." if EN else f"Rezervna kopija nije napravljena: {e}\nBrisanje je zaustavljeno."))
                    dugmad(("Next  ›" if EN else "Dalje  ›"), stanje="disabled")
                    return
            folder, kopije = st["kopija"]
            self.napomena(sadrzaj, wraplength=520, tekst=("Backup has been made." if EN else "Rezervna kopija je napravljena."), ok=True)
            for _, cilj in kopije:
                self.lbl(sadrzaj, "•  " + os.path.basename(cilj), 10, fg=INK2).pack(anchor="w", pady=1)
            self.lbl(sadrzaj, f"Folder: {folder}", 9, fg=INK2, wraplength=540, justify="left").pack(
                anchor="w", pady=(8, 0))
            lk = self.lbl(sadrzaj, ("Open backup folder" if EN else "Otvori folder sa kopijom"), 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(anchor="w", pady=(6, 0))
            lk.bind("<Button-1>", lambda e: otvori_folder(folder))
            dugmad()

        def k4():
            self.lbl(sadrzaj, ("To confirm, type exactly:" if EN else "Da potvrdiš, upiši tačno reči:"), 10).pack(anchor="w")
            self.lbl(sadrzaj, ("DELETE ALL" if EN else "OBRIŠI SVE"), 18, "bold", fg=BAD).pack(anchor="w", pady=(6, 10))
            e = ttk.Entry(sadrzaj, textvariable=st["tekst"], width=24, font=self.f(13))
            e.pack(anchor="w")
            info = self.lbl(sadrzaj, "", 9, fg=INK2)
            info.pack(anchor="w", pady=(6, 0))
            b = dugmad(stanje="disabled")

            def provera(*_):
                if EN:
                    ok = norm(st["tekst"].get()) == "DELETEALL"
                else:
                    ok = norm(st["tekst"].get()).replace("Š", "S") == "OBRISISVE"
                b.state(["!disabled"] if ok else ["disabled"])
                info.config(text=("Confirmed." if EN else "Potvrđeno.") if ok else ("The \"Next\" button turns on when you type the exact text." if EN else "Dugme „Dalje“ se uključuje kad upišeš tačan tekst."),
                            fg=OK if ok else INK2)
            tr_id = st["tekst"].trace_add("write", provera)
            e.bind("<Destroy>", lambda ev: st["tekst"].trace_remove("write", tr_id))
            provera()
            e.focus_set()

        def k5():
            if st["gotovo"]:
                folder, kopije = st["kopija"]
                self.napomena(sadrzaj, wraplength=520, tekst=("All animals have been deleted." if EN else "Sva grla su obrisana."), ok=True)
                self.lbl(sadrzaj, ("The backup is saved in the folder:" if EN else "Rezervna kopija je sačuvana u folderu:"), 10).pack(anchor="w")
                self.lbl(sadrzaj, folder, 9, fg=INK2, wraplength=540, justify="left").pack(anchor="w", pady=(2, 10))
                self.lbl(sadrzaj, ("If this was a mistake, click \"Restore data\" – everything will be as before." if EN else "Ako je ovo bila greška, klikni „Vrati podatke“ – sve će biti kao pre brisanja."),
                         9, fg=INK2, wraplength=540, justify="left").pack(anchor="w")
                self.btn(dno, ("Restore data" if EN else "Vrati podatke"), vrati).pack(side="left")
                self.btn(dno, ("Close" if EN else "Zatvori"), win.destroy, "Primary").pack(side="right")
                return
            sta = ("all animals and the whole history" if EN else "sva grla i celu istoriju") if st["istorija"].get() == "sve" else ("all animals (history is kept)" if EN else "sva grla (istorija ostaje)")
            self.lbl(sadrzaj, (f"Last step. Clicking the button deletes {sta}." if EN else f"Poslednji korak. Klikom na dugme briše se {sta}."), 11, "bold",
                     wraplength=540, justify="left").pack(anchor="w")
            self.lbl(sadrzaj, (f"Number of animals: {n_grla}" if EN else f"Broj grla: {n_grla}") + ((f"   ·   history records: {n_ist}" if EN else f"   ·   zapisa istorije: {n_ist}")
                                                          if st["istorija"].get() == "sve" else ""),
                     10, fg=INK2).pack(anchor="w", pady=(6, 0))
            odb = self.lbl(sadrzaj, "", 10, "bold", fg=WARN)
            odb.pack(anchor="w", pady=(16, 0))
            b = dugmad(("Permanently delete all" if EN else "Trajno obriši sve"), obrisi_sve, "Danger", stanje="disabled")
            st["odbrojavanje"] = 5

            def tik():
                if not odb.winfo_exists():
                    return
                if st["odbrojavanje"] > 0:
                    odb.config(text=(f"The button turns on in {st['odbrojavanje']} s…" if EN else f"Dugme se uključuje za {st['odbrojavanje']} s…"))
                    st["odbrojavanje"] -= 1
                    win.after(1000, tik)
                else:
                    odb.config(text=("You can confirm the deletion." if EN else "Možeš potvrditi brisanje."), fg=BAD)
                    b.state(["!disabled"])
            tik()

        def otvori_folder(folder):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}" &')
            except OSError:
                pass

        def zatvori_prozore():
            for w in (self.karton_win, getattr(self, "ist_win", None), getattr(self, "stablo_win", None)):
                if w is not None and w.winfo_exists():
                    w.destroy()
            self.ui.update(partner="", partner_upit="", partner_vise=[], sA="", sB="")

        def obrisi_sve():
            zatvori_prozore()
            self.tab.redovi = []
            if st["istorija"].get() == "sve":
                self.ist.zapisi = []
            self.promena((f"Deleted all {n_grla} animals." if EN else f"Obrisano svih {n_grla} grla."))
            st["gotovo"] = True
            nacrtaj()

        def vrati():
            folder, kopije = st["kopija"]
            try:
                for izvor, cilj in kopije:
                    shutil.copy2(cilj, izvor)
                self.tab.ucitaj()
                self.ist = Istorija(self.tab.putanja)
                self.pods = Podsetnici(self.tab.putanja)
            except Exception as e:
                messagebox.showerror(("Restore failed" if EN else "Vraćanje nije uspelo"), str(e), parent=win)
                return
            self.model = Model(self.tab.redovi)
            self.prikazi(self.strana)
            self.toast((f"Restored {len(self.tab.redovi)} animals from the backup." if EN else f"Vraćeno {len(self.tab.redovi)} grla iz rezervne kopije."))
            win.destroy()

        win.bind("<Escape>", lambda e: win.destroy())
        nacrtaj()
        win.update_idletasks()
        win.geometry(f"+{self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2}"
                     f"+{self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 3)}")


    def obrisi_grla(self, ids, parent=None):
        ids = [i for i in ids if self.red_za(i) and self.red_za(i).get("status") != "obrisano"]
        if not ids:
            return False
        naziv = ids[0] if len(ids) == 1 else (f"{len(ids)} animals ({', '.join(ids[:5])}{'…' if len(ids) > 5 else ''})" if EN else f"{len(ids)} grla ({', '.join(ids[:5])}{'…' if len(ids) > 5 else ''})")
        if not messagebox.askyesno(
                ("Delete animal" if EN else "Obriši grlo"), (f"Delete {naziv}?\n\n"
                "The animal disappears from the list and all searches, but stays in the pedigree, "
                "so that the relationships of its offspring stay correct.\n\n"
                "You can restore it on the \"Deleted animals\" page." if EN else f"Obrisati {naziv}?\n\n"
                "Grlo nestaje iz liste i iz svih pretraga, ali ostaje zapamćeno u rodoslovu, "
                "da bi srodstvo njegovih potomaka bilo tačno.\n\n"
                "Možeš ga vratiti na strani „Obrisana grla“."), parent=parent or self.root):
            return False
        for i in ids:
            self.red_za(i)["status"] = "obrisano"
            self.ist.dodaj(i, AUTO, ("Animal deleted from the list (kept in the pedigree)" if EN else "Grlo obrisano iz liste (ostaje u rodoslovu)"), automatski=True)
        if self.karton_win and self.karton_win.winfo_exists() and getattr(self.karton_win, "grlo", None) in ids:
            self.karton_win.destroy()
        if self.ui.get("partner") in ids:
            self.ui.update(partner="", partner_upit="")
        self.promena((f"Deleted: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}" if EN else f"Obrisano: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}"))
        return True


    def vrati_grla(self, ids):
        for i in ids:
            r = self.red_za(i)
            if r:
                r["status"] = "aktivno"
                self.ist.dodaj(i, AUTO, ("Animal restored to the herd" if EN else "Grlo vraćeno u stado"), automatski=True)
        self.promena((f"Restored to herd: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}" if EN else f"Vraćeno u stado: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}"))


    def trajno_obrisi(self, ids):
        m = self.model
        pot = sorted({k for k, pr in m.P.items() for i in ids if i in pr and k not in ids}, key=sort_key)
        upoz = ((f"\n\nWarning: {', '.join(pot[:6])}{'…' if len(pot) > 6 else ''} has/have this animal as a parent. "
                "Their ancestors through this animal will be lost and the relationships will be wrong." if EN else f"\n\nPažnja: {', '.join(pot[:6])}{'…' if len(pot) > 6 else ''} ima(ju) ovo grlo kao roditelja. "
                "Njihovi preci preko ovog grla biće izgubljeni i srodstvo će biti netačno.")
                if pot else "")
        if not messagebox.askyesno(("Permanent deletion" if EN else "Trajno brisanje"), (f"Permanently delete {', '.join(ids[:5])}"
                                   f"{'…' if len(ids) > 5 else ''}? This cannot be undone.{upoz}" if EN else f"Trajno obrisati {', '.join(ids[:5])}"
                                   f"{'…' if len(ids) > 5 else ''}? Ovo se ne može poništiti.{upoz}"),
                                   icon="warning"):
            return
        self.tab.redovi = [r for r in self.tab.redovi if r["id"] not in ids]
        self.promena((f"Permanently deleted: {len(ids)} animals" if EN else f"Trajno obrisano: {len(ids)} grla"))


    def meni_grla(self, tv, ev):
        iid = tv.identify_row(ev.y)
        if not iid or iid not in self.model.A:
            return
        if iid not in tv.selection():
            tv.selection_set(iid)
        sel = [i for i in tv.selection() if i in self.model.A]
        mn = tk.Menu(self.root, tearoff=0, font=self.f(10), bg=SURF, fg=INK, activebackground=SURF2,
                     activeforeground=INK, bd=0)
        if len(sel) == 1:
            mn.add_command(label=("Open card" if EN else "Otvori karton"), command=lambda: self.karton(iid))
            mn.add_command(label=("Edit details" if EN else "Izmeni podatke"), command=lambda: self.forma(iid))
            mn.add_command(label=("Change ear tag" if EN else "Promeni ušnu markicu"), command=lambda: self.promena_markice(iid))
            mn.add_command(label=("Partner search" if EN else "Pretraga partnera"), command=lambda: self.idi_na_pretragu(iid))
            mn.add_command(label=("Pedigree (family tree)" if EN else "Poreklo (rodoslovno stablo)"), command=lambda: self.stablo(iid))
            mn.add_command(label=("Animal history (details and entry)" if EN else "Istorija grla (podaci i unos)"), command=lambda: self.istorija_prozor(iid))
            mn.add_command(label=("Add event…" if EN else "Dodaj događaj…"), command=lambda: self.dogadjaj_forma(iid))
            mn.add_command(label=("Add reminder…" if EN else "Dodaj podsetnik…"), command=lambda: self.podsetnik_forma(iid))
            mn.add_separator()
        mn.add_command(label=(f"Move to another herd{'' if len(sel) == 1 else f' ({len(sel)} animals)'}…" if EN else f"Premesti u drugo stado{'' if len(sel) == 1 else f' ({len(sel)} grla)'}…"),
                       command=lambda: self.promena_stada(sel))
        st_ = self.model.A[iid]["stado"]
        if st_:
            mn.add_command(label=(f"Rename herd \"{st_}\"…" if EN else f"Preimenuj stado „{st_}“…"), command=lambda: self.preimenuj_stado(st_))
        mn.add_command(label=(f"Export{'' if len(sel) == 1 else f' ({len(sel)} animals)'}…" if EN else f"Izvezi{'' if len(sel) == 1 else f' ({len(sel)} grla)'}…"),
                       command=lambda: self.izvezi(oznacena=sel))
        mn.add_separator()
        mn.add_command(label=(f"Delete{'' if len(sel) == 1 else f' ({len(sel)} animals)'}" if EN else f"Obriši{'' if len(sel) == 1 else f' ({len(sel)} grla)'}"),
                       foreground=BAD, command=lambda: self.obrisi_grla(sel))
        try:
            mn.tk_popup(ev.x_root, ev.y_root)
        finally:
            mn.grab_release()


    def s_obrisana(self):
        body = self.strana_okvir(scroll=False)
        m = self.model
        obr = m.obrisana()
        self.zaglavlje(body, ("Deleted animals" if EN else "Obrisana grla"),
                       ("These animals are not shown in the list or searches, but stay in the pedigree so that the relationships "
                       "of their offspring stay correct." if EN else "Ova grla se ne vide u listi ni u pretragama, ali ostaju u rodoslovu da bi srodstvo "
                       "njihovih potomaka bilo tačno."),
                       [(("← Back to animals" if EN else "← Nazad na grla"), lambda: self.prikazi("grla"), "Secondary")])
        if not obr:
            self.napomena(body, ("There are no deleted animals." if EN else "Nema obrisanih grla."), ok=True)
            return
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        wrap, tv = self.tabela(body, [("id", ("Animal" if EN else "Grlo"), 105), ("markica", ("Ear tag" if EN else "Markica"), 125), ("pol", ("Sex" if EN else "Pol"), 70),
                                      ("rasa", ("Breed" if EN else "Rasa"), 130), ("stado", ("Herd" if EN else "Stado"), 90),
                                      ("pot", ("Offspring in pedigree" if EN else "Potomaka u rodoslovu"), 150, "e")], visina=14)
        for i, a in enumerate(obr):
            n = sum(1 for pr in m.P.values() if a["id"] in pr)
            tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag_siv,
                      values=(a["markica"] or "–", m.pol_naziv(a["id"]), a["rasa"] or "–", a["stado"] or "–", n),
                      tags=["odd"] if i % 2 else [])
        izbor = lambda: [i for i in tv.selection() if i in m.A]
        def vrati():
            s_ = izbor()
            if s_:
                self.vrati_grla(s_)
            else:
                self.toast(("First select an animal in the table." if EN else "Prvo označi grlo u tabeli."))
        def trajno():
            s_ = izbor()
            if s_:
                self.trajno_obrisi(s_)
            else:
                self.toast(("First select an animal in the table." if EN else "Prvo označi grlo u tabeli."))
        self.btn(tb, ("Restore to herd" if EN else "Vrati u stado"), vrati, "Primary").pack(side="left")
        self.btn(tb, ("Delete permanently" if EN else "Trajno obriši"), trajno, "Danger").pack(side="left", padx=8)
        self.lbl(tb, ("Select an animal (or several with Ctrl), then choose an action." if EN else "Označi grlo (ili više uz Ctrl) pa izaberi radnju."), 9, fg=INK2).pack(side="left", padx=8)
        wrap.pack(fill="both", expand=True)
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
