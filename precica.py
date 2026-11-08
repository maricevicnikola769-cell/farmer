"""Ikonica na radnoj površini za verziju iz Microsoft prodavnice.

Programi iz prodavnice (MSIX) se pojavljuju samo u Start meniju. Pri prvom pokretanju program jednom pita
da li da napravi ikonicu na radnoj površini. Verzija sa GitHub-a (Setup.exe) ikonicu pravi sama pri instalaciji,
pa se tamo ništa ne pita.
"""
import os
import subprocess
import sys
from tkinter import messagebox

from jezik import T

APP_ID = "HerdDoc"            # <Application Id> iz msix/napravi_msix.py
IME_IKONICE = "HerdDoc.lnk"


def ime_paketa():
    """Package Family Name kad program radi iz Microsoft prodavnice; inače None."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        duz = ctypes.c_uint32(0)
        k32 = ctypes.windll.kernel32
        if k32.GetCurrentPackageFamilyName(ctypes.byref(duz), None) != 122:   # 122 = bafer premali → ima paket
            return None
        buf = ctypes.create_unicode_buffer(duz.value)
        if k32.GetCurrentPackageFamilyName(ctypes.byref(duz), buf) != 0:
            return None
        return buf.value or None
    except Exception:
        return None


def radna_povrsina():
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0:   # 0x10 = radna površina
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _ps_tekst(s):
    return "'" + s.replace("'", "''") + "'"


def napravi(pfn, folder=None):
    """Pravi HerdDoc.lnk na radnoj površini koji otvara aplikaciju iz prodavnice. Vraća True ako je uspelo."""
    put = os.path.join(folder or radna_povrsina(), IME_IKONICE)
    windir = os.environ.get("WINDIR", r"C:\Windows")
    skripta = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + _ps_tekst(put) + "); "
               "$s.TargetPath = " + _ps_tekst(os.path.join(windir, "explorer.exe")) + "; "
               "$s.Arguments = " + _ps_tekst("shell:AppsFolder\\" + pfn + "!" + APP_ID) + "; "
               "$s.IconLocation = " + _ps_tekst(sys.executable + ",0") + "; "
               "$s.Description = 'HerdDoc'; $s.Save()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", skripta],
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return os.path.isfile(put)


def ponudi(app):
    """Jednom (pri prvom pokretanju verzije iz prodavnice) pita da li da napravi ikonicu na radnoj površini."""
    pod = getattr(app, "pod", None)
    if pod is None or pod.get("precica_pitano"):
        return
    pfn = ime_paketa()
    if not pfn:
        return
    pod["precica_pitano"] = True
    try:
        app.sacuvaj_podesavanja()
    except Exception:
        pass
    if os.path.isfile(os.path.join(radna_povrsina(), IME_IKONICE)):
        return
    if not messagebox.askyesno("HerdDoc", T("Da napravim ikonicu HerdDoc na radnoj površini?",
                                            "Create a HerdDoc icon on the desktop?"), parent=app.root):
        return
    if napravi(pfn):
        try:
            app.toast(T("Ikonica je na radnoj površini.", "The icon is on the desktop."))
        except Exception:
            pass
    else:
        messagebox.showinfo("HerdDoc", T("Ikonicu nije moguće napraviti. HerdDoc možeš da prevučeš iz Start menija na radnu površinu.",
                                         "Could not create the icon. You can drag HerdDoc from the Start menu to the desktop."),
                            parent=app.root)
