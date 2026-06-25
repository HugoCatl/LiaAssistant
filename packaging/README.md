# Empaquetado de LIA

## Construir el `.exe`

En Windows, con el venv del proyecto activado:

```bash
pyinstaller --noconfirm --clean packaging/lia.spec
```

Resultado: **`dist/LIA.exe`** (onefile, sin consola, ~178 MB). El icono se genera
con `python packaging/make_icon.py` (lo hace también `build.bat`).

> `build.bat` es un atajo todo-en-uno: genera el icono, construye el exe y lo
> copia a Descargas.

## Qué repartes al usuario

**Solo `LIA.exe`.** Un único archivo. Cuando el usuario lo abre por primera vez,
el propio exe **se autoinstala** (`src/bootstrap/self_install.py`):

- se copia a `%LOCALAPPDATA%\Programs\LIA`,
- crea accesos directos en el Escritorio y el menú Inicio,
- se registra en "Agregar o quitar programas" (con desinstalador, sin admin),
- y abre el onboarding (nombre, clave de Gemini, carpeta de notas).

No hace falta descomprimir nada, ni `.bat`, ni Python, ni Obsidian. Las siguientes
veces se abre desde el acceso directo.

> Los scripts `Instalar-LIA.ps1` / `Instalar LIA.bat` siguen disponibles como
> instalador alternativo, pero con la auto-instalación ya **no son necesarios**.

## Dónde guarda LIA sus datos

Config (`.env`), historial, feedback, logs y temporales van a
`%LOCALAPPDATA%\LiaAssistant`. Las notas van a la carpeta que el usuario elige en
el onboarding (archivos `.md`; Obsidian es opcional).

## Lo que el usuario verá la primera vez

- **SmartScreen** ("editor desconocido") porque el exe no está firmado →
  *Más información → Ejecutar de todos modos*.
- Tiene que poner **su** clave gratis de Gemini (aistudio.google.com/apikey).
- La primera búsqueda semántica o nota por voz **descarga los modelos** (~100-200 MB).

## Si el .exe falla al abrir

Suele ser un `ModuleNotFoundError` de alguna librería. Añade ese módulo a
`hiddenimports` en `lia.spec` y reconstruye. El log está en
`%LOCALAPPDATA%\LiaAssistant\lia.log`.
