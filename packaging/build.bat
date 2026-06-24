@echo off
REM ============================================================
REM  TODO EN UNO: construye LIA.exe y, si Inno Setup esta
REM  instalado, genera tambien LIA-Setup.exe. Un solo doble clic.
REM ============================================================
setlocal
cd /d "%~dp0\.."
set "DEST=%USERPROFILE%\Downloads"

echo [1/6] Activando entorno virtual (si existe)...
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo   Sin venv; se usara el Python del sistema.
)

echo [2/6] Instalando herramientas de empaquetado...
python -m pip install --upgrade pyinstaller pillow || goto :error

echo [3/6] Generando icono...
python packaging\make_icon.py || goto :error

echo [4/6] Construyendo LIA.exe (tarda unos minutos)...
pyinstaller --noconfirm --clean packaging\lia.spec || goto :error

echo [5/6] Copiando a Descargas y creando acceso directo...
copy /Y "dist\LIA.exe" "%DEST%\LIA.exe" >nul || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -File "packaging\install_shortcuts.ps1" -Exe "%DEST%\LIA.exe"

echo [6/6] Generando instalador (si Inno Setup esta presente)...
set "ISCC="
set "PF86=%ProgramFiles(x86)%"
set "PF=%ProgramFiles%"
if exist "%PF86%\Inno Setup 6\ISCC.exe" set "ISCC=%PF86%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%PF%\Inno Setup 6\ISCC.exe" set "ISCC=%PF%\Inno Setup 6\ISCC.exe"
if defined ISCC (
    "%ISCC%" "packaging\installer.iss" || goto :error
    copy /Y "packaging\LIA-Setup.exe" "%DEST%\LIA-Setup.exe" >nul
    set "HASSETUP=1"
) else (
    echo   Inno Setup no encontrado. Para generar el instalador, instalalo
    echo   desde https://jrsoftware.org/isdl.php y vuelve a ejecutar este .bat.
)

echo.
echo ============================================================
echo  LISTO.
echo   - App:        %DEST%\LIA.exe   (+ acceso directo en el Escritorio)
if defined HASSETUP echo   - Instalador: %DEST%\LIA-Setup.exe
echo ============================================================
pause
exit /b 0

:error
echo.
echo  ERROR durante el proceso. Revisa los mensajes de arriba y pasamelos.
pause
exit /b 1
