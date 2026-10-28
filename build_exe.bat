@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   Compilando GestionPrestamos a ejecutable Windows
echo ===================================================

set "PY_CMD="

:: 1. Verificar si pyinstaller esta directamente en el PATH
where pyinstaller >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=pyinstaller"
    goto :RUN_BUILD
)

:: 2. Verificar si la instalación activa de Python 3.14 en AppData tiene PyInstaller
if exist "%LOCALAPPDATA%\Programs\Python\Python314\Scripts\pyinstaller.exe" (
    set "PY_CMD="%LOCALAPPDATA%\Programs\Python\Python314\Scripts\pyinstaller.exe""
    goto :RUN_BUILD
)

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" -m PyInstaller --version >nul 2>nul
    if !errorlevel! equ 0 (
        set "PY_CMD="%LOCALAPPDATA%\Programs\Python\Python314\python.exe" -m PyInstaller"
        goto :RUN_BUILD
    )
)

:: 3. Verificar con el lanzador de Python 'py'
py -m PyInstaller --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py -m PyInstaller"
    goto :RUN_BUILD
)

:: 4. Probar con 'python' del PATH (verificando que tenga el modulo)
python -m PyInstaller --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python -m PyInstaller"
    goto :RUN_BUILD
)

:: 5. Buscar en otras versiones conocidas de Python en AppData
for %%V in (Python313 Python312 Python311 Python310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\%%V\Scripts\pyinstaller.exe" (
        set "PY_CMD="%LOCALAPPDATA%\Programs\Python\%%V\Scripts\pyinstaller.exe""
        goto :RUN_BUILD
    )
    if exist "%LOCALAPPDATA%\Programs\Python\%%V\python.exe" (
        "%LOCALAPPDATA%\Programs\Python\%%V\python.exe" -m PyInstaller --version >nul 2>nul
        if !errorlevel! equ 0 (
            set "PY_CMD="%LOCALAPPDATA%\Programs\Python\%%V\python.exe" -m PyInstaller"
            goto :RUN_BUILD
        )
    )
)

:: Si no se encontro ningun ejecutable valido
echo.
echo [ERROR] No se encontro PyInstaller instalado en el entorno actual.
echo Se detecto que Windows esta ejecutando el alias de Windows Store.
echo.
echo Para solucionarlo:
echo 1) Desactiva los alias de ejecucion en:
echo    Inicio -> 'Administrar alias de ejecucion de aplicaciones' -> Desactivar 'Python' / 'Python3'
echo 2) O instala las dependencias en tu version activa ejecutando:
echo    pip install -r requirements.txt
echo.
pause
exit /b 1

:RUN_BUILD
echo.
echo Utilizando: !PY_CMD!
echo Verificando si dist\GestionPrestamos.exe esta en uso...
taskkill /F /IM GestionPrestamos.exe >nul 2>nul
echo Compilando archivo .spec...
echo.

!PY_CMD! --noconfirm GestionPrestamos.spec

if %errorlevel% equ 0 (
    echo.
    echo ===================================================
    echo   Compilacion exitosa!
    echo   Ejecutable generado en: dist\GestionPrestamos.exe
    echo ===================================================
) else (
    echo.
    echo ===================================================
    echo   Ocurrio un error durante la compilacion.
    echo ===================================================
)

echo.
pause
