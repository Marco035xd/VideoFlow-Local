@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Instalador - VideoFlow Local

 echo.
 echo ================================================================
 echo              INSTALADOR DE VIDEOFLOW LOCAL
 echo ================================================================
 echo.

where winget >nul 2>&1
if errorlevel 1 (
    echo [AVISO] No se encontro winget. Las dependencias externas tendran
    echo que instalarse manualmente si aun no existen.
) else (
    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo [1/5] Instalando FFmpeg...
        winget install --id Gyan.FFmpeg --exact --accept-package-agreements --accept-source-agreements
    ) else (
        echo [1/5] FFmpeg ya esta instalado.
    )

    where deno >nul 2>&1
    if errorlevel 1 (
        echo [2/5] Instalando Deno para mejorar la compatibilidad con YouTube...
        winget install --id DenoLand.Deno --exact --accept-package-agreements --accept-source-agreements
    ) else (
        echo [2/5] Deno ya esta instalado.
    )

    echo [3/5] Preparando Microsoft Edge WebView2 para la ventana de escritorio...
    winget install --id Microsoft.EdgeWebView2Runtime --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
)

set "PY_CMD="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3.11"

if not defined PY_CMD (
    py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo.
    echo [FALTA PYTHON] Se necesita Python 3.11 o superior.
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo Instalando Python 3.11...
        winget install --id Python.Python.3.11 --exact --accept-package-agreements --accept-source-agreements
        echo.
        echo Python fue instalado. Cierra esta ventana y ejecuta INSTALAR.bat otra vez.
    ) else (
        echo Instala Python 3.11 o superior y marca la opcion "Add Python to PATH".
    )
    echo.
    pause
    exit /b 1
)

 echo [4/5] Preparando el entorno privado de Python...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip wheel
if errorlevel 1 goto :error

 echo [5/5] Instalando VideoFlow y el motor de descarga...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :error
python packaging\install_separation_runtime.py %1
if errorlevel 1 goto :error

 echo.
 echo ================================================================
 echo INSTALACION COMPLETADA
 echo ================================================================
 echo.
 echo Puedes abrir la aplicacion con INICIAR.bat
 echo Si FFmpeg o Deno se instalaron ahora, conviene cerrar esta ventana
 echo antes de iniciar para que Windows actualice el PATH.
 echo.
pause
exit /b 0

:error
 echo.
 echo [ERROR] La instalacion no se completo. Revisa los mensajes anteriores.
 echo.
pause
exit /b 1
