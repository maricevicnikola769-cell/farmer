"""Dnevnik grešaka: svaka greška se zapisuje u farmer-greske.log (folder sa podacima programa),
a „Prijavi problem“ pravi izveštaj koji korisnik može da pošalje (bez podataka o grlima – samo greške i brojevi)."""
import os
import platform
import sys
import threading
import time
import traceback
from tkinter import filedialog, messagebox

from osnova import APP_DIR, VERZIJA
from jezik import T

LOG = os.path.join(APP_DIR, "farmer-greske.log")
NAJVISE = 512 * 1024                      # posle toga stari dnevnik ide u .1 (čuva se jedan prethodni)
PODRSKA = "herddoc1@gmail.com"            # e-pošta za prijavu problema


def zapisi(naslov, tekst=""):
    try:
        if os.path.isfile(LOG) and os.path.getsize(LOG) > NAJVISE:
            os.replace(LOG, LOG + ".1")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} · HerdDoc {VERZIJA} · {naslov}\n{str(tekst).rstrip()}\n")
    except OSError:
        pass


def zapisi_izuzetak(exc, val, tb, gde=""):
    zapisi(gde or getattr(exc, "__name__", "greška"), "".join(traceback.format_exception(exc, val, tb)))


def postavi():
    """Greške van prozora (pozadinske niti, pokretanje) takođe idu u dnevnik."""
    stari = sys.excepthook

    def glavna(e, v, t):
        zapisi_izuzetak(e, v, t, "neuhvaćena greška")
        stari(e, v, t)
    sys.excepthook = glavna
    threading.excepthook = lambda a: zapisi_izuzetak(a.exc_type, a.exc_value, a.exc_traceback,
                                                     "pozadina " + (a.thread.name if a.thread else ""))


def poslednje_linije(n=400):
    linije = []
    for p in (LOG + ".1", LOG):
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                linije += f.read().splitlines()
        except OSError:
            pass
    return linije[-n:]


class DnevnikDeo:
    """Prijava problema iz programa."""

    def greska_u_prozoru(self, exc, val, tb):
        zapisi_izuzetak(exc, val, tb, "greška u prozoru")
        if messagebox.askyesno(T("Greška", "Error"),
                               T("Došlo je do greške:\n\n", "An error occurred:\n\n") + "".join(traceback.format_exception_only(exc, val)) +
                               T("\nGreška je zapisana. Da li želiš da napraviš izveštaj za slanje (da se greška popravi)?",
                                 "\nThe error was recorded. Do you want to make a report to send (so it can be fixed)?"),
                               icon="error"):
            self.prijavi_problem()

    def izvestaj(self):
        info = [T("HerdDoc – izveštaj o problemu", "HerdDoc – problem report"),
                f"{T('Verzija', 'Version')}: {VERZIJA}  ·  {T('vreme', 'time')}: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"{T('Sistem', 'System')}: {platform.platform()}  ·  Python {platform.python_version()}"]
        try:
            info.append(f"{T('Grla', 'Animals')}: {len(self.tab.redovi)}  ·  {T('zapisa u istoriji', 'history records')}: {len(self.ist.zapisi)}"
                        f"  ·  {T('podsetnika', 'reminders')}: {len(self.pods.zapisi)}")
            s = self.pod.get("sinh", {})
            info.append(f"{T('Telefoni', 'Phones')}: {len(s.get('telefoni', {}))}  ·  {T('upareno', 'paired')}: {bool(s.get('farma'))}"
                        f"  ·  {T('usklađivanje', 'sync')}: {getattr(self, 'sinh_stanje', {}).get('tekst', '')}")
        except Exception:
            pass
        linije = poslednje_linije()
        return "\n".join(info + ["", T("--- poslednje zapisane greške ---", "--- last recorded errors ---")] +
                         (linije or [T("(nema zapisanih grešaka)", "(no recorded errors)")])) + "\n"

    def prijavi_problem(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        put = filedialog.asksaveasfilename(
            title=T("Sačuvaj izveštaj o problemu", "Save problem report"),
            initialdir=desktop if os.path.isdir(desktop) else APP_DIR,
            initialfile=f"HerdDoc-izvestaj-{time.strftime('%Y%m%d-%H%M')}.txt", defaultextension=".txt",
            filetypes=[(T("Tekst", "Text"), "*.txt")])
        if not put:
            return
        try:
            with open(put, "w", encoding="utf-8") as f:
                f.write(self.izvestaj())
        except OSError as e:
            messagebox.showerror("HerdDoc", str(e))
            return
        if messagebox.askyesno(T("Izveštaj je napravljen", "Report saved"),
                               T(f"Sačuvano:\n{put}\n\nPošalji ovaj fajl" + (f" na {PODRSKA}" if PODRSKA else " proizvođaču programa") +
                                 " (mejlom ili Viberom) i napiši ukratko šta si radio kad se problem pojavio.\n\n"
                                 "U izveštaju nisu tvoje tablice – samo zapisane greške i brojevi.\n\n"
                                 "Da otvorim novi mejl sa izveštajem?",
                                 f"Saved:\n{put}\n\nSend this file" + (f" to {PODRSKA}" if PODRSKA else " to the program's maker") +
                                 " and briefly describe what you were doing when the problem appeared.\n\n"
                                 "The report does not contain your tables – only recorded errors and counts.\n\n"
                                 "Open a new e-mail with the report?")):
            self.otvori_mejl()

    def otvori_mejl(self, tekst=None):
        """Novi mejl podršci (podrazumevani program za poštu) sa izveštajem u tekstu poruke."""
        import webbrowser
        from urllib.parse import quote
        telo = tekst if tekst is not None else self.izvestaj()
        if len(telo) > 900:                      # Windows ne podnosi dugačke mailto adrese – ostatak je u sačuvanom fajlu
            telo = telo[:900] + T("\n…(ceo izveštaj je u priloženom fajlu)", "\n…(the full report is in the attached file)")
        uvod = T("Opis problema (šta si radio kad se pojavio):\n\n\n", "Problem description (what you were doing):\n\n\n")
        adresa = (f"mailto:{PODRSKA}?subject={quote(T('HerdDoc – prijava problema', 'HerdDoc – problem report') + ' ' + VERZIJA)}"
                  f"&body={quote(uvod + telo)}")
        try:
            webbrowser.open(adresa)
        except Exception:
            messagebox.showinfo("HerdDoc", T("Pošalji izveštaj na: ", "Send the report to: ") + PODRSKA)
