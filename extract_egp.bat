@echo off
REM ============================================================
REM  Extractor SAS EG  —  wrapper Python
REM
REM  Tres formas de uso:
REM    1. Drag & drop : arrastra el .egp o la carpeta sobre este .bat
REM    2. Doble clic  : pedirá la ruta interactivamente
REM    3. CLI         : extract_egp.bat "C:\ruta\proyecto.egp"
REM
REM  Para incluir también los .log de cada nodo:
REM    extract_egp.bat "C:\ruta\proyecto.egp" --logs
REM ============================================================

setlocal
set "SCRIPT_DIR=%~dp0"
set "PY_SCRIPT=%SCRIPT_DIR%extract_egp.py"

REM --- Verificar que Python está disponible ---
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python no encontrado en el PATH.
    echo Instala Python desde https://www.python.org o activa el entorno de CP4D.
    echo.
    pause
    exit /b 1
)

REM --- Verificar que el .py está junto a este .bat ---
if not exist "%PY_SCRIPT%" (
    echo.
    echo ERROR: No se encuentra extract_egp.py en la misma carpeta que este .bat.
    echo Carpeta esperada: %SCRIPT_DIR%
    echo.
    pause
    exit /b 1
)

REM --- Resolver input ---
if "%~1"=="" (
    echo.
    echo === Extractor SAS EG ===
    echo.
    set /p "INPUT_PATH=Ruta al .egp, .zip o carpeta extraida: "
    set "EXTRA_ARGS="
) else (
    set "INPUT_PATH=%~1"
    set "EXTRA_ARGS=%2 %3 %4"
)

if "%INPUT_PATH%"=="" (
    echo Sin ruta de entrada. Saliendo.
    pause
    exit /b 1
)

echo.
python "%PY_SCRIPT%" "%INPUT_PATH%" %EXTRA_ARGS%

echo.
echo ============================================================
echo  Pulsa cualquier tecla para cerrar.
echo ============================================================
pause >nul
endlocal
