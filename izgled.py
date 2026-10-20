"""Izgled: logo, boje, font, ikonica markice, prozor sa klizačem i ikonica u naslovnoj traci."""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from osnova import EN, _ZUTI_LOGO


# logo programa (PNG, ugrađen da program radi kao jedan fajl)
LOGO = {
    64: (
        ("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"
        "SUVORK5CYII=" if _ZUTI_LOGO else "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")
    ),
    36: (
        ("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" if _ZUTI_LOGO else "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")
    ),
    32: (
        ("iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAE8klEQVR42q2Xz29UVRTHP+feN29m6EzrFC2glRjAH4EWiIlSEQQx"
        "xMTERF2wYQNRY6KJMbhkYUz0XzCS6E43szFGZaExkaAJVo3EFrQlWKtCgQaw8zrTmfveu8fFtAilrdOBs3lv8d453+8933POPQJQ"
        "LmP37SMtv0X47DO8aGB/mtDvlSIg3JqpESIbMOTh48+O8uG+t3FzMUUVI4K/8hX9HV18EGZ4NE3AxeA9t8WMgTADNgDnGKxWeKl7"
        "L0OqGAGIjrMpzHI8DClFEamAiGC4jaaKV9BiEescV12DncWdnDI6Shb4KAwpTUfERrDtBleFVOXa83oTwRjBTkfEYUhJlY90lGxQ"
        "u8iBQoGtUURqhMyizgGvsqggVCGXUUKrxClkrFJzzf/mAclEEWmxyNbaRQ4EKhxME1SWEJsCgUAubJ7jQsGthbErOd77/n7+nFrB"
        "E/dNcvDhMUT1ZhAgaYKqcDBQpc85RBYhp4AViFzAu8ce4FwlT2BudKoKGQsjkwXOXi2SzyQcG+shToU3tp+l0hCs6A3pcA5U6QtE"
        "6FiI1Zx5LxTySnl4De//sIHuvMOrzEKbe4KqkM+k3LmiAShW4OvfV/PKI2dvCH7Nr4IIHUGrAqu5gM5sTGcuxiWG1N+YNAEaaVO7"
        "2SAlcgE9HXXCAGpOMLIwy5YBzDmo1DPs3/wHz/dNUK0LxuisAOHb8ZUcGdzAVD1kfWma1x8bZanTXRaAOZaJF3q7avT3ThHPgL2u"
        "YLesnuKpdReYiPL0rZqiO58wE7Mo+2UDmAPhEoN3QtUJ1ui1nHoV1pVqPHRXjXoMtZjZVsftA9CsjGaz0eukWAgVa5U4gal6E5hp"
        "YYoE7XS7fJBi80qXKsY2Ufx4rpPfJjvpX/0P/aumqbnWxliwPOYQBp5Tk518ObyKqhPyGWX4Yicf/rSOemLJWs87e3/hhY3nqS6h"
        "/rYAeBVWZFK+GL2HT3/tvb4NkM+kdIQJUSPDkcH17F1/gYz1zXpfqrpuZeh4L6TazHdgFFUhtCn1xBKn0tJFYtll2EgNW9dcZWNP"
        "RCMRslY5c7nAN2M9hIGn6gL2bxlnZUfKdOM2p8CIMuMsT2+Y4MD2v9AZEAu1hvDxybUMX7qDh+++wr6+v/+3/tvvAwIzcUA6I1Tq"
        "TYaBUV5+dBwYB6DaaN1fW33AiGJNc+DY2clYmflvNtgWmC8bgOrC73PamOuIy7WgVfVlA38tp9nA3/pduVUARiBJ4NSlLqZd8/NT"
        "l7pIElpqtbcEIFWhmFWOjvRQHl7LawNnADgyuIEn113kmQcvEc277SxbT6pUF2WiIAZOTpQo5R2H94xweM8Ipbzj5EQJMdx862xZ"
        "yNCMLQyHIaqKX6jkvIdtvZeZrGY59Hk/hz7fzGQ1y7bey3jf/KadHSEMURGG7eGD2GyOZxsOP38fEIE4gfV31ujKOT45fS/j/3Tw"
        "5uMjPLfpPHXXng4UfC6HaTjeER0lG13gRLGTrdMRsSyyG3SEzTkP0JVTqq7tDSkuFMlEFU4WVzMgAPUTbBTDt0utZl6FYLbWEy8t"
        "tdmlVjP17MgNcNqoYnIDnK7W2OUcg8UCNp/DzD9aI0qqkCrLDm4E8jlMsYB1jsFqjV25AU6rYowIvlzGdu9m6NMv2Fl3vJp4vkOo"
        "zNe4tLerK0Il8XxXd7w69DM7unczVC5jRfD/AoiFQTDA2f8+AAAAAElFTkSuQmCC" if _ZUTI_LOGO else "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAE7klEQVR42sWXz29c1RXHP+fe+954xvGvhCiBxPwSbZQ6BUEikIqo"
        "VAhkgbpqR0WUolZUCBZt/4CqUpeVumoXLLJC/KgaGZZFIhhFqgpssBCQELFISjDgENVW/HPG7953Thczkzi248wMVD3Sld579+l+"
        "v+fnPUdYJ/V63U9OTpad98PPHh1plM5rUQp9iMu9Vb2W08enFq6HIRs3Dj75o9vyLHvWRI5ius/MMgCM3kgIBiAiEXFfitlUEePx"
        "s387dWE9CVkPfvdTjzwtWfirz8KIphJT49sQcYILnjKmBYvptx+98vZLHUzpPBx6+tGnsjx7WWNC1ZJgDpGeTd9W/FqDmZkh6pwE"
        "lwViEX9x+qW3XqnX614AmfjZY/tDlbMYVVMFEbf14SCyvVXWkgegEkrUNvA3U3EOhEZqcPDMiZNfOMBcrs/7PAyqmm4HrgaN6Ldc"
        "qzGwXAT2Da+yb7jBShHYRFXEqZr6PAy6XJ8HLLTiRI5pUhPMsUWsCRBVqIaSO8ZW0XWm7uw3S8dPJ2Z44vtfAPDqh+P85b0DVIJi"
        "do2LnCY1EY4Bv5fD9aMjscpZcf5mUzU2MOhonnnlhR+/z723LNCMLXiBKzQE2JEba2XrWy2HX752hHc+v4kdeVrvDhPnxLSczRoc"
        "DEshZhXLwvWiTcQokueOnSvce8sCsYRqZmTZOvS2rBYQSyGZUMuVvUMNkjpENv9rRlgKMQsuhK5yzQwaSRjwxrn5GtNf7ST3LfOK"
        "QFLhh7dfYt9YBIyZ+Qrvfr6bwSyhurV6LgQLPeWYQSWD6S938rs3DjNWXaNUh4gRS8fEngWeODQDAn//aJxLywNUs7Q5G9ZJ6Kew"
        "5EEZqxaMDkRKEzBwzpi5XOOPpyYwoBrKG4L3TQBrLWu7RoDlIqAqjA4UeDGSuRuC900gqrC4luG9kVQwg4O7F9lVK/j46xFWYqAS"
        "tKuzeiIgAqXCnh1NHr7za4YqkZUYeGD/HM8c+TfVoHx8cZjf/OM+5lZzMm/X1IBvTMCJ0Yzwg1vneOj2uSvu8A7WSlhsCveML/Lz"
        "ez7jT//8HmOhaMXIt+kCowWYh/aLQCpb+a8moMZwJXZ9Xk8E1IRqZpy+OMTUub3UspJG8tx38zwPf2cOMBYbntfPjFPxekPz90zA"
        "DLIAn1waaZm4VhBLx1AeefzAV+wdXuPUud18+p9hal2kYH9ZYK06sLNWMFotUBWSCpOnx9sWKrsG7zsNzaBUubIARgciSGuvW/Ce"
        "CHTuk45fN0J0KmLPjWu3GkcVghjirxajvlrljQQ0JemmAj1z+Dx5EGbmKxz77iXu3z/HchFw8s0aVzeUsihCul7laybPbaMr/GRi"
        "lj9MTfDg8aMsrXmevPsCzdS+6/vplIU02JTkpienFkFmxYlhmzPXidFMniLBXbuWObTnMiMDkcvNrD8XmJm0zDY7PTm16NpN85su"
        "ODFEN/o+98rs0gB//tcBfn3kM9741TtcuDzIix/cyWCeeor4druuLjgx403Aum7LG9Fz164lbhosOH1xhGby5KG7ardtW16v192Z"
        "EydnSrXnXBacOOfMSJjp1ZsfG8yTnZ/fYe9e2GVJxXJfmunV/W2XmZqRxDnnsuBKtefOnDg5U6/X3dajWQgjWm4ezToRb9bbqChO"
        "cN5Tpi1Gs22HU9X9Rrtv/F8Op//P8fy/OcDHrY2/4vAAAAAASUVORK5CYII=")
    ),
    16: (
        ("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACEUlEQVR42m2Tv2sUURDHP7Pv7d3t5hRjLviz8Uc4EJQUlsFOEQVJ"
        "Kf4P9v4BFrYBS0srLRQrCak0GCFNRFQCRpEIiqhJzrvbe7f73lhsAnfZTDm872fezHdGALZfcT1NeFDkXAgBCwgjoUAIgghqjRY2"
        "5mM/496RK7yU7jLX4pgX1lDvD0qlKsgIIhJIapAX4ApIEyg8Ls+5FamyEBvqvQy/p6nZEmAiiA24IuLp+5N83UqoWej28bGhrsqC"
        "/HtNABBBggppTXm4co7nn04jogjCwEds/Gly+dRfntx+g6qiigJYkfF+I4G336fYGcTcaP/AB6HjLDuDmDOTXYwoedmiAFj2hexC"
        "Lh7b5v7ND+DKV19+NWilriw7WpADIigEFVDIPaxtHmIqHdKIlcKPW1T5gSok1vPu5yR3n83Sc5aVzSkuHd/m0fwqRgJhxOcqoBwo"
        "rojY3EkZ5IZ+Xs4gaOnMaB8VQCTQzw2zJ7Z4fGeVrA/L31qcPdoliQPDYnxH7EEzsLLrUQ5FEK6e/83QUxFXAAJ4hY6LAfChzHWc"
        "EKEVMUCkWu5FUGGirix9btGe7tCe7rC00aJZV4Rq5T1dBKxPJIiq+qGHmVaPLDdkuWGm1cMVIPvcD4qfSBBgfeyYehk0LHScAeBw"
        "3ZcAGXcpbYwcU3OOxcwxH2DNGvJBgaaxJ42rYkBNRB5gLXPMN+dY/A/S4PZF4nAFhQAAAABJRU5ErkJggg==" if _ZUTI_LOGO else "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACVElEQVR42n2TzWtdVRTFf2vfc+8NeblpajFoqBJKoaO01YqgIoLa"
        "QVUMdKhUx3amUwch/4CdtaVDtTguDpxUOxQtKFowowZBgx/EvEHz9d752B28JiZpdcHhcAa/tfc+5yyxsGAsLpa5d1991ppwzot3"
        "FAAXOxKY5AWQVffKcPjVnevf/MDCggng5Huvf2ChuoSsBTA59i9OcYjZCFYA4V4GJeUPf/705hWdev/sadCPCEr2JLkGqWIrGSCK"
        "w1goPNltsbrZEuRulQIO4M8Ed5+3OpCHKVVG2EoVZ2b6vHHiT0yZXMSR8SEvzPa59t0s124fp7OYCHUoMc4HCj2BI5cE2zHw5okV"
        "3nluhaWVcUww0UamJiNHJzcpLsAlcAq9gPDRNY3kD/allXHe+vwVanPakHn+qTV++uMQvSZRXFQghBuPkAkkWB/WFIfp3oBbd6fZ"
        "GAYq890iAOEgLDmDbBydGnD17e+ZbCMvzfb5cukJPr55kqZK6H8NAHeozZnptujaxFhb6NrIvtL/ZVBcjNWFX9dazn/xMlNt5NRM"
        "n+V/JmiqgrvYO8QjDXIRlWC8zjShcPv3xxgLhXBgfgDDR13vwBNNpGsjGfF4b5uYRdckKj0EO44MY8NBQj5IxrHD69Tm/PL3IV58"
        "epWNGPY97+ggdxDGhkm64SkjU2iqkpb7vfztb0fyX+ttvrU8nSeamLOTHR8tJ1ml4Ckj6YYA5i68drGqwyc7YdqMFcVFr06Y2P1p"
        "u114GeSYPrrz2deXtT/OzTkvuQtWMEfDoj2UHHs4zvcBWFEY9eczbFYAAAAASUVORK5CYII=")
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
