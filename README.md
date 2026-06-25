# ✧ LIA — Tu segundo cerebro de escritorio con IA

**LIA** es un asistente de escritorio para Windows que vive como un **orbe minimalista** en tu pantalla y captura tus ideas **desde cualquier aplicación** —por voz, portapapeles o mirando tu pantalla— para convertirlas en una colección de notas Markdown que **se organiza y se conecta sola**.

No es "otro chat con IA": es un **segundo cerebro** que te acompaña en el escritorio, aprende qué te interesa y teje las conexiones entre tus notas por ti.

> 📐 ¿Buscas el detalle técnico? → **[ARQUITECTURA.md](ARQUITECTURA.md)** (qué tecnología usa y qué hace cada pieza).

---

## ¿Por qué es diferente?

- 🌍 **Captura desde cualquier sitio, no solo dentro de un editor.** Estás trabajando en lo que sea y sueltas una idea por voz, portapapeles o pantalla, sin cambiar de contexto.
- 🔒 **Local-first de verdad.** La búsqueda semántica, el clustering, el aprendizaje y el índice corren **en tu máquina**. Solo la conversación con el modelo sale a la nube.
- 🧠 **Aprende de ti.** Los recordatorios proactivos se **callan** cuando aprenden que ese tipo de aviso no te aporta.
- 📂 **Tus notas son tuyas.** Archivos `.md` normales en una carpeta tuya. **Obsidian es opcional** (solo si quieres ver el grafo bonito).

---

## ✨ Funcionalidades

**Presencia e interfaz**
- 🟣 **Orbe state-reactive**: presencia elegante (estilo Siri/Raycast), dibujada con gradientes animados; late, gira y cambia de expresión según el estado.
- 💬 **Chat con burbujas reales**: tus mensajes a la derecha, los de Lia a la izquierda con su mini-orbe; *streaming* token a token, indicador "escribiendo…", marcas de tiempo y **Markdown** renderizado.
- 🔔 **Bandeja del sistema** (mostrar/ocultar/salir) y **chime** de recordatorios sintetizado (sin assets).
- ⌨️ **Atajos**: `Shift_L + L` global para mostrar/ocultar, `Esc` cierra el panel, `↑` recupera tu último mensaje.

**Inteligencia y memoria**
- 🧠 **Memoria conversacional**: Lia recuerda los turnos anteriores; el historial persiste entre sesiones.
- 🔍 **Búsqueda semántica local**: pregunta *"¿qué sé sobre productividad?"* y encuentra notas que ni mencionan esa palabra (embeddings ONNX, 100% local).
- 🔗 **Auto-enlazado**: al crear una nota, Lia detecta las relacionadas por significado y las enlaza sola (`[[ ]]`).
- 🏷️ **Auto-tags de entidades**: etiqueta `persona/…`, `proyecto/…`, `lugar/…` automáticamente.
- 🗂️ **Clustering de temas**: descubre los temas latentes de tu vault ("tienes N notas sobre X").
- 📓 **Resumen diario**: digest que conecta lo capturado hoy con tus notas anteriores.
- ✏️ **Edición fina**: cambia un dato puntual de una nota larga sin reescribirla entera.

**Captura y proactividad**
- 🎙️ **Voz**: micrófono con transcripción local (Whisper).
- 📸 **Visión de pantalla**: captura la pantalla como contexto para Gemini bajo demanda.
- 🤖 **Recordatorios proactivos**: detectan cuándo merece la pena anotar (portapapeles, foco prolongado, fin de día) y **aprenden** de tu feedback (Sí / Ahora no).
- ⚡ **Enrutamiento Flash/Pro**: Gemini Flash para acción rápida, Pro para razonamiento o mentoría.
- 🔊 **Respuesta por voz** (Edge-TTS) y **automatización del SO** (abrir apps, portapapeles).

---

## 🚀 Instalación

### Opción A — Usuario final (recomendada): un archivo, un doble clic

1. Descarga **`LIA.exe`**.
2. Doble clic. Windows SmartScreen avisará (app sin firmar) → **Más información → Ejecutar de todos modos**.
3. A partir de ahí es automático: LIA **se autoinstala** (se copia a su carpeta, crea el acceso directo en el escritorio y se registra en *Agregar o quitar programas*) y abre la **bienvenida**.
4. Escribe tu nombre, pega tu **clave gratis de Gemini** ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)) y elige la carpeta de notas (se crea sola). Listo.

> No necesitas instalar Python, ni Obsidian, ni nada. Todo va dentro del `.exe`. La primera vez que uses voz o búsqueda semántica, LIA descargará sus modelos de IA (~100-200 MB).

### Opción B — Desarrollador (desde el código)

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Requisitos: **Python 3.10+** y una API Key de Gemini. En el primer arranque, el onboarding crea el `.env` por ti (o cópialo de `.env.example`).

---

## ⚙️ Configuración

Casi todo se configura desde la **interfaz** (onboarding y menú de ajustes): nombre, clave, carpeta, voz, micrófono y sonido de recordatorios. Para ajustes avanzados, el `.env`:

| Variable | Por defecto | Qué hace |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | — | Tu clave de Gemini (gratis). |
| `OBSIDIAN_VAULT_PATH` | — | Carpeta donde Lia guarda las notas `.md`. |
| `GEMINI_MODEL` / `GEMINI_MODEL_REASONING` | `gemini-2.5-flash` / `pro` | Modelos rápido / de razonamiento. |
| `PROACTIVE_ENABLED` | `True` | Activa los recordatorios proactivos. |
| `LIA_PROACTIVE_DEBUG` | `False` | Tiempos cortos + demo al arrancar (para probar). |
| `TTS_ENABLED` / `TTS_VOICE` | `True` / `es-ES-ElviraNeural` | Voz de respuesta. |

---

## 🔒 Privacidad

La transcripción de voz (Whisper), la búsqueda semántica (embeddings), el clustering y el aprendizaje del feedback corren **100% en tu máquina**. Solo la conversación con el modelo de lenguaje (y, bajo demanda, una captura de pantalla) viaja a Gemini — **nunca tu vault completo**. Toda la configuración y el estado viven en `%LOCALAPPDATA%/LiaAssistant`.

---

## 🧪 Pruebas

```bash
.\venv\Scripts\pytest tests/ -q
```

~100 pruebas que cubren núcleo, servicios, motor proactivo, ML de relevancia, búsqueda semántica, clustering, auto-enlazado, edición de notas, interfaz de chat, panel de info y auto-instalación.

---

## 🛠️ Estructura del proyecto

```plaintext
LiaAssistant/
├── main.py                       # Arranque (auto-instalación + onboarding + arranque)
├── config/
│   ├── settings.py               # Configuración tipada (Pydantic) desde .env
│   ├── paths.py                  # Rutas de datos (%LOCALAPPDATA%/LiaAssistant)
│   └── logging_setup.py          # Log a fichero + errores legibles
├── src/
│   ├── core/
│   │   ├── orchestrator.py       # Mediator: coordina UI, estado, voz, IA, proactividad
│   │   └── state_manager.py      # Máquina de estados (Idle/Listening/Processing/Responding)
│   ├── bootstrap/
│   │   └── self_install.py       # Auto-instalación del .exe en el primer arranque
│   ├── gui/
│   │   ├── view.py               # Panel glassmorphic translúcido sin marcos
│   │   ├── orb_mascot.py         # Orbe minimalista state-reactive
│   │   ├── mascot_behavior.py    # Colocación, clic/doble-clic/arrastre, snap
│   │   ├── onboarding.py         # Bienvenida / ajustes (nombre, clave, carpeta, voz)
│   │   ├── tray_icon.py          # Icono de bandeja (mostrar/ocultar/salir)
│   │   ├── splash.py             # Pantalla de carga con progreso
│   │   ├── chime.py              # Chime de recordatorios sintetizado (WAV)
│   │   ├── md_render.py          # Markdown → HTML para las respuestas
│   │   └── components/
│   │       ├── chat_view.py      # Conversación con burbujas reales + streaming
│   │       ├── info_panel.py     # Popup de acciones rápidas (rediseñado)
│   │       ├── input_field.py    # Campo de entrada (pill) + atajo ↑
│   │       ├── mascot_bubble.py  # Burbuja "Sí / Ahora no" proactiva
│   │       └── reminder_bubble.py# Burbuja de recordatorio (Listo / Posponer)
│   ├── io/
│   │   ├── audio_recorder.py     # Micrófono con VAD (hilo aparte)
│   │   └── keyboard_listener.py  # Atajo global (QThread + pynput)
│   ├── services/
│   │   ├── gemini_service.py     # Workers Flash/Pro: streaming + tool-calling + memoria
│   │   ├── whisper_local.py      # Transcripción local (faster-whisper)
│   │   ├── tts_service.py        # Voz de respuesta (Edge-TTS)
│   │   ├── os_automation.py      # Abrir apps, portapapeles
│   │   ├── conversation_store.py # Historial persistente (JSON)
│   │   ├── system_monitor.py     # Portapapeles / ventana activa / inactividad
│   │   ├── proactive_engine.py   # Decide CUÁNDO sugerir (reglas + ML)
│   │   ├── relevance_scorer.py   # Regresión logística que aprende del feedback
│   │   ├── feedback_store.py     # Feedback proactivo (SQLite)
│   │   ├── reminder_service.py / reminders.py  # Recordatorios con hora
│   │   ├── semantic_index.py     # Índice vectorial del vault (fastembed/ONNX)
│   │   ├── semantic_search.py    # Herramienta search_notes_semantic
│   │   ├── auto_link.py          # Enlazado automático de notas afines
│   │   ├── topic_clusters.py     # Clustering de temas (KMeans)
│   │   └── daily_summary.py      # Resumen diario con conexiones
│   └── storage/
│       └── obsidian_manager.py   # CRUD de notas: crear/leer/escribir/editar/etiquetar
├── packaging/                    # Build del .exe (PyInstaller), icono, instalador
├── tests/                        # Suite pytest (~100 pruebas)
└── requirements.txt
```

---

## 📈 Estado

LIA está **funcionalmente completa** y es distribuible como `.exe` autoinstalable. Para el detalle de fases y lo que queda, ver **[ESTADO_Y_FASES.md](ESTADO_Y_FASES.md)**.
