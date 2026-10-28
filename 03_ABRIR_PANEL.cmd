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
    echo La API no responde. Abri 02_INICIAR_API.cmd y espera a que arranque.
    pause
    exit /b 1
)

echo SupportOps - panel en http://127.0.0.1:8501
echo Deja abierta esta ventana y la de la API mientras usas el programa.
".venv\Scripts\python.exe" -m streamlit run "streamlit_app.py" --server.address=127.0.0.1 --server.port=8501
echo.
echo El panel se detuvo.
pause
