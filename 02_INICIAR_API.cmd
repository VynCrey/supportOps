@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta 01_PREPARAR_NETBOOK.cmd.
    pause
    exit /b 1
)

echo SupportOps API - dejala abierta mientras usas el panel.
echo Escribi la contrasena local de PostgreSQL cuando se solicite.
".venv\Scripts\python.exe" "run.py"
echo.
echo La API se detuvo. Para volver a usar el panel, ejecuta este archivo otra vez.
pause
