# ✧ LIA Assistant - Asistente Personal y Segundo Cerebro Autónomo

LIA es un asistente virtual de escritorio nativo de Windows, de alto rendimiento y baja latencia, diseñado para servir como el puente de captura para tu **Segundo Cerebro (Second Brain)**. Se ejecuta como un demonio en segundo plano y se activa de forma instantánea mediante un atajo global de teclado para registrar, organizar y conectar tu vida profesional y personal directamente en tu bóveda local de Obsidian.

---

## 💡 Propósito Principal

El núcleo de LIA es la **construcción automatizada de tu gráfico de conocimiento**. Cada vez que registras una tarea, proyecto de IA, tema de estudio, hobby, nota de amigos o credenciales, LIA analiza la información, crea o actualiza las notas correspondientes en Obsidian y las **vincula bidireccionalmente** mediante corchetes dobles (`[[Nota]]`) al perfil principal (por ejemplo, `[[TuNombre]]`). Con el tiempo, tu gráfico de relaciones en Obsidian se dibuja solo, permitiéndote navegar visualmente por tus pensamientos y proyectos sin esfuerzo de organización manual.

---

## 🛠️ Arquitectura y Estructura del Proyecto

El código está organizado modularmente siguiendo el principio de Separación de Concernimientos (Separation of Concerns):

```plaintext
LiaAssistant/
│
├── config/                         # Gestión de variables de entorno y perfiles
│   ├── __init__.py
│   └── settings.py                 # Validación con Pydantic-Settings
│
├── src/                            # Código fuente de la aplicación
│   ├── __init__.py
│   │
│   ├── core/                       # Núcleo lógico (Orquestador y Máquina de Estados)
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Patrón Mediator. Coordina la UI, Eventos y Estado
│   │   └── state_manager.py        # Gestión del estado del asistente (Idle, Listening, Processing, Responding)
│   │
│   ├── gui/                        # Capa de Presentación (Interfaz Gráfica)
│   │   ├── __init__.py
│   │   ├── components/             # Sub-widgets PyQt6 reutilizables
│   │   │   ├── input_field.py      # Entrada de texto personalizada
│   │   │   └── output_display.py   # Área de salida de texto para respuestas
│   │   └── view.py                 # Ventana principal translúcida y sin marcos con diseño Glassmorphism
│   │
│   ├── io/                         # Capa de Percepción e Interacción de Hardware
│   │   ├── __init__.py
│   │   ├── audio_recorder.py       # Captura de audio de micrófono en hilo secundario
│   │   └── keyboard_listener.py    # Captura global de eventos de teclado (QThread + pynput)
│   │
│   ├── services/                   # Proveedores de Servicios Externos y Locales
│   │   ├── __init__.py
│   │   ├── gemini_service.py       # Workers asíncronos para Gemini Flash y Pro
│   │   ├── os_automation.py        # Automatización de Windows (abrir apps, etc.)
│   │   └── whisper_local.py        # Transcripción local de audio con Whisper
│   │
│   └── storage/                    # Capa de Persistencia y Memoria
│       ├── __init__.py
│       └── obsidian_manager.py     # Gestor de lectura, escritura y búsqueda en el Vault local
│
├── tests/                          # Suite de pruebas automatizadas
│   ├── __init__.py
│   ├── test_core.py                # Pruebas de configuración y máquina de estados
│   ├── test_services.py            # Pruebas de automatización e integración de modelos
│   └── test_storage.py             # Pruebas de lectura/escritura en Obsidian
│
├── .env.example                    # Plantilla de variables de entorno
├── requirements.txt                # Dependencias fijadas del proyecto
└── main.py                         # Punto de entrada de la aplicación
```

---

## ✨ Funcionalidades Clave

1. **Interfaz Glassmorphic Fluida**: Ventana translúcida elegante sin bordes, con efectos de desenfoque y sombras de color purpura que se superpone a cualquier app.
2. **Interacción Proactiva**: LIA te recibe dinámicamente con saludos motivadores cada vez que inicias o abres el panel (ej. *"¡Hola Usuario! ¿Qué idea se te ha ocurrido hoy? 💡"*), incitándote a registrar tus pensamientos.
3. **Captura por Voz Multimodal**: Micrófono integrado y transcripción local asíncrona mediante **Whisper** para registrar notas simplemente hablando.
4. **Vinculación Bidireccional Inteligente**: Auto-conexión de notas mediante sintaxis de doble corchete `[[Nota]]` para que el mapa relacional de Obsidian se autoorganice en segundo plano.
5. **Enrutamiento y Ahorro de Tokens**:
   - **Gemini Flash (Worker de Acción)**: Ejecuta rápidamente la captura de notas, edición en Obsidian y comandos de sistema.
   - **Gemini Pro (Worker de Razonamiento)**: Reservado exclusivamente para peticiones explícitas de análisis a fondo o mentoría compleja.
6. **Automatización del OS**: Capacidad de iniciar aplicaciones del sistema (`bloc de notas`, `calculadora`, `Paint 3D`, `Teams`, etc.) por comando directo.

---

## 🚀 Instalación y Puesta en Marcha

### 1. Requisitos Previos
* **Python 3.10 o superior** instalado en el sistema.

### 2. Configurar el Entorno
```bash
# Crear y activar el entorno virtual
python -m venv venv
.\venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
Copia el archivo `.env.example` a `.env` y rellena las claves correspondientes:
```env
GEMINI_API_KEY=tu_clave_aqui
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MODEL_REASONING=gemini-2.5-pro
OBSIDIAN_VAULT_PATH=C:\LIAI
WHISPER_MODEL_PATH=small
DEBUG=True
```

### 4. Ejecutar la Aplicación
```bash
python main.py
```
* **Mostrar/Ocultar**: Presiona la combinación de teclas **`Shift_L + L`** de forma global desde cualquier ventana.
* **Mover la Ventana**: Haz clic y arrastra con el botón izquierdo sobre el panel para reposicionar la ventana.

---

## 🧪 Pruebas Unitarias

Para ejecutar el conjunto de pruebas unitarias:
```bash
.\venv\Scripts\pytest tests/
```
