# ✧ LIA Assistant — Asistente Personal y Segundo Cerebro Autónomo

LIA es un asistente virtual de escritorio nativo de Windows, de alto rendimiento y baja latencia, diseñado como el puente de captura para tu **Segundo Cerebro (Second Brain)**. Se ejecuta como un demonio en segundo plano, vive en el escritorio como un **orbe minimalista** y se activa al instante con un atajo global para registrar, organizar y **conectar por significado** tu vida profesional y personal en tu bóveda local de Obsidian.

> 📄 ¿Buscas el detalle técnico? Lee **[ARQUITECTURA.md](ARQUITECTURA.md)** — qué tecnología se usa y qué hace cada cosa.

---

## 💡 Propósito principal

El núcleo de LIA es la **construcción automatizada de tu grafo de conocimiento**. Cada vez que registras una idea, tarea, proyecto o nota, LIA analiza la información, crea o actualiza las notas en Obsidian y las **vincula bidireccionalmente** (`[[Nota]]`) a tu perfil principal. Con el tiempo, tu grafo se dibuja solo.

A esto se suman tres capacidades que la convierten en algo más que un capturador:

- 🟣 **Presencia viva (orbe)** que reacciona a su estado y te acompaña en el escritorio.
- 🔔 **Recordatorios proactivos** que detectan cuándo merece la pena anotar algo.
- 🧠 **Memoria semántica** que encuentra tus notas por *significado*, no por palabra exacta.

---

## ✨ Funcionalidades clave

1. **Orbe minimalista state-reactive**: presencia elegante en una esquina (estilo Siri/Raycast), dibujada con gradientes animados. Late, gira y cambia de expresión según el estado (escuchando, pensando, hablando, recordando). Clic para abrir, arrastrar para mover.
2. **Recordatorios proactivos inteligentes**: un motor observa el portapapeles, la ventana activa y tu inactividad y, sin interrumpir, sugiere capturar lo importante mediante una burbuja "Sí / Ahora no".
3. **Aprendizaje del feedback (ML local)**: una regresión logística aprende de cada "Sí/Ahora no" y **silencia los patrones de recordatorio que rechazas**. Cuanto más la usas, menos molesta.
4. **Búsqueda semántica del vault**: embeddings locales (ONNX) permiten preguntar *"¿qué sé sobre productividad?"* y encontrar notas que ni mencionan esa palabra. 100% local.
5. **Captura por voz multimodal**: micrófono integrado con transcripción local asíncrona vía **Whisper**.
6. **Visión de pantalla**: captura la pantalla como contexto visual para Gemini bajo demanda ("mira mi pantalla y resume…").
7. **Vinculación bidireccional automática**: el grafo de Obsidian se autoorganiza con sintaxis `[[Nota]]`.
8. **Enrutamiento Flash/Pro**: Gemini Flash para acción rápida; Gemini Pro reservado para razonamiento o mentoría compleja.
9. **Respuesta por voz (TTS)**: confirmaciones habladas con Edge-TTS.
10. **Automatización del SO**: abrir aplicaciones, leer/escribir el portapapeles.

---

## 🛠️ Estructura del proyecto

```plaintext
LiaAssistant/
│
├── config/
│   └── settings.py              # Configuración validada con Pydantic-Settings (.env)
│
├── src/
│   ├── core/
│   │   ├── orchestrator.py      # Patrón Mediator: coordina UI, estado, voz, proactividad
│   │   └── state_manager.py     # Máquina de estados (Idle/Listening/Processing/Responding)
│   │
│   ├── gui/                     # Capa de presentación (PyQt6)
│   │   ├── view.py              # Panel glassmorphic translúcido sin marcos
│   │   ├── orb_mascot.py        # Orbe minimalista state-reactive (la presencia)
│   │   ├── mascot_behavior.py   # Mixin: colocación, clic/arrastre, snap al borde
│   │   ├── mascot_factory.py    # Construye la mascota
│   │   └── components/          # Sub-widgets (input, output, burbuja proactiva)
│   │
│   ├── io/                      # Percepción de hardware
│   │   ├── audio_recorder.py    # Captura de micrófono con VAD (hilo aparte)
│   │   └── keyboard_listener.py # Atajo global (QThread + pynput)
│   │
│   ├── services/               # Lógica de servicios (cloud y local)
│   │   ├── gemini_service.py    # Workers asíncronos Flash/Pro con tool-calling
│   │   ├── whisper_local.py     # Transcripción local (faster-whisper)
│   │   ├── tts_service.py       # Síntesis de voz (Edge-TTS)
│   │   ├── os_automation.py     # Abrir apps, portapapeles
│   │   ├── system_monitor.py    # Vigila portapapeles, ventana activa, inactividad
│   │   ├── proactive_engine.py  # Reglas + ML: decide CUÁNDO sugerir
│   │   ├── relevance_scorer.py  # Regresión logística que aprende del feedback
│   │   ├── feedback_store.py    # Persistencia del feedback (SQLite)
│   │   ├── semantic_index.py    # Índice vectorial del vault (fastembed)
│   │   └── semantic_search.py   # Herramienta search_notes_semantic
│   │
│   └── storage/
│       └── obsidian_manager.py  # CRUD + búsqueda por palabra en el Vault
│
├── tests/                       # Suite pytest (núcleo, servicios, proactivo, ML, semántico…)
├── docs/                        # Guías (validación de la Fase 2, etc.)
├── .env.example
├── requirements.txt
└── main.py                      # Punto de entrada
```

---

## 🚀 Instalación y puesta en marcha

### 1. Requisitos
* **Python 3.10 o superior**.
* **Obsidian** con una bóveda local creada.
* Una **API Key de Google Gemini** (gratis en Google AI Studio).

### 2. Entorno
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Variables de entorno
Copia `.env.example` a `.env` y rellena:
```env
GEMINI_API_KEY=tu_clave_aqui
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MODEL_REASONING=gemini-2.5-pro
OBSIDIAN_VAULT_PATH=C:\RutaDeTuVault
WHISPER_MODEL_PATH=small
TTS_ENABLED=True
USER_NAME=TuNombre
```

### 4. Ejecutar
```bash
python main.py
```
* **Mostrar/Ocultar panel**: `Shift_L + L` de forma global.
* **Abrir desde el orbe**: clic sobre el orbe; arrástralo para reposicionarlo.

---

## ⚙️ Configuración opcional

| Variable | Por defecto | Qué hace |
| :--- | :--- | :--- |
| `PROACTIVE_ENABLED` | `True` | Activa/desactiva los recordatorios proactivos. |
| `LIA_PROACTIVE_DEBUG` | `False` | Tiempos en segundos + sugerencia demo al arrancar (ver [docs/validacion_fase2.md](docs/validacion_fase2.md)). |
| `TTS_VOICE` | `es-ES-ElviraNeural` | Voz de Edge-TTS. |

---

## 🧪 Pruebas

```bash
.\venv\Scripts\pytest tests/
```

La suite cubre el núcleo, los servicios, el motor proactivo, el modelo de relevancia (ML) y la búsqueda semántica.

---

## 🔒 Privacidad

La transcripción de voz (Whisper), la búsqueda semántica (embeddings) y el aprendizaje del feedback corren **100% en tu máquina**. Solo la conversación con el modelo de lenguaje (y, bajo demanda, una captura de pantalla) viaja a la API de Gemini — nunca tu vault completo. El histórico de feedback se guarda en SQLite local bajo `%LOCALAPPDATA%/LiaAssistant`.
