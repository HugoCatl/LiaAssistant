# Plan de Implementación - Respuestas Humanas y Naturales (Sin Detalles Técnicos)

Este plan detalla el cambio en el comportamiento de respuesta de LIA para hacerla mucho más conversacional, natural y similar a una persona, evitando cualquier jerga técnica, mención a búsquedas de notas, o avisos de que está consultando u obteniendo información de archivos locales de Obsidian.

## User Review Required

> [!IMPORTANT]
> **Ocultar Origen de la Información**:
> - LIA ya no dirá frases como: *"He buscado en tu nota..."*, *"De acuerdo a tus apuntes..."*, o *"He encontrado en Obsidian..."*. 
> - En su lugar, responderá directamente de forma fluida y natural, actuando como si ella recordara la información por sí misma.
>
> **Confirmación Natural de Acciones**:
> - En lugar de confirmar la creación de archivos con nombres técnicos (ej: *"He creado la nota 'Rutina de Gimnasio.md' en tu vault"*), LIA lo dirá de manera conversacional (ej: *"He guardado tu nueva rutina de gimnasio, espero que te sirva mucho para motivarte"*).
LLL
## Proposed Changes

### Capa de Servicios

#### [MODIFY] [gemini_service.py](file:///c:/LiaAssistant/src/services/gemini_service.py)

- **Actualizar `GeminiWorker` (Flash)**:
  - Añadir directrices en su `system_instruction` para responder de forma concisa pero sumamente natural y humana.
  - Prohibir terminantemente el uso de terminología sobre archivos, notas, llamadas de sistema o el origen de sus datos.
- **Actualizar `GeminiReasoningWorker` (Pro)**:
  - Robustecer su `system_instruction` con directrices de personalidad. LIA debe actuar como un mentor o amigo cercano.
  - Prohibir cualquier mención técnica a Obsidian, notas específicas, o búsquedas realizadas en segundo plano. Cuando consulte la memoria del usuario, debe responder integrando la información de manera invisible y fluida (ej: si sabe que el usuario va al gimnasio Viver, responder *"Como vas al gimnasio Viver, te sugiero..."* en vez de *"He encontrado en tu nota de hobbies que vas al gimnasio Viver, por lo tanto..."*).

## Verification Plan

### Automated Tests
- Ejecutar `pytest` para comprobar que la lógica interna de los agentes de Gemini y el Orquestador no sufren regresiones.

### Manual Verification
1. Iniciar la aplicación de LIA.
2. Hacer una pregunta de memoria: *"¿Te acuerdas de mis amigos del gimnasio?"*
   - **Comportamiento esperado**: LIA responderá algo como: *"Sí, claro, Juanjo y Pablo, que viven en Gérica"* en lugar de *"Sí, he buscado en tu nota 'Amigos del Gimnasio' y he visto que Juanjo y Pablo viven en Gérica"*.
3. Pedir a LIA que cree una nota: *"Guarda que mañana tengo cita médica a las 10:00"*.
   - **Comportamiento esperado**: LIA guardará la nota en segundo plano y responderá: *"Perfecto, ya lo he anotado en tu agenda para que no se te pase"* en lugar de *"He guardado 'Cita Médica' en tu vault de Obsidian con la etiqueta #salud"*.
