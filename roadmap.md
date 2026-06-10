# 🗺️ LIA Assistant - Hoja de Ruta y Futuras Fases

Este documento detalla las opciones propuestas para expandir las capacidades de LIA en sus próximas etapas de desarrollo.

---

## 🚀 Opciones de Expansión

### 1. Fase: Contexto de Pantalla Activa (Visión Multimodal) 👁️
Permitir que LIA vea y analice lo que tienes abierto en pantalla en el momento de activarla.
* **Mecánica**: Al presionar `Shift_L + L`, se toma una captura de pantalla invisible de la ventana activa y se envía a Gemini como entrada de imagen.
* **Casos de Uso**:
  - *"Resume esta web que tengo abierta"* (sin copiar y pegar).
  - *"Explícame el error en esta captura de pantalla de mi consola"*.
  - *"Guarda esta tabla/infografía en mi nota de proyectos de Obsidian"*.

### 2. Fase: Integración del Portapapeles (Clipboard) y Búsqueda Web 🌐
Mejorar la interacción con el sistema operativo y la web.
* **Mecánica**:
  - **Portapapeles**: Herramientas para leer y escribir el portapapeles de Windows (ej. *"Copia al portapapeles el último código"* o *"Crea una nota con el texto que tengo copiado"*).
  - **Búsqueda Web**: Integrar una API de búsqueda en internet para responder preguntas de actualidad o buscar documentación reciente.

### 3. Fase: Dashboard Diario y Resúmenes Autónomos 📊
Delegar a LIA la organización activa de la bóveda de Obsidian.
* **Mecánica**: Tarea en segundo plano que compila al final del día toda la información capturada de forma fragmentada.
* **Casos de Uso**:
  - Creación de una nota `Diario 2026-06-11.md` estructurando: Ideas de IA generadas, Tareas profesionales completadas/pendientes, Resumen de entrenamientos/hobbies del día, y Enlaces sugeridos para el gráfico de conocimiento.

### 4. Fase: Respuestas por Voz Activas (TTS - Text to Speech) 🗣️
Hacer que LIA sea un asistente manos libres completo.
* **Mecánica**: Integración de un motor de voz (local como `pyttsx3` o mediante APIs en la nube de alta calidad).
* **Casos de Uso**: Escuchar la confirmación de LIA o explicaciones de notas por audio sin tener que leer el panel.

---

## 🧠 Reflexión Técnica: ¿Es el momento de migrar a Ollama (Modelos Locales)?

La propuesta de usar **Ollama** para que los tokens sean 100% gratuitos y el sistema funcione de forma local/privada es muy atractiva, pero conlleva un equilibrio de pros y contras técnicos:

| Criterio | Enfoque Actual (Gemini API) | Enfoque Local (Ollama) |
| :--- | :--- | :--- |
| **Costo de Tokens** | De pago (aunque Gemini Flash es sumamente económico, fracciones de céntimo). | **100% Gratis e ilimitados**. |
| **Consumo de Hardware** | Prácticamente **cero**. Todo el cómputo pesado ocurre en servidores de Google. | **Muy alto**. Requiere uso intensivo de GPU y VRAM (mínimo 6GB-8GB dedicados para modelos de 8B parámetros). |
| **Impacto en el PC** | No afecta el rendimiento de otras aplicaciones (juegos, compiladores). | Puede causar caídas de frames en juegos o ralentización del PC mientras el modelo razona. |
| **Llamada a Herramientas** | **Excelente**. Gemini soporta nativamente la ejecución de funciones (`tools`) con gran precisión. | **Limitado/Inestable**. Modelos pequeños (como Llama-3 8B) suelen cometer errores en la sintaxis de llamada a funciones. |
| **Privacidad** | Los datos viajan a la API de Google. | **Absoluta**. Ningún dato sale de tu ordenador. |

### Propuesta Híbrida Recomendada (Best of Both Worlds) 🧩
En lugar de una migración total, una excelente alternativa es el **enfoque híbrido**:
1. **LIA Local (Ollama)** para notas sensibles, resúmenes cotidianos y capturas sencillas sin llamadas a sistema pesadas.
2. **LIA Cloud (Gemini Flash)** para cuando requieras automatización compleja (abrir apps, búsquedas webs, etc.) o cuando estés jugando/trabajando con alta carga en el PC para no saturar tus recursos locales.
