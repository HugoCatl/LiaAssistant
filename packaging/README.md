# Empaquetado de LIA

## Un solo doble clic: `build.bat`

En Windows, con el venv del proyecto activado, **doble clic en `build.bat`**.
Hace todo sin necesitar nada externo (ni Inno Setup):

1. Construye `LIA.exe` (onefile, sin consola).
2. Lo copia a Descargas y crea el acceso directo en el Escritorio.
3. Arma el paquete de instalacion en `Descargas\LIA-Instalador\` y su zip
   `Descargas\LIA-Instalador.zip`.

## Que repartes al usuario

- **Lo mas simple:** el `LIA.exe` suelto. Lo abre directamente, sin instalar.
- **Con instalador (recomendado):** el `LIA-Instalador.zip`. El usuario lo
  descomprime y da **doble clic en `Instalar LIA.bat`**. El instalador (solo
  PowerShell, sin dependencias) le deja elegir carpeta, crea accesos directos,
  pregunta si abrir LIA al iniciar Windows y registra un **desinstalador** en
  "Agregar o quitar programas". No pide permisos de administrador.

El usuario final no instala Inno Setup ni Python ni nada: solo necesita su clave
de Gemini en el primer arranque.

## Donde guarda LIA sus datos

Config (`.env`), audios temporales, capturas y feedback van a
`%LOCALAPPDATA%\LiaAssistant`. Las notas van a tu vault de Obsidian.

## Alternativa: instalador con Inno Setup (opcional)

Si prefieres un instalador .exe clasico tipo asistente, existe `installer.iss`
para Inno Setup. Es opcional; el paquete PowerShell de arriba ya cubre lo mismo
sin descargar nada.

## Si el .exe falla al abrir

Suele ser un `ModuleNotFoundError` de las librerias de IA. Anade ese modulo a
`hiddenimports` en `lia.spec` y reconstruye.
