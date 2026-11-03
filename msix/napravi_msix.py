"""Pravi HerdDoc.msix za Microsoft Store od dist/HerdDoc.exe (pokreće ga GitHub Actions posle PyInstaller-a).

Microsoft Store sam potpisuje MSIX posle provere, pa sertifikat za potpisivanje ne treba.
Identitet paketa (Name, Publisher) se prepisuje iz Partner Center-a u msix/identitet.json.
Upotreba: python msix/napravi_msix.py 2.123   (verzija programa; MSIX dobija 2.123.0.0)
"""
import glob
import json
import os
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

from PIL import Image

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(KOREN, "dist")
FOLDER = os.path.join(DIST, "msix")
ZNAK = os.path.join(KOREN, "assets", "logo", "herddoc-znak.png")

# ime fajla -> (širina, visina, deo površine koji zauzima znak)
SLIKE = {"StoreLogo.png": (50, 50, 1.0), "Square44x44Logo.png": (44, 44, 1.0), "Square44x44Logo.targetsize-256.png": (256, 256, 1.0),
         "Square150x150Logo.png": (150, 150, 0.66), "Wide310x150Logo.png": (310, 150, 0.66), "LargeTile.png": (310, 310, 0.6),
         "SmallTile.png": (71, 71, 0.8)}

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap">
  <Identity Name="{name}" Publisher="{publisher}" Version="{verzija}" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>HerdDoc</DisplayName>
    <PublisherDisplayName>{publisher_name}</PublisherDisplayName>
    <Logo>Images\\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="sr-Latn-RS" />
    <Resource Language="en-US" />
  </Resources>
  <Applications>
    <Application Id="HerdDoc" Executable="HerdDoc.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="HerdDoc" Description="HerdDoc – rodoslov i evidencija stada"
                          BackgroundColor="transparent"
                          Square150x150Logo="Images\\Square150x150Logo.png" Square44x44Logo="Images\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Images\\Wide310x150Logo.png" Square310x310Logo="Images\\LargeTile.png"
                         Square71x71Logo="Images\\SmallTile.png" ShortName="HerdDoc" />
      </uap:VisualElements>
    </Application>
  </Applications>
  <Capabilities>
    <Capability Name="internetClient" />
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""


def napravi_slike(folder):
    znak = Image.open(ZNAK).convert("RGBA")
    os.makedirs(folder, exist_ok=True)
    for ime, (w, h, deo) in SLIKE.items():
        st = int(min(w, h) * deo)
        z = znak.resize((st, st), Image.LANCZOS)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        im.paste(z, ((w - st) // 2, (h - st) // 2), z)
        im.save(os.path.join(folder, ime))


def manifest(verzija, ident):
    return MANIFEST.format(name=escape(ident["Name"]), publisher=escape(ident["Publisher"], {'"': "&quot;"}),
                           publisher_name=escape(ident["PublisherDisplayName"]), verzija=verzija)


def msix_verzija(v):
    delovi = [int(x) for x in str(v).split(".") if x.isdigit()][:3]
    delovi += [0] * (3 - len(delovi))
    return ".".join(str(x) for x in delovi) + ".0"        # Store traži da četvrti broj bude 0


def nadji_makeappx():
    kand = sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\10\bin\10.*\x64\makeappx.exe"), reverse=True)
    if kand:
        return kand[0]
    return shutil.which("makeappx") or shutil.which("makeappx.exe")


def main():
    verzija = msix_verzija(sys.argv[1] if len(sys.argv) > 1 else "1.0")
    with open(os.path.join(KOREN, "msix", "identitet.json"), encoding="utf-8") as f:
        ident = json.load(f)
    shutil.rmtree(FOLDER, ignore_errors=True)
    os.makedirs(FOLDER)
    shutil.copy2(os.path.join(DIST, "HerdDoc.exe"), FOLDER)
    shutil.copy2(os.path.join(KOREN, "farmer.ico"), FOLDER)
    napravi_slike(os.path.join(FOLDER, "Images"))
    with open(os.path.join(FOLDER, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest(verzija, ident))
    alat = nadji_makeappx()
    if not alat:
        sys.exit("makeappx.exe nije pronađen (Windows SDK)")
    izlaz = os.path.join(DIST, "HerdDoc.msix")
    subprocess.run([alat, "pack", "/d", FOLDER, "/p", izlaz, "/o"], check=True)
    print("MSIX:", izlaz, verzija)


if __name__ == "__main__":
    main()
