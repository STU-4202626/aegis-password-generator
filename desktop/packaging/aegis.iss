#define AppName "AEGIS"
#define AppVersion "0.3.9"
#define AppPublisher "AEGIS"
#define AppExeName "AEGIS.exe"

[Setup]
AppId={{8D8E0B2A-53BB-42D7-85F4-C2A81A83091B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={localappdata}\Programs\AEGIS
DefaultGroupName=AEGIS
DisableProgramGroupPage=yes
OutputDir=..\installer-output
OutputBaseFilename=AEGIS-Setup-{#AppVersion}-Windows-x64
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=..\assets\aegis.ico
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

[Files]
Source: "..\dist\AEGIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\AEGIS"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\AEGIS"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch AEGIS"; Flags: nowait postinstall skipifsilent

; Upgrades reuse the same AppId. User data stays in the user profile, outside
; the application installation folder. Uninstall must never remove the vault.
