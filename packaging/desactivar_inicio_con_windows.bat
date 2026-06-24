@echo off
REM Doble clic: LIA dejara de abrirse al encender el PC.
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\LIA.lnk" 2>nul
echo LIA ya no se abrira al iniciar Windows.
pause
