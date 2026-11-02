"""Prirast: težina grla iz događaja „Merenje težine“ (vrednost = kg) i dnevni prirast u gramima na dan."""
import re
import tkinter as tk

import jezik
from jezik import T
from podaci import parsiraj_datum
from izgled import BAD, INK, INK2, OK, SURF, SURF2


def kg(v):
    """'350', '350,5', '350.5 kg' -> 350.5; inače None."""
    m = re.search(r"\d+(?:[.,]\d+)?", str(v or ""))
    if not m:
        return None
    x = float(m.group(0).replace(",", "."))
    return x if 0 < x < 3000 else None


def merenja(istorija, x):
    """[(datum, kg)] po datumu; više merenja istog dana -> poslednje upisano."""
    dog = jezik.DOGADJAJI[5]                 # Merenje težine (na trenutnom jeziku)
    po_danu = {}
    for z in sorted((z for z in istorija.zapisi if z["grlo"] == x and z["dogadjaj"] == dog), key=lambda z: z.get("uneto", "")):
        d, t = parsiraj_datum(z.get("datum")), kg(z.get("vrednost"))
        if d and t:
            po_danu[d] = t
    return sorted(po_danu.items())


def prirast(niz):
    """Dnevni prirast u g/dan između dva merenja (ili None)."""
    (d1, t1), (d2, t2) = niz
    dana = (d2 - d1).days
    return round((t2 - t1) * 1000 / dana) if dana > 0 else None


def stat(istorija, x):
    m = merenja(istorija, x)
    s = dict(merenja=m, poslednje=m[-1] if m else None, od_prethodnog=None, dana_prethodno=None, prosek=None, ukupno_kg=None)
    if len(m) >= 2:
        s["od_prethodnog"] = prirast(m[-2:])
        s["dana_prethodno"] = (m[-1][0] - m[-2][0]).days
        s["prosek"] = prirast([m[0], m[-1]])
        s["ukupno_kg"] = round(m[-1][1] - m[0][1], 1)
    return s


def fmt_kg(x):
    t = f"{x:.1f}".rstrip("0").rstrip(".")
    return t if jezik.JEZIK == "en" else t.replace(".", ",")


def fmt_g(g):
    return ("+" if g > 0 else "") + f"{g:,}".replace(",", " ") + " " + T("g/dan", "g/day")


class PrirastDeo:
    """Težina i prirast na kartonu grla."""

    def prirast_na_kartonu(self, parent, x):
        s = stat(self.ist, x)
        if not s["poslednje"]:
            return
        fd = lambda d: d.strftime("%d.%m.%Y." if not jezik.EN else "%d/%m/%Y")
        self.lbl(parent, T("Težina i prirast", "Weight and gain"), 10, "bold").pack(anchor="w", pady=(18, 6))
        fr = tk.Frame(parent, bg=SURF)
        fr.pack(anchor="w", fill="x")
        d, t = s["poslednje"]
        redovi = [(T("Poslednja težina", "Last weight"), f"{fmt_kg(t)} kg  ({fd(d)})", INK)]
        if s["od_prethodnog"] is not None:
            redovi.append((T("Prirast od prethodnog merenja", "Gain since previous weighing"),
                           fmt_g(s["od_prethodnog"]) + T(f"\n(za {s['dana_prethodno']} dana)", f"\n(over {s['dana_prethodno']} days)"),
                           OK if s["od_prethodnog"] > 0 else BAD))
        if s["prosek"] is not None and len(s["merenja"]) > 2:
            redovi.append((T("Prosečan dnevni prirast", "Average daily gain"),
                           fmt_g(s["prosek"]) + T(f"\n(od {fd(s['merenja'][0][0])})", f"\n(since {fd(s['merenja'][0][0])})"), INK))
        for i, (k, v, boja) in enumerate(redovi):
            self.lbl(fr, k, 10, fg=INK2).grid(row=i, column=0, sticky="w", pady=2)
            self.lbl(fr, v, 10, "bold", fg=boja, wraplength=190, justify="left").grid(row=i, column=1, sticky="w", padx=(14, 0), pady=2)
        if len(s["merenja"]) >= 2:                       # poslednjih 6 merenja: datum, kg, prirast
            tb = tk.Frame(parent, bg=SURF2)
            tb.pack(anchor="w", fill="x", pady=(8, 0))
            posl = s["merenja"][-6:]
            pre = s["merenja"][-7] if len(s["merenja"]) > 6 else None
            for i, (dd, tt) in enumerate(posl):
                p = prirast([posl[i - 1], (dd, tt)]) if i else (prirast([pre, (dd, tt)]) if pre else None)
                self.lbl(tb, fd(dd), 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 14), pady=1)
                self.lbl(tb, f"{fmt_kg(tt)} kg", 9, "bold", bg=SURF2).grid(row=i, column=1, sticky="e", padx=(0, 14))
                self.lbl(tb, fmt_g(p) if p is not None else "", 9, fg=(OK if p and p > 0 else BAD) if p is not None else INK2,
                         bg=SURF2).grid(row=i, column=2, sticky="w", padx=(0, 12))
