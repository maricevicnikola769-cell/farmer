"""Farmer – rodoslov stada, srodstvo, inbriding i plan parenja.
Farmer – herd pedigree, relationship, inbreeding and mating plan.

Jedan program na dva jezika (srpski / English). Jezik se bira u programu (dole levo).
Pokretanje: dupli klik na ovaj fajl (potreban je Python 3.8+ sa python.org).
Podaci se čuvaju u CSV tablici (otvara se i u Excelu).

Program je podeljen na više fajlova (osnova.py, podaci.py, rodoslov.py, ...); svi moraju biti u istom folderu.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # da nađe ostale fajlove programa


if __name__ == "__main__":
    try:
        from app import main
        main()
    except Exception:
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Farmer", traceback.format_exc())
        except Exception:
            print(traceback.format_exc())
