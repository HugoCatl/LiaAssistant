# Empaquetado de LIA

## Todo en uno: doble clic en `build.bat`

En Windows, con el venv del proyecto activado, **doble clic en `build.bat`**.
Hace TODO de una vez:

1. Activa el venv e instala PyInstaller/Pillow.
2. Genera el icono y construye `LIA.exe` (onefile, sin consola).
3. Copia `LIA.exe` a Descargas y crea el acceso directo en el Escritorio.
4. Si tienes Inno Setup instalado, **genera tambien `LIA-Setup.exe`**
   (instalador con eleccion de carpeta + desinstalador) y lo copia a Descargas.

Resultado en tu carpeta de Descargas:
- `LIA.exe` -> la app portatil (para probar o pasar a un colega rapido).
- `LIA-Setup.exe` -> el instalador completo (si habia Inno Setup).

## Requisito unico para el instalador

Instala **Inno Setup** (gratis, una sola vez): https://jrsoftware.org/isdl.php
Despues, `build.bat` lo detecta solo y crea el `LIA-Setup.exe` automaticamente.
Si no esta instalado, `build.bat` igual te deja el `LIA.exe` y te avisa.

## Inicio con Windows (modo portatil)

Si usas el `LIA.exe` suelto: doble clic en `activar_inicio_con_windows.bat`
para que se abra al encender el PC (`desactivar_...` lo quita). Con el
instalador, esa opcion sale como una casilla durante la instalacion.

## Donde guarda LIA sus datos

Config (`.env`), audios temporales, capturas y feedback van a
`%LOCALAPPDATA%\LiaAssistant` (no a Descargas ni junto al .exe). Las notas van a
tu vault de Obsidian.

## Si el .exe falla al abrir

Suele ser un `ModuleNotFoundError` de las librerias de IA. Anade ese modulo a
`hiddenimports` en `lia.spec` y reconstruye.
