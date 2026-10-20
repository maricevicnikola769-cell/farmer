"""Farmer – rodoslov stada, srodstvo, inbriding i plan parenja.
Farmer – herd pedigree, relationship, inbreeding and mating plan.

Jedan program na dva jezika (srpski / English). Jezik se bira u programu (dole levo).
Pokretanje: dupli klik na ovaj fajl (potreban je Python 3.8+ sa python.org).
Podaci se čuvaju u CSV tablici (otvara se i u Excelu).
"""
import csv
import json
import os
import shutil
import sys
import traceback
from datetime import date, datetime, timedelta
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

VERZIJA = "2.1"
_IMENA_PODATAKA = ("stado.csv", "herd.csv", "rodoslov_podesavanja.json", "herd_pedigree_settings.json")


def _engleski_exe():
    """Instalacija 'Farmer English' (FarmerEnglish.exe) podrazumevano radi na engleskom."""
    return getattr(sys, "frozen", False) and "english" in os.path.basename(sys.executable).lower()


def _folder_za_podatke():
    """Gde program čuva stado, podešavanja i rezervne kopije.
    - pokrenut kao .py: pored samog fajla;
    - prenosni .exe koji pored sebe već ima podatke: tu;
    - instaliran program: Dokumenti\\Farmer (engleska instalacija: Dokumenti\\Farmer English)."""
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(__file__))
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for ime in _IMENA_PODATAKA:
        if os.path.exists(os.path.join(exe_dir, ime)):
            return exe_dir
    dok = ""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:  # 5 = Dokumenti
            dok = buf.value
    except Exception:
        pass
    if not dok:
        dok = os.path.join(os.path.expanduser("~"), "Documents")
    folder = os.path.join(dok, "Farmer English" if _engleski_exe() else "Farmer")
    try:
        os.makedirs(folder, exist_ok=True)
        return folder
    except OSError:
        return exe_dir


APP_DIR = _folder_za_podatke()


def _prvi_postojeci(*imena):
    for ime in imena:
        if os.path.exists(os.path.join(APP_DIR, ime)):
            return os.path.join(APP_DIR, ime)
    return None


PODESAVANJA = (_prvi_postojeci("rodoslov_podesavanja.json", "herd_pedigree_settings.json")
               or os.path.join(APP_DIR, "rodoslov_podesavanja.json"))


def _jezik_sistema():
    """Jezik Windows-a: srpski, hrvatski, bosanski, crnogorski -> sr, sve ostalo -> en."""
    try:
        import ctypes
        return "sr" if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x1A else "en"
    except Exception:
        import locale
        loc = (locale.getdefaultlocale()[0] or "").lower()
        return "sr" if loc[:2] in ("sr", "hr", "bs", "me", "sh") else "en"


def _izaberi_jezik():
    try:
        with open(PODESAVANJA, encoding="utf-8") as f:
            j = json.load(f).get("jezik")
        if j in ("sr", "en"):
            return j
    except (OSError, ValueError, AttributeError):
        pass
    if os.path.exists(os.path.join(APP_DIR, "stado.csv")):
        return "sr"
    if os.path.exists(os.path.join(APP_DIR, "herd.csv")) or os.path.exists(os.path.join(APP_DIR, "herd_pedigree_settings.json")):
        return "en"
    if getattr(sys, "frozen", False):      # instalacija: Farmer = srpski, Farmer English = engleski
        return "en" if _engleski_exe() else "sr"
    return _jezik_sistema()


_ZUTI_LOGO = _engleski_exe()
JEZIK = _izaberi_jezik()
EN = JEZIK == "en"


def _uz_tablicu(putanja_tablice, sr_nastavak, en_nastavak):
    """Prateći fajl tablice (istorija, podsetnici): postojeći na bilo kom jeziku, inače na trenutnom."""
    baza = os.path.splitext(putanja_tablice)[0]
    za_jezik, drugi = (baza + en_nastavak, baza + sr_nastavak) if EN else (baza + sr_nastavak, baza + en_nastavak)
    if not os.path.exists(za_jezik) and os.path.exists(drugi):
        return drugi
    return za_jezik


def _ime_stada():
    """Podrazumevana tablica: postojeća (stado.csv / herd.csv), inače po jeziku."""
    p = _prvi_postojeci("stado.csv", "herd.csv")
    return os.path.basename(p) if p else ("herd.csv" if EN else "stado.csv")


# vrednosti sačuvane na jednom jeziku (događaji, poreklo, rase...) se pri čitanju prevode na trenutni jezik
_SR_EN = {"stado.csv": "herd.csv", "rodoslov_podesavanja.json": "herd_pedigree_settings.json", "Farmer": "Farmer English", "Poslednje upisana prvo": "Last added first", "Prvo upisana prvo": "First added first", "Po oznaci": "By tag", "Najmlađa prvo": "Youngest first", "Sopstveni odgoj": "Home bred", "Kupljeno": "Purchased", "Uvoz": "Imported", "goveda": "cattle", "ovce": "sheep", "koze": "goats", "svinje": "pigs", "konji": "horses", "mužjak": "male", "ženka": "female", "mladunče": "young", "mladunčad": "young", "%d.%m.%Y.": "%d/%m/%Y", "hibrid": "hybrid", "hibrid ": "hybrid ", "Tera se": "In heat", "Parenje / osemenjavanje": "Mating / insemination", "Podmladak": "Young stock", "romanovska": "romanov", "Romanovska ovca": "Romanov sheep", "Obična ovca": "Common sheep", "Koza": "Goat", "Svinja": "Pig", "Krava": "Cow", "Kobila": "Mare", "Porođaj": "Birth", "Vakcinacija": "Vaccination", "Lečenje": "Treatment", "Merenje težine": "Weighing", "Premeštanje": "Move", "Prodaja": "Sale", "Uginuće": "Death", "Napomena": "Note", "Promena u evidenciji": "Record change", "Parenja": "Matings", "Lečenja": "Treatments", "Porođaji": "Births", "Potomak": "Offspring", "_istorija.csv": "_history.csv", "%d.%m.%Y": "%d/%m/%Y", "_podsetnici.csv": "_reminders.csv", "drugo": "other", "roditelj i potomak": "parent–offspring", "puni brat / sestra": "full sibling", "polubrat / polusestra": "half sibling", "predak i potomak": "ancestor and descendant", "blisko srodni": "closely related", "dalji rod": "distant relatives", "daleko srodni": "very distantly related", "nesrodni": "unrelated", "pol nepoznat": "sex unknown", "odlično": "excellent", "dobro": "good", "prihvatljivo": "acceptable", "rizično": "risky", "ne preporučuje se": "not recommended", "Tablica se ne može učitati": "The table cannot be loaded", "stado_novo.csv": "herd_new.csv", "automatske": "automatic", "srodstvo i parenje": "kinship & mating", "Grla": "Animals", "Parenje": "Mating", "Srodstvo": "Relationship", "Istorija": "History", "Obaveštenja": "Notifications", "Pregled": "Overview", "Promeni tablicu…": "Change table…", "Nije sačuvano": "Not saved", "Greška u tablici": "Error in table", "Tablica je ponovo učitana (izmenjena u Excelu).": "The table was reloaded (changed in Excel).", "Izaberi tablicu sa grlima": "Choose the animals table", "CSV tablica": "CSV table", "Svi fajlovi": "All files", "Uvezi tablicu iz Excela (CSV)": "Import table from Excel (CSV)", "Uvoz nije uspeo": "Import failed", " grla.": " animals.", "Tablica": "Table", "Stado je još prazno": "The herd is still empty", "+  Dodaj prvo grlo": "+  Add first animal", "Uvezi tablicu iz Excela": "Import table from Excel", "Evidencija svih grla sa roditeljima.": "Records of all animals with their parents.", "Pretraga partnera": "Partner search", "Uvezi": "Import", "Otvori u Excelu": "Open in Excel", "+  Novo grlo": "+  New animal", "⌕  Traži po oznaci, markici, rasi…": "⌕  Search by tag, ear tag, breed…", "Svi polovi": "All sexes", "Ženska": "Females", "Muška": "Males", "Svako poreklo": "Any origin", "Samo u zapatu": "Only in herd", "Redosled:": "Order:", "Grlo": "Animal", "Markica": "Ear tag", "Pol": "Sex", "Rasa": "Breed", "Starost": "Age", "Otac": "Sire", "Majka": "Dam", "Upisano": "Added", "Inbriding": "Inbreeding", "Nijedno grlo ne odgovara pretrazi.": "No animal matches the search.", "Promena ušne markice": "Change ear tag", "Ranije markice: ": "Previous ear tags: ", "Nova markica": "New ear tag", "npr. RS 1234-5678. Ostavi prazno da ukloniš markicu.": "e.g. UK 123456 700123. Leave empty to remove the ear tag.", "Sačuvaj": "Save", "Otkaži": "Cancel", "Premeštanje u drugo stado": "Move to another herd", "Sadašnje stado: ": "Current herd: ", "Novo stado": "New herd", "Izaberi postojeće stado ili upiši novi naziv.": "Choose an existing herd or type a new name.", "Datum premeštanja": "Date of move", "Zapiši premeštanje u istoriju grla": "Record the move in the animal's history", "Upiši ili izaberi novo stado.": "Type or choose the new herd.", "Datum nije ispravan. Upiši ga kao 15.03.2026.": "The date is not valid. Enter it as 15/03/2026.", "Grla su već u tom stadu.": "The animals are already in that herd.", "Premesti": "Move", "Preimenovanje stada": "Rename herd", "Novi naziv": "New name", "Upiši novi naziv.": "Type a new name.", "Brisanje svih grla": "Delete all animals", "U evidenciji nema nijednog grla.": "There are no animals in the records.", "Upozorenje": "Warning", "Šta se briše": "What is deleted", "Rezervna kopija": "Backup", "Potvrda": "Confirmation", "Brisanje": "Deletion", "‹  Nazad": "‹  Back", "U evidenciji je sada:": "Currently in the records:", "Razumem, dalje  ›": "I understand, next  ›", "Izaberi šta se briše:": "Choose what is deleted:", "Sva grla i cela istorija": "All animals and the whole history", "Evidencija postaje potpuno prazna, kao novi program.": "The records become completely empty, like a new program.", "Samo grla, istorija ostaje sačuvana": "Animals only, history is kept", "rezervne_kopije": "backups", "Dalje  ›": "Next  ›", "Rezervna kopija je napravljena.": "Backup has been made.", "Otvori folder sa kopijom": "Open backup folder", "Da potvrdiš, upiši tačno reči:": "To confirm, type exactly:", "OBRIŠI SVE": "DELETE ALL", "Potvrđeno.": "Confirmed.", "Dugme „Dalje“ se uključuje kad upišeš tačan tekst.": "The \"Next\" button turns on when you type the exact text.", "Sva grla su obrisana.": "All animals have been deleted.", "Rezervna kopija je sačuvana u folderu:": "The backup is saved in the folder:", "Vrati podatke": "Restore data", "Zatvori": "Close", "sva grla i celu istoriju": "all animals and the whole history", "sva grla (istorija ostaje)": "all animals (history is kept)", "Trajno obriši sve": "Permanently delete all", "Možeš potvrditi brisanje.": "You can confirm the deletion.", "Vraćanje nije uspelo": "Restore failed", "Obriši grlo": "Delete animal", "Grlo obrisano iz liste (ostaje u rodoslovu)": "Animal deleted from the list (kept in the pedigree)", "Grlo vraćeno u stado": "Animal restored to the herd", "Trajno brisanje": "Permanent deletion", "Otvori karton": "Open card", "Izmeni podatke": "Edit details", "Promeni ušnu markicu": "Change ear tag", "Poreklo (rodoslovno stablo)": "Pedigree (family tree)", "Istorija grla (podaci i unos)": "Animal history (details and entry)", "Dodaj događaj…": "Add event…", "Dodaj podsetnik…": "Add reminder…", "Obrisana grla": "Deleted animals", "← Nazad na grla": "← Back to animals", "Nema obrisanih grla.": "There are no deleted animals.", "Stado": "Herd", "Potomaka u rodoslovu": "Offspring in pedigree", "Prvo označi grlo u tabeli.": "First select an animal in the table.", "Vrati u stado": "Restore to herd", "Trajno obriši": "Delete permanently", "Plan za celo stado": "Plan for the whole herd", "npr. K12 ili RS 1234-5678": "e.g. K12 or UK 123456 700123", "Pronađi partnere": "Find partners", "Samo ista rasa": "Same breed only", "Uključi i grla van zapata": "Include animals out of herd", "ženskih": "female", "muških": "male", " i rase": " and breed", " u zapatu.": " in the herd.", "Odnos": "Relation", "Zajednički geni": "Shared genes", "Procena": "Rating", "Najviše ženki po mužjaku:": "Max. females per male:", "(prazno = bez ograničenja)": "(empty = no limit)", "ženskih grla": "female animals", "muških grla": "male animals", "prosečan inbriding potomstva": "average inbreeding of offspring", "parenja iznad granice": "matings above the limit", "Ženka": "Female", "Rasa partnera": "Partner breed", "Inbriding potomka": "Offspring inbreeding", "nema slobodnog partnera": "no free partner", "Opterećenje muških grla": "Load on males", "Koliko ženki je dodeljeno svakom mužjaku u ovom planu.": "How many females are assigned to each male in this plan.", "Prvo grlo": "First animal", "Drugo grlo": "Second animal", "Najsrodniji parovi u zapatu": "Most related pairs in the herd", "Grla koja treba držati odvojeno pri parenju.": "Animals that should be kept apart when mating.", "Nema srodnih parova prema upisanom rodoslovu.": "No related pairs according to the recorded pedigree.", "Grlo A": "Animal A", "Grlo B": "Animal B", "Pregled stada": "Herd overview", "Stanje inbridinga, najčešći očevi i greške u podacima.": "Inbreeding status, most common sires and data errors.", "Granica rizika": "Risk limit", "3,125% – strogo": "3.125% – strict", "6,25% – preporučeno": "6.25% – recommended", "12,5% – blago": "12.5% – mild", "grla u zapatu": "animals in herd", "prosečan inbriding": "average inbreeding", "grla iznad granice": "above the limit", "Najčešći očevi": "Most common sires", "Jedan otac ima više od 30% potomaka u zapatu.": "One sire has more than 30% of the offspring in the herd.", "Očevi još nisu upisani.": "No sires entered yet.", "Grla sa najvećim inbridingom": "Animals with the highest inbreeding", "Ova grla potiču od srodnih roditelja.": "These animals come from related parents.", "Nijedno grlo u zapatu nema inbriding.": "No animal in the herd is inbred.", "Vrsta": "Species", "Muških": "Males", "Ženskih": "Females", "Prosečan F": "Average F", "Najveći F": "Highest F", "Provera podataka": "Data check", "Nisu pronađene greške u rodoslovu.": "No errors found in the pedigree.", "Opasna zona": "Danger zone", "Obriši sva grla…": "Delete all animals…", "poznat samo kao roditelj": "known only as a parent", "obrisano (čuva se u rodoslovu)": "deleted (kept in the pedigree)", "u zapatu": "in herd", "nije u zapatu": "not in herd", "promeni": "change", "Poreklo": "Origin", "nije upisano": "not entered", "Ranije markice": "Previous ear tags", "Ušna markica": "Ear tag", "Rođeno": "Born", "Karenca": "Withdrawal", "Roditelji": "Parents", "otac nepoznat": "sire unknown", "majka nepoznata": "dam unknown", "Dede i babe": "Grandparents", "Udeo gena od predaka": "Share of genes from ancestors", "nema upisanih": "none recorded", "Najbolji partneri": "Best partners", "nema": "none", "+ Dodaj podsetnik": "+ Add reminder", "Svi događaji": "All events", "nema zapisa": "no records", "+ Dodaj događaj": "+ Add event", "Cela istorija  ›": "Full history  ›", "Poreklo – stablo": "Pedigree – tree", "Upiši potomka": "Add offspring", "Svi partneri": "All partners", "Obriši": "Delete", "meso": "meat", "mleko": "milk", "karenca: ": "withdrawal: ", "Datum": "Date", "Događaj": "Event", "Opis": "Description", "Mladi": "Young", "· evidencija": "· record", "Nosivost (trajanje gravidnosti)": "Gestation length", "Nosivost – trajanje gravidnosti": "Gestation length", "Vrsta / rasa": "Species / breed", "Najmanje": "Minimum", "Najviše": "Maximum", "Prosek": "Average", "Nosivost je sačuvana.": "Gestation length saved.", "Podrazumevano": "Defaults", "☑ rođeno: ": "☑ born: ", "✕ mladi nisu upisani u listu": "✕ young not entered in the list", "✕ nije uspelo": "✕ failed", "– ponovljeno parenje": "– repeated mating", "čeka mlade": "waiting for young", "Parenje nije uspelo": "Mating failed", "Parenje označeno kao neuspelo.": "Mating marked as failed.", "Za ovo parenje mladi su već upisani: ": "Young have already been entered for this mating: ", "Gravidnost još traje": "Pregnancy still in progress", "nepoznata": "unknown", "nepoznat": "unknown", "Rođenje mladih": "Birth of young", "Datum rođenja": "Date of birth", "Mrtvorođenih": "Stillborn", "Datum rođenja nije ispravan. Upiši ga kao 15.03.2026.": "The date of birth is not valid. Enter it as 15/03/2026.", "Datum rođenja ne može biti u budućnosti.": "The date of birth cannot be in the future.", "Broj mladih mora biti ceo broj.": "The number of young must be a whole number.", "Upiši koliko je mladih rođeno.": "Enter how many young were born.", "Zabeleži rođenje": "Record birth", "Odmah upiši u listu": "Enter in list now", "Uklanjanje mladih sa spiska": "Removing young from the list", "Ukloni mlade koji neće biti upisani": "Remove young that will not be entered", "Uginulo": "Died", "Koliko ukloniti": "How many to remove", "Razlog": "Reason", "Prodato": "Sold", "Zaklano": "Slaughtered", "Poklonjeno": "Given away", "Drugo": "Other", "Broj mora biti ceo broj.": "The number must be a whole number.", "Ukloni sa spiska": "Remove from list", "Datum rođenja i stado su automatski.": "Date of birth and herd are automatic.", "Oznaka / ime *": "Tag / name *", "Ušna markica (minđuša)": "Ear tag number", "Pol *": "Sex *", "Žensko": "Female", "Muško": "Male", "Ostali mladi": "Remaining young", "Upiši u listu grla": "Enter in animal list", "Ukloni sa spiska…": "Remove from list…", "Svi događaji u stadu – od najnovijeg ka starijim.": "All events in the herd – from newest to oldest.", "Nosivost": "Gestation", "+  Dodaj događaj": "+  Add event", "⌕  Grlo ili markica…": "⌕  Animal or ear tag…", "Prikaži i promene u evidenciji": "Show record changes too", "Nosivost…": "Gestation…", "Dobijeni mladi": "Young born", "nije uspelo": "failed", "Upiši u listu": "Enter in list", "Ukloni…": "Remove…", "Sve": "All", "svih zapisa": "all records", "vakcinacija": "vaccination", "Nema zapisa za izabrani filter.": "No records for the selected filter.", "Prvo označi zapis u tabeli.": "First select a record in the table.", "Automatski zapisi se ne menjaju.": "Automatic records cannot be changed.", "Automatski zapisi se ne brišu.": "Automatic records cannot be deleted.", "Obriši zapis": "Delete record", "Izmeni zapis": "Edit record", "Dvoklik menja zapis. Sivo = automatske promene.": "Double-click edits a record. Grey = automatic changes.", "Datum rođenja nije ispravan. Upiši ga kao 15.03.2022.": "The date of birth is not valid. Enter it as 15/03/2022.", "Grlo ne može biti sopstveni roditelj.": "An animal cannot be its own parent.", "rasa": "breed", "pol": "sex", "datum rođenja": "date of birth", "otac": "sire", "majka": "dam", "poreklo od": "origin from", "Izmena podataka – ": "Details changed – ", "Farmer – kopije": "Farmer – backups", "danas": "today", "juče": "yesterday", "Kopija: još nije napravljena": "Backup: not made yet", "rucne": "manual", "Kopije će se praviti i na izabranoj lokaciji.": "Backups will also be made in the chosen location.", "Vraćanje iz kopije": "Restore from backup", "Još nema nijedne rezervne kopije.": "There are no backups yet.", "Vraćanje iz rezervne kopije": "Restore from backup", "Datum i vreme": "Date and time", "Lokacija": "Location", "%d.%m.%Y. %H:%M": "%d/%m/%Y %H:%M", "automatska (dnevna)": "automatic (daily)", "ručna": "manual", "druga lokacija": "second location", "pored programa": "next to the program", "_pre_vracanja": "_before_restore", "Vrati izabranu kopiju": "Restore selected backup", "Otvori folder": "Open folder", "Rezervne kopije": "Backups", "%d.%m.%Y. u %H:%M": "%d/%m/%Y at %H:%M", "još nije napravljena": "not made yet", "Napravi kopiju sada": "Make backup now", "Vrati iz kopije…": "Restore from backup…", "Druga lokacija…": "Second location…", "Zabeleženo: ne tera se – verovatno je gravidna.": "Recorded: not in heat – probably pregnant.", "Ne tera se": "Not in heat", "Očekuje se ter ": "Heat expected ", "Upiši parenje": "Record mating", "Karenca – ": "Withdrawal – ", "Karenca meso (dana)": "Meat withdrawal (days)", "mleko (dana)": "milk (days)", "mrtvorođenih:\\s*(\\d+)": "stillborn:\\s*(\\d+)", "Plodnost ženki": "Female fertility", "Još nema upisanih parenja ni porođaja.": "No matings or births recorded yet.", "Porođaja": "Births", "Živih": "Alive", "Mrtvih": "Stillborn", "Razmak (d.)": "Interval (d.)", "Parenja/porođ.": "Matings/birth", "Poslednji": "Last", "Nije uspelo": "Failed", "Porođaj se očekuje ": "Birth expected ", "svakog dana": "any day now", "sutra": "tomorrow", "Urađeno": "Done", "Odloži 7 d.": "Postpone 7 d.", "Izmeni": "Edit", "Prikaži": "Show", "Hitno": "Urgent", "Uskoro": "Soon", "Zakazano": "Scheduled", "Nema ničeg hitnog.": "Nothing urgent.", "+  Novi podsetnik": "+  New reminder", "Za informaciju": "For information", "Otvori obaveštenja": "Open notifications", "Kasnije": "Later", "urađeno po podsetniku": "done as reminded", " · sledeći je zakazan": " · the next one is scheduled", "Izmena podsetnika": "Edit reminder", "Novi podsetnik": "New reminder", "Grlo (prazno = celo stado)": "Animal (empty = whole herd)", "Šta treba uraditi": "What needs to be done", "Ponavljanje": "Repeat", "ne ponavlja se": "does not repeat", "svake nedelje": "every week", "svakog meseca": "every month", "na 3 meseca": "every 3 months", "na 6 meseci": "every 6 months", "svake godine": "every year", "Izaberi šta treba uraditi.": "Choose what needs to be done.", "Obriši podsetnik": "Delete reminder", "Obrisati ovaj podsetnik?": "Delete this reminder?", "Podsetnik obrisan.": "Reminder deleted.", "Drugo…": "Other…", "npr. Kastracija, Odbijanje…": "e.g. Castration, Weaning…", "obrisano": "deleted", "van zapata": "out of herd", "Karton": "Card", "Podaci o grlu": "Animal details", "Izmeni polje i klikni „Sačuvaj podatke“.": "Edit a field and click \"Save details\".", "Od koga / odakle": "From whom / where", "U zapatu (nije prodato ni uginulo)": "In herd (not sold or dead)", "Potomaka": "Offspring", "Poznatih predaka": "Known ancestors", "melez": "crossbred", "Sačuvaj podatke": "Save details", "Novi zapis u istoriju": "New history record", "Događaj – klikni na vrstu": "Event – click a type", "Vrednost": "Value", "Opis / napomena": "Description / note", "Težina (kg)": "Weight (kg)", "Vakcina / preparat": "Vaccine / product", "Lek / dijagnoza": "Drug / diagnosis", "Kupac / cena": "Buyer / price", "Broj mladunaca": "Number of young", "Prirodno / VO": "Natural / AI", "Partner (bik / ovan…)": "Partner (bull / ram…)", "Izaberi vrstu događaja klikom na jedno od dugmadi.": "Choose the event type by clicking one of the buttons.", "Grlo će biti označeno kao van zapata.": "The animal will be marked as out of herd.", "Izaberi vrstu događaja (parenje, lečenje, porođaj…).": "Choose the event type (mating, treatment, birth…).", "+  Dodaj zapis": "+  Add record", "Izmena događaja": "Edit event", "Novi događaj": "New event", "Grlo *": "Animal *", "Datum *": "Date *", "Događaj * – klikni na vrstu": "Event * – click a type", "Označi grlo kao van zapata": "Mark the animal as out of herd", "Novo stado / lokacija": "New herd / location", "Način (prirodno / VO)": "Method (natural / AI)", "Izaberi grlo sa spiska (oznaka ili markica).": "Choose an animal from the list (tag or ear tag).", "Izaberi događaj.": "Choose an event.", "roditelj": "parent", "deda / baba": "grandparent", "pradeda / prababa": "great-grandparent", "čukundeda / čukunbaba": "great-great-grandparent", "Stablo": "Tree", "Prikaži generacija:": "Generations shown:", "Za ovo grlo nisu upisani roditelji.": "No parents are entered for this animal.", "Nijedan predak se ne ponavlja u celom poznatom rodoslovu.": "No ancestor is repeated in the whole known pedigree.", "Deca": "Children", "Unuci": "Grandchildren", "Praunuci": "Great-grandchildren", "Čukununuci": "Great-great-grandchildren", "Nema upisanih potomaka.": "No descendants recorded.", "Ovo grlo još nema upisanih potomaka.": "This animal has no recorded descendants yet.", "Drugi roditelj": "Other parent", "Udeo gena": "Share of genes", "Rođen": "Born", "  Rođeni, još bez minđuše": "  Born, no ear tag yet", "čeka upis u listu": "waiting for entry in the list", "Dvoklik na potomka otvara njegov karton.": "Double-click a descendant to open its card.", "po ocu": "paternal", "po majci": "maternal", "sestra": "sister", "brat": "brother", "Braća i sestre": "Siblings", "pun ": "full ", "polu": "half-", "Nećaci (deca braće i sestara)": "Nephews and nieces (children of siblings)", "stric": "uncle", "tetka": "aunt", "ujak": "uncle", "Braća i sestre roditelja": "Siblings of parents", " (polu)": " (half)", "Prvi rođaci": "First cousins", "Srodnik": "Relative", "Inbriding mladih": "Inbreeding of young", "Kompletnost rodoslova:  ": "Pedigree completeness:  ", "Predak": "Ancestor", "Generacija": "Generation", "Puta": "Times", ". generacija": " generations", "Pradede i prababe": "Great-grandparents", "Čukundede i čukunbabe": "Great-great-grandparents", "Izmena grla": "Edit animal", "Novo grlo": "New animal", "Oznaka grla *": "Animal tag *", "npr. K12 ili ime": "e.g. K12 or a name", "npr. RS 1234-5678": "e.g. UK 123456 700123", "dan.mesec.godina, npr. 15.03.2022": "day/month/year, e.g. 15/03/2022", "Stado / lokacija": "Herd / location", "oznaka ili markica; prazno ako je nepoznat": "tag or ear tag; empty if unknown", "oznaka ili markica; prazno ako je nepoznata": "tag or ear tag; empty if unknown", "Grlo je u zapatu (nije prodato ni uginulo)": "The animal is in the herd (not sold or dead)", "Upiši oznaku grla.": "Enter the animal's tag.", " Obrisano je – vrati ga iz liste „Obrisana grla“.": " It is deleted – restore it from the \"Deleted animals\" list.", "Izaberi pol.": "Choose the sex.", "Datum nije ispravan. Upiši ga kao 15.03.2022.": "The date is not valid. Enter it as 15/03/2022.", "stado": "herd", "Grlo upisano u evidenciju": "Animal added to the records", "Sačuvaj i dodaj još": "Save and add another", "Farmer.Program": "Farmer.English", "Greška": "Error", "Farmer – greška": "Farmer – error"}
_EN_SR = {"herd.csv": "stado.csv", "herd_pedigree_settings.json": "rodoslov_podesavanja.json", "Farmer English": "Farmer", "Last added first": "Poslednje upisana prvo", "First added first": "Prvo upisana prvo", "By tag": "Po oznaci", "Youngest first": "Najmlađa prvo", "Home bred": "Sopstveni odgoj", "Purchased": "Kupljeno", "Imported": "Uvoz", "cattle": "goveda", "sheep": "ovce", "goats": "koze", "pigs": "svinje", "horses": "konji", "male": "muških", "female": "ženskih", "young": "mladunče", "%d/%m/%Y": "%d.%m.%Y", "hybrid": "hibrid", "hybrid ": "hibrid ", "In heat": "Tera se", "Mating / insemination": "Parenje / osemenjavanje", "Young stock": "Podmladak", "romanov": "romanovska", "Romanov sheep": "Romanovska ovca", "Common sheep": "Obična ovca", "Goat": "Koza", "Pig": "Svinja", "Cow": "Krava", "Mare": "Kobila", "Birth": "Porođaj", "Vaccination": "Vakcinacija", "Treatment": "Lečenje", "Weighing": "Merenje težine", "Move": "Premeštanje", "Sale": "Prodaja", "Death": "Uginuće", "Note": "Napomena", "Record change": "Promena u evidenciji", "Matings": "Parenja", "Treatments": "Lečenja", "Births": "Porođaji", "Offspring": "Potomak", "_history.csv": "_istorija.csv", "_reminders.csv": "_podsetnici.csv", "other": "drugo", "parent–offspring": "roditelj i potomak", "full sibling": "puni brat / sestra", "half sibling": "polubrat / polusestra", "ancestor and descendant": "predak i potomak", "closely related": "blisko srodni", "distant relatives": "dalji rod", "very distantly related": "daleko srodni", "unrelated": "nesrodni", "sex unknown": "pol nepoznat", "excellent": "odlično", "good": "dobro", "acceptable": "prihvatljivo", "risky": "rizično", "not recommended": "ne preporučuje se", "The table cannot be loaded": "Tablica se ne može učitati", "herd_new.csv": "stado_novo.csv", "automatic": "automatske", "kinship & mating": "srodstvo i parenje", "Animals": "Grla", "Mating": "Parenje", "Relationship": "Srodstvo", "History": "Istorija", "Notifications": "Obaveštenja", "Overview": "Pregled", "Change table…": "Promeni tablicu…", "Not saved": "Nije sačuvano", "Error in table": "Greška u tablici", "The table was reloaded (changed in Excel).": "Tablica je ponovo učitana (izmenjena u Excelu).", "Choose the animals table": "Izaberi tablicu sa grlima", "CSV table": "CSV tablica", "All files": "Svi fajlovi", "Import table from Excel (CSV)": "Uvezi tablicu iz Excela (CSV)", "Import failed": "Uvoz nije uspeo", " animals.": " grla.", "Table": "Tablica", "The herd is still empty": "Stado je još prazno", "+  Add first animal": "+  Dodaj prvo grlo", "Import table from Excel": "Uvezi tablicu iz Excela", "Records of all animals with their parents.": "Evidencija svih grla sa roditeljima.", "Partner search": "Pretraga partnera", "Import": "Uvezi", "Open in Excel": "Otvori u Excelu", "+  New animal": "+  Novo grlo", "⌕  Search by tag, ear tag, breed…": "⌕  Traži po oznaci, markici, rasi…", "All sexes": "Svi polovi", "Females": "Ženska", "Males": "Muška", "Any origin": "Svako poreklo", "Only in herd": "Samo u zapatu", "Order:": "Redosled:", "Animal": "Grlo", "Ear tag": "Markica", "Sex": "Pol", "Breed": "Rasa", "Age": "Starost", "Sire": "Otac", "Dam": "Majka", "Added": "Upisano", "Inbreeding": "Inbriding", "No animal matches the search.": "Nijedno grlo ne odgovara pretrazi.", "Change ear tag": "Promena ušne markice", "Previous ear tags: ": "Ranije markice: ", "New ear tag": "Nova markica", "e.g. UK 123456 700123. Leave empty to remove the ear tag.": "npr. RS 1234-5678. Ostavi prazno da ukloniš markicu.", "Save": "Sačuvaj", "Cancel": "Otkaži", "Move to another herd": "Premeštanje u drugo stado", "Current herd: ": "Sadašnje stado: ", "New herd": "Novo stado", "Choose an existing herd or type a new name.": "Izaberi postojeće stado ili upiši novi naziv.", "Date of move": "Datum premeštanja", "Record the move in the animal's history": "Zapiši premeštanje u istoriju grla", "Type or choose the new herd.": "Upiši ili izaberi novo stado.", "The date is not valid. Enter it as 15/03/2026.": "Datum nije ispravan. Upiši ga kao 15.03.2026.", "The animals are already in that herd.": "Grla su već u tom stadu.", "Rename herd": "Preimenovanje stada", "New name": "Novi naziv", "Type a new name.": "Upiši novi naziv.", "Delete all animals": "Brisanje svih grla", "There are no animals in the records.": "U evidenciji nema nijednog grla.", "Warning": "Upozorenje", "What is deleted": "Šta se briše", "Backup": "Rezervna kopija", "Confirmation": "Potvrda", "Deletion": "Brisanje", "‹  Back": "‹  Nazad", "Currently in the records:": "U evidenciji je sada:", "I understand, next  ›": "Razumem, dalje  ›", "Choose what is deleted:": "Izaberi šta se briše:", "All animals and the whole history": "Sva grla i cela istorija", "The records become completely empty, like a new program.": "Evidencija postaje potpuno prazna, kao novi program.", "Animals only, history is kept": "Samo grla, istorija ostaje sačuvana", "backups": "rezervne_kopije", "Next  ›": "Dalje  ›", "Backup has been made.": "Rezervna kopija je napravljena.", "Open backup folder": "Otvori folder sa kopijom", "To confirm, type exactly:": "Da potvrdiš, upiši tačno reči:", "DELETE ALL": "OBRIŠI SVE", "Confirmed.": "Potvrđeno.", "The \"Next\" button turns on when you type the exact text.": "Dugme „Dalje“ se uključuje kad upišeš tačan tekst.", "All animals have been deleted.": "Sva grla su obrisana.", "The backup is saved in the folder:": "Rezervna kopija je sačuvana u folderu:", "Restore data": "Vrati podatke", "Close": "Zatvori", "all animals and the whole history": "sva grla i celu istoriju", "all animals (history is kept)": "sva grla (istorija ostaje)", "Permanently delete all": "Trajno obriši sve", "You can confirm the deletion.": "Možeš potvrditi brisanje.", "Restore failed": "Vraćanje nije uspelo", "Delete animal": "Obriši grlo", "Animal deleted from the list (kept in the pedigree)": "Grlo obrisano iz liste (ostaje u rodoslovu)", "Animal restored to the herd": "Grlo vraćeno u stado", "Permanent deletion": "Trajno brisanje", "Open card": "Otvori karton", "Edit details": "Izmeni podatke", "Pedigree (family tree)": "Poreklo (rodoslovno stablo)", "Animal history (details and entry)": "Istorija grla (podaci i unos)", "Add event…": "Dodaj događaj…", "Add reminder…": "Dodaj podsetnik…", "Deleted animals": "Obrisana grla", "← Back to animals": "← Nazad na grla", "There are no deleted animals.": "Nema obrisanih grla.", "Herd": "Stado", "Offspring in pedigree": "Potomaka u rodoslovu", "First select an animal in the table.": "Prvo označi grlo u tabeli.", "Restore to herd": "Vrati u stado", "Delete permanently": "Trajno obriši", "Plan for the whole herd": "Plan za celo stado", "e.g. K12 or UK 123456 700123": "npr. K12 ili RS 1234-5678", "Find partners": "Pronađi partnere", "Same breed only": "Samo ista rasa", "Include animals out of herd": "Uključi i grla van zapata", " and breed": " i rase", " in the herd.": " u zapatu.", "Relation": "Odnos", "Shared genes": "Zajednički geni", "Rating": "Procena", "Max. females per male:": "Najviše ženki po mužjaku:", "(empty = no limit)": "(prazno = bez ograničenja)", "female animals": "ženskih grla", "male animals": "muških grla", "average inbreeding of offspring": "prosečan inbriding potomstva", "matings above the limit": "parenja iznad granice", "Female": "Ženka", "Partner breed": "Rasa partnera", "Offspring inbreeding": "Inbriding potomka", "no free partner": "nema slobodnog partnera", "Load on males": "Opterećenje muških grla", "How many females are assigned to each male in this plan.": "Koliko ženki je dodeljeno svakom mužjaku u ovom planu.", "First animal": "Prvo grlo", "Second animal": "Drugo grlo", "Most related pairs in the herd": "Najsrodniji parovi u zapatu", "Animals that should be kept apart when mating.": "Grla koja treba držati odvojeno pri parenju.", "No related pairs according to the recorded pedigree.": "Nema srodnih parova prema upisanom rodoslovu.", "Animal A": "Grlo A", "Animal B": "Grlo B", "Herd overview": "Pregled stada", "Inbreeding status, most common sires and data errors.": "Stanje inbridinga, najčešći očevi i greške u podacima.", "Risk limit": "Granica rizika", "3.125% – strict": "3,125% – strogo", "6.25% – recommended": "6,25% – preporučeno", "12.5% – mild": "12,5% – blago", "animals in herd": "grla u zapatu", "average inbreeding": "prosečan inbriding", "above the limit": "grla iznad granice", "Most common sires": "Najčešći očevi", "One sire has more than 30% of the offspring in the herd.": "Jedan otac ima više od 30% potomaka u zapatu.", "No sires entered yet.": "Očevi još nisu upisani.", "Animals with the highest inbreeding": "Grla sa najvećim inbridingom", "These animals come from related parents.": "Ova grla potiču od srodnih roditelja.", "No animal in the herd is inbred.": "Nijedno grlo u zapatu nema inbriding.", "Species": "Vrsta", "Average F": "Prosečan F", "Highest F": "Najveći F", "Data check": "Provera podataka", "No errors found in the pedigree.": "Nisu pronađene greške u rodoslovu.", "Danger zone": "Opasna zona", "Delete all animals…": "Obriši sva grla…", "known only as a parent": "poznat samo kao roditelj", "deleted (kept in the pedigree)": "obrisano (čuva se u rodoslovu)", "in herd": "u zapatu", "not in herd": "nije u zapatu", "change": "promeni", "Origin": "Poreklo", "not entered": "nije upisano", "Previous ear tags": "Ranije markice", "Born": "Rođen", "Withdrawal": "Karenca", "Parents": "Roditelji", "sire unknown": "otac nepoznat", "dam unknown": "majka nepoznata", "Grandparents": "Dede i babe", "Share of genes from ancestors": "Udeo gena od predaka", "none recorded": "nema upisanih", "Best partners": "Najbolji partneri", "none": "nema", "+ Add reminder": "+ Dodaj podsetnik", "All events": "Svi događaji", "no records": "nema zapisa", "+ Add event": "+ Dodaj događaj", "Full history  ›": "Cela istorija  ›", "Pedigree – tree": "Poreklo – stablo", "Add offspring": "Upiši potomka", "All partners": "Svi partneri", "Delete": "Obriši", "meat": "meso", "milk": "mleko", "withdrawal: ": "karenca: ", "Date": "Datum", "Event": "Događaj", "Description": "Opis", "Young": "Mladi", "· record": "· evidencija", "Gestation length": "Nosivost (trajanje gravidnosti)", "Species / breed": "Vrsta / rasa", "Minimum": "Najmanje", "Maximum": "Najviše", "Average": "Prosek", "Gestation length saved.": "Nosivost je sačuvana.", "Defaults": "Podrazumevano", "☑ born: ": "☑ rođeno: ", "✕ young not entered in the list": "✕ mladi nisu upisani u listu", "✕ failed": "✕ nije uspelo", "– repeated mating": "– ponovljeno parenje", "waiting for young": "čeka mlade", "Mating failed": "Parenje nije uspelo", "Mating marked as failed.": "Parenje označeno kao neuspelo.", "Young have already been entered for this mating: ": "Za ovo parenje mladi su već upisani: ", "Pregnancy still in progress": "Gravidnost još traje", "unknown": "nepoznat", "Birth of young": "Rođenje mladih", "Date of birth": "Datum rođenja", "Stillborn": "Mrtvorođenih", "The date of birth is not valid. Enter it as 15/03/2026.": "Datum rođenja nije ispravan. Upiši ga kao 15.03.2026.", "The date of birth cannot be in the future.": "Datum rođenja ne može biti u budućnosti.", "The number of young must be a whole number.": "Broj mladih mora biti ceo broj.", "Enter how many young were born.": "Upiši koliko je mladih rođeno.", "Record birth": "Zabeleži rođenje", "Enter in list now": "Odmah upiši u listu", "Removing young from the list": "Uklanjanje mladih sa spiska", "Remove young that will not be entered": "Ukloni mlade koji neće biti upisani", "Died": "Uginulo", "How many to remove": "Koliko ukloniti", "Reason": "Razlog", "Sold": "Prodato", "Slaughtered": "Zaklano", "Given away": "Poklonjeno", "Other": "Drugo", "The number must be a whole number.": "Broj mora biti ceo broj.", "Remove from list": "Ukloni sa spiska", "Date of birth and herd are automatic.": "Datum rođenja i stado su automatski.", "Tag / name *": "Oznaka / ime *", "Ear tag number": "Ušna markica (minđuša)", "Sex *": "Pol *", "Male": "Muško", "Remaining young": "Ostali mladi", "Enter in animal list": "Upiši u listu grla", "Remove from list…": "Ukloni sa spiska…", "All events in the herd – from newest to oldest.": "Svi događaji u stadu – od najnovijeg ka starijim.", "Gestation": "Nosivost", "+  Add event": "+  Dodaj događaj", "⌕  Animal or ear tag…": "⌕  Grlo ili markica…", "Show record changes too": "Prikaži i promene u evidenciji", "Gestation…": "Nosivost…", "Young born": "Dobijeni mladi", "failed": "nije uspelo", "Enter in list": "Upiši u listu", "Remove…": "Ukloni…", "All": "Sve", "all records": "svih zapisa", "vaccination": "vakcinacija", "No records for the selected filter.": "Nema zapisa za izabrani filter.", "First select a record in the table.": "Prvo označi zapis u tabeli.", "Automatic records cannot be changed.": "Automatski zapisi se ne menjaju.", "Automatic records cannot be deleted.": "Automatski zapisi se ne brišu.", "Delete record": "Obriši zapis", "Edit record": "Izmeni zapis", "Double-click edits a record. Grey = automatic changes.": "Dvoklik menja zapis. Sivo = automatske promene.", "The date of birth is not valid. Enter it as 15/03/2022.": "Datum rođenja nije ispravan. Upiši ga kao 15.03.2022.", "An animal cannot be its own parent.": "Grlo ne može biti sopstveni roditelj.", "breed": "rasa", "sex": "pol", "date of birth": "datum rođenja", "sire": "otac", "dam": "majka", "origin from": "poreklo od", "Details changed – ": "Izmena podataka – ", "Farmer – backups": "Farmer – kopije", "today": "danas", "yesterday": "juče", "Backup: not made yet": "Kopija: još nije napravljena", "manual": "rucne", "Backups will also be made in the chosen location.": "Kopije će se praviti i na izabranoj lokaciji.", "Restore from backup": "Vraćanje iz kopije", "There are no backups yet.": "Još nema nijedne rezervne kopije.", "Date and time": "Datum i vreme", "Type": "Vrsta", "Location": "Lokacija", "%d/%m/%Y %H:%M": "%d.%m.%Y. %H:%M", "automatic (daily)": "automatska (dnevna)", "second location": "druga lokacija", "next to the program": "pored programa", "_before_restore": "_pre_vracanja", "Restore selected backup": "Vrati izabranu kopiju", "Open folder": "Otvori folder", "Backups": "Rezervne kopije", "%d/%m/%Y at %H:%M": "%d.%m.%Y. u %H:%M", "not made yet": "još nije napravljena", "Make backup now": "Napravi kopiju sada", "Restore from backup…": "Vrati iz kopije…", "Second location…": "Druga lokacija…", "Recorded: not in heat – probably pregnant.": "Zabeleženo: ne tera se – verovatno je gravidna.", "Not in heat": "Ne tera se", "Heat expected ": "Očekuje se ter ", "Record mating": "Upiši parenje", "Withdrawal – ": "Karenca – ", "Meat withdrawal (days)": "Karenca meso (dana)", "milk (days)": "mleko (dana)", "stillborn:\\s*(\\d+)": "mrtvorođenih:\\s*(\\d+)", "Female fertility": "Plodnost ženki", "No matings or births recorded yet.": "Još nema upisanih parenja ni porođaja.", "Alive": "Živih", "Interval (d.)": "Razmak (d.)", "Matings/birth": "Parenja/porođ.", "Last": "Poslednji", "Failed": "Nije uspelo", "Birth expected ": "Porođaj se očekuje ", "any day now": "svakog dana", "tomorrow": "sutra", "Done": "Urađeno", "Postpone 7 d.": "Odloži 7 d.", "Edit": "Izmeni", "Show": "Prikaži", "Urgent": "Hitno", "Soon": "Uskoro", "Scheduled": "Zakazano", "Nothing urgent.": "Nema ničeg hitnog.", "+  New reminder": "+  Novi podsetnik", "For information": "Za informaciju", "Open notifications": "Otvori obaveštenja", "Later": "Kasnije", "done as reminded": "urađeno po podsetniku", " · the next one is scheduled": " · sledeći je zakazan", "Edit reminder": "Izmena podsetnika", "New reminder": "Novi podsetnik", "Animal (empty = whole herd)": "Grlo (prazno = celo stado)", "What needs to be done": "Šta treba uraditi", "Repeat": "Ponavljanje", "does not repeat": "ne ponavlja se", "every week": "svake nedelje", "every month": "svakog meseca", "every 3 months": "na 3 meseca", "every 6 months": "na 6 meseci", "every year": "svake godine", "Choose what needs to be done.": "Izaberi šta treba uraditi.", "Delete reminder": "Obriši podsetnik", "Delete this reminder?": "Obrisati ovaj podsetnik?", "Reminder deleted.": "Podsetnik obrisan.", "Other…": "Drugo…", "e.g. Castration, Weaning…": "npr. Kastracija, Odbijanje…", "deleted": "obrisano", "out of herd": "van zapata", "Card": "Karton", "Animal details": "Podaci o grlu", "Edit a field and click \"Save details\".": "Izmeni polje i klikni „Sačuvaj podatke“.", "From whom / where": "Od koga / odakle", "In herd (not sold or dead)": "U zapatu (nije prodato ni uginulo)", "Known ancestors": "Poznatih predaka", "crossbred": "melez", "Save details": "Sačuvaj podatke", "New history record": "Novi zapis u istoriju", "Event – click a type": "Događaj – klikni na vrstu", "Value": "Vrednost", "Description / note": "Opis / napomena", "Weight (kg)": "Težina (kg)", "Vaccine / product": "Vakcina / preparat", "Drug / diagnosis": "Lek / dijagnoza", "Buyer / price": "Kupac / cena", "Number of young": "Broj mladunaca", "Natural / AI": "Prirodno / VO", "Partner (bull / ram…)": "Partner (bik / ovan…)", "Choose the event type by clicking one of the buttons.": "Izaberi vrstu događaja klikom na jedno od dugmadi.", "The animal will be marked as out of herd.": "Grlo će biti označeno kao van zapata.", "Choose the event type (mating, treatment, birth…).": "Izaberi vrstu događaja (parenje, lečenje, porođaj…).", "+  Add record": "+  Dodaj zapis", "Edit event": "Izmena događaja", "New event": "Novi događaj", "Animal *": "Grlo *", "Date *": "Datum *", "Event * – click a type": "Događaj * – klikni na vrstu", "Mark the animal as out of herd": "Označi grlo kao van zapata", "New herd / location": "Novo stado / lokacija", "Method (natural / AI)": "Način (prirodno / VO)", "Choose an animal from the list (tag or ear tag).": "Izaberi grlo sa spiska (oznaka ili markica).", "Choose an event.": "Izaberi događaj.", "parent": "roditelj", "grandparent": "deda / baba", "great-grandparent": "pradeda / prababa", "great-great-grandparent": "čukundeda / čukunbaba", "Tree": "Stablo", "Generations shown:": "Prikaži generacija:", "No parents are entered for this animal.": "Za ovo grlo nisu upisani roditelji.", "No ancestor is repeated in the whole known pedigree.": "Nijedan predak se ne ponavlja u celom poznatom rodoslovu.", "Children": "Deca", "Grandchildren": "Unuci", "Great-grandchildren": "Praunuci", "Great-great-grandchildren": "Čukununuci", "No descendants recorded.": "Nema upisanih potomaka.", "This animal has no recorded descendants yet.": "Ovo grlo još nema upisanih potomaka.", "Other parent": "Drugi roditelj", "Share of genes": "Udeo gena", "  Born, no ear tag yet": "  Rođeni, još bez minđuše", "waiting for entry in the list": "čeka upis u listu", "Double-click a descendant to open its card.": "Dvoklik na potomka otvara njegov karton.", "paternal": "po ocu", "maternal": "po majci", "sister": "sestra", "brother": "brat", "Siblings": "Braća i sestre", "full ": "pun ", "half-": "polu", "Nephews and nieces (children of siblings)": "Nećaci (deca braće i sestara)", "uncle": "stric", "aunt": "tetka", "Siblings of parents": "Braća i sestre roditelja", " (half)": " (polu)", "First cousins": "Prvi rođaci", "Relative": "Srodnik", "Inbreeding of young": "Inbriding mladih", "Pedigree completeness:  ": "Kompletnost rodoslova:  ", "Ancestor": "Predak", "Generation": "Generacija", "Times": "Puta", " generations": ". generacija", "Great-grandparents": "Pradede i prababe", "Great-great-grandparents": "Čukundede i čukunbabe", "Edit animal": "Izmena grla", "New animal": "Novo grlo", "Animal tag *": "Oznaka grla *", "e.g. K12 or a name": "npr. K12 ili ime", "e.g. UK 123456 700123": "npr. RS 1234-5678", "day/month/year, e.g. 15/03/2022": "dan.mesec.godina, npr. 15.03.2022", "Herd / location": "Stado / lokacija", "tag or ear tag; empty if unknown": "oznaka ili markica; prazno ako je nepoznat", "The animal is in the herd (not sold or dead)": "Grlo je u zapatu (nije prodato ni uginulo)", "Enter the animal's tag.": "Upiši oznaku grla.", " It is deleted – restore it from the \"Deleted animals\" list.": " Obrisano je – vrati ga iz liste „Obrisana grla“.", "Choose the sex.": "Izaberi pol.", "The date is not valid. Enter it as 15/03/2022.": "Datum nije ispravan. Upiši ga kao 15.03.2022.", "herd": "stado", "Animal added to the records": "Grlo upisano u evidenciju", "Save and add another": "Sačuvaj i dodaj još", "Farmer.English": "Farmer.Program", "Error": "Greška", "Farmer – error": "Farmer – greška"}


def prevedi_vrednost(v):
    return (_SR_EN.get(v, v) if v not in _EN_SR else v) if EN else (_EN_SR.get(v, v) if v not in _SR_EN else v)

KOLONE = ["id", "markica", "vrsta", "rasa", "pol", "datum_rodjenja", "otac", "majka", "status", "stado",
          "poreklo", "poreklo_od", "stare_markice", "uneto"]
REDOSLEDI = [("Last added first" if EN else "Poslednje upisana prvo"), ("First added first" if EN else "Prvo upisana prvo"), ("By tag" if EN else "Po oznaci"), ("Youngest first" if EN else "Najmlađa prvo")]


def sada():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
POREKLA = [("Home bred" if EN else "Sopstveni odgoj"), ("Purchased" if EN else "Kupljeno"), ("Imported" if EN else "Uvoz")]
VRSTE = [("cattle" if EN else "goveda"), ("sheep" if EN else "ovce"), ("goats" if EN else "koze"), ("pigs" if EN else "svinje"), ("horses" if EN else "konji")]
if EN:
    NAZIVI = {   # species prefix (English and Serbian) -> (male, female, young, young plural)
        "cat": ("bull", "cow", "calf", "calves"), "cow": ("bull", "cow", "calf", "calves"),
        "bul": ("bull", "cow", "calf", "calves"), "gov": ("bull", "cow", "calf", "calves"),
        "she": ("ram", "ewe", "lamb", "lambs"), "ewe": ("ram", "ewe", "lamb", "lambs"), "ovc": ("ram", "ewe", "lamb", "lambs"),
        "goa": ("buck", "doe", "kid", "kids"), "koz": ("buck", "doe", "kid", "kids"),
        "pig": ("boar", "sow", "piglet", "piglets"), "sow": ("boar", "sow", "piglet", "piglets"),
        "svi": ("boar", "sow", "piglet", "piglets"),
        "hor": ("stallion", "mare", "foal", "foals"), "kon": ("stallion", "mare", "foal", "foals"),
    }
else:
    NAZIVI = {
        "gov": ("bik", "krava", "tele", "telad"), "bik": ("bik", "krava", "tele", "telad"),
        "kra": ("bik", "krava", "tele", "telad"), "ovc": ("ovan", "ovca", "jagnje", "jagnjad"),
        "ova": ("ovan", "ovca", "jagnje", "jagnjad"), "koz": ("jarac", "koza", "jare", "jarad"),
        "svi": ("nerast", "krmača", "prase", "prasad"), "kon": ("pastuv", "kobila", "ždrebe", "ždrebad"),
    }


# logo programa (PNG, ugrađen da program radi kao jedan fajl)
LOGO = {
    64: (
        ("iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAJL0lEQVR42u2bbYxcZRXHf+e5986dO7Mzu33ZbaFLEShtwYZKIZBA"
        "QUhQoVU+SIyBGsEaNSRIQhBj0C9EhA+EBCVEkQQwkRAoUSKiNVGgtNAADS8tUopaKG1puy3dZeflztyX5/hhZpftdgvb3dnubtMn"
        "mWTm3pmbOb97nv/znHPPEY4wVHFESAH6XmZm4HCVKlday7lqOcVCm4BhagwrUBbDTjG8YYS1YcrfOy7i4HBbhg8ZwXABRARbXsdJ"
        "js/NAqs8l1OMgSSGOAVrmVLDGPAccL3Gf4sTdio8ltb5TduX2aOKAVQEPSKApvGIoOUN/MDzuCuTY3ZchXqERVAUIzIyvEkeqgoI"
        "FkX8DMbLQVTlQBxze9tyHhpq32EABk7yAk6Y5cEgz+p6BeKEBHBEppzBn0MDBVLPxfXzEFZ4+JUaP7rsssZUGIAgg8avwdCJhBn+"
        "FHTwjfJBEgXHTDPDDxMHRQXStpm4YR/PBBHfZD/Kt7AiqAwVif4XebQwi+tLHxMbg8dxNKwlLszCK33MH4qXcsOAzUafbLwpr2d1"
        "YQbXVw4ef8Y3RdKrHCQuzOD68npWi5DqkziiipRfptMRthlDMU5gCi1vrdUFsJ4L1tKfKovaLmK/kYay3xIU6Yhi7FQz3qqQ2k9f"
        "VscuSQImirFBkQ5SbhFBpfd5OhyXrX6GOXGMMoUApCoEruK5Q+6ihUrUNGhsLKznIfWIfYWAxa6f4SrfZ241xIq0znhVxny3FDAC"
        "RV/ZdiDHC+93sbs/oOgnXND9MRfNP0hiIUnHBMFEETYfMLdcZYVrLSuNQRm2Qxrn0oPvQMYb3yUffPU0HnhlAaW6hzTB/O61BXz1"
        "jL388oot5DPJ2CAIagwqwkoXYVmSINKinZ1VyHmwq99n3ftdVGMXEWW0eC1CxlF29AU89tYXyHkpM4No8OcC/OXdeUSp8MDVbzSN"
        "16PVAkliBGGZi9IdJw3XaIVgBZ6yeW+RG585nz2lLEbGNn0coxT9GFUhsYdeZG4h5F/b5/LP/3ayYlEPpZrgmKOCYOIUULpdhHyr"
        "A5v7Ni5kXzlLV75OOlbVVo74W6uCiLLugy5WLuoZk+9aCyrk3VapvgKuUUp1w+7+gJyXEFuDKi0fquAAfWEG1bHPXQHjTsTyJYCq"
        "HDY3j8pNP8MDRBrnZuXqiGkAGSuFCQFwJLcthd6o5cqIUvCTwTt+GGDg8tP3NTxgHPI94QBEIEmFjiDituVb8RzFfobbWiDjwI7e"
        "gN9vOoOMY8m6dhCcKuwtZ7nm7J1cfvoBKnXBiE5dAAN3P+8lXLd0J647ylVL4ORiyK9fXsT+qj942HdTVi3dwS8ue4ckPfolcFKn"
        "QF/okHUt6WiES2DV0l1ceup+Nnw4m49KAYVMwnnzDrLspH5qCaR2fO5/TAEMiKBjGpui0fzv/rrQ1Vbn2qW7PwWZQjlqLIPSgq3b"
        "MQVw1MBEiVOoJ3KIpoxnzk8rAAMGO6ITdv3jMvExrT3AqqA64ObSWDJb7PZTFoBVIecpjgNxAiKK23wfJjIhU+GYAkhVmq+RV4Gi"
        "r7y5p8jT78zjf71tGFHO6uznmi/u4sxZVUrj3PRMKgARaPfTRnpLR1ajh187lXs2LKaWOHimEaKue7+LJ7bM584rtrBi0T7KLYYw"
        "4QAGYvu+msdP1i7FMXrY3t4I1BLD89vn4BplZhBhm98pihImDj/9x1LmFTeyZE6JMG4dhGPiAUaUWuzy120nDwYvekjk2DhW8BNQ"
        "DkmAWBWybkpv6PPI66dx38rN03UKKO1+/LkaMfJxQ9ZL+XdPB72hIRjtdnoqiuBYsy2CEqWGKDHkPEurUrjHFIAMDeaHB/fCiLH/"
        "gPek1jA7V6c9mzSCoOk2BRSIU3NEMtY2ihyybko6RAOkmWqrxC5fW7CHIAP94VEnQSc3IRKnhs58jbu+8haZZkJkuGckarjzhbPZ"
        "sreDmUHUSKU3RXBPKcvlp/ew6ksfUq2DMdMsGFKFjGNZdnIfWZfDBEwVHAcevHoTd794Fut3dBJGHqAUMgnfPfcDblu+Dc9Y4pSW"
        "hMHHfgooVCKH1I6s4BpBV77O/V9/k20H8nzQm8eIsmBWmTNmhoTN2iRpcbnGMRVBI4oRZcQkrkCUQj0VzpxV4azOCtAwulRvXQJk"
        "SgdDjedzShh/+qDSoBMWCU7ZhMhEGnwiIXICwAkAJwBMGAAdouYjKTyAHq8AFHCkYWiUmMaSJjq4fg8cc2RqQTCtu5AAwh3PLWFP"
        "OcB3U8LIIYwcfDdlTzngjueWANL87nEEILVC3lce39zNmrfnk/MSKpHLwtklFs4uUYlccl7Cmrfn8/jmbvK+HhLxTTaAcRfIOEap"
        "RsKft55C0Y+pJQ43XfgeT127kaeu3chNF75HmDgU/Zint55CNWpdODvOaWsNSsWMww9UG40K+ysZespZUhXmt1f5/nnbSVIlSZXV"
        "523n1PYqVoV95SwHKhk8hwkpnxn1nTcgSsUg7GpWYtrxQHAGBU+JrRBbwXMacJLmZ5rnjeikGg9YzwGEXQbldddFdYziLAKxhc58"
        "RHexigAflQLufWkxfbUMfbUM9760mI9KAQJ0F6t05iNiy4REd6N0fXU9FOV11xietZZVKGNujbBW8DPKdefs4OZnZ9OZr/Pklvk8"
        "t30OAAcqPvlMyv6Kz3Xn7MB3oV6bRB1QxFpElWdFN9FeCnl3vMXS2iySvGfDQn776gIC1w7dGhEmDjde8B9uu+Q9wmaBw2S5f8ZD"
        "as1iaQEobeDutg5+VuolMTK+EDnw4G/b5vDE2/PZ9UkOgO72Kt9e8iErFu0jjCdX+a2SFGbgVvu4O7+c21veMGEVCj4kFnpDB4AZ"
        "QYproFRnTKWzrVz2DmuYYA2mcDE9NuVWv5GGS8eXzGjU9tRiKGRSCpmUWtw4ZiZ57yNK6ucxccqthYvpYeB+DDQQldbzSNtMbmhV"
        "09TQ53+TPQaapsoHebRwCd8bsPlE29yQzcxg42TV56FcGzccV42TVR4JQn7ISI2TwyEMaZ39VSZH5zRvnd0fx/z8c1tnh0EQEWzP"
        "Ok5qz/JjVb4z7ZqnY3aK4Y+f1Li/a7TN08NADG+fv1ItV1rL+QrzrE6d9nkFa4SywG4xbDKGtWHK2tG0z/8fi/hk+RsT6zEAAAAA"
        "SUVORK5CYII=" if _ZUTI_LOGO else "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAKgklEQVR42u2bXWyc1ZnHf885533HY08cOwFDGmIM5UMbHEBKGjXb"
        "RsM2ZelFW1ZsR10QC9UWVd1dtTddoRU3qSv1Amm5WO0FVcRuW8r2xv2ABaQGyse0u9AGXJGAh43ChibNkmJwHCczY8/7cZ5ezIzj"
        "JE7icex4rPaRXsl+Z/TO+f/P8/2exzJ/kUKhYC8vXG4P3XYIiijtJDsx+dvydmvfVimVSvMHNU/gZnh4OJ19c/NXvhLAwc6onDHL"
        "iTvM1TxcWx3ZtSuefb9QKNjh4WEP59+o8xOwc6dhaMgD5PN5N3lN5i9U+YzCFlXtF1ilil1OAkRIFU6KyGGB10X42ep3ay8Vi8Xk"
        "TAwtEdBgMAXMLff/5QOIfE2MDIo1qPeoV9A2sQIRxAhiDJp61OtbqP7b3u8/9xjgZ2GZHwH5fN4Vi8Vk8L5P3WyN+44J3DZNUnyS"
        "ekU8oiIqgszLhJZeFFVRRUUFNcZZI87i4+TV1CdffevxF/c1MV2QgOYXN/3tjjuNc0+IMbk0ShJBDSKGlSCqXhFvQ+fU+7JPknvf"
        "/MELT81FgjlT7YvFYrLpnh13Wud+imoujeJUBLdiwNdNwojg0ihOUc1Z53666Z4ddxaLxaRQKNi5NaDhLG65746b1OgegaxPvcpK"
        "Aj6nMqg31ojClHjZuvfx3aOzHaOZTUQ+n3ce/z1jbadPvV/p4OvKIMan3htrOz3+e/l83s3GbBrALUNDfmIgvN9lgi1plCQiYtsC"
        "AGBEMaIL9rgiYtMoSVwm2DIxEN7P0JDP5/O2+XypJzabXTTd+5a19nqfpNoONm9FiVJDLa0vJWM9ofWkKgtyjMZZSdP0QNgxMTiy"
        "ayQB1BQKBQNoXF2z3Tp3w2KCFzm1e61c1tTzi+PTAT3ZiG0bxtm2YZyebMTx6WDeKeyZjtEnqVrnboira7YDWigUrBvbONZ4lv+c"
        "2EA1ES9nRIeFiBGlllqixLS0WkHxKnS4lH/65H7++qYjrMlGABybCvnR6FU8uuc6TOM3WknFVMSLNYIknwVeHNs4Jq5I0QOoMVvU"
        "ewEVLjK/EYFy5OhfXeXq3mpLGaMRqMaWv9l0iM9vep/pKZhuRO7uTMQ/fvIgV+ameOj5W8gGSX25LVCg3ouKfAygSNE37T+Ip9e8"
        "I9b0a+I9snANMKKUI8ddG4/wUP5/yYXJgghUhUokdecnTTOGVIXVWeUfnrqV595Zx6pMjJ8vCYoXZ4xP/eGw49h1I7tGYgeQ1HJd"
        "qOZQ5WLSWxGIUsuG1VUeypfoDDyVeOEPbPqC2c+XRgny6eve52cHPlInR+dtX4IqopqD3k5g0gH4OCfYyMhFhyyllhqu6amQCz2V"
        "SM4CsRiOFYW12RqB9QuqxxQxUTk0AG5papNZiz0tEkEr0dyIzhHN6iFgvJohTg0StqABc8iSEHAuybh6bNeL8AHa+Pzn/3dFPQpc"
        "pIJdEgJUhYxTHvmfG9j3fg+dLjmn45orCiS+6RMg16n8+I11vHDwSnKtOMBlJaABbN/ve3jp3SvozsTnzOaaecDe3/dw5MQ7Z+UB"
        "//Gbeh6Qsb7FENgGJtAZJKzKxOTC8++cCKRe+Jf/vpEf7uvnmt4qAO9OdPLeiSyrMglycaa/PAR4ldOuC3nRno6Y41Mhvyp3zNQC"
        "PR117Vms2HJJCWhVUhWcUQKbzPiSVBe3C9fWBDSVQXXpWo9tR0CzgpxtNkvZfG4rAqwo06llKj7Vi8kGKR02XXTVXxYCmrW+Ncrs"
        "JE8aSc5kLWCgp8Kf949zWVeNDysZXjm8lt8e76J7EWL+shIgwMlawLFqSJKeHQW8F/5u80G+vu0AvZ2nKsiJquNfX7me/9w3cMHw"
        "2bYEiEDsoTD4O7ZuOEZo0xnHJiixN/R1TXPPzUeIPUxOyUyc73AJ37z9bSqx4yelq1h9niSqfQlAiT18YfC9eq9J51APhZPT9T/d"
        "rAoy9oKLla9uPcALB68gSQUjrLw8oG4C5/HoUneCcznGWgIbuqe5Ye1JfnO0l64gWbTQeEmdoMyq7Fqs3zFGyS4i8GUhwEmj1J1D"
        "O7xC4mXOHoARpRIJ/3+ik8B4FFl5BAhwMrIk3py1fK/QGaTkMo0ukuiMX4i9oTfneXq0j4PHcq31ANuFAK9CNlAe3L2JV3532Wnh"
        "TBo5f3cm5pHPvMFNHykTR3VSjEAu9JSO5nj4l39GxqWLuvvLoAGOY1On5wHNXsGHlQxffnIrD2w+yPaBD8iFMeUo4Je/vZzHXr+W"
        "yVpAh0tXZh5wygcogVGcUfwZpt4VJpQjx7eLG1n965iuMKESOSanA7rCZEnAwyK8AWq5sjvH5VVwovRmI7zC5FSAV+jNRjjRJQHf"
        "dsWQUu8ENZOh5v9LWp+0cx/gkhRo/JHLnwj4EwFLUPpezOcrmgARiFOZeX2leqqn16wB4lTaigSzmOBriWFDd5VvfGI/USo4q6zK"
        "KM4qUSp84xP72dBdpZaYtiFh8QhAqSWWB7e/zeC6MqBUIssv3l1DJbKAMriuzIPb36aWWKRNTts7ABOUVX3gF3o0pr77lmvXlNk+"
        "8AFRDEdPZvn7/9rM/g+7ufGyEzz6+RHWd0+xfeADrl1T5shkJ6Hzy3LeWlAf5GqnDkq6TLmCSLlhqLqQ3Y+9YX13lazzhA6e3b+O"
        "0bEe1q+aYnSsh2f3X0noIOs867uniL259FqgKCKoSBkmqnUCdmJGdo3ECofFCCoL2xMRpRo7vIL3MNBTAZSxSgZQBnqqeF8vc6ux"
        "ReTSb72KqtTPwRwe2TUSsxNj8uQNgKi8JsYotL4yVaHDphwYX8V7JztIPOz46Bjf2vEmH98wzrd2vMmOj46ReHjvZAcHxlfRMasz"
        "fAmVX8UYFdXXAPLkjekr9WkDxTOaehFV07pm1YuXyemA7+y5njCo373v1sN8967XuO/Ww4ASBvDonuuZnA5mip1LC1+Npl5QeQag"
        "r9SntlQqKSBXfbz3SBJlvmidXaveK9JaoFLqhxv3vd/LsUrAlvXH6Qw9RuoNj3LkeLh4I8Oj/Yve1pqnmtaPysbpgbBz4p+PjhzV"
        "UqnkZ06JF4vF5Ob7b/+yDYPHkuk4EVlYqWxEOdF4xbWtf5y1nTXGqxleXeJXXBfGT+I6ApdG8QP7vv/8vzcxy4wj37lT8i+/bI5d"
        "Hb5qA7elPiixsBPjy/GS8/zgNbVhYNM4eX3NoWhb8bbbPENDCszYuwIUi8XEYL7k07RqrDGq6hfyg6kKofX0ZqOZa8GnvC8evDfW"
        "GJ+mVYP50qyRGT09Exwa8oVCwe59fPeoxv5uEaFBQrpAlSP1MnMtR8KjqqmxxogIGvu79z6+e7RQKNjZY3TnHJoavPdTf2WD4Akx"
        "pmuFD01V0ji+960nXnxyrqGps2z80KFDPp/Pu9eefrl02WD/s0bkFpsJrhYQ9d4rkkp9RA3apaqrj815VLygGGeNDZ3RJH01SeK7"
        "Rp94qTjvsbmm/FEPTs7IXKOzyB2o36pKP5Brh9FZoCzCYcTsEXT3oozOnkMbZmRjoRBmeyey7TA8PTXRO1UaHo4utOYFE9D8bqFQ"
        "MGMbx6RI0TOEbyvHtxOTJ2/6Sn06n6nxpvwBr4WBbXT2CooAAAAASUVORK5CYII=")
    ),
    36: (
        ("iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAFPklEQVR42r2Y22scVRzHP79zZmYvWTdla2vTatW20VoKikoRalC8"
        "gaIoPvgPiNoqgsY38UVBwQf1SfACPog+GBAExQv60FIVMQhWbUmaxoLXGtskbjK72bmcnw8z1tBu0t3u6oFhHuYw53u+399dyJcq"
        "RgQ3+ymbBwZ5wKXc5RzbVCkDQn+WitAwhqPG8n74F6/XbuWnf84GMABjY1gRXPg5eyuDjAc+T3mWKwUG+ggGQAQGPMuVgc9TlUHG"
        "w8/ZK4IbG8MCiCpWhHTxAC8O1Hi8VYc4IQWMSF/BsEwNBZzvYQtVCGd5qTLCqCpWAOoHeOi8tbwSzhI7xTN9AqIqOS3a9rtT1AjJ"
        "QA1/4SR7qiO8KuGXbEL5wVqqcQKSy7jqQR1uKHjZu5Vkwkv7rc73IE2pI+w0LmVvucyaKEY7AeNUsMKKjxEIPCj6cGyuzLG5MkUf"
        "PAPa5iYCJorRcpk1OPZ4AncnMdqJvQhQ9pV6y+C0/XYjMB97PH9gO/uOrQfghktnePqmQxS9hFTPZEoESWJUlXs8YGscI3IWb1IF"
        "z8ILXwzzweQmAuva31igGVv+WCxSDhKsKGPfb2ZDZYknb5yk3hSs0TNYimMAtnoIJadnl6nkKdOzZd74ZguSSyOibW9hRKkWY1KX"
        "fa2VIsZ/qbEUcQaYZQYOQsnrJoC0EkPgKUYcIDQiS6pnaq1A2U8JrMOIMp9Yzh9oEXgQRoKRlRnwuo1qWRARVOGJ3RNcOLhEK5Hc"
        "tTM55pd8Xv5qmOOLJQSlVo548NppnJ79DK+XOHPr1uNs2bAE8bJ4rln837Vplo+nNgBw+2W/s21tg0bEquz0DGgh8omaLRrJaTIo"
        "bK2FPHb9NABxTA7mP2bIiGKN5vEnA5Rq5q+N2KA5IyJnZ6YvgFIVUpc9KpmNVQv5waKkKTTizpjpC6DBQkxQVoLo32j34eR6Ppka"
        "ouCl3LfzZ67e+Bdh1DmocwAkQCbDm99eyrqBiCiFwMLvCwXe+X4ziRMU4cPJjbxx79dcvXGeZiwdydY1IF3mUG8dvITUZVKpZiyc"
        "V8jCvhXlRKPA2wcvZteF8+j/IZlvHN6ydGxzA3ZOEKP4xhFGFtXOq7yeAG1fV6fkpziXBcS5ps/hPwcp+wmxs4Sxx23bjkPOIP+F"
        "20tOvio8e8tBrrigwVKUJd7FyPLiF5ez79h6fON49Lop7tnxG+EqOayvDMXOkCQQOSF2SsGmPHPzYU6Ek3hGWVNyhFF3RXlPgCTP"
        "b5LXQanCQkuoBCkK1FuCFe3qnz0Bag9QSfRfI+92dQXo9Cpxpaqxlw6hK0AlP8WIYgw4ByUv7XuLZDoNhtbA+K816q2A+pJPvRUw"
        "/lsNa0D/T0Cal69HT5Z4bv8Ohtcu8PjIEYbXLvDc/h0cPVmi5OmpHqx3QEpztcTnAN+DwzNVZsIio7sneOSOaUZ3TzATFjk8U8X3"
        "sn29lTKA0jTAtO+jusI/hcxehqpNAuv46MgQ300M8tGRIQLrGKo2ca43Q1Zwvo8C054I73k+O7WFE2lfhDUi4aqhOvdfM80rXw/z"
        "7qGLaKWWPbumuGqoTiOSjguwlXp9z8dEEe9J+BmbKK3eSmtOqWdg34/rmDhRZfv5dW7c8ieJy1oY6YWdZa10V8MGBSpB7goOFqPe"
        "pGo7bOh2HJOqnCqK7DnKtNo4xoiQjo1hKyOMNuZ4WCwzlQq2WEDa2ZQ9VdifGxgRKBaQSgUrlpnGHA9XRhjNh2apnD7Sa+znIlvg"
        "QYU7nWPYuf6O9IyhYQxTAh+kLV4r38DPy0d6fwNJMFYehxw5cQAAAABJRU5ErkJggg==" if _ZUTI_LOGO else "iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAFe0lEQVR42s2Y3W8dRxXAf2dm9u5d26mTQprUtfthNbTQJpIj2ioC"
        "FIIK5A/gEkFVqvLQVpUoSKUPfEjGQjylfUJCokIRECIURfCAQkHBqFRNJUpUKLGaUlIL0iaR41RubCf2vbszc3jYaxPsa9f2tSWO"
        "NNqX2ZnfnK+Zc2CB1Go1y2KRdRofuNf/ThrEMES858Dn+pKMA6q6F7glqibo4gVXJYIakQK4ICIvFbMcfePoiXfn9lwIJAwOCkND"
        "cefDn33GOPmude4GVUWjsp4iRhARgvdTGvj+6Z+feJbBQcPQkAIqc6o7duxY2PXwgz92WfqYbxRoVI+oSLuaWSAqKCoqRpxLE/xs"
        "4/nTh4cfn2OQ62Cedh3ps342z1ESpD0QI4oIqELUFkspilC4rFLxM41vnj48/FytVrMCMPDVB3tCkLOIpEQ1rRxw4WbLuwvMeEvD"
        "W5yJdFYC2voXxUhEtWGt7vjboeGLDsAX8lBSTTqKeuFlBZq5lrvWp27SxCjcu+0KO7dP8u6VDv5y/kNUXGi1sGhQbe79EHDQNQNg"
        "n6oqorKcchRQFe7rnaCz4hedWgQa3nDXh6d5as9ZutIyeH5y6jYOnvwoHYlffBBRUVUVdN88EEKPxqYDL8FjRZlqJHxtzz/5+idG"
        "8b5E15Zzoe5hclZwBh7dfY7fn72ZkUubF0GJIhpVEHoADCCquA8yUwSsUfb0vYcGuJobfDN7qP53QAmTB8EapQiCEbips46PS/tD"
        "k0Hc6nIb5N6gQGKUdyYzpuoJ1iiqpcl8FLZ11enbnFPPoaszcvFKwt/HtpC5sLTvNcWtOrE1QzlLlB/++SP85s1b6E4LggoiUERh"
        "e1edZz75D+7ZPsXl8ZTnTt7FezNpax9qF2hh+FtTjjlnqrrI+NUq33hhgC1ZwdWGI6isCKZtoKXM2pGUHl8vDBUbEdEVway/hhSm"
        "c0cRDEaUTWkJtlKYtoCkmSAnZipoFLyWEfTpOy5xX9/7nL+ScfytHnwUnCi6kUACFBH23jHOliynIwnUveXOG6d5ZOAdrAUsfOr2"
        "cZ7+3QCruRXXBiRQL4Qv3nuBL++6cH0u4VoBIS8J9u+4zNGRCU6e20pXpViR6UxbT4lmMoyx/BYRQiwT4dzmnRVP1JUraU0aUsAZ"
        "eH2sm7HpKomN5MHQe8MMu3un8R5cooxernLq/I10JGFjo0wVMqcceq2fX5/pZUu1IA+GTWnBE/e/zcd732dsqsqPXr2TyXpCttFA"
        "c1rKEk93WpT+geCDcPDlu0ldqbGKjauCaTsPRRWCyvzXCGyulnBVF+bnrEbWNVMrEJoAa32Km7VGVjMxr28FsBoNKRAVEhtxtiRJ"
        "jC77xtkwDVlRrjYSvrTrHA/cOsnoRJXpuuHJB96mr3uGRjDrBmUAFcEvNymokNrIVwb+xcjYJj7/03089dvd9N80y2f6L3GtcBjT"
        "XkHZZFDTtMdFMaIqy9+B2nTY8vGtbTnv9YWjGFGUi/MmU+RFERG0dcFlRcmD4dBf+9nZO82pJ05w6AuvMTqeMTy6rbweoqyVSEVE"
        "FH1x3qldokd8XnxPrKREXRQ8QYWu1POrN/qYrCfs33GJy9dSfvH6rUzMVlb0Vl4Sx4r4vJhxiRwBsLVazf7xyPGprbv6G0lW2R99"
        "KFBMq4Ioscqb49288NbNvPTvreTRUl0rzFwpXa0kPvffOv2z4RO1Ws3aM2fOaK1Ws3/65fFXtn7sth6XpffHGEUVj+icEbW5hFaT"
        "qFniNUuCGlGNKiplAbSioUJEJYoR66oV62cbz48cHv72fLOhZTvGmu/YxHZvaDumCJMxxB+MHP7DwUXtmFYNK5txQFT3qmqvgluP"
        "hpWAF5HzyzWs+H9r6f0HCnjUiDzDWzMAAAAASUVORK5CYII=")
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


def nazivi(vrsta):
    return NAZIVI.get((vrsta or "")[:3], (("male" if EN else "mužjak"), ("female" if EN else "ženka"), ("young" if EN else "mladunče"), ("young" if EN else "mladunčad")))


def norm(t):
    return "".join(c for c in str(t or "").upper() if c.isalnum())


def kolona(k):
    k = (k or "").strip().lower()
    for a, b in (("đ", "dj"), ("č", "c"), ("ć", "c"), ("š", "s"), ("ž", "z")):
        k = k.replace(a, b)
    return "_".join(k.split())


def stare_lista(r):
    """Ranije usne markice grla (kolona stare_markice, razdvojene zarezom)."""
    return [x.strip() for x in str(r.get("stare_markice", "") or "").split(",") if x.strip()]


def sort_key(s):
    """K2 < K10 (prirodno sortiranje)."""
    import re
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", str(s))]


def parsiraj_datum(t):
    t = str(t or "").strip().rstrip(".")
    if not t:
        return None
    try:
        t = t.split(" ")[0]
        if "-" in t:
            g, m, d = t.split("-")[:3]
            return date(int(g), int(m), int(d))
        for s in (".", "/"):
            if s in t:
                d, m, g = t.split(s)[:3]
                return date(int(g), int(m), int(d))
        if len(t) == 4 and t.isdigit():
            return date(int(t), 7, 1)
    except (ValueError, TypeError):
        pass
    return None


def fmt_datum(d):
    return d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y.")) if d else ""


def starost_meseci(d):
    if not d:
        return None
    n = date.today()
    return (n.year - d.year) * 12 + n.month - d.month - (n.day < d.day)


def fmt_starost(m):
    if m is None:
        return ""
    if m < 24:
        return (f"{m} mo." if EN else f"{m} mes.")
    g = m // 12
    if EN:
        return f"{g} " + ("year" if g == 1 else "years")
    else:
        return f"{g} " + ("godine" if 2 <= g % 10 <= 4 and not 12 <= g % 100 <= 14 else "godina")


def fmt_upis(t):
    """'2026-10-05 14:30:00' -> '05.10.2026.'"""
    try:
        return datetime.strptime(t[:10], "%Y-%m-%d").strftime(("%d/%m/%Y" if EN else "%d.%m.%Y."))
    except (ValueError, TypeError):
        return "–"


def pct(f):
    if EN:
        return (f"{f * 100:.2f}" if 0 < f < 0.1 else f"{f * 100:.1f}") + "%"
    else:
        return (f"{f * 100:.2f}" if 0 < f < 0.1 else f"{f * 100:.1f}").replace(".", ",") + "%"


# =============================================================== podaci (CSV)

class Tablica:
    def __init__(self, putanja, ucitaj=True):
        self.putanja = putanja
        self.redovi = []          # lista dict-ova sa kljucevima iz KOLONE (+ dodatne kolone)
        self.dodatne = []
        self.mtime = None
        if ucitaj:
            self.ucitaj()

    def ucitaj(self):
        self.redovi, self.dodatne = [], []
        if not os.path.isfile(self.putanja):
            self.mtime = None
            return
        redovi, zaglavlje = procitaj_csv(self.putanja)
        self.dodatne = [k for k in zaglavlje if k not in KOLONE and k not in ALIAS]
        self.redovi = redovi
        self.mtime = os.path.getmtime(self.putanja)

    def sacuvaj(self):
        zagl = KOLONE + self.dodatne
        tmp = self.putanja + ".tmp"
        if EN:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([EN_KOL.get(k, k) for k in zagl])
                for r in self.redovi:            # redosled upisa se cuva
                    vr = dict(r)
                    vr["status"] = STATUS_EN.get(vr.get("status", ""), vr.get("status", ""))
                    vr["pol"] = {"z": "f"}.get(vr.get("pol", ""), vr.get("pol", ""))
                    w.writerow([vr.get(k, "") for k in zagl])
        else:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(zagl)
                for r in self.redovi:            # redosled upisa se cuva
                    w.writerow([r.get(k, "") for k in zagl])
        os.replace(tmp, self.putanja)
        self.mtime = os.path.getmtime(self.putanja)


EN_KOL = {"id": "id", "markica": "ear_tag", "vrsta": "species", "rasa": "breed", "pol": "sex",
          "datum_rodjenja": "birth_date", "otac": "sire", "majka": "dam", "status": "status", "stado": "herd",
          "poreklo": "origin", "poreklo_od": "origin_from", "stare_markice": "old_ear_tags", "uneto": "added"}
EN_IST = {"grlo": "animal", "datum": "date", "dogadjaj": "event", "opis": "description", "partner": "partner",
          "vrednost": "value", "automatski": "automatic", "uneto": "added", "ishod": "outcome", "ter": "heat",
          "karenca_meso": "withdrawal_meat_days", "karenca_mleko": "withdrawal_milk_days"}
EN_POD = {"grlo": "animal", "datum": "date", "tip": "type", "tekst": "text", "ponavljanje": "repeat_days",
          "gotovo": "done", "uneto": "added"}
STATUS_EN = {"aktivno": "active", "neaktivno": "inactive", "obrisano": "deleted"}
ALIAS = {"oznaka": "id", "grlo": "id", "usna_markica": "markica", "usni_broj": "markica",
         "broj_markice": "markica", "rodjen": "datum_rodjenja", "rodjeno": "datum_rodjenja",
         "datum": "datum_rodjenja", "tag": "id", "animal": "id", "name": "id", "eartag": "markica",
         "ear_tag_number": "markica", "father": "otac", "mother": "majka", "date_of_birth": "datum_rodjenja",
         "dob": "datum_rodjenja", "birthdate": "datum_rodjenja", "born": "datum_rodjenja", "gender": "pol",
         **{v: k for k, v in EN_KOL.items()}}
POL_MAP = {"m": "m", "z": "z", "ž": "z", "f": "z", "b": "m", "k": "z"}


def norm_rasa(r):
    """Rase se pišu malim slovima, osim oznake hibrida: 'hibrid L×J'."""
    r = " ".join(str(r or "").split())
    if r.lower().startswith(("hybrid" if EN else "hibrid")):
        kod = r[6:].strip().upper().replace("X", "×").replace("*", "×").replace(" ", "")
        return (f"hybrid {kod}" if EN else f"hibrid {kod}") if kod else ("hybrid" if EN else "hibrid")
    return r.lower()


def kod_rase(rasa, druga=""):
    """Oznaka rase u nazivu hibrida: prvo slovo (dva, ako obe rase počinju istim slovom).
    Hibrid kao roditelj ulazi u zagradi: D×(L×J)."""
    rasa = norm_rasa(rasa)
    if rasa.startswith(("hybrid " if EN else "hibrid ")):
        return f"({rasa[7:]})"
    if not rasa:
        return "?"
    d = norm_rasa(druga)
    if d and not d.startswith(("hybrid" if EN else "hibrid")) and d[0] == rasa[0] and d != rasa:
        return rasa[:2].capitalize()
    return rasa[0].upper()


def rasa_potomka(rasa_oca, rasa_majke):
    """Ista rasa -> ta rasa; različite -> 'hibrid O×M' (prvo otac, pa majka); jedna nepoznata -> poznata."""
    ro, rm = norm_rasa(rasa_oca), norm_rasa(rasa_majke)
    if not ro or ro == rm:
        return rm
    if not rm:
        return ro
    return (f"hybrid {kod_rase(ro, rm)}×{kod_rase(rm, ro)}" if EN else f"hibrid {kod_rase(ro, rm)}×{kod_rase(rm, ro)}")


def vrsta_norm(v):
    v = (v or "").strip().lower()
    return {"gov": "goveda", "bik": "goveda", "kra": "goveda", "ovc": "ovce", "ova": "ovce",
            "koz": "koze", "svi": "svinje", "kon": "konji",
            "cat": "goveda", "cow": "goveda", "bul": "goveda", "she": "ovce", "ewe": "ovce", "ram": "ovce",
            "goa": "koze", "pig": "svinje", "swi": "svinje", "sow": "svinje", "boa": "svinje",
            "hor": "konji", "mar": "konji"}.get(v[:3], v) if not EN else {"cat": "cattle", "cow": "cattle", "bul": "cattle", "gov": "cattle", "bik": "cattle", "kra": "cattle",
            "she": "sheep", "ewe": "sheep", "ram": "sheep", "ovc": "sheep", "ova": "sheep",
            "goa": "goats", "koz": "goats", "pig": "pigs", "swi": "pigs", "sow": "pigs", "boa": "pigs",
            "svi": "pigs", "hor": "horses", "mar": "horses", "kon": "horses"}.get(v[:3], v)


def procitaj_csv(putanja):
    kod = "latin-1"
    for k in ("utf-8-sig", "cp1250"):
        try:
            with open(putanja, encoding=k) as f:
                f.read()
            kod = k
            break
        except UnicodeDecodeError:
            continue
    with open(putanja, newline="", encoding=kod) as f:
        prvi = f.readline()
        f.seek(0)
        sep = ";" if prvi.count(";") >= prvi.count(",") else ","
        citac = csv.reader(f, delimiter=sep)
        try:
            zaglavlje = [kolona(k) for k in next(citac)]
        except StopIteration:
            return [], []
        zaglavlje = [ALIAS.get(k, k) if ALIAS.get(k, k) not in zaglavlje else k for k in zaglavlje]
        if "id" not in zaglavlje and "markica" not in zaglavlje:
            raise ValueError(("The table must have an 'id' (tag) or 'ear_tag' column.\n" if EN else
                              "Tablica mora imati kolonu 'id' (oznaka) ili 'markica'.\n") +
                             (f"Columns found: {', '.join(zaglavlje)}" if EN else f"Pronađene kolone: {', '.join(zaglavlje)}"))
        redovi = []
        for red in citac:
            if not any(x.strip() for x in red):
                continue
            r = {k: (red[i].strip() if i < len(red) else "") for i, k in enumerate(zaglavlje)}
            r["id"] = r.get("id") or r.get("markica", "")
            if not r["id"]:
                continue
            r["pol"] = POL_MAP.get(r.get("pol", "").lower()[:1], "")
            r["vrsta"] = vrsta_norm(r.get("vrsta", ""))
            r["rasa"] = norm_rasa(r.get("rasa", ""))
            for p in ("otac", "majka"):
                if r.get(p, "") == "0":
                    r[p] = ""
            st = r.get("status", "").lower()
            r["status"] = ("aktivno" if st == "" or st.startswith(("akt", "act")) else
                           "obrisano" if st.startswith(("obr", "del")) else "neaktivno")
            for p in ("poreklo", "rasa"):
                r[p] = prevedi_vrednost(r.get(p, ""))
            redovi.append(r)
        return redovi, zaglavlje


# =============================================================== istorija grla

IST_KOLONE = ["grlo", "datum", "dogadjaj", "opis", "partner", "vrednost", "automatski", "uneto", "ishod",
              "ter", "karenca_meso", "karenca_mleko"]
TER = ("In heat" if EN else "Tera se")
# dužina polnog ciklusa (dana) – kad se ženka ponovo tera ako nije ostala gravidna
TER_CIKLUS = {("cattle" if EN else "goveda"): 21, ("sheep" if EN else "ovce"): 17, ("goats" if EN else "koze"): 21, ("pigs" if EN else "svinje"): 21, ("horses" if EN else "konji"): 21}
PARENJE = ("Mating / insemination" if EN else "Parenje / osemenjavanje")
STADO_PODMLADAK = ("Young stock" if EN else "Podmladak")
# prosečno trajanje gravidnosti u danima
# trajanje gravidnosti (dana) i koliko dana ranije je dozvoljen upis mladih (prevremeni porođaj u granicama normale)
# nosivost: ključ -> (naziv, vrsta, rase po kojima se prepoznaje, najmanje, najviše, prosek) dana
GRAVIDNOST_PROFILI = {
    ("romanov" if EN else "romanovska"): (("Romanov sheep" if EN else "Romanovska ovca"), ("sheep" if EN else "ovce"), ("romanov",), 138, 143, 140),
    ("sheep" if EN else "ovce"): (("Common sheep" if EN else "Obična ovca"), ("sheep" if EN else "ovce"), (), 145, 152, 150),
    ("goats" if EN else "koze"): (("Goat" if EN else "Koza"), ("goats" if EN else "koze"), (), 145, 151, 150),
    ("pigs" if EN else "svinje"): (("Pig" if EN else "Svinja"), ("pigs" if EN else "svinje"), (), 110, 120, 114),
    ("cattle" if EN else "goveda"): (("Cow" if EN else "Krava"), ("cattle" if EN else "goveda"), (), 275, 290, 283),
    ("horses" if EN else "konji"): (("Mare" if EN else "Kobila"), ("horses" if EN else "konji"), (), 320, 360, 340),
}
DOGADJAJI = [("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("In heat" if EN else "Tera se"), ("Birth" if EN else "Porođaj"), ("Vaccination" if EN else "Vakcinacija"), ("Treatment" if EN else "Lečenje"), ("Weighing" if EN else "Merenje težine"),
             ("Move" if EN else "Premeštanje"), ("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće"), ("Note" if EN else "Napomena")]
AUTO = ("Record change" if EN else "Promena u evidenciji")
# kartice u istoriji: naziv -> koji događaji spadaju u grupu
GRUPE = [(("Matings" if EN else "Parenja"), (("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("In heat" if EN else "Tera se"))),
         (("Treatments" if EN else "Lečenja"), (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))),
         (("Births" if EN else "Porođaji"), (("Birth" if EN else "Porođaj"), ("Offspring" if EN else "Potomak")))]


class Istorija:
    """Dnevnik dogadjaja za svako grlo, cuva se u <tablica>_istorija.csv."""

    def __init__(self, putanja_tablice):
        self.putanja = _uz_tablicu(putanja_tablice, "_istorija.csv", "_history.csv")
        self.zapisi = []
        if os.path.isfile(self.putanja):
            try:
                kod = "utf-8-sig"
                try:
                    open(self.putanja, encoding=kod).read()
                except UnicodeDecodeError:
                    kod = "cp1250"
                with open(self.putanja, newline="", encoding=kod) as f:
                    prvi = f.readline()
                    f.seek(0)
                    sep = ";" if prvi.count(";") >= prvi.count(",") else ","
                    for r in csv.DictReader(f, delimiter=sep):
                        r = {({v_: k_ for k_, v_ in EN_IST.items()}.get(kolona(k), kolona(k))): (v or "").strip()
                             for k, v in r.items() if k}
                        for p in ("dogadjaj", "ishod", "ter"):
                            if r.get(p):
                                r[p] = prevedi_vrednost(r[p])
                        if r.get("grlo"):
                            self.zapisi.append({k: r.get(k, "") for k in IST_KOLONE})
            except OSError:
                pass

    def sacuvaj(self):
        tmp = self.putanja + ".tmp"
        if EN:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([EN_IST.get(k, k) for k in IST_KOLONE])
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in IST_KOLONE])
        else:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(IST_KOLONE)
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in IST_KOLONE])
        os.replace(tmp, self.putanja)

    def dodaj(self, grlo, dogadjaj, opis="", datum=None, partner="", vrednost="", automatski=False,
              karenca_meso="", karenca_mleko=""):
        z = dict(grlo=grlo, datum=datum or date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), dogadjaj=dogadjaj, opis=opis,
                 partner=partner, vrednost=vrednost, automatski="1" if automatski else "", uneto=sada(),
                 ishod="", ter="", karenca_meso=karenca_meso, karenca_mleko=karenca_mleko)
        self.zapisi.append(z)
        return z

    def za(self, grlo=None, auto=True):
        z = [x for x in self.zapisi if (grlo is None or x["grlo"] == grlo) and (auto or not x["automatski"])]
        return sorted(z, key=lambda x: (parsiraj_datum(x["datum"]) or date.min, x["uneto"]), reverse=True)

    def preimenuj(self, staro, novo):
        for z in self.zapisi:
            if z["grlo"] == staro:
                z["grlo"] = novo
            if z["partner"] == staro:
                z["partner"] = novo


class Podsetnici:
    """Podsetnici za grla (vakcinacija, lečenje…), čuvaju se u <tablica>_podsetnici.csv."""
    KOLONE = ["grlo", "datum", "tip", "tekst", "ponavljanje", "gotovo", "uneto"]

    def __init__(self, putanja_tablice):
        self.putanja = _uz_tablicu(putanja_tablice, "_podsetnici.csv", "_reminders.csv")
        self.zapisi = []
        if os.path.isfile(self.putanja):
            try:
                kod = "utf-8-sig"
                try:
                    open(self.putanja, encoding=kod).read()
                except UnicodeDecodeError:
                    kod = "cp1250"
                with open(self.putanja, newline="", encoding=kod) as f:
                    for r in csv.DictReader(f, delimiter=";"):
                        r = {({v_: k_ for k_, v_ in EN_POD.items()}.get(kolona(k), kolona(k))): (v or "").strip()
                             for k, v in r.items() if k}
                        if r.get("tip"):
                            r["tip"] = prevedi_vrednost(r["tip"])
                        if r.get("datum"):
                            self.zapisi.append({k: r.get(k, "") for k in self.KOLONE})
            except OSError:
                pass

    def sacuvaj(self):
        if not self.zapisi and not os.path.isfile(self.putanja):
            return
        tmp = self.putanja + ".tmp"
        if EN:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([EN_POD.get(k, k) for k in self.KOLONE])
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in self.KOLONE])
        else:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(self.KOLONE)
                for z in self.zapisi:
                    w.writerow([z.get(k, "") for k in self.KOLONE])
        os.replace(tmp, self.putanja)

    def dodaj(self, grlo, datum, tip, tekst="", ponavljanje=0):
        z = dict(grlo=grlo or "", datum=datum, tip=tip, tekst=tekst, ponavljanje=str(ponavljanje or ""),
                 gotovo="", uneto=sada())
        self.zapisi.append(z)
        return z

    def aktivni(self, grlo=None):
        return [z for z in self.zapisi if not z["gotovo"] and (grlo is None or z["grlo"] == grlo)]

    def preimenuj(self, staro, novo):
        for z in self.zapisi:
            if z["grlo"] == staro:
                z["grlo"] = novo


# =============================================================== racunanje

class Model:
    def __init__(self, redovi):
        self.A, self.P, self.by_mark, self.warn = {}, {}, {}, []
        self._gen, self._kin = {}, {}
        for rb, r in enumerate(redovi):
            jid = r["id"].strip()
            if jid in self.A:
                self.warn.append((f"Tag {jid} is entered more than once." if EN else f"Oznaka {jid} je upisana više puta."))
                continue
            self.A[jid] = dict(id=jid, markica=r.get("markica", ""), vrsta=r.get("vrsta") or ("other" if EN else "drugo"),
                               rasa=r.get("rasa", ""), pol=r.get("pol") or None,
                               datum=parsiraj_datum(r.get("datum_rodjenja")),
                               aktivno=r.get("status", "aktivno") == "aktivno", stado=r.get("stado", ""),
                               obrisano=r.get("status") == "obrisano",
                               osnivac=False, _otac=r.get("otac", ""), _majka=r.get("majka", ""),
                               stare=stare_lista(r), poreklo=r.get("poreklo", "").strip(),
                               poreklo_od=r.get("poreklo_od", "").strip(), rb=rb, uneto=r.get("uneto", ""))
            if r.get("markica"):
                n = norm(r["markica"])
                if n in self.by_mark and self.by_mark[n] != jid:
                    self.warn.append((f"Ear tag {r['markica']} is entered for both {self.by_mark[n]} and {jid}." if EN else f"Markica {r['markica']} je upisana i za {self.by_mark[n]} i za {jid}."))
                self.by_mark[n] = jid
        for a in list(self.A.values()):   # stari brojevi markica i dalje nalaze grlo
            for st in a.get("stare", []):
                self.by_mark.setdefault(norm(st), a["id"])
        for a in list(self.A.values()):
            self.P[a["id"]] = (self.nadji(a["_otac"]) or (a["_otac"] or None),
                               self.nadji(a["_majka"]) or (a["_majka"] or None))
        for jid, par in list(self.P.items()):
            for i, r in enumerate(par):
                if r and r not in self.A:
                    self.A[r] = dict(id=r, markica="", vrsta=self.A[jid]["vrsta"], rasa="",
                                     pol="m" if i == 0 else "z", datum=None, aktivno=False, stado="",
                                     osnivac=True, obrisano=False, stare=[], poreklo="", poreklo_od="",
                                     rb=-1, uneto="")
                    self.P[r] = (None, None)
        for o, m in list(self.P.values()):
            if o and not self.A[o]["pol"]:
                self.A[o]["pol"] = "m"
            if m and not self.A[m]["pol"]:
                self.A[m]["pol"] = "z"
        # provere
        for jid, (o, m) in list(self.P.items()):
            if jid in (o, m):
                self.warn.append((f"{jid} is entered as its own parent." if EN else f"{jid} je upisan kao sopstveni roditelj."))
                self.P[jid] = (None, None)
        for jid in list(self.P):
            if jid in self.preci(jid):
                self.warn.append((f"{jid} is its own ancestor – check the parents "
                                 "(this animal's pedigree is temporarily ignored)." if EN else f"{jid} je sam sebi predak – proveri roditelje "
                                 "(rodoslov ovog grla je privremeno zanemaren)."))
                self.P[jid] = (None, None)
        for jid, (o, m) in self.P.items():
            a = self.A[jid]
            for r in (o, m):
                if not r:
                    continue
                p = self.A[r]
                if p["vrsta"] != a["vrsta"] and not p["osnivac"]:
                    self.warn.append((f"{jid} ({a['vrsta']}) has parent {r} ({p['vrsta']}) – different species." if EN else f"{jid} ({a['vrsta']}) ima roditelja {r} ({p['vrsta']}) – različite vrste."))
                if p["datum"] and a["datum"] and p["datum"] >= a["datum"]:
                    self.warn.append((f"{r} was born after its offspring {jid} – check the dates." if EN else f"{r} je rođen posle svog potomka {jid} – proveri datume."))
            if o and self.A[o]["pol"] == "z":
                self.warn.append((f"{o} is entered as sire of {jid}, but is marked as female." if EN else f"{o} je upisan kao otac grla {jid}, a označen je kao žensko."))
            if m and self.A[m]["pol"] == "m":
                self.warn.append((f"{m} is entered as dam of {jid}, but is marked as male." if EN else f"{m} je upisana kao majka grla {jid}, a označena je kao muško."))

    def nadji(self, t):
        t = str(t or "").strip()
        if not t:
            return None
        if t in self.A:
            return t
        n = norm(t)
        if n in self.by_mark:
            return self.by_mark[n]
        for k in self.A:
            if norm(k) == n:
                return k
        return None

    def grla(self, samo_aktivna=False, redosled="Poslednje upisana prvo"):
        """Grla za liste i pretragu (obrisana se ne prikazuju, ali ostaju u rodoslovu).
        Podrazumevano: poslednje upisano grlo je prvo, pa sve starija."""
        g = [a for a in self.A.values() if not a["osnivac"] and not a["obrisano"]
             and (a["aktivno"] or not samo_aktivna)]
        return self.poredaj(g, redosled)

    @staticmethod
    def poredaj(g, redosled="Poslednje upisana prvo"):
        if redosled == ("By tag" if EN else "Po oznaci"):
            return sorted(g, key=lambda a: sort_key(a["id"]))
        if redosled == ("Youngest first" if EN else "Najmlađa prvo"):
            return sorted(g, key=lambda a: (a["datum"] or date.min, a["rb"]), reverse=True)
        kljuc = lambda a: (a["uneto"] or "", a["rb"])     # bez datuma upisa -> mesto u tablici
        return sorted(g, key=kljuc, reverse=redosled != ("First added first" if EN else "Prvo upisana prvo"))

    def obrisana(self):
        return self.poredaj([a for a in self.A.values() if a.get("obrisano")])

    def preci(self, x):
        rez, stek = set(), [x]
        while stek:
            for r in self.P.get(stek.pop(), (None, None)):
                if r and r not in rez:
                    rez.add(r)
                    stek.append(r)
        return rez

    def gen(self, x):
        if x is None:
            return -1
        if x not in self._gen:
            o, m = self.P.get(x, (None, None))
            self._gen[x] = 1 + max(self.gen(o), self.gen(m))
        return self._gen[x]

    def kinship(self, a, b):
        if a is None or b is None:
            return 0.0
        if a == b:
            o, m = self.P.get(a, (None, None))
            return 0.5 * (1 + self.kinship(o, m))
        ga, gb = self.gen(a), self.gen(b)
        if ga > gb or (ga == gb and a > b):
            a, b = b, a
        k = (a, b)
        if k not in self._kin:
            o, m = self.P.get(b, (None, None))
            self._kin[k] = 0.5 * (self.kinship(a, o) + self.kinship(a, m))
        return self._kin[k]

    def doprinos(self, x, predak):
        """Koliki deo gena grlo x u proseku nosi od pretka (50% od roditelja, 25% od dede...)."""
        if x is None:
            return 0.0
        if x == predak:
            return 1.0
        if not hasattr(self, "_dop"):
            self._dop = {}
        k = (x, predak)
        if k not in self._dop:
            o, m = self.P.get(x, (None, None))
            self._dop[k] = 0.5 * (self.doprinos(o, predak) + self.doprinos(m, predak))
        return self._dop[k]

    def putanje(self, x):
        """Svi preci grla kroz SVE generacije: {predak: {generacija: broj puteva}}."""
        if not hasattr(self, "_put"):
            self._put = {}
        if x in self._put:
            return self._put[x]
        rez = {}
        for p in self.P.get(x, (None, None)):
            if not p:
                continue
            rez.setdefault(p, {})
            rez[p][1] = rez[p].get(1, 0) + 1
            for a, gens in self.putanje(p).items():
                d = rez.setdefault(a, {})
                for g, n in gens.items():
                    d[g + 1] = d.get(g + 1, 0) + n
        self._put[x] = rez
        return rez

    def kompletnost(self, x, do_gen):
        """Za svaku generaciju: koliko predaka je poznato od mogucih (2, 4, 8...)."""
        nivo, rez = [x], []
        for g in range(1, do_gen + 1):
            nivo = [p for y in nivo for p in self.P.get(y, (None, None)) if p]
            rez.append((g, len(nivo), 2 ** g))
            if not nivo:
                break
        return rez

    def udeli_predaka(self, x):
        return sorted(((self.doprinos(x, p), p) for p in self.preci(x)), key=lambda t: (-t[0], sort_key(t[1])))

    def inbr(self, x):
        o, m = self.P.get(x, (None, None))
        return self.kinship(o, m)

    def r(self, a, b):
        return 2 * self.kinship(a, b) / ((1 + self.inbr(a)) * (1 + self.inbr(b))) ** 0.5

    def odnos(self, a, b):
        oa, ma = self.P.get(a, (None, None))
        ob, mb = self.P.get(b, (None, None))
        if a in (ob, mb) or b in (oa, ma):
            return ("parent–offspring" if EN else "roditelj i potomak")
        if oa and ma and oa == ob and ma == mb:
            return ("full sibling" if EN else "puni brat / sestra")
        if (oa and oa == ob) or (ma and ma == mb):
            return ("half sibling" if EN else "polubrat / polusestra")
        if a in self.preci(b) or b in self.preci(a):
            return ("ancestor and descendant" if EN else "predak i potomak")
        r = self.r(a, b)
        return (("closely related" if EN else "blisko srodni") if r >= 0.2 else ("distant relatives" if EN else "dalji rod") if r >= 0.06
                else ("very distantly related" if EN else "daleko srodni") if r > 0 else ("unrelated" if EN else "nesrodni"))

    def pol_naziv(self, x):
        a = self.A[x]
        n = nazivi(a["vrsta"])
        return {"m": n[0], "z": n[1]}.get(a["pol"], ("sex unknown" if EN else "pol nepoznat"))


def procena(f, prag):
    if f == 0:
        return ("excellent" if EN else "odlično"), OK
    if f < prag / 2:
        return ("good" if EN else "dobro"), OK
    if f <= prag:
        return ("acceptable" if EN else "prihvatljivo"), WARN
    if f < 0.125:
        return ("risky" if EN else "rizično"), BAD
    return ("not recommended" if EN else "ne preporučuje se"), BAD


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


# =============================================================== aplikacija

class App:
    def __init__(self, root):
        self.root = root
        self.pod = self.ucitaj_podesavanja()
        self.prag = self.pod.get("prag", 0.0625)
        self.F = izaberi_font()
        root.title("Farmer")
        self.logo = {}
        try:
            self.logo = {k: tk.PhotoImage(data=v) for k, v in LOGO.items()}
        except tk.TclError:
            pass
        # ikonica prozora: prvo .ico (za stare prozore), pa logo iz programa PREKO nje -
        # tako je u naslovnoj traci i na traci zadataka uvek novi logo
        ico = os.path.join(APP_DIR, "farmer.ico")
        if not os.path.exists(ico): ico = os.path.join(getattr(sys, "_MEIPASS", APP_DIR), "farmer.ico")
        if sys.platform.startswith("win") and os.path.isfile(ico):
            try:
                root.iconbitmap(default=ico)
            except tk.TclError:
                pass
        if self.logo:
            try:
                root.iconphoto(True, self.logo[64], self.logo[32], self.logo[16])
            except tk.TclError:
                pass
        # Windows: ikonica u naslovnoj traci se postavlja i direktno preko sistema (najpouzdanije)
        if sys.platform.startswith("win") and os.path.isfile(ico):
            root.after(150, lambda: postavi_win_ikonicu(root, ico))
        root.configure(bg=BG)
        root.geometry(self.pod.get("prozor", "1240x800"))
        root.minsize(980, 620)
        self.stilovi()
        self.img_tag = ikonica_markice(TAG)
        self.img_tag_siv = ikonica_markice("#B9C2BB")

        putanja = self.pod.get("tablica") or os.path.join(APP_DIR, _ime_stada())
        if not os.path.isdir(os.path.dirname(putanja) or "."):
            putanja = os.path.join(APP_DIR, _ime_stada())
        try:
            self.tab = Tablica(putanja)
        except Exception as e:
            messagebox.showerror(("The table cannot be loaded" if EN else "Tablica se ne može učitati"), str(e))
            novi = os.path.join(APP_DIR, _ime_stada())
            if putanja != novi and os.path.isfile(novi):
                try:
                    self.tab = Tablica(novi)
                except Exception:
                    self.tab = Tablica(os.path.join(APP_DIR, ("herd_new.csv" if EN else "stado_novo.csv")), ucitaj=False)
            else:
                self.tab = Tablica(os.path.join(APP_DIR, ("herd_new.csv" if EN else "stado_novo.csv") if putanja == novi else _ime_stada()),
                                   ucitaj=False)
        self.model = Model(self.tab.redovi)
        self.ist = Istorija(self.tab.putanja)
        self.pods = Podsetnici(self.tab.putanja)
        self.strana = "grla"
        self.ui = {"q": "", "pol": "", "poreklo": "", "samo_akt": True, "par_tab": "partner", "partner": "", "ista_rasa": False,
                   "plan_max": 0, "sA": "", "sB": ""}
        self.karton_win = None

        self.shell()
        self.prikazi("grla")
        root.after(700, self.obavestenja_na_startu)
        root.after(1500, self.dnevna_kopija)
        root.bind("<FocusIn>", self.proveri_promenu)
        root.protocol("WM_DELETE_WINDOW", self.zatvori)

    # ------------------------------------------------------------ podesavanja
    def ucitaj_podesavanja(self):
        try:
            with open(PODESAVANJA, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def sacuvaj_podesavanja(self):
        self.pod.update(prag=self.prag, tablica=self.tab.putanja)
        try:
            with open(PODESAVANJA, "w", encoding="utf-8") as f:
                json.dump(self.pod, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def zatvori(self):
        try:
            self.zatvori_kopija()
        except Exception:
            pass
        if self.root.state() == "normal":
            self.pod["prozor"] = self.root.geometry()
        self.sacuvaj_podesavanja()
        self.root.destroy()

    # ------------------------------------------------------------ stil
    def f(self, size=11, weight="normal"):
        return (self.F, size, weight)

    def stilovi(self):
        s = ttk.Style()
        s.theme_use("clam")
        F = self.F
        s.configure(".", background=BG, foreground=INK, font=(F, 10), bordercolor=LINE,
                    lightcolor=LINE, darkcolor=LINE, troughcolor=SURF2, focuscolor=BRAND)
        for name, bg, fg, hov, bd in (("Primary", BRAND, "#FFFFFF", BRAND_H, BRAND),
                                      ("Secondary", SURF, INK, SURF2, LINE),
                                      ("Danger", SURF, BAD, BAD_BG, SURF)):
            s.configure(f"{name}.TButton", background=bg, foreground=fg, font=(F, 10, "bold"),
                        padding=(16, 8), borderwidth=1, bordercolor=bd, lightcolor=bg, darkcolor=bg,
                        focusthickness=0, relief="solid")
            s.map(f"{name}.TButton", background=[("active", hov), ("disabled", SURF2)],
                  lightcolor=[("active", hov)], darkcolor=[("active", hov)],
                  foreground=[("disabled", INK2)])
        s.configure("TEntry", fieldbackground=SURF, padding=(10, 7), bordercolor=LINE,
                    lightcolor=SURF, darkcolor=SURF, insertcolor=INK)
        s.map("TEntry", bordercolor=[("focus", BRAND)], lightcolor=[("focus", BRAND)])
        s.configure("TCombobox", fieldbackground=SURF, background=SURF, padding=(10, 6), arrowsize=14,
                    bordercolor=LINE, lightcolor=SURF, darkcolor=SURF, arrowcolor=INK2)
        s.map("TCombobox", fieldbackground=[("readonly", SURF)], bordercolor=[("focus", BRAND)],
              selectbackground=[("readonly", SURF)], selectforeground=[("readonly", INK)])
        self.root.option_add("*TCombobox*Listbox.font", (F, 10))
        self.root.option_add("*TCombobox*Listbox.selectBackground", BRAND)
        s.configure("TCheckbutton", background=BG, font=(F, 10), indicatorcolor=SURF,
                    indicatorbackground=SURF)
        s.map("TCheckbutton", indicatorcolor=[("selected", BRAND)], background=[("active", BG)])
        s.configure("Card.TCheckbutton", background=SURF)
        s.map("Card.TCheckbutton", background=[("active", SURF)])
        s.configure("Card.TRadiobutton", background=SURF, font=(F, 10), indicatorcolor=SURF)
        s.map("Card.TRadiobutton", indicatorcolor=[("selected", BRAND)], background=[("active", SURF)])
        s.configure("Treeview", background=SURF, fieldbackground=SURF, foreground=INK, rowheight=36,
                    borderwidth=0, font=(F, 10))
        s.map("Treeview", background=[("selected", "#D5E6DA")], foreground=[("selected", INK)])
        s.configure("Treeview.Heading", background=SURF2, foreground=INK2, font=(F, 9, "bold"),
                    relief="flat", padding=(8, 8), borderwidth=0)
        s.map("Treeview.Heading", background=[("active", SURF2)])
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.configure("Green.Horizontal.TProgressbar", troughcolor=SURF2, background=BRAND, thickness=8,
                    borderwidth=0, lightcolor=BRAND, darkcolor=BRAND)
        s.configure("Vertical.TScrollbar", background=SURF2, troughcolor=BG, bordercolor=BG, arrowcolor=INK2,
                    lightcolor=SURF2, darkcolor=SURF2, gripcount=0)

    # ------------------------------------------------------------ okvir
    def shell(self):
        side = tk.Frame(self.root, bg=SURF, width=230, highlightthickness=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(self.root, bg=LINE, width=1).pack(side="left", fill="y")

        brand = tk.Frame(side, bg=SURF)
        brand.pack(fill="x", padx=14, pady=(22, 26))
        if self.logo.get(36):
            tk.Label(brand, image=self.logo[36], bg=SURF, bd=0).pack(side="left")
        else:
            c = tk.Canvas(brand, width=34, height=38, bg=SURF, highlightthickness=0)
            c.pack(side="left")
            self.crtaj_markicu(c, 2, 2, 30, 34)
        t = tk.Frame(brand, bg=SURF)
        t.pack(side="left", padx=10)
        tk.Label(t, text="Farmer", bg=SURF, fg=INK, font=self.f(12, "bold")).pack(anchor="w")
        tk.Label(t, text=("kinship & mating" if EN else "srodstvo i parenje"), bg=SURF, fg=INK2, font=self.f(9)).pack(anchor="w")

        self.nav = {}
        for key, txt, ic in (("grla", ("Animals" if EN else "Grla"), "☰"), ("parenje", ("Mating" if EN else "Parenje"), "⚭"),
                             ("srodstvo", ("Relationship" if EN else "Srodstvo"), "⑂"), ("istorija", ("History" if EN else "Istorija"), "◷"),
                             ("obavestenja", ("Notifications" if EN else "Obaveštenja"), "◉"), ("pregled", ("Overview" if EN else "Pregled"), "▥"),
                             ("statistika", T("Statistika", "Statistics"), "▤"), ("stampa", T("Štampa i PDF", "Print and PDF"), "⎙")):
            row = tk.Frame(side, bg=SURF, cursor="hand2")
            row.pack(fill="x", padx=12, pady=1)
            li = tk.Label(row, text=ic, bg=SURF, fg=INK2, font=self.f(12), width=2)
            li.pack(side="left", padx=(10, 4), pady=9)
            lt = tk.Label(row, text=txt, bg=SURF, fg=INK2, font=self.f(11, "bold"), anchor="w")
            lt.pack(side="left", fill="x", expand=True)
            for w in (row, li, lt):
                w.bind("<Button-1>", lambda e, k=key: self.prikazi(k))
                w.bind("<Enter>", lambda e, k=key: self.nav_hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self.nav_hover(k, False))
            self.nav[key] = (row, li, lt)

        foot = tk.Frame(side, bg=SURF)
        foot.pack(side="bottom", fill="x", padx=18, pady=18)
        self.lbl_fajl = tk.Label(foot, text="", bg=SURF, fg=INK2, font=self.f(9), anchor="w", justify="left",
                                 wraplength=190)
        self.lbl_fajl.pack(anchor="w")
        lnk = tk.Label(foot, text=("Change table…" if EN else "Promeni tablicu…"), bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2")
        lnk.pack(anchor="w", pady=(4, 0))
        lnk.bind("<Button-1>", lambda e: self.promeni_tablicu())
        jez = tk.Label(foot, text=T("🌐 English", "🌐 Srpski"), bg=SURF, fg=BRAND, font=self.f(9, "bold"), cursor="hand2")
        jez.pack(anchor="w", pady=(6, 0))
        jez.bind("<Button-1>", lambda e: self.promeni_jezik())
        self.lbl_kopija = tk.Label(foot, text="", bg=SURF, fg=INK2, font=self.f(9), anchor="w", cursor="hand2")
        self.lbl_kopija.pack(anchor="w", pady=(8, 0))
        self.lbl_kopija.bind("<Button-1>", lambda e: self.prikazi("pregled"))
        self.osvezi_fajl_label()
        self.osvezi_kopija_label()

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.toast_lbl = None

    def osvezi_fajl_label(self):
        self.lbl_fajl.config(text=(f"Data: {os.path.basename(self.tab.putanja)}" if EN else f"Podaci: {os.path.basename(self.tab.putanja)}"))

    def nav_hover(self, k, on):
        row, li, lt = self.nav[k]
        bg = SURF2 if (on or k == self.strana) else SURF
        for w in (row, li, lt):
            w.config(bg=bg)

    def crtaj_markicu(self, c, x, y, w, h, boja=TAG, rupa=SURF):
        r = w * 0.18
        c.create_polygon(self.zaobljeno(x, y, x + w, y + h * 0.62, r) + [x + w, y + h * 0.62],
                         fill=boja, outline=boja, smooth=True)
        c.create_arc(x, y + h - w, x + w, y + h, start=180, extent=180, fill=boja, outline=boja)
        c.create_rectangle(x, y + h * 0.4, x + w, y + h - w / 2, fill=boja, outline=boja)
        cx, cy, rr = x + w / 2, y + h * 0.22, w * 0.1
        c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=rupa, outline="#B8A04A")
        c.create_line(x + w * 0.22, y + h * 0.52, x + w * 0.78, y + h * 0.52, fill=TAG_INK, width=2.4,
                      capstyle="round")
        c.create_line(x + w * 0.22, y + h * 0.7, x + w * 0.55, y + h * 0.7, fill=TAG_INK, width=2.4,
                      capstyle="round")

    @staticmethod
    def zaobljeno(x1, y1, x2, y2, r):
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    def cip(self, parent, text, cmd=None, siv=False, bg=SURF, big=False):
        """Ciparska 'usna markica' sa oznakom grla."""
        fnt = self.f(16 if big else 10, "bold")
        fo = tkfont.Font(font=fnt)
        tw = fo.measure(text)
        h = 40 if big else 26
        pl, pr = (34, 16) if big else (22, 10)
        w = tw + pl + pr
        c = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0, cursor="hand2" if cmd else "")
        boja = "#DDE3DC" if siv else TAG
        r = 9 if big else 7
        c.create_polygon(self.zaobljeno(1, 1, w - 1, h - 1, r), fill=boja, outline=boja, smooth=True)
        hr = 5 if big else 3.5
        hx = 17 if big else 11
        c.create_oval(hx - hr, h / 2 - hr, hx + hr, h / 2 + hr, fill=bg, outline="#A8963F" if not siv else "#AAB3AC")
        c.create_text(pl, h / 2, text=text, anchor="w", font=fnt, fill=TAG_INK if not siv else INK2)
        if cmd:
            c.bind("<Button-1>", lambda e: cmd())
        return c

    def btn(self, parent, text, cmd, kind="Secondary"):
        return ttk.Button(parent, text=text, command=cmd, style=f"{kind}.TButton", cursor="hand2")

    def card(self, parent, padx=20, pady=18):
        outer = tk.Frame(parent, bg=LINE)
        inner = tk.Frame(outer, bg=SURF)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        body = tk.Frame(inner, bg=SURF)
        body.pack(fill="both", expand=True, padx=padx, pady=pady)
        return outer, body

    def lbl(self, parent, text, size=10, weight="normal", fg=INK, bg=None, **kw):
        return tk.Label(parent, text=text, font=self.f(size, weight), fg=fg,
                        bg=bg or parent.cget("bg"), **kw)

    def badge(self, parent, text, fg, bg=None):
        bgc = {OK: OK_BG, WARN: WARN_BG, BAD: BAD_BG}.get(fg, SURF2)
        return tk.Label(parent, text=f" {text} ", font=self.f(9, "bold"), fg=fg, bg=bgc, padx=6, pady=1)

    def toast(self, text):
        if self.toast_lbl and self.toast_lbl.winfo_exists():
            self.toast_lbl.destroy()
        t = tk.Label(self.main, text=text, bg=INK, fg="#FFFFFF", font=self.f(10, "bold"), padx=18, pady=10)
        t.place(relx=0.5, rely=1.0, y=-24, anchor="s")
        self.toast_lbl = t
        self.root.after(2600, lambda: t.winfo_exists() and t.destroy())

    def stat(self, parent, broj, tekst, boja=INK):
        o, b = self.card(parent, 16, 12)
        self.lbl(b, broj, 22, "bold", fg=boja).pack(anchor="w")
        self.lbl(b, tekst, 9, fg=INK2).pack(anchor="w")
        return o

    def tabela(self, parent, kolone, visina=10, tree=True):
        wrap = tk.Frame(parent, bg=LINE)
        inner = tk.Frame(wrap, bg=SURF)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        cols = [k for k, *_ in kolone[1:]] if tree else [k for k, *_ in kolone]
        tv = ttk.Treeview(inner, columns=cols, show="tree headings" if tree else "headings", height=visina,
                          selectmode="extended")
        sb = ttk.Scrollbar(inner, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        for i, (k, naslov, w, *anc) in enumerate(kolone):
            cid = "#0" if (tree and i == 0) else k
            tv.heading(cid, text=naslov, anchor=anc[0] if anc else "w")
            tv.column(cid, width=w, minwidth=40, anchor=anc[0] if anc else "w", stretch=True)
        tv.tag_configure("odd", background="#FAFBF9")
        tv.tag_configure("off", foreground="#98A39B")
        tv.tag_configure("bad", foreground=BAD)
        tv.tag_configure("warn", foreground=WARN)
        tv.tag_configure("ok", foreground=OK)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return wrap, tv

    # ------------------------------------------------------------ podaci
    def promena(self, poruka=None):
        try:
            self.ist.sacuvaj()
            self.pods.sacuvaj()
        except OSError:
            pass
        try:
            self.tab.sacuvaj()
        except PermissionError:
            messagebox.showerror(("Not saved" if EN else "Nije sačuvano"),
                                 ("The table is open in Excel or another program.\n"
                                 "Close it and try again." if EN else "Tablica je otvorena u Excelu ili drugom programu.\n"
                                 "Zatvori je pa pokušaj ponovo."))
            self.tab.ucitaj()
        self.model = Model(self.tab.redovi)
        self.prikazi(self.strana)
        if self.karton_win and self.karton_win.winfo_exists():
            self.karton(self.karton_win.grlo)
        if poruka:
            self.toast(poruka)

    def proveri_promenu(self, e=None):
        if e is not None and e.widget is not self.root:
            return
        p = self.tab.putanja
        if os.path.isfile(p) and self.tab.mtime and os.path.getmtime(p) != self.tab.mtime:
            try:
                self.tab.ucitaj()
            except Exception as ex:
                messagebox.showerror(("Error in table" if EN else "Greška u tablici"), str(ex))
                return
            self.model = Model(self.tab.redovi)
            self.prikazi(self.strana)
            self.toast(("The table was reloaded (changed in Excel)." if EN else "Tablica je ponovo učitana (izmenjena u Excelu)."))

    def promeni_tablicu(self):
        p = filedialog.askopenfilename(title=("Choose the animals table" if EN else "Izaberi tablicu sa grlima"), initialdir=APP_DIR,
                                       filetypes=[(("CSV table" if EN else "CSV tablica"), "*.csv"), (("All files" if EN else "Svi fajlovi"), "*.*")])
        if not p:
            return
        try:
            t = Tablica(p)
        except Exception as e:
            messagebox.showerror(("The table cannot be loaded" if EN else "Tablica se ne može učitati"), str(e))
            return
        self.tab = t
        self.ist = Istorija(t.putanja)
        self.pods = Podsetnici(t.putanja)
        self.model = Model(t.redovi)
        self.sacuvaj_podesavanja()
        self.osvezi_fajl_label()
        self.prikazi(self.strana)
        self.toast((f"Loaded {len(t.redovi)} animals." if EN else f"Učitano {len(t.redovi)} grla."))

    def uvezi(self):
        p = filedialog.askopenfilename(title=("Import table from Excel (CSV)" if EN else "Uvezi tablicu iz Excela (CSV)"),
                                       filetypes=[(("CSV table" if EN else "CSV tablica"), "*.csv"), (("All files" if EN else "Svi fajlovi"), "*.*")])
        if not p:
            return
        try:
            redovi, _ = procitaj_csv(p)
        except Exception as e:
            messagebox.showerror(("Import failed" if EN else "Uvoz nije uspeo"), str(e))
            return
        po_id = {r["id"]: r for r in self.tab.redovi}
        nov = izm = 0
        for r in redovi:
            r = {k: r.get(k, "") for k in KOLONE}
            if r["id"] in po_id:
                if not r["uneto"]:
                    r.pop("uneto")
                po_id[r["id"]].update(r)
                izm += 1
            else:
                r["uneto"] = r.get("uneto") or sada()
                self.tab.redovi.append(r)
                self.ist.dodaj(r["id"], AUTO, (f"Added by import from table {os.path.basename(p)}" if EN else f"Upisano uvozom iz tablice {os.path.basename(p)}"), automatski=True)
                po_id[r["id"]] = r
                nov += 1
        self.promena((f"Imported: {nov} new" if EN else f"Uvezeno: {nov} novih") + ((f", {izm} changed" if EN else f", {izm} izmenjenih") if izm else "") + (" animals." if EN else " grla."))

    def otvori_excel(self):
        if not os.path.isfile(self.tab.putanja):
            self.tab.sacuvaj()
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.tab.putanja)
            elif sys.platform == "darwin":
                os.system(f'open "{self.tab.putanja}"')
            else:
                os.system(f'xdg-open "{self.tab.putanja}" &')
            self.toast(("When you save changes in Excel, the program will reload them." if EN else "Kad sačuvaš izmene u Excelu, program će ih sam učitati."))
        except OSError:
            messagebox.showinfo(("Table" if EN else "Tablica"), self.tab.putanja)

    # ------------------------------------------------------------ strane
    def prikazi(self, strana):
        self.strana = strana
        for k in self.nav:
            row, li, lt = self.nav[k]
            akt = k == strana or (k == "grla" and strana == "obrisana")
            for w in (row, li, lt):
                w.config(bg=SURF2 if akt else SURF)
            lt.config(fg=INK if akt else INK2)
            li.config(fg=BRAND if akt else INK2)
        self.osvezi_nav_brojac()
        for w in self.main.winfo_children():
            if w is not self.toast_lbl:
                w.destroy()
        getattr(self, "s_" + strana)()

    def zaglavlje(self, parent, naslov, podnaslov="", akcije=()):
        h = tk.Frame(parent, bg=BG)
        h.pack(fill="x", pady=(0, 18))
        desno = tk.Frame(h, bg=BG)
        desno.pack(side="right", anchor="s")
        for txt, cmd, kind in reversed(akcije):
            self.btn(desno, txt, cmd, kind).pack(side="right", padx=(8, 0))
        levo = tk.Frame(h, bg=BG)
        levo.pack(side="left", fill="x", expand=True)
        self.lbl(levo, naslov, 24, "bold").pack(anchor="w")
        if podnaslov:
            self.lbl(levo, podnaslov, 10, fg=INK2, justify="left",
                     wraplength=620 if not akcije else 300).pack(anchor="w", pady=(2, 0))
        return h

    def prazno(self, parent):
        o, b = self.card(parent, 30, 50)
        o.pack(fill="x")
        if self.logo.get(64):
            tk.Label(b, image=self.logo[64], bg=SURF, bd=0).pack()
        else:
            c = tk.Canvas(b, width=56, height=64, bg=SURF, highlightthickness=0)
            c.pack()
            self.crtaj_markicu(c, 4, 2, 48, 58)
        self.lbl(b, ("The herd is still empty" if EN else "Stado je još prazno"), 16, "bold").pack(pady=(14, 4))
        self.lbl(b, ("Add animals one by one or import an existing table from Excel.\n"
                    "For each animal enter the sire and dam if you know them." if EN else "Dodaj grla jedno po jedno ili uvezi postojeću tablicu iz Excela.\n"
                    "Za svako grlo upiši oca i majku ako ih znaš."), 10, fg=INK2, justify="center").pack()
        r = tk.Frame(b, bg=SURF)
        r.pack(pady=(18, 0))
        self.btn(r, ("+  Add first animal" if EN else "+  Dodaj prvo grlo"), lambda: self.forma(), "Primary").pack(side="left", padx=4)
        self.btn(r, ("Import table from Excel" if EN else "Uvezi tablicu iz Excela"), self.uvezi).pack(side="left", padx=4)

    def strana_okvir(self, scroll=True):
        if scroll:
            sf = ScrollFrame(self.main)
            sf.pack(fill="both", expand=True)
            body = tk.Frame(sf.inner, bg=BG)
            body.pack(fill="both", expand=True, padx=36, pady=28)
            return body
        body = tk.Frame(self.main, bg=BG)
        body.pack(fill="both", expand=True, padx=36, pady=28)
        return body

    # ---------- Grla
    def s_grla(self):
        body = self.strana_okvir(scroll=False)
        sva = self.model.grla()
        akt = sum(a["aktivno"] for a in sva)
        self.zaglavlje(body, ("Animals" if EN else "Grla"), (f"{akt} in herd, {len(sva)} recorded in total." if EN else f"{akt} u zapatu, ukupno {len(sva)} upisanih.")
                       if sva else ("Records of all animals with their parents." if EN else "Evidencija svih grla sa roditeljima."),
                       [(("Partner search" if EN else "Pretraga partnera"), self.idi_na_pretragu, "Secondary"),
                        (("Import" if EN else "Uvezi"), self.uvezi, "Secondary"), (("Open in Excel" if EN else "Otvori u Excelu"), self.otvori_excel, "Secondary"),
                        (("+  New animal" if EN else "+  Novo grlo"), lambda: self.forma(), "Primary")])
        if not sva:
            self.prazno(body)
            return
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        self.q_var = tk.StringVar(value=self.ui["q"])
        e = ttk.Entry(tb, textvariable=self.q_var, font=self.f(10), width=26)
        e.pack(side="left")
        ph = self.lbl(tb, ("⌕  Search by tag, ear tag, breed…" if EN else "⌕  Traži po oznaci, markici, rasi…"), 10, fg="#98A39B", bg=SURF)
        def ph_show(*_):
            if self.q_var.get():
                ph.place_forget()
            else:
                ph.place(in_=e, x=10, rely=0.5, anchor="w")
        ph.bind("<Button-1>", lambda ev: e.focus_set())
        ph_show()
        self.pol_var = tk.StringVar(value={"": ("All sexes" if EN else "Svi polovi"), "z": ("Females" if EN else "Ženska"), "m": ("Males" if EN else "Muška")}[self.ui["pol"]])
        cb = ttk.Combobox(tb, textvariable=self.pol_var, values=[("All sexes" if EN else "Svi polovi"), ("Females" if EN else "Ženska"), ("Males" if EN else "Muška")], width=10,
                          state="readonly", font=self.f(10))
        cb.pack(side="left", padx=10)
        self.por_var = tk.StringVar(value=self.ui.get("poreklo") or ("Any origin" if EN else "Svako poreklo"))
        cbp = ttk.Combobox(tb, textvariable=self.por_var, values=[("Any origin" if EN else "Svako poreklo")] + POREKLA, width=15,
                           state="readonly", font=self.f(10))
        cbp.pack(side="left", padx=(0, 10))
        cbp.bind("<<ComboboxSelected>>", lambda ev: self.grla_filter())
        self.akt_var = tk.BooleanVar(value=self.ui["samo_akt"])
        ttk.Checkbutton(tb, text=("Only in herd" if EN else "Samo u zapatu"), variable=self.akt_var,
                        command=lambda: self.grla_filter()).pack(side="left", padx=6)
        self.red_var = tk.StringVar(value=self.ui.get("redosled") or REDOSLEDI[0])
        cbr = ttk.Combobox(tb, textvariable=self.red_var, values=REDOSLEDI, state="readonly", width=21,
                           font=self.f(10))
        cbr.pack(side="right")
        cbr.bind("<<ComboboxSelected>>", lambda ev: self.grla_filter())
        self.lbl(tb, ("Order:" if EN else "Redosled:"), 9, "bold", fg=INK2).pack(side="right", padx=(0, 6))

        wrap, tv = self.tabela(body, [("id", ("Animal" if EN else "Grlo"), 105), ("markica", ("Ear tag" if EN else "Markica"), 125), ("pol", ("Sex" if EN else "Pol"), 70),
                                      ("rasa", ("Breed" if EN else "Rasa"), 130), ("starost", ("Age" if EN else "Starost"), 90), ("otac", ("Sire" if EN else "Otac"), 100),
                                      ("majka", ("Dam" if EN else "Majka"), 100), ("upis", ("Added" if EN else "Upisano"), 95), ("f", ("Inbreeding" if EN else "Inbriding"), 90, "e")],
                               visina=14)
        wrap.pack(fill="both", expand=True)
        self.tv_grla = tv
        tv.bind("<Double-1>", lambda ev: self.otvori_iz(tv))
        tv.bind("<Return>", lambda ev: self.otvori_iz(tv))
        tv.bind("<Delete>", lambda ev: self.obrisi_grla([i for i in tv.selection() if i in self.model.A]))
        tv.bind("<Button-3>", lambda ev: self.meni_grla(tv, ev))
        tv.bind("<Button-2>", lambda ev: self.meni_grla(tv, ev))
        dno = tk.Frame(body, bg=BG)
        dno.pack(fill="x", pady=(8, 0))
        self.lbl(dno, ("Double-click opens the card, right-click gives more options. To delete, select an animal (or several with Ctrl) and press Delete." if EN else "Dvoklik otvara karton, desni klik daje više opcija. Za brisanje označi grlo (ili više uz Ctrl) i pritisni Delete."),
                 9, fg=INK2).pack(side="left")
        n_obr = len(self.model.obrisana())
        if n_obr:
            lnk = self.lbl(dno, (f"Deleted animals ({n_obr})" if EN else f"Obrisana grla ({n_obr})"), 9, "bold", fg=BRAND, cursor="hand2")
            lnk.pack(side="right")
            lnk.bind("<Button-1>", lambda e: self.prikazi("obrisana"))
        self.q_var.trace_add("write", lambda *_: (ph_show(), self.grla_filter()))
        cb.bind("<<ComboboxSelected>>", lambda ev: self.grla_filter())
        self.grla_filter()

    def grla_filter(self):
        self.ui["q"] = self.q_var.get()
        self.ui["pol"] = {("Females" if EN else "Ženska"): "z", ("Males" if EN else "Muška"): "m"}.get(self.pol_var.get(), "")
        self.ui["poreklo"] = "" if self.por_var.get() == ("Any origin" if EN else "Svako poreklo") else self.por_var.get()
        self.ui["samo_akt"] = self.akt_var.get()
        self.ui["redosled"] = self.red_var.get()
        tv, m, q = self.tv_grla, self.model, norm(self.ui["q"])
        tv.delete(*tv.get_children())
        i = 0
        for a in m.grla(redosled=self.ui["redosled"]):
            if self.ui["samo_akt"] and not a["aktivno"]:
                continue
            if self.ui["poreklo"] and norm(a["poreklo"]) != norm(self.ui["poreklo"]):
                continue
            if self.ui["pol"] and a["pol"] != self.ui["pol"]:
                continue
            if q and not (any(q in norm(a[k]) for k in ("id", "markica", "rasa", "stado", "poreklo_od"))
                          or any(q in norm(x) for x in a["stare"])):
                continue
            o, mj = m.P[a["id"]]
            f = m.inbr(a["id"])
            tags = ["odd"] if i % 2 else []
            if not a["aktivno"]:
                tags.append("off")
            elif f > self.prag:
                tags.append("bad")
            if self.karenca(a["id"]):
                tags.append("kar")
            tv.tag_configure("kar", foreground=WARN)
            tv.insert("", "end", iid=a["id"], text="  " + a["id"] + ("  ✚" if "kar" in tags else ""), image=self.img_tag,
                      values=(a["markica"] or "–", m.pol_naziv(a["id"]), a["rasa"] or "–",
                              fmt_starost(starost_meseci(a["datum"])) or "–", o or "–", mj or "–",
                              fmt_upis(a["uneto"]), pct(f) + ("  ⚠" if f > self.prag else "")), tags=tags)
            i += 1
        if not i:
            tv.insert("", "end", text="", values=("", ("No animal matches the search." if EN else "Nijedno grlo ne odgovara pretrazi."), "", "", "", "", "", ""))

    def idi_na_pretragu(self, x=None):
        self.ui.update(par_tab="partner", partner_vise=[])
        if x:
            self.ui.update(partner=x, partner_upit=x)
        self.prikazi("parenje")

    def otvori_iz(self, tv):
        sel = tv.selection()
        if sel and sel[0] in self.model.A:
            self.karton(sel[0])

    # ---------- brisanje
    def red_za(self, jid):
        return next((r for r in self.tab.redovi if r["id"] == jid), None)

    # ---------- usne markice
    def markica_zauzeta(self, mk, red):
        """Vrati poruku ako je markica vec kod drugog grla, inace None."""
        n = norm(mk)
        for r in self.tab.redovi:
            if r is red:
                continue
            if r.get("markica") and norm(r["markica"]) == n:
                return (f"Ear tag {mk} is already entered for animal {r['id']}." if EN else f"Markica {mk} je već upisana za grlo {r['id']}.")
            if any(norm(x) == n for x in stare_lista(r)):
                return (f"Ear tag {mk} previously belonged to animal {r['id']}." if EN else f"Markica {mk} je ranije pripadala grlu {r['id']}.")
            if norm(r["id"]) == n:
                return (f"{mk} is already the tag of animal {r['id']}." if EN else f"{mk} je već oznaka grla {r['id']}.")
        return None

    def primeni_markicu(self, red, nova, zapamti=True):
        """Promeni markicu i popravi potomke koji su roditelja upisali preko stare markice."""
        stara = (red.get("markica") or "").strip()
        nova = nova.strip()
        if stara and norm(stara) != norm(nova):
            n = norm(stara)
            for r in self.tab.redovi:
                if r is red:
                    continue
                for p in ("otac", "majka"):
                    if r.get(p) and norm(r[p]) == n and r[p] != red["id"]:
                        r[p] = red["id"]
            if zapamti:
                st = stare_lista(red)
                if all(norm(x) != n for x in st):
                    st.append(stara)
                red["stare_markice"] = ", ".join(st)
        red["stare_markice"] = ", ".join(x for x in stare_lista(red) if norm(x) != norm(nova))
        if norm(stara) != norm(nova):
            self.ist.dodaj(red["id"], AUTO, (f"Ear tag changed: {stara or '–'} → {nova or '–'}" if EN else f"Ušna markica promenjena: {stara or '–'} → {nova or '–'}"), automatski=True)
        red["markica"] = nova

    def promena_markice(self, jid, parent=None):
        red = self.red_za(jid)
        if not red:
            return
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Change ear tag" if EN else "Promena ušne markice"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Change ear tag" if EN else "Promena ušne markice"), 16, "bold").pack(anchor="w")
        top = tk.Frame(b, bg=SURF)
        top.pack(anchor="w", pady=(14, 4))
        self.cip(top, jid).pack(side="left")
        self.lbl(top, (f"current ear tag:  {red.get('markica') or '–'}" if EN else f"sadašnja markica:  {red.get('markica') or '–'}"), 10, fg=INK2).pack(side="left", padx=12)
        stare = stare_lista(red)
        if stare:
            self.lbl(b, ("Previous ear tags: " if EN else "Ranije markice: ") + ", ".join(stare), 9, fg=INK2).pack(anchor="w")
        self.lbl(b, ("New ear tag" if EN else "Nova markica"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 4))
        var = tk.StringVar(value=red.get("markica", ""))
        e = ttk.Entry(b, textvariable=var, width=36, font=self.f(11))
        e.pack(anchor="w", fill="x")
        self.lbl(b, ("e.g. UK 123456 700123. Leave empty to remove the ear tag." if EN else "npr. RS 1234-5678. Ostavi prazno da ukloniš markicu."),
                 8, fg="#8A968D").pack(anchor="w")
        zap = tk.BooleanVar(value=True)
        ttk.Checkbutton(b, text=("Remember the old ear tag (search still finds the animal by its old number)" if EN else "Zapamti staru markicu (pretraga i dalje nalazi grlo po starom broju)"),
                        variable=zap, style="Card.TCheckbutton").pack(anchor="w", pady=(12, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            nova = var.get().strip()
            if norm(nova) == norm(red.get("markica")) and nova == (red.get("markica") or ""):
                win.destroy()
                return
            if nova:
                poruka = self.markica_zauzeta(nova, red)
                if poruka:
                    err.config(text=poruka)
                    return
            stara = red.get("markica") or "–"
            self.primeni_markicu(red, nova, zapamti=zap.get())
            win.grab_release()
            win.destroy()
            self.promena((f"{jid}: ear tag {stara} → {nova or '–'}" if EN else f"{jid}: markica {stara} → {nova or '–'}"))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
        e.focus_set()
        e.select_range(0, "end")

    # ---------- stado
    def sva_stada(self):
        return sorted({r.get("stado", "").strip() for r in self.tab.redovi if r.get("stado", "").strip()},
                      key=sort_key)

    def promena_stada(self, ids, parent=None):
        ids = [i for i in ids if self.red_za(i)]
        if not ids:
            return
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Move to another herd" if EN else "Premeštanje u drugo stado"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Move to another herd" if EN else "Premeštanje u drugo stado"), 16, "bold").pack(anchor="w")
        top = tk.Frame(b, bg=SURF)
        top.pack(anchor="w", pady=(12, 4))
        for i in ids[:8]:
            self.cip(top, i).pack(side="left", padx=(0, 6))
        if len(ids) > 8:
            self.lbl(top, (f"+ {len(ids) - 8} more" if EN else f"+ još {len(ids) - 8}"), 9, fg=INK2).pack(side="left")
        sada_st = sorted({self.red_za(i).get("stado") or "–" for i in ids})
        self.lbl(b, ("Current herd: " if EN else "Sadašnje stado: ") + ", ".join(sada_st), 10, fg=INK2).pack(anchor="w")
        self.lbl(b, ("New herd" if EN else "Novo stado"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 4))
        sv = tk.StringVar(value="")
        e = ttk.Combobox(b, textvariable=sv, values=self.sva_stada(), width=34, font=self.f(11))
        e.pack(anchor="w", fill="x")
        self.lbl(b, ("Choose an existing herd or type a new name." if EN else "Izaberi postojeće stado ili upiši novi naziv."), 8, fg="#8A968D").pack(anchor="w")
        self.lbl(b, ("Date of move" if EN else "Datum premeštanja"), 9, "bold", fg=INK2).pack(anchor="w", pady=(12, 4))
        dv = tk.StringVar(value=date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        ttk.Entry(b, textvariable=dv, width=16, font=self.f(10)).pack(anchor="w")
        zv = tk.BooleanVar(value=True)
        ttk.Checkbutton(b, text=("Record the move in the animal's history" if EN else "Zapiši premeštanje u istoriju grla"), variable=zv,
                        style="Card.TCheckbutton").pack(anchor="w", pady=(12, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            novo = sv.get().strip()
            if not novo:
                err.config(text=("Type or choose the new herd." if EN else "Upiši ili izaberi novo stado."))
                return
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            # isti naziv kao postojece stado (bez obzira na velika slova) -> koristi postojeci
            novo = next((x for x in self.sva_stada() if x.lower() == novo.lower()), novo)
            pomereno = 0
            for i in ids:
                r = self.red_za(i)
                staro = (r.get("stado") or "").strip()
                if staro == novo:
                    continue
                r["stado"] = novo
                pomereno += 1
                if zv.get():
                    self.ist.dodaj(i, ("Move" if EN else "Premeštanje"), (f"From herd {staro or '–'} to herd {novo}" if EN else f"Iz stada {staro or '–'} u stado {novo}"),
                                   datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), vrednost=novo)
            win.grab_release()
            win.destroy()
            self.promena((f"Moved to herd {novo}: {pomereno} animals" if EN else f"Premešteno u stado {novo}: {pomereno} grla") if pomereno else ("The animals are already in that herd." if EN else "Grla su već u tom stadu."))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, ("Move" if EN else "Premesti"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
        e.focus_set()

    def preimenuj_stado(self, staro):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Rename herd" if EN else "Preimenovanje stada"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        n = sum(1 for r in self.tab.redovi if (r.get("stado") or "").strip() == staro)
        self.lbl(b, ("Rename herd" if EN else "Preimenovanje stada"), 16, "bold").pack(anchor="w")
        self.lbl(b, (f"Herd \"{staro}\" has {n} animals. The new name applies to all of them." if EN else f"Stado „{staro}“ ima {n} grla. Novi naziv važi za sva ta grla."), 10, fg=INK2).pack(
            anchor="w", pady=(8, 0))
        self.lbl(b, ("New name" if EN else "Novi naziv"), 9, "bold", fg=INK2).pack(anchor="w", pady=(14, 4))
        sv = tk.StringVar(value=staro)
        e = ttk.Entry(b, textvariable=sv, width=34, font=self.f(11))
        e.pack(anchor="w", fill="x")
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            novo = sv.get().strip()
            if not novo:
                err.config(text=("Type a new name." if EN else "Upiši novi naziv."))
                return
            if novo == staro:
                win.destroy()
                return
            for r in self.tab.redovi:
                if (r.get("stado") or "").strip() == staro:
                    r["stado"] = novo
                    self.ist.dodaj(r["id"], AUTO, (f"Herd renamed: {staro} → {novo}" if EN else f"Stado preimenovano: {staro} → {novo}"), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Herd \"{staro}\" is now \"{novo}\"" if EN else f"Stado „{staro}“ je sada „{novo}“"))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(18, 0))
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.update_idletasks()
        win.geometry(f"+{self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2}"
                     f"+{self.root.winfo_rooty() + 120}")
        e.focus_set()
        e.select_range(0, "end")

    # ---------- brisanje svih grla (5 koraka)
    def brisanje_svih(self):
        n_grla = len(self.tab.redovi)
        if not n_grla:
            messagebox.showinfo(("Delete all animals" if EN else "Brisanje svih grla"), ("There are no animals in the records." if EN else "U evidenciji nema nijednog grla."))
            return
        n_ist = len(self.ist.zapisi)
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Delete all animals" if EN else "Brisanje svih grla"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        st = {"korak": 1, "istorija": tk.StringVar(value="sve"), "kopija": None, "tekst": tk.StringVar(),
              "odbrojavanje": 0, "gotovo": False}
        NASLOVI = [("Warning" if EN else "Upozorenje"), ("What is deleted" if EN else "Šta se briše"), ("Backup" if EN else "Rezervna kopija"), ("Confirmation" if EN else "Potvrda"), ("Deletion" if EN else "Brisanje")]

        glava = tk.Frame(win, bg=SURF)
        glava.pack(fill="x", padx=26, pady=(22, 0))
        sadrzaj = tk.Frame(win, bg=SURF, width=560, height=290)
        sadrzaj.pack(fill="both", expand=True, padx=26, pady=(14, 0))
        sadrzaj.pack_propagate(False)
        dno = tk.Frame(win, bg=SURF)
        dno.pack(fill="x", padx=26, pady=(10, 20))

        def nacrtaj():
            for w in glava.winfo_children() + sadrzaj.winfo_children() + dno.winfo_children():
                w.destroy()
            k = st["korak"]
            self.lbl(glava, (f"Step {k} of 5 – {NASLOVI[k - 1]}" if EN else f"Korak {k} od 5 – {NASLOVI[k - 1]}"), 16, "bold",
                     fg=BAD if k >= 4 else INK).pack(anchor="w")
            tr = tk.Frame(glava, bg=SURF)
            tr.pack(anchor="w", pady=(10, 0))
            for i in range(1, 6):
                boja = BAD if i <= k and k >= 4 else BRAND if i <= k else SURF2
                tk.Frame(tr, bg=boja, width=100, height=6).pack(side="left", padx=(0, 6))
            [k1, k2, k3, k4, k5][k - 1]()

        def dugmad(dalje_txt="Dalje  ›", dalje=None, dalje_stil="Primary", nazad=True, stanje="normal"):
            self.btn(dno, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="left")
            b = self.btn(dno, dalje_txt, dalje or sledeci, dalje_stil)
            b.pack(side="right")
            if stanje == "disabled":
                b.state(["disabled"])
            if nazad and st["korak"] > 1:
                self.btn(dno, ("‹  Back" if EN else "‹  Nazad"), prethodni).pack(side="right", padx=8)
            return b

        def sledeci():
            st["korak"] += 1
            nacrtaj()

        def prethodni():
            st["korak"] -= 1
            nacrtaj()

        def k1():
            self.napomena(sadrzaj, wraplength=520, tekst=("This action deletes ALL animals from the records. After that the animal list, mating plan, "
                                   "relationships and overview will be empty." if EN else "Ova radnja briše SVA grla iz evidencije. Posle toga lista grla, plan parenja, "
                                   "srodstvo i pregled biće prazni."))
            self.lbl(sadrzaj, ("Currently in the records:" if EN else "U evidenciji je sada:"), 10, "bold").pack(anchor="w", pady=(4, 6))
            for t in ((f"•  {n_grla} animals (including deleted and out of herd)" if EN else f"•  {n_grla} grla (uključujući obrisana i van zapata)"),
                      (f"•  {n_ist} history records" if EN else f"•  {n_ist} zapisa u istoriji"),
                      (f"•  table: {self.tab.putanja}" if EN else f"•  tablica: {self.tab.putanja}")):
                self.lbl(sadrzaj, t, 10, fg=INK2, wraplength=540, justify="left").pack(anchor="w", pady=1)
            self.lbl(sadrzaj, ("If you only want to remove some animals, cancel and use normal deletion "
                              "(select the animal and press Delete)." if EN else "Ako želiš da ukloniš samo neka grla, otkaži i koristi obično brisanje "
                              "(označi grlo i pritisni Delete)."), 9, fg=INK2, wraplength=540,
                     justify="left").pack(anchor="w", pady=(14, 0))
            dugmad(("I understand, next  ›" if EN else "Razumem, dalje  ›"))

        def k2():
            self.lbl(sadrzaj, ("Choose what is deleted:" if EN else "Izaberi šta se briše:"), 10, "bold").pack(anchor="w", pady=(0, 8))
            for val, t, opis in (("sve", ("All animals and the whole history" if EN else "Sva grla i cela istorija"),
                                  ("The records become completely empty, like a new program." if EN else "Evidencija postaje potpuno prazna, kao novi program.")),
                                 ("grla", ("Animals only, history is kept" if EN else "Samo grla, istorija ostaje sačuvana"),
                                  ("History records stay in the file but are not shown until the animals are entered again." if EN else "Zapisi iz istorije ostaju u fajlu, ali se ne vide dok se grla ponovo ne upišu."))):
                ttk.Radiobutton(sadrzaj, text=t, value=val, variable=st["istorija"],
                                style="Card.TRadiobutton").pack(anchor="w", pady=(6, 0))
                self.lbl(sadrzaj, opis, 9, fg=INK2).pack(anchor="w", padx=26)
            dugmad()

        def k3():
            self.lbl(sadrzaj, ("Before deleting, the program makes a backup of all data. Everything can be "
                              "restored from it if you change your mind." if EN else "Pre brisanja program pravi rezervnu kopiju svih podataka. Iz nje se sve može "
                              "vratiti ako se predomisliš."), 10, wraplength=540, justify="left").pack(anchor="w")
            if not st["kopija"]:
                try:
                    folder = self.folder_kopija()
                    os.makedirs(folder, exist_ok=True)
                    oznaka = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    kopije = []
                    for izvor in (self.tab.putanja, self.ist.putanja):
                        if os.path.isfile(izvor):
                            ime, ext = os.path.splitext(os.path.basename(izvor))
                            cilj = os.path.join(folder, (f"{ime}_before_delete_{oznaka}{ext}" if EN else f"{ime}_pre_brisanja_{oznaka}{ext}"))
                            shutil.copy2(izvor, cilj)
                            kopije.append((izvor, cilj))
                    st["kopija"] = (folder, kopije)
                except OSError as e:
                    self.napomena(sadrzaj, wraplength=520, tekst=(f"Backup was not made: {e}\nDeletion has been stopped." if EN else f"Rezervna kopija nije napravljena: {e}\nBrisanje je zaustavljeno."))
                    dugmad(("Next  ›" if EN else "Dalje  ›"), stanje="disabled")
                    return
            folder, kopije = st["kopija"]
            self.napomena(sadrzaj, wraplength=520, tekst=("Backup has been made." if EN else "Rezervna kopija je napravljena."), ok=True)
            for _, cilj in kopije:
                self.lbl(sadrzaj, "•  " + os.path.basename(cilj), 10, fg=INK2).pack(anchor="w", pady=1)
            self.lbl(sadrzaj, f"Folder: {folder}", 9, fg=INK2, wraplength=540, justify="left").pack(
                anchor="w", pady=(8, 0))
            lk = self.lbl(sadrzaj, ("Open backup folder" if EN else "Otvori folder sa kopijom"), 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(anchor="w", pady=(6, 0))
            lk.bind("<Button-1>", lambda e: otvori_folder(folder))
            dugmad()

        def k4():
            self.lbl(sadrzaj, ("To confirm, type exactly:" if EN else "Da potvrdiš, upiši tačno reči:"), 10).pack(anchor="w")
            self.lbl(sadrzaj, ("DELETE ALL" if EN else "OBRIŠI SVE"), 18, "bold", fg=BAD).pack(anchor="w", pady=(6, 10))
            e = ttk.Entry(sadrzaj, textvariable=st["tekst"], width=24, font=self.f(13))
            e.pack(anchor="w")
            info = self.lbl(sadrzaj, "", 9, fg=INK2)
            info.pack(anchor="w", pady=(6, 0))
            b = dugmad(stanje="disabled")

            def provera(*_):
                if EN:
                    ok = norm(st["tekst"].get()) == "DELETEALL"
                else:
                    ok = norm(st["tekst"].get()).replace("Š", "S") == "OBRISISVE"
                b.state(["!disabled"] if ok else ["disabled"])
                info.config(text=("Confirmed." if EN else "Potvrđeno.") if ok else ("The \"Next\" button turns on when you type the exact text." if EN else "Dugme „Dalje“ se uključuje kad upišeš tačan tekst."),
                            fg=OK if ok else INK2)
            tr_id = st["tekst"].trace_add("write", provera)
            e.bind("<Destroy>", lambda ev: st["tekst"].trace_remove("write", tr_id))
            provera()
            e.focus_set()

        def k5():
            if st["gotovo"]:
                folder, kopije = st["kopija"]
                self.napomena(sadrzaj, wraplength=520, tekst=("All animals have been deleted." if EN else "Sva grla su obrisana."), ok=True)
                self.lbl(sadrzaj, ("The backup is saved in the folder:" if EN else "Rezervna kopija je sačuvana u folderu:"), 10).pack(anchor="w")
                self.lbl(sadrzaj, folder, 9, fg=INK2, wraplength=540, justify="left").pack(anchor="w", pady=(2, 10))
                self.lbl(sadrzaj, ("If this was a mistake, click \"Restore data\" – everything will be as before." if EN else "Ako je ovo bila greška, klikni „Vrati podatke“ – sve će biti kao pre brisanja."),
                         9, fg=INK2, wraplength=540, justify="left").pack(anchor="w")
                self.btn(dno, ("Restore data" if EN else "Vrati podatke"), vrati).pack(side="left")
                self.btn(dno, ("Close" if EN else "Zatvori"), win.destroy, "Primary").pack(side="right")
                return
            sta = ("all animals and the whole history" if EN else "sva grla i celu istoriju") if st["istorija"].get() == "sve" else ("all animals (history is kept)" if EN else "sva grla (istorija ostaje)")
            self.lbl(sadrzaj, (f"Last step. Clicking the button deletes {sta}." if EN else f"Poslednji korak. Klikom na dugme briše se {sta}."), 11, "bold",
                     wraplength=540, justify="left").pack(anchor="w")
            self.lbl(sadrzaj, (f"Number of animals: {n_grla}" if EN else f"Broj grla: {n_grla}") + ((f"   ·   history records: {n_ist}" if EN else f"   ·   zapisa istorije: {n_ist}")
                                                          if st["istorija"].get() == "sve" else ""),
                     10, fg=INK2).pack(anchor="w", pady=(6, 0))
            odb = self.lbl(sadrzaj, "", 10, "bold", fg=WARN)
            odb.pack(anchor="w", pady=(16, 0))
            b = dugmad(("Permanently delete all" if EN else "Trajno obriši sve"), obrisi_sve, "Danger", stanje="disabled")
            st["odbrojavanje"] = 5

            def tik():
                if not odb.winfo_exists():
                    return
                if st["odbrojavanje"] > 0:
                    odb.config(text=(f"The button turns on in {st['odbrojavanje']} s…" if EN else f"Dugme se uključuje za {st['odbrojavanje']} s…"))
                    st["odbrojavanje"] -= 1
                    win.after(1000, tik)
                else:
                    odb.config(text=("You can confirm the deletion." if EN else "Možeš potvrditi brisanje."), fg=BAD)
                    b.state(["!disabled"])
            tik()

        def otvori_folder(folder):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}" &')
            except OSError:
                pass

        def zatvori_prozore():
            for w in (self.karton_win, getattr(self, "ist_win", None), getattr(self, "stablo_win", None)):
                if w is not None and w.winfo_exists():
                    w.destroy()
            self.ui.update(partner="", partner_upit="", partner_vise=[], sA="", sB="")

        def obrisi_sve():
            zatvori_prozore()
            self.tab.redovi = []
            if st["istorija"].get() == "sve":
                self.ist.zapisi = []
            self.promena((f"Deleted all {n_grla} animals." if EN else f"Obrisano svih {n_grla} grla."))
            st["gotovo"] = True
            nacrtaj()

        def vrati():
            folder, kopije = st["kopija"]
            try:
                for izvor, cilj in kopije:
                    shutil.copy2(cilj, izvor)
                self.tab.ucitaj()
                self.ist = Istorija(self.tab.putanja)
                self.pods = Podsetnici(self.tab.putanja)
            except Exception as e:
                messagebox.showerror(("Restore failed" if EN else "Vraćanje nije uspelo"), str(e), parent=win)
                return
            self.model = Model(self.tab.redovi)
            self.prikazi(self.strana)
            self.toast((f"Restored {len(self.tab.redovi)} animals from the backup." if EN else f"Vraćeno {len(self.tab.redovi)} grla iz rezervne kopije."))
            win.destroy()

        win.bind("<Escape>", lambda e: win.destroy())
        nacrtaj()
        win.update_idletasks()
        win.geometry(f"+{self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2}"
                     f"+{self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 3)}")

    def obrisi_grla(self, ids, parent=None):
        ids = [i for i in ids if self.red_za(i) and self.red_za(i).get("status") != "obrisano"]
        if not ids:
            return False
        naziv = ids[0] if len(ids) == 1 else (f"{len(ids)} animals ({', '.join(ids[:5])}{'…' if len(ids) > 5 else ''})" if EN else f"{len(ids)} grla ({', '.join(ids[:5])}{'…' if len(ids) > 5 else ''})")
        if not messagebox.askyesno(
                ("Delete animal" if EN else "Obriši grlo"), (f"Delete {naziv}?\n\n"
                "The animal disappears from the list and all searches, but stays in the pedigree, "
                "so that the relationships of its offspring stay correct.\n\n"
                "You can restore it on the \"Deleted animals\" page." if EN else f"Obrisati {naziv}?\n\n"
                "Grlo nestaje iz liste i iz svih pretraga, ali ostaje zapamćeno u rodoslovu, "
                "da bi srodstvo njegovih potomaka bilo tačno.\n\n"
                "Možeš ga vratiti na strani „Obrisana grla“."), parent=parent or self.root):
            return False
        for i in ids:
            self.red_za(i)["status"] = "obrisano"
            self.ist.dodaj(i, AUTO, ("Animal deleted from the list (kept in the pedigree)" if EN else "Grlo obrisano iz liste (ostaje u rodoslovu)"), automatski=True)
        if self.karton_win and self.karton_win.winfo_exists() and getattr(self.karton_win, "grlo", None) in ids:
            self.karton_win.destroy()
        if self.ui.get("partner") in ids:
            self.ui.update(partner="", partner_upit="")
        self.promena((f"Deleted: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}" if EN else f"Obrisano: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}"))
        return True

    def vrati_grla(self, ids):
        for i in ids:
            r = self.red_za(i)
            if r:
                r["status"] = "aktivno"
                self.ist.dodaj(i, AUTO, ("Animal restored to the herd" if EN else "Grlo vraćeno u stado"), automatski=True)
        self.promena((f"Restored to herd: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}" if EN else f"Vraćeno u stado: {', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}"))

    def trajno_obrisi(self, ids):
        m = self.model
        pot = sorted({k for k, pr in m.P.items() for i in ids if i in pr and k not in ids}, key=sort_key)
        upoz = ((f"\n\nWarning: {', '.join(pot[:6])}{'…' if len(pot) > 6 else ''} has/have this animal as a parent. "
                "Their ancestors through this animal will be lost and the relationships will be wrong." if EN else f"\n\nPažnja: {', '.join(pot[:6])}{'…' if len(pot) > 6 else ''} ima(ju) ovo grlo kao roditelja. "
                "Njihovi preci preko ovog grla biće izgubljeni i srodstvo će biti netačno.")
                if pot else "")
        if not messagebox.askyesno(("Permanent deletion" if EN else "Trajno brisanje"), (f"Permanently delete {', '.join(ids[:5])}"
                                   f"{'…' if len(ids) > 5 else ''}? This cannot be undone.{upoz}" if EN else f"Trajno obrisati {', '.join(ids[:5])}"
                                   f"{'…' if len(ids) > 5 else ''}? Ovo se ne može poništiti.{upoz}"),
                                   icon="warning"):
            return
        self.tab.redovi = [r for r in self.tab.redovi if r["id"] not in ids]
        self.promena((f"Permanently deleted: {len(ids)} animals" if EN else f"Trajno obrisano: {len(ids)} grla"))

    def meni_grla(self, tv, ev):
        iid = tv.identify_row(ev.y)
        if not iid or iid not in self.model.A:
            return
        if iid not in tv.selection():
            tv.selection_set(iid)
        sel = [i for i in tv.selection() if i in self.model.A]
        mn = tk.Menu(self.root, tearoff=0, font=self.f(10), bg=SURF, fg=INK, activebackground=SURF2,
                     activeforeground=INK, bd=0)
        if len(sel) == 1:
            mn.add_command(label=("Open card" if EN else "Otvori karton"), command=lambda: self.karton(iid))
            mn.add_command(label=("Edit details" if EN else "Izmeni podatke"), command=lambda: self.forma(iid))
            mn.add_command(label=("Change ear tag" if EN else "Promeni ušnu markicu"), command=lambda: self.promena_markice(iid))
            mn.add_command(label=("Partner search" if EN else "Pretraga partnera"), command=lambda: self.idi_na_pretragu(iid))
            mn.add_command(label=("Pedigree (family tree)" if EN else "Poreklo (rodoslovno stablo)"), command=lambda: self.stablo(iid))
            mn.add_command(label=("Animal history (details and entry)" if EN else "Istorija grla (podaci i unos)"), command=lambda: self.istorija_prozor(iid))
            mn.add_command(label=("Add event…" if EN else "Dodaj događaj…"), command=lambda: self.dogadjaj_forma(iid))
            mn.add_command(label=("Add reminder…" if EN else "Dodaj podsetnik…"), command=lambda: self.podsetnik_forma(iid))
            mn.add_separator()
        mn.add_command(label=(f"Move to another herd{'' if len(sel) == 1 else f' ({len(sel)} animals)'}…" if EN else f"Premesti u drugo stado{'' if len(sel) == 1 else f' ({len(sel)} grla)'}…"),
                       command=lambda: self.promena_stada(sel))
        st_ = self.model.A[iid]["stado"]
        if st_:
            mn.add_command(label=(f"Rename herd \"{st_}\"…" if EN else f"Preimenuj stado „{st_}“…"), command=lambda: self.preimenuj_stado(st_))
        mn.add_separator()
        mn.add_command(label=(f"Delete{'' if len(sel) == 1 else f' ({len(sel)} animals)'}" if EN else f"Obriši{'' if len(sel) == 1 else f' ({len(sel)} grla)'}"),
                       foreground=BAD, command=lambda: self.obrisi_grla(sel))
        try:
            mn.tk_popup(ev.x_root, ev.y_root)
        finally:
            mn.grab_release()

    def s_obrisana(self):
        body = self.strana_okvir(scroll=False)
        m = self.model
        obr = m.obrisana()
        self.zaglavlje(body, ("Deleted animals" if EN else "Obrisana grla"),
                       ("These animals are not shown in the list or searches, but stay in the pedigree so that the relationships "
                       "of their offspring stay correct." if EN else "Ova grla se ne vide u listi ni u pretragama, ali ostaju u rodoslovu da bi srodstvo "
                       "njihovih potomaka bilo tačno."),
                       [(("← Back to animals" if EN else "← Nazad na grla"), lambda: self.prikazi("grla"), "Secondary")])
        if not obr:
            self.napomena(body, ("There are no deleted animals." if EN else "Nema obrisanih grla."), ok=True)
            return
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        wrap, tv = self.tabela(body, [("id", ("Animal" if EN else "Grlo"), 105), ("markica", ("Ear tag" if EN else "Markica"), 125), ("pol", ("Sex" if EN else "Pol"), 70),
                                      ("rasa", ("Breed" if EN else "Rasa"), 130), ("stado", ("Herd" if EN else "Stado"), 90),
                                      ("pot", ("Offspring in pedigree" if EN else "Potomaka u rodoslovu"), 150, "e")], visina=14)
        for i, a in enumerate(obr):
            n = sum(1 for pr in m.P.values() if a["id"] in pr)
            tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag_siv,
                      values=(a["markica"] or "–", m.pol_naziv(a["id"]), a["rasa"] or "–", a["stado"] or "–", n),
                      tags=["odd"] if i % 2 else [])
        izbor = lambda: [i for i in tv.selection() if i in m.A]
        def vrati():
            s_ = izbor()
            if s_:
                self.vrati_grla(s_)
            else:
                self.toast(("First select an animal in the table." if EN else "Prvo označi grlo u tabeli."))
        def trajno():
            s_ = izbor()
            if s_:
                self.trajno_obrisi(s_)
            else:
                self.toast(("First select an animal in the table." if EN else "Prvo označi grlo u tabeli."))
        self.btn(tb, ("Restore to herd" if EN else "Vrati u stado"), vrati, "Primary").pack(side="left")
        self.btn(tb, ("Delete permanently" if EN else "Trajno obriši"), trajno, "Danger").pack(side="left", padx=8)
        self.lbl(tb, ("Select an animal (or several with Ctrl), then choose an action." if EN else "Označi grlo (ili više uz Ctrl) pa izaberi radnju."), 9, fg=INK2).pack(side="left", padx=8)
        wrap.pack(fill="both", expand=True)
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))

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

    def napomena(self, parent, tekst, ok=False, wraplength=820):
        f = tk.Frame(parent, bg=OK_BG if ok else WARN_BG)
        f.pack(fill="x", pady=(0, 14))
        self.lbl(f, tekst, 10, fg=OK if ok else WARN, justify="left", wraplength=wraplength).pack(
            anchor="w", padx=14, pady=10)

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
        min_r = 0.25 if len(akt) > 300 else 1e-9
        po_v = {}
        for x in akt:
            po_v.setdefault(x["vrsta"], []).append(x["id"])
        parovi = []
        for ids in po_v.values():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    r = m.r(ids[i], ids[j])
                    if r >= min_r:
                        parovi.append((r, ids[i], ids[j]))
        parovi.sort(reverse=True)
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

    # ---------- karton
    def karton(self, x):
        m = self.model
        if x not in m.A:
            return
        if self.karton_win and self.karton_win.winfo_exists():
            win = self.karton_win
            for w in win.winfo_children():
                w.destroy()
        else:
            win = tk.Toplevel(self.root, bg=SURF)
            win.geometry(f"480x{min(760, self.root.winfo_height())}+"
                         f"{self.root.winfo_rootx() + max(0, self.root.winfo_width() - 500)}+{self.root.winfo_rooty() + 20}")
            win.transient(self.root)
            win.bind("<Escape>", lambda e: win.destroy())
            self.karton_win = win
        win.grlo = x
        a = m.A[x]
        win.title((f"Animal card {x}" if EN else f"Karton grla {x}"))
        pt = tk.Frame(win, bg=SURF)
        pt.pack(fill="x", padx=24, pady=(12, 0))
        self.btn(pt, T("🖨 Rodoslovni list / PDF", "🖨 Pedigree certificate / PDF"), lambda: self.stampaj_rodoslov(x)).pack(side="right")
        sf = ScrollFrame(win, bg=SURF)
        sf.pack(fill="both", expand=True)
        b = tk.Frame(sf.inner, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=22)
        top = tk.Frame(b, bg=SURF)
        top.pack(fill="x")
        self.cip(top, x, big=True, siv=a["osnivac"]).pack(side="left")
        t = tk.Frame(top, bg=SURF)
        t.pack(side="left", padx=14)
        self.lbl(t, m.pol_naziv(x) + (", " + a["rasa"] if a["rasa"] else ""), 12, "bold").pack(anchor="w")
        if a["rasa"].startswith(("hybrid" if EN else "hibrid")):
            o_h, m_h = m.P.get(x, (None, None))
            ro_ = m.A[o_h]["rasa"] if o_h in m.A else ""
            rm_ = m.A[m_h]["rasa"] if m_h in m.A else ""
            if ro_ or rm_:
                self.lbl(t, (f"sire {ro_ or '?'} × dam {rm_ or '?'}" if EN else f"otac {ro_ or '?'} × majka {rm_ or '?'}"), 9, fg=INK2).pack(anchor="w")
        self.lbl(t, ("known only as a parent" if EN else "poznat samo kao roditelj") if a["osnivac"] else ("deleted (kept in the pedigree)" if EN else "obrisano (čuva se u rodoslovu)")
                 if a.get("obrisano") else ("in herd" if EN else "u zapatu") if a["aktivno"] else ("not in herd" if EN else "nije u zapatu"),
                 9, fg=BAD if a.get("obrisano") else INK2).pack(anchor="w")

        def sekcija(naslov):
            self.lbl(b, naslov, 10, "bold").pack(anchor="w", pady=(18, 6))
            fr = tk.Frame(b, bg=SURF)
            fr.pack(anchor="w", fill="x")
            return fr

        if a["osnivac"]:
            self.lbl(b, ("This animal is entered only as a parent. Add it as an animal if you want to enter\n"
                        "its details and ancestors." if EN else "Ovo grlo je upisano samo kao roditelj. Dodaj ga kao grlo ako želiš da upišeš\n"
                        "njegove podatke i pretke."), 10, fg=INK2, justify="left").pack(anchor="w", pady=(14, 8))
            self.btn(b, (f"Add {x} as an animal" if EN else f"Dodaj {x} kao grlo"), lambda: (win.destroy(), self.forma(preset=dict(
                id=x, pol=a["pol"], vrsta=a["vrsta"]))), "Primary").pack(anchor="w")
        else:
            kv = tk.Frame(b, bg=SURF)
            kv.pack(fill="x", pady=(16, 0))
            st = starost_meseci(a["datum"])
            mr = tk.Frame(kv, bg=SURF)
            mr.grid(row=0, column=1, sticky="w", padx=16, pady=3)
            self.lbl(mr, a["markica"] or "–", 10, "bold").pack(side="left")
            lnk = self.lbl(mr, ("change" if EN else "promeni"), 9, "bold", fg=BRAND, cursor="hand2")
            lnk.pack(side="left", padx=10)
            lnk.bind("<Button-1>", lambda e: self.promena_markice(x, parent=win))
            por = a["poreklo"] + (f" – {a['poreklo_od']}" if a["poreklo_od"] else "") if a["poreklo"] else a["poreklo_od"]
            self.lbl(kv, ("Origin" if EN else "Poreklo"), 10, fg=INK2).grid(row=6, column=0, sticky="nw", pady=3)
            self.lbl(kv, por or ("not entered" if EN else "nije upisano"), 10, "bold" if por else "normal", fg=INK if por else INK2,
                     wraplength=260, justify="left").grid(row=6, column=1, sticky="w", padx=16, pady=3)
            if a["stare"]:
                self.lbl(kv, ("Previous ear tags" if EN else "Ranije markice"), 10, fg=INK2).grid(row=5, column=0, sticky="nw", pady=3)
                self.lbl(kv, ", ".join(a["stare"]), 10, fg=INK2, wraplength=260, justify="left").grid(
                    row=5, column=1, sticky="w", padx=16, pady=3)
            for i, (k, v) in enumerate(((("Ear tag" if EN else "Ušna markica"), None), (("Species" if EN else "Vrsta"), a["vrsta"]),
                                        (("Born" if EN else "Rođeno"), (fmt_datum(a["datum"]) + (f"  ({fmt_starost(st)})" if st is not None else ""))
                                         if a["datum"] else "–"),
                                        (("Herd" if EN else "Stado"), a["stado"] or "–"))):
                self.lbl(kv, k, 10, fg=INK2).grid(row=i, column=0, sticky="w", pady=3)
                if v is not None and k != ("Herd" if EN else "Stado"):
                    self.lbl(kv, v, 10, "bold").grid(row=i, column=1, sticky="w", padx=16, pady=3)
            sr = tk.Frame(kv, bg=SURF)
            sr.grid(row=3, column=1, sticky="w", padx=16, pady=3)
            self.lbl(sr, a["stado"] or "–", 10, "bold").pack(side="left")
            lns = self.lbl(sr, ("change" if EN else "promeni"), 9, "bold", fg=BRAND, cursor="hand2")
            lns.pack(side="left", padx=10)
            lns.bind("<Button-1>", lambda e: self.promena_stada([x], parent=win))
            f = m.inbr(x)
            self.lbl(kv, ("Inbreeding" if EN else "Inbriding"), 10, fg=INK2).grid(row=4, column=0, sticky="w", pady=3)
            self.badge(kv, pct(f), BAD if f > self.prag else WARN if f > self.prag / 2 else OK if f else INK2).grid(
                row=4, column=1, sticky="w", padx=16, pady=3)
            kar = self.opis_karence(x)
            if kar:
                self.lbl(kv, ("Withdrawal" if EN else "Karenca"), 10, fg=BAD).grid(row=7, column=0, sticky="nw", pady=3)
                self.lbl(kv, kar, 10, "bold", fg=BAD, wraplength=260, justify="left").grid(
                    row=7, column=1, sticky="w", padx=16, pady=3)

        o, mj = m.P[x]
        fr = sekcija(("Parents" if EN else "Roditelji"))
        for p, t in ((o, ("sire unknown" if EN else "otac nepoznat")), (mj, ("dam unknown" if EN else "majka nepoznata"))):
            if p:
                self.cip(fr, p, lambda p=p: self.karton(p), siv=m.A[p]["osnivac"]).pack(side="left", padx=(0, 6))
            else:
                self.lbl(fr, f" {t} ", 9, fg=INK2, bg=SURF2).pack(side="left", padx=(0, 6))
        dede = [r for p in (o, mj) if p for r in m.P.get(p, ()) if r]
        if dede:
            fr = sekcija(("Grandparents" if EN else "Dede i babe"))
            for d in dede:
                self.cip(fr, d, lambda d=d: self.karton(d), siv=m.A[d]["osnivac"]).pack(side="left", padx=(0, 6))
        if EN:
            if a["pol"] == "z" and not a["osnivac"]:
                pl = self.plodnost(x)
                if pl["porodjaja"] or pl["parenja"]:
                    fr = sekcija("Fertility")
                    tab_ = tk.Frame(fr, bg=SURF2)
                    tab_.pack(fill="x")
                    for i, (k_, v_) in enumerate((
                            ("Births", pl["porodjaja"]),
                            ("Born alive", f"{pl['zivih']}" + (f"  (average {pl['prosek']:.1f} per birth)"
                                                                  if pl["porodjaja"] else "")),
                            ("Stillborn", pl["mrtvih"] or "–"),
                            ("Interval between births", f"{round(pl['razmak'])} days" if pl["razmak"] else "–"),
                            ("Matings / failed", f"{pl['parenja']} / {pl['neuspela']}"),
                            ("First birth at", f"{pl['prvi_mes']} months" if pl["prvi_mes"] is not None else "–"))):
                        self.lbl(tab_, k_, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 10), pady=2)
                        self.lbl(tab_, str(v_), 9, "bold", bg=SURF2).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        else:
            if a["pol"] == "z" and not a["osnivac"]:
                pl = self.plodnost(x)
                if pl["porodjaja"] or pl["parenja"]:
                    fr = sekcija("Plodnost")
                    tab_ = tk.Frame(fr, bg=SURF2)
                    tab_.pack(fill="x")
                    for i, (k_, v_) in enumerate((
                            ("Porođaja", pl["porodjaja"]),
                            ("Rođeno živih", f"{pl['zivih']}" + (f"  (prosek {pl['prosek']:.1f} po porođaju)".replace(".", ",")
                                                                  if pl["porodjaja"] else "")),
                            ("Mrtvorođenih", pl["mrtvih"] or "–"),
                            ("Razmak između porođaja", f"{round(pl['razmak'])} dana" if pl["razmak"] else "–"),
                            ("Parenja / neuspela", f"{pl['parenja']} / {pl['neuspela']}"),
                            ("Prvi porođaj sa", f"{pl['prvi_mes']} meseci" if pl["prvi_mes"] is not None else "–"))):
                        self.lbl(tab_, k_, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 10), pady=2)
                        self.lbl(tab_, str(v_), 9, "bold", bg=SURF2).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        udeli = [(d, p) for d, p in m.udeli_predaka(x) if p not in (o, mj)][:6]
        if udeli:
            fr = sekcija(("Share of genes from ancestors" if EN else "Udeo gena od predaka"))
            for d, p in udeli:
                r = tk.Frame(fr, bg=SURF)
                r.pack(fill="x", pady=2)
                self.cip(r, p, lambda p=p: self.karton(p), siv=m.A[p]["osnivac"]).pack(side="left")
                self.lbl(r, pct(d), 10, "bold", width=7, anchor="e").pack(side="right")
                ttk.Progressbar(r, style="Green.Horizontal.TProgressbar", maximum=100, value=d * 100).pack(
                    side="left", fill="x", expand=True, padx=10)
        if m.putanje(x):
            lk = self.lbl(b, (f"Show all ancestors ({len(m.putanje(x))})  ›" if EN else f"Prikaži sve pretke ({len(m.putanje(x))})  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(anchor="w", pady=(6, 0))
            lk.bind("<Button-1>", lambda e: self.stablo(x, 4, "svi"))
        n_boc = len(self.bocni_srodnici(x))
        if n_boc:
            lb_ = self.lbl(b, (f"Collateral relatives – siblings, cousins ({n_boc})  ›" if EN else f"Bočni srodnici – braća, sestre, rođaci ({n_boc})  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            lb_.pack(anchor="w", pady=(4, 0))
            lb_.bind("<Button-1>", lambda e: self.stablo(x, 4, "bocni"))
        pot = sorted((k for k, pr in m.P.items() if x in pr), key=sort_key)
        fr = sekcija((f"Offspring ({len(pot)})" if EN else f"Potomci ({len(pot)})"))
        if not pot:
            self.lbl(fr, ("none recorded" if EN else "nema upisanih"), 10, fg=INK2).pack(side="left")
        red = None
        for i, p in enumerate(pot[:40]):
            if i % 6 == 0:
                red = tk.Frame(fr, bg=SURF)
                red.pack(anchor="w", pady=2)
            self.cip(red, p, lambda p=p: self.karton(p)).pack(side="left", padx=(0, 6))

        n_svih = sum(len(v) for v in self.potomci_po_kolenima(x).values())
        if n_svih > len(pot):
            lpo = self.lbl(b, (f"All descendants – children, grandchildren ({n_svih})  ›" if EN else f"Svi potomci – deca, unuci, praunuci ({n_svih})  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            lpo.pack(anchor="w", pady=(4, 0))
            lpo.bind("<Button-1>", lambda e: self.stablo(x, 4, "potomci"))
        if a["aktivno"] and a["pol"] and not a["osnivac"]:
            kand = sorted((m.kinship(x, k["id"]), k["id"]) for k in m.grla(True)
                          if k["id"] != x and k["vrsta"] == a["vrsta"] and k["pol"] != a["pol"])[:5]
            if kand:
                fr = sekcija(("Best partners" if EN else "Najbolji partneri"))
                for f, k in kand:
                    r = tk.Frame(fr, bg=SURF)
                    r.pack(fill="x", pady=3)
                    self.cip(r, k, lambda k=k: self.karton(k)).pack(side="left")
                    self.lbl(r, (f"genes {pct(m.r(x, k))}" if EN else f"geni {pct(m.r(x, k))}"), 9, fg=INK2).pack(side="left", padx=8)
                    t, boja = procena(f, self.prag)
                    self.badge(r, t, boja).pack(side="right")
                    self.lbl(r, pct(f), 10, "bold").pack(side="right", padx=10)

        if not a["osnivac"]:
            obv = [o for o in self.obavestenja(x) if o["grlo"] == x or o.get("podsetnik")]
            fr = sekcija((f"Notifications ({len(obv)})" if EN else f"Obaveštenja ({len(obv)})"))
            if not obv:
                self.lbl(fr, ("none" if EN else "nema"), 10, fg=INK2).pack(anchor="w")
            for o in obv[:5]:
                self.red_obavestenja(fr, o, kompakt=True)
            lp = self.lbl(b, ("+ Add reminder" if EN else "+ Dodaj podsetnik"), 9, "bold", fg=BRAND, cursor="hand2")
            lp.pack(anchor="w", pady=(4, 0))
            lp.bind("<Button-1>", lambda e: self.podsetnik_forma(x, parent=win))
            zap = self.ist.za(x)
            fr = sekcija((f"History ({len(zap)})" if EN else f"Istorija ({len(zap)})"))
            sz = tk.Frame(fr, bg=SURF)
            sz.pack(fill="x", pady=(0, 6))
            for i, (naziv, vrste) in enumerate(GRUPE):
                zz = [z for z in zap if z["dogadjaj"] in vrste]
                k = tk.Frame(sz, bg=SURF2, cursor="hand2")
                k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
                sz.columnconfigure(i, weight=1, uniform="g")
                a1 = tk.Label(k, text=f"{naziv}: {len(zz)}", font=self.f(9, "bold"), bg=SURF2, fg=INK)
                a1.pack(anchor="w", padx=8, pady=(5, 0))
                a2 = tk.Label(k, text=zz[0]["datum"] if zz else "–", font=self.f(8), bg=SURF2, fg=INK2)
                a2.pack(anchor="w", padx=8, pady=(0, 5))
                for w in (k, a1, a2):
                    w.bind("<Button-1>", lambda e, n=naziv: (self.ui.setdefault("ist_" + x, {"vrsta": ("All events" if EN else "Svi događaji"),
                           "auto": True, "q": ""}).update(grupa=n, vrsta=("All events" if EN else "Svi događaji")), self.istorija_prozor(x)))
            if not zap:
                self.lbl(fr, ("no records" if EN else "nema zapisa"), 10, fg=INK2).pack(anchor="w")
            for z in zap[:5]:
                r = tk.Frame(fr, bg=SURF)
                r.pack(fill="x", pady=2)
                self.lbl(r, z["datum"], 9, "bold", fg=INK2, width=11, anchor="w").pack(side="left", anchor="n")
                tekst = (z["dogadjaj"] if z["dogadjaj"] != AUTO else "") + \
                        (" – " if z["dogadjaj"] != AUTO and (z["opis"] or z["partner"] or z["vrednost"]) else "") + \
                        ", ".join(v for v in (z["opis"], (f"partner {z['partner']}" if z["partner"] else ""),
                                              z["vrednost"]) if v)
                self.lbl(r, tekst, 9, fg=INK2 if z["automatski"] else INK, wraplength=330,
                         justify="left").pack(side="left", anchor="w")
            lr = tk.Frame(b, bg=SURF)
            lr.pack(anchor="w", pady=(6, 0))
            l1 = self.lbl(lr, ("+ Add event" if EN else "+ Dodaj događaj"), 9, "bold", fg=BRAND, cursor="hand2")
            l1.pack(side="left")
            l1.bind("<Button-1>", lambda e: self.dogadjaj_forma(x, parent=win))
            l2 = self.lbl(lr, ("Full history  ›" if EN else "Cela istorija  ›"), 9, "bold", fg=BRAND, cursor="hand2")
            l2.pack(side="left", padx=16)
            l2.bind("<Button-1>", lambda e: self.istorija_prozor(x))

        act1 = tk.Frame(b, bg=SURF)
        act1.pack(anchor="w", pady=(24, 0))
        if not a["osnivac"]:
            self.btn(act1, ("Edit details" if EN else "Izmeni podatke"), lambda: (win.destroy(), self.forma(x)), "Primary").pack(side="left", padx=(0, 8))
        self.btn(act1, ("Pedigree – tree" if EN else "Poreklo – stablo"), lambda: self.stablo(x)).pack(side="left")
        if not a["osnivac"]:
            act = tk.Frame(b, bg=SURF)
            act.pack(anchor="w", pady=(8, 0))
            dete = dict(vrsta=a["vrsta"], rasa=a["rasa"], stado=a["stado"])
            dete["otac" if a["pol"] == "m" else "majka"] = x
            self.btn(act, ("Add offspring" if EN else "Upiši potomka"), lambda: (win.destroy(), self.forma(preset=dete))).pack(side="left", padx=(0, 8))
            if a.get("obrisano"):
                self.btn(act, ("Restore to herd" if EN else "Vrati u stado"), lambda: self.vrati_grla([x])).pack(side="left")
            else:
                if a["pol"]:
                    self.btn(act, ("All partners" if EN else "Svi partneri"), lambda: (win.destroy(), self.idi_na_pretragu(x))).pack(side="left")
                self.btn(act, ("Delete" if EN else "Obriši"), lambda: self.obrisi_grla([x], parent=win), "Danger").pack(side="left", padx=8)
        win.lift()

    # ---------- poreklo / rodoslovno stablo
    # ---------- istorija
    def opis_zapisa(self, z):
        dod = []
        if z["partner"]:
            dod.append(f"partner {z['partner']}")
        if z["vrednost"]:
            dod.append(z["vrednost"])
        kar = [(f"{n} {z.get(k)} days" if EN else f"{n} {z.get(k)} d.") for k, n in (("karenca_meso", ("meat" if EN else "meso")), ("karenca_mleko", ("milk" if EN else "mleko"))) if z.get(k)]
        if kar:
            dod.append(("withdrawal: " if EN else "karenca: ") + ", ".join(kar))
        return " · ".join(v for v in [z["opis"]] + dod if v)

    def tabela_istorije(self, parent, zapisi, sa_grlom, visina=14):
        kol = [("datum", ("Date" if EN else "Datum"), 100)] + ([("grlo", ("Animal" if EN else "Grlo"), 90)] if sa_grlom else []) + \
              [("dog", ("Event" if EN else "Događaj"), 160), ("opis", ("Description" if EN else "Opis"), 250), ("ishod", ("Young" if EN else "Mladi"), 185)]
        wrap, tv = self.tabela(parent, kol, visina=visina, tree=False)
        tv.tag_configure("auto", foreground=INK2)
        tv.tag_configure("ceka", foreground=BRAND)
        for i, z in enumerate(zapisi):
            vals = [z["datum"]] + ([z["grlo"]] if sa_grlom else []) + \
                   [z["dogadjaj"] if z["dogadjaj"] != AUTO else ("· record" if EN else "· evidencija"), self.opis_zapisa(z),
                    self.opis_ishoda(z)]
            tv.insert("", "end", iid=str(self.ist.zapisi.index(z)), values=vals,
                      tags=(["odd"] if i % 2 else []) + (["auto"] if z["automatski"] else []) +
                           (["ceka"] if self.ceka_porodjaj(z) else []))
        return wrap, tv

    # ---------- parenje -> porođaj -> podmladak
    def roditelji_parenja(self, z):
        """(majka, otac) iz zapisa o parenju, bez obzira kod koga je parenje upisano."""
        m = self.model
        g = z["grlo"]
        p = (m.nadji(z.get("partner")) or z.get("partner") or "").strip() or None
        if g in m.A and m.A[g]["pol"] == "m":
            return p, g
        return g, p

    def profil_gravidnosti(self, vrsta, rasa=""):
        """(ključ, naziv, najmanje, najviše, prosek) dana gravidnosti – po rasi majke, pa po vrsti."""
        v = vrsta_norm(vrsta or "")
        r = norm_rasa(rasa or "")
        kljuc = None
        for k, (naziv, vr, prepoznaj, *_d) in GRAVIDNOST_PROFILI.items():
            if prepoznaj and vr == v and any(p in r for p in prepoznaj):
                kljuc = k
                break
        if kljuc is None:
            kljuc = next((k for k, (naziv, vr, prepoznaj, *_d) in GRAVIDNOST_PROFILI.items()
                          if vr == v and not prepoznaj), None)
        if kljuc is None:
            return None, v, None, None, None
        naziv, _, _, mn, mx, pr = GRAVIDNOST_PROFILI[kljuc]
        pod = self.pod.get("gravidnost2", {}).get(kljuc)
        if pod:
            mn, mx, pr = (int(x) for x in pod)
        return kljuc, naziv, mn, mx, pr

    def gravidnost(self, vrsta, rasa=""):
        """(prosek, koliko dana ranije je dozvoljen upis) – zbog starijih delova programa."""
        _, _, mn, mx, pr = self.profil_gravidnosti(vrsta, rasa)
        return (pr, pr - mn) if pr else (None, 0)

    def vrsta_parenja(self, z):
        majka, _ = self.roditelji_parenja(z)
        g = majka if majka in self.model.A else z["grlo"]
        return self.model.A[g]["vrsta"] if g in self.model.A else ""

    def rasa_parenja(self, z):
        majka, _ = self.roditelji_parenja(z)
        return self.model.A[majka]["rasa"] if majka in self.model.A else ""

    def granice_porodjaja(self, z):
        """(najranije, očekivano, najkasnije) datum porođaja za parenje, ili (None, None, None)."""
        d = parsiraj_datum(z["datum"])
        _, _, mn, mx, pr = self.profil_gravidnosti(self.vrsta_parenja(z), self.rasa_parenja(z))
        if not (d and pr):
            return None, None, None
        return d + timedelta(days=mn), d + timedelta(days=pr), d + timedelta(days=mx)

    def ocekivani_porodjaj(self, z):
        return self.granice_porodjaja(z)[1]

    def upis_moguc_od(self, z):
        """Najraniji normalan dan porođaja – od tada je upis mladih otvoren."""
        return self.granice_porodjaja(z)[0]

    def najkasniji_porodjaj(self, z):
        return self.granice_porodjaja(z)[2]

    def podesavanje_gravidnosti(self, parent=None):
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Gestation length" if EN else "Nosivost (trajanje gravidnosti)"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Gestation length" if EN else "Nosivost – trajanje gravidnosti"), 16, "bold").grid(row=0, column=0, columnspan=5, sticky="w")
        self.lbl(b, ("Entering young opens from the minimum number of days. After the maximum number of days the program reports that the "
                    "due date has passed. The average is used for the expected date." if EN else "Upis mladih se otvara od najmanjeg broja dana. Posle najvećeg broja dana program javlja da je "
                    "termin prošao. Prosek se koristi za očekivani datum."), 9, fg=INK2, wraplength=520,
                 justify="left").grid(row=1, column=0, columnspan=5, sticky="w", pady=(4, 12))
        for c, t in enumerate((("Species / breed" if EN else "Vrsta / rasa"), ("Minimum" if EN else "Najmanje"), ("Maximum" if EN else "Najviše"), ("Average" if EN else "Prosek"), "")):
            self.lbl(b, t, 9, "bold", fg=INK2).grid(row=2, column=c, sticky="w", padx=(0, 14), pady=(0, 4))
        polja = {}
        for i, (k, (naziv, vr, prep, mn0, mx0, pr0)) in enumerate(GRAVIDNOST_PROFILI.items(), 3):
            _, _, mn, mx, pr = self.profil_gravidnosti(vr, prep[0] if prep else "")
            vs = [tk.StringVar(value=str(x)) for x in (mn, mx, pr)]
            self.lbl(b, naziv, 10, "bold").grid(row=i, column=0, sticky="w", padx=(0, 14), pady=3)
            for c, v in enumerate(vs, 1):
                ttk.Entry(b, textvariable=v, width=7, font=self.f(10)).grid(row=i, column=c, sticky="w", padx=(0, 14))
            self.lbl(b, (f"default {mn0}–{mx0}, ~{pr0}" if EN else f"podraz. {mn0}–{mx0}, ~{pr0}"), 8, fg="#8A968D").grid(row=i, column=4, sticky="w")
            polja[k] = vs
        self.lbl(b, ("Gestation is always determined by the breed of the DAM: Romanov ewe × any ram = 138–143 days; "
                    "other ewe × Romanov ram = as a common sheep." if EN else "Nosivost se uvek određuje po rasi MAJKE: romanovska ovca × bilo koji ovan = 138–143 dana; "
                    "druga ovca × romanovski ovan = kao obična ovca."), 8, fg="#8A968D").grid(
            row=19, column=0, columnspan=5, sticky="w", pady=(6, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=520, justify="left")
        err.grid(row=20, column=0, columnspan=5, sticky="w", pady=(8, 0))

        def sacuvaj(ev=None):
            novo = {}
            for k, vs in polja.items():
                naziv = GRAVIDNOST_PROFILI[k][0]
                try:
                    mn, mx, pr = (int(v.get()) for v in vs)
                except ValueError:
                    err.config(text=(f"{naziv}: enter whole numbers of days." if EN else f"{naziv}: upiši cele brojeve dana."))
                    return
                if not (30 <= mn <= pr <= mx <= 500):
                    err.config(text=(f"{naziv}: must be minimum ≤ average ≤ maximum (30–500 days)." if EN else f"{naziv}: mora biti najmanje ≤ prosek ≤ najviše (30–500 dana)."))
                    return
                novo[k] = [mn, mx, pr]
            self.pod["gravidnost2"] = novo
            self.pod.pop("gravidnost", None)
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            self.toast(("Gestation length saved." if EN else "Nosivost je sačuvana."))
            self.osvezi_istoriju()

        def vrati():
            for k, vs in polja.items():
                for v, x in zip(vs, GRAVIDNOST_PROFILI[k][3:]):
                    v.set(str(x))

        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=21, column=0, columnspan=5, sticky="ew", pady=(16, 0))
        self.btn(fb, ("Defaults" if EN else "Podrazumevano"), vrati).pack(side="left")
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, parent)

    def ceka_porodjaj(self, z):
        return z["dogadjaj"] == PARENJE and not z.get("ishod") and not z["automatski"]

    def opis_ishoda(self, z):
        if z["dogadjaj"] != PARENJE or z["automatski"]:
            return ""
        ish = z.get("ishod", "")
        if ish.startswith("rodjeno:"):
            return ("☑ born: " if EN else "☑ rođeno: ") + ish[8:].replace(",", ", ")
        lg = self.leglo(z)
        if lg:
            uk, dd, vec = lg
            return (f"🏷 {uk} born {dd} – waiting for ear tag" if EN else f"🏷 {uk} rođeno {dd} – čeka minđušu") + (f" ({len(vec)}/{uk})" if vec else "")
        if ish == "uklonjeno":
            return ("✕ young not entered in the list" if EN else "✕ mladi nisu upisani u listu")
        if ish == "neuspelo":
            return ("✕ failed" if EN else "✕ nije uspelo")
        if ish == "ponovljeno":
            return ("– repeated mating" if EN else "– ponovljeno parenje")
        oc = self.ocekivani_porodjaj(z)
        od = self.upis_moguc_od(z)
        if od and date.today() < od:
            return (f"⏳ pregnant until {oc.strftime('%d/%m/%Y')}" if EN else f"⏳ gravidna do {oc.strftime('%d.%m.%Y')}")
        return "☐ " + ((f"entry open (due {oc.strftime('%d/%m/%Y')})" if EN else f"upis otvoren (termin {oc.strftime('%d.%m.%Y')})") if oc else ("waiting for young" if EN else "čeka mlade"))

    def cekaju_porodjaj(self, x=None):
        """Parenja bez upisanih mladih – za svaku ženku samo poslednje parenje."""
        posl = {}
        for z in self.ist.zapisi:
            if z["dogadjaj"] != PARENJE or z["automatski"]:
                continue
            majka, _ = self.roditelji_parenja(z)
            if x is not None and x not in (z["grlo"], majka, self.model.nadji(z.get("partner"))):
                continue
            kljuc = majka or z["grlo"]
            d = parsiraj_datum(z["datum"]) or date.min
            if kljuc not in posl or d >= (parsiraj_datum(posl[kljuc]["datum"]) or date.min):
                posl[kljuc] = z
        lista = [z for z in posl.values() if self.ceka_porodjaj(z)]
        return sorted(lista, key=lambda z: self.ocekivani_porodjaj(z) or date.max)

    def zatvori_stara_parenja(self, nz):
        """Novo parenje iste ženke: ranija parenja bez mladih označi kao ponovljena."""
        if nz.get("dogadjaj") != PARENJE:
            return
        majka, _ = self.roditelji_parenja(nz)
        d = parsiraj_datum(nz["datum"]) or date.min
        for z in self.ist.zapisi:
            if z is not nz and self.ceka_porodjaj(z) and self.roditelji_parenja(z)[0] == majka \
                    and (parsiraj_datum(z["datum"]) or date.min) <= d:
                z["ishod"] = "ponovljeno"

    def oznaci_neuspelo(self, z):
        if messagebox.askyesno(("Mating failed" if EN else "Parenje nije uspelo"),
                               (f"Mark the mating of {z['datum']} ({z['grlo']}) as failed?\n"
                               "It will no longer be shown among expected births." if EN else f"Označiti parenje od {z['datum']} ({z['grlo']}) kao neuspelo?\n"
                               "Neće se više prikazivati među očekivanim porođajima.")):
            z["ishod"] = "neuspelo"
            self.promena(("Mating marked as failed." if EN else "Parenje označeno kao neuspelo."))
            self.osvezi_istoriju()

    def osvezi_istoriju(self):
        self.osvezi_nav_brojac()
        if getattr(self, "ist_win", None) and self.ist_win.winfo_exists() and getattr(self.ist_win, "grlo", None):
            self.istorija_prozor(self.ist_win.grlo)
        if self.strana == "istorija":
            self.prikazi("istorija")

    # ---------- leglo: rođenje se beleži odmah (broj mladih), a u listu grla se upisuju kasnije (minđuša)
    @staticmethod
    def leglo(z):
        """'leglo:N:dd.mm.gggg:id1,id2' -> (N, datum, [upisani]) ili None."""
        ish = z.get("ishod", "") or ""
        if not ish.startswith("leglo:"):
            return None
        delovi = (ish.split(":", 3) + ["", "", "", ""])[:4]
        try:
            n = int(delovi[1])
        except ValueError:
            n = 0
        return n, delovi[2], [i for i in delovi[3].split(",") if i]

    def cekaju_mindjusu(self, x=None):
        rez = []
        for z in self.ist.zapisi:
            if z["dogadjaj"] != PARENJE or not self.leglo(z):
                continue
            majka, otac = self.roditelji_parenja(z)
            if x is not None and x not in (z["grlo"], majka, otac):
                continue
            rez.append(z)
        return sorted(rez, key=lambda z: parsiraj_datum(self.leglo(z)[1]) or date.min)

    def upis_podmlatka(self, z, parent=None, prevremeni=False):
        """Štikliran 'Dobijeni mladi': ako mladi već čekaju minđušu – upis u listu, inače beleženje rođenja."""
        m = self.model
        if z.get("ishod", "").startswith("rodjeno:"):
            ids = [i for i in z["ishod"][8:].split(",") if i]
            messagebox.showinfo(("Young stock" if EN else "Podmladak"), ("Young have already been entered for this mating: " if EN else "Za ovo parenje mladi su već upisani: ") + ", ".join(ids),
                                parent=parent or self.root)
            if ids and ids[0] in m.A:
                self.karton(ids[0])
            return
        if self.leglo(z):
            self.upis_u_listu(z, parent)
            return
        od = self.upis_moguc_od(z)
        oc = self.ocekivani_porodjaj(z)
        if od and date.today() < od and not prevremeni:
            dana_ost = (od - date.today()).days
            if not messagebox.askyesno(
                    ("Pregnancy still in progress" if EN else "Gravidnost još traje"),
                    (f"Mating: {z['datum']}\nExpected birth: {oc.strftime('%d/%m/%Y')}\n"
                    f"Young can be entered from {od.strftime('%d/%m/%Y')} (in {dana_ost} days).\n\n"
                    "Was this a PREMATURE birth and do you still want to enter the young?" if EN else f"Parenje: {z['datum']}\nOčekivani porođaj: {oc.strftime('%d.%m.%Y')}\n"
                    f"Upis mladih je moguć od {od.strftime('%d.%m.%Y')} (za {dana_ost} dana).\n\n"
                    "Da li je bio PREVREMENI porođaj i želiš ipak da upišeš mlade?"),
                    icon="warning", parent=parent or self.root):
                return
            prevremeni = True
        self.rodjenje_dijalog(z, parent, prevremeni)

    def podaci_legla(self, z):
        m = self.model
        majka, otac = self.roditelji_parenja(z)
        ref = majka if majka in m.A else z["grlo"]
        vrsta = m.A.get(ref, {}).get("vrsta") or ("cattle" if EN else "goveda")
        rm = (m.A[majka]["rasa"] if majka in m.A else "") or ""
        ro = (m.A[otac]["rasa"] if otac in m.A else "") or ""
        rasa = rasa_potomka(ro, rm)
        return majka, otac, vrsta, rasa, nazivi(vrsta)

    def zaglavlje_legla(self, b, z, majka, otac):
        m = self.model
        top = tk.Frame(b, bg=SURF)
        top.pack(anchor="w", pady=(12, 2))
        for naslov, g, nep in ((("Dam" if EN else "Majka"), majka, ("unknown" if EN else "nepoznata")), (("Sire" if EN else "Otac"), otac, ("unknown" if EN else "nepoznat"))):
            self.lbl(top, naslov, 9, "bold", fg=INK2).pack(side="left")
            if g:
                self.cip(top, g, siv=g not in m.A or m.A[g]["osnivac"]).pack(side="left", padx=(6, 16))
            else:
                self.lbl(top, nep, 10, fg=INK2).pack(side="left", padx=(6, 16))

    def postavi_prozor(self, win, parent):
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(10, (r.winfo_height() - win.winfo_height()) // 3)}")

    def rodjenje_dijalog(self, z, parent=None, prevremeni=False):
        """Korak 1: beleži se samo da su mladi rođeni, datum i broj – bez pola i oznaka."""
        m = self.model
        majka, otac, vrsta, rasa, n = self.podaci_legla(z)
        od, oc = self.upis_moguc_od(z), self.ocekivani_porodjaj(z)
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Birth of young" if EN else "Rođenje mladih"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, (f"Young born ({n[3]})" if EN else f"Rođeni mladi ({n[3]})"), 16, "bold").pack(anchor="w")
        self.zaglavlje_legla(b, z, majka, otac)
        self.lbl(b, (f"Mating {z['datum']}" if EN else f"Parenje {z['datum']}") + ((f"   ·   due {oc.strftime('%d/%m/%Y')}" if EN else f"   ·   termin {oc.strftime('%d.%m.%Y')}") if oc else ""),
                 9, fg=INK2).pack(anchor="w", pady=(4, 0))

        g = tk.Frame(b, bg=SURF2)
        g.pack(fill="x", pady=(14, 4))
        gi = tk.Frame(g, bg=SURF2)
        gi.pack(fill="x", padx=14, pady=10)
        dv = tk.StringVar(value=date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        bv = tk.StringVar(value="1")
        mv = tk.StringVar(value="0")
        for i, (nasl, var, w) in enumerate(((("Date of birth" if EN else "Datum rođenja"), dv, 14), ((f"Number alive ({n[3]})" if EN else f"Broj živih ({n[3]})"), bv, 6),
                                            (("Stillborn" if EN else "Mrtvorođenih"), mv, 6))):
            f = tk.Frame(gi, bg=SURF2)
            f.grid(row=0, column=i, sticky="w", padx=(0, 22))
            self.lbl(f, nasl, 9, "bold", fg=INK2, bg=SURF2).pack(anchor="w")
            (ttk.Entry(f, textvariable=var, width=w, font=self.f(11)) if i == 0 else
             ttk.Spinbox(f, from_=0 if i == 2 else 1, to=30, textvariable=var, width=w,
                         font=self.f(11))).pack(anchor="w", pady=(3, 0))
        prev_v = tk.BooleanVar(value=prevremeni)
        if od:
            ttk.Checkbutton(b, text=(f"Premature birth (before {od.strftime('%d/%m/%Y')})" if EN else f"Prevremeni porođaj (pre {od.strftime('%d.%m.%Y')})"), variable=prev_v,
                            style="Card.TCheckbutton").pack(anchor="w", pady=(6, 0))
        info = tk.Frame(b, bg=OK_BG)
        info.pack(fill="x", pady=(12, 0))
        self.lbl(info, ("You don't need to know the sex, tag or ear tag now. The young will wait on the list "
                       "\"Waiting for ear tag\", and you move them to the animal list when they get their ear tags." if EN else "Pol, oznaku i ušnu markicu ne moraš sada da znaš. Mladi će čekati na spisku "
                       "„Čekaju minđušu“, a u listu grla ih prebacuješ kad dobiju minđušu."),
                 9, fg=OK, bg=OK_BG, wraplength=480, justify="left").pack(anchor="w", padx=12, pady=8)
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=500, justify="left")
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(odmah=False):
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date of birth is not valid. Enter it as 15/03/2026." if EN else "Datum rođenja nije ispravan. Upiši ga kao 15.03.2026."))
                return
            if d > date.today():
                err.config(text=("The date of birth cannot be in the future." if EN else "Datum rođenja ne može biti u budućnosti."))
                return
            dp = parsiraj_datum(z["datum"])
            if dp and d <= dp:
                err.config(text=(f"The date of birth must be after the mating date ({z['datum']})." if EN else f"Datum rođenja mora biti posle datuma parenja ({z['datum']})."))
                return
            if od and d < od and not prev_v.get():
                err.config(text=(f"Pregnancy lasts until {oc.strftime('%d/%m/%Y')} – the earliest date of birth is "
                                f"{od.strftime('%d/%m/%Y')}. For an earlier birth tick \"Premature birth\"." if EN else f"Gravidnost traje do {oc.strftime('%d.%m.%Y')} – najraniji datum rođenja je "
                                f"{od.strftime('%d.%m.%Y')}. Za raniji porođaj štikliraj „Prevremeni porođaj“."))
                return
            try:
                zivih, mrtvih = int(bv.get()), int(mv.get() or 0)
            except ValueError:
                err.config(text=("The number of young must be a whole number." if EN else "Broj mladih mora biti ceo broj."))
                return
            if zivih < 0 or mrtvih < 0 or zivih + mrtvih == 0:
                err.config(text=("Enter how many young were born." if EN else "Upiši koliko je mladih rođeno."))
                return
            dstr = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
            opis = (f"Born alive: {zivih}" if EN else f"Rođeno živih: {zivih}") + ((f", stillborn: {mrtvih}" if EN else f", mrtvorođenih: {mrtvih}") if mrtvih else "")
            if od and d < od:
                opis += (f" – premature birth ({(oc - d).days} days before due date)" if EN else f" – prevremeni porođaj ({(oc - d).days} dana pre termina)")
            if majka:
                self.ist.dodaj(majka, ("Birth" if EN else "Porođaj"), opis, datum=dstr, partner=otac or "", vrednost=str(zivih))
            if otac and otac in m.A and not m.A[otac]["osnivac"]:
                self.ist.dodaj(otac, ("Offspring" if EN else "Potomak"), opis, datum=dstr, partner=majka or "", automatski=True)
            z["ishod"] = f"leglo:{zivih}:{dstr}:" if zivih else "rodjeno:"
            win.grab_release()
            win.destroy()
            self.promena((f"Birth recorded: {zivih} {n[3]} ({majka or '?'} × {otac or '?'})" if EN else f"Zabeleženo rođenje: {zivih} {n[3]} ({majka or '?'} × {otac or '?'})"))
            self.osvezi_istoriju()
            if odmah and zivih:
                self.upis_u_listu(z, parent)

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Record birth" if EN else "Zabeleži rođenje"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Enter in list now" if EN else "Odmah upiši u listu"), lambda: sacuvaj(True)).pack(side="right", padx=8)
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="left")
        win.bind("<Escape>", lambda ev: win.destroy())
        self.postavi_prozor(win, parent)

    def ukloni_iz_legla(self, z, parent=None):
        """Mladi koji neće biti upisani u listu (uginuli, prodati…) – uklanjaju se sa spiska čekanja."""
        lg = self.leglo(z)
        if not lg:
            return
        ukupno, dstr, vec = lg
        ostalo = ukupno - len(vec)
        majka, otac, vrsta, rasa, n = self.podaci_legla(z)
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Removing young from the list" if EN else "Uklanjanje mladih sa spiska"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Remove young that will not be entered" if EN else "Ukloni mlade koji neće biti upisani"), 15, "bold").pack(anchor="w")
        self.zaglavlje_legla(b, z, majka, otac)
        self.lbl(b, (f"Born {dstr}   ·   still waiting on the list: {ostalo} {n[3]}" if EN else f"Rođeno {dstr}   ·   na spisku čeka još {ostalo} {n[3]}")
                    + ((f" (entered: {', '.join(vec)})" if EN else f" (upisano: {', '.join(vec)})") if vec else ""), 9, fg=INK2).pack(anchor="w", pady=(4, 12))
        g = tk.Frame(b, bg=SURF)
        g.pack(fill="x")
        kv = tk.StringVar(value="1")
        rv = tk.StringVar(value=("Died" if EN else "Uginulo"))
        dv = tk.StringVar(value=date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        for i, (nasl, w) in enumerate(((("How many to remove" if EN else "Koliko ukloniti"), None), (("Reason" if EN else "Razlog"), None), (("Date" if EN else "Datum"), None))):
            f = tk.Frame(g, bg=SURF)
            f.grid(row=0, column=i, sticky="w", padx=(0, 16))
            self.lbl(f, nasl, 9, "bold", fg=INK2).pack(anchor="w")
            if i == 0:
                ttk.Spinbox(f, from_=1, to=ostalo, textvariable=kv, width=6, font=self.f(11)).pack(anchor="w", pady=(3, 0))
            elif i == 1:
                ttk.Combobox(f, textvariable=rv, values=[("Died" if EN else "Uginulo"), ("Sold" if EN else "Prodato"), ("Slaughtered" if EN else "Zaklano"), ("Given away" if EN else "Poklonjeno"), ("Other" if EN else "Drugo")],
                             width=14, font=self.f(10)).pack(anchor="w", pady=(3, 0))
            else:
                ttk.Entry(f, textvariable=dv, width=12, font=self.f(10)).pack(anchor="w", pady=(3, 0))
        sv_ = tk.BooleanVar(value=False)
        ttk.Checkbutton(b, text=(f"Remove all remaining ({ostalo})" if EN else f"Ukloni sve preostale ({ostalo})"), variable=sv_, style="Card.TCheckbutton",
                        command=lambda: kv.set(str(ostalo)) if sv_.get() else None).pack(anchor="w", pady=(10, 0))
        self.lbl(b, ("Note" if EN else "Napomena"), 9, "bold", fg=INK2).pack(anchor="w", pady=(10, 3))
        nv = tk.StringVar()
        ttk.Entry(b, textvariable=nv, width=50, font=self.f(10)).pack(anchor="w", fill="x")
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=460, justify="left")
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            try:
                k = int(kv.get())
            except ValueError:
                err.config(text=("The number must be a whole number." if EN else "Broj mora biti ceo broj."))
                return
            if not 1 <= k <= ostalo:
                err.config(text=(f"You can remove from 1 to {ostalo}." if EN else f"Možeš ukloniti od 1 do {ostalo}."))
                return
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            razlog = rv.get().strip() or ("Other" if EN else "Drugo")
            novo_uk = ukupno - k
            if novo_uk <= len(vec):
                z["ishod"] = ("rodjeno:" + ",".join(vec)) if vec else "uklonjeno"
            else:
                z["ishod"] = f"leglo:{novo_uk}:{dstr}:{','.join(vec)}"
            opis = (f"From the litter of {dstr} removed {k} {n[3] if k > 1 else n[2]} – {razlog.lower()}" if EN else f"Iz legla od {dstr} uklonjeno {k} {n[3] if k > 1 else n[2]} – {razlog.lower()}")
            if nv.get().strip():
                opis += f" ({nv.get().strip()})"
            if majka:
                self.ist.dodaj(majka, AUTO, opis, datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Removed from the list: {k} {n[3] if k > 1 else n[2]} ({razlog.lower()})" if EN else f"Uklonjeno sa spiska: {k} {n[3] if k > 1 else n[2]} ({razlog.lower()})"))
            self.osvezi_istoriju()

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Remove from list" if EN else "Ukloni sa spiska"), sacuvaj, "Danger").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        self.postavi_prozor(win, parent)

    def upis_u_listu(self, z, parent=None):
        """Korak 2: mladi dobili minđušu – upis oznake, markice i pola; datum i stado su automatski."""
        m = self.model
        lg = self.leglo(z)
        if not lg:
            return
        ukupno, dstr, vec = lg
        d = parsiraj_datum(dstr) or date.today()
        majka, otac, vrsta, rasa, n = self.podaci_legla(z)
        ostalo = max(1, ukupno - len(vec))

        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title((f"Entry in animal list – {n[3]}" if EN else f"Upis u listu grla – {n[3]}"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, (f"Entry in animal list ({n[3]})" if EN else f"Upis u listu grla ({n[3]})"), 16, "bold").pack(anchor="w")
        self.zaglavlje_legla(b, z, majka, otac)
        star = (date.today() - d).days
        self.lbl(b, (f"Litter: {ukupno} {n[3]}" if EN else f"Leglo: {ukupno} {n[3]}") + ((f", already entered {len(vec)} ({', '.join(vec)})" if EN else f", već upisano {len(vec)} ({', '.join(vec)})") if vec else "")
                 + ((f"   ·   inbreeding of young {pct(m.kinship(majka, otac))}" if EN else f"   ·   inbriding mladih {pct(m.kinship(majka, otac))}") if majka in m.A and otac in m.A else ""),
                 9, fg=INK2).pack(anchor="w", pady=(4, 0))

        auto = tk.Frame(b, bg=SURF2)
        auto.pack(fill="x", pady=(14, 4))
        g1 = tk.Frame(auto, bg=SURF2)
        g1.pack(fill="x", padx=14, pady=10)
        sv = tk.StringVar(value=STADO_PODMLADAK)
        for i, (nasl, vr) in enumerate(((("Date of birth" if EN else "Datum rođenja"), (f"{dstr}  ({star} days)" if EN else f"{dstr}  ({star} dana)")),
                                        (("Species / breed" if EN else "Vrsta / rasa"), f"{vrsta}{', ' + rasa if rasa else ''}"))):
            f = tk.Frame(g1, bg=SURF2)
            f.grid(row=0, column=i if i == 0 else 2, sticky="w", padx=(0, 22))
            self.lbl(f, nasl, 9, "bold", fg=INK2, bg=SURF2).pack(anchor="w")
            self.lbl(f, vr, 10, "bold", bg=SURF2).pack(anchor="w", pady=(6, 0))
        f = tk.Frame(g1, bg=SURF2)
        f.grid(row=0, column=1, sticky="w", padx=(0, 22))
        self.lbl(f, ("Herd" if EN else "Stado"), 9, "bold", fg=INK2, bg=SURF2).pack(anchor="w")
        ttk.Combobox(f, textvariable=sv, values=[STADO_PODMLADAK] + [x for x in self.sva_stada()
                                                                    if x != STADO_PODMLADAK],
                     width=16, font=self.f(10)).pack(anchor="w", pady=(3, 0))
        self.lbl(b, ("Date of birth and herd are automatic." if EN else "Datum rođenja i stado su automatski."), 8, fg="#8A968D").pack(anchor="w")

        self.lbl(b, (f"Enter each {n[2]}" if EN else f"Upiši svako {n[2]}"), 11, "bold").pack(anchor="w", pady=(14, 4))
        zag = tk.Frame(b, bg=SURF)
        zag.pack(fill="x")
        for t, w in ((("Tag / name *" if EN else "Oznaka / ime *"), 17), (("Ear tag number" if EN else "Ušna markica (minđuša)"), 19), (("Sex *" if EN else "Pol *"), 20)):
            self.lbl(zag, t, 9, "bold", fg=INK2, width=w, anchor="w").pack(side="left")
        lista = tk.Frame(b, bg=SURF)
        lista.pack(fill="x")
        redovi = []

        def dodaj_red(fokus=True):
            r = tk.Frame(lista, bg=SURF)
            r.pack(fill="x", pady=3)
            iv, mv, pv = tk.StringVar(), tk.StringVar(), tk.StringVar()
            e = ttk.Entry(r, textvariable=iv, width=15, font=self.f(10))
            e.pack(side="left", padx=(0, 10))
            ttk.Entry(r, textvariable=mv, width=17, font=self.f(10)).pack(side="left", padx=(0, 10))
            seg = tk.Frame(r, bg=SURF2)
            seg.pack(side="left")
            dug = {}

            def postavi(k):
                pv.set(k)
                for kk, lb in dug.items():
                    lb.config(bg=SURF if kk == k else SURF2, fg=INK if kk == k else INK2)
            for k, t in (("z", ("Female" if EN else "Žensko")), ("m", ("Male" if EN else "Muško"))):
                lb = tk.Label(seg, text=t, font=self.f(9, "bold"), padx=12, pady=4, bg=SURF2, fg=INK2,
                              cursor="hand2")
                lb.pack(side="left", padx=2, pady=2)
                lb.bind("<Button-1>", lambda ev, k=k: postavi(k))
                dug[k] = lb
            red_ = {"okvir": r, "id": iv, "mk": mv, "pol": pv}
            x_ = self.lbl(r, "✕", 11, "bold", fg=INK2, cursor="hand2")
            x_.pack(side="left", padx=10)
            x_.bind("<Button-1>", lambda ev: ukloni(red_))
            redovi.append(red_)
            if fokus:
                e.focus_set()

        def ukloni(red_):
            if len(redovi) > 1:
                red_["okvir"].destroy()
                redovi.remove(red_)

        for i in range(ostalo):
            dodaj_red(fokus=i == 0)
        lk = self.lbl(b, (f"+ Add another {n[2]}" if EN else f"+ Dodaj još jedno {n[2]}"), 9, "bold", fg=BRAND, cursor="hand2")
        lk.pack(anchor="w", pady=(6, 0))
        lk.bind("<Button-1>", lambda e: dodaj_red())
        self.lbl(b, ("If a young animal has no ear tag yet, remove its row (✕) – you will enter it later." if EN else "Ako neko mladunče još nema minđušu, ukloni njegov red (✕) – upisaćeš ga kasnije."), 8,
                 fg="#8A968D").pack(anchor="w", pady=(2, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD, wraplength=560, justify="left")
        err.pack(anchor="w", pady=(10, 0))

        def sacuvaj(ev=None):
            stado = sv.get().strip() or STADO_PODMLADAK
            novi, vidjeni = [], set()
            for i, r in enumerate(redovi, 1):
                nid, mk, pol = r["id"].get().strip(), r["mk"].get().strip(), r["pol"].get()
                if not nid:
                    err.config(text=(f"Enter a tag or name for {n[2]} no. {i} (or remove the row ✕)." if EN else f"Upiši oznaku ili ime za {i}. {n[2]} (ili ukloni red ✕)."))
                    return
                if nid in vidjeni or self.red_za(nid) or nid in m.A:
                    err.config(text=(f"Tag {nid} already exists. Choose another." if EN else f"Oznaka {nid} već postoji. Izaberi drugu."))
                    return
                if mk:
                    poruka = self.markica_zauzeta(mk, None)
                    if poruka or any(norm(mk) == norm(x["markica"]) for x in novi):
                        err.config(text=poruka or (f"Ear tag {mk} is entered twice." if EN else f"Markica {mk} je upisana dva puta."))
                        return
                if pol not in ("m", "z"):
                    err.config(text=(f"Choose the sex for {nid}." if EN else f"Izaberi pol za {nid}."))
                    return
                vidjeni.add(nid)
                novi.append(dict(id=nid, markica=mk, vrsta=vrsta, rasa=rasa, pol=pol, datum_rodjenja=dstr,
                                 otac=otac or "", majka=majka or "", status="aktivno", stado=stado,
                                 poreklo=("Home bred" if EN else "Sopstveni odgoj"), poreklo_od="", stare_markice="", uneto=sada()))
            for x in novi:
                self.tab.redovi.append(x)
                self.ist.dodaj(x["id"], AUTO, (f"Born {dstr} from {majka or '?'} × {otac or '?'} – entered in the list "
                                              f"(herd {stado})" if EN else f"Rođeno {dstr} od {majka or '?'} × {otac or '?'} – upisano u listu "
                                              f"(stado {stado})"), automatski=True)
            sad = vec + [x["id"] for x in novi]
            opis = ", ".join((f"{x['id']} ({'male' if x['pol'] == 'm' else 'female'})" if EN else f"{x['id']} ({'muško' if x['pol'] == 'm' else 'žensko'})") for x in novi)
            if majka:
                self.ist.dodaj(majka, AUTO, (f"Young stock entered in the list: {opis}" if EN else f"Podmladak upisan u listu: {opis}"), automatski=True)
            if len(sad) >= ukupno:
                z["ishod"] = "rodjeno:" + ",".join(sad)
            else:
                ost = ukupno - len(sad)
                cekaj = messagebox.askyesno(
                    ("Remaining young" if EN else "Ostali mladi"), (f"Entered {len(sad)} of {ukupno}. {ost} remaining.\n\n"
                                    "Are the others still waiting for ear tags?\n\n"
                                    "Yes – they stay on the list for later\nNo – they are gone (died, sold…)" if EN else f"Upisano {len(sad)} od {ukupno}. Ostalo još {ost}.\n\n"
                                    "Da li ostali još čekaju minđušu?\n\n"
                                    "Da – ostaju na spisku za kasnije\nNe – nema ih više (uginuli, prodati…)"),
                    parent=win)
                if cekaj:
                    z["ishod"] = f"leglo:{ukupno}:{dstr}:{','.join(sad)}"
                else:
                    z["ishod"] = "rodjeno:" + ",".join(sad)
                    if majka:
                        self.ist.dodaj(majka, AUTO, (f"From the litter ({dstr}) {ost} not entered – died or sold" if EN else f"Od legla ({dstr}) nije upisano {ost} – uginuli ili prodati"),
                                       automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Entered in the list: {', '.join(x['id'] for x in novi)} (herd {stado})" if EN else f"Upisano u listu: {', '.join(x['id'] for x in novi)} (stado {stado})"))
            self.osvezi_istoriju()

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Enter in animal list" if EN else "Upiši u listu grla"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        self.btn(fb, ("Remove from list…" if EN else "Ukloni sa spiska…"), lambda: (win.grab_release(), win.destroy(),
                                                    self.ukloni_iz_legla(z, parent)), "Danger").pack(side="left")
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda ev: win.destroy())
        self.postavi_prozor(win, parent)

    def s_istorija(self):
        body = self.strana_okvir(scroll=False)
        self.zaglavlje(body, ("History" if EN else "Istorija"), ("All events in the herd – from newest to oldest." if EN else "Svi događaji u stadu – od najnovijeg ka starijim."),
                       [(("Gestation" if EN else "Nosivost"), self.podesavanje_gravidnosti, "Secondary"),
                        (("+  Add event" if EN else "+  Dodaj događaj"), lambda: self.dogadjaj_forma(None), "Primary")])
        self.istorija_lista(body, None)

    def istorija_lista(self, body, x, bez_dodaj=False):
        """Lista zapisa sa filterima (za jedno grlo ili celo stado)."""
        tb = tk.Frame(body, bg=BG)
        tb.pack(fill="x", pady=(0, 12))
        key = "ist_" + (x or "_sve")
        st = self.ui.setdefault(key, {"vrsta": ("All events" if EN else "Svi događaji"), "auto": x is not None, "q": ""})
        qv = tk.StringVar(value=st["q"])
        if x is None:
            e = ttk.Entry(tb, textvariable=qv, width=22, font=self.f(10))
            e.pack(side="left", padx=(0, 10))
            ph = self.lbl(tb, ("⌕  Animal or ear tag…" if EN else "⌕  Grlo ili markica…"), 10, fg="#98A39B", bg=SURF)
            def ph_show(*_):
                ph.place_forget() if qv.get() else ph.place(in_=e, x=10, rely=0.5, anchor="w")
            ph.bind("<Button-1>", lambda ev: e.focus_set())
            ph_show()
            qv.trace_add("write", ph_show)
        vv = tk.StringVar(value=st["vrsta"])
        cb = ttk.Combobox(tb, textvariable=vv, values=[("All events" if EN else "Svi događaji")] + DOGADJAJI + [("Offspring" if EN else "Potomak")],
                          state="readonly", width=22, font=self.f(10))
        cb.pack(side="left")
        av = tk.BooleanVar(value=st["auto"])
        ttk.Checkbutton(tb, text=("Show record changes too" if EN else "Prikaži i promene u evidenciji"), variable=av).pack(side="left", padx=12)
        kartice = tk.Frame(body, bg=BG)
        kartice.pack(fill="x", pady=(0, 12))
        cekaju = self.cekaju_porodjaj(x)
        if cekaju:
            co, cc = self.card(body, 16, 10)
            co.pack(fill="x", pady=(0, 12))
            hr = tk.Frame(cc, bg=SURF)
            hr.pack(fill="x")
            self.lbl(hr, (f"Waiting for young ({len(cekaju)})" if EN else f"Čekaju mlade ({len(cekaju)})"), 11, "bold").pack(side="left")
            lg = self.lbl(hr, ("Gestation…" if EN else "Nosivost…"), 9, "bold", fg=BRAND, cursor="hand2")
            lg.pack(side="right")
            lg.bind("<Button-1>", lambda e: self.podesavanje_gravidnosti())
            self.lbl(cc, ("Tick \"Young born\" after the pregnancy time – enter date and number (sex and tag later)." if EN else "„Dobijeni mladi“ se može štiklirati tek kad prođe vreme gravidnosti – tada upisuješ datum i "
                         "broj rođenih (pol i oznaku kasnije)."), 9, fg=INK2).pack(anchor="w", pady=(0, 6))
            danas = date.today()
            for z in cekaju[:5]:
                majka, otac = self.roditelji_parenja(z)
                oc = self.ocekivani_porodjaj(z)
                r = tk.Frame(cc, bg=SURF)
                r.pack(fill="x", pady=2)
                od = self.upis_moguc_od(z)
                otvoreno = od is None or danas >= od
                cv = tk.BooleanVar(value=False)
                cb_ = ttk.Checkbutton(r, text=("Young born" if EN else "Dobijeni mladi"), variable=cv, style="Card.TCheckbutton",
                                      command=lambda z=z, cv=cv: (cv.set(False), self.upis_podmlatka(z)))
                cb_.pack(side="left")
                if not otvoreno:
                    cb_.state(["disabled"])
                self.lbl(r, f"{majka or '?'} × {otac or '?'}", 10, "bold").pack(side="left", padx=(14, 10))
                self.lbl(r, (f"mated {z['datum']}" if EN else f"pareno {z['datum']}"), 9, fg=INK2).pack(side="left")
                if oc:
                    dk = self.najkasniji_porodjaj(z)
                    if not otvoreno:
                        txt, boja = ((f"pregnant · birth {od.strftime('%d/%m')}–{dk.strftime('%d/%m/%Y')} "
                                     f"(in {(od - danas).days} d.)" if EN else f"gravidna · porođaj {od.strftime('%d.%m.')}–{dk.strftime('%d.%m.%Y')} "
                                     f"(za {(od - danas).days} d.)")), INK2
                    elif danas <= dk:
                        txt, boja = (f"birth ~{oc.strftime('%d/%m')} (latest {dk.strftime('%d/%m')}) – entry open" if EN else f"porođaj ~{oc.strftime('%d.%m.')} (najkasnije {dk.strftime('%d.%m.')}) – upis otvoren"), WARN
                    else:
                        txt, boja = (f"due date passed {dk.strftime('%d/%m/%Y')} ({(danas - dk).days} d.)" if EN else f"termin prošao {dk.strftime('%d.%m.%Y')} ({(danas - dk).days} d.)"), BAD
                    self.lbl(r, txt, 9, "bold", fg=boja).pack(side="left", padx=12)
                if not otvoreno:
                    lp = self.lbl(r, "prevremeni?", 9, fg=BRAND, cursor="hand2")
                    lp.pack(side="right", padx=(10, 0))
                    lp.bind("<Button-1>", lambda e, z=z: self.upis_podmlatka(z))
                lk = self.lbl(r, ("failed" if EN else "nije uspelo"), 9, fg=INK2, cursor="hand2")
                lk.pack(side="right")
                lk.bind("<Button-1>", lambda e, z=z: self.oznaci_neuspelo(z))
            if len(cekaju) > 5:
                self.lbl(cc, (f"… and {len(cekaju) - 5} more (see the \"Young\" column in the table)" if EN else f"… i još {len(cekaju) - 5} (vidi kolonu „Mladi“ u tabeli)"), 9, fg=INK2).pack(anchor="w")
        legla = self.cekaju_mindjusu(x)
        if legla:
            lo, lc = self.card(body, 16, 10)
            lo.pack(fill="x", pady=(0, 12))
            self.lbl(lc, (f"Waiting for ear tag – entry in animal list ({len(legla)})" if EN else f"Čekaju minđušu – upis u listu grla ({len(legla)})"), 11, "bold").pack(anchor="w")
            self.lbl(lc, ("Young born without tag and sex. When they get their ear tags, click \"Enter in list\"." if EN else "Rođeni mladi bez oznake i pola. Kad dobiju minđušu, klikni „Upiši u listu“."), 9,
                     fg=INK2).pack(anchor="w", pady=(0, 6))
            for z in legla:
                uk, dd, vec = self.leglo(z)
                majka, otac = self.roditelji_parenja(z)
                dr = parsiraj_datum(dd)
                star = (date.today() - dr).days if dr else None
                n_ = nazivi(self.vrsta_parenja(z))
                r = tk.Frame(lc, bg=SURF)
                r.pack(fill="x", pady=2)
                self.btn(r, ("Enter in list" if EN else "Upiši u listu"), lambda z=z: self.upis_u_listu(z), "Primary").pack(side="right")
                self.btn(r, ("Remove…" if EN else "Ukloni…"), lambda z=z: self.ukloni_iz_legla(z), "Danger").pack(side="right", padx=8)
                self.lbl(r, f"{majka or '?'} × {otac or '?'}", 10, "bold").pack(side="left")
                self.lbl(r, f"{uk - len(vec)} {n_[3]}" + ((f" (of {uk})" if EN else f" (od {uk})") if vec else ""), 10, "bold",
                         fg=BRAND).pack(side="left", padx=12)
                self.lbl(r, (f"born {dd}" if EN else f"rođeno {dd}") + ((f" · {star} d. old" if EN else f" · staro {star} d.") if star is not None else ""), 9,
                         fg=INK2).pack(side="left")
        dugmad = tk.Frame(body, bg=BG)
        dugmad.pack(fill="x", pady=(0, 10))
        holder = tk.Frame(body, bg=BG)
        holder.pack(fill="both", expand=True)
        stanje = {"tv": None}
        st.setdefault("grupa", "")

        def crtaj_kartice():
            for w in kartice.winfo_children():
                w.destroy()
            svi = self.ist.za(x)
            for i, (naziv, vrste) in enumerate([(("All" if EN else "Sve"), None)] + GRUPE):
                if x is None and vrste:      # za celo stado porođaj se broji jednom (kod majke)
                    vrste = tuple(v for v in vrste if v != ("Offspring" if EN else "Potomak"))
                zz = [z for z in svi if vrste is None or z["dogadjaj"] in vrste]
                if vrste is None:
                    zz = [z for z in zz if av.get() or not z["automatski"]]
                akt = st["grupa"] == ("" if vrste is None else naziv)
                bg = BRAND if akt else SURF
                fg, fg2 = ("#FFFFFF", "#D7E6DC") if akt else (INK, INK2)
                k = tk.Frame(kartice, bg=bg if akt else LINE, cursor="hand2")
                k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
                kartice.columnconfigure(i, weight=1, uniform="k")
                u = tk.Frame(k, bg=bg)
                u.pack(fill="both", expand=True, padx=1, pady=1)
                l1 = tk.Label(u, text=naziv, font=self.f(10, "bold"), bg=bg, fg=fg)
                l1.pack(anchor="w", padx=14, pady=(10, 0))
                l2 = tk.Label(u, text=str(len(zz)), font=self.f(20, "bold"), bg=bg, fg=fg)
                l2.pack(anchor="w", padx=14)
                if vrste is None:
                    pod = ("all records" if EN else "svih zapisa")
                elif zz:
                    z0 = zz[0]
                    pod = (f"last {z0['datum']}" if EN else f"poslednje {z0['datum']}")
                    if naziv == ("Matings" if EN else "Parenja") and z0["partner"]:
                        pod += (f"\nwith {z0['partner']}" if EN else f"\nsa {z0['partner']}")
                    elif naziv == ("Treatments" if EN else "Lečenja") and (z0["vrednost"] or z0["dogadjaj"] == ("Vaccination" if EN else "Vakcinacija")):
                        det = z0["vrednost"] or ("vaccination" if EN else "vakcinacija")
                        pod += "\n" + (det if len(det) <= 24 else det[:23] + "…")
                else:
                    pod = ("no records" if EN else "nema zapisa")
                l3 = tk.Label(u, text=pod, font=self.f(9), bg=bg, fg=fg2, justify="left")
                l3.pack(anchor="w", padx=14, pady=(0, 10))
                for w in (k, u, l1, l2, l3):
                    w.bind("<Button-1>", lambda e, n=("" if vrste is None else naziv): izaberi_grupu(n))

        def izaberi_grupu(n):
            st["grupa"] = n
            if n:
                vv.set(("All events" if EN else "Svi događaji"))
            osvezi()

        def osvezi(*_):
            st.update(vrsta=vv.get(), auto=av.get(), q=qv.get())
            for w in holder.winfo_children():
                w.destroy()
            crtaj_kartice()
            grupa = dict(GRUPE).get(st["grupa"])
            if grupa and x is None:
                grupa = tuple(v for v in grupa if v != ("Offspring" if EN else "Potomak"))
            zap = self.ist.za(x, auto=av.get() or bool(grupa))
            if grupa:
                zap = [z for z in zap if z["dogadjaj"] in grupa]
            if vv.get() != ("All events" if EN else "Svi događaji"):
                zap = [z for z in zap if z["dogadjaj"] == vv.get()]
            q = norm(qv.get())
            if q and x is None:
                ids = {g for g in self.model.A if q in norm(g) or q in norm(self.model.A[g]["markica"])}
                zap = [z for z in zap if z["grlo"] in ids or q in norm(z["grlo"])]
            if not zap:
                self.napomena(holder, ("No records for the selected filter." if EN else "Nema zapisa za izabrani filter.") if self.ist.za(x) else
                              ("No records yet. Add the first event with the \"Add event\" button." if EN else "Još nema zapisa. Dodaj prvi događaj dugmetom „Dodaj događaj“."), ok=True)
                stanje["tv"] = None
                return
            wrap, tv = self.tabela_istorije(holder, zap, x is None)
            wrap.pack(fill="both", expand=True)
            stanje["tv"] = tv
            tv.bind("<Double-1>", lambda e: izmeni())
            tv.bind("<Delete>", lambda e: obrisi())

            def klik_mladi(e, tv=tv):
                if tv.identify_region(e.x, e.y) != "cell":
                    return
                kol = tv.identify_column(e.x)
                if tv.heading(kol, "text") != ("Young" if EN else "Mladi"):
                    return
                iid = tv.identify_row(e.y)
                if iid:
                    z = self.ist.zapisi[int(iid)]
                    if z["dogadjaj"] == PARENJE and not z["automatski"]:
                        self.upis_podmlatka(z)
                        return "break"
            tv.bind("<Button-1>", klik_mladi, add="+")

        def izabran():
            tv = stanje["tv"]
            sel = tv.selection() if tv else ()
            if not sel:
                self.toast(("First select a record in the table." if EN else "Prvo označi zapis u tabeli."))
                return None
            return self.ist.zapisi[int(sel[0])]

        def izmeni():
            z = izabran()
            if not z:
                return
            if z["automatski"]:
                self.toast(("Automatic records cannot be changed." if EN else "Automatski zapisi se ne menjaju."))
                return
            self.dogadjaj_forma(z["grlo"], zapis=z, posle=osvezi)

        def obrisi():
            z = izabran()
            if not z:
                return
            if z["automatski"]:
                self.toast(("Automatic records cannot be deleted." if EN else "Automatski zapisi se ne brišu."))
                return
            if messagebox.askyesno(("Delete record" if EN else "Obriši zapis"), (f"Delete the record \"{z['dogadjaj']}\" of {z['datum']}?" if EN else f"Obrisati zapis „{z['dogadjaj']}“ od {z['datum']}?")):
                self.ist.zapisi.remove(z)
                self.ist.sacuvaj()
                osvezi()

        if x and not bez_dodaj:
            self.btn(dugmad, ("+  Add event" if EN else "+  Dodaj događaj"), lambda: self.dogadjaj_forma(x, posle=osvezi), "Primary").pack(
                side="left", padx=(0, 8))
        self.btn(dugmad, ("Edit record" if EN else "Izmeni zapis"), izmeni).pack(side="left")
        self.btn(dugmad, ("Delete record" if EN else "Obriši zapis"), obrisi, "Danger").pack(side="left", padx=8)
        self.lbl(dugmad, ("Double-click edits a record. Grey = automatic changes." if EN else "Dvoklik menja zapis. Sivo = automatske promene."), 9,
                 fg=INK2).pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda e: (st.update(grupa=""), osvezi()))
        av.trace_add("write", osvezi)
        qv.trace_add("write", osvezi)
        osvezi()
        return osvezi

    def azuriraj_grlo(self, red, novi):
        """Primeni izmene podataka grla (bez promene oznake) i zapiši ih u istoriju. Vrati poruku greške ili None."""
        mk = (novi.get("markica") or "").strip()
        if mk and norm(mk) != norm(red.get("markica")):
            poruka = self.markica_zauzeta(mk, red)
            if poruka:
                return poruka
        d = (novi.get("datum_rodjenja") or "").strip()
        if d:
            pd = parsiraj_datum(d)
            if not pd:
                return ("The date of birth is not valid. Enter it as 15/03/2022." if EN else "Datum rođenja nije ispravan. Upiši ga kao 15.03.2022.")
            if pd == parsiraj_datum(red.get("datum_rodjenja")):
                novi["datum_rodjenja"] = red.get("datum_rodjenja", "")   # isti datum, drugi zapis – ne menjaj
            else:
                novi["datum_rodjenja"] = pd.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
        for p in ("otac", "majka"):
            v = (novi.get(p) or "").strip()
            if v and (v == red["id"] or self.model.nadji(v) == red["id"]):
                return ("An animal cannot be its own parent." if EN else "Grlo ne može biti sopstveni roditelj.")
            novi[p] = self.model.nadji(v) or v if v else ""
        if norm(mk) != norm(red.get("markica")):
            self.primeni_markicu(red, mk, zapamti=True)
        novi.pop("markica", None)
        nazivi_polja = dict(rasa=("breed" if EN else "rasa"), pol=("sex" if EN else "pol"), datum_rodjenja=("date of birth" if EN else "datum rođenja"), otac=("sire" if EN else "otac"), majka=("dam" if EN else "majka"),
                            status="status", stado="stado", poreklo="poreklo", poreklo_od=("origin from" if EN else "poreklo od"))
        promene = [f"{n}: {red.get(k) or '–'} → {novi.get(k) or '–'}" for k, n in nazivi_polja.items()
                   if k in novi and (red.get(k) or "") != (novi.get(k) or "")]
        if promene:
            self.ist.dodaj(red["id"], AUTO, ("Details changed – " if EN else "Izmena podataka – ") + "; ".join(promene), automatski=True)
        red.update(novi)
        return None

    # ================================================================ REZERVNE KOPIJE
    # Imena foldera postoje na oba jezika: kopije napravljene na jednom jeziku vide se i na drugom.
    _KOREN = ("rezervne_kopije", "backups")
    _KOREN2 = ("Farmer – kopije", "Farmer – backups")
    _AUTO = ("automatske", "automatic")
    _RUCNE = ("rucne", "manual")
    _PRATECI = ("_istorija.csv", "_history.csv", "_podsetnici.csv", "_reminders.csv")

    @staticmethod
    def _postojeci(osnova, imena):
        """Postojeći podfolder na bilo kom jeziku, inače ime na trenutnom jeziku."""
        for ime in imena:
            if os.path.isdir(os.path.join(osnova, ime)):
                return os.path.join(osnova, ime)
        return os.path.join(osnova, imena[1] if EN else imena[0])

    # ---------------------------------------------- druga lokacija (USB, OneDrive, Google Drive)
    @staticmethod
    def _diskovi():
        """Windows: [(slovo, tip, oznaka, serijski)]; tip 2 = USB/prenosivi."""
        rez = []
        try:
            import ctypes
            k = ctypes.windll.kernel32
            maska = k.GetLogicalDrives()
            for i in range(26):
                if not maska >> i & 1:
                    continue
                d = f"{chr(65 + i)}:\\"
                tip = k.GetDriveTypeW(d)
                if tip not in (2, 3, 4):          # prenosivi, lokalni, mrežni
                    continue
                ime = ctypes.create_unicode_buffer(261)
                ser = ctypes.c_ulong(0)
                ok = k.GetVolumeInformationW(d, ime, 261, ctypes.byref(ser), None, None, None, 0)
                rez.append((d, tip, ime.value if ok else "", ser.value if ok else 0))
        except Exception:
            pass
        return rez

    def _serijski(self, putanja):
        d = os.path.splitdrive(os.path.abspath(putanja))[0].upper() + "\\"
        for slovo, _, _, ser in self._diskovi():
            if slovo == d:
                return ser
        return 0

    def predlozi_lokacije(self):
        """Pronađeni OneDrive, Google Drive, Dropbox i USB diskovi: [(naziv, folder)]."""
        rez, home = [], os.path.expanduser("~")

        def dodaj(naziv, p):
            if p and os.path.isdir(p) and os.path.normcase(p) not in [os.path.normcase(x[1]) for x in rez]:
                rez.append((naziv, p))
        for env in ("OneDriveConsumer", "OneDriveCommercial", "OneDrive"):
            dodaj("OneDrive", os.environ.get(env, ""))
        dodaj("OneDrive", os.path.join(home, "OneDrive"))
        diskovi = self._diskovi()
        for slovo, tip, oznaka, _ in diskovi:
            if "google" in oznaka.lower():
                try:
                    for ime in sorted(os.listdir(slovo)):
                        if os.path.isdir(os.path.join(slovo, ime)) and not ime.startswith((".", "$")):
                            dodaj("Google Drive", os.path.join(slovo, ime))
                            break
                except OSError:
                    pass
        for ime in ("Google Drive", "My Drive", "GoogleDrive"):
            dodaj("Google Drive", os.path.join(home, ime))
        dodaj("Dropbox", os.path.join(home, "Dropbox"))
        for slovo, tip, oznaka, _ in diskovi:
            if tip == 2:
                dodaj(f"USB {slovo[:2]}" + (f" ({oznaka})" if oznaka else ""), slovo)
        return rez

    def druga_lokacija_stanje(self):
        """'nema' (nije izabrana), 'ok', ili 'nedostupna' (USB izvađen, disk nije tu).
        Ako je USB dobio drugo slovo (E: -> F:), sam ga pronađe po serijskom broju."""
        d2 = self.pod.get("kopija2", "")
        if not d2:
            return "nema"
        if os.path.isdir(d2):
            return "ok"
        ser = self.pod.get("kopija2_disk", 0)
        if ser:
            ostatak = os.path.splitdrive(d2)[1]
            for slovo, _, _, s in self._diskovi():
                nova = os.path.join(slovo, ostatak.lstrip("\\/"))
                if s == ser and os.path.isdir(nova):
                    self.pod["kopija2"] = nova
                    self.sacuvaj_podesavanja()
                    return "ok"
        return "nedostupna"

    def postavi_drugu_lokaciju(self, d):
        self.pod["kopija2"] = d
        self.pod["kopija2_disk"] = self._serijski(d)
        self.sacuvaj_podesavanja()
        if self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0], tiho=False) and \
                self.pod.get("poslednja_kopija2", "")[:10] == date.today().strftime("%Y-%m-%d"):
            self.toast(T("Kopija je napravljena i na: ", "Backup also made on: ") + d)
        if self.strana == "pregled":
            self.prikazi("pregled")

    def izaberi_drugu_lokaciju(self, uvod=False):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Druga lokacija za kopije", "Second backup location"))
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        self.lbl(b, T("Zaštiti stado od kvara računara", "Protect your herd if the computer breaks") if uvod
                 else T("Druga lokacija za kopije", "Second backup location"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Kopije su sada samo na ovom računaru. Ako se disk pokvari, računar ukrade ili uđe virus, "
                      "rodoslov se gubi. Izaberi i drugo mesto – program će tamo sam kopirati podatke svaki dan i pri zatvaranju.\n\n"
                      "Najbolje je OneDrive ili Google Drive: kopija ode i na internet.",
                      "Backups are only on this computer now. If the disk fails, the computer is stolen or gets a virus, "
                      "the pedigree is lost. Choose a second place – the program will copy the data there every day and when closing.\n\n"
                      "OneDrive or Google Drive is best: the copy also goes online."),
                 9, fg=INK2, wraplength=520, justify="left").pack(anchor="w", pady=(4, 12))

        def izaberi(d):
            win.destroy()
            self.postavi_drugu_lokaciju(d)

        def drugi():
            d = filedialog.askdirectory(parent=win, title=T("Izaberi folder za kopije (USB, OneDrive, Google Drive…)",
                                                            "Choose a backup folder (USB, OneDrive, Google Drive…)"))
            if d:
                izaberi(os.path.normpath(d))
        predlozi = self.predlozi_lokacije()
        if predlozi:
            self.lbl(b, T("Pronađeno na ovom računaru:", "Found on this computer:"), 10, "bold").pack(anchor="w", pady=(0, 4))
        for naziv, p in predlozi:
            r = tk.Frame(b, bg=SURF)
            r.pack(fill="x", pady=2)
            self.btn(r, naziv, lambda p=p: izaberi(p), "Primary" if naziv in ("OneDrive", "Google Drive") else "Secondary").pack(side="left")
            self.lbl(r, p, 9, fg=INK2).pack(side="left", padx=10)
        if not predlozi:
            self.napomena(b, T("Nije pronađen ni OneDrive, ni Google Drive, ni USB. Uključi USB pa otvori ovaj prozor ponovo, "
                               "ili izaberi folder ručno.", "No OneDrive, Google Drive or USB found. Plug in a USB stick and open this "
                               "window again, or choose a folder yourself."), wraplength=520)
        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, T("Drugi folder…", "Other folder…"), drugi).pack(side="left")
        if self.pod.get("kopija2"):
            def ukloni():
                self.pod.pop("kopija2", None)
                self.pod.pop("kopija2_disk", None)
                self.sacuvaj_podesavanja()
                win.destroy()
                self.osvezi_kopija_label()
                if self.strana == "pregled":
                    self.prikazi("pregled")
            self.btn(fb, T("Ukloni drugu lokaciju", "Remove second location"), ukloni, "Danger").pack(side="left", padx=8)
        self.btn(fb, T("Kasnije", "Later") if uvod else T("Otkaži", "Cancel"), win.destroy).pack(side="right")
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, None)

    def folder_kopija(self, druga=False):
        if druga:
            if self.druga_lokacija_stanje() != "ok":
                return None
            return self._postojeci(self.pod["kopija2"], self._KOREN2)
        return self._postojeci(os.path.dirname(os.path.abspath(self.tab.putanja)), self._KOREN)

    def fajlovi_podataka(self):
        return [p for p in (self.tab.putanja, self.ist.putanja, self.pods.putanja) if os.path.isfile(p)]

    def napravi_kopiju(self, vrsta="automatske", naziv=None, tiho=True):
        """Kopira tablicu, istoriju i podsetnike pored programa i na drugu lokaciju. Vraća folder kopije ili None."""
        fajlovi = self.fajlovi_podataka()
        if not fajlovi:
            return None
        imena = self._RUCNE if vrsta in self._RUCNE else self._AUTO
        naziv = naziv or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        cilj = None
        for druga in (False, True):
            koren = self.folder_kopija(druga)
            if not koren:
                continue
            try:
                grupa = self._postojeci(koren, imena)
                f = os.path.join(grupa, naziv)
                os.makedirs(f, exist_ok=True)
                for p in fajlovi:
                    shutil.copy2(p, os.path.join(f, os.path.basename(p)))
                self.ocisti_stare_kopije(grupa)
                if druga:
                    self.pod["poslednja_kopija2"] = sada()
                else:
                    cilj = f
            except OSError as e:
                if not tiho:
                    messagebox.showerror(T("Rezervna kopija", "Backup"),
                                         (T("Kopija na drugoj lokaciji nije napravljena:\n", "Backup on the second location was not made:\n")
                                          if druga else T("Kopija nije napravljena:\n", "Backup was not made:\n")) + str(e))
        if cilj:
            self.pod["poslednja_kopija"] = sada()
        self.sacuvaj_podesavanja()
        self.osvezi_kopija_label()
        return cilj

    @staticmethod
    def ocisti_stare_kopije(folder, zadrzi=30):
        try:
            sve = sorted(d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d)))
            for d in sve[:-zadrzi]:
                shutil.rmtree(os.path.join(folder, d), ignore_errors=True)
        except OSError:
            pass

    def dnevna_kopija(self):
        """Jednom dnevno, pri pokretanju (i kad se USB uključi kasnije): automatske/GGGG-MM-DD."""
        dan = date.today().strftime("%Y-%m-%d")
        treba = not os.path.isdir(os.path.join(self._postojeci(self.folder_kopija(), self._AUTO), dan))
        if self.druga_lokacija_stanje() == "ok" and self.pod.get("poslednja_kopija2", "")[:10] != dan:
            treba = True
        if treba:
            self.napravi_kopiju(self._AUTO[1] if EN else self._AUTO[0], dan)
        self.podseti_na_drugu_lokaciju()

    def podseti_na_drugu_lokaciju(self):
        """Ako druga lokacija nije izabrana, jednom nedeljno ponudi da se izabere."""
        if self.druga_lokacija_stanje() != "nema" or not self.tab.redovi:
            return
        if self.pod.get("kopija2_podsetnik", "")[:10] > (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"):
            return
        if any(isinstance(w, tk.Toplevel) and w.winfo_exists() for w in self.root.winfo_children()):
            self.root.after(4000, self.podseti_na_drugu_lokaciju)   # sačeka da se zatvore obaveštenja
            return
        self.pod["kopija2_podsetnik"] = sada()
        self.sacuvaj_podesavanja()
        self.izaberi_drugu_lokaciju(uvod=True)

    def zatvori_kopija(self):
        """Pri zatvaranju: kopija; ako je USB izvađen, ponudi da se uključi."""
        dan = date.today().strftime("%Y-%m-%d")
        while (self.druga_lokacija_stanje() == "nedostupna" and self.pod.get("poslednja_kopija2", "")[:10] != dan and
               messagebox.askretrycancel(T("Druga lokacija nije dostupna", "Second location not available"),
                                         T(f"Kopija ne može da se napravi na:\n{self.pod.get('kopija2')}\n\n"
                                           "Ako je to USB, uključi ga i klikni „Pokušaj ponovo“.\n"
                                           "„Otkaži“ zatvara program bez te kopije (kopija pored programa se pravi svakako).",
                                           f"The backup cannot be made on:\n{self.pod.get('kopija2')}\n\n"
                                           "If it is a USB stick, plug it in and click \"Retry\".\n"
                                           "\"Cancel\" closes the program without that copy (the copy next to the program is made anyway)."))):
            pass
        self.napravi_kopiju(self._AUTO[1] if EN else self._AUTO[0], dan)

    @staticmethod
    def _kad(t):
        try:
            dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None
        kad = (T("danas", "today") if dt.date() == date.today() else T("juče", "yesterday") if dt.date() == date.today() - timedelta(days=1)
               else dt.strftime(T("%d.%m.%Y.", "%d/%m/%Y")))
        return f"{kad} {dt.strftime('%H:%M')}"

    def osvezi_kopija_label(self):
        if not getattr(self, "lbl_kopija", None):
            return
        try:
            if not self.lbl_kopija.winfo_exists():
                return
        except tk.TclError:
            return
        kad = self._kad(self.pod.get("poslednja_kopija", ""))
        if not kad:
            self.lbl_kopija.config(text=T("Kopija: još nije napravljena", "Backup: not made yet"), fg=WARN, wraplength=180)
            return
        st = self.druga_lokacija_stanje()
        if st == "ok":
            dodatak, boja = T("  ·  i na drugom mestu ✓", "  ·  also on 2nd location ✓"), INK2
        elif st == "nedostupna":
            kad2 = self._kad(self.pod.get("poslednja_kopija2", ""))
            dodatak, boja = T("\nDruga lokacija nije uključena", "\nSecond location not plugged in") + \
                (T(f" (poslednja: {kad2})", f" (last: {kad2})") if kad2 else ""), WARN
        else:
            dodatak, boja = T("\nSamo na ovom računaru", "\nOnly on this computer"), WARN
        self.lbl_kopija.config(text=T(f"Kopija: {kad}", f"Backup: {kad}") + dodatak, fg=boja, justify="left", wraplength=180)

    # ---------------------------------------------- spisak i vraćanje
    def _kopija_u_folderu(self, put):
        """Glavna tablica u folderu kopije (stado.csv, herd.csv ili druga .csv koja nije istorija/podsetnici)."""
        try:
            csvovi = sorted(f for f in os.listdir(put) if f.lower().endswith(".csv") and not f.lower().endswith(self._PRATECI))
        except OSError:
            return None
        ime = os.path.basename(self.tab.putanja)
        if ime in csvovi:
            return os.path.join(put, ime)
        return os.path.join(put, csvovi[0]) if csvovi else None

    @staticmethod
    def _broj_grla(tab):
        try:
            with open(tab, encoding="utf-8-sig", errors="ignore") as f:
                return max(0, sum(1 for l in f if l.strip()) - 1)
        except OSError:
            return 0

    def spisak_kopija(self, dodatni=None):
        """Sve kopije: pored programa, na drugoj lokaciji i (opciono) u folderu koji je korisnik izabrao."""
        rez, videno = [], set()

        def obradi(put, vrsta, gde):
            put = os.path.normpath(put)
            if os.path.normcase(put) in videno:
                return
            tab = self._kopija_u_folderu(put)
            if tab:
                videno.add(os.path.normcase(put))
                rez.append(dict(put=put, tab=tab, vrsta=vrsta, gde=gde, vreme=os.path.getmtime(tab), grla=self._broj_grla(tab)))
        mesta = [(self.folder_kopija(), T("pored programa", "next to the program"))]
        if self.folder_kopija(True):
            mesta.append((self.folder_kopija(True), T("druga lokacija", "second location")))
        for koren, gde in mesta:
            for imena in (self._AUTO, self._RUCNE):
                for ime in imena:
                    f = os.path.join(koren, ime)
                    if os.path.isdir(f):
                        for d in os.listdir(f):
                            obradi(os.path.join(f, d), "rucne" if imena is self._RUCNE else "automatske", gde)
        if dodatni:
            gde = os.path.basename(os.path.normpath(dodatni)) or dodatni
            for koren, dirs, _ in os.walk(dodatni):
                if koren[len(dodatni):].count(os.sep) >= 4:
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs if not d.startswith((".", "$"))]
                obradi(koren, "rucne" if os.path.basename(os.path.dirname(koren)) in self._RUCNE else "automatske", gde)
        return sorted(rez, key=lambda k: -k["vreme"])

    def otvori_folder(self, folder):
        try:
            os.makedirs(folder, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}" &')
        except OSError:
            messagebox.showinfo("Folder", folder)

    def vrati_iz_kopije(self):
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(T("Vraćanje iz rezervne kopije", "Restore from backup"))
        win.transient(self.root)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        self.lbl(b, T("Vraćanje iz rezervne kopije", "Restore from backup"), 15, "bold").pack(anchor="w")
        self.lbl(b, T("Izaberi kopiju. Trenutni podaci se pre vraćanja sami sačuvaju kao nova kopija, pa se ništa ne gubi.\n"
                      "Novi računar? Uključi USB (ili otvori OneDrive / Google Drive) i klikni „Potraži na USB-u…“.",
                      "Choose a backup. The current data is first saved as a new backup, so nothing is lost.\n"
                      "New computer? Plug in the USB stick (or open OneDrive / Google Drive) and click \"Search USB…\"."),
                 9, fg=INK2, wraplength=600, justify="left").pack(anchor="w", pady=(2, 10))
        wrap, tv = self.tabela(b, [("kad", T("Datum i vreme", "Date and time"), 150), ("vrsta", T("Vrsta", "Type"), 140),
                                   ("grla", T("Grla", "Animals"), 60, "e"), ("gde", T("Lokacija", "Location"), 200)], visina=12, tree=False)
        wrap.pack(fill="both", expand=True)
        prazno = self.lbl(b, "", 9, fg=WARN, wraplength=600, justify="left")
        prazno.pack(anchor="w", pady=(6, 0))
        st = {"kopije": []}

        def popuni(dodatni=None):
            st["kopije"] = self.spisak_kopija(dodatni)
            tv.delete(*tv.get_children())
            for i, k in enumerate(st["kopije"]):
                tv.insert("", "end", iid=str(i), values=(
                    datetime.fromtimestamp(k["vreme"]).strftime(T("%d.%m.%Y. %H:%M", "%d/%m/%Y %H:%M")),
                    T("ručna", "manual") if k["vrsta"] == "rucne" else T("automatska (dnevna)", "automatic (daily)"),
                    k["grla"], k["gde"]), tags=["odd"] if i % 2 else [])
            if st["kopije"]:
                tv.selection_set("0")
                prazno.config(text="")
            else:
                prazno.config(text=T("Nema pronađenih kopija.", "No backups found.") + (
                    "" if dodatni else T(" Ako su na USB-u ili OneDrive-u, klikni „Potraži na USB-u…“.",
                                         " If they are on a USB stick or OneDrive, click \"Search USB…\".")))

        def potrazi():
            d = filedialog.askdirectory(parent=win, title=T("Izaberi USB ili folder sa kopijama", "Choose the USB stick or folder with backups"))
            if d:
                popuni(os.path.normpath(d))
                if not st["kopije"]:
                    prazno.config(text=T(f"U folderu {d} nema kopija Farmera.", f"No Farmer backups in {d}."))

        def vrati():
            sel = tv.selection()
            if not sel:
                return
            k = st["kopije"][int(sel[0])]
            kad = datetime.fromtimestamp(k["vreme"]).strftime(T("%d.%m.%Y. %H:%M", "%d/%m/%Y %H:%M"))
            if not messagebox.askyesno(T("Vraćanje iz kopije", "Restore from backup"),
                                       T(f"Vratiti podatke iz kopije od {kad} ({k['grla']} grla)?\n\n"
                                         "Trenutni podaci biće prvo sačuvani kao nova ručna kopija.",
                                         f"Restore data from the backup of {kad} ({k['grla']} animals)?\n\n"
                                         "The current data will first be saved as a new manual backup."), parent=win):
                return
            self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0],
                                datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + T("_pre_vracanja", "_before_restore"), tiho=False)
            try:
                folder = os.path.dirname(os.path.abspath(self.tab.putanja))
                for ime in os.listdir(k["put"]):
                    izvor = os.path.join(k["put"], ime)
                    if os.path.isfile(izvor) and ime.lower().endswith(".csv"):
                        shutil.copy2(izvor, os.path.join(folder, ime))
                self.tab = Tablica(os.path.join(folder, os.path.basename(k["tab"])))
                self.ist = Istorija(self.tab.putanja)
                self.pods = Podsetnici(self.tab.putanja)
            except Exception as e:
                messagebox.showerror(T("Vraćanje nije uspelo", "Restore failed"), str(e), parent=win)
                return
            self.model = Model(self.tab.redovi)
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            if hasattr(self, "osvezi_fajl_label"):
                self.osvezi_fajl_label()
            self.prikazi(self.strana)
            self.toast(T(f"Vraćeni podaci iz kopije od {kad}.", f"Data restored from the backup of {kad}."))

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(14, 0))
        self.btn(fb, T("Vrati izabranu kopiju", "Restore selected backup"), vrati, "Primary").pack(side="right")
        self.btn(fb, T("Otkaži", "Cancel"), win.destroy).pack(side="right", padx=8)
        self.btn(fb, T("Potraži na USB-u…", "Search USB…"), potrazi).pack(side="left")
        self.btn(fb, T("Otvori folder", "Open folder"), lambda: self.otvori_folder(self.folder_kopija())).pack(side="left", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        popuni()
        self.postavi_prozor(win, None)

    def kartica_kopija(self, body):
        o, c = self.card(body)
        o.pack(fill="x")
        lev = tk.Frame(c, bg=SURF)
        lev.pack(fill="x")
        self.lbl(lev, T("Rezervne kopije", "Backups"), 13, "bold").pack(anchor="w")
        kad = self._kad(self.pod.get("poslednja_kopija", "")) or T("još nije napravljena", "not made yet")
        self.lbl(lev, T(f"Program svaki dan sam pravi kopiju i čuva poslednjih 30. Poslednja kopija: {kad}.",
                        f"The program makes a backup every day and keeps the last 30. Last backup: {kad}."), 9,
                 fg=INK2, wraplength=620, justify="left").pack(anchor="w")
        st = self.druga_lokacija_stanje()
        d2 = self.pod.get("kopija2", "")
        kad2 = self._kad(self.pod.get("poslednja_kopija2", "")) or T("još nije", "not yet")
        if st == "ok":
            tekst, boja = T(f"✓ Druga lokacija: {d2}  ·  poslednja kopija tamo: {kad2}", f"✓ Second location: {d2}  ·  last copy there: {kad2}"), OK
        elif st == "nedostupna":
            tekst, boja = T(f"Druga lokacija nije dostupna: {d2} (USB nije uključen?)  ·  poslednja kopija tamo: {kad2}",
                            f"Second location not available: {d2} (USB not plugged in?)  ·  last copy there: {kad2}"), WARN
        else:
            tekst, boja = T("Kopije su samo na ovom računaru. Izaberi drugu lokaciju (OneDrive, Google Drive ili USB) – ako se računar pokvari, kopija ostaje.",
                            "Backups are only on this computer. Choose a second location (OneDrive, Google Drive or USB) – if the computer breaks, the backup remains."), WARN
        self.lbl(lev, tekst, 9, "bold" if st != "ok" else "normal", fg=boja, wraplength=620, justify="left").pack(anchor="w", pady=(4, 0))
        dd = tk.Frame(c, bg=SURF)
        dd.pack(fill="x", pady=(10, 0))
        self.btn(dd, T("Napravi kopiju sada", "Make backup now"), lambda: (self.napravi_kopiju(self._RUCNE[1] if EN else self._RUCNE[0], tiho=False),
                                                                          self.toast(T("Rezervna kopija je napravljena.", "Backup has been made.")),
                                                                          self.prikazi("pregled")), "Primary").pack(side="left")
        self.btn(dd, T("Vrati iz kopije…", "Restore from backup…"), self.vrati_iz_kopije).pack(side="left", padx=8)
        self.btn(dd, T("Druga lokacija…", "Second location…") if st != "nema" else T("Izaberi drugu lokaciju…", "Choose second location…"),
                 self.izaberi_drugu_lokaciju, "Secondary" if st != "nema" else "Primary").pack(side="left")
        self.btn(dd, T("Otvori folder", "Open folder"), lambda: self.otvori_folder(self.folder_kopija())).pack(side="left", padx=8)

    # ================================================================ TER
    def ciklus_tera(self, vrsta):
        return TER_CIKLUS.get(vrsta_norm(vrsta or ""), 21)

    def tera_se(self, z):
        """Posle parenja ženka se ponovo tera – parenje nije uspelo; nudi se novo parenje."""
        majka, otac = self.roditelji_parenja(z)
        z["ter"] = "da"
        z["ishod"] = "neuspelo"
        if majka:
            self.ist.dodaj(majka, TER, (f"In heat again – mating of {z['datum']} failed" if EN else f"Ponovo se tera – parenje od {z['datum']} nije uspelo"))
        self.promena((f"{majka or '?'}: mating of {z['datum']} marked as failed (in heat again)." if EN else f"{majka or '?'}: parenje od {z['datum']} označeno kao neuspelo (ponovo se tera)."))
        self.posle_obavestenja()
        if majka and majka in self.model.A:
            self.dogadjaj_forma(majka, preset={"dogadjaj": PARENJE, "partner": otac or ""})

    def ne_tera_se(self, z):
        z["ter"] = "ne"
        self.promena(("Recorded: not in heat – probably pregnant." if EN else "Zabeleženo: ne tera se – verovatno je gravidna."))
        self.posle_obavestenja()

    def posle_novog_zapisa(self, nz):
        """Zajedničko posle svakog ručno upisanog događaja."""
        self.zatvori_stara_parenja(nz)
        if nz.get("dogadjaj") == TER:
            for z in self.cekaju_porodjaj(nz["grlo"]):
                majka, _ = self.roditelji_parenja(z)
                if majka == nz["grlo"] and (parsiraj_datum(z["datum"]) or date.min) < (parsiraj_datum(nz["datum"]) or date.max):
                    z["ishod"] = "neuspelo"
                    z["ter"] = "da"
                    self.ist.dodaj(majka, AUTO, (f"Mating of {z['datum']} marked as failed (the female is in heat again)" if EN else f"Parenje od {z['datum']} označeno kao neuspelo (ženka se ponovo tera)"),
                                   datum=nz["datum"], automatski=True)

    def obavestenja_ter(self, x=None):
        danas = date.today()
        rez = []
        # posle parenja: proveriti ter
        for z in self.cekaju_porodjaj():
            if z.get("ter"):
                continue
            majka, otac = self.roditelji_parenja(z)
            if x is not None and x != majka:
                continue
            dp = parsiraj_datum(z["datum"])
            if not dp or majka not in self.model.A:
                continue
            c = self.ciklus_tera(self.model.A[majka]["vrsta"])
            ds = (danas - dp).days
            if c - 3 <= ds <= c + 7:
                kad = dp + timedelta(days=c)
                rez.append(dict(nivo=1, grlo=majka, naslov=(f"Check for heat – day {ds} after mating" if EN else f"Proveri ter – {ds}. dan od parenja"),
                                opis=(f"Mated {z['datum']} with {otac or '?'}. If she is not in heat around {kad.strftime('%d/%m')} "
                                     f"(cycle {c} d.), she is probably pregnant." if EN else f"Pareno {z['datum']} sa {otac or '?'}. Ako se ne tera oko {kad.strftime('%d.%m.')} "
                                     f"(ciklus {c} d.), verovatno je gravidna."),
                                datum=kad, akcije=[(("Not in heat" if EN else "Ne tera se"), lambda z=z: self.ne_tera_se(z), "Primary"),
                                                   (("In heat" if EN else "Tera se"), lambda z=z: self.tera_se(z), "Secondary")]))
        # ženke koje nisu gravidne: sledeći ter iz poslednjeg zabeleženog tera
        poslednji = {}
        for z in self.ist.zapisi:
            if z["dogadjaj"] == TER and not z["automatski"]:
                d = parsiraj_datum(z["datum"])
                if d and (z["grlo"] not in poslednji or d > poslednji[z["grlo"]]):
                    poslednji[z["grlo"]] = d
        gravidne = {self.roditelji_parenja(z)[0] for z in self.cekaju_porodjaj()}
        for g, d in poslednji.items():
            if (x is not None and x != g) or g in gravidne or g not in self.model.A or not self.model.A[g]["aktivno"]:
                continue
            if any(z["dogadjaj"] == PARENJE and self.roditelji_parenja(z)[0] == g and
                   (parsiraj_datum(z["datum"]) or date.min) >= d for z in self.ist.zapisi):
                continue
            c = self.ciklus_tera(self.model.A[g]["vrsta"])
            sl = d + timedelta(days=c)
            while sl < danas - timedelta(days=2):
                sl += timedelta(days=c)
            if (sl - danas).days <= 3:
                rez.append(dict(nivo=2 if sl > danas else 1, grlo=g,
                                naslov=("Heat expected " if EN else "Očekuje se ter ") + (("today" if EN else "danas") if sl == danas else (f"around {sl.strftime('%d/%m')}" if EN else f"oko {sl.strftime('%d.%m.')}")),
                                opis=(f"Last heat {d.strftime('%d/%m/%Y')} · cycle {c} days. Watch whether she comes into heat." if EN else f"Poslednji ter {d.strftime('%d.%m.%Y')} · ciklus {c} dana. Prati da li se tera."),
                                datum=sl, akcije=[(("Record mating" if EN else "Upiši parenje"), lambda g=g: self.dogadjaj_forma(
                                    g, preset={"dogadjaj": PARENJE}), "Primary"),
                                                  (("In heat" if EN else "Tera se"), lambda g=g: self.dogadjaj_forma(
                                                      g, preset={"dogadjaj": TER}), "Secondary")]))
        return rez

    # ================================================================ KARENCA
    def karenca(self, x):
        """{'meso': (do_datum, zapis), 'mleko': (...)} – samo karence koje još traju."""
        danas = date.today()
        rez = {}
        for z in self.ist.zapisi:
            if z["grlo"] != x:
                continue
            d = parsiraj_datum(z["datum"])
            if not d:
                continue
            for vrsta, kljuc in (("meso", "karenca_meso"), ("mleko", "karenca_mleko")):
                try:
                    n = int(z.get(kljuc) or 0)
                except ValueError:
                    n = 0
                if n > 0:
                    do = d + timedelta(days=n)
                    if do >= danas and (vrsta not in rez or do > rez[vrsta][0]):
                        rez[vrsta] = (do, z)
        return rez

    def opis_karence(self, x, kratko=False):
        k = self.karenca(x)
        if not k:
            return ""
        delovi = []
        for vrsta in ("meso", "mleko"):
            if vrsta in k:
                do = k[vrsta][0]
                ost = (do - date.today()).days
                delovi.append((f"{dict(meso='meat', mleko='milk')[vrsta]} until {do.strftime('%d/%m')}" if EN else f"{vrsta} do {do.strftime('%d.%m.')}") + ("" if kratko else (f" ({ost} d. left)" if EN else f" (još {ost} d.)")))
        return ", ".join(delovi)

    def obavestenja_karenca(self, x=None):
        rez = []
        for a in self.model.grla(True):
            if x is not None and a["id"] != x:
                continue
            k = self.karenca(a["id"])
            if not k:
                continue
            z = max(k.values(), key=lambda t: t[0])[1]
            rez.append(dict(nivo=2, grlo=a["id"], naslov=("Withdrawal – " if EN else "Karenca – ") + self.opis_karence(a["id"]),
                            opis=(f"After: {z['dogadjaj'].lower()} {z['datum']}" if EN else f"Posle: {z['dogadjaj'].lower()} {z['datum']}") + (f" ({z['vrednost']})" if z["vrednost"] else "")
                                 + (". Do not sell for slaughter / do not deliver milk while the withdrawal period lasts." if EN else ". Ne prodavati za klanje / ne isporučivati mleko dok karenca traje."),
                            datum=min(t[0] for t in k.values()), akcije=[]))
        return rez

    def okvir_karence(self, parent, vars_, vrednosti=("", "")):
        """Dva polja za karencu (meso, mleko) – za lečenje i vakcinaciju."""
        f = tk.Frame(parent, bg=SURF)
        for i, (naslov, kljuc, v0) in enumerate(((("Meat withdrawal (days)" if EN else "Karenca meso (dana)"), "karenca_meso", vrednosti[0]),
                                                (("milk (days)" if EN else "mleko (dana)"), "karenca_mleko", vrednosti[1]))):
            ff = tk.Frame(f, bg=SURF)
            ff.pack(side="left", padx=(0 if i == 0 else 8, 0))
            self.lbl(ff, naslov, 9, "bold", fg=BAD).pack(anchor="w")
            v = tk.StringVar(value=v0)
            ttk.Entry(ff, textvariable=v, width=7, font=self.f(10)).pack(anchor="w", pady=(3, 0))
            vars_[kljuc] = v
        return f

    @staticmethod
    def broj_dana(v):
        t = "".join(ch for ch in str(v or "") if ch.isdigit())
        return t if t and int(t) > 0 else ""

    # ================================================================ PLODNOST
    def plodnost(self, x):
        import re
        por = sorted((z for z in self.ist.zapisi if z["grlo"] == x and z["dogadjaj"] == ("Birth" if EN else "Porođaj")),
                     key=lambda z: parsiraj_datum(z["datum"]) or date.min)
        zivih = mrtvih = 0
        for z in por:
            v = "".join(ch for ch in z.get("vrednost", "") if ch.isdigit())
            zivih += int(v) if v else 1
            mm = re.search((r"stillborn:\s*(\d+)" if EN else r"mrtvorođenih:\s*(\d+)"), z.get("opis", ""))
            mrtvih += int(mm.group(1)) if mm else 0
        datumi = [parsiraj_datum(z["datum"]) for z in por if parsiraj_datum(z["datum"])]
        razmaci = [(b - a).days for a, b in zip(datumi, datumi[1:]) if (b - a).days > 20]
        parenja = [z for z in self.ist.zapisi if z["dogadjaj"] == PARENJE and not z["automatski"]
                   and self.roditelji_parenja(z)[0] == x]
        neuspela = sum(1 for z in parenja if z.get("ishod") == "neuspelo")
        a = self.model.A.get(x, {})
        prvi = None
        if datumi and a.get("datum"):
            prvi = (datumi[0].year - a["datum"].year) * 12 + datumi[0].month - a["datum"].month
        potomaka = sum(1 for pr in self.model.P.values() if x in pr)
        return dict(porodjaja=len(por), zivih=zivih, mrtvih=mrtvih,
                    prosek=(zivih / len(por)) if por else 0,
                    razmak=(sum(razmaci) / len(razmaci)) if razmaci else None,
                    parenja=len(parenja), neuspela=neuspela,
                    po_gravidnosti=(len(parenja) / len(por)) if por and len(parenja) >= len(por) else None,
                    prvi_mes=prvi, potomaka=potomaka, poslednji=datumi[-1] if datumi else None)

    def kartica_plodnosti(self, body):
        m = self.model
        redovi = []
        for a in m.grla(True):
            if a["pol"] != "z":
                continue
            p = self.plodnost(a["id"])
            if p["porodjaja"] or p["parenja"]:
                redovi.append((a, p))
        o, c = self.card(body)
        o.pack(fill="x")
        self.lbl(c, ("Female fertility" if EN else "Plodnost ženki"), 13, "bold").pack(anchor="w")
        self.lbl(c, ("Sorted by young per birth. Helps you choose which females to keep for breeding." if EN else "Poređano po broju mladih po porođaju. Pomaže da izabereš koje ženke zadržati za priplod."), 9,
                 fg=INK2).pack(anchor="w", pady=(0, 10))
        if not redovi:
            self.lbl(c, ("No matings or births recorded yet." if EN else "Još nema upisanih parenja ni porođaja."), 10, fg=INK2).pack(anchor="w")
            return
        redovi.sort(key=lambda t: (-t[1]["prosek"], -t[1]["porodjaja"]))
        wrap, tv = self.tabela(c, [("id", ("Female" if EN else "Ženka"), 95), ("rasa", ("Breed" if EN else "Rasa"), 100), ("por", ("Births" if EN else "Porođaja"), 80, "e"),
                                   ("ziv", ("Alive" if EN else "Živih"), 60, "e"), ("pros", ("Average" if EN else "Prosek"), 70, "e"),
                                   ("mrt", ("Stillborn" if EN else "Mrtvih"), 65, "e"), ("raz", ("Interval (d.)" if EN else "Razmak (d.)"), 90, "e"),
                                   ("par", ("Matings/birth" if EN else "Parenja/porođ."), 105, "e"), ("pos", ("Last" if EN else "Poslednji"), 95)],
                               visina=min(10, len(redovi)))
        wrap.pack(fill="x")
        if EN:
            for i, (a, p) in enumerate(redovi):
                tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag, values=(
                    a["rasa"] or "–", p["porodjaja"], p["zivih"], f"{p['prosek']:.1f}" if p["porodjaja"] else "–",
                    p["mrtvih"] or "–", round(p["razmak"]) if p["razmak"] else "–",
                    f"{p['po_gravidnosti']:.1f}" if p["po_gravidnosti"] else "–",
                    p["poslednji"].strftime("%d/%m/%Y") if p["poslednji"] else "–"), tags=["odd"] if i % 2 else [])
        else:
            for i, (a, p) in enumerate(redovi):
                tv.insert("", "end", iid=a["id"], text="  " + a["id"], image=self.img_tag, values=(
                    a["rasa"] or "–", p["porodjaja"], p["zivih"], f"{p['prosek']:.1f}".replace(".", ",") if p["porodjaja"] else "–",
                    p["mrtvih"] or "–", round(p["razmak"]) if p["razmak"] else "–",
                    f"{p['po_gravidnosti']:.1f}".replace(".", ",") if p["po_gravidnosti"] else "–",
                    p["poslednji"].strftime("%d.%m.%Y") if p["poslednji"] else "–"), tags=["odd"] if i % 2 else [])
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))

    # ---------- obaveštenja i podsetnici
    def obavestenja(self, x=None):
        """Sva obaveštenja: [{nivo, grlo, naslov, opis, kljuc, akcije:[(tekst, fn, stil)]}]. nivo: 0 hitno, 1 uskoro, 2 info, 3 zakazano."""
        m = self.model
        danas = date.today()
        rez = []
        # 1) porođaji
        for z in self.cekaju_porodjaj():
            majka, otac = self.roditelji_parenja(z)
            if x is not None and x not in (majka, otac, z["grlo"]):
                continue
            oc, od = self.ocekivani_porodjaj(z), self.upis_moguc_od(z)
            if not oc:
                continue
            dana = (oc - danas).days
            dk = self.najkasniji_porodjaj(z)
            par = (f"{majka or '?'} × {otac or '?'}, mated {z['datum']}" if EN else f"{majka or '?'} × {otac or '?'}, pareno {z['datum']}")
            akc = [(("Young born" if EN else "Dobijeni mladi"), lambda z=z: self.upis_podmlatka(z), "Primary"),
                   (("Failed" if EN else "Nije uspelo"), lambda z=z: self.oznaci_neuspelo(z), "Secondary")]
            if dk and danas > dk:
                rez.append(dict(nivo=0, grlo=majka, naslov=(f"Due date passed {(danas - dk).days} d. ago" if EN else f"Termin porođaja je prošao pre {(danas - dk).days} d."),
                                opis=(f"Latest {dk.strftime('%d/%m/%Y')} · {par}. Enter the young or mark the mating as failed." if EN else f"Najkasnije {dk.strftime('%d.%m.%Y')} · {par}. Upiši mlade ili označi da parenje nije uspelo."),
                                datum=dk, akcije=akc))
            elif od and danas >= od:
                rez.append(dict(nivo=1, grlo=majka, naslov=("Birth expected " if EN else "Porođaj se očekuje ") +
                                (("today" if EN else "danas") if dana == 0 else (f"in {dana} d." if EN else f"za {dana} d.") if dana > 0 else ("any day now" if EN else "svakog dana")),
                                opis=(f"Around {oc.strftime('%d/%m/%Y')}, latest {dk.strftime('%d/%m/%Y')} · {par}. "
                                     "Entering young is open." if EN else f"Oko {oc.strftime('%d.%m.%Y')}, najkasnije {dk.strftime('%d.%m.%Y')} · {par}. "
                                     "Upis mladih je otvoren."),
                                datum=oc, akcije=akc))
            elif dana <= 21:
                rez.append(dict(nivo=2, grlo=majka, naslov=(f"Birth in {dana} d." if EN else f"Porođaj za {dana} d."),
                                opis=(f"Due {oc.strftime('%d/%m/%Y')} · {par}. Prepare the birthing area." if EN else f"Termin {oc.strftime('%d.%m.%Y')} · {par}. Pripremi prostor za porođaj."),
                                datum=oc, akcije=[]))
        # 2) mladi čekaju minđušu
        for z in self.cekaju_mindjusu(x):
            uk, dd, vec = self.leglo(z)
            majka, otac = self.roditelji_parenja(z)
            dr = parsiraj_datum(dd)
            star = (danas - dr).days if dr else 0
            n_ = nazivi(self.vrsta_parenja(z))
            rez.append(dict(nivo=1 if star >= 14 else 2, grlo=majka,
                            naslov=(f"{uk - len(vec)} {n_[3]} waiting for ear tag ({star} d.)" if EN else f"{uk - len(vec)} {n_[3]} čeka minđušu ({star} d.)"),
                            opis=(f"Born {dd} · {majka or '?'} × {otac or '?'}. Enter them in the animal list when they get their ear tags." if EN else f"Rođeno {dd} · {majka or '?'} × {otac or '?'}. Upiši ih u listu grla kad dobiju minđušu."),
                            datum=dr, akcije=[(("Enter in list" if EN else "Upiši u listu"), lambda z=z: self.upis_u_listu(z), "Primary"),
                                              (("Remove…" if EN else "Ukloni…"), lambda z=z: self.ukloni_iz_legla(z), "Secondary")]))
        # 3) podsetnici
        for p in self.pods.aktivni(x):
            d = parsiraj_datum(p["datum"]) or danas
            dana = (d - danas).days
            nivo = 0 if dana < 0 else 1 if dana <= 3 else 3
            kad = ((f"{-dana} d. overdue" if EN else f"zakasnelo {-dana} d.") if dana < 0 else ("today" if EN else "danas") if dana == 0 else
                   ("tomorrow" if EN else "sutra") if dana == 1 else (f"in {dana} d." if EN else f"za {dana} d."))
            pon = int(p.get("ponavljanje") or 0)
            rez.append(dict(nivo=nivo, grlo=p["grlo"] or None, naslov=(f"{p['tip'] or 'Reminder'} – {kad}" if EN else f"{p['tip'] or 'Podsetnik'} – {kad}"),
                            opis=f"{p['datum']}" + (f" · {p['tekst']}" if p["tekst"] else "") +
                                 ((f" · repeats every {pon} d." if EN else f" · ponavlja se na {pon} d.") if pon else ""),
                            datum=d, podsetnik=p,
                            akcije=[(("Done" if EN else "Urađeno"), lambda p=p: self.podsetnik_uradjen(p), "Primary"),
                                    (("Postpone 7 d." if EN else "Odloži 7 d."), lambda p=p: self.podsetnik_odlozi(p, 7), "Secondary"),
                                    (("Edit" if EN else "Izmeni"), lambda p=p: self.podsetnik_forma(zapis=p), "Secondary")]))
        # 4) ter i karenca
        rez += self.obavestenja_ter(x)
        rez += self.obavestenja_karenca(x)
        # 5) greške u podacima
        if x is None and m.warn:
            rez.append(dict(nivo=2, grlo=None, naslov=(f"{len(m.warn)} warnings in the data" if EN else f"{len(m.warn)} upozorenja u podacima"),
                            opis=("The program found possible errors in the pedigree (e.g. wrong sex of a parent or a date)." if EN else "Program je našao moguće greške u rodoslovu (npr. pogrešan pol roditelja ili datum)."),
                            datum=None, akcije=[(("Show" if EN else "Prikaži"), lambda: self.prikazi("pregled"), "Secondary")]))
        rez.sort(key=lambda o: (o["nivo"], o["datum"] or date.max))
        return rez

    def broj_obavestenja(self):
        try:
            return sum(1 for o in self.obavestenja() if o["nivo"] <= 1)
        except Exception:
            return 0

    def osvezi_nav_brojac(self):
        if "obavestenja" not in self.nav:
            return
        n = self.broj_obavestenja()
        row, li, lt = self.nav["obavestenja"]
        lt.config(text=("Notifications" if EN else "Obaveštenja") + (f"  ({n})" if n else ""))
        li.config(fg=BAD if n else (BRAND if self.strana == "obavestenja" else INK2))

    def red_obavestenja(self, parent, o, bg=SURF, kompakt=False):
        boje = {0: (BAD, BAD_BG, ("Urgent" if EN else "Hitno")), 1: (WARN, WARN_BG, ("Soon" if EN else "Uskoro")), 2: (BRAND, SURF2, "Info"),
                3: (INK2, SURF2, ("Scheduled" if EN else "Zakazano"))}
        fg, bgb, txt = boje[o["nivo"]]
        r = tk.Frame(parent, bg=bg)
        r.pack(fill="x", pady=4)
        tk.Frame(r, bg=fg, width=4).pack(side="left", fill="y", padx=(0, 12))
        lev = tk.Frame(r, bg=bg)
        lev.pack(side="left", fill="x", expand=True)
        gornji = tk.Frame(lev, bg=bg)
        gornji.pack(anchor="w")
        if not kompakt:
            tk.Label(gornji, text=f" {txt} ", font=self.f(8, "bold"), bg=bgb, fg=fg).pack(side="left", padx=(0, 8))
        if o["grlo"] and not kompakt:
            self.cip(gornji, o["grlo"], lambda g=o["grlo"]: self.karton(g), bg=bg,
                     siv=o["grlo"] not in self.model.A or self.model.A[o["grlo"]]["osnivac"]).pack(side="left", padx=(0, 8))
        self.lbl(gornji, o["naslov"], 10, "bold", fg=fg if o["nivo"] == 0 else INK, bg=bg).pack(side="left")
        self.lbl(lev, o["opis"], 9, fg=INK2, bg=bg, wraplength=380 if kompakt else 560,
                 justify="left").pack(anchor="w", pady=(2, 0))
        if kompakt:
            if o["akcije"]:
                ak = tk.Frame(lev, bg=bg)
                ak.pack(anchor="w", pady=(3, 0))
                for t, fn, stil in o["akcije"][:2]:
                    lk = self.lbl(ak, t, 9, "bold", fg=BRAND, bg=bg, cursor="hand2")
                    lk.pack(side="left", padx=(0, 14))
                    lk.bind("<Button-1>", lambda e, fn=fn: fn())
            return r
        if o["akcije"]:
            dd = tk.Frame(r, bg=bg)
            dd.pack(side="right", padx=(10, 0))
            for t, fn, stil in reversed(o["akcije"] if not kompakt else o["akcije"][:1]):
                self.btn(dd, t, fn, stil).pack(side="right", padx=(6, 0))
        return r

    def s_obavestenja(self):
        body = self.strana_okvir()
        sva = self.obavestenja()
        aktivna = [o for o in sva if o["nivo"] <= 2]
        zakazano = [o for o in sva if o["nivo"] == 3]
        n = sum(1 for o in sva if o["nivo"] <= 1)
        self.zaglavlje(body, ("Notifications" if EN else "Obaveštenja"),
                       ((f"{n} {'thing needs' if n == 1 else 'things need'} attention." if EN else f"{n} {'stvar traži' if n == 1 else 'stvari traže'} pažnju.") if n else
                        ("Nothing urgent." if EN else "Nema ničeg hitnog.")) + (" The program tracks births, heat, withdrawal periods, untagged young and reminders." if EN else " Program sam prati porođaje, ter, karencu, mlade bez minđuše i podsetnike."),
                       [(("+  New reminder" if EN else "+  Novi podsetnik"), lambda: self.podsetnik_forma(), "Primary")])
        if not aktivna and not zakazano:
            self.napomena(body, ("All is well – no notifications. Add a reminder for an animal (vaccination, "
                                "treatment, sale…) with the \"New reminder\" button." if EN else "Sve je u redu – nema obaveštenja. Dodaj podsetnik za grlo (vakcinacija, "
                                "lečenje, prodaja…) dugmetom „Novi podsetnik“."), ok=True)
            return
        for nivo, naslov in ((0, ("Urgent" if EN else "Hitno")), (1, ("Soon" if EN else "Uskoro")), (2, ("For information" if EN else "Za informaciju"))):
            grupa = [o for o in aktivna if o["nivo"] == nivo]
            if not grupa:
                continue
            o_, c_ = self.card(body, 18, 12)
            o_.pack(fill="x", pady=(0, 14))
            self.lbl(c_, f"{naslov} ({len(grupa)})", 12, "bold", fg=BAD if nivo == 0 else INK).pack(anchor="w", pady=(0, 4))
            for o in grupa:
                self.red_obavestenja(c_, o)
        if zakazano:
            o_, c_ = self.card(body, 18, 12)
            o_.pack(fill="x", pady=(0, 14))
            self.lbl(c_, (f"Scheduled reminders ({len(zakazano)})" if EN else f"Zakazani podsetnici ({len(zakazano)})"), 12, "bold").pack(anchor="w", pady=(0, 4))
            for o in zakazano:
                self.red_obavestenja(c_, o)

    def obavestenja_na_startu(self):
        sva = [o for o in self.obavestenja() if o["nivo"] <= 1]
        if not sva:
            return
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Notifications" if EN else "Obaveštenja"))
        win.transient(self.root)
        win.resizable(False, False)
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=24, pady=20)
        h = sum(1 for o in sva if o["nivo"] == 0)
        self.lbl(b, (f"You have {len(sva)} notifications" if EN else f"Imaš {len(sva)} obaveštenja"), 15, "bold").pack(anchor="w")
        self.lbl(b, ((f"{h} urgent · " if EN else f"{h} hitno · ") if h else "") + (f"{len(sva) - h} soon" if EN else f"{len(sva) - h} uskoro"), 9, fg=BAD if h else INK2).pack(anchor="w", pady=(2, 10))
        for o in sva[:5]:
            r = tk.Frame(b, bg=SURF)
            r.pack(fill="x", pady=3)
            tk.Frame(r, bg=BAD if o["nivo"] == 0 else WARN, width=4, height=34).pack(side="left", padx=(0, 10))
            if o["grlo"]:
                self.cip(r, o["grlo"]).pack(side="left", padx=(0, 8))
            self.lbl(r, o["naslov"], 10, "bold").pack(side="left")
        if len(sva) > 5:
            self.lbl(b, (f"… and {len(sva) - 5} more" if EN else f"… i još {len(sva) - 5}"), 9, fg=INK2).pack(anchor="w", pady=(4, 0))
        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        self.btn(fb, ("Open notifications" if EN else "Otvori obaveštenja"), lambda: (win.destroy(), self.prikazi("obavestenja")), "Primary").pack(side="right")
        self.btn(fb, ("Later" if EN else "Kasnije"), win.destroy).pack(side="right", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, None)

    def podsetnik_uradjen(self, p):
        d = date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
        p["gotovo"] = d
        if p["grlo"]:
            tip = p["tip"] if p["tip"] in DOGADJAJI else ("Note" if EN else "Napomena")
            self.ist.dodaj(p["grlo"], tip, (p["tip"] + ": " if tip == ("Note" if EN else "Napomena") and p["tip"] not in ("", ("Note" if EN else "Napomena"))
                                            else "") + (p["tekst"] or ("done as reminded" if EN else "urađeno po podsetniku")), datum=d)
        pon = int(p.get("ponavljanje") or 0)
        if pon:
            sl = (parsiraj_datum(p["datum"]) or date.today()) + timedelta(days=pon)
            while sl <= date.today():
                sl += timedelta(days=pon)
            self.pods.dodaj(p["grlo"], sl.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), p["tip"], p["tekst"], pon)
        self.promena((f"Done: {p['tip'] or 'reminder'}" if EN else f"Urađeno: {p['tip'] or 'podsetnik'}") + (f" – {p['grlo']}" if p["grlo"] else "") +
                     ((" · the next one is scheduled" if EN else " · sledeći je zakazan") if pon else ""))
        self.posle_obavestenja()

    def podsetnik_odlozi(self, p, dana):
        d = max(parsiraj_datum(p["datum"]) or date.today(), date.today()) + timedelta(days=dana)
        p["datum"] = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))
        self.promena((f"Reminder postponed to {p['datum']}" if EN else f"Podsetnik odložen za {p['datum']}"))
        self.posle_obavestenja()

    def posle_obavestenja(self):
        self.osvezi_nav_brojac()
        if getattr(self, "ist_win", None) and self.ist_win.winfo_exists() and getattr(self.ist_win, "grlo", None):
            self.istorija_prozor(self.ist_win.grlo)
        if self.karton_win and self.karton_win.winfo_exists() and getattr(self.karton_win, "grlo", None):
            self.karton(self.karton_win.grlo)

    def podsetnik_forma(self, grlo=None, zapis=None, parent=None):
        m = self.model
        z = zapis or {}
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Edit reminder" if EN else "Izmena podsetnika") if zapis else ("New reminder" if EN else "Novi podsetnik"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Edit reminder" if EN else "Izmena podsetnika") if zapis else ("New reminder" if EN else "Novi podsetnik"), 16, "bold").pack(anchor="w")
        self.lbl(b, ("The program will notify you when the day comes (and 3 days before)." if EN else "Program će te obavestiti kad dođe dan (i 3 dana pre toga)."), 9, fg=INK2).pack(anchor="w", pady=(2, 10))
        g = tk.Frame(b, bg=SURF)
        g.pack(fill="x")
        gv = tk.StringVar(value=z.get("grlo") or grlo or "")
        dv = tk.StringVar(value=z.get("datum") or (date.today() + timedelta(days=7)).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        f = tk.Frame(g, bg=SURF)
        f.grid(row=0, column=0, sticky="w", padx=(0, 16))
        self.lbl(f, ("Animal (empty = whole herd)" if EN else "Grlo (prazno = celo stado)"), 9, "bold", fg=INK2).pack(anchor="w")
        ttk.Combobox(f, textvariable=gv, values=[a["id"] for a in m.grla()], width=18, font=self.f(10)).pack(anchor="w", pady=(3, 0))
        f = tk.Frame(g, bg=SURF)
        f.grid(row=0, column=1, sticky="w")
        self.lbl(f, ("Date" if EN else "Datum"), 9, "bold", fg=INK2).pack(anchor="w")
        de = tk.Frame(f, bg=SURF)
        de.pack(anchor="w", pady=(3, 0))
        ttk.Entry(de, textvariable=dv, width=12, font=self.f(10)).pack(side="left")
        for t, dn in (("+7", 7), ("+30", 30), ("+90", 90)):
            lk = self.lbl(de, t, 9, "bold", fg=BRAND, cursor="hand2")
            lk.pack(side="left", padx=(8, 0))
            lk.bind("<Button-1>", lambda e, dn=dn: dv.set((date.today() + timedelta(days=dn)).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y"))))
        self.lbl(b, ("What needs to be done" if EN else "Šta treba uraditi"), 9, "bold", fg=INK2).pack(anchor="w", pady=(12, 4))
        tv = tk.StringVar(value=z.get("tip", ("Vaccination" if EN else "Vakcinacija")))
        self.izbor_dogadjaja(b, tv, po_redu=5).pack(anchor="w")
        self.lbl(b, ("Description" if EN else "Opis"), 9, "bold", fg=INK2).pack(anchor="w", pady=(10, 3))
        xv = tk.StringVar(value=z.get("tekst", ""))
        ttk.Entry(b, textvariable=xv, width=60, font=self.f(10)).pack(anchor="w", fill="x")
        self.lbl(b, ("e.g. foot-and-mouth vaccine, check after treatment, sale to a buyer…" if EN else "npr. vakcina protiv šapa i slinavke, kontrola posle lečenja, prodaja kupcu…"), 8, fg="#8A968D").pack(anchor="w")
        pf = tk.Frame(b, bg=SURF)
        pf.pack(anchor="w", pady=(10, 0))
        self.lbl(pf, ("Repeat" if EN else "Ponavljanje"), 9, "bold", fg=INK2).pack(side="left", padx=(0, 8))
        opc = {("does not repeat" if EN else "ne ponavlja se"): 0, ("every week" if EN else "svake nedelje"): 7, ("every month" if EN else "svakog meseca"): 30, ("every 3 months" if EN else "na 3 meseca"): 90,
               ("every 6 months" if EN else "na 6 meseci"): 182, ("every year" if EN else "svake godine"): 365}
        pon0 = int(z.get("ponavljanje") or 0)
        pv = tk.StringVar(value=next((k for k, v in opc.items() if v == pon0), (f"every {pon0} days" if EN else f"svakih {pon0} dana") if pon0 else ("does not repeat" if EN else "ne ponavlja se")))
        ttk.Combobox(pf, textvariable=pv, values=list(opc), width=16, font=self.f(10)).pack(side="left")
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.pack(anchor="w", pady=(8, 0))

        def sacuvaj(ev=None):
            gr = gv.get().strip()
            if gr:
                g2 = m.nadji(gr)
                if not g2:
                    err.config(text=(f"Animal \"{gr}\" was not found." if EN else f"Grlo „{gr}“ nije pronađeno."))
                    return
                gr = g2
            d = parsiraj_datum(dv.get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            tip = tv.get().strip()
            if not tip:
                err.config(text=("Choose what needs to be done." if EN else "Izaberi šta treba uraditi."))
                return
            pt = pv.get().strip()
            if pt in opc:
                pon = opc[pt]
            else:
                cif = "".join(ch for ch in pt if ch.isdigit())
                pon = int(cif) if cif else 0
            if zapis:
                zapis.update(grlo=gr, datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), tip=tip, tekst=xv.get().strip(), ponavljanje=str(pon))
            else:
                self.pods.dodaj(gr, d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), tip, xv.get().strip(), pon)
            win.grab_release()
            win.destroy()
            self.promena((f"Reminder saved for {d.strftime('%d/%m/%Y')}" if EN else f"Podsetnik sačuvan za {d.strftime('%d.%m.%Y')}"))
            self.posle_obavestenja()

        fb = tk.Frame(b, bg=SURF)
        fb.pack(fill="x", pady=(16, 0))
        if zapis:
            def obrisi():
                if messagebox.askyesno(("Delete reminder" if EN else "Obriši podsetnik"), ("Delete this reminder?" if EN else "Obrisati ovaj podsetnik?"), parent=win):
                    self.pods.zapisi.remove(zapis)
                    win.grab_release()
                    win.destroy()
                    self.promena(("Reminder deleted." if EN else "Podsetnik obrisan."))
                    self.posle_obavestenja()
            self.btn(fb, ("Delete" if EN else "Obriši"), obrisi, "Danger").pack(side="left")
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Return>", sacuvaj)
        win.bind("<Escape>", lambda e: win.destroy())
        self.postavi_prozor(win, parent)

    def izbor_dogadjaja(self, parent, var, bg=SURF, po_redu=5):
        """Dugmad za izbor vrste događaja (+ 'Drugo…' za sopstveni naziv). Vraća okvir."""
        okvir = tk.Frame(parent, bg=bg)
        cipovi = {}
        drugo_v = tk.StringVar(value=var.get() if var.get() and var.get() not in DOGADJAJI else "")
        drugo_e = ttk.Entry(okvir, textvariable=drugo_v, width=26, font=self.f(10))
        stanje = {"drugo": bool(drugo_v.get())}

        def stil(*_):
            izbor = var.get()
            for naziv, lb in cipovi.items():
                akt = (naziv == izbor) if naziv != ("Other…" if EN else "Drugo…") else stanje["drugo"]
                lb.config(bg=BRAND if akt else SURF2, fg="#FFFFFF" if akt else INK)
            if stanje["drugo"]:
                drugo_e.grid(row=99, column=0, columnspan=po_redu, sticky="w", pady=(6, 0))
            else:
                drugo_e.grid_remove()

        def klik(naziv):
            if naziv == ("Other…" if EN else "Drugo…"):
                stanje["drugo"] = True
                var.set(drugo_v.get().strip())
                stil()
                drugo_e.focus_set()
            else:
                stanje["drugo"] = False
                var.set(naziv)
                stil()

        for i, naziv in enumerate(DOGADJAJI + [("Other…" if EN else "Drugo…")]):
            lb = tk.Label(okvir, text=naziv, font=self.f(9, "bold"), padx=10, pady=5, cursor="hand2", bg=SURF2, fg=INK)
            lb.grid(row=i // po_redu, column=i % po_redu, sticky="ew", padx=(0, 6), pady=(0, 6))
            lb.bind("<Button-1>", lambda e, n=naziv: klik(n))
            cipovi[naziv] = lb
        drugo_v.trace_add("write", lambda *_: stanje["drugo"] and var.set(drugo_v.get().strip()))
        var.trace_add("write", stil)
        ph = self.lbl(okvir, ("e.g. Castration, Weaning…" if EN else "npr. Kastracija, Odbijanje…"), 9, fg="#98A39B", bg=SURF)
        def ph_show(*_):
            if stanje["drugo"] and not drugo_v.get():
                ph.place(in_=drugo_e, x=8, rely=0.5, anchor="w")
            else:
                ph.place_forget()
        drugo_v.trace_add("write", ph_show)
        var.trace_add("write", ph_show)
        ph.bind("<Button-1>", lambda e: drugo_e.focus_set())
        stil()
        ph_show()
        return okvir

    def istorija_prozor(self, x):
        """Prozor grla: levo podaci (čitanje i izmena), desno unos novog zapisa i cela istorija."""
        m = self.model
        if x not in m.A or m.A[x]["osnivac"]:
            if x in m.A:
                self.karton(x)
            return
        if getattr(self, "ist_win", None) and self.ist_win.winfo_exists():
            win = self.ist_win
            for w in win.winfo_children():
                w.destroy()
        else:
            win = tk.Toplevel(self.root, bg=BG)
            win.geometry(f"1200x780+{self.root.winfo_rootx() + 20}+{max(0, self.root.winfo_rooty() - 10)}")
            win.minsize(1000, 640)
            win.transient(self.root)
            win.bind("<Escape>", lambda e: win.destroy())
            self.ist_win = win
        win.title((f"Animal {x} – details and history" if EN else f"Grlo {x} – podaci i istorija"))
        win.grlo = x
        a = m.A[x]
        red = self.red_za(x)

        # ---------- zaglavlje
        h = tk.Frame(win, bg=BG)
        h.pack(fill="x", padx=24, pady=(18, 12))
        self.cip(h, x, lambda: self.karton(x), big=True, bg=BG).pack(side="left")
        t = tk.Frame(h, bg=BG)
        t.pack(side="left", padx=14)
        self.lbl(t, f"{m.pol_naziv(x).capitalize()}{', ' + a['rasa'] if a['rasa'] else ''}", 15, "bold").pack(anchor="w")
        st = starost_meseci(a["datum"])
        self.lbl(t, "   ·   ".join(v for v in (
            (f"ear tag {a['markica'] or '–'}" if EN else f"markica {a['markica'] or '–'}"),
            f"{fmt_starost(st)}" if st is not None else "",
            ("in herd" if EN else "u zapatu") if a["aktivno"] else ("deleted" if EN else "obrisano") if a.get("obrisano") else ("out of herd" if EN else "van zapata"),
            (f"inbreeding {pct(m.inbr(x))}" if EN else f"inbriding {pct(m.inbr(x))}")) if v), 10, fg=INK2).pack(anchor="w")
        dd = tk.Frame(h, bg=BG)
        dd.pack(side="right")
        self.btn(dd, ("Card" if EN else "Karton"), lambda: self.karton(x)).pack(side="left", padx=(0, 8))
        self.btn(dd, ("Pedigree – tree" if EN else "Poreklo – stablo"), lambda: self.stablo(x)).pack(side="left", padx=(0, 8))
        self.btn(dd, ("Partner search" if EN else "Pretraga partnera"), lambda: (win.destroy(), self.idi_na_pretragu(x))).pack(side="left")

        telo = tk.Frame(win, bg=BG)
        telo.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # ---------- levo: podaci o grlu
        lo, lc = self.card(telo, 18, 16)
        lo.pack(side="left", fill="y", padx=(0, 16))
        self.lbl(lc, ("Animal details" if EN else "Podaci o grlu"), 13, "bold").grid(row=0, column=0, columnspan=2, sticky="w")
        self.lbl(lc, ("Edit a field and click \"Save details\"." if EN else "Izmeni polje i klikni „Sačuvaj podatke“."), 9, fg=INK2).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        sva = m.grla()
        pv = {}

        def polje(r, c, naslov, key, vrednost, vals=None, state="normal", span=1):
            f = tk.Frame(lc, bg=SURF)
            f.grid(row=r, column=c, columnspan=span, sticky="new", padx=(0 if c == 0 else 10, 0), pady=4)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            v = tk.StringVar(value=vrednost or "")
            w = (ttk.Combobox(f, textvariable=v, values=vals, state=state, width=16, font=self.f(10))
                 if vals is not None else ttk.Entry(f, textvariable=v, width=18, font=self.f(10)))
            w.pack(fill="x", pady=(3, 0))
            pv[key] = v
            return w

        n = nazivi(a["vrsta"])
        pol_opcije = {n[1].capitalize(): "z", n[0].capitalize(): "m"}
        dat = parsiraj_datum(red.get("datum_rodjenja"))
        polje(2, 0, ("Ear tag" if EN else "Ušna markica"), "markica", red.get("markica"))
        polje(2, 1, ("Breed" if EN else "Rasa"), "rasa", red.get("rasa"), sorted({g["rasa"] for g in sva if g["rasa"]}))
        polje(3, 0, ("Sex" if EN else "Pol"), "pol", next((k for k, v in pol_opcije.items() if v == red.get("pol")), ""),
              list(pol_opcije), "readonly")
        polje(3, 1, ("Date of birth" if EN else "Datum rođenja"), "datum_rodjenja", dat.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if dat else red.get("datum_rodjenja"))
        polje(4, 0, ("Sire" if EN else "Otac"), "otac", red.get("otac"),
              sorted((g["id"] for g in m.A.values() if g["pol"] == "m" and g["id"] != x), key=sort_key))
        polje(4, 1, ("Dam" if EN else "Majka"), "majka", red.get("majka"),
              sorted((g["id"] for g in m.A.values() if g["pol"] == "z" and g["id"] != x), key=sort_key))
        polje(5, 0, ("Herd" if EN else "Stado"), "stado", red.get("stado"), self.sva_stada())
        polje(5, 1, ("Origin" if EN else "Poreklo"), "poreklo", red.get("poreklo"), POREKLA)
        polje(6, 0, ("From whom / where" if EN else "Od koga / odakle"), "poreklo_od", red.get("poreklo_od"),
              sorted({g["poreklo_od"] for g in sva if g["poreklo_od"]}), span=2)
        akt = tk.BooleanVar(value=red.get("status", "aktivno") == "aktivno")
        if red.get("status") != "obrisano":
            ttk.Checkbutton(lc, text=("In herd (not sold or dead)" if EN else "U zapatu (nije prodato ni uginulo)"), variable=akt,
                            style="Card.TCheckbutton").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        # informacije samo za čitanje
        info = tk.Frame(lc, bg=SURF2)
        info.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        o, mj = m.P[x]
        pot = [k for k, pr in m.P.items() if x in pr]
        for i, (k, v) in enumerate(((("Parents" if EN else "Roditelji"), f"{o or '?'} × {mj or '?'}"),
                                    (("Offspring" if EN else "Potomaka"), str(len(pot))),
                                    (("Known ancestors" if EN else "Poznatih predaka"), str(len(m.putanje(x)))),
                                    (("Inbreeding" if EN else "Inbriding"), pct(m.inbr(x))),
                                    (("Added" if EN else "Upisano"), fmt_upis(a["uneto"])),
                                    (("Previous ear tags" if EN else "Ranije markice"), ", ".join(a["stare"]) or "–"))):
            self.lbl(info, k, 9, fg=INK2, bg=SURF2).grid(row=i, column=0, sticky="w", padx=(12, 8), pady=2)
            self.lbl(info, v, 9, "bold", bg=SURF2, wraplength=180, justify="left").grid(
                row=i, column=1, sticky="w", padx=(0, 12), pady=2)
        err_p = self.lbl(lc, "", 9, "bold", fg=BAD, wraplength=330, justify="left")
        err_p.grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def sacuvaj_podatke():
            novi = {k: v.get().strip() for k, v in pv.items()}
            novi["pol"] = pol_opcije.get(novi["pol"], red.get("pol", ""))
            novi["rasa"] = norm_rasa(novi["rasa"])
            o_, m_ = self.model.nadji(novi.get("otac")), self.model.nadji(novi.get("majka"))
            if o_ and m_ and (not novi["rasa"] or novi["rasa"].startswith(("hybrid" if EN else "hibrid")) or novi["rasa"] == ("crossbred" if EN else "melez")):
                novi["rasa"] = rasa_potomka(self.model.A[o_]["rasa"], self.model.A[m_]["rasa"]) or novi["rasa"]
            if red.get("status") != "obrisano":
                novi["status"] = "aktivno" if akt.get() else "neaktivno"
            greska = self.azuriraj_grlo(red, novi)
            if greska:
                err_p.config(text=greska)
                return
            self.promena((f"Details saved: {x}" if EN else f"Sačuvani podaci: {x}"))
            self.istorija_prozor(x)

        self.btn(lc, ("Save details" if EN else "Sačuvaj podatke"), sacuvaj_podatke, "Primary").grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # ---------- desno: novi zapis + istorija
        dsf = ScrollFrame(telo)
        dsf.pack(side="left", fill="both", expand=True)
        desno = tk.Frame(dsf.inner, bg=BG)
        desno.pack(fill="both", expand=True, padx=(0, 10))
        no, nc = self.card(desno, 18, 14)
        no.pack(fill="x", pady=(0, 14))
        self.lbl(nc, ("New history record" if EN else "Novi zapis u istoriju"), 13, "bold").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        ev = {}

        def ep(r, c, naslov, key, vrednost="", vals=None, width=16, span=1, state="normal"):
            f = tk.Frame(nc, bg=SURF)
            f.grid(row=r, column=c, columnspan=span, sticky="new", padx=(0 if c == 0 else 10, 0), pady=3)
            lab = self.lbl(f, naslov, 9, "bold", fg=INK2)
            lab.pack(anchor="w")
            v = tk.StringVar(value=vrednost)
            w = (ttk.Combobox(f, textvariable=v, values=vals, width=width, font=self.f(10), state=state)
                 if vals is not None else ttk.Entry(f, textvariable=v, width=width, font=self.f(10)))
            w.pack(fill="x", pady=(3, 0))
            ev[key] = v
            return lab

        for c in range(4):
            nc.columnconfigure(c, weight=1)
        # vrsta događaja – dugmad; podrazumevano prema izabranoj kartici
        grupa = self.ui.get("ist_" + x, {}).get("grupa", "")
        pocetni = {("Matings" if EN else "Parenja"): ("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("Treatments" if EN else "Lečenja"): ("Treatment" if EN else "Lečenje"), ("Births" if EN else "Porođaji"): ("Birth" if EN else "Porođaj")}.get(grupa, "")
        ev["dogadjaj"] = tk.StringVar(value=pocetni)
        self.lbl(nc, ("Event – click a type" if EN else "Događaj – klikni na vrstu"), 9, "bold", fg=INK2).grid(row=1, column=0, columnspan=4, sticky="w")
        self.izbor_dogadjaja(nc, ev["dogadjaj"]).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 2))
        ep(3, 0, ("Date" if EN else "Datum"), "datum", date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), width=12)
        suprotni = [k["id"] for k in m.grla() if k["vrsta"] == a["vrsta"] and k["pol"] and k["pol"] != a["pol"]]
        lab_par = ep(3, 1, "Partner", "partner", "", suprotni, width=12)
        f_par_ = lab_par.master
        f_kar = self.okvir_karence(nc, ev)
        lab_vr = ep(3, 2, ("Value" if EN else "Vrednost"), "vrednost", "", width=16, span=2)
        ep(4, 0, ("Description / note" if EN else "Opis / napomena"), "opis", "", width=60, span=4)
        poruka = self.lbl(nc, "", 9, fg=INK2, wraplength=620, justify="left")
        poruka.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))
        nazivi_vr = {("Weighing" if EN else "Merenje težine"): ("Weight (kg)" if EN else "Težina (kg)"), ("Vaccination" if EN else "Vakcinacija"): ("Vaccine / product" if EN else "Vakcina / preparat"),
                     ("Treatment" if EN else "Lečenje"): ("Drug / diagnosis" if EN else "Lek / dijagnoza"), ("Sale" if EN else "Prodaja"): ("Buyer / price" if EN else "Kupac / cena"), ("Move" if EN else "Premeštanje"): ("New herd" if EN else "Novo stado"),
                     ("Birth" if EN else "Porođaj"): ("Number of young" if EN else "Broj mladunaca"), ("Mating / insemination" if EN else "Parenje / osemenjavanje"): ("Natural / AI" if EN else "Prirodno / VO")}

        def prilagodi(*_):
            d = ev["dogadjaj"].get()
            lab_vr.config(text=nazivi_vr.get(d, ("Value" if EN else "Vrednost")))
            if d in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija")):
                f_par_.grid_remove()
                f_kar.grid(row=3, column=1, sticky="nw", padx=(10, 0), pady=3)
            else:
                f_kar.grid_remove()
                f_par_.grid()
            lab_par.config(text=("Partner (bull / ram…)" if EN else "Partner (bik / ovan…)") if d in (("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("Birth" if EN else "Porođaj")) else "Partner")
            p_ = m.nadji(ev["partner"].get())
            if not d:
                poruka.config(text=("Choose the event type by clicking one of the buttons." if EN else "Izaberi vrstu događaja klikom na jedno od dugmadi."), fg=INK2)
            elif d == ("Mating / insemination" if EN else "Parenje / osemenjavanje") and p_ and p_ != x:
                f = m.kinship(x, p_)
                t_, boja = procena(f, self.prag)
                dp = parsiraj_datum(ev["datum"].get())
                zenka = x if a["pol"] == "z" else p_
                _, nz_, mn_, mx_, pr_ = self.profil_gravidnosti(a["vrsta"], m.A[zenka]["rasa"] if zenka in m.A else "")
                oc = ((f"  Expected birth: {(dp + timedelta(days=pr_)).strftime('%d/%m/%Y')} "
                      f"(between {(dp + timedelta(days=mn_)).strftime('%d/%m')} and "
                      f"{(dp + timedelta(days=mx_)).strftime('%d/%m/%Y')}) – gestation: {nz_.lower()}, "
                      f"by the dam's breed." if EN else f"  Očekivani porođaj: {(dp + timedelta(days=pr_)).strftime('%d.%m.%Y')} "
                      f"(između {(dp + timedelta(days=mn_)).strftime('%d.%m.')} i "
                      f"{(dp + timedelta(days=mx_)).strftime('%d.%m.%Y')}) – nosivost: {nz_.lower()}, "
                      f"po rasi majke.") if dp and pr_ else "")
                poruka.config(text=(f"Expected inbreeding of offspring: {pct(f)} ({t_}), shared genes "
                                   f"{pct(m.r(x, p_))}.{oc}" if EN else f"Očekivani inbriding potomka: {pct(f)} ({t_}), zajednički geni "
                                   f"{pct(m.r(x, p_))}.{oc}"), fg=boja)
            elif d == ("Sale" if EN else "Prodaja") and "meso" in self.karenca(x):
                poruka.config(text=(f"WARNING: meat withdrawal lasts until {self.karenca(x)['meso'][0].strftime('%d/%m/%Y')}! "
                                   "The animal will be marked as out of herd." if EN else f"PAŽNJA: karenca za meso traje do {self.karenca(x)['meso'][0].strftime('%d.%m.%Y')}! "
                                   "Grlo će biti označeno kao van zapata."), fg=BAD)
            elif d in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and a["aktivno"]:
                poruka.config(text=("The animal will be marked as out of herd." if EN else "Grlo će biti označeno kao van zapata."), fg=WARN)
            elif d in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija")):
                poruka.config(text=("Enter the withdrawal period from the drug leaflet – the program will warn you while it lasts." if EN else "Upiši karencu iz uputstva leka – program će upozoravati dok traje."), fg=INK2)
            elif d == TER:
                poruka.config(text=("If the female has been mated, that mating will be marked as failed." if EN else "Ako je ženka sparena, to parenje će biti označeno kao neuspelo."), fg=INK2)
            elif d == ("Move" if EN else "Premeštanje"):
                poruka.config(text=("Enter the new herd in the \"New herd\" field – the animal's herd will change." if EN else "Upiši novo stado u polje „Novo stado“ – stado grla će se promeniti."), fg=INK2)
            else:
                poruka.config(text="")
        for k in ("dogadjaj", "partner", "datum"):
            ev[k].trace_add("write", prilagodi)
        prilagodi()

        def dodaj_zapis(e=None):
            d = parsiraj_datum(ev["datum"].get())
            if not d:
                poruka.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."), fg=BAD)
                return
            dog = ev["dogadjaj"].get().strip()
            if not dog:
                poruka.config(text=("Choose the event type (mating, treatment, birth…)." if EN else "Izaberi vrstu događaja (parenje, lečenje, porođaj…)."), fg=BAD)
                return
            par = ev["partner"].get().strip()
            par = m.nadji(par) or par
            vr = ev["vrednost"].get().strip()
            leci = dog in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))
            nz = self.ist.dodaj(x, dog, opis=ev["opis"].get().strip(), datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")),
                                partner="" if leci else par, vrednost=vr,
                                karenca_meso=self.broj_dana(ev["karenca_meso"].get()) if leci else "",
                                karenca_mleko=self.broj_dana(ev["karenca_mleko"].get()) if leci else "")
            self.posle_novog_zapisa(nz)
            if dog in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and red.get("status") == "aktivno":
                red["status"] = "neaktivno"
                self.ist.dodaj(x, AUTO, (f"Status: out of herd ({dog.lower()})" if EN else f"Status: van zapata ({dog.lower()})"), automatski=True)
            if dog == ("Move" if EN else "Premeštanje") and vr and vr != red.get("stado"):
                staro = red.get("stado") or "–"
                vr = next((s_ for s_ in self.sva_stada() if s_.lower() == vr.lower()), vr)
                red["stado"] = vr
                self.ist.dodaj(x, AUTO, (f"Herd: {staro} → {vr}" if EN else f"Stado: {staro} → {vr}"), automatski=True)
            self.promena((f"Recorded: {x} – {dog}" if EN else f"Zapisano: {x} – {dog}"))
            self.istorija_prozor(x)

        self.btn(nc, ("+  Add record" if EN else "+  Dodaj zapis"), dodaj_zapis, "Primary").grid(row=5, column=3, sticky="e", pady=(8, 0))

        lista = tk.Frame(desno, bg=BG)
        lista.pack(fill="both", expand=True)
        self.lbl(lista, ("History" if EN else "Istorija"), 13, "bold").pack(anchor="w", pady=(0, 8))
        win.osvezi = self.istorija_lista(lista, x, bez_dodaj=True)
        win.lift()

    def dogadjaj_forma(self, x=None, zapis=None, parent=None, posle=None, preset=None):
        m = self.model
        win = tk.Toplevel(parent or self.root, bg=SURF)
        win.title(("Edit event" if EN else "Izmena događaja") if zapis else ("New event" if EN else "Novi događaj"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Edit event" if EN else "Izmena događaja") if zapis else ("New event" if EN else "Novi događaj"), 16, "bold").grid(row=0, column=0, columnspan=2,
                                                                                 sticky="w", pady=(0, 12))
        sva = m.grla()
        vars_ = {}

        def polje(r, c, naslov, key, vrednost="", vals=None, state="normal", width=26, span=1):
            f = tk.Frame(b, bg=SURF)
            f.grid(row=r, column=c, columnspan=span, sticky="new", padx=(0 if c == 0 else 14, 0), pady=6)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            v = tk.StringVar(value=vrednost)
            w = (ttk.Combobox(f, textvariable=v, values=vals, state=state, width=width, font=self.f(10))
                 if vals is not None else ttk.Entry(f, textvariable=v, width=width, font=self.f(10)))
            w.pack(fill="x", pady=(4, 0))
            vars_[key] = v
            return w, f

        z = zapis or preset or {}
        w_grlo, _ = polje(1, 0, ("Animal *" if EN else "Grlo *"), "grlo", z.get("grlo") or x or "", [g["id"] for g in sva])
        polje(1, 1, ("Date *" if EN else "Datum *"), "datum", z.get("datum") or date.today().strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")))
        fd = tk.Frame(b, bg=SURF)
        fd.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)
        self.lbl(fd, ("Event * – click a type" if EN else "Događaj * – klikni na vrstu"), 9, "bold", fg=INK2).pack(anchor="w")
        vars_["dogadjaj"] = tk.StringVar(value=z.get("dogadjaj", ""))
        self.izbor_dogadjaja(fd, vars_["dogadjaj"], po_redu=4).pack(anchor="w", pady=(4, 0))
        w_dog = fd
        w_vr, f_vr = polje(3, 0, ("Value" if EN else "Vrednost"), "vrednost", z.get("vrednost", ""))
        w_par, f_par = polje(3, 1, ("Partner (bull / ram…)" if EN else "Partner (bik / ovan…)"), "partner", z.get("partner", ""), [])
        f_kar = self.okvir_karence(b, vars_, (z.get("karenca_meso", ""), z.get("karenca_mleko", "")))
        self.lbl(b, ("Description / note" if EN else "Opis / napomena"), 9, "bold", fg=INK2).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 4))
        opis = tk.Text(b, width=58, height=4, font=self.f(10), relief="flat", highlightthickness=1,
                       highlightbackground=LINE, highlightcolor=BRAND, wrap="word", padx=8, pady=6)
        opis.grid(row=5, column=0, columnspan=2, sticky="ew")
        opis.insert("1.0", z.get("opis", ""))
        info = self.lbl(b, "", 9, fg=INK2, wraplength=520, justify="left")
        info.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        vz = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(b, text=("Mark the animal as out of herd" if EN else "Označi grlo kao van zapata"), variable=vz, style="Card.TCheckbutton")
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))
        nazivi_vr = {("Weighing" if EN else "Merenje težine"): ("Weight (kg)" if EN else "Težina (kg)"), ("Vaccination" if EN else "Vakcinacija"): ("Vaccine / product" if EN else "Vakcina / preparat"),
                     ("Treatment" if EN else "Lečenje"): ("Drug / diagnosis" if EN else "Lek / dijagnoza"), ("Sale" if EN else "Prodaja"): ("Buyer / price" if EN else "Kupac / cena"), ("Move" if EN else "Premeštanje"): ("New herd / location" if EN else "Novo stado / lokacija"),
                     ("Birth" if EN else "Porođaj"): ("Number of young" if EN else "Broj mladunaca"), ("Mating / insemination" if EN else "Parenje / osemenjavanje"): ("Method (natural / AI)" if EN else "Način (prirodno / VO)")}

        def prilagodi(*_):
            d = vars_["dogadjaj"].get()
            g = m.nadji(vars_["grlo"].get())
            if d in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija")):
                f_par.grid_remove()
                f_kar.grid(row=3, column=1, sticky="nw", padx=(14, 0), pady=6)
            else:
                f_kar.grid_remove()
                f_par.grid()
            for w_ in f_vr.winfo_children():
                if isinstance(w_, tk.Label):
                    w_.config(text=nazivi_vr.get(d, ("Value" if EN else "Vrednost")))
            if g:
                a_ = m.A[g]
                suprotni = [k["id"] for k in m.grla() if k["vrsta"] == a_["vrsta"] and k["pol"] and k["pol"] != a_["pol"]]
                w_par.configure(values=suprotni)
            if d in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and not zapis:
                chk.grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
            else:
                chk.grid_remove()
            # ocekivani inbriding za parenje
            p_ = m.nadji(vars_["partner"].get())
            if d == ("Mating / insemination" if EN else "Parenje / osemenjavanje") and g and p_ and g != p_:
                f = m.kinship(g, p_)
                t_, boja = procena(f, self.prag)
                info.config(text=(f"Expected inbreeding of offspring: {pct(f)} ({t_}), shared genes {pct(m.r(g, p_))}." if EN else f"Očekivani inbriding potomka: {pct(f)} ({t_}), zajednički geni {pct(m.r(g, p_))}."),
                            fg=boja)
            else:
                info.config(text="")
        for k in ("dogadjaj", "grlo", "partner"):
            vars_[k].trace_add("write", prilagodi)
        prilagodi()

        def sacuvaj(ev=None):
            g = m.nadji(vars_["grlo"].get())
            if not g or m.A[g]["osnivac"]:
                err.config(text=("Choose an animal from the list (tag or ear tag)." if EN else "Izaberi grlo sa spiska (oznaka ili markica)."))
                return
            d = parsiraj_datum(vars_["datum"].get())
            if not d:
                err.config(text=("The date is not valid. Enter it as 15/03/2026." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2026."))
                return
            dog = vars_["dogadjaj"].get().strip()
            if not dog:
                err.config(text=("Choose an event." if EN else "Izaberi događaj."))
                return
            par = vars_["partner"].get().strip()
            par = m.nadji(par) or par
            leci = dog in (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))
            podaci = dict(grlo=g, datum=d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")), dogadjaj=dog, opis=opis.get("1.0", "end").strip(),
                          partner="" if leci else par, vrednost=vars_["vrednost"].get().strip(),
                          karenca_meso=self.broj_dana(vars_["karenca_meso"].get()) if leci else "",
                          karenca_mleko=self.broj_dana(vars_["karenca_mleko"].get()) if leci else "")
            if zapis:
                zapis.update(podaci)
            else:
                self.posle_novog_zapisa(self.ist.dodaj(**podaci))
                if dog in (("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće")) and vz.get():
                    r = self.red_za(g)
                    if r and r.get("status") == "aktivno":
                        r["status"] = "neaktivno"
                        self.ist.dodaj(g, AUTO, (f"Status: out of herd ({dog.lower()})" if EN else f"Status: van zapata ({dog.lower()})"), automatski=True)
            win.grab_release()
            win.destroy()
            self.promena((f"Recorded in history: {g} – {dog}" if EN else f"Zapisano u istoriju: {g} – {dog}"))
            if posle:
                try:
                    posle()
                except tk.TclError:
                    pass
            if getattr(self, "ist_win", None) and self.ist_win.winfo_exists() and hasattr(self.ist_win, "osvezi"):
                try:
                    self.ist_win.osvezi()
                except tk.TclError:
                    pass

        fb = tk.Frame(b, bg=SURF)
        fb.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        r = parent or self.root
        win.geometry(f"+{r.winfo_rootx() + max(0, (r.winfo_width() - win.winfo_width()) // 2)}"
                     f"+{r.winfo_rooty() + max(20, (r.winfo_height() - win.winfo_height()) // 3)}")
        (w_dog if (x or zapis) else w_grlo).focus_set()

    @staticmethod
    def naziv_gen(g):
        return {1: ("parent" if EN else "roditelj"), 2: ("grandparent" if EN else "deda / baba"), 3: ("great-grandparent" if EN else "pradeda / prababa"), 4: ("great-great-grandparent" if EN else "čukundeda / čukunbaba")}.get(
            g, (f"generation {g}" if EN else f"{g}. koleno"))

    def stablo(self, x, gen=4, tab="stablo"):
        m = self.model
        if x not in m.A:
            return
        if getattr(self, "stablo_win", None) and self.stablo_win.winfo_exists():
            win = self.stablo_win
            for w in win.winfo_children():
                w.destroy()
        else:
            win = tk.Toplevel(self.root, bg=BG)
            win.geometry(f"1040x700+{self.root.winfo_rootx() + 30}+{self.root.winfo_rooty() + 20}")
            win.transient(self.root)
            win.bind("<Escape>", lambda e: win.destroy())
            self.stablo_win = win
        win.title((f"Pedigree of animal {x}" if EN else f"Poreklo grla {x}"))
        a = m.A[x]
        put = m.putanje(x)                       # SVI preci, sve generacije
        dubina = max((max(gs) for gs in put.values()), default=0)
        ponavlja = {y: gs for y, gs in put.items() if sum(gs.values()) > 1}
        gen = max(2, min(gen, min(7, dubina) + 1))

        # zaglavlje
        h = tk.Frame(win, bg=BG)
        h.pack(fill="x", padx=24, pady=(18, 6))
        self.cip(h, x, lambda: self.karton(x), big=True, bg=BG, siv=a["osnivac"]).pack(side="left")
        t = tk.Frame(h, bg=BG)
        t.pack(side="left", padx=14)
        self.lbl(t, (f"Pedigree – {m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}" if EN else f"Poreklo – {m.pol_naziv(x)}{', ' + a['rasa'] if a['rasa'] else ''}"), 14, "bold").pack(anchor="w")
        por = a["poreklo"] + (f" – {a['poreklo_od']}" if a["poreklo_od"] else "") if a["poreklo"] else a["poreklo_od"]
        info = (f"{len(put)} known ancestors in {dubina} generations   ·   inbreeding {pct(m.inbr(x))}" if EN else f"{len(put)} poznatih predaka u {dubina} generacija   ·   inbriding {pct(m.inbr(x))}")
        self.lbl(t, (f"{por}   ·   " if por else "") + info, 10, fg=INK2).pack(anchor="w")

        seg = tk.Frame(win, bg=BG)
        seg.pack(fill="x", padx=24, pady=(4, 8))
        sg = tk.Frame(seg, bg=SURF2)
        sg.pack(side="left")
        n_boc = len(self.bocni_srodnici(x))
        n_pot = sum(len(v) for v in self.potomci_po_kolenima(x).values())
        for k, tx in (("stablo", ("Tree" if EN else "Stablo")), ("svi", (f"All ancestors ({len(put)})" if EN else f"Svi preci ({len(put)})")),
                      ("potomci", (f"Descendants ({n_pot})" if EN else f"Potomci ({n_pot})")), ("bocni", (f"Collateral relatives ({n_boc})" if EN else f"Bočni srodnici ({n_boc})"))):
            akt = tab == k
            lb = tk.Label(sg, text=tx, font=self.f(10, "bold"), bg=SURF if akt else SURF2, fg=INK if akt else INK2,
                          padx=14, pady=6, cursor="hand2")
            lb.pack(side="left", padx=3, pady=3)
            lb.bind("<Button-1>", lambda e, k=k: self.stablo(x, gen, k))
        if tab == "stablo" and dubina >= 2:
            desno = tk.Frame(seg, bg=BG)
            desno.pack(side="right")
            self.lbl(desno, ("Generations shown:" if EN else "Prikaži generacija:"), 9, "bold", fg=INK2).pack(side="left", padx=(0, 6))
            gv = tk.StringVar(value=str(gen - 1))
            cg = ttk.Combobox(desno, textvariable=gv, values=[str(i) for i in range(1, min(7, dubina) + 1)],
                              state="readonly", width=4, font=self.f(10))
            cg.pack(side="left")
            cg.bind("<<ComboboxSelected>>", lambda e: self.stablo(x, int(gv.get()) + 1, "stablo"))

        # preci koji se ponavljaju – kroz CEO rodoslov, ne samo prikazane generacije
        leg = tk.Frame(win, bg=BG)
        leg.pack(fill="x", padx=24, pady=(0, 6))
        if not put:
            self.lbl(leg, ("No parents are entered for this animal." if EN else "Za ovo grlo nisu upisani roditelji."), 10, fg=INK2).pack(anchor="w")
        elif ponavlja:
            opis = ", ".join((f"{y} ({sum(gs.values())}×, gen. {' and '.join(str(g) for g in sorted(gs))})" if EN else f"{y} ({sum(gs.values())}×, gen. {' i '.join(str(g) for g in sorted(gs))})")
                             for y, gs in sorted(ponavlja.items(), key=lambda t: (min(t[1]), sort_key(t[0]))))
            self.lbl(leg, ("Ancestors repeated in the whole pedigree (cause of inbreeding): " if EN else "Preci koji se ponavljaju u celom rodoslovu (uzrok inbridinga): ") + opis, 9, fg=BAD,
                     wraplength=980, justify="left").pack(anchor="w")
            dalji = [y for y, gs in ponavlja.items() if min(gs) >= gen]
            if tab == "stablo" and dalji:
                self.lbl(leg, (f"Some of them are beyond the generations shown ({', '.join(sorted(dalji, key=sort_key))})"
                              " – increase the number of generations or open the \"All ancestors\" tab." if EN else f"Neki od njih su dalje od prikazanih generacija ({', '.join(sorted(dalji, key=sort_key))})"
                              " – povećaj broj generacija ili otvori karticu „Svi preci“."), 9, fg=WARN,
                         wraplength=980, justify="left").pack(anchor="w")
        else:
            self.lbl(leg, ("No ancestor is repeated in the whole known pedigree." if EN else "Nijedan predak se ne ponavlja u celom poznatom rodoslovu."), 9, fg=OK).pack(anchor="w")

        if tab == "svi":
            self.svi_preci(win, x, put, ponavlja, dubina)
        elif tab == "bocni":
            self.tab_bocni(win, x)
        elif tab == "potomci":
            self.tab_potomci(win, x)
        else:
            self.crtaj_stablo(win, x, gen, ponavlja)
        win.lift()

    def potomci_po_kolenima(self, x):
        """{koleno: [potomak, ...]} – 1 deca, 2 unuci, 3 praunuci…"""
        m = self.model
        deca = {}
        for k, (o, mj) in m.P.items():
            for p in (o, mj):
                if p:
                    deca.setdefault(p, set()).add(k)
        rez, vidjeni, nivo, g = {}, {x}, {x}, 1
        while nivo and g <= 10:
            sl = set()
            for y in nivo:
                sl |= deca.get(y, set())
            sl -= vidjeni
            if not sl:
                break
            rez[g] = sorted(sl, key=lambda y: (m.A[y]["datum"] or date.max, sort_key(y)))
            vidjeni |= sl
            nivo, g = sl, g + 1
        return rez

    def tab_potomci(self, win, x):
        m = self.model
        po = self.potomci_po_kolenima(x)
        ukupno = sum(len(v) for v in po.values())
        legla = [z for z in self.cekaju_mindjusu(x)]
        nazivi_k = {1: ("Children" if EN else "Deca"), 2: ("Grandchildren" if EN else "Unuci"), 3: ("Great-grandchildren" if EN else "Praunuci"), 4: ("Great-great-grandchildren" if EN else "Čukununuci")}
        opis = " · ".join((f"{nazivi_k.get(k, f'generation {k}')}: {len(v)}" if EN else f"{nazivi_k.get(k, f'{k}. koleno')}: {len(v)}") for k, v in po.items())
        self.lbl(win, ((f"In total {ukupno} descendants – {opis}." if EN else f"Ukupno {ukupno} potomaka – {opis}.") if ukupno else ("No descendants recorded." if EN else "Nema upisanih potomaka.")) +
                 (" Share of genes = how many genes the descendant carries from this animal." if EN else " Udeo gena = koliko gena potomak nosi od ovog grla."), 9, fg=INK2, wraplength=980,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not ukupno and not legla:
            self.napomena(body, ("This animal has no recorded descendants yet." if EN else "Ovo grlo još nema upisanih potomaka."), ok=True)
            return
        wrap, tv = self.tabela(body, [("id", ("Offspring" if EN else "Potomak"), 200), ("odnos", ("Other parent" if EN else "Drugi roditelj"), 200),
                                      ("pol", ("Sex" if EN else "Pol"), 80), ("geni", ("Share of genes" if EN else "Udeo gena"), 95, "e"), ("rasa", ("Breed" if EN else "Rasa"), 120),
                                      ("rod", ("Born" if EN else "Rođen"), 95), ("st", "Status", 140)], visina=16)
        wrap.pack(fill="both", expand=True)
        tv.tag_configure("grupa", font=self.f(10, "bold"), background=SURF2)
        for k, lst in po.items():
            gr = tv.insert("", "end", text=(f"  {nazivi_k.get(k, f'generation {k}')} ({len(lst)})" if EN else f"  {nazivi_k.get(k, f'{k}. koleno')} ({len(lst)})"), open=k <= 2,
                           tags=["grupa"])
            for y in lst:
                p = m.A[y]
                o, mj = m.P.get(y, (None, None))
                if k == 1:
                    drugi = mj if o == x else o
                    dr = (f"{'dam' if o == x else 'sire'} {drugi}" if EN else f"{'majka' if o == x else 'otac'} {drugi}") if drugi else ("unknown" if EN else "nepoznat")
                else:
                    preko = [r for r in (o, mj) if r and (r in po.get(k - 1, []))]
                    dr = (f"through {', '.join(preko)}" if EN else f"preko {', '.join(preko)}") if preko else "–"
                st = (("deleted" if EN else "obrisano") if p.get("obrisano") else ("in herd" if EN else "u zapatu") if p["aktivno"] else ("out of herd" if EN else "van zapata"))
                tv.insert(gr, "end", iid=y, text="  " + y, image=self.img_tag, values=(
                    dr, m.pol_naziv(y), pct(m.doprinos(y, x)), p["rasa"] or "–",
                    fmt_datum(p["datum"]) or "–", st), tags=[] if p["aktivno"] else ["off"])
        if legla:
            gr = tv.insert("", "end", text=("  Born, no ear tag yet" if EN else "  Rođeni, još bez minđuše"), open=True, tags=["grupa"])
            for z in legla:
                uk, dd, vec = self.leglo(z)
                majka, otac = self.roditelji_parenja(z)
                tv.insert(gr, "end", text=(f"  {uk - len(vec)} young" if EN else f"  {uk - len(vec)} mladih"), values=(
                    f"{majka or '?'} × {otac or '?'}", "–", "50,0%", "–", dd, ("waiting for entry in the list" if EN else "čeka upis u listu")))
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Double-click a descendant to open its card." if EN else "Dvoklik na potomka otvara njegov karton."), 9, fg=INK2).pack(anchor="w", pady=(8, 0))

    def bocni_srodnici(self, x):
        """Bočni (kolateralni) srodnici: braća/sestre, braća/sestre roditelja, nećaci, prvi rođaci.
        Vraća [(grupa, srodnik, opis odnosa)]."""
        m = self.model
        deca = {}
        for k, (o, mj) in m.P.items():
            for p in (o, mj):
                if p:
                    deca.setdefault(p, set()).add(k)

        def braca(y):
            o, mj = m.P.get(y, (None, None))
            rez = {}
            for s in (deca.get(o, set()) | deca.get(mj, set())) - {y}:
                so, sm = m.P.get(s, (None, None))
                if o and mj and so == o and sm == mj:
                    rez[s] = "pun"
                elif o and so == o:
                    rez[s] = ("paternal" if EN else "po ocu")
                elif mj and sm == mj:
                    rez[s] = ("maternal" if EN else "po majci")
            return rez

        def naziv(s, z_, m_):
            return m_ if m.A.get(s, {}).get("pol") == "m" else z_ if m.A.get(s, {}).get("pol") == "z" else f"{m_} / {z_}"

        rez, vidjeni = [], {x}
        predci = m.preci(x)
        # 1) braća i sestre
        for s, tip in sorted(braca(x).items(), key=lambda t: (t[1] != "pun", sort_key(t[0]))):
            ime = naziv(s, ("sister" if EN else "sestra"), ("brother" if EN else "brat"))
            rez.append((("Siblings" if EN else "Braća i sestre"), s, (("full " if EN else "pun ") if tip == "pun" else ("half-" if EN else "polu")) + ime +
                        ("" if tip == "pun" else f" ({tip})")))
            vidjeni.add(s)
        # dvostruki odnos: brat/sestra koji je ujedno i dete brata/sestre
        sib = set(braca(x))
        for i, (g, y, op) in enumerate(rez):
            if any(p_ in sib for p_ in m.P.get(y, (None, None)) if p_):
                rez[i] = (g, y, op + (f", also {naziv(y, 'niece', 'nephew')}" if EN else f", ujedno {naziv(y, 'nećaka', 'nećak')}"))
        # 2) deca braće i sestara
        for s in list(braca(x)):
            for d in sorted(deca.get(s, set()) - vidjeni, key=sort_key):
                rez.append((("Nephews and nieces (children of siblings)" if EN else "Nećaci (deca braće i sestara)"), d, (f"child of {s}" if EN else f"dete od {s}")))
                vidjeni.add(d)
        # 3) braća i sestre roditelja
        o, mj = m.P.get(x, (None, None))
        strane = []
        for rod, strana, (mz, zz) in ((o, ("paternal" if EN else "po ocu"), (("uncle" if EN else "stric"), ("aunt" if EN else "tetka"))), (mj, ("maternal" if EN else "po majci"), (("uncle" if EN else "ujak"), ("aunt" if EN else "tetka")))):
            if not rod:
                continue
            for s, tip in sorted(braca(rod).items(), key=lambda t: sort_key(t[0])):
                if s in vidjeni or s in predci:
                    continue
                rez.append((("Siblings of parents" if EN else "Braća i sestre roditelja"), s, (f"{strana} {naziv(s, zz, mz)}" if EN else f"{naziv(s, zz, mz)} {strana}") +
                            ("" if tip == "pun" else (" (half)" if EN else " (polu)"))))
                vidjeni.add(s)
                strane.append((s, strana))
        # 4) prvi rođaci (deca braće i sestara roditelja)
        for s, strana in strane:
            for d in sorted(deca.get(s, set()) - vidjeni, key=sort_key):
                if d in predci:
                    continue
                rez.append((("First cousins" if EN else "Prvi rođaci"), d, (f"child of {s} ({strana})" if EN else f"dete od {s} ({strana})")))
                vidjeni.add(d)
        return rez

    def tab_bocni(self, win, x):
        m = self.model
        sr = self.bocni_srodnici(x)
        self.lbl(win, ("Collateral relatives are neither ancestors nor descendants, but share ancestors with this animal. "
                      "Be careful when mating – a high share of genes also means higher inbreeding of the young." if EN else "Bočni srodnici nisu ni preci ni potomci, ali imaju zajedničke pretke sa ovim grlom. "
                      "Pazi pri parenju – visok procenat zajedničkih gena znači i veći inbriding mladih."), 9,
                 fg=INK2, wraplength=980, justify="left").pack(anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not sr:
            self.napomena(body, ("No known collateral relatives (siblings, cousins…) according to the recorded pedigree." if EN else "Nema poznatih bočnih srodnika (braće, sestara, rođaka…) prema upisanom rodoslovu."),
                          ok=True)
            return
        wrap, tv = self.tabela(body, [("id", ("Relative" if EN else "Srodnik"), 240), ("odnos", ("Relation" if EN else "Odnos"), 260), ("geni", ("Shared genes" if EN else "Zajednički geni"), 120, "e"),
                                      ("f", ("Inbreeding of young" if EN else "Inbriding mladih"), 120, "e"), ("rasa", ("Breed" if EN else "Rasa"), 110),
                                      ("rod", ("Born" if EN else "Rođen"), 70), ("st", "Status", 140)], visina=16)
        wrap.pack(fill="both", expand=True)
        tv.tag_configure("grupa", font=self.f(10, "bold"), background=SURF2)
        grupe = {}
        for g, y, opis in sr:
            if g not in grupe:
                grupe[g] = tv.insert("", "end", text="  " + g, open=True, tags=["grupa"])
        brojac = {}
        for g, y, opis in sr:
            brojac[g] = brojac.get(g, 0) + 1
            p = m.A.get(y, {})
            r = m.r(x, y)
            suprotan = p.get("pol") and m.A[x]["pol"] and p.get("pol") != m.A[x]["pol"]
            f = m.kinship(x, y) if suprotan else None
            st = (("known only as a parent" if EN else "poznat samo kao roditelj") if p.get("osnivac") else ("deleted" if EN else "obrisano") if p.get("obrisano")
                  else ("in herd" if EN else "u zapatu") if p.get("aktivno") else ("out of herd" if EN else "van zapata"))
            tagovi = []
            if f is not None and f > self.prag and p.get("aktivno"):
                tagovi.append("bad")
            elif not p.get("aktivno"):
                tagovi.append("off")
            tv.insert(grupe[g], "end", iid=y, text="  " + y, image=self.img_tag_siv if p.get("osnivac") else self.img_tag,
                      values=(opis, pct(r), pct(f) if f is not None else "–", p.get("rasa") or "–",
                              p["datum"].year if p.get("datum") else "–", st), tags=tagovi)
        for g, iid in grupe.items():
            tv.item(iid, text=f"  {g} ({brojac[g]})")
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Red = opposite sex in the herd with which the young would have inbreeding above the limit. "
                       "Double-click opens the card." if EN else "Crveno = suprotan pol u zapatu sa kojim bi mladi imali inbriding iznad granice. "
                       "Dvoklik otvara karton."), 9, fg=INK2).pack(anchor="w", pady=(8, 0))

    def svi_preci(self, win, x, put, ponavlja, dubina):
        m = self.model
        kom = m.kompletnost(x, dubina)
        if kom:
            self.lbl(win, ("Pedigree completeness:  " if EN else "Kompletnost rodoslova:  ") + "   ".join(
                (f"gen. {g}: {n}/{od}" if EN else f"{g}. gen {n}/{od}") for g, n, od in kom), 9, fg=INK2, wraplength=980, justify="left").pack(
                anchor="w", padx=24, pady=(0, 6))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        if not put:
            return
        wrap, tv = self.tabela(body, [("id", ("Ancestor" if EN else "Predak"), 110), ("gen", ("Generation" if EN else "Generacija"), 220), ("put", ("Times" if EN else "Puta"), 60, "e"),
                                      ("udeo", ("Share of genes" if EN else "Udeo gena"), 95, "e"), ("pol", ("Sex" if EN else "Pol"), 75), ("mk", ("Ear tag" if EN else "Markica"), 115),
                                      ("rasa", ("Breed" if EN else "Rasa"), 95), ("st", "Status", 160)], visina=16)
        wrap.pack(fill="both", expand=True)
        redovi = sorted(put.items(), key=lambda t: (-m.doprinos(x, t[0]), min(t[1]), sort_key(t[0])))
        for i, (y, gs) in enumerate(redovi):
            p = m.A[y]
            n = sum(gs.values())
            gen_txt = (f"{min(gs)}.  {self.naziv_gen(min(gs))}" if len(gs) == 1
                       else ", ".join(str(g) for g in sorted(gs)) + (" generations" if EN else ". generacija"))
            st = (("known only as a parent" if EN else "poznat samo kao roditelj") if p["osnivac"] else ("deleted" if EN else "obrisano") if p.get("obrisano")
                  else ("in herd" if EN else "u zapatu") if p["aktivno"] else ("out of herd" if EN else "van zapata"))
            tags = (["odd"] if i % 2 else []) + (["bad"] if y in ponavlja else []) + (["off"] if p["osnivac"] else [])
            tv.insert("", "end", iid=y, text="  " + y, image=self.img_tag_siv if p["osnivac"] else self.img_tag,
                      values=(gen_txt, f"{n}×", pct(m.doprinos(x, y)), m.pol_naziv(y), p["markica"] or "–",
                              p["rasa"] or "–", st), tags=tags)
        tv.bind("<Double-1>", lambda e: self.otvori_iz(tv))
        self.lbl(body, ("Red = the ancestor appears more than once.  Double-click opens the ancestor's card." if EN else "Crveno = predak se pojavljuje više puta.  Dvoklik otvara karton pretka."), 9, fg=INK2).pack(
            anchor="w", pady=(8, 0))

    def crtaj_stablo(self, win, x, gen, ponavlja):
        m = self.model
        sloti = {}
        def skupi(y, g, i):
            if g >= gen:
                return
            sloti[(g, i)] = y
            o, mj = m.P.get(y, (None, None)) if y else (None, None)
            skupi(o, g + 1, 2 * i)
            skupi(mj, g + 1, 2 * i + 1)
        skupi(x, 0, 0)
        self.lbl(win, ("Each ancestor shows what share of genes the animal carries from it (sum of all paths). "
                      "Click an ancestor to show its pedigree, double-click opens its card." if EN else "Uz svakog pretka piše koliki deo gena grlo nosi od njega (zbir svih puteva). "
                      "Klik na pretka prikazuje njegovo poreklo, dvoklik otvara karton."), 9, fg=INK2,
                 wraplength=980, justify="left").pack(anchor="w", padx=24)

        wrap = tk.Frame(win, bg=LINE)
        wrap.pack(fill="both", expand=True, padx=24, pady=(4, 20))
        c = tk.Canvas(wrap, bg=SURF, highlightthickness=0)
        sy = ttk.Scrollbar(wrap, orient="vertical", command=c.yview)
        sx = ttk.Scrollbar(wrap, orient="horizontal", command=c.xview)
        c.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        c.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        BW, BH, GAP = 196, 50, 34
        listova = 2 ** (gen - 1)
        visina = max(480, listova * (BH + 12) + 40)
        for g in range(gen):
            nz = ("Animal" if EN else "Grlo") if g == 0 else {1: ("Parents" if EN else "Roditelji"), 2: ("Grandparents" if EN else "Dede i babe"), 3: ("Great-grandparents" if EN else "Pradede i prababe"),
                                         4: ("Great-great-grandparents" if EN else "Čukundede i čukunbabe")}.get(g, (f"generation {g}" if EN else f"{g}. koleno"))
            c.create_text(20 + g * (BW + GAP) + BW / 2, 16, text=nz, font=self.f(9, "bold"), fill=INK2)
        pos = {}
        for (g, i) in sloti:
            pos[(g, i)] = (20 + g * (BW + GAP), 30 + (i + 0.5) * (visina - 40) / (2 ** g))
        for (g, i), (cx, cy) in pos.items():
            for k in (0, 1):
                ch = (g + 1, 2 * i + k)
                if ch in pos:
                    px, py = pos[ch]
                    mx = cx + BW + GAP / 2
                    c.create_line(cx + BW, cy, mx, cy, mx, py, px, py, fill=LINE, width=2)
        for (g, i), y in sloti.items():
            cx, cy = pos[(g, i)]
            x1, y1, x2, y2 = cx, cy - BH / 2, cx + BW, cy + BH / 2
            uloga = "" if g == 0 else (("sire" if EN else "otac") if i % 2 == 0 else ("dam" if EN else "majka"))
            if not y:
                c.create_polygon(self.zaobljeno(x1, y1, x2, y2, 8), smooth=True, fill=BG, outline="#C3CBC4", dash=(4, 3))
                c.create_text(x1 + 14, cy, text=(f"{uloga} unknown" if EN else f"{uloga} nepoznat{'a' if uloga == 'majka' else ''}") if uloga else "",
                              anchor="w", font=self.f(9), fill="#98A39B")
                continue
            p = m.A[y]
            rep_ = y in ponavlja
            tag = f"b{g}_{i}"
            c.create_polygon(self.zaobljeno(x1, y1, x2, y2, 8), smooth=True,
                             fill=SURF2 if p["osnivac"] else (BAD_BG if rep_ else SURF),
                             outline=BAD if rep_ else (BRAND if g == 0 else LINE), width=2 if (rep_ or g == 0) else 1,
                             tags=tag)
            c.create_rectangle(x1 + 1, y1 + 8, x1 + 6, y2 - 8, fill=TAG if not p["osnivac"] else "#C9D0CA",
                               outline="", tags=tag)
            c.create_text(x1 + 16, cy - 9, text=y, anchor="w", font=self.f(10, "bold"), fill=INK, tags=tag)
            if uloga:
                c.create_text(x2 - 10, cy - 9, text=(f"{uloga} · {pct(m.doprinos(x, y))} genes" if EN else f"{uloga} · {pct(m.doprinos(x, y))} gena"), anchor="e",
                              font=self.f(8), fill=BAD if rep_ else INK2, tags=tag)
            sub = " · ".join(v for v in (p["markica"], p["rasa"]) if v)
            if p["datum"] and len(sub) + 7 <= 30:
                sub = (sub + " · " if sub else "") + str(p["datum"].year)
            sub = sub or (("known only as a parent" if EN else "poznat samo kao roditelj") if p["osnivac"] else "")
            if len(sub) > 30:
                sub = sub[:29] + "…"
            c.create_text(x1 + 16, cy + 10, text=sub, anchor="w", font=self.f(8), fill=INK2, tags=tag)
            if g > 0:
                c.tag_bind(tag, "<Button-1>", lambda e, y=y: self.stablo(y, gen))
            c.tag_bind(tag, "<Double-1>", lambda e, y=y: self.karton(y))
            c.tag_bind(tag, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.config(cursor=""))
            # oznaka da ovaj predak ima jos predaka iza ivice prikaza
            if g == gen - 1 and any(m.P.get(y, (None, None))):
                c.create_text(x2 + 6, cy, text="›", anchor="w", font=self.f(14, "bold"), fill=INK2)
        c.configure(scrollregion=(0, 0, 40 + gen * (BW + GAP), visina + 10))
        c.bind("<MouseWheel>", lambda e: c.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units"))
        c.bind("<Button-4>", lambda e: c.yview_scroll(-1, "units"))
        c.bind("<Button-5>", lambda e: c.yview_scroll(1, "units"))

    # ---------- forma
    def forma(self, jid=None, preset=None):
        red = next((r for r in self.tab.redovi if r["id"] == jid), None) if jid else None
        posl = self.pod.get("poslednje", {})
        v = dict(red) if red else {"vrsta": posl.get("vrsta", ("cattle" if EN else "goveda")), "rasa": posl.get("rasa", ""),
                                   "stado": posl.get("stado", ""), "status": "aktivno", **(preset or {})}
        win = tk.Toplevel(self.root, bg=SURF)
        win.title(("Edit animal" if EN else "Izmena grla") if red else ("New animal" if EN else "Novo grlo"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        b = tk.Frame(win, bg=SURF)
        b.pack(fill="both", expand=True, padx=26, pady=22)
        self.lbl(b, ("Edit animal" if EN else "Izmena grla") if red else ("New animal" if EN else "Novo grlo"), 17, "bold").grid(row=0, column=0, columnspan=2,
                                                                          sticky="w", pady=(0, 14))
        m = self.model
        sva = m.grla()
        vars_ = {}

        def polje(r, c, naslov, key, widget="entry", values=(), hint=""):
            f = tk.Frame(b, bg=SURF)
            f.grid(row=r, column=c, sticky="new", padx=(0 if c == 0 else 14, 0), pady=6)
            self.lbl(f, naslov, 9, "bold", fg=INK2).pack(anchor="w")
            var = tk.StringVar(value=v.get(key, ""))
            if widget == "entry":
                w = ttk.Entry(f, textvariable=var, width=28, font=self.f(10))
            else:
                w = ttk.Combobox(f, textvariable=var, values=list(values), width=26, font=self.f(10),
                                 state="readonly" if widget == "select" else "normal")
            w.pack(fill="x", pady=(4, 0))
            if hint:
                self.lbl(f, hint, 8, fg="#8A968D").pack(anchor="w")
            vars_[key] = var
            return w

        e_id = polje(1, 0, ("Animal tag *" if EN else "Oznaka grla *"), "id", hint=("e.g. K12 or a name" if EN else "npr. K12 ili ime"))
        polje(1, 1, ("Ear tag" if EN else "Ušna markica"), "markica", hint=("e.g. UK 123456 700123" if EN else "npr. RS 1234-5678"))
        vr = polje(2, 0, ("Species" if EN else "Vrsta"), "vrsta", "combo", VRSTE)
        polje(2, 1, ("Breed" if EN else "Rasa"), "rasa", "combo", sorted({a["rasa"] for a in sva if a["rasa"]}))

        pf = tk.Frame(b, bg=SURF)
        pf.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
        self.lbl(pf, ("Sex *" if EN else "Pol *"), 9, "bold", fg=INK2).pack(anchor="w")
        segf = tk.Frame(pf, bg=SURF2)
        segf.pack(anchor="w", pady=(4, 0))
        pol = tk.StringVar(value=v.get("pol", ""))
        seg_btns = {}

        def crtaj_seg(*_):
            n = nazivi(vrsta_norm(vars_["vrsta"].get()))
            for k, lb in seg_btns.items():
                akt = pol.get() == k
                lb.config(text=(n[1] if k == "z" else n[0]).capitalize(), bg=SURF if akt else SURF2,
                          fg=INK if akt else INK2)
        for k in ("z", "m"):
            lb = tk.Label(segf, font=self.f(10, "bold"), padx=20, pady=6, cursor="hand2")
            lb.pack(side="left", padx=3, pady=3)
            lb.bind("<Button-1>", lambda e, k=k: (pol.set(k), crtaj_seg()))
            seg_btns[k] = lb
        crtaj_seg()
        vars_["vrsta"].trace_add("write", crtaj_seg)

        d = parsiraj_datum(v.get("datum_rodjenja"))
        v["datum_rodjenja"] = d.strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if d else v.get("datum_rodjenja", "")
        polje(4, 0, ("Date of birth" if EN else "Datum rođenja"), "datum_rodjenja", hint=("day/month/year, e.g. 15/03/2022" if EN else "dan.mesec.godina, npr. 15.03.2022"))
        polje(4, 1, ("Herd / location" if EN else "Stado / lokacija"), "stado", "combo", sorted({a["stado"] for a in sva if a["stado"]}))
        polje(5, 0, ("Sire" if EN else "Otac"), "otac", "combo", sorted((a["id"] for a in m.A.values() if a["pol"] == "m"), key=sort_key),
              hint=("tag or ear tag; empty if unknown" if EN else "oznaka ili markica; prazno ako je nepoznat"))
        polje(5, 1, ("Dam" if EN else "Majka"), "majka", "combo", sorted((a["id"] for a in m.A.values() if a["pol"] == "z"), key=sort_key),
              hint=("tag or ear tag; empty if unknown" if EN else "oznaka ili markica; prazno ako je nepoznata"))
        polje(6, 0, ("Origin" if EN else "Poreklo"), "poreklo", "combo", POREKLA)
        polje(6, 1, ("From whom / where" if EN else "Od koga / odakle"), "poreklo_od", "combo",
              sorted({a["poreklo_od"] for a in sva if a["poreklo_od"]}))

        def auto_rasa(*_):
            """Kad su upisani otac i majka različitih rasa, rasa postaje 'hibrid O×M'."""
            o_, m_ = m.nadji(vars_["otac"].get()), m.nadji(vars_["majka"].get())
            if not o_ or not m_:
                return
            predlog = rasa_potomka(m.A[o_]["rasa"], m.A[m_]["rasa"])
            sad = vars_["rasa"].get().strip().lower()
            if predlog and (not sad or sad.startswith(("hybrid" if EN else "hibrid")) or sad == ("crossbred" if EN else "melez")):
                vars_["rasa"].set(predlog)
        vars_["otac"].trace_add("write", auto_rasa)
        vars_["majka"].trace_add("write", auto_rasa)
        akt = tk.BooleanVar(value=v.get("status", "aktivno") != "neaktivno")
        ttk.Checkbutton(b, text=("The animal is in the herd (not sold or dead)" if EN else "Grlo je u zapatu (nije prodato ni uginulo)"), variable=akt,
                        style="Card.TCheckbutton").grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
        err = self.lbl(b, "", 10, "bold", fg=BAD)
        err.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def sacuvaj(dalje=False):
            nid = vars_["id"].get().strip()
            if not nid:
                err.config(text=("Enter the animal's tag." if EN else "Upiši oznaku grla."))
                e_id.focus_set()
                return
            dup = next((r for r in self.tab.redovi if r["id"] == nid and r is not red), None)
            if dup:
                err.config(text=(f"Animal {nid} already exists." if EN else f"Grlo {nid} već postoji.") + ((" It is deleted – restore it from the \"Deleted animals\" list." if EN else " Obrisano je – vrati ga iz liste „Obrisana grla“.")
                                                             if dup.get("status") == "obrisano" else ""))
                return
            mk = vars_["markica"].get().strip()
            if mk:
                zauzeto = self.markica_zauzeta(mk, red)
                if zauzeto:
                    err.config(text=zauzeto)
                    return
            if pol.get() not in ("m", "z"):
                err.config(text=("Choose the sex." if EN else "Izaberi pol."))
                return
            dat = vars_["datum_rodjenja"].get().strip()
            if dat and not parsiraj_datum(dat):
                err.config(text=("The date is not valid. Enter it as 15/03/2022." if EN else "Datum nije ispravan. Upiši ga kao 15.03.2022."))
                return
            o, mj = vars_["otac"].get().strip(), vars_["majka"].get().strip()
            if nid in (o, mj):
                err.config(text=("An animal cannot be its own parent." if EN else "Grlo ne može biti sopstveni roditelj."))
                return
            novi = dict(id=nid, markica=mk, vrsta=vrsta_norm(vars_["vrsta"].get()) or ("cattle" if EN else "goveda"),
                        rasa=norm_rasa(vars_["rasa"].get()), pol=pol.get(),
                        datum_rodjenja=parsiraj_datum(dat).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")) if dat else "",
                        otac=o, majka=mj, status=("obrisano" if red and red.get("status") == "obrisano"
                                                  else "aktivno" if akt.get() else "neaktivno"),
                        stado=vars_["stado"].get().strip(), poreklo=vars_["poreklo"].get().strip(),
                        poreklo_od=vars_["poreklo_od"].get().strip())
            if red:
                staro = red["id"]
                if staro != nid:
                    self.ist.preimenuj(staro, nid)
                    self.pods.preimenuj(staro, nid)
                    self.ist.dodaj(nid, AUTO, (f"Tag changed: {staro} → {nid}" if EN else f"Oznaka promenjena: {staro} → {nid}"), automatski=True)
                red["id"] = nid
                if norm(red.get("markica")) != norm(mk):
                    self.primeni_markicu(red, mk, zapamti=True)
                nazivi_polja = dict(vrsta="vrsta", rasa="rasa", pol="pol", datum_rodjenja=("date of birth" if EN else "datum rođenja"),
                                    otac=("sire" if EN else "otac"), majka=("dam" if EN else "majka"), status="status", stado=("herd" if EN else "stado"),
                                    poreklo="poreklo", poreklo_od=("origin from" if EN else "poreklo od"))
                promene = [f"{n}: {red.get(k) or '–'} → {novi.get(k) or '–'}" for k, n in nazivi_polja.items()
                           if (red.get(k) or "") != (novi.get(k) or "")]
                if promene:
                    self.ist.dodaj(nid, AUTO, ("Details changed – " if EN else "Izmena podataka – ") + "; ".join(promene), automatski=True)
                red.update(novi)
                if staro != nid:
                    for r in self.tab.redovi:
                        if r.get("otac") == staro:
                            r["otac"] = nid
                        if r.get("majka") == staro:
                            r["majka"] = nid
            else:
                novi["uneto"] = sada()
                self.tab.redovi.append(novi)
                self.ist.dodaj(nid, AUTO, ("Animal added to the records" if EN else "Grlo upisano u evidenciju") +
                               (f" ({novi['poreklo']}{' – ' + novi['poreklo_od'] if novi['poreklo_od'] else ''})"
                                if novi["poreklo"] else ""), automatski=True)
                if dat:     # rodjenje se upisuje i u istoriju roditelja
                    for rod, drugi in ((mj, o), (o, mj)):
                        rid = self.model.nadji(rod) if rod else None
                        if rid and not self.model.A[rid]["osnivac"]:
                            self.ist.dodaj(rid, ("Birth" if EN else "Porođaj") if rod == mj else ("Offspring" if EN else "Potomak"),
                                           (f"Offspring born {nid} ({'male' if pol.get() == 'm' else 'female'})" if EN else f"Rođen potomak {nid} ({'muško' if pol.get() == 'm' else 'žensko'})"),
                                           datum=parsiraj_datum(dat).strftime(("%d/%m/%Y" if EN else "%d.%m.%Y")),
                                           partner=self.model.nadji(drugi) or drugi or "", automatski=True)
            self.pod["poslednje"] = dict(vrsta=novi["vrsta"], rasa=novi["rasa"], stado=novi["stado"])
            self.sacuvaj_podesavanja()
            win.grab_release()
            win.destroy()
            self.promena((f"Saved: {nid}" if EN else f"Sačuvano: {nid}"))
            if dalje:
                self.forma()

        def obrisi():
            if self.obrisi_grla([red["id"]], parent=win):
                win.destroy()

        fb = tk.Frame(win, bg=SURF)
        fb.pack(fill="x", padx=26, pady=(0, 20))
        tk.Frame(win, bg=LINE, height=1).place(in_=fb, relx=0, y=-10, relwidth=1)
        if red and red.get("status") != "obrisano":
            self.btn(fb, ("Delete animal" if EN else "Obriši grlo"), obrisi, "Danger").pack(side="left")
        self.btn(fb, ("Save" if EN else "Sačuvaj"), sacuvaj, "Primary").pack(side="right")
        if not red:
            self.btn(fb, ("Save and add another" if EN else "Sačuvaj i dodaj još"), lambda: sacuvaj(True)).pack(side="right", padx=8)
        self.btn(fb, ("Cancel" if EN else "Otkaži"), win.destroy).pack(side="right", padx=(0, 8) if red else 0)
        win.bind("<Return>", lambda e: sacuvaj())
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + max(20, (self.root.winfo_height() - win.winfo_height()) // 2)
        win.geometry(f"+{x}+{y}")
        (e_id if not v.get("id") else vr).focus_set()



# =============================================================== FARMER PRO
# Promena jezika, štampa i PDF (rodoslovni list, plan parenja, spisak stada) i statistika.

def T(sr, en):
    return en if EN else sr


def _html_esc(t):
    return (str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


_HTML_STIL = """
*{box-sizing:border-box} body{font-family:'Segoe UI',Arial,sans-serif;color:#18221C;margin:0;background:#F3F5F1}
.list{max-width:900px;margin:24px auto;background:#fff;padding:34px 40px;border-radius:10px;box-shadow:0 2px 14px rgba(0,0,0,.08)}
.zag{display:flex;align-items:center;gap:16px;border-bottom:3px solid #2E5E45;padding-bottom:14px;margin-bottom:18px}
.zag img{width:56px;height:56px} .zag h1{margin:0;font-size:26px;color:#2E5E45} .zag .pod{color:#56645A;font-size:13px}
.zag .desno{margin-left:auto;text-align:right;color:#56645A;font-size:12px}
h2{font-size:15px;color:#2E5E45;margin:22px 0 8px;text-transform:uppercase;letter-spacing:.04em}
table{border-collapse:collapse;width:100%;font-size:12.5px} th,td{border:1px solid #D6DDD3;padding:5px 7px;text-align:left;vertical-align:middle}
th{background:#E9EDE6;font-weight:600} tr:nth-child(even) td{background:#FAFBF9}
.podaci td{border:none;padding:3px 10px 3px 0} .podaci td:first-child{color:#56645A;width:150px}
.rod td{border:1px solid #C9D3C6;height:34px;font-size:11.5px;background:#fff !important}
.rod .m{border-left:4px solid #3B6FB6} .rod .z{border-left:4px solid #C2577A} .rod .n{color:#9AA59D;border-left:4px solid #D6DDD3}
.rod b{font-size:12.5px} .rod small{color:#56645A}
.znak{display:inline-block;padding:2px 9px;border-radius:10px;font-weight:600;font-size:12px}
.ok{background:#DDF1E3;color:#23804A} .warn{background:#FBEBCB;color:#9A5C00} .bad{background:#F8DEDA;color:#B3322B}
.dno{margin-top:26px;border-top:1px solid #D6DDD3;padding-top:8px;color:#56645A;font-size:11px;display:flex;justify-content:space-between}
.potpis{margin-top:40px;display:flex;gap:60px} .potpis div{flex:1;border-top:1px solid #18221C;padding-top:4px;font-size:11px;color:#56645A}
.dugme{position:fixed;top:14px;right:14px;background:#2E5E45;color:#fff;border:none;padding:11px 18px;border-radius:8px;font-size:14px;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,.2)}
.sazetak{display:flex;gap:10px;flex-wrap:wrap} .sazetak div{background:#F3F5F1;border-radius:8px;padding:8px 14px;font-size:12px}
.sazetak b{display:block;font-size:18px;color:#2E5E45}
@media print{body{background:#fff}.list{box-shadow:none;margin:0;max-width:none;padding:0}.dugme{display:none}
 h2{break-after:avoid} tr{break-inside:avoid} @page{size:A4;margin:14mm}}
"""


def _otvori_html(naziv, naslov, podnaslov, telo):
    import tempfile
    logo = LOGO.get(64, "")
    if isinstance(logo, (tuple, list)):
        logo = "".join(logo)
    html = (f"<!doctype html><html lang='{JEZIK}'><head><meta charset='utf-8'><title>{_html_esc(naslov)}</title>"
            f"<style>{_HTML_STIL}</style></head><body>"
            f"<button class='dugme' onclick='window.print()'>{T('🖨 Štampaj / Sačuvaj kao PDF', '🖨 Print / Save as PDF')}</button>"
            f"<div class='list'><div class='zag'><img src='data:image/png;base64,{logo}' alt=''>"
            f"<div><h1>{_html_esc(naslov)}</h1><div class='pod'>{_html_esc(podnaslov)}</div></div>"
            f"<div class='desno'>Farmer {VERZIJA}<br>{fmt_datum(date.today())}</div></div>{telo}"
            f"<div class='dno'><span>{T('Napravljeno u programu Farmer', 'Made with Farmer')}</span>"
            f"<span>{_html_esc(os.path.basename(getattr(_html_esc, 'tablica', '') or ''))}</span></div></div></body></html>")
    folder = os.path.join(tempfile.gettempdir(), "Farmer-stampa")
    os.makedirs(folder, exist_ok=True)
    put = os.path.join(folder, naziv + ".html")
    with open(put, "w", encoding="utf-8") as f:
        f.write(html)
    try:
        if sys.platform.startswith("win"):
            os.startfile(put)
        else:
            import webbrowser
            webbrowser.open("file://" + put)
    except Exception:
        messagebox.showinfo("Farmer", T("Dokument je sačuvan ovde:\n", "The document was saved here:\n") + put)
    return put


def _znak(f, prag):
    t, boja = procena(f, prag)
    k = "ok" if boja == OK else "warn" if boja == WARN else "bad"
    return f"<span class='znak {k}'>{pct(f)} · {_html_esc(t)}</span>"


def _deca(m, x):
    return [y for y, (o, mm) in m.P.items() if x in (o, mm) and y in m.A and not m.A[y]["osnivac"]]


def _app_stampaj_rodoslov(self, x):
    m = self.model
    if x not in m.A:
        return
    _html_esc.tablica = self.tab.putanja
    a = m.A[x]
    f = m.inbr(x)
    red = lambda k, v: f"<tr><td>{_html_esc(k)}</td><td><b>{_html_esc(v)}</b></td></tr>" if v else ""
    o, mj = m.P.get(x, (None, None))
    podaci = ("<table class='podaci'>" + red(T("Oznaka", "ID"), x) + red(T("Ušna markica", "Ear tag"), a.get("markica"))
              + red(T("Vrsta", "Species"), a.get("vrsta")) + red(T("Rasa", "Breed"), a.get("rasa"))
              + red(T("Pol", "Sex"), m.pol_naziv(x)) + red(T("Datum rođenja", "Date of birth"), fmt_datum(a.get("datum")))
              + red(T("Starost", "Age"), fmt_starost(starost_meseci(a.get("datum"))))
              + red(T("Otac", "Sire"), o) + red(T("Majka", "Dam"), mj)
              + red(T("Stado", "Herd"), a.get("stado")) + red(T("Poreklo", "Origin"), a.get("poreklo"))
              + f"<tr><td>{T('Inbriding (F)', 'Inbreeding (F)')}</td><td>{_znak(f, self.prag)}</td></tr></table>")
    # rodoslov u 4 generacije
    niz = [[x]]
    for g in range(4):
        sl = []
        for y in niz[-1]:
            sl.extend(m.P.get(y, (None, None)) if y else (None, None))
        niz.append(sl)
    gens = max([2] + [g for g in range(1, 5) if any(niz[g])])   # prazna kolena se ne prikazuju
    redovi = 2 ** gens
    tab = "<table class='rod'><tr>" + "".join(f"<th>{T(n_sr, n_en)}</th>" for n_sr, n_en in
                                             (("Roditelji", "Parents"), ("Babe i dede", "Grandparents"),
                                              ("Prababe i pradede", "Great-grandparents"),
                                              ("4. koleno", "4th generation"))[:gens]) + "</tr>"
    for r in range(redovi):
        tab += "<tr>"
        for g in range(1, gens + 1):
            span = redovi // (2 ** g)
            if r % span:
                continue
            y = niz[g][r // span]
            if y and y in m.A:
                b = m.A[y]
                kl = "m" if b.get("pol") == "m" else "z"
                det = " · ".join(t for t in (b.get("markica"), b.get("rasa"),
                                              str(b["datum"].year) if b.get("datum") else "") if t)
                fy = m.inbr(y)
                tab += (f"<td rowspan='{span}' class='{kl}'><b>{_html_esc(y)}</b>"
                        + (f"<br><small>{_html_esc(det)}</small>" if det else "")
                        + (f"<br><small>F {pct(fy)}</small>" if fy > 0 else "") + "</td>")
            else:
                tab += f"<td rowspan='{span}' class='n'>{T('nepoznat', 'unknown')}</td>"
        tab += "</tr>"
    tab += "</table>"
    komp = m.kompletnost(x, gens)
    komp_t = " · ".join(f"{g}. {T('koleno', 'gen.')}: {n}/{u}" for g, n, u in komp)
    preci = [(d, p) for d, p in m.udeli_predaka(x) if d > 0][:8]
    preci_t = ""
    if preci:
        preci_t = (f"<h2>{T('Najveći udeo gena', 'Largest gene contributions')}</h2><table><tr><th>{T('Predak', 'Ancestor')}</th>"
                   f"<th>{T('Rasa', 'Breed')}</th><th>{T('Udeo gena', 'Gene share')}</th></tr>"
                   + "".join(f"<tr><td>{_html_esc(p)}</td><td>{_html_esc(m.A[p].get('rasa', ''))}</td><td>{pct(d)}</td></tr>"
                             for d, p in preci) + "</table>")
    deca = _deca(m, x)
    deca_t = ""
    if deca:
        deca_t = (f"<h2>{T('Potomci', 'Offspring')} ({len(deca)})</h2><table><tr><th>{T('Oznaka', 'ID')}</th>"
                  f"<th>{T('Pol', 'Sex')}</th><th>{T('Datum rođenja', 'Date of birth')}</th><th>{T('Drugi roditelj', 'Other parent')}</th></tr>"
                  + "".join(f"<tr><td>{_html_esc(y)}</td><td>{_html_esc(m.pol_naziv(y))}</td>"
                            f"<td>{fmt_datum(m.A[y].get('datum'))}</td>"
                            f"<td>{_html_esc(next((p for p in m.P.get(y, (None, None)) if p and p != x), ''))}</td></tr>"
                            for y in sorted(deca, key=sort_key)[:40]) + "</table>")
    ist = [z for z in self.ist.za(x, auto=False)][:20]
    ist_t = ""
    if ist:
        ist_t = (f"<h2>{T('Istorija', 'History')}</h2><table><tr><th>{T('Datum', 'Date')}</th><th>{T('Događaj', 'Event')}</th>"
                 f"<th>{T('Opis', 'Description')}</th></tr>"
                 + "".join(f"<tr><td>{_html_esc(z.get('datum'))}</td><td>{_html_esc(z.get('dogadjaj'))}</td>"
                           f"<td>{_html_esc(' '.join(t for t in (z.get('partner'), z.get('vrednost'), z.get('opis')) if t))}</td></tr>"
                           for z in ist) + "</table>")
    telo = (podaci + f"<h2>{T('Rodoslov', 'Pedigree')}</h2>" + tab
            + f"<div style='font-size:11.5px;color:#56645A;margin-top:6px'>{T('Poznati preci', 'Known ancestors')}: {komp_t}</div>"
            + preci_t + deca_t + ist_t
            + f"<div class='potpis'><div>{T('Odgajivač', 'Breeder')}</div><div>{T('Datum i potpis', 'Date and signature')}</div></div>")
    _otvori_html(f"rodoslov-{x}", T("Rodoslovni list", "Pedigree certificate"), f"{x} · {m.pol_naziv(x)}"
                 + (f" · {a['rasa']}" if a.get("rasa") else ""), telo)


def _app_stampaj_plan(self):
    m = self.model
    _html_esc.tablica = self.tab.putanja
    akt = m.grla(True)
    zenke = [a for a in akt if a["pol"] == "z"]
    muz = [a for a in akt if a["pol"] == "m"]
    ista = self.ui.get("ista_rasa")
    redovi = ""
    for z in sorted(zenke, key=lambda a: sort_key(a["id"])):
        opc = sorted((m.kinship(z["id"], x["id"]), x["id"]) for x in muz
                     if x["vrsta"] == z["vrsta"] and (not ista or x["rasa"] == z["rasa"]))
        if not opc:
            redovi += f"<tr><td><b>{_html_esc(z['id'])}</b></td><td>{_html_esc(z['rasa'])}</td><td colspan='3'>{T('nema odgovarajućeg mužjaka', 'no suitable male')}</td></tr>"
            continue
        celije = "".join(f"<td>{_html_esc(i)}<br>{_znak(f, self.prag)}</td>" for f, i in opc[:3])
        celije += "<td></td>" * (3 - min(3, len(opc)))
        redovi += f"<tr><td><b>{_html_esc(z['id'])}</b><br><small>{_html_esc(z.get('markica', ''))}</small></td><td>{_html_esc(z['rasa'])}</td>{celije}</tr>"
    telo = (f"<div class='sazetak'><div><b>{len(zenke)}</b>{T('ženskih grla', 'females')}</div><div><b>{len(muz)}</b>"
            f"{T('muških grla', 'males')}</div><div><b>{pct(self.prag)}</b>{T('granica rizika', 'risk limit')}</div></div>"
            f"<h2>{T('Predlog parenja (najmanje srodni mužjaci prvi)', 'Mating suggestions (least related males first)')}</h2>"
            f"<table><tr><th>{T('Ženka', 'Female')}</th><th>{T('Rasa', 'Breed')}</th><th>{T('1. izbor', '1st choice')}</th>"
            f"<th>{T('2. izbor', '2nd choice')}</th><th>{T('3. izbor', '3rd choice')}</th></tr>{redovi}</table>"
            f"<div style='font-size:11.5px;color:#56645A;margin-top:8px'>"
            f"{T('Procenat je očekivani inbriding potomka (F).', 'The percentage is the expected inbreeding of the offspring (F).')}</div>")
    _otvori_html("plan-parenja", T("Plan parenja", "Mating plan"), T("Predlog za celo stado", "Suggestions for the whole herd"), telo)


def _app_stampaj_spisak(self):
    m = self.model
    _html_esc.tablica = self.tab.putanja
    akt = sorted(m.grla(True), key=lambda a: (a.get("stado", ""), a.get("vrsta", ""), sort_key(a["id"])))
    po_vrsti = {}
    for a in akt:
        k = (a.get("vrsta", ""), a.get("pol"))
        po_vrsti[k] = po_vrsti.get(k, 0) + 1
    vrste = sorted({k[0] for k in po_vrsti})
    saz = "".join(f"<div><b>{po_vrsti.get((v, 'z'), 0) + po_vrsti.get((v, 'm'), 0) + po_vrsti.get((v, None), 0)}</b>"
                  f"{_html_esc(v)} ({po_vrsti.get((v, 'z'), 0)} {T('ž', 'f')} / {po_vrsti.get((v, 'm'), 0)} {T('m', 'm')})</div>"
                  for v in vrste)
    redovi = ""
    stado = None
    for a in akt:
        if a.get("stado", "") != stado:
            stado = a.get("stado", "")
            redovi += f"<tr><th colspan='9'>{T('Stado', 'Herd')}: {_html_esc(stado or T('bez naziva', 'unnamed'))}</th></tr>"
        o, mj = m.P.get(a["id"], (None, None))
        redovi += (f"<tr><td><b>{_html_esc(a['id'])}</b></td><td>{_html_esc(a.get('markica'))}</td><td>{_html_esc(a.get('vrsta'))}</td>"
                   f"<td>{_html_esc(a.get('rasa'))}</td><td>{_html_esc(m.pol_naziv(a['id']))}</td><td>{fmt_datum(a.get('datum'))}</td>"
                   f"<td>{_html_esc(o or '')}</td><td>{_html_esc(mj or '')}</td><td>{pct(m.inbr(a['id']))}</td></tr>")
    telo = (f"<div class='sazetak'><div><b>{len(akt)}</b>{T('grla u zapatu', 'animals in herd')}</div>{saz}</div>"
            f"<h2>{T('Spisak grla', 'Animal list')}</h2><table><tr><th>{T('Oznaka', 'ID')}</th><th>{T('Markica', 'Ear tag')}</th>"
            f"<th>{T('Vrsta', 'Species')}</th><th>{T('Rasa', 'Breed')}</th><th>{T('Pol', 'Sex')}</th><th>{T('Rođeno', 'Born')}</th>"
            f"<th>{T('Otac', 'Sire')}</th><th>{T('Majka', 'Dam')}</th><th>F</th></tr>{redovi}</table>")
    _otvori_html("spisak-stada", T("Spisak stada", "Herd list"), T("Sva grla u zapatu", "All animals in the herd"), telo)


def _app_promeni_jezik(self):
    """Promena jezika odmah, bez ponovnog pokretanja programa."""
    global EN, JEZIK
    novi = "sr" if EN else "en"
    strana = self.strana if self.strana != "obrisana" else "grla"
    for w in (self.karton_win, getattr(self, "ist_win", None), getattr(self, "stablo_win", None)):
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
    for sacuvaj in (self.ist.sacuvaj, self.pods.sacuvaj):
        try:
            sacuvaj()
        except Exception:
            pass
    self.pod["jezik"] = novi
    self.sacuvaj_podesavanja()
    JEZIK, EN = novi, novi == "en"
    _jezicke_konstante()
    # podaci se ponovo čitaju - nazivi događaja, vrsta i porekla se prevode na novi jezik
    try:
        self.tab = Tablica(self.tab.putanja)
    except Exception:
        pass
    self.model = Model(self.tab.redovi)
    self.ist = Istorija(self.tab.putanja)
    self.pods = Podsetnici(self.tab.putanja)
    self.ui.update(q="", pol="", poreklo="", partner="", partner_upit="", partner_vise=[], sA="", sB="")
    self.karton_win = None
    for w in self.root.winfo_children():
        w.destroy()
    self.shell()
    self.prikazi(strana)
    try:
        self.toast(T("Jezik: srpski", "Language: English"))
    except Exception:
        pass


# ---------------------------------------------------------------- statistika
def _crtaj_stubice(self, parent, naslov, podaci, boja=BRAND, sirina=520, visina=200, fmt=str):
    o, c = self.card(parent)
    o.pack(fill="x", pady=(0, 14))
    self.lbl(c, naslov, 11, "bold").pack(anchor="w")
    if not podaci:
        self.lbl(c, T("Još nema podataka.", "No data yet."), 9, fg=INK2).pack(anchor="w", pady=6)
        return
    cv = tk.Canvas(c, width=sirina, height=visina, bg=SURF, highlightthickness=0)
    cv.pack(anchor="w", pady=(8, 0), fill="x")
    def nacrtaj(e=None):
        cv.delete("all")
        W = max(200, cv.winfo_width() or sirina)
        H = visina
        lev, dno, vrh = 8, 34, 18
        mx = max(v for _, v in podaci) or 1
        n = len(podaci)
        kor = (W - lev * 2) / n
        bw = min(46, kor * 0.68)
        cv.create_line(lev, H - dno, W - lev, H - dno, fill=LINE)
        for i, (k, v) in enumerate(podaci):
            x = lev + kor * i + kor / 2
            h = (H - dno - vrh) * (v / mx)
            cv.create_rectangle(x - bw / 2, H - dno - h, x + bw / 2, H - dno, fill=boja, outline="")
            cv.create_text(x, H - dno - h - 8, text=fmt(v), fill=INK, font=self.f(9, "bold"))
            cv.create_text(x, H - dno + 12, text=str(k)[:12], fill=INK2, font=self.f(8))
    cv.bind("<Configure>", nacrtaj)
    nacrtaj()


def _app_s_statistika(self):
    m = self.model
    sf = ScrollFrame(self.main, bg=BG)
    sf.pack(fill="both", expand=True)
    body = tk.Frame(sf.inner, bg=BG)
    body.pack(fill="both", expand=True, padx=32, pady=28)
    self.zaglavlje(body, T("Statistika", "Statistics"), T("Pregled stada u brojevima i grafikonima.",
                                                          "Your herd in numbers and charts."),
                   akcije=((T("🖨 Spisak stada", "🖨 Herd list"), self.stampaj_spisak, "Secondary"),))
    akt = m.grla(True)
    if not akt:
        self.napomena(body, T("U zapatu još nema grla.", "There are no animals in the herd yet."))
        return
    fs = [m.inbr(a["id"]) for a in akt]
    zen = sum(1 for a in akt if a["pol"] == "z")
    muz = sum(1 for a in akt if a["pol"] == "m")
    iznad = sum(1 for f in fs if f > self.prag)
    red = tk.Frame(body, bg=BG)
    red.pack(fill="x", pady=(0, 14))
    for vr, opis, boja in ((len(akt), T("grla u zapatu", "animals in herd"), BRAND),
                           (f"{zen} / {muz}", T("ženska / muška", "female / male"), INK),
                           (pct(sum(fs) / len(fs)), T("prosečan inbriding", "average inbreeding"), INK),
                           (iznad, T("iznad granice rizika", "above the risk limit"), BAD if iznad else OK)):
        o, c = self.card(red, padx=16, pady=12)
        o.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl(c, str(vr), 20, "bold", fg=boja).pack(anchor="w")
        self.lbl(c, opis, 9, fg=INK2).pack(anchor="w")
    # po rasi
    rase = {}
    for a in akt:
        k = a.get("rasa") or T("bez rase", "no breed")
        rase[k] = rase.get(k, 0) + 1
    _crtaj_stubice(self, body, T("Grla po rasi", "Animals by breed"), sorted(rase.items(), key=lambda t: -t[1])[:10])
    # rođenja po godinama
    god = {}
    for a in m.grla(False):
        if a.get("datum"):
            god[a["datum"].year] = god.get(a["datum"].year, 0) + 1
    _crtaj_stubice(self, body, T("Rođena grla po godinama", "Animals born per year"), sorted(god.items())[-10:], boja="#3B6FB6")
    # inbriding
    klase = [(T("0%", "0%"), 0), ("<3,1%" if not EN else "<3.1%", 0), ("<6,25%" if not EN else "<6.25%", 0),
             ("<12,5%" if not EN else "<12.5%", 0), ("≥12,5%" if not EN else "≥12.5%", 0)]
    cnt = [0] * 5
    for f in fs:
        cnt[0 if f == 0 else 1 if f < 0.03125 else 2 if f < 0.0625 else 3 if f < 0.125 else 4] += 1
    _crtaj_stubice(self, body, T("Inbriding grla u zapatu", "Inbreeding of animals in the herd"),
                   [(klase[i][0], cnt[i]) for i in range(5)], boja=WARN)
    # porođaji po mesecima (poslednjih 12)
    porod = DOGADJAJI[2]
    danas = date.today()
    meseci = []
    for i in range(11, -1, -1):
        y, mm = danas.year, danas.month - i
        while mm <= 0:
            mm += 12
            y -= 1
        meseci.append((y, mm))
    br = {k: 0 for k in meseci}
    for z in self.ist.zapisi:
        if z.get("dogadjaj") == porod:
            d = parsiraj_datum(z.get("datum"))
            if d and (d.year, d.month) in br:
                br[(d.year, d.month)] += 1
    if any(br.values()):
        _crtaj_stubice(self, body, T("Porođaji u poslednjih 12 meseci", "Births in the last 12 months"),
                       [(f"{mm:02d}/{str(y)[2:]}", br[(y, mm)]) for y, mm in meseci], boja=OK)


def _app_s_stampa(self):
    sf = ScrollFrame(self.main, bg=BG)
    sf.pack(fill="both", expand=True)
    body = tk.Frame(sf.inner, bg=BG)
    body.pack(fill="both", expand=True, padx=32, pady=28)
    self.zaglavlje(body, T("Štampa i PDF", "Print and PDF"),
                   T("Dokument se otvara u pregledaču. Tamo klikni „Štampaj / Sačuvaj kao PDF“.",
                     "The document opens in your browser. Click “Print / Save as PDF” there."))
    def stavka(naslov, opis, dugme, cmd, dodatak=None):
        o, c = self.card(body)
        o.pack(fill="x", pady=(0, 12))
        red = tk.Frame(c, bg=SURF)
        red.pack(fill="x")
        lev = tk.Frame(red, bg=SURF)
        lev.pack(side="left", fill="x", expand=True)
        self.lbl(lev, naslov, 12, "bold").pack(anchor="w")
        self.lbl(lev, opis, 9, fg=INK2, justify="left", wraplength=520).pack(anchor="w", pady=(2, 0))
        self.btn(red, dugme, cmd, "Primary").pack(side="right")
        if dodatak:
            dodatak(red)
    izbor = tk.StringVar()
    def birac(red):
        ids = [a["id"] for a in self.model.grla(False)]
        cb = ttk.Combobox(red, textvariable=izbor, values=ids, width=16, font=self.f(10))
        cb.pack(side="right", padx=10)
        if ids:
            izbor.set(ids[0])
    def rodoslov():
        x = self.model.nadji(izbor.get()) if izbor.get() else None
        if not x:
            messagebox.showwarning("Farmer", T("Izaberi ili upiši oznaku grla.", "Choose or type an animal ID."))
            return
        self.stampaj_rodoslov(x)
    stavka(T("Rodoslovni list grla", "Pedigree certificate"),
           T("Podaci o grlu, rodoslov u 4 kolena, inbriding, potomci i istorija. Za prodaju, sajmove i matičnu evidenciju.",
             "Animal data, 4-generation pedigree, inbreeding, offspring and history. For sales, shows and registries."),
           T("🖨 Napravi", "🖨 Create"), rodoslov, birac)
    stavka(T("Plan parenja", "Mating plan"),
           T("Za svaku ženku tri najmanje srodna mužjaka i očekivani inbriding potomka.",
             "For each female the three least related males and the expected inbreeding of the offspring."),
           T("🖨 Napravi", "🖨 Create"), self.stampaj_plan)
    stavka(T("Spisak stada", "Herd list"),
           T("Sva grla u zapatu po stadima, sa markicama, roditeljima i inbridingom. Za veterinara ili inspekciju.",
             "All animals in the herd by herd group, with ear tags, parents and inbreeding. For the vet or inspection."),
           T("🖨 Napravi", "🖨 Create"), self.stampaj_spisak)


App.stampaj_rodoslov = _app_stampaj_rodoslov
App.stampaj_plan = _app_stampaj_plan
App.stampaj_spisak = _app_stampaj_spisak
App.promeni_jezik = _app_promeni_jezik
App.s_statistika = _app_s_statistika
App.s_stampa = _app_s_stampa



def _jezicke_konstante():
    """Ponovo postavi nazive koji zavise od jezika (posle promene jezika)."""
    global AUTO, DOGADJAJI, GRAVIDNOST_PROFILI, GRUPE, NAZIVI, PARENJE, POREKLA, REDOSLEDI, STADO_PODMLADAK, TER, TER_CIKLUS, VRSTE
    REDOSLEDI = [("Last added first" if EN else "Poslednje upisana prvo"), ("First added first" if EN else "Prvo upisana prvo"), ("By tag" if EN else "Po oznaci"), ("Youngest first" if EN else "Najmlađa prvo")]
    POREKLA = [("Home bred" if EN else "Sopstveni odgoj"), ("Purchased" if EN else "Kupljeno"), ("Imported" if EN else "Uvoz")]
    VRSTE = [("cattle" if EN else "goveda"), ("sheep" if EN else "ovce"), ("goats" if EN else "koze"), ("pigs" if EN else "svinje"), ("horses" if EN else "konji")]
    if EN:
        NAZIVI = {   # species prefix (English and Serbian) -> (male, female, young, young plural)
            "cat": ("bull", "cow", "calf", "calves"), "cow": ("bull", "cow", "calf", "calves"),
            "bul": ("bull", "cow", "calf", "calves"), "gov": ("bull", "cow", "calf", "calves"),
            "she": ("ram", "ewe", "lamb", "lambs"), "ewe": ("ram", "ewe", "lamb", "lambs"), "ovc": ("ram", "ewe", "lamb", "lambs"),
            "goa": ("buck", "doe", "kid", "kids"), "koz": ("buck", "doe", "kid", "kids"),
            "pig": ("boar", "sow", "piglet", "piglets"), "sow": ("boar", "sow", "piglet", "piglets"),
            "svi": ("boar", "sow", "piglet", "piglets"),
            "hor": ("stallion", "mare", "foal", "foals"), "kon": ("stallion", "mare", "foal", "foals"),
        }
    else:
        NAZIVI = {
            "gov": ("bik", "krava", "tele", "telad"), "bik": ("bik", "krava", "tele", "telad"),
            "kra": ("bik", "krava", "tele", "telad"), "ovc": ("ovan", "ovca", "jagnje", "jagnjad"),
            "ova": ("ovan", "ovca", "jagnje", "jagnjad"), "koz": ("jarac", "koza", "jare", "jarad"),
            "svi": ("nerast", "krmača", "prase", "prasad"), "kon": ("pastuv", "kobila", "ždrebe", "ždrebad"),
        }
    TER = ("In heat" if EN else "Tera se")
    TER_CIKLUS = {("cattle" if EN else "goveda"): 21, ("sheep" if EN else "ovce"): 17, ("goats" if EN else "koze"): 21, ("pigs" if EN else "svinje"): 21, ("horses" if EN else "konji"): 21}
    PARENJE = ("Mating / insemination" if EN else "Parenje / osemenjavanje")
    STADO_PODMLADAK = ("Young stock" if EN else "Podmladak")
    GRAVIDNOST_PROFILI = {
        ("romanov" if EN else "romanovska"): (("Romanov sheep" if EN else "Romanovska ovca"), ("sheep" if EN else "ovce"), ("romanov",), 138, 143, 140),
        ("sheep" if EN else "ovce"): (("Common sheep" if EN else "Obična ovca"), ("sheep" if EN else "ovce"), (), 145, 152, 150),
        ("goats" if EN else "koze"): (("Goat" if EN else "Koza"), ("goats" if EN else "koze"), (), 145, 151, 150),
        ("pigs" if EN else "svinje"): (("Pig" if EN else "Svinja"), ("pigs" if EN else "svinje"), (), 110, 120, 114),
        ("cattle" if EN else "goveda"): (("Cow" if EN else "Krava"), ("cattle" if EN else "goveda"), (), 275, 290, 283),
        ("horses" if EN else "konji"): (("Mare" if EN else "Kobila"), ("horses" if EN else "konji"), (), 320, 360, 340),
    }
    DOGADJAJI = [("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("In heat" if EN else "Tera se"), ("Birth" if EN else "Porođaj"), ("Vaccination" if EN else "Vakcinacija"), ("Treatment" if EN else "Lečenje"), ("Weighing" if EN else "Merenje težine"),
                 ("Move" if EN else "Premeštanje"), ("Sale" if EN else "Prodaja"), ("Death" if EN else "Uginuće"), ("Note" if EN else "Napomena")]
    AUTO = ("Record change" if EN else "Promena u evidenciji")
    GRUPE = [(("Matings" if EN else "Parenja"), (("Mating / insemination" if EN else "Parenje / osemenjavanje"), ("In heat" if EN else "Tera se"))),
             (("Treatments" if EN else "Lečenja"), (("Treatment" if EN else "Lečenje"), ("Vaccination" if EN else "Vakcinacija"))),
             (("Births" if EN else "Porođaji"), (("Birth" if EN else "Porođaj"), ("Offspring" if EN else "Potomak")))]


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


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        try:   # da Windows na traci zadataka prikaže logo programa, a ne Python
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(("Farmer.English" if EN else "Farmer.Program"))
        except Exception:
            pass
    sys.setrecursionlimit(20000)
    root = tk.Tk()

    def greska(exc, val, tb):
        messagebox.showerror(("Error" if EN else "Greška"), ("An error occurred:\n\n" if EN else "Došlo je do greške:\n\n") + "".join(traceback.format_exception_only(exc, val)))
    root.report_callback_exception = greska
    App(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(("Farmer – error" if EN else "Farmer – greška"), traceback.format_exc())
        except Exception:
            print(traceback.format_exc())
