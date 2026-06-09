# Plan de Implementación - Fase 4: Integración con Obsidian (Persistencia y Memoria a Largo Plazo)

Proponer y estructurar la **Fase 4** del desarrollo de LIA Assistant, enfocada en la creación de su capa de memoria (Storage). El objetivo es conectar a LIA con un "Vault" (bóveda) local de Obsidian, dándole la capacidad de actuar como tu "Segundo Cerebro" (Second Brain).

## Resumen de la Fase 4

LIA podrá guardar de forma autónoma resúmenes de conversaciones, recordar ideas clave que le dictes, o buscar información en tus notas pasadas directamente manipulando archivos Markdown locales de Obsidian. Todo esto será posible inyectando nuevas herramientas (Tools/Function Calling) en el enrutador lógico de Gemini.

---

## Preguntas Abiertas

> [!WARNING]
> **Ruta del Vault de Obsidian**: Necesitarás configurar en el archivo `.env` la ruta absoluta hacia tu carpeta principal de Obsidian (`OBSIDIAN_VAULT_PATH=C:\Ruta\A\Tu\Vault`). ¿Tienes ya un Vault específico de pruebas para LIA o usaremos tu Vault personal principal?

> [!IMPORTANT]
> **Permisos y Modificación de Notas**: ¿Deseas que LIA tenga permisos absolutos para **sobrescribir/editar** notas existentes, o preferimos que por seguridad en esta fase solo pueda **crear nuevas notas** (añadiendo la fecha/hora en el título) y **leer/buscar** en el Vault? Mi recomendación es empezar con crear y leer, para proteger tus notas originales.

---

## Cambios Propuestos

### Capa de Persistencia y Memoria

#### [NUEVO] [obsidian_manager.py](file:///c:/LiaAssistant/src/storage/obsidian_manager.py)
Creación del módulo base para interactuar con el sistema de archivos del Vault.
- **Funciones principales**:
  - `create_note(title: str, content: str, tags: list[str] = None)`: Crea un archivo `.md` en la carpeta base del Vault.
  - `read_note(title: str) -> str`: Lee el contenido de una nota existente.
  - `search_notes(query: str) -> list[str]`: Busca palabras clave dentro del contenido de todas las notas del Vault y devuelve los extractos relevantes.

---

### Capa de Servicios Externos

#### [MODIFICAR] [gemini_service.py](file:///c:/LiaAssistant/src/services/gemini_service.py)
- Importar las funciones de `obsidian_manager.py`.
- Añadir las funciones `create_note`, `read_note` y `search_notes` al arreglo de `tools` de la configuración de Gemini.
- Actualizar la `system_instruction` para que LIA sepa de la existencia de su "Memoria" en Obsidian y sepa cuándo debe guardar información útil o buscarla si no sabe la respuesta a algo del usuario.

#### [MODIFICAR] [orchestrator.py](file:///c:/LiaAssistant/src/core/orchestrator.py)
- Añadir el enrutamiento lógico para interceptar cuándo Gemini llama a las funciones de Obsidian (en la señal `tool_call_detected`), ejecutarlas de forma asíncrona y devolverle a Gemini el resultado de la búsqueda o la confirmación de guardado.

---

## Plan de Verificación

### Pruebas Automatizadas
- Crear el archivo `tests/test_storage.py` con pruebas unitarias para `obsidian_manager.py` usando un directorio temporal (mock_vault) para asegurar que se leen y escriben los archivos `.md` correctamente sin afectar un Vault real.

### Verificación Manual
1. Iniciar la aplicación de LIA.
2. Darle una orden de guardado: *"LIA, guarda en mis notas que la contraseña del router es 1234"* y comprobar en la UI que LIA confirma la acción.
3. Verificar físicamente abriendo la aplicación de Obsidian y buscando la nueva nota generada por LIA.
4. En otra sesión, preguntarle: *"LIA, ¿recuerdas cuál me dijiste que era la contraseña del router?"*. Verificar que LIA realiza una búsqueda en Obsidian antes de responder con el dato exacto.
