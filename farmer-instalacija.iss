; Instalacija za Farmer – jedan program za oba jezika (srpski / English); pravi je GitHub Actions preko Inno Setup-a
#ifndef AppVersion
  #define AppVersion "1.0"
#endif

[Setup]
AppId={{6B1F3C2A-8E4D-4F7A-9C11-FA2E0B7D5A01}
AppName=Farmer
AppVersion={#AppVersion}
AppPublisher=Nikola Marićević
DefaultDirName={autopf}\Farmer
DefaultGroupName=Farmer
UninstallDisplayIcon={app}\Farmer.exe
SetupIconFile=farmer.ico
OutputDir=dist
OutputBaseFilename=Farmer-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
CloseApplications=force

[Tasks]
Name: "desktopicon"; Description: "Ikonica na radnoj površini / Desktop icon"; GroupDescription: "Dodatno / Additional:"

[Files]
Source: "dist\Farmer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "farmer.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Farmer"; Filename: "{app}\Farmer.exe"
Name: "{group}\Podaci - Data (Dokumenti\Farmer)"; Filename: "{userdocs}\Farmer"
Name: "{group}\Ukloni Farmer - Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Farmer"; Filename: "{app}\Farmer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Farmer.exe"; Description: "Pokreni Farmer / Start Farmer"; Flags: nowait postinstall skipifsilent

[Code]
// Pre instalacije zatvori Farmer ako je otvoren (da instalacija ne zapne)
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM Farmer.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Result := '';
end;
