@echo off
REM Doble clic: LIA se abrira automaticamente al encender el PC.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_shortcuts.ps1" -Exe "%USERPROFILE%\Downloads\LIA.exe" -Startup
pause
