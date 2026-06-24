@echo off
REM ============================================================
REM  TODO EN UNO (sin dependencias externas): construye LIA.exe
REM  y arma el paquete de instalacion LIA-Instalador. Un doble clic.
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

echo [5/6] Copiando LIA.exe a Descargas y creando acceso directo...
copy /Y "dist\LIA.exe" "%DEST%\LIA.exe" >nul || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -File "packaging\install_shortcuts.ps1" -Exe "%DEST%\LIA.exe"

echo [6/6] Armando el paquete de instalacion (sin dependencias)...
set "PKG=%DEST%\LIA-Instalador"
if exist "%PKG%" rmdir /s /q "%PKG%"
mkdir "%PKG%"
copy /Y "dist\LIA.exe" "%PKG%\LIA.exe" >nul || goto :error
copy /Y "packaging\Instalar-LIA.ps1" "%PKG%\Instalar-LIA.ps1" >nul || goto :error
copy /Y "packaging\Instalar LIA.bat" "%PKG%\Instalar LIA.bat" >nul || goto :error
powershell -NoProfile -Command "Compress-Archive -Path '%PKG%\*' -DestinationPath '%DEST%\LIA-Instalador.zip' -Force"

echo.
echo ============================================================
echo  LISTO.
echo   - App suelta:     %DEST%\LIA.exe   (+ acceso directo)
echo   - Para repartir:  %DEST%\LIA-Instalador.zip
echo     (el usuario lo descomprime y da doble clic en "Instalar LIA.bat")
echo ============================================================
pause
exit /b 0

:error
echo.
echo  ERROR durante el proceso. Revisa los mensajes de arriba y pasamelos.
pause
exit /b 1
