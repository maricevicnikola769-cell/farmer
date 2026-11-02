"""Čitanje teksta iz nalaza laboratorije (PDF, slika).

- PDF napravljen na računaru (laboratorija ga pošalje mejlom): tekst se vadi tačno (pypdf, BSD licenca).
- Slika ili skeniran PDF: prepoznavanje teksta (OCR) ugrađeno u Windows 10/11 – bez dodatnih programa.
  OCR može da pogreši, zato korisnik uvek pregleda tekst pre čuvanja.
"""
import os
import subprocess
import sys
import tempfile

SLIKE = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".webp")
MAKS_STRANA = 6           # duži nalazi su retki; ne čitamo knjige

# Windows OCR preko PowerShell-a (WinRT). Rezultat se piše u UTF-8 fajl (da č, ć, š, ž, đ stignu ispravno).
_PS = r'''
param([string]$Ulaz, [string]$Izlaz, [string]$Jezik)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$m = [System.WindowsRuntimeSystemExtensions].GetMethods()
$asOp = ($m | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$asAct = ($m | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
function Cekaj($op, [Type]$tip) { $t = $asOp.MakeGenericMethod($tip).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
function CekajA($a) { $t = $asAct.Invoke($null, @($a)); $t.Wait(-1) | Out-Null }
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

$eng = $null
foreach ($l in [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages) {
  if ($eng -eq $null -and $l.LanguageTag.ToLower().StartsWith($Jezik.ToLower())) { $eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($l) }
}
if ($eng -eq $null) { $eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if ($eng -eq $null) { throw 'OCR-NEMA-JEZIKA' }

function Procitaj($tok) {
  $dek = Cekaj ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($tok)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bmp = Cekaj ($dek.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $max = [Windows.Media.Ocr.OcrEngine]::MaxImageDimension
  if ($bmp.PixelWidth -gt $max -or $bmp.PixelHeight -gt $max) {
    $k = [Math]::Min($max / $bmp.PixelWidth, $max / $bmp.PixelHeight)
    $tr = New-Object Windows.Graphics.Imaging.BitmapTransform
    $tr.ScaledWidth = [uint32]($dek.PixelWidth * $k); $tr.ScaledHeight = [uint32]($dek.PixelHeight * $k)
    $bmp = Cekaj ($dek.GetSoftwareBitmapAsync($bmp.BitmapPixelFormat, $bmp.BitmapAlphaMode, $tr,
      [Windows.Graphics.Imaging.ExifOrientationMode]::RespectExifOrientation,
      [Windows.Graphics.Imaging.ColorManagementMode]::DoNotColorManage)) ([Windows.Graphics.Imaging.SoftwareBitmap])
  }
  $rez = Cekaj ($eng.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
  ($rez.Lines | % { $_.Text }) -join "`n"
}

$fajl = Cekaj ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Ulaz)) ([Windows.Storage.StorageFile])
$delovi = @()
if ($Ulaz.ToLower().EndsWith('.pdf')) {
  $doc = Cekaj ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($fajl)) ([Windows.Data.Pdf.PdfDocument])
  $n = [Math]::Min([int]$doc.PageCount, MAKS_STRANA)
  for ($i = 0; $i -lt $n; $i++) {
    $str = $doc.GetPage([uint32]$i)
    $tok = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $op = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $op.DestinationWidth = [uint32]2400
    CekajA ($str.RenderToStreamAsync($tok, $op))
    $tok.Seek(0)
    $delovi += (Procitaj $tok)
  }
} else {
  $tok = Cekaj ($fajl.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $delovi += (Procitaj $tok)
}
[IO.File]::WriteAllText($Izlaz, ($delovi -join "`n`n"), (New-Object Text.UTF8Encoding $false))
'''.replace("MAKS_STRANA", str(MAKS_STRANA))

# jezik programa -> jezik prepoznavanja u Windows-u (srpski: latinica)
_OCR_JEZIK = {"sr": "sr-Latn", "en": "en", "de": "de", "fr": "fr", "es": "es", "pt": "pt"}


class GreskaCitanja(Exception):
    pass


def je_pdf(put):
    return put.lower().endswith(".pdf")


def je_slika(put):
    return put.lower().endswith(SLIKE)


def sredi(tekst):
    """Uklanja prazne redove viška i razmake na krajevima redova."""
    redovi, prazan = [], False
    for r in (tekst or "").replace("\r", "").split("\n"):
        r = " ".join(r.split())
        if not r:
            if redovi and not prazan:
                redovi.append("")
            prazan = True
            continue
        redovi.append(r)
        prazan = False
    return "\n".join(redovi).strip()


def tekst_iz_pdf(put):
    """Tačan tekst iz PDF-a napravljenog na računaru; prazno za skeniran PDF (tamo nema teksta, samo slika)."""
    try:
        from pypdf import PdfReader
        r = PdfReader(put)
        if r.is_encrypted:
            r.decrypt("")
        return sredi("\n\n".join((s.extract_text() or "") for s in r.pages[:MAKS_STRANA]))
    except Exception:
        return ""


def ocr_moguc():
    return sys.platform == "win32"


def ocr_windows(put, jezik_koda="sr", vreme=120):
    """Prepoznavanje teksta sa slike / skeniranog PDF-a ugrađenim Windows OCR-om."""
    if not ocr_moguc():
        raise GreskaCitanja("nema-ocr")
    d = tempfile.mkdtemp(prefix="herddoc_ocr_")
    ps, izlaz = os.path.join(d, "ocr.ps1"), os.path.join(d, "tekst.txt")
    try:
        with open(ps, "w", encoding="utf-8-sig") as f:
            f.write(_PS)
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps,
                            os.path.abspath(put), izlaz, _OCR_JEZIK.get(jezik_koda, "en")],
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=vreme, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if not os.path.isfile(izlaz):
            poruka = (r.stderr or b"").decode("utf-8", "replace")
            raise GreskaCitanja("nema-jezika" if "OCR-NEMA-JEZIKA" in poruka else "ocr")
        with open(izlaz, encoding="utf-8") as f:
            return sredi(f.read())
    except subprocess.TimeoutExpired:
        raise GreskaCitanja("ocr")
    except OSError:
        raise GreskaCitanja("ocr")
    finally:
        for p in (ps, izlaz):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass


def procitaj(put, jezik_koda="sr", ocr=None):
    """Vraća (tekst, tacno). tacno=True: tekst izvađen iz PDF-a (bez greške); False: prepoznat sa slike (proveriti).
    Baca GreskaCitanja ako ne može da se pročita."""
    ocr = ocr or ocr_windows
    if je_pdf(put):
        t = tekst_iz_pdf(put)
        if len(t.replace(" ", "")) >= 20:          # ima pravog teksta – tačno
            return t, True
        return sredi(ocr(put, jezik_koda)), False  # skeniran PDF
    if je_slika(put):
        return sredi(ocr(put, jezik_koda)), False
    raise GreskaCitanja("format")
