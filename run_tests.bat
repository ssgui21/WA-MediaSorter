@echo off
chcp 65001 >nul
title WA-MediaSorter - Testes Automatizados

echo =======================================================
echo          WA-MediaSorter - Execução dos Testes
echo =======================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Executando pytest...
"%PYTHON_EXE%" -m pytest tests/ -v

echo.
pause
