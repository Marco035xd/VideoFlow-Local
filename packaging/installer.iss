#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define ProjectRoot SourcePath + ".."

[Setup]
AppId={{2C4E7DA8-9B1B-41D7-8797-FD2AFA1DC774}
AppName=VideoFlow Local
AppVersion={#AppVersion}
AppPublisher=VideoFlow Local
AppPublisherURL=https://github.com/Marco035xd/VideoFlow-Local
DefaultDirName={localappdata}\Programs\VideoFlow Local
DefaultGroupName=VideoFlow Local
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#ProjectRoot}\release
OutputBaseFilename=VideoFlow-Local-{#AppVersion}-Setup-x64
SetupIconFile={#ProjectRoot}\static\app.ico
UninstallDisplayIcon={app}\VideoFlowLocal.exe
WizardStyle=modern
Compression=lzma2/normal
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
AppMutex=Local\VideoFlowLocal-8765

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#ProjectRoot}\dist\VideoFlowLocal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VideoFlow Local"; Filename: "{app}\VideoFlowLocal.exe"
Name: "{autodesktop}\VideoFlow Local"; Filename: "{app}\VideoFlowLocal.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VideoFlowLocal.exe"; Description: "Abrir VideoFlow Local"; Flags: nowait postinstall skipifsilent
