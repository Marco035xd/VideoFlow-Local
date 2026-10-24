#ifndef AppVersion
  #define AppVersion "1.5.0"
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
MinVersion=10.0.17763
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
Source: "{#ProjectRoot}\build\prerequisites\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: dontcopy

[Icons]
Name: "{group}\VideoFlow Local"; Filename: "{app}\VideoFlowLocal.exe"; AppUserModelID: "VideoFlow.Local.Desktop"
Name: "{autodesktop}\VideoFlow Local"; Filename: "{app}\VideoFlowLocal.exe"; AppUserModelID: "VideoFlow.Local.Desktop"; Tasks: desktopicon

[Run]
Filename: "{app}\VideoFlowLocal.exe"; Description: "Abrir VideoFlow Local"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Key = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function RuntimeInRegistry(RootKey: Integer): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(RootKey, WebView2Key, 'pv', Version);
  if Result then
    Result := (Version <> '') and (Version <> '0.0.0.0');
end;

function HasWebView2: Boolean;
begin
  Result := RuntimeInRegistry(HKCU32) or RuntimeInRegistry(HKCU64) or
            RuntimeInRegistry(HKLM32) or RuntimeInRegistry(HKLM64);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
begin
  Result := '';
  if HasWebView2 then
    Exit;
  WizardForm.StatusLabel.Caption := 'Instalando Microsoft Edge WebView2 para la ventana de escritorio...';
  ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
  if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install',
              '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    Result := 'No se pudo iniciar la instalación de Microsoft Edge WebView2. Vuelve a ejecutar el instalador.'
  else if not HasWebView2 then
    Result := 'No se pudo completar la instalación de Microsoft Edge WebView2. Comprueba tu conexión a Internet y vuelve a ejecutar el instalador. Código: ' + IntToStr(ExitCode);
end;
