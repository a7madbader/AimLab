; Inno Setup script: wraps dist\AimLabPro into a normal Windows installer with a desktop shortcut.
#define AppName "AIMLAB PRO"
#define AppVersion "0.1.0"

[Setup]
AppId={{B7E1B1F4-6C1A-4D7B-9C55-A1B2C3D40001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AIMLAB PRO
DefaultDirName={autopf}\AimLabPro
DefaultGroupName={#AppName}
OutputDir=..\installer_output
OutputBaseFilename=AimLabPro-Setup-{#AppVersion}
SetupIconFile=..\assets\aimlab.ico
UninstallDisplayIcon={app}\AimLabPro.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\AimLabPro\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\AimLabPro.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\AimLabPro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AimLabPro.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
