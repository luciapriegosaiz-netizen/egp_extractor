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

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "PY_SCRIPT=%SCRIPT_DIR%extract_egp.py"

REM --- Verificar que el .py está junto a este .bat ---
if not exist "%PY_SCRIPT%" (
    echo.
    echo ERROR: No se encuentra extract_egp.py en la misma carpeta que este .bat.
    echo Carpeta esperada: %SCRIPT_DIR%
    echo.
    pause
    exit /b 1
)

REM --- Buscar Python de forma robusta ---
set "PYTHON_CMD="

REM Opción 1: Usar 'py' (launcher oficial de Python en Windows)
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto python_found
)

REM Opción 2: Usar 'python' (si está en PATH)
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto python_found
)

REM Opción 3: Usar 'python3' (si está en PATH)
where python3 >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python3"
    goto python_found
)

REM Opción 4: Ruta típica de Python en Windows
if exist "C:\Python311\python.exe" (
    set "PYTHON_CMD=C:\Python311\python.exe"
    goto python_found
)
if exist "C:\Python310\python.exe" (
    set "PYTHON_CMD=C:\Python310\python.exe"
    goto python_found
)
if exist "C:\Python39\python.exe" (
    set "PYTHON_CMD=C:\Python39\python.exe"
    goto python_found
)

REM Si no se encontró Python
echo.
echo ERROR: Python no encontrado en el PATH.
echo.
echo Soluciones:
echo   1. Instala Python desde https://www.python.org/downloads/
echo   2. En el instalador, marca "Add Python to PATH"
echo   3. Reinicia tu sesión de Windows después de instalar
echo.
echo O intenta ejecutar directamente desde cmd.exe:
echo   python extract_egp.py "Proyecto_SCA_modificado.egp" --logs
echo.
pause
exit /b 1

:python_found
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

if "!INPUT_PATH!"=="" (
    echo Sin ruta de entrada. Saliendo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Ejecutando con: %PYTHON_CMD%
echo ============================================================
echo.

%PYTHON_CMD% "%PY_SCRIPT%" "!INPUT_PATH!" %EXTRA_ARGS%

echo.
echo ============================================================
echo  Pulsa cualquier tecla para cerrar.
echo ============================================================
pause >nul
endlocal
