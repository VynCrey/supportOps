@echo off
setlocal
cd /d "%~dp0"

echo SupportOps - preparacion inicial de esta computadora
echo.

if not exist "requirements.txt" goto carpeta_incompleta
if not exist "schema.sql" goto carpeta_incompleta
if not exist "kb.json" goto carpeta_incompleta

set "PYTHON=py -3.11"
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    python -c "import sys; sys.exit(sys.version_info[:2] != (3, 11))" >nul 2>&1
    if errorlevel 1 goto falta_python
    set "PYTHON=python"
)

where.exe ollama >nul 2>&1
if errorlevel 1 goto falta_ollama

if /I "%~1"=="--verificar" (
    echo Python 3.11 y Ollama encontrados.
    echo Los archivos necesarios estan en esta carpeta.
    exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creando el entorno de Python...
    %PYTHON% -m venv ".venv"
    if errorlevel 1 goto fallo
) else (
    echo [1/4] El entorno de Python ya existe.
)

echo [2/4] Instalando las bibliotecas del proyecto...
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto fallo

echo [3/4] Creando la base y los clientes ficticios...
echo Escribi la contrasena del usuario postgres de ESTA computadora.
".venv\Scripts\python.exe" "bootstrap.py"
if errorlevel 1 goto fallo

echo [4/4] Cargando los documentos de la base de conocimiento...
echo Escribi de nuevo la misma contrasena de postgres.
".venv\Scripts\python.exe" "cargar_kb.py"
if errorlevel 1 goto fallo

echo Descargando el modelo local qwen2.5:3b. Puede tardar.
ollama pull qwen2.5:3b
if errorlevel 1 goto fallo

echo.
echo Preparacion terminada. Abri 02_INICIAR_API.cmd y despues 03_ABRIR_PANEL.cmd.
pause
exit /b 0

:carpeta_incompleta
echo Faltan archivos. Descomprimi el ZIP completo antes de ejecutar este programa.
pause
exit /b 1

:falta_python
echo Falta Python 3.11. Instalalo y abri de nuevo esta ventana.
echo https://www.python.org/downloads/windows/
pause
exit /b 1

:falta_ollama
echo Falta Ollama o no aparece en PATH. Instalalo y abri de nuevo esta ventana.
echo https://ollama.com/download/windows
pause
exit /b 1

:fallo
echo.
echo La preparacion se detuvo. Lee el error de arriba.
echo Podes volver a ejecutar este archivo: la muestra y la KB no se duplican.
pause
exit /b 1
