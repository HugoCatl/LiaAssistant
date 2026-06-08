# ✧ LIA Assistant - Asistente Virtual de Escritorio

LIA Assistant es un asistente virtual de escritorio de alto rendimiento, baja latencia y consumo optimizado diseñado para integrarse con el sistema operativo de forma nativa. Opera como un servicio en segundo plano (daemon) y se activa a través de interrupciones globales de teclado.

---

## 🛠️ Arquitectura y Estructura del Proyecto

El código está organizado de forma modular siguiendo el principio de Separación de Concernimientos (Separation of Concerns) para facilitar la mantenibilidad y escalabilidad del sistema:

```plaintext
LiaAssistant/
│
├── config/                         # Gestión de variables de entorno y perfiles
│   ├── __init__.py
│   └── settings.py                 # Validación de variables con Pydantic-Settings
│
├── src/                            # Código fuente de la aplicación
│   ├── __init__.py
│   │
│   ├── core/                       # Núcleo lógico (Orquestador y Máquina de Estados)
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Patrón Mediator para coordinar la UI, Eventos y Estado
│   │   └── state_manager.py        # Gestión del estado del asistente (Idle, Listening, Processing, Responding)
│   │
│   ├── gui/                        # Capa de Presentación (Interfaz Gráfica)
│   │   ├── __init__.py
│   │   ├── components/             # Sub-widgets reutilizables
│   │   │   ├── input_field.py      # Entrada de texto personalizada
│   │   │   └── output_display.py   # Área de salida de texto para respuestas
│   │   └── view.py                 # Ventana principal translúcida y sin marcos (PyQt6)
│   │
│   ├── io/                         # Capa de Percepción e Interacción de Hardware
│   │   ├── __init__.py
│   │   └── keyboard_listener.py    # Captura global de eventos de teclado (QThread + pynput)
│   │
│   ├── services/                   # Proveedores de Servicios Externos y Locales (Próximos sprints)
│   │   └── __init__.py
│   │
│   └── storage/                    # Capa de Persistencia y Memoria (Próximos sprints)
│       └── __init__.py
│
├── tests/                          # Suite de pruebas automatizadas
│   ├── __init__.py
│   ├── test_core.py                # Pruebas del núcleo (configuración y estados)
│   └── test_services.py            # Pruebas de los servicios
│
├── .env.example                    # Plantilla de variables de entorno
├── requirements.txt                # Dependencias fijadas del proyecto
└── main.py                         # Punto de entrada de la aplicación
```

---

## 🚀 Instalación y Puesta en Marcha

Siga los siguientes pasos para configurar el entorno localmente en Windows:

### 1. Requisitos Previos
* **Python 3.10 o superior** instalado en el sistema.

### 2. Clonar y Configurar el Entorno
Cree un entorno virtual limpio e instale las dependencias necesarias:

```bash
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual
.\venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
Copie la plantilla de configuración e ingrese sus claves:

```bash
cp .env.example .env
```

Edite el archivo `.env` para añadir su `GEMINI_API_KEY` u otras rutas locales (por ejemplo, el Vault de Obsidian).

---

## ⌨️ Uso de la Aplicación

Inicie el servicio de LIA Assistant ejecutando:

```bash
python main.py
```

### Controles de la Interfaz
- **Mostrar/Ocultar**: Presione la combinación de teclas **`Shift_L + L`** de forma global desde cualquier ventana o aplicación para mostrar u ocultar el asistente.
- **Mover la Ventana**: Haga clic y arrastre con el botón izquierdo del ratón en cualquier parte vacía del panel del asistente para reposicionar la ventana translúcida en su pantalla.
- **Cerrar en Segundo Plano**: Al presionar la `×` superior, el asistente se ocultará, pero seguirá escuchando el atajo de teclado en segundo plano (daemon). Para cerrar por completo el proceso, termine la ejecución en su terminal.

---

## 🧪 Pruebas Unitarias

Para ejecutar el conjunto de pruebas unitarias y verificar el correcto funcionamiento del núcleo:

```bash
# Ejecutar pytest desde el entorno virtual
.\venv\Scripts\pytest tests/
```
