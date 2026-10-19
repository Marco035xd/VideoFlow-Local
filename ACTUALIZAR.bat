@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Actualizador - VideoFlow Local

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta INSTALAR.bat
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
echo Actualizando yt-dlp y las dependencias de Python...
python -m pip install --upgrade pip wheel
if errorlevel 1 goto :error
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :error

where winget >nul 2>&1
if not errorlevel 1 (
    echo Comprobando versiones de FFmpeg y Deno...
    winget upgrade --id Gyan.FFmpeg --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
    winget upgrade --id DenoLand.Deno --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
)

echo.
echo Actualizacion terminada.
echo Cierra y vuelve a abrir VideoFlow para aplicar los cambios.
pause
exit /b 0

:error
echo No se pudieron actualizar las dependencias de Python.
pause
exit /b 1
