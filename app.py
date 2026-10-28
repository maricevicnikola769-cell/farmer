"""Sklapa glavni prozor programa (App) iz svih delova i pokreće program (main)."""
import json
import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox

from osnova import EN, PODESAVANJA, _engleski_exe, _jezik_sistema, _prvi_postojeci
from jezik import postavi_jezik
from izgled import BG, BRAND, BRAND_H, INK, INK2, LINE, LOGO, SURF2
from ekran_osnova import OsnovaProzora
from ekran_grla import GrlaEkran
from ekran_parenje import ParenjeEkran
from karton import KartonEkran
from gravidnost import GravidnostDeo
from istorija import IstorijaDeo
from kopije import KopijeDeo
from obavestenja import ObavestenjaDeo
from stampa import StampaDeo
from izvoz import IzvozDeo
from mlecnost import MlecnostDeo
from citac import CitacDeo
from finansije import FinansijeDeo
from oblak_kopija import OblakKopijaDeo
from telefon_prenos import TelefonDeo
from sinhronizacija import SinhronizacijaDeo
import dnevnik
from dnevnik import DnevnikDeo


class App(OsnovaProzora, GrlaEkran, ParenjeEkran, KartonEkran, GravidnostDeo, IstorijaDeo, KopijeDeo, ObavestenjaDeo, StampaDeo, TelefonDeo,
          SinhronizacijaDeo, DnevnikDeo, IzvozDeo, MlecnostDeo, CitacDeo, FinansijeDeo, OblakKopijaDeo):
    """Glavni prozor programa, sklopljen iz delova (svaki deo je u svom fajlu)."""


def prvo_pokretanje():
    """Prvi put: nema podešavanja ni tablice sa grlima (instalacija 'HerdDoc English' odmah radi na engleskom)."""
    return not (os.path.exists(PODESAVANJA) or _prvi_postojeci("stado.csv", "herd.csv") or _engleski_exe())


def izbor_jezika_na_startu(root):
    """Mali prozor pri prvom pokretanju: Srpski / English. Izbor se pamti; kasnije se menja dole levo (🌐)."""
    predlog = _jezik_sistema()
    izbor = tk.StringVar(value="")
    root.title("HerdDoc")
    root.configure(bg="#FFFFFF")
    root.geometry("460x300")
    okvir = tk.Frame(root, bg="#FFFFFF")
    okvir.place(relx=0.5, rely=0.5, anchor="center")
    try:
        slika = tk.PhotoImage(data=LOGO[64]) if 64 in LOGO else None
    except Exception:
        slika = None
    if slika:
        root._logo_izbor = slika
        tk.Label(okvir, image=slika, bg="#FFFFFF").pack(pady=(0, 10))
    tk.Label(okvir, text="HerdDoc", font=("Segoe UI", 20, "bold"), bg="#FFFFFF", fg=INK).pack()
    tk.Label(okvir, text="Izaberi jezik  ·  Choose language", font=("Segoe UI", 11), bg="#FFFFFF", fg=INK2).pack(pady=(4, 18))
    dugmad = tk.Frame(okvir, bg="#FFFFFF")
    dugmad.pack()
    for kod, naziv in (("sr", "Srpski"), ("en", "English")):
        glavno = kod == predlog
        tk.Button(dugmad, text=naziv, width=12, font=("Segoe UI", 12, "bold"), relief="flat", cursor="hand2",
                  bg=BRAND if glavno else SURF2, fg="#FFFFFF" if glavno else INK,
                  activebackground=BRAND_H if glavno else LINE, activeforeground="#FFFFFF" if glavno else INK,
                  command=lambda k=kod: izbor.set(k)).pack(side="left", padx=8, ipady=6)
    tk.Label(okvir, text="Kasnije se menja dole levo (🌐)  ·  Can be changed later, bottom left (🌐)",
             font=("Segoe UI", 8), bg="#FFFFFF", fg="#8A968F").pack(pady=(18, 0))
    root.protocol("WM_DELETE_WINDOW", lambda: izbor.set(predlog))
    root.bind("<Return>", lambda e: izbor.set(predlog))
    root.wait_variable(izbor)
    novi = izbor.get() or predlog
    root.unbind("<Return>")
    for w in root.winfo_children():
        w.destroy()
    root.configure(bg=BG)
    try:
        with open(PODESAVANJA, "w", encoding="utf-8") as f:
            json.dump({"jezik": novi}, f)
    except OSError:
        pass
    postavi_jezik(novi)


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        try:   # da Windows na traci zadataka prikaže logo programa, a ne Python
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(("HerdDoc.English" if EN else "HerdDoc.Program"))
        except Exception:
            pass
    sys.setrecursionlimit(20000)
    dnevnik.postavi()
    root = tk.Tk()

    def greska(exc, val, tb):
        dnevnik.zapisi_izuzetak(exc, val, tb, "greška pri pokretanju")
        messagebox.showerror(("Error" if EN else "Greška"), ("An error occurred:\n\n" if EN else "Došlo je do greške:\n\n") + "".join(traceback.format_exception_only(exc, val)))
    root.report_callback_exception = greska
    if prvo_pokretanje():
        izbor_jezika_na_startu(root)
    app = App(root)
    root.report_callback_exception = app.greska_u_prozoru      # greška -> dnevnik + ponuda izveštaja
    root.mainloop()
