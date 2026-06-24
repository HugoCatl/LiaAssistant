# 🏗️ LIA Assistant — Documento Técnico de Arquitectura

Este documento describe **toda la tecnología que usa LIA y qué hace cada pieza**. Sirve como referencia para entender el sistema de un vistazo: qué librería resuelve qué problema, cómo se reparten las responsabilidades por capas y cómo fluyen los datos.

---

## 1. Visión general

LIA es una aplicación de escritorio **Python + PyQt6** estructurada por capas (Separation of Concerns). Combina servicios en la nube (modelo de lenguaje) con cómputo **100% local** para todo lo sensible: voz, embeddings y aprendizaje del feedback.

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py (arranque)                     │
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
        │ burbuja      │  │ audio    │  │ proactivo, ML, │
        │              │  │          │  │ semántico      │
        └──────────────┘  └──────────┘  └───┬────────────┘
                                            │
                                   ┌────────▼────────┐
                                   │    storage/     │
                                   │ Obsidian Vault  │
                                   └─────────────────┘
```

---

## 2. Stack tecnológico (qué hace cada dependencia)

| Tecnología | Rol en LIA | Local / Nube |
| :--- | :--- | :--- |
| **Python 3.10+** | Lenguaje base. | — |
| **PyQt6** | Framework de GUI: ventana sin marcos, orbe (QPainter), señales/slots, hilos (`QThread`), reproducción de audio (`QtMultimedia`). | Local |
| **PyQt6 QtOpenGLWidgets + PyOpenGL** | Renderizado OpenGL transparente para la mascota Live2D opcional. | Local |
| **google-genai** | Cliente del modelo de lenguaje **Gemini** (Flash y Pro), con *streaming* y *function calling* (tool-calling). Es el cerebro conversacional. | Nube |
| **faster-whisper** | Transcripción de voz a texto (STT) en local, CPU, cuantización INT8. La voz nunca sale del equipo. | Local |
| **edge-tts** | Síntesis de voz (TTS) con voces neuronales de Microsoft Edge. | Nube |
| **sounddevice** | Captura de audio del micrófono a 16 kHz mono. | Local |
| **pynput** | Escucha del atajo global de teclado (`Shift_L + L`) en segundo plano. | Local |
| **fastembed** | Embeddings de texto vía **ONNX Runtime** (sin PyTorch). Convierte notas y consultas en vectores para la búsqueda semántica. Modelo multilingüe pequeño (≈0.22 GB). | Local |
| **numpy** | Álgebra para la búsqueda por coseno y para la regresión logística del score de relevancia. | Local |
| **sqlite3** (stdlib) | Persistencia del feedback proactivo (Sí/Ahora no). | Local |
| **Pillow** | Captura de pantalla (`ImageGrab`) como contexto visual para Gemini. | Local |
| **pyperclip** | Lectura/escritura del portapapeles de Windows. | Local |
| **live2d-py** | Runtime de modelos Live2D (Cubism 2 vía `live2d.v2`, Cubism 3 vía `live2d.v3`). Mascota tipo personaje opcional. | Local |
| **pydantic / pydantic-settings** | Validación tipada de la configuración desde `.env`. | Local |
| **python-dotenv** | Carga del archivo `.env`. | Local |
| **pytest** | Suite de pruebas automatizadas. | Local |
| **Obsidian** (externo) | Almacén final del conocimiento: notas Markdown con enlaces `[[...]]`. | Local |

---

## 3. Capas y módulos (qué hace cada archivo)

### 3.1. Núcleo (`src/core/`)
- **`orchestrator.py`** — Patrón **Mediator**. Es el director de orquesta: recibe el atajo de teclado, gestiona la voz (grabación → Whisper → Gemini → TTS), lanza los *workers* de Gemini, actualiza la UI y el estado, y conecta el sistema proactivo (monitor → motor → burbuja → mascota).
- **`state_manager.py`** — Máquina de estados finita con 4 estados (`IDLE`, `LISTENING`, `PROCESSING`, `RESPONDING`). Emite señales Qt cuando cambia; la UI y el orbe reaccionan a ellas.

### 3.2. Presentación (`src/gui/`)
- **`view.py`** — Panel principal: ventana **glassmorphic** translúcida y sin marcos, arrastrable, con campo de entrada y área de respuesta en *streaming*.
- **`orb_mascot.py`** — **Presencia por defecto**. Orbe minimalista dibujado con `QRadialGradient`/`QConicalGradient`: núcleo con volumen, halo rotatorio (hipnótico), respiración y efectos por estado (ondas al escuchar, spinner al pensar, anillos al hablar, pip al recordar). Sin assets ni licencias.
- **`live2d_mascot.py`** — Mascota tipo **personaje Live2D** (opt-in). `QOpenGLWidget` con fondo transparente; elige el runtime (`v2`/`v3`) según la extensión del modelo.
- **`mascot.py`** — Gato dibujado en QPainter (legacy, opt-in con `LIA_MASCOT=cat`). Única variante que "pasea" por el borde.
- **`mascot_behavior.py`** — **Mixin** compartido por todas las mascotas: clic vs. arrastre, *snap* al borde de pantalla y (opcional) paseo.
- **`mascot_factory.py`** — Decide qué presencia construir: orbe por defecto, Live2D si `LIVE2D_MODEL_PATH`, gato si `LIA_MASCOT=cat`.
- **`components/`** — `input_field.py`, `output_display.py` y **`mascot_bubble.py`** (la burbuja "Sí / Ahora no" de las sugerencias proactivas, con auto-descarte).

### 3.3. Percepción de hardware (`src/io/`)
- **`audio_recorder.py`** — Captura de micrófono en hilo aparte con **VAD** (detección de actividad de voz): arranca al hablar, para tras un silencio.
- **`keyboard_listener.py`** — Atajo global (`QThread` + `pynput`) que muestra/oculta el panel desde cualquier app.

### 3.4. Servicios (`src/services/`)

**Conversación y voz**
- **`gemini_service.py`** — Dos *workers* `QThread`: **Flash** (acción rápida, captura, automatización) y **Pro** (razonamiento/mentoría). Hacen *streaming* token a token y **tool-calling**: el modelo invoca funciones Python (notas, portapapeles, apps, búsqueda) que se ejecutan localmente y se le devuelven.
- **`whisper_local.py`** — Worker de transcripción local con faster-whisper.
- **`tts_service.py`** — Síntesis de voz con Edge-TTS (singleton, sanea el texto antes de hablar).
- **`os_automation.py`** — Abrir aplicaciones de Windows y leer/escribir el portapapeles.

**Sistema proactivo (Fase 2 + ML de Fase 3)**
- **`system_monitor.py`** — Sondea cada pocos segundos el **portapapeles**, el **título de la ventana activa** (`ctypes`/Win32) y los **segundos de inactividad** (`GetLastInputInfo`). Emite señales solo ante cambios relevantes.
- **`proactive_engine.py`** — **Decide CUÁNDO sugerir**. Aplica reglas (portapapeles, foco prolongado ≥30 min, inactividad, fin de día) con *cooldowns*, y antes de emitir consulta al **score de relevancia**. Si el modelo predice rechazo, Lia se calla.
- **`relevance_scorer.py`** — **Regresión logística** (numpy puro, sin sklearn) que predice `P(aceptar)` a partir de features interpretables (tipo de sugerencia *one-hot* + hora, longitud, es-URL…). *Warmup* de 10 ejemplos antes de filtrar.
- **`feedback_store.py`** — Persiste cada Sí/Ahora no en **SQLite** local (`%LOCALAPPDATA%/LiaAssistant/feedback.db`). Es la fuente de entrenamiento del scorer.

**Memoria semántica (Fase 3)**
- **`semantic_index.py`** — Índice vectorial del vault. Recorre las notas `.md`, las embebe (fastembed/ONNX), persiste los vectores y reconstruye **incrementalmente por `mtime`**. Búsqueda por **similitud de coseno**. El embebedor es intercambiable (stub determinista en tests).
- **`semantic_search.py`** — Expone la herramienta `search_notes_semantic(query)` que usa Gemini para buscar por significado. Si el modelo no está disponible, **cae a búsqueda por palabra clave**.

### 3.5. Persistencia (`src/storage/`)
- **`obsidian_manager.py`** — CRUD sobre el Vault: `create_note`, `read_note`, `write_note`, `append_to_note` y `search_notes` (por palabra). Genera *frontmatter* YAML, evita duplicados y protege contra escapes de directorio.

### 3.6. Configuración (`config/`)
- **`settings.py`** — Modelo Pydantic que valida y tipa todas las variables de `.env` (claves de Gemini, ruta del vault, voz, flags proactivos, modelo Live2D…).

---

## 4. Flujos de datos principales

**a) Captura por texto/voz**
```
Atajo/Orbe → panel → (voz: micrófono → VAD → Whisper local) → texto
   → GeminiWorker (Flash/Pro, streaming + tool-calling)
   → ejecuta herramientas locales (Obsidian / portapapeles / apps / búsqueda)
   → respuesta en streaming → TTS (Edge) → orbe vuelve a IDLE
```

**b) Recordatorio proactivo (con aprendizaje)**
```
SystemMonitor (portapapeles/ventana/inactividad)
   → ProactiveEngine (reglas + cooldown)
   → RelevanceScorer.predict()  ── ¿P(aceptar) ≥ umbral? ──┐
        sí → burbuja "Sí / Ahora no" junto al orbe          │
        no → Lia se calla                                    │
   → feedback del usuario → FeedbackStore (SQLite) → reentrena el scorer
```

**c) Búsqueda semántica**
```
Pregunta conceptual → Gemini llama a search_notes_semantic()
   → SemanticIndex.build() (incremental) → embeddings ONNX
   → similitud de coseno → notas más afines → respuesta
```

---

## 5. Decisiones de diseño relevantes

- **Orbe en vez de personaje**: máxima profesionalidad, cero dependencias de arte/licencias y control total del render. El modo personaje (Live2D) queda como opt-in.
- **fastembed (ONNX) en vez de sentence-transformers (PyTorch)**: evita arrastrar +1 GB de dependencias; viable para distribuir.
- **Regresión logística manual (numpy) en vez de scikit-learn**: cero peso extra e **interpretable** (se puede ver por qué Lia decide callar).
- **Todo lo sensible en local**: voz, embeddings y aprendizaje no salen del equipo; al modelo de lenguaje solo va la conversación.
- **Reconstrucción incremental del índice**: barata en cada arranque/búsqueda (solo re-embebe lo que cambió).

---

## 6. Estado de las fases

| Fase | Contenido | Estado |
| :--- | :--- | :--- |
| **1 — Presencia** | Orbe minimalista state-reactive; pipeline Live2D opcional. | ✅ |
| **2 — Proactividad** | Monitor de sistema + motor de reglas + burbuja no invasiva. | ✅ |
| **3 — Cerebro (parte A)** | Búsqueda semántica local del vault (fastembed). | ✅ |
| **3 — Cerebro (parte B)** | Score de relevancia que aprende del feedback. | ✅ |
| **3 — Cerebro (resto)** | Auto-tags (NER), clustering de temas. | ⏳ Pendiente |
| **4 — Resumen diario** | Digest que conecta capturas en conocimiento. | ⏳ Pendiente |
| **5 — Producto** | Instalador, settings UI, onboarding, arranque con Windows. | ⏳ Pendiente |
