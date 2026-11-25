@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta 01_PREPARAR_NETBOOK.cmd.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "verificar_netbook.py"
set "RESULTADO=%errorlevel%"
pause
exit /b %RESULTADO%
