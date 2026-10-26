; Instalacija za HerdDoc (ranije Farmer) – jedan program za oba jezika (srpski / English); pravi je GitHub Actions preko Inno Setup-a
; AppId je isti kao kod Farmera, pa se nova verzija instalira preko stare (podaci i podešavanja ostaju).
#ifndef AppVersion
  #define AppVersion "1.0"
#endif

[Setup]
AppId={{6B1F3C2A-8E4D-4F7A-9C11-FA2E0B7D5A01}
AppName=HerdDoc
AppVersion={#AppVersion}
AppPublisher=Nikola Marićević
DefaultDirName={autopf}\HerdDoc
DefaultGroupName=HerdDoc
UsePreviousGroup=no
SetupIconFile=farmer.ico
OutputDir=dist
OutputBaseFilename=HerdDoc-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
CloseApplications=force

[Tasks]
Name: "desktopicon"; Description: "Ikonica na radnoj površini / Desktop icon"; GroupDescription: "Dodatno / Additional:"

[InstallDelete]
; ostaci starog naziva (Farmer): program i prečice
Type: files; Name: "{app}\Farmer.exe"
Type: files; Name: "{autodesktop}\Farmer.lnk"
Type: filesandordirs; Name: "{autoprograms}\Farmer"

[Files]
Source: "dist\HerdDoc.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "farmer.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HerdDoc"; Filename: "{app}\HerdDoc.exe"
Name: "{group}\Podaci - Data"; Filename: "{code:FolderPodataka}"
Name: "{group}\Ukloni HerdDoc - Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\HerdDoc"; Filename: "{app}\HerdDoc.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\HerdDoc.exe"; Description: "Pokreni HerdDoc / Start HerdDoc"; Flags: nowait postinstall skipifsilent

[Code]
// Pre instalacije zatvori program ako je otvoren (da instalacija ne zapne) – i pod starim imenom
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM HerdDoc.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM Farmer.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Result := '';
end;

// Prečica "Podaci" vodi u folder koji program stvarno koristi: stari Dokumenti\Farmer ako postoji, inače Dokumenti\HerdDoc
function FolderPodataka(Param: String): String;
begin
  if DirExists(ExpandConstant('{userdocs}\Farmer')) and not DirExists(ExpandConstant('{userdocs}\HerdDoc')) then
    Result := ExpandConstant('{userdocs}\Farmer')
  else
    Result := ExpandConstant('{userdocs}\HerdDoc');
end;
