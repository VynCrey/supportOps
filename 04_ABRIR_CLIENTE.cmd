@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta 01_PREPARAR_NETBOOK.cmd.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import urllib.request; respuesta = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); assert respuesta.status == 200" >nul 2>&1
if errorlevel 1 (
    echo La API no responde. Abri 02_INICIAR_API.cmd primero.
    pause
    exit /b 1
)

echo Tienda Faro - vista del cliente en http://127.0.0.1:8502
".venv\Scripts\python.exe" -m streamlit run "cliente_app.py" --server.address=127.0.0.1 --server.port=8502
pause
