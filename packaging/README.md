# Empaquetado de LIA (.exe)

Genera un único `LIA.exe` para Windows con PyInstaller.

## Cómo construirlo

Desde la raíz del proyecto, en Windows, **con el venv del proyecto activado**
(para que PyInstaller vea todas las dependencias instaladas):

```bat
.\venv\Scripts\activate
packaging\build.bat
```

El ejecutable queda en `packaging\dist\LIA.exe`.

`build.bat` hace tres cosas: instala `pyinstaller` y `pillow`, genera el icono
`lia.ico` (un orbe morado a juego con la mascota) y ejecuta `pyinstaller lia.spec`.

## Qué incluye (y qué no)

- **Incluye**: PyQt6, el cliente de Gemini, edge-tts, sounddevice (con la DLL de
  PortAudio), y las librerías de IA local (faster-whisper, fastembed/onnxruntime).
- **No incluye los modelos** de voz (Whisper) ni de embeddings (fastembed): se
  descargan a la caché del usuario la **primera vez** que se usan. Por eso el
  primer arranque con voz/búsqueda semántica tarda un poco más y necesita red.
- **No incluye el `.env`** (lleva tu clave de Gemini). En el primer arranque, el
  **onboarding** crea la configuración. Si quieres distribuirlo ya configurado,
  añade `.env.example` a `datas` en `lia.spec`.

## Notas y posibles ajustes

- Si al abrir el `.exe` falta algún módulo (`ModuleNotFoundError`), añádelo a
  `hiddenimports` en `lia.spec` y reconstruye.
- El primer build es lento (analiza todas las dependencias). Los siguientes van
  más rápidos si no usas `--clean`.
- Para arranque automático con Windows (Fase 5), crea un acceso directo a
  `LIA.exe` en la carpeta `shell:startup`. Esto se puede automatizar más adelante
  desde el panel de ajustes con un toggle.
