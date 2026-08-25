; Instalator Windows budowany przez Inno Setup.
; Nie wymaga uprawnien administratora - instaluje sie dla biezacego uzytkownika.
#define AppName "Grafik dyzurow"
#define AppExe "Grafik.exe"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
; AppId decyduje o tym, czy instalator rozpozna wczesniejsza instalacje
; i podmieni ja w miejscu, zamiast zakladac druga obok. Bez tej linii Inno
; przyjmuje wartosc AppName, wiec zmiana nazwy programu po cichu zerwalaby
; sciezke aktualizacji. Wartosc jest celowo taka sama jak dotychczasowa
; domyslna - NIE WOLNO jej zmieniac, bo rozjedzie sie z juz zainstalowanymi
; kopiami.
AppId=Grafik dyzurow
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Grafik
DefaultDirName={autopf}\Grafik
DefaultGroupName=Grafik
OutputDir=..\dist
OutputBaseFilename=Grafik-Instalator-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableDirPage=yes
WizardStyle=modern
SetupIconFile=grafik.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
; Aktualizacja przy uruchomionym programie: Inno zamyka go i wznawia,
; zamiast zadac restartu komputera.
CloseApplications=yes
RestartApplications=yes
; Grafiki leza w {userappdata}\Grafik i nie sa objete instalacja ani
; odinstalowaniem - aktualizacja nadpisuje wylacznie pliki programu.

[Languages]
Name: "polski"; MessagesFile: "compiler:Languages\Polish.isl"

[Files]
Source: "..\dist\Grafik\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Utworz skrot na pulpicie"; \
    GroupDescription: "Skroty:"; Flags: checkedonce

[Run]
Filename: "{app}\{#AppExe}"; Description: "Uruchom Grafik"; \
    Flags: nowait postinstall skipifsilent
