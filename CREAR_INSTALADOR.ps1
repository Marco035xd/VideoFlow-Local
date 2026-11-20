param([string]$InnoCompiler = "", [ValidateSet('directml', 'cuda', 'cpu')][string]$SeparationRuntime)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonBuild = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonBuild)) { throw 'Ejecuta INSTALAR.bat primero.' }
& $pythonBuild -m pip install --upgrade -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar las herramientas de compilacion.' }
$runtimeArguments = @('packaging/install_separation_runtime.py')
if ($SeparationRuntime) { $runtimeArguments += $SeparationRuntime }
& $pythonBuild @runtimeArguments
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el motor de separacion.' }
$prerequisiteFolder = Join-Path $PSScriptRoot 'build\prerequisites'
New-Item -ItemType Directory -Path $prerequisiteFolder -Force | Out-Null
$webviewBootstrapper = Join-Path $prerequisiteFolder 'MicrosoftEdgeWebview2Setup.exe'
if (-not (Test-Path -LiteralPath $webviewBootstrapper)) {
    Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $webviewBootstrapper
}
$bootstrapperSignature = Get-AuthenticodeSignature -FilePath $webviewBootstrapper
if ($bootstrapperSignature.Status -ne 'Valid' -or $bootstrapperSignature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
    throw 'El instalador de WebView2 no tiene una firma valida de Microsoft.'
}
& $pythonBuild packaging/prepare_build.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar los recursos.' }
& $pythonBuild -m PyInstaller --noconfirm --clean VideoFlowLocal.spec
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear VideoFlowLocal.exe.' }
if (-not $InnoCompiler) {
    $compilerCandidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    $InnoCompiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $InnoCompiler) { throw 'Instala Inno Setup 6 o indica -InnoCompiler con la ruta de ISCC.exe.' }
$appVersion = & $pythonBuild -c 'from app_paths import APP_VERSION; print(APP_VERSION)'
& $InnoCompiler "/DAppVersion=$appVersion" packaging/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'No se pudo compilar el instalador.' }
Write-Host "Instalador creado en release\VideoFlow-Local-$appVersion-Setup-x64.exe"
