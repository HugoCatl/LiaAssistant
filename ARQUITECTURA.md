# 🏗️ LIA Assistant — Documento Técnico de Arquitectura

Describe **toda la tecnología que usa LIA y qué hace cada pieza**: qué librería resuelve qué problema, cómo se reparten las responsabilidades por capas y cómo fluyen los datos.

---

## 1. Visión general

LIA es una aplicación de escritorio **Python + PyQt6** estructurada por capas. Combina un servicio en la nube (el modelo de lenguaje) con cómputo **100% local** para todo lo sensible: voz, embeddings, clustering y aprendizaje del feedback. Se distribuye como **un único `.exe`** (PyInstaller) que se **autoinstala** en el primer arranque.

```
┌──────────────────────────────────────────────────────────────┐
│   main.py  →  self_install (1er arranque)  →  onboarding      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                 ┌─────────────▼─────────────┐
                 │   core/orchestrator.py    │  ← Mediator: conecta todo
                 │   core/state_manager.py   │  ← Máquina de estados
                 └──┬──────────┬─────────┬───┘
                    │          │         │
        ┌───────────▼──┐  ┌────▼─────┐  ┌▼───────────────┐
        │     gui/     │  │   io/    │  │   services/    │
        │ orbe, panel, │  │ teclado, │  │ gemini, voz,   │
        │ burbujas,    │  │ audio    │  │ proactivo, ML, │
        │ bandeja      │  │          │  │ semántico…     │
        └──────────────┘  └──────────┘  └───┬────────────┘
                                            │
                                   ┌────────▼────────┐
                                   │    storage/     │
                                   │  Notas .md      │
                                   └─────────────────┘
```

---

## 2. Stack tecnológico (qué hace cada dependencia)

| Tecnología | Rol en LIA | Local / Nube |
| :--- | :--- | :--- |
| **Python 3.10+** | Lenguaje base. | — |
| **PyQt6** | GUI: ventana sin marcos, orbe (QPainter + gradientes), señales/slots, hilos (`QThread`), audio (`QtMultimedia` para TTS y `QSoundEffect` para el chime). | Local |
| **google-genai** | Cliente de **Gemini** (Flash y Pro) con *streaming* y *function calling* (tool-calling). El cerebro conversacional. | Nube |
| **faster-whisper** | Transcripción de voz (STT) en local, CPU, INT8. La voz nunca sale del equipo. | Local |
| **edge-tts** | Síntesis de voz (TTS) con voces neuronales. | Nube |
| **sounddevice** | Captura de micrófono a 16 kHz mono. | Local |
| **pynput** | Atajo global de teclado (`Shift_L + L`) en segundo plano. | Local |
| **fastembed** | Embeddings vía **ONNX Runtime** (sin PyTorch). Vectoriza notas y consultas. Modelo multilingüe (~0.22 GB). | Local |
| **numpy** | Coseno para la búsqueda, KMeans del clustering y la regresión logística del scorer. | Local |
| **sqlite3** (stdlib) | Persistencia del feedback proactivo. | Local |
| **Pillow** | Captura de pantalla (`ImageGrab`) como contexto visual; genera el icono. | Local |
| **pyperclip** | Lectura/escritura del portapapeles. | Local |
| **pydantic / pydantic-settings / python-dotenv** | Configuración tipada desde `.env`. | Local |
| **PyInstaller** | Empaqueta todo (intérprete + librerías) en un único `LIA.exe`. | Local |
| **pytest** | Suite de pruebas (~100). | Local |
| **Obsidian** (*opcional*, externo) | Visor del grafo de notas. **No es requisito**: las notas son `.md` planos. | Local |

---

## 3. Capas y módulos (qué hace cada archivo)

### 3.1. Arranque (`main.py`, `src/bootstrap/`)
- **`main.py`** — Orquesta el arranque: auto-instalación → onboarding (si falta config) → pantalla de carga → construcción de componentes → bandeja → arranque.
- **`bootstrap/self_install.py`** — Si el `.exe` se ejecuta desde fuera de su carpeta (p. ej. Descargas), se **copia a `%LOCALAPPDATA%/Programs/LIA`**, crea accesos directos (escritorio + inicio) y se registra en "Agregar o quitar programas". Idempotente y silencioso; no actúa en desarrollo.

### 3.2. Núcleo (`src/core/`)
- **`orchestrator.py`** — Patrón **Mediator**. Recibe el atajo, gestiona la voz (grabación → Whisper → Gemini → TTS), lanza los *workers* de Gemini **con memoria conversacional**, actualiza la UI y el estado, conecta el sistema proactivo y reproduce el chime de recordatorios.
- **`state_manager.py`** — Máquina de estados (`IDLE`, `LISTENING`, `PROCESSING`, `RESPONDING`). Emite señales Qt; la UI y el orbe reaccionan.

### 3.3. Presentación (`src/gui/`)
- **`view.py`** — Panel principal **glassmorphic** translúcido, sin marcos, arrastrable. `Esc` lo oculta.
- **`orb_mascot.py`** — La presencia: orbe dibujado con `QRadialGradient`/`QConicalGradient`, con efectos por estado. Sin assets ni licencias.
- **`mascot_behavior.py`** — Mixin de ventana: colocación, clic vs. doble-clic vs. arrastre, *snap* al borde.
- **`onboarding.py`** — Diálogo de bienvenida/ajustes: nombre, clave de Gemini y carpeta de notas (se crea sola); en modo ajustes, además voz y micrófono. Escribe el `.env`.
- **`tray_icon.py`** — Icono de bandeja: mostrar/ocultar y **salir** de verdad.
- **`splash.py`** — Pantalla de carga con barra (cubre la carga de los módulos pesados).
- **`chime.py`** — Sintetiza el sonido de recordatorio (dos notas con envolvente) en un WAV; sin assets externos.
- **`md_render.py`** — Convierte el Markdown de las respuestas a HTML de Qt (negritas, listas, código, enlaces).
- **`components/`**:
  - **`chat_view.py`** — Conversación con **burbujas reales** (`QScrollArea`): usuario a la derecha, Lia a la izquierda con mini-orbe. *Streaming* token a token, indicador "escribiendo…", timestamps y Markdown al cerrar el turno.
  - **`info_panel.py`** — Popup de acciones rápidas (ejemplos + acciones) con secciones y filas icono/título/subtítulo.
  - **`input_field.py`** — Campo de entrada *pill*; `↑` recupera el último mensaje.
  - **`mascot_bubble.py`** / **`reminder_bubble.py`** — Burbujas proactiva ("Sí / Ahora no") y de recordatorio ("Listo / Posponer").

### 3.4. Percepción de hardware (`src/io/`)
- **`audio_recorder.py`** — Micrófono en hilo aparte con **VAD** (arranca al hablar, para tras un silencio).
- **`keyboard_listener.py`** — Atajo global (`QThread` + `pynput`).

### 3.5. Servicios (`src/services/`)

**Conversación y voz**
- **`gemini_service.py`** — Dos *workers* `QThread`: **Flash** (acción) y **Pro** (razonamiento). *Streaming* + **tool-calling** (el modelo invoca funciones Python locales) y **memoria conversacional** acotada entre turnos.
- **`whisper_local.py`** — Transcripción local con faster-whisper.
- **`tts_service.py`** — Voz de respuesta (Edge-TTS, singleton).
- **`os_automation.py`** — Abrir apps y portapapeles.
- **`conversation_store.py`** — Persiste el historial de la conversación (JSON) para recuperarlo entre sesiones.

**Sistema proactivo (reglas + ML)**
- **`system_monitor.py`** — Sondea portapapeles, **app activa** (`ctypes`/Win32) e **inactividad** (`GetLastInputInfo`).
- **`proactive_engine.py`** — Decide **CUÁNDO sugerir**: reglas (portapapeles *note-worthy*, foco prolongado **por app**, inactividad, fin de día) con *cooldowns*, filtradas por el scorer.
- **`relevance_scorer.py`** — **Regresión logística** (numpy puro) que predice `P(aceptar)`. *Warmup* de 10 ejemplos antes de filtrar.
- **`feedback_store.py`** — Persiste cada Sí/Ahora no en **SQLite**; entrena al scorer.
- **`reminder_service.py` / `reminders.py`** — Recordatorios con hora ("recuérdame… a las…").

**Memoria semántica e inteligencia del vault**
- **`semantic_index.py`** — Índice vectorial: embebe las notas `.md` (fastembed/ONNX), persiste vectores y reconstruye **incrementalmente por `mtime`**. Búsqueda por **coseno**. Embebedor intercambiable (stub en tests).
- **`semantic_search.py`** — Herramienta `search_notes_semantic(query)`; cae a búsqueda por palabra si el modelo no está.
- **`auto_link.py`** — Al crear una nota, busca las afines por significado y añade una sección **`🔗 Relacionado`** con enlaces `[[ ]]`. Idempotente y a prueba de fallos.
- **`topic_clusters.py`** — Clustering de **temas latentes** (KMeans esférico en numpy) sobre los vectores. Herramienta `get_note_clusters()`.
- **`daily_summary.py`** — Herramienta `get_todays_activity()`: recopila lo capturado hoy y sus conexiones; Gemini redacta el digest y lo guarda como `Diario AAAA-MM-DD`.

### 3.6. Persistencia (`src/storage/`)
- **`obsidian_manager.py`** — CRUD de notas: `create_note` (con auto-enlazado y auto-tags), `read_note`, `write_note`, `append_to_note`, **`editar_nota`** (edición fina buscar/reemplazar) y `search_notes`. Genera *frontmatter* YAML, **normaliza etiquetas** de entidades, evita duplicados y protege contra escapes de directorio.

### 3.7. Configuración y rutas (`config/`)
- **`settings.py`** — Modelo Pydantic que valida el `.env`.
- **`paths.py`** — Centraliza las rutas de datos en `%LOCALAPPDATA%/LiaAssistant` (config, historial, feedback, logs); el `.env` vive ahí en el `.exe` y en la raíz en desarrollo.
- **`logging_setup.py`** — Log a fichero (`lia.log`) + traducción de excepciones a mensajes legibles.

---

## 4. Flujos de datos principales

**a) Captura por texto/voz (con memoria)**
```
Atajo/Orbe → panel → (voz: micrófono → VAD → Whisper local) → texto
   → GeminiWorker (Flash/Pro) con historial previo, streaming + tool-calling
   → ejecuta herramientas locales (notas / portapapeles / apps / búsqueda)
   → burbuja de Lia (streaming → Markdown) → TTS → historial persistido → IDLE
```

**b) Recordatorio proactivo (con aprendizaje)**
```
SystemMonitor (portapapeles/app/inactividad)
   → ProactiveEngine (reglas + cooldown)
   → RelevanceScorer.predict() ── ¿P(aceptar) ≥ umbral? ──┐
        sí → burbuja "Sí / Ahora no" + chime               │
        no → Lia se calla                                   │
   → feedback → FeedbackStore (SQLite) → reentrena el scorer
```

**c) Crear nota con auto-enlazado**
```
create_note() → frontmatter + auto-tags de entidades
   → auto_link.find_related (índice semántico, coseno)
   → añade sección 🔗 Relacionado [[ ]] → escribe el .md
```

---

## 5. Decisiones de diseño relevantes

- **`.exe` autoinstalable**: un único archivo que al primer doble clic se copia, crea accesos y se registra. Cero fricción de distribución (sin zip, sin .bat, sin Python).
- **Orbe en vez de personaje**: profesionalidad, cero dependencias de arte/licencias y control total del render. Se descartaron gato (QPainter) y Live2D.
- **Obsidian opcional**: las notas son `.md` planos; el usuario no necesita instalar nada para usar LIA.
- **fastembed (ONNX) en vez de sentence-transformers (PyTorch)**: evita arrastrar +1 GB; viable para distribuir.
- **Regresión logística manual (numpy) en vez de scikit-learn**: cero peso extra e **interpretable**.
- **Todo lo sensible en local**: voz, embeddings, clustering y aprendizaje no salen del equipo.
- **Reconstrucción incremental del índice**: barata en cada arranque/búsqueda (solo re-embebe lo que cambió).
- **Memoria conversacional acotada**: se conservan los últimos turnos para dar contexto sin disparar el coste de tokens.

---

## 6. Estado de las fases

| Fase | Contenido | Estado |
| :--- | :--- | :--- |
| **1 — Presencia** | Orbe minimalista state-reactive. | ✅ |
| **2 — Proactividad** | Monitor + motor de reglas + burbuja, con anti-spam. | ✅ |
| **3A — Búsqueda semántica** | Búsqueda local del vault por significado. | ✅ |
| **3B — Score que aprende** | Relevancia aprendida del feedback (regresión logística). | ✅ |
| **3C — Clustering** | Temas latentes (KMeans sobre embeddings). | ✅ |
| **3D — Auto-tags** | Etiquetado de entidades vía Gemini. | ✅ |
| **3E — Auto-enlazado** | Conexión automática de notas afines. | ✅ |
| **4 — Resumen diario** | Digest que conecta lo de hoy con notas anteriores. | ✅ |
| **4.5 — Pulido** | Burbujas de chat, Markdown, onboarding, bandeja, historial, errores legibles, log, chime, atajos, edición fina. | ✅ |
| **5 — Producto** | `.exe` autoinstalable (PyInstaller) + onboarding plug-and-play. | ✅ |

### Pendiente / ideas futuras
- Captura rápida (atajo → escribir → guardar sin abrir conversación).
- Selector de color de acento; acciones "Copiar / Abrir en Obsidian" en cada burbuja.
- Firma del ejecutable (evitar el aviso de SmartScreen) y opción de LLM local para privacidad total.
