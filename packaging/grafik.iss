; Instalator Windows budowany przez Inno Setup.
#define AppName "Grafik dyzurow"
#define AppExe "Grafik.exe"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\Grafik
DefaultGroupName=Grafik
OutputDir=..\dist
OutputBaseFilename=Grafik-Instalator-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
; Instalacja dla biezacego uzytkownika nie wymaga uprawnien administratora.
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
WizardStyle=modern

[Languages]
Name: "polski"; MessagesFile: "compiler:Languages\Polish.isl"

[Files]
Source: "..\dist\Grafik\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Grafik dyzurow"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\Grafik dyzurow"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Utworz skrot na pulpicie"; GroupDescription: "Skroty:"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Uruchom program"; Flags: nowait postinstall skipifsilent
