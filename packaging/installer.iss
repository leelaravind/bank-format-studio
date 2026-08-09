; Inno Setup script — Bank Statement Format Studio (per-user install, offline).
; Build after PyInstaller:  iscc packaging\installer.iss
; Signing (OWNER ACTION - certificate required): configure SignTool below or
; sign BankFormatStudio.exe + the installer with signtool/Trusted Signing in CI.

#define AppName "Bank Statement Format Studio"
#define AppVersion "1.0.0"
; OWNER ACTION: set the legal entity name before release
#define AppPublisher "OWNER-LEGAL-ENTITY-NAME"
#define DistDir "dist\\BankFormatStudio"

[Setup]
AppId={{6E7B62F1-9C64-4A7E-A87A-BFS0V1000001}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
; SEC-22: per-user install, no elevation
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputBaseFilename=BankFormatStudio-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; No network access anywhere in the installer (fully offline).
; OWNER ACTION: uncomment when signing is configured
; SignTool=bfs_sign $f

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
; LGPL obligation artefacts must ship in the install dir:
Source: "THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "licenses\*"; DestDir: "{app}\licenses"; Flags: recursesubdirs ignoreversion
Source: "..\docs\CSV-DIALECT.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\BankFormatStudio.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\BankFormatStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\BankFormatStudio.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
