@echo off
REM ============================================================
REM  Construye LIA.exe (onefile, sin consola) y lo copia a Descargas.
REM  Basta con hacer DOBLE CLIC en este archivo.
REM ============================================================
setlocal
cd /d "%~dp0\.."

echo [1/5] Activando entorno virtual (si existe)...
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo   No hay venv; se usara el Python del sistema.
)

echo [2/5] Instalando herramientas de empaquetado...
python -m pip install --upgrade pyinstaller pillow || goto :error

echo [3/5] Generando icono...
python packaging\make_icon.py || goto :error

echo [4/5] Construyendo LIA.exe (esto tarda unos minutos)...
pyinstaller --noconfirm --clean packaging\lia.spec || goto :error

echo [5/6] Copiando a Descargas...
set "DEST=%USERPROFILE%\Downloads"
copy /Y "dist\LIA.exe" "%DEST%\LIA.exe" >nul || goto :error

echo [6/6] Creando acceso directo en el Escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -File "packaging\install_shortcuts.ps1" -Exe "%DEST%\LIA.exe"

echo.
echo ============================================================
echo  LISTO.
echo   - LIA.exe en:  %DEST%\LIA.exe
echo   - Acceso directo en el Escritorio.
echo   - Para abrir LIA al encender el PC: doble clic en
echo     packaging\ac