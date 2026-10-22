"""Strane 'Parenje', 'Srodstvo' i 'Pregled': najbolji partneri, plan parenja, srodstvo dva grla, pregled stada."""
import tkinter as tk
from tkinter import ttk

from osnova import EN
from jezik import T
from podaci import fmt_starost, nazivi, norm, pct, sort_key, starost_meseci
from izgled import BAD, BG, INK, INK2, OK, SURF, SURF2, WARN
from rodoslov import procena


class ParenjeEkran:
    """Strane 'Parenje', 'Srodstvo' i 'Pregled': najbolji partneri, plan parenja, srodstvo dva grla, pregled stada."""


    # ---------- Parenje
    def s_parenje(self):
        body = self.strana_okvir()
        self.zaglavlje(body, ("Mating" if EN else "Parenje"), ("The program chooses partners so that the offspring have as little inbreeding as possible. "
                                            f"The risk limit is {pct(self.prag)} (changed on the Overview page)." if EN else "Program bira partnere tako da potomstvo ima što manji inbriding. "
                                            f"Granica rizika je {pct(self.prag)} (menja se na strani Pregled)."))
        segw = tk.Frame(body, bg=BG)
        segw.pack(fill="x", pady=(0, 16))
        seg = tk.Frame(segw, bg=SURF2)
        seg.pack(side="left")
        for k, t in (("partner", ("Partner search" if EN else "Pretraga partnera")), ("plan", ("Plan for the whole herd" if EN else "Plan za celo stado"))):
            akt = self.ui["par_tab"] == k
            b = tk.Label(seg, text=t, font=self.f(10, "bold"), bg=SURF if akt else SURF2, fg=INK if akt else INK2,
                         padx=14, pady=7, cursor="hand2")
            b.pack(side="left", padx=3, pady=3)
            b.bind("<Button-1>", lambda e, k=k: (self.ui.update(par_tab=k), self.prikazi("parenje")))
        if not self.model.grla():
            self.prazno(body)
            return
        (self.partner_view if self.ui["par_tab"] == "partner" else self.plan_view)(body)


    def opis_grla(self, a):
        return f"{a['id']}" + (f"  ·  {a['markica']}" if a["markica"] else "") + f"  ({self.model.pol_naziv(a['id'])})"


    def partner_view(self, body):
        m = self.model
        akt = m.grla(True)
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, ("Partner search" if EN else "Pretraga partnera"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("Type the tag or ear tag of an animal and press Enter. The program finds partners of the opposite sex, "
                    "with the least related ones at the top." if EN else "Upiši oznaku ili ušnu markicu grla i pritisni Enter. Program nalazi partnere suprotnog pola, "
                    "a na vrhu su oni sa najmanjim srodstvom."), 9, fg=INK2, wraplength=760,
                 justify="left").pack(anchor="w", pady=(2, 10))
        row = tk.Frame(c, bg=SURF)
        row.pack(fill="x")
        var = tk.StringVar(value=self.ui.get("partner_upit", self.ui["partner"]))
        svi_opisi = [self.opis_grla(g) for g in akt]
        e = ttk.Combobox(row, textvariable=var, values=svi_opisi, width=34, font=self.f(11))
        e.pack(side="left")
        ph = self.lbl(row, ("e.g. K12 or UK 123456 700123" if EN else "npr. K12 ili RS 1234-5678"), 10, fg="#98A39B", bg=SURF)

        def ph_show(*_):
            if var.get():
                ph.place_forget()
            else:
                ph.place(in_=e, x=10, rely=0.5, anchor="w")
        ph.bind("<Button-1>", lambda ev: e.focus_set())
        ph_show()

        def suzi(ev=None):
            # dok kucas, padajuci spisak prikazuje samo grla koja odgovaraju
            if ev is not None and ev.keysym in ("Return", "KP_Enter", "Down", "Up", "Escape"):
                return
            q = norm(var.get())
            e.configure(values=[d for g, d in zip(akt, svi_opisi)
                                if not q or q in norm(g["id"]) or q in norm(g["markica"])
                                or any(q in norm(x) for x in g["stare"])])
            ph_show()

        def trazi(ev=None):
            upit = var.get().strip()
            if "  ·  " in upit or "  (" in upit:          # izabrano sa spiska
                upit = upit.split("  ")[0]
            self.ui["partner_upit"] = upit
            self.ui["partner"] = ""
            self.ui["partner_vise"] = []
            self.ui["partner_obrisano"] = ""
            if upit:
                x = m.nadji(upit)
                if x and m.A[x].get("obrisano"):
                    self.ui["partner_obrisano"] = x
                elif x and not m.A[x]["osnivac"]:
                    self.ui["partner"] = x
                    self.ui["partner_upit"] = x
                else:
                    q = norm(upit)
                    pogodci = [g["id"] for g in m.grla() if q in norm(g["id"]) or q in norm(g["markica"])
                               or any(q in norm(x) for x in g["stare"])]
                    if len(pogodci) == 1:
                        self.ui["partner"] = self.ui["partner_upit"] = pogodci[0]
                    else:
                        self.ui["partner_vise"] = pogodci[:30]
            self.prikazi("parenje")

        e.bind("<KeyRelease>", suzi)
        e.bind("<Return>", trazi)
        e.bind("<KP_Enter>", trazi)
        e.bind("<<ComboboxSelected>>", trazi)
        self.btn(row, ("Find partners" if EN else "Pronađi partnere"), trazi, "Primary").pack(side="left", padx=10)
        row2 = tk.Frame(c, bg=SURF)
        row2.pack(fill="x", pady=(10, 0))
        rv = tk.BooleanVar(value=self.ui["ista_rasa"])
        ttk.Checkbutton(row2, text=("Same breed only" if EN else "Samo ista rasa"), variable=rv, style="Card.TCheckbutton",
                        command=lambda: (self.ui.update(ista_rasa=rv.get()), self.prikazi("parenje"))).pack(
            side="left")
        uv = tk.BooleanVar(value=self.ui.get("partner_svi", False))
        ttk.Checkbutton(row2, text=("Include animals out of herd" if EN else "Uključi i grla van zapata"), variable=uv, style="Card.TCheckbutton",
                        command=lambda: (self.ui.update(partner_svi=uv.get()), self.prikazi("parenje"))).pack(
            side="left", padx=18)
        if not self.ui["partner"]:
            e.focus_set()

        x = self.ui["partner"]
        upit = self.ui.get("partner_upit", "")
        if not x:
            vise = self.ui.get("partner_vise", [])
            if upit and vise:
                tk.Frame(c, bg=SURF, height=12).pack()
                self.lbl(c, (f"Several animals match \"{upit}\". Choose one:" if EN else f"Više grla odgovara upitu „{upit}“. Izaberi jedno:"), 10, fg=INK2).pack(anchor="w")
                ch = tk.Frame(c, bg=SURF)
                ch.pack(anchor="w", pady=(6, 0))
                for i, g in enumerate(vise):
                    if i and i % 8 == 0:
                        ch = tk.Frame(c, bg=SURF)
                        ch.pack(anchor="w", pady=(4, 0))
                    self.cip(ch, g, lambda g=g: (self.ui.update(partner=g, partner_upit=g, partner_vise=[]),
                                                  self.prikazi("parenje"))).pack(side="left", padx=(0, 6))
            elif upit and self.ui.get("partner_obrisano"):
                tk.Frame(c, bg=SURF, height=12).pack()
                self.napomena(c, (f"Animal {self.ui['partner_obrisano']} is deleted. You can restore it on the page "
                                 "Animals → Deleted animals." if EN else f"Grlo {self.ui['partner_obrisano']} je obrisano. Možeš ga vratiti na strani "
                                 "Grla → Obrisana grla."))
            elif upit:
                tk.Frame(c, bg=SURF, height=12).pack()
                self.napomena(c, (f"Animal \"{upit}\" was not found by tag or ear tag." if EN else f"Grlo „{upit}“ nije pronađeno ni po oznaci ni po ušnoj markici."))
            return
        if x not in m.A or m.A[x]["osnivac"]:
            return
        a = m.A[x]
        if not a["pol"]:
            tk.Frame(body, bg=BG, height=16).pack()
            self.napomena(body, (f"Animal {x} has no sex entered. Enter the sex in the animal card and try again." if EN else f"Grlu {x} nije upisan pol. Upiši pol u kartonu grla pa pokušaj ponovo."))
            return

        # izabrano grlo
        tk.Frame(body, bg=BG, height=16).pack()
        o, c2 = self.card(body, 20, 14)
        o.pack(fill="x")
        top = tk.Frame(c2, bg=SURF)
        top.pack(fill="x")
        self.cip(top, x, lambda: self.karton(x), big=True).pack(side="left")
        t = tk.Frame(top, bg=SURF)
        t.pack(side="left", padx=14)
        self.lbl(t, f"{m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}", 12, "bold").pack(anchor="w")
        o_, mj = m.P[x]
        self.lbl(t, (f"ear tag {a['markica'] or '–'}   ·   sire {o_ or '–'}   ·   dam {mj or '–'}"
                    f"   ·   inbreeding {pct(m.inbr(x))}" if EN else f"markica {a['markica'] or '–'}   ·   otac {o_ or '–'}   ·   majka {mj or '–'}"
                    f"   ·   inbriding {pct(m.inbr(x))}"), 9, fg=INK2).pack(anchor="w")

        izvor = m.grla(not self.ui.get("partner_svi", False))
        kand = [(m.kinship(x, k["id"]), m.r(x, k["id"]), k) for k in izvor
                if k["id"] != x and k["vrsta"] == a["vrsta"] and k["pol"] and k["pol"] != a["pol"]
                and (not self.ui["ista_rasa"] or k["rasa"] == a["rasa"])]
        kand.sort(key=lambda t: (t[0], t[1], sort_key(t[2]["id"])))   # najmanje srodni na vrhu
        tk.Frame(body, bg=BG, height=16).pack()
        suprotni = ("female" if EN else "ženskih") if a["pol"] == "m" else ("male" if EN else "muških")
        if not kand:
            self.napomena(body, (f"There are no {suprotni} animals of the same species" if EN else f"Nema {suprotni} grla iste vrste") +
                          ((" and breed" if EN else " i rase") if self.ui["ista_rasa"] else "") + (" in the herd." if EN else " u zapatu."))
            return
        nesrodni = sum(1 for f, r, k in kand if f == 0)
        dobri = sum(1 for f, r, k in kand if f <= self.prag)
        if kand[0][0] > self.prag:
            self.napomena(body, (f"No partner in the herd is below the limit of {pct(self.prag)}. "
                                "Consider buying an unrelated animal or semen." if EN else f"Ni jedan partner u stadu nije ispod granice od {pct(self.prag)}. "
                                "Razmisli o nabavci nesrodnog grla ili semena."))
        else:
            self.napomena(body, (f"Found {len(kand)} {suprotni} animals: {nesrodni} completely unrelated, "
                                f"{dobri} below the limit of {pct(self.prag)}. The best choice is at the top." if EN else f"Pronađeno {len(kand)} {suprotni} grla: {nesrodni} potpuno nesrodnih, "
                                f"{dobri} ispod granice od {pct(self.prag)}. Najbolji izbor je na vrhu."), ok=True)
        if EN:
            pass
        else:
            mlad = nazivi(a["vrsta"])[3]
        wrap, tv = self.tabela(body, [("id", "Partner", 100), ("mk", ("Ear tag" if EN else "Markica"), 115), ("rasa", ("Breed" if EN else "Rasa"), 90),
                                      ("st", ("Age" if EN else "Starost"), 80), ("odnos", ("Relation" if EN else "Odnos"), 130), ("r", ("Shared genes" if EN else "Zajednički geni"), 125, "e"),
                                      ("f", ("Offspring F" if EN else f"Inbriding za {mlad}"), 125, "e"), ("pr", ("Rating" if EN else "Procena"), 150)],
                               visina=min(len(kand), 14))
        wrap.pack(fill="x")
        for i, (f, r, k) in enumerate(kand):
            t, boja = procena(f, self.prag)
            tv.insert("", "end", iid=k["id"], text=f"  {i + 1}.  {k['id']}", image=self.img_tag,
                      values=(k["markica"] or "–", k["rasa"] or "–", fmt_starost(starost_meseci(k["datum"])) or "–",
                              m.odnos(x, k["id"]), pct(r), pct(f), t),
                      tags=(["odd"] if i % 2 else []) + [{OK: "", WARN: "warn", BAD: "bad"}[boja]]
                           + ([] if k["aktivno"] else ["off"]))
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Double-click a partner to open its card.  Shared genes = the share of genes two animals "
                       "have from the same ancestors (parent and offspring or full sibling ≈ 50%, half sibling ≈ 25%, "
                       "unrelated 0%)." if EN else "Dvoklik na partnera otvara njegov karton.  Zajednički geni = koliki deo gena dva grla "
                       "imaju od istih predaka (roditelj i potomak ili pun brat/sestra ≈ 50%, polubrat ≈ 25%, "
                       "nesrodni 0%)."), 9, fg=INK2, wraplength=900, justify="left").pack(anchor="w", pady=(8, 0))


    def plan_view(self, body):
        m = self.model
        akt = m.grla(True)
        o, c = self.card(body)
        o.pack(fill="x")
        row = tk.Frame(c, bg=SURF)
        row.pack(fill="x")
        self.btn(row, T("🖨 Štampaj plan", "🖨 Print plan"), self.stampaj_plan).pack(side="right")
        self.lbl(row, ("Max. females per male:" if EN else "Najviše ženki po mužjaku:"), 10, "bold", fg=INK2).pack(side="left")
        mv = tk.StringVar(value=str(self.ui["plan_max"] or ""))
        sp = ttk.Spinbox(row, from_=0, to=999, textvariable=mv, width=6, font=self.f(10))
        sp.pack(side="left", padx=8)
        self.lbl(row, ("(empty = no limit)" if EN else "(prazno = bez ograničenja)"), 9, fg=INK2).pack(side="left")
        rv = tk.BooleanVar(value=self.ui["ista_rasa"])
        ttk.Checkbutton(row, text=("Same breed only" if EN else "Samo ista rasa"), variable=rv, style="Card.TCheckbutton",
                        command=lambda: (self.ui.update(ista_rasa=rv.get()), self.prikazi("parenje"))).pack(
            side="left", padx=18)

        def prim(*_):
            try:
                self.ui["plan_max"] = max(0, int(mv.get() or 0))
            except ValueError:
                self.ui["plan_max"] = 0
            self.prikazi("parenje")
        sp.config(command=prim)
        sp.bind("<Return>", prim)
        sp.bind("<FocusOut>", lambda e: str(self.ui["plan_max"] or "") != mv.get() and prim())
        tk.Frame(body, bg=BG, height=16).pack()

        zenke = [a for a in akt if a["pol"] == "z"]
        muz = [a for a in akt if a["pol"] == "m"]
        if not zenke or not muz:
            self.napomena(body, (f"The plan needs both female and male animals in the herd "
                                f"(now: {len(zenke)} female, {len(muz)} male)." if EN else f"Za plan su potrebna i ženska i muška grla u zapatu "
                                f"(sada: {len(zenke)} ženskih, {len(muz)} muških)."))
            return
        mx = self.ui["plan_max"]
        opc = {z["id"]: sorted((m.kinship(z["id"], x["id"]), x["id"]) for x in muz
                               if x["vrsta"] == z["vrsta"] and (not self.ui["ista_rasa"] or x["rasa"] == z["rasa"]))
               for z in zenke}
        kor = {x["id"]: 0 for x in muz}
        plan = []
        def tez(z):
            l = opc[z["id"]]
            return (sum(1 for f, _ in l if f <= self.prag), l[0][0] if l else 1)
        for z in sorted(zenke, key=tez):
            izbor = None
            for f, x in opc[z["id"]]:
                if mx and kor[x] >= mx:
                    continue
                kand = [(kor[x2], sort_key(x2), x2) for f2, x2 in opc[z["id"]]
                        if abs(f2 - f) < 1e-12 and not (mx and kor[x2] >= mx)]
                izbor = (f, min(kand)[2])
                break
            if izbor:
                kor[izbor[1]] += 1
            plan.append((z["id"], izbor[1] if izbor else None, izbor[0] if izbor else None))
        plan.sort(key=lambda t: sort_key(t[0]))
        fs = [f for _, x, f in plan if x]
        prob = sum(1 for _, x, f in plan if not x or f > self.prag)

        st = tk.Frame(body, bg=BG)
        st.pack(fill="x", pady=(0, 14))
        for i, (b, t, boja) in enumerate(((str(len(zenke)), ("female animals" if EN else "ženskih grla"), INK), (str(len(muz)), ("male animals" if EN else "muških grla"), INK),
                                          (pct(sum(fs) / len(fs)) if fs else "–", ("average inbreeding of offspring" if EN else "prosečan inbriding potomstva"), INK),
                                          (str(prob), ("matings above the limit" if EN else "parenja iznad granice"), BAD if prob else OK))):
            self.stat(st, b, t, boja).grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            st.columnconfigure(i, weight=1, uniform="s")
        if prob:
            self.napomena(body, (f"{prob} matings are above the limit or without a partner. "
                                "Consider buying a new unrelated male or semen." if EN else f"{prob} parenja je iznad granice ili bez partnera. "
                                "Razmisli o nabavci novog nesrodnog muškog grla ili semena."))
        wrap, tv = self.tabela(body, [("z", ("Female" if EN else "Ženka"), 120), ("rasa", ("Breed" if EN else "Rasa"), 120), ("stado", ("Herd" if EN else "Stado"), 90),
                                      ("x", "Partner", 110), ("rx", ("Partner breed" if EN else "Rasa partnera"), 120),
                                      ("f", ("Offspring inbreeding" if EN else "Inbriding potomka"), 150, "e"), ("pr", ("Rating" if EN else "Procena"), 150)],
                               visina=min(len(plan), 14))
        wrap.pack(fill="x")
        for i, (z, x, f) in enumerate(plan):
            a = m.A[z]
            if x:
                t, boja = procena(f, self.prag)
                tag = {OK: "", WARN: "warn", BAD: "bad"}[boja]
            else:
                t, tag = ("no free partner" if EN else "nema slobodnog partnera"), "bad"
            tv.insert("", "end", iid=z, text="  " + z, image=self.img_tag,
                      values=(a["rasa"] or "–", a["stado"] or "–", x or "–", m.A[x]["rasa"] if x else "",
                              pct(f) if x else "", t), tags=(["odd"] if i % 2 else []) + [tag])
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))

        tk.Frame(body, bg=BG, height=16).pack()
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, ("Load on males" if EN else "Opterećenje muških grla"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("How many females are assigned to each male in this plan." if EN else "Koliko ženki je dodeljeno svakom mužjaku u ovom planu."), 9, fg=INK2).pack(anchor="w", pady=(0, 10))
        if EN:
            for x in sorted(muz, key=lambda a: -kor[a["id"]]):
                r = tk.Frame(c, bg=SURF)
                r.pack(fill="x", pady=4)
                self.cip(r, x["id"], lambda i=x["id"]: self.karton(i)).pack(side="left")
                self.lbl(r, x["rasa"], 9, fg=INK2, width=14, anchor="w").pack(side="left", padx=8)
                n = kor[x["id"]]
                self.lbl(r, f"{n} " + ("female" if n == 1 else "females"), 10, "bold",
                         width=10, anchor="e").pack(side="right")
                pb = ttk.Progressbar(r, style="Green.Horizontal.TProgressbar", maximum=len(zenke), value=n)
                pb.pack(side="left", fill="x", expand=True, padx=8)
        else:
            for x in sorted(muz, key=lambda a: -kor[a["id"]]):
                r = tk.Frame(c, bg=SURF)
                r.pack(fill="x", pady=4)
                self.cip(r, x["id"], lambda i=x["id"]: self.karton(i)).pack(side="left")
                self.lbl(r, x["rasa"], 9, fg=INK2, width=14, anchor="w").pack(side="left", padx=8)
                n = kor[x["id"]]
                self.lbl(r, f"{n} " + ("ženka" if n == 1 else "ženke" if 2 <= n <= 4 else "ženki"), 10, "bold",
                         width=10, anchor="e").pack(side="right")
                pb = ttk.Progressbar(r, style="Green.Horizontal.TProgressbar", maximum=len(zenke), value=n)
                pb.pack(side="left", fill="x", expand=True, padx=8)


    # ---------- Srodstvo
    def s_srodstvo(self):
        body = self.strana_okvir()
        self.zaglavlje(body, ("Relationship" if EN else "Srodstvo"), ("Choose two animals and see how related they are and what their offspring would be like." if EN else "Izaberi dva grla i vidi koliko su srodna i kakvo bi bilo njihovo potomstvo."))
        m = self.model
        sva = m.grla()
        if not sva:
            self.prazno(body)
            return
        opisi = [self.opis_grla(a) for a in sva]
        o, c = self.card(body)
        o.pack(fill="x")
        row = tk.Frame(c, bg=SURF)
        row.pack(fill="x")
        vars_ = {}
        for i, (k, t) in enumerate((("sA", ("First animal" if EN else "Prvo grlo")), ("sB", ("Second animal" if EN else "Drugo grlo")))):
            f = tk.Frame(row, bg=SURF)
            f.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 16, 0))
            row.columnconfigure(i, weight=1)
            self.lbl(f, t, 10, "bold", fg=INK2).pack(anchor="w")
            v = tk.StringVar(value=next((d for a, d in zip(sva, opisi) if a["id"] == self.ui[k]), ""))
            cb = ttk.Combobox(f, textvariable=v, values=opisi, state="readonly", font=self.f(10))
            cb.pack(fill="x", pady=(6, 0))
            cb.bind("<<ComboboxSelected>>",
                    lambda e, k=k, v=v: (self.ui.update({k: sva[opisi.index(v.get())]["id"]}), self.prikazi("srodstvo")))
            vars_[k] = v
        a, b = self.ui["sA"], self.ui["sB"]
        if EN:
            if a in m.A and b in m.A and a != b:
                A, B = m.A[a], m.A[b]
                if A["vrsta"] != B["vrsta"]:
                    tk.Frame(c, bg=SURF, height=14).pack()
                    self.napomena(c, f"{a} is {A['vrsta']}, and {b} is {B['vrsta']} – different species.")
                else:
                    f, r = m.kinship(a, b), m.r(a, b)
                    v = tk.Frame(c, bg=SURF)
                    v.pack(fill="x", pady=(18, 0))
                    t, boja = procena(f, self.prag)
                    for i, (big, small, col) in enumerate(((pct(r), f"shared genes (r = {r:.3f})", INK),
                                                           (m.odnos(a, b), "odnos", INK),
                                                           (pct(f), f"inbreeding of the {nazivi(A['vrsta'])[2]}", boja))):
                        fr = tk.Frame(v, bg=SURF2)
                        fr.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
                        v.columnconfigure(i, weight=1, uniform="v")
                        self.lbl(fr, big, 22 if i != 1 else 15, "bold", fg=col).pack(anchor="w", padx=16, pady=(12, 0))
                        self.lbl(fr, small, 9, fg=INK2).pack(anchor="w", padx=16, pady=(0, 12 if i != 2 else 4))
                        if i == 2:
                            self.badge(fr, t, boja).pack(anchor="w", padx=16, pady=(0, 12))
                    self.lbl(c, "Common ancestors", 10, "bold").pack(anchor="w", pady=(16, 6))
                    zaj = sorted((m.preci(a) | {a}) & (m.preci(b) | {b}), key=sort_key)
                    ch = tk.Frame(c, bg=SURF)
                    ch.pack(anchor="w")
                    if zaj:
                        for z in zaj:
                            self.cip(ch, z, lambda z=z: self.karton(z), siv=m.A[z]["osnivac"]).pack(side="left", padx=(0, 6))
                    else:
                        self.lbl(ch, "no known common ancestors", 10, fg=INK2).pack(side="left")
        else:
            if a in m.A and b in m.A and a != b:
                A, B = m.A[a], m.A[b]
                if A["vrsta"] != B["vrsta"]:
                    tk.Frame(c, bg=SURF, height=14).pack()
                    self.napomena(c, f"{a} je {A['vrsta']}, a {b} {B['vrsta']} – različite vrste.")
                else:
                    f, r = m.kinship(a, b), m.r(a, b)
                    v = tk.Frame(c, bg=SURF)
                    v.pack(fill="x", pady=(18, 0))
                    t, boja = procena(f, self.prag)
                    for i, (big, small, col) in enumerate(((pct(r), f"zajedničkih gena (r = {r:.3f})".replace(".", ","), INK),
                                                           (m.odnos(a, b), "odnos", INK),
                                                           (pct(f), f"inbriding {nazivi(A['vrsta'])[2]}ta", boja))):
                        fr = tk.Frame(v, bg=SURF2)
                        fr.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
                        v.columnconfigure(i, weight=1, uniform="v")
                        self.lbl(fr, big, 22 if i != 1 else 15, "bold", fg=col).pack(anchor="w", padx=16, pady=(12, 0))
                        self.lbl(fr, small, 9, fg=INK2).pack(anchor="w", padx=16, pady=(0, 12 if i != 2 else 4))
                        if i == 2:
                            self.badge(fr, t, boja).pack(anchor="w", padx=16, pady=(0, 12))
                    self.lbl(c, "Zajednički preci", 10, "bold").pack(anchor="w", pady=(16, 6))
                    zaj = sorted((m.preci(a) | {a}) & (m.preci(b) | {b}), key=sort_key)
                    ch = tk.Frame(c, bg=SURF)
                    ch.pack(anchor="w")
                    if zaj:
                        for z in zaj:
                            self.cip(ch, z, lambda z=z: self.karton(z), siv=m.A[z]["osnivac"]).pack(side="left", padx=(0, 6))
                    else:
                        self.lbl(ch, "nema poznatih zajedničkih predaka", 10, fg=INK2).pack(side="left")

        tk.Frame(body, bg=BG, height=16).pack()
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, ("Most related pairs in the herd" if EN else "Najsrodniji parovi u zapatu"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("Animals that should be kept apart when mating." if EN else "Grla koja treba držati odvojeno pri parenju."), 9, fg=INK2).pack(anchor="w", pady=(0, 10))
        akt = m.grla(True)
        kes = getattr(self, "_kes_parovi", None)
        if kes and kes[0] is m:                      # isti podaci – ne računa se ponovo
            parovi = list(kes[1])
        elif len(akt) > 1500:                        # veliko stado: računa se u pozadini, strana odmah radi
            self.lbl(c, ("⏳ Calculating… (large herd, a few seconds)" if EN else "⏳ Računam… (veliko stado, par sekundi)"), 10, fg=INK2).pack(anchor="w")
            if getattr(self, "_parovi_racuna", None) is not m:
                self._parovi_racuna = m

                def racunaj():
                    try:
                        rez = izracunaj_parove(m, akt)
                    except Exception:
                        rez = []
                    self._kes_parovi = (m, rez[:200])

                    def gotovo():
                        self._parovi_racuna = None
                        if self.strana == "srodstvo" and self.model is m:
                            self.prikazi("srodstvo")
                    self._sinh_red.put((gotovo, ()))     # glavni deo programa ga preuzima (Tk ne sme iz pozadine)
                import threading
                threading.Thread(target=racunaj, daemon=True).start()
            return
        else:
            parovi = izracunaj_parove(m, akt)
            self._kes_parovi = (m, parovi[:200])
        if not parovi:
            self.lbl(c, ("No related pairs according to the recorded pedigree." if EN else "Nema srodnih parova prema upisanom rodoslovu."), 10, fg=INK2).pack(anchor="w")
            return
        wrap, tv = self.tabela(c, [("a", ("Animal A" if EN else "Grlo A"), 120), ("b", ("Animal B" if EN else "Grlo B"), 120), ("od", ("Relation" if EN else "Odnos"), 200),
                                   ("r", ("Shared genes" if EN else "Zajednički geni"), 120, "e")], visina=min(len(parovi), 12))
        wrap.pack(fill="x")
        for i, (r, x, y) in enumerate(parovi[:40]):
            tv.insert("", "end", text="  " + x, image=self.img_tag,
                      values=(y, m.odnos(x, y), pct(r)), tags=["odd"] if i % 2 else [])


    # ---------- Pregled
    def s_pregled(self):
        body = self.strana_okvir()
        h = self.zaglavlje(body, ("Herd overview" if EN else "Pregled stada"), ("Inbreeding status, most common sires and data errors." if EN else "Stanje inbridinga, najčešći očevi i greške u podacima."))
        pf = tk.Frame(h, bg=BG)
        pf.pack(side="right", anchor="s")
        self.lbl(pf, ("Risk limit" if EN else "Granica rizika"), 9, "bold", fg=INK2).pack(anchor="w")
        opcije = {("3.125% – strict" if EN else "3,125% – strogo"): 0.03125, ("6.25% – recommended" if EN else "6,25% – preporučeno"): 0.0625, ("12.5% – mild" if EN else "12,5% – blago"): 0.125}
        pv = tk.StringVar(value=next((k for k, v in opcije.items() if abs(v - self.prag) < 1e-9), ("6.25% – recommended" if EN else "6,25% – preporučeno")))
        cb = ttk.Combobox(pf, textvariable=pv, values=list(opcije), state="readonly", width=22, font=self.f(10))
        cb.pack()
        cb.bind("<<ComboboxSelected>>", lambda e: (setattr(self, "prag", opcije[pv.get()]),
                                                   self.sacuvaj_podesavanja(), self.prikazi("pregled")))
        m = self.model
        sva = m.grla()
        if not sva:
            self.prazno(body)
            return
        akt = [a for a in sva if a["aktivno"]]
        F = [m.inbr(a["id"]) for a in akt]
        iznad = sum(f > self.prag for f in F)
        st = tk.Frame(body, bg=BG)
        st.pack(fill="x", pady=(0, 16))
        for i, (b, t, col) in enumerate(((str(len(akt)), ("animals in herd" if EN else "grla u zapatu"), INK),
                                         (str(sum(a["pol"] == "z" for a in akt)), ("female" if EN else "ženskih"), INK),
                                         (str(sum(a["pol"] == "m" for a in akt)), ("male" if EN else "muških"), INK),
                                         (pct(sum(F) / len(F)) if F else "–", ("average inbreeding" if EN else "prosečan inbriding"), INK),
                                         (str(iznad), ("above the limit" if EN else "grla iznad granice"), BAD if iznad else OK))):
            self.stat(st, b, t, col).grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            st.columnconfigure(i, weight=1, uniform="s")

        dva = tk.Frame(body, bg=BG)
        dva.pack(fill="x")
        dva.columnconfigure(0, weight=1, uniform="d")
        dva.columnconfigure(1, weight=1, uniform="d")
        o, c = self.card(dva)
        o.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.lbl(c, ("Most common sires" if EN else "Najčešći očevi"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("When one male has too many offspring, the next generation becomes related." if EN else "Kad jedan mužjak ima previše potomaka, sledeća generacija postaje srodna."), 9, fg=INK2,
                 wraplength=380, justify="left").pack(anchor="w", pady=(0, 10))
        oc = {}
        for a in akt:
            o_ = m.P[a["id"]][0]
            if o_:
                oc[o_] = oc.get(o_, 0) + 1
        ocl = sorted(oc.items(), key=lambda t: -t[1])[:8]
        if ocl and ocl[0][1] / len(akt) > 0.3:
            self.napomena(c, ("One sire has more than 30% of the offspring in the herd." if EN else "Jedan otac ima više od 30% potomaka u zapatu."))
        if not ocl:
            self.lbl(c, ("No sires entered yet." if EN else "Očevi još nisu upisani."), 10, fg=INK2).pack(anchor="w")
        for x, n in ocl:
            r = tk.Frame(c, bg=SURF)
            r.pack(fill="x", pady=4)
            self.cip(r, x, lambda x=x: self.karton(x), siv=m.A[x]["osnivac"]).pack(side="left")
            self.lbl(r, f"{n} ({round(n / len(akt) * 100)}%)", 10, "bold", width=10, anchor="e").pack(side="right")
            ttk.Progressbar(r, style="Green.Horizontal.TProgressbar", maximum=len(akt), value=n).pack(
                side="left", fill="x", expand=True, padx=10)

        o, c = self.card(dva)
        o.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.lbl(c, ("Animals with the highest inbreeding" if EN else "Grla sa najvećim inbridingom"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("These animals come from related parents." if EN else "Ova grla potiču od srodnih roditelja."), 9, fg=INK2).pack(anchor="w", pady=(0, 10))
        inb = sorted(((f, a) for f, a in zip(F, akt) if f > 0), key=lambda t: -t[0])[:10]
        if not inb:
            self.napomena(c, ("No animal in the herd is inbred." if EN else "Nijedno grlo u zapatu nema inbriding."), ok=True)
        for f, a in inb:
            r = tk.Frame(c, bg=SURF)
            r.pack(fill="x", pady=4)
            self.cip(r, a["id"], lambda x=a["id"]: self.karton(x)).pack(side="left")
            o_, mj = m.P[a["id"]]
            self.lbl(r, f"{o_} × {mj}", 9, fg=INK2).pack(side="left", padx=10)
            self.badge(r, pct(f), BAD if f > self.prag else WARN if f > self.prag / 2 else OK).pack(side="right")

        tk.Frame(body, bg=BG, height=16).pack()
        grupe = {}
        for a in akt:
            grupe.setdefault((a["vrsta"], a["rasa"] or "–", a["stado"] or "–"), []).append(a)
        wrap, tv = self.tabela(body, [("v", ("Species" if EN else "Vrsta"), 100), ("r", ("Breed" if EN else "Rasa"), 130), ("s", ("Herd" if EN else "Stado"), 100),
                                      ("n", ("Animals" if EN else "Grla"), 70, "e"), ("m", ("Males" if EN else "Muških"), 70, "e"), ("z", ("Females" if EN else "Ženskih"), 70, "e"),
                                      ("pf", ("Average F" if EN else "Prosečan F"), 100, "e"), ("mf", ("Highest F" if EN else "Najveći F"), 100, "e")],
                               visina=min(len(grupe), 8), tree=False)
        wrap.pack(fill="x")
        for i, ((v, r, s), g) in enumerate(sorted(grupe.items(), key=lambda t: -len(t[1]))):
            f = [m.inbr(a["id"]) for a in g]
            tv.insert("", "end", values=(v, r, s, len(g), sum(a["pol"] == "m" for a in g),
                                         sum(a["pol"] == "z" for a in g), pct(sum(f) / len(f)), pct(max(f))),
                      tags=["odd"] if i % 2 else [])

        tk.Frame(body, bg=BG, height=16).pack()
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, ("Data check" if EN else "Provera podataka"), 13, "bold").pack(anchor="w", pady=(0, 8))
        if not m.warn:
            self.napomena(c, ("No errors found in the pedigree." if EN else "Nisu pronađene greške u rodoslovu."), ok=True)
        for w in m.warn[:40]:
            r = tk.Frame(c, bg=SURF)
            r.pack(fill="x", pady=3)
            self.badge(r, "!", WARN).pack(side="left", anchor="n")
            self.lbl(r, w, 10, justify="left", wraplength=780).pack(side="left", padx=8, anchor="w")

        tk.Frame(body, bg=BG, height=16).pack()
        self.kartica_plodnosti(body)
        tk.Frame(body, bg=BG, height=16).pack()
        self.kartica_kopija(body)

        # opasna zona
        tk.Frame(body, bg=BG, height=16).pack()
        o = tk.Frame(body, bg=BAD)
        o.pack(fill="x")
        c = tk.Frame(o, bg=SURF)
        c.pack(fill="both", expand=True, padx=1, pady=1)
        red_ = tk.Frame(c, bg=SURF)
        red_.pack(fill="x", padx=20, pady=16)
        lev = tk.Frame(red_, bg=SURF)
        lev.pack(side="left", fill="x", expand=True)
        self.lbl(lev, ("Danger zone" if EN else "Opasna zona"), 13, "bold", fg=BAD).pack(anchor="w")
        self.lbl(lev, ("Delete all animals from the records. Done in 5 steps, with an automatic backup." if EN else "Brisanje svih grla iz evidencije. Radi se u 5 koraka, uz automatsku rezervnu kopiju."),
                 9, fg=INK2).pack(anchor="w")
        self.btn(red_, ("Delete all animals…" if EN else "Obriši sva grla…"), self.brisanje_svih, "Danger").pack(side="right")


def izracunaj_parove(m, akt):
    """Najsrodniji parovi u zapatu, od najsrodnijeg."""
    min_r = 0.25 if len(akt) > 300 else 1e-9
    po_v = {}
    for x in akt:
        po_v.setdefault(x["vrsta"], []).append(x["id"])
    parovi = []
    for ids in po_v.values():
        if len(akt) <= 300:                          # malo stado: svaki par
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    r = m.r(ids[i], ids[j])
                    if r >= min_r:
                        parovi.append((r, ids[i], ids[j]))
        else:                                        # veliko stado: samo mužjak × ženka sa zajedničkim roditeljem ili dedom/babom
            parovi += najsrodniji_parovi(m, ids, min_r)
    parovi.sort(reverse=True)
    return parovi


def najsrodniji_parovi(m, ids, min_r):
    """Parovi mužjak–ženka sa r >= min_r (0,25 = polubraća, deda–unuka, stric–sinovica i bliže).
    Takvi skoro uvek imaju zajedničkog pretka najviše tri generacije unazad, pa se ostali parovi ni ne računaju –
    kod 10.000 grla to je razlika između nekoliko minuta i delića sekunde."""
    dubina = 3 if len(ids) <= 3000 else 2            # vrlo veliko stado: do baba/deda (inače traje predugo)

    def blizu(x):                                    # grlo, roditelji, babe/dede (i prababe/pradede)
        s_, nivo = {x}, [x]
        for _ in range(dubina):
            nivo = [p for y in nivo for p in m.P.get(y, ()) if p]
            s_.update(nivo)
        return s_
    zenke, muski = [x for x in ids if m.A[x]["pol"] == "z"], [x for x in ids if m.A[x]["pol"] == "m"]
    ix = {}
    for z in zenke:
        for p in blizu(z):
            ix.setdefault(p, []).append(z)
    rez = []
    for o in muski:
        kand = set()
        for p in blizu(o):
            kand.update(ix.get(p, ()))
        for z in kand:
            r = m.r(o, z)
            if r >= min_r:
                rez.append((r, o, z))
    return rez
