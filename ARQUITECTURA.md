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
| **PyQt6** | Framework de GUI: ventana sin marcos, orbe (QPainter con gradientes), señales/slots, hilos (`QThread`), reproducción de audio (`QtMultimedia`). | Local |
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
- **`orb_mascot.py`** — La presencia de Lia en el escritorio. Orbe minimalista dibujado con `QRadialGradient`/`QConicalGradient`: núcleo con volumen, halo rotatorio (hipnótico), respiración y efectos por estado (ondas al escuchar, spinner al pensar, anillos al hablar, pip al recordar). Sin assets ni licencias.
- **`mascot_behavior.py`** — **Mixin** con el comportamiento de ventana: colocación en el borde, clic vs. arrastre y *snap* al borde de pantalla.
- **`mascot_factory.py`** — Construye la mascota (`make_mascot()`), punto único de creación.
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

**Clustering de temas (Fase 3B)**
- **`topic_clusters.py`** — Agrupa las notas en **temas latentes** reutilizando los vectores del índice semántico. KMeans esférico (coseno) en numpy puro. Expone la herramienta `get_note_clusters()`: descubre patrones ("tienes N notas sobre X"), etiqueta cada tema con su nota más representativa.

**Resumen diario (Fase 4)**
- **`daily_summary.py`** — Expone la herramienta `get_todays_activity()`: recopila las notas capturadas **hoy** (por `mtime`) y, con el índice semántico, descubre sus **conexiones con notas anteriores**. Devuelve datos a Gemini, que redacta el digest y lo guarda como nota `Diario AAAA-MM-DD`. La herramienta no llama al LLM (evita recursión/coste).

### 3.5. Persistencia (`src/storage/`)
- **`obsidian_manager.py`** — CRUD sobre el Vault: `create_note`, `read_note`, `write_note`, `append_to_note` y `search_notes` (por palabra). Genera *frontmatter* YAML, evita duplicados y protege contra escapes de directorio.

### 3.6. Configuración (`config/`)
- **`settings.py`** — Modelo Pydantic que valida y tipa todas las variables de `.env` (claves de Gemini, ruta del vault, voz, flags proactivos…).

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

- **Orbe en vez de personaje**: máxima profesionalidad, cero dependencias de arte/licencias y control total del render. Se descartaron las mascotas tipo personaje (gato QPainter y Live2D) para no añadir peso ni distracción a una herramienta de productividad.
- **fastembed (ONNX) en vez de sentence-transformers (PyTorch)**: evita arrastrar +1 GB de dependencias; viable para distribuir.
- **Regresión logística manual (numpy) en vez de scikit-learn**: cero peso extra e **interpretable** (se puede ver por qué Lia decide callar).
- **Todo lo sensible en local**: voz, embeddings y aprendizaje no salen del equipo; al modelo de lenguaje solo va la conversación.
- **Reconstrucción incremental del índice**: barata en cada arranque/búsqueda (solo re-embebe lo que cambió).

---

## 6. Estado de las fases

| Fase | Contenido | Estado |
| :--- | :--- | :--- |
| **1 — Presencia** | Orbe minimalista state-reactive en el escritorio. | ✅ |
| **2 — Proactividad** | Monitor de sistema + motor de reglas + burbuja no invasiva. | ✅ |
| **3A — Búsqueda semántica** | Búsqueda local del vault por significado (fastembed). | ✅ |
| **3B — Score que aprende** | Relevancia que aprende del feedback (regresión logística). | ✅ |
| **3C — Clustering** | Descubrimiento de temas latentes (KMeans sobre embeddings). | ✅ |
| **3D — Auto-tags** | Etiquetado de entidades (persona/proyecto/lugar) vía Gemini. | ✅ |
| **4 — Resumen diario** | Digest que conecta capturas de hoy con notas anteriores. | ✅ |
| **4.5 — Pulido profesional** | Ajustes in-app, bandeja del sistema, onboarding, historial… (ver §7). | ⏳ Pendiente |
| **5 — Producto** | Instalador `.exe`, arranque con Windows, distribución. | ⏳ Pendiente |

---

## 7. Fase 4.5 — Pulido profesional (backlog priorizado)

Mejoras de bajo coste y alto impacto en la percepción de "producto", **antes** del empaquetado de la Fase 5. Ordenadas por ratio valor/esfuerzo.

### Tier 1 — Quick wins (≈1–2 h)
1. **Icono en la bandeja del sistema** (`QSystemTrayIcon`): mostrar/ocultar, abrir ajustes y **salir** de verdad. Comportamiento esperable de toda app de escritorio.
2. **Onboarding de primer arranque**: si falta `GEMINI_API_KEY` o `OBSIDIAN_VAULT_PATH`, un diálogo amable para configurarlos en vez de un error.
3. **Manejo elegante de errores**: mensajes claros (API caída, sin red, clave inválida) en lugar de excepciones crudas.
4. **Log a fichero**: diagnóstico en `%LOCALAPPDATA%/LiaAssistant/lia.log` (rotativo).
5. **Arranque con Windows** (opcional): acceso directo en la carpeta de inicio, con toggle.

### Tier 2 — Media jornada, alto impacto
6. **Panel de Ajustes in-app**: editar clave, vault, nombre/perfil, voz TTS, color de acento y flags proactivos **sin tocar `.env`**. Con botón "Probar" para validar clave/vault.
7. **Historial de conversación persistente**: al reabrir el panel se recupera el contexto reciente (SQLite local).
8. **Render Markdown en las respuestas**: negritas, listas y bloques de código (gran salto visual sobre el texto plano actual).
9. **Modo captura rápida**: atajo → escribes → Enter guarda la nota al instante, sin abrir conversación.

### Tier 3 — Toques finos (pequeños)
10. **Selector de color de acento**: unifica orbe + panel; personalización con sensación premium.
11. **Acciones en la respuesta**: "Copiar" y "Abrir en Obsidian".
12. **Diálogo Acerca de / versión**.
