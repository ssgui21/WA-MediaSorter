@echo off
chcp 65001 >nul
title WA-MediaSorter - Servidor Local

echo =======================================================
echo          WA-MediaSorter - Organizador de Imagens
echo =======================================================
echo.

cd /d "%~dp0"

:: 1. Verificar se o ambiente virtual existe
if exist ".venv\Scripts\python.exe" (
    echo [OK] Ambiente virtual (.venv) encontrado.
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto START_APP
)

:: 2. Se não existir .venv, procurar o Python no sistema
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Python encontrado no sistema. Criando ambiente virtual '.venv'...
    python -m venv .venv
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON_EXE=.venv\Scripts\python.exe"
        echo [INFO] Instalando dependências do requirements.txt...
        "%PYTHON_EXE%" -m pip install --upgrade pip
        "%PYTHON_EXE%" -m pip install -r requirements.txt
        goto START_APP
    )
)

:: Se o Python não foi encontrado
echo [AVISO] O Python no foi detectado no sistema ou o ambiente virtual ainda no foi configurado.
echo.
echo Para executar a aplicao com o seu Python:
echo   1. Certifique-se de que o Python 3.10+ est instalado no seu computador.
echo   2. Execute: python -m venv .venv
echo   3. Execute: .venv\Scripts\pip install -r requirements.txt
echo   4. Execute este arquivo run.bat novamente.
echo.
pause
exit /b 1

:START_APP
echo.
echo =======================================================
echo  Iniciando servidor local em: http://127.0.0.1:8000
echo  Para encerrar a aplicao, pressione CTRL + C
echo =======================================================
echo.

:: Abrir o navegador automaticamente aps 2 segundos
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"

:: Iniciar o servidor FastAPI / Uvicorn
"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
