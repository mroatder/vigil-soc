; Per-user installer, so it needs no administrator rights.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E1B7C52-9D3A-4F0E-8A61-3C7F2B90D4E1}
AppName=Vigil
AppVersion={#AppVersion}
AppPublisher=mroatder
DefaultDirName={localappdata}\Programs\Vigil
DefaultGroupName=Vigil
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=VigilSetup-{#AppVersion}
SetupIconFile=vigil.ico
UninstallDisplayIcon={app}\Vigil.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "..\dist\Vigil.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Vigil"; Filename: "{app}\Vigil.exe"
Name: "{autodesktop}\Vigil"; Filename: "{app}\Vigil.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Vigil.exe"; Description: "Start Vigil"; Flags: nowait postinstall skipifsilent
