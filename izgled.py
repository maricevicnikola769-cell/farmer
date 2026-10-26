"""Izgled: logo, boje, font, ikonica markice, prozor sa klizačem i ikonica u naslovnoj traci."""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from osnova import EN, _ZUTI_LOGO


# logo programa (PNG, ugrađen da program radi kao jedan fajl)
# Znak programa HerdDoc (H sa granama rodoslova); žuta varijanta za englesku instalaciju.
LOGO = {
    64: (
        "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAE4UlEQVR42u2bXWyTVRiAn/PRdu3Xsp8W534IbBD5GURkDNT9QIgx"
        "emEQCEiiJtyANyQmoOKFXmnMElFJMN4YbzTOsBgF8YIYQkyhWxCWSOIPGFk2YSu4sHZb/9e1x4vB2E+p7fcVaMv3XrXvd/p+533O"
        "+57znp7vA0MebhGZNpQSEfbQmBS8KKANqAYWAvYH7EMMuAn8BpxWEnSqm7iWMwBSIoJd7BTwPrCsAAY1AXQKeMveilcXgJEulpqS"
        "fINgQwFG95iEdxwtfCYEMmsAYx5aFfgOqCzwNP/KbmWPaCKeMYCAh80CfgLMxTDRSTjhsLIjFQRltiLipl5AZ7E4f2uUt4QifJTq"
        "mjJ7wksoHAUeKcL17vWgh5fTpkDAwy4BR4t42fdPSJaWt+GfEwFSIgS8V+R1T4VJcDBlBITOsk4KevKx14NjNobDJbjUGLWlEb3m"
        "wuE4j1ZuJghguq1NKmwVMr8cvzDo5HD3Cvr9d4rN+oog+5v/oqnWp9WsarPwArdSfSoFhKQ1F50OxMz8MVRGIKZvETk/4OLAycYZ"
        "zgP0+R3sP9nI+QGX9vlQsm3uKiCo1ev8qd4qtnRsZO/xDWzp2Mip3irNtj7pXk4imbpOSyQFh7uX6+nqijkAhKRa78i3uxuITUya"
        "jE0otLsbNEXCwKjK1ZH0e6x/RuwMjtm0dnfx3FUAHHoA9PntRCfmzdBFJ+bR589+s+iLWDJqNxwu0drdsrtWgpq3YFJkpU8nLjWW"
        "WTt7THe/cwYgl1JbGqGuIpS2TV1FiNr5keIEALC/+TImJfW6bFIkbzRfzsl98hbA+lofB9supbz2dtufrNNeBxQGgMlUCKfU1+iv"
        "BgsDwP0QA4ABwABgADAAGAAeYjHd6xvs+7HJiAADgAHAAPDwToLPLr1BlSOq6bc3glZdf6zmBYCtDQOsrfZr+u2v1yvuOQBjDjAA"
        "GAAMAAYAA4ABwACgW8Zipqz0RQVgYFSl3b065bX2M6v0HGMXBoBDnpVTI20zJ1hVOYrNnJiMgKiZQ56VBbEZGmXauXmmMhyx0ON1"
        "AlDliPLF1l9wquP4whb2HH+SG0ErFwZd+MIWnOp4vvg9lioCrmqxdD1gQ946xN1UPzTlpFMdZ1P9EABSgjeYfRqUlcSz0mch3jkA"
        "hEDTebPNlLizfQ1YZ25np31Xp7XLVJY4g6yZtZNcU+1niTOYMwBTKSCTHEOwM1tLdeUhyqxxRqNm3P2VHDm3jKYaHz1eJ+7+yQfN"
        "y6xxFpeHNPX04+cu8uXFev6+OZ/HFgTY/USf7vgX4J72eVKGfsahmvkXULM1+O3vi9I+tXWg+TI7Vl/Ln5lPsNbRwsUZKVC5mSCC"
        "T7XY27n6KnvX92JRkjP0FiXJa01X8st5yaXbzs+IAABfD2WWKFeABVpsD4dLOHfNhS9qwWkd56lFN3HZxsknUSTb1TaOpQQAEPTw"
        "CvB1MZa9ArrUFtqmv0IzpxBytNKB5EgR+j8cF+ye/f5QykrQbuNNCSeKyPnxJGwrb6E3o1JYNBF3eNkuBZ8Xw8hLeL60lbN3SYs0"
        "E+bkO4P7BHwAlBZizivzeNX2NP1p2vy/hDzUSPgQ2MV9OEvIxVInBe/Ob+X7DCBlLuFzLEwmeAnJM0geR7AAsD7gUQ5KGAC8QnBG"
        "wg/T13lDDEkv/wG6knWHFGVULQAAAABJRU5ErkJggg=="
        if _ZUTI_LOGO else
        "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"
    ),
    36: (
        "iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAACvElEQVR42u2Y30tTYRjHP+/ZdG0nF5vaD0OL1It+WCCG5Y+gQPSu"
        "0AjSoIsuvBCi/yDqD6iLQOpaCIqh2IUUEcVyBZL9AENTSRnWgpxNN3/N7bxdNKc2d47E3Az8Xr3vw/Pyfs77PM8553lhi0msZwy6"
        "yRcKLUAdUCTBlqLNgkIyIgVdqgOXOErYECjUyw3gNpCzyYfxRdO4Zj+DJylQsJf7AlrTGKFFCc05NXQmAMVO5m4G0mZBSGrUWvrj"
        "QLGcGQXsGcrlT2o15UKgKQCxBE4pTChs5tXYbt5484howsj9RMjDBQBzzFC3kU18QSvzSyYOOUO6fhMzNlq7T/JrPhuAEmeIB+f7"
        "sGZFk1eg4CLQqcTmB4xgBn/aufyoiiuu0zwd2afr2/HxYBwGYHRqJz3DBfobSI4ALAOphkH2OQj/iTB9E7m6vv45S6Jt3mK0xa7V"
        "QIbS1jyMvioKpv4OR4ItmZTNKJlLZV4O583E5w2lPsozCaQISZFjNj4vdgY3vnarfVy3gYxk/pdF80tmvgWthj5pA3KP5+Mez9/O"
        "of8nh+pLfdw8O6Drc+vlMZ4ZfPO2Q7YNlFGgybnsVWNLZoG8ARXXQBEWs4aaHaH/uxOPd3NfjNN6Ti++7iEqFTqa3vKkxU2udZGe"
        "Yf2SNity3bGOZlaAJING/zcAUSnQpEAi4rZkqiv+gcWk4bCGqSqc3Eif7V3pyzw0CYkraRcxbeNq5ykimsAsJAtRE3ca3lNZ6Ndv"
        "SyMKJkVu6ISk4HpONfcEgHyMabaAD0CZXh51D+1nIWKivsTH8b2BVKZOQMuixF6JP97BzfZSIeE1sCPdpS4lbTm1tK+pMrWGd4qk"
        "GVhM632QoH0ZJqHsbbV0aQrngKE0sASkpE2tps3wwkp+JjsUoFGBRikplSnq+wXMAWNS8FyaeWivxM9W12/RNN2Oi6wFOQAAAABJ"
        "RU5ErkJggg=="
        if _ZUTI_LOGO else
        "iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAC5UlEQVR42u2YyU9TURSHv/PaYkFwwBExFY1gHNFISBzSiNqILBwQ"
        "o9FAYoxx4cb/wOEfMG6MLlyAU+IYExdKIZo4RtGIaESQQTQYFSigUgvtuy7Aiil9r1FoMelv1Xfz6ztfzj3n9vTCKJMMtbhsz8Yp"
        "AX/fbkRcgANF0rAEE74qqFeoa7p34uVXly71mgItKV5/EOEoSMrI5kK90UT2Pi913w8LtLjEdVJgfxR3yCdK7ao+U3E1BKg/M3Is"
        "BmXzQ4msriktfwqg/aoZJXIkRnVs15Q6zeHDWhAo4O/bLTBuOKMkJ/hZM/szKx1tWDVlXE2Qnd1wbwuAdaD8XZEESUvxkmgL0NiR"
        "bOibOa6HU5ufMDGxv4nediSz/3ou3j5LeCiRIuCqNvA8ywxm/pRuLux4wNmih+RnfjT0Fi9tDsIAzE39RkFWq9n5syC4ZcBYM6Ds"
        "NA8Jmg5A7sx2Q++kJF/oWqLPbNvGDwYylWZ2mg5SVWvqn8FU6FokcYZNF2sc1Lb97pGb9TN4FksgXQnvPL+roMGkCUYc6F8UBzKT"
        "9W++lGjzk57iNfVEDciZ8QVnxpd4Df0/NXSrPo0jtxcZeg7lvWSDyW9efMviQDEFGjzjDDXvRBXIMeE7RQtb8Pk1vvdayUnvYJVj"
        "BA9GgS4j07o5n7BqiuIrK9h0zkl7zxgKsoxb2q/LkJ8NhtjuIJASXpvNNwAWUWiiEFRwLZzcDdPxBTQ83gQevJ8cyRTVMuhgVJdB"
        "doazVjZOo2RpE2XbHuFXgt0S4EbdDMPXP/4wifzSPAK6RJQhgXIAC4Aza3ldu+3HVmDaUOZun407zVPRldDsGcvxR/MiGkkDuphm"
        "ckCdvah9bdVN3qB7UbErRxPuAvYYXMIceFFWfuKPLnt5xl0lsAvwRRdGnfgFE9L21WXua7oua4HaKJB09mem4oDphdXC7dsTLPau"
        "QtFUoVJkoobpf7/Qg9AkSrl9qPO1ZZXtjHb9BMaN+BMwjcZCAAAAAElFTkSuQmCC"
    ),
    32: (
        "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACiUlEQVR42u2XS0hUURjHf+d4r+87Wr4lKCiLDMMeIJYPbBXZoodt"
        "gooWrQoXbWrZNog2LSNaSESL3BgtEioYtFYhPXRwVAIFyRx1HF/jnXtPi8brozuO4owW+d/de/7n/P/nO99373dgiyFWvgh1UIhN"
        "sxA0AmVA1gY1ggp6gGfZkzwWZwjHNBDyckkIngBGkjbssyXnPSfw/WEgKv7CLSoJRsCyqM6px+8YCHVQKBR9Sdz5SnzOMjkmGohI"
        "AGyaEyVuWpLgnB6Pdng6lSsAGoAQnI2bSXM6RloEKVRMzpu+Yu57y5k1U6gsGefB6S4y9Yg7WXEVeCqj57B3NfG3A0U0ttRzvbUK"
        "y3ZPEcsWjjhA1/AOXnbvWm3ZSgD52wzZqzE/DOZjK4E/YPBzJs2VM2NqjvgCxmJwo8h1DKwHSrlHwEgzOVo65jxLFHV7RuKuJxOZ"
        "2ndqfRBNkerdAY6UjG+uAU3azlckN31+TXMkW4xtA9p6J1x8XvOfR6CiaIJ0zXYdm4tIvvzITa6Be6e+UmLMuo4NhzLWfUTbVfBv"
        "GJiaX0wV2xaba8A36sH7vYAMzQLgYeeBpBgIxiK09xVT6pnl9bX33K3r5uNQPjPz7sWjp9hLfkwqnvbkogFBVyxWpm4RCut0j+Tg"
        "Dxjowl4mtBT5mWGaDg1Slhfi3MGheAb6F3tCRYuCejfWhfJB2vuLuNl2HCkUt6r8MQ0A3D7pW1tjA21OW67eoU3rfAIqYnW6A+PZ"
        "7MwIU5AVTsTRB22TfZ4GRp2UnvSyXwo6gbwkV55S0GTU0LqsCjy19NqSGhQ9SRQPLhV3vZyqb6ROjXEDuCwE5Qvd6wZuv1NK0KsU"
        "r5TJI08Do/xN+AVkL8tqz9HXJQAAAABJRU5ErkJggg=="
        if _ZUTI_LOGO else
        "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACp0lEQVR42u2W3UuTURzHP+dsc1MbvmYIrUKdmKQJ3lj0Mgq96OWi"
        "t4ug+ScIQdBtl3XTTXUloSUSQUkQUfQiyzIQ8i1LLRVCQl1Oa87U9cydLqxt2TOn6LTI79XDc37n+X7O7/ecc36wxhLzXxQ7K7KQ"
        "VKHUYcAOJC/Twwv0KFT9dIqpuv/KQ39UgCJn+Skh1HUQ1jgtuFdJcayr9nHvHwBz5tzWy8oKa0xKdnXUPukLARQ7K7IQwf44rnx+"
        "5d+kD34vdblcAQmApGqlzE2GICkWLUaUKh7banQCGAGEUkdUjCkpFg2f30hQRa9QRd4I5/d2k2iapWM4jXOPSpjSjPrBQVEJ1EgA"
        "BbkLmR/IcfPA+Zya4y0YpD6qQaqQOUBJ9hdOFH6KXgRByVzy57RhIYAymwcpFPYMHxuT/LoxSaZAyPyX0qPE/lRqJMCiDwsh9DPg"
        "85toG0oPV1lB08esmN+WK/lvX3qxPfTcPJhJ+3Da6gIEguFceWcSFjVHssZaBzAudcLd0y//8wx0uVOZCehzW4xBijZ9jS/AhcYd"
        "DPsSdceyrdNLLtH6Lvg3AJITAuFrV6jVBSjInGDftlGmAwYAzu5+HxcAb7SA8rwRhiYSOXTDwcWmQspsHpIiMhIpbVbqXky6TRlM"
        "RAJ0RAuc0gxYzRqFWV7sGT40JX8zipRnysyddzb6xqzc69kcq8cYCJ8DStQh1H69wIZuG+W5bq4dfU1QCa622KMCAFxuLlhU6pXg"
        "fqjZcTgcxvEtpjagKFqnm5M2yfi0mdFv5pUovdekaXmtt1yeUKF2Vh7MV8hXQEacd54SSp3srHva8Nsu6Lz57IOSYg/QE0dzb6Q5"
        "gCFy9HPHgCczv7RaGGfcUpAKWAHLMk0nEeqtEqI6QdPOtNc3tvI36Qf8ft3u4MYq9AAAAABJRU5ErkJggg=="
    ),
    16: (
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABbElEQVR42qWTsUtCURjFf/c+M7M3vIISKUqEiBqaC2owLBxqiJZo"
        "a+sPaW+qMWqIaGqLIHCRxEaVCIIkSUqXyFB7mO/dBk2emCZ0xh/3nHu/w/0EDZkxghaEFQzRRUpS0TQuvPPkAARA6YYdFIeAh95U"
        "RLGlL3ElzBjBmuDuL/OXJenTbCd6U4IZaQlWnOai2cdpMtBijmZ8hI6W2Y9PO/GwtFmTtsLvpMm8wcHtFOWqq8kKJQ+2EuQ+vC3B"
        "NkzItpLqtaAcbH36BYDI1GvbaLKnykQ9zt3aAQCuTp7z9CRulwVAtaZ1zO4YcPngbz7P7vK4jgEnmwl0dw2AUtXF6nHo13OSf6ot"
        "IJ03kEKRfR/sLUAKnp0gVTDYC6eIZUearF+zCQyV8eufrWZBTpQS+KhxT2OJUnmDaMbH9lyWUd3sdrmpWczWlylGBMEZYPQ4ugns"
        "6ouciB9SiTNm2WwIwXjXPwWPUnI9sMATwDc2+Gsy+YdXXAAAAABJRU5ErkJggg=="
        if _ZUTI_LOGO else
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABdUlEQVR42qWSzStEURjGf++Zj8iUj80YZDQLRe7MkmQ1M0qysULK"
        "x6yUlb2/wxqFlSwsTD7/BU1Jk9SIEopRQ2Pce48FTTO445Zn+Zzz/HrPex7hS0YqGcFSSbRupoYU+lVbvp3Mxt4NgAAYs8l50bIC"
        "1OFOzyh7MrN6lBYjlYyIKWd/hX0em3dLVVqPaOlRypThynBj3TvTsVxVOB654yR1zNJgttJuEWFMaSRU6cZa8yz2X9DgN8teMFBE"
        "iaaj8bUKrKFTfR9V0JSX86XdbBsA6YvQL0t1I/2JK5k/r3udMhPGFSXTA4DfazmyHQGj3bfYLsZ0BMxuD1AofR4H/Cb7cycOxfqn"
        "fgCMYB5bC+GmF5cAzXVVD0J5lg+jDHU9lL03S5F7auC2UP/9e26kbyoRVD51DjQDRFvzxCN3bGbC3BdqtruIll4BiM4lRrDVFtDk"
        "8ulFkIXM+v5auXCxmXi7jRpXSEetpK31pcfjPThdTecAPgCQQW7hZAeFCwAAAABJRU5ErkJggg=="
    ),
}


# boje
BG, SURF, SURF2 = "#F3F5F1", "#FFFFFF", "#E9EDE6"


INK, INK2, LINE = "#18221C", "#56645A", "#D6DDD3"


TAG, TAG_INK, BRAND, BRAND_H = "#F4C400", "#1B1A12", "#2E5E45", "#24503A"


OK, OK_BG, WARN, WARN_BG, BAD, BAD_BG = "#23804A", "#DDF1E3", "#9A5C00", "#FBEBCB", "#B3322B", "#F8DEDA"


# =============================================================== UI pomocnici

def izaberi_font():
    fam = set(tkfont.families())
    for f in ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Cantarell",
              "DejaVu Sans"):
        if f in fam:
            return f
    return "TkDefaultFont"


def ikonica_markice(boja):
    """Mala slika usne markice (za tabele)."""
    w, h = 16, 18
    img = tk.PhotoImage(width=w, height=h)
    for y in range(h):
        xs = []
        for x in range(w):
            inside = 2 <= x <= 13 and 1 <= y <= 16
            if y < 3 and (x in (2, 13)):
                inside = False
            if y > 10:  # zaobljen donji deo
                cx, cy, rr = 7.5, 10, 6.2
                inside = inside and ((x - cx) ** 2 + (y - cy) ** 2 <= rr * rr)
            if (x - 7.5) ** 2 + (y - 5) ** 2 <= 3.2:
                inside = False
            if inside:
                xs.append(x)
        for x in xs:
            img.put(boja, (x, y))
    return img


class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.bind("<Enter>", self._ukljuci)
        self.bind("<Leave>", self._iskljuci)

    def _ukljuci(self, e=None):
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", lambda e: self._wheel(e, -1))
        self.bind_all("<Button-5>", lambda e: self._wheel(e, 1))

    def _iskljuci(self, e=None):
        for s in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(s)

    def _scroll(self, n):
        if self.winfo_exists() and self.winfo_ismapped():
            self.canvas.yview_scroll(n, "units")

    def _wheel(self, e, smer=None):
        # ne skroluj stranu kad je mis iznad tabele (tabela skroluje sama)
        if isinstance(e.widget, ttk.Treeview) or not self.winfo_exists():
            return
        if smer is None:
            smer = int(-e.delta / 120) if abs(e.delta) >= 120 else (-1 if e.delta > 0 else 1)
        self._scroll(smer)


def postavi_win_ikonicu(prozor, ico):
    ("""Load the .ico and set it as the small and big window icon (title bar, Alt+Tab).""" if EN else """Učita .ico i postavi ga kao malu i veliku ikonicu prozora (naslovna traka, Alt+Tab).""")
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.LoadImageW.restype = wintypes.HANDLE
        u.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        u.SendMessageW.restype = ctypes.c_ssize_t
        u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        u.GetParent.restype = wintypes.HWND
        u.GetParent.argtypes = [wintypes.HWND]
        prozor.update_idletasks()
        hwnd = u.GetParent(prozor.winfo_id()) or prozor.winfo_id()
        for vrsta, metrika, rezerva in ((0, 49, 16), (1, 11, 32)):   # ICON_SMALL / ICON_BIG
            vel = u.GetSystemMetrics(metrika) or rezerva
            h = u.LoadImageW(None, ico, 1, vel, vel, 0x10)            # IMAGE_ICON, LR_LOADFROMFILE
            if h:
                u.SendMessageW(hwnd, 0x0080, vrsta, h)                  # WM_SETICON
    except Exception:
        pass
