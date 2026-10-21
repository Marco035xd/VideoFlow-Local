@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title VideoFlow Local

if not exist ".venv\Scripts\python.exe" (
    echo VideoFlow aun no esta instalado.
    echo Se abrira el instalador.
    call INSTALAR.bat
)

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro el entorno de Python.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" launcher.py
