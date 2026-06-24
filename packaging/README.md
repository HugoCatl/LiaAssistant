# Empaquetado de LIA

Dos formas de distribuir LIA. Ambas parten de construir `LIA.exe` con PyInstaller.

## 1) Construir el .exe (siempre)

En Windows, con el venv del proyecto activado, **doble clic en `build.bat`**.
Hace: activa el venv, instala PyInstaller/Pillow, genera el icono, compila
`LIA.exe`, lo copia a tu carpeta de Descargas y crea un acceso directo en el
Escritorio. El ejecutable queda en `packaging\dist\LIA.exe` y en Descargas.

## 2a) Modo portatil (rapido)

Te quedas con `LIA.exe` tal cual (en Descargas o donde quieras). El acceso
directo del Escritorio ya lo crea `build.bat`. Para que arranque con Windows:
doble clic en `activar_inicio_con_windows.bat` (y `desactivar_...` para quitarlo).

## 2b) Instalador real (recomendado para "plug and play")

Genera un `LIA-Setup.exe` que deja **elegir la carpeta de instalacion**, crea
accesos directos, opcion de inicio con Windows y un **desinstalador**.

1. Instala Inno Setup (gratis): https://jrsoftware.org/isdl.php
2. Asegurate de tener `packaging\dist\LIA.exe` (lo deja `build.bat`).
3. Doble clic en `packaging\installer.iss` -> boton **Compile**
   (o `ISCC.exe packaging\installer.iss`).
4. Obtienes `packaging\LIA-Setup.exe`. Ese es el que compartes/instalas.

El instalador no pide permisos de administrador (instala en la carpeta del
usuario), por lo que la instalacion es directa.

## Donde guarda LIA sus datos

Config (`.env`), audios temporales, capturas y la base de feedback se guardan en
`%LOCALAPPDATA%\LiaAssistant`, no en Descargas ni junto al .exe. Las notas van a
tu vault de Obsidian (la carpeta que elijas en los ajustes).

## Si el .exe falla al abrir

Suele ser un `ModuleNotFoundError` de las librerias de IA. Anade ese modulo a
`hiddenimports` en `lia.spec` y reconstruye.
