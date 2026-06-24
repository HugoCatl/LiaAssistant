@echo off
REM ============================================================
REM  Empaqueta LIA en un unico LIA.exe (onefile, sin consola).
REM  Ejecutalo en Windows, idealmente con el venv del proyecto activado:
REM      .\venv\Scripts\activate
REM      packaging\build.bat
REM ============================================================
cd /d "%~dp0"

echo [1/3] Instalando herramientas de empaquetado...
python -m pip install --upgrade pyinstaller pillow || goto :error

echo [2/3] Generando icono...
python make_icon.py || goto :error

echo [3/3] Construyendo LIA.exe...
pyinstaller --noconfirm --clean lia.spec || goto :error

echo.
echo ============================================================
echo  Listo. El ejecutable esta en:  packaging\dist\LIA.exe
echo ============================================================
pause
exit /b 0

:error
echo.
echo  ERROR durante el empaquetado. Revisa los mensajes de arriba.
pause
exit /b 1
