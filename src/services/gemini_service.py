from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from google import genai
from google.genai import types
from config import settings
from src.services.os_automation import open_application, get_clipboard_content, set_clipboard_content
from src.storage.obsidian_manager import (
    create_note, read_note, search_notes, search_notes_semantic,
    write_note, append_to_note, editar_nota,
)
from src.services.daily_summary import get_todays_activity
from src.services.topic_clusters import get_note_clusters
from src.services.vault_gardener import (
    revisar_memoria, marcar_entidades_distintas, ignorar_nota_suelta,
)
from src.services.entity_card import ficha_entidad
from src.services.reminders import crear_recordatorio, listar_recordatorios

# Map tool names to python functions for execution inside workers
TOOL_MAP = {
    "open_application": open_application,
    "create_note": create_note,
    "read_note": read_note,
    "search_notes": search_notes,
    "search_notes_semantic": search_notes_semantic,
    "get_todays_activity": get_todays_activity,
    "get_note_clusters": get_note_clusters,
    "revisar_memoria": revisar_memoria,
    "marcar_entidades_distintas": marcar_entidades_distintas,
    "ignorar_nota_suelta": ignorar_nota_suelta,
    "ficha_entidad": ficha_entidad,
    "write_note": write_note,
    "append_to_note": append_to_note,
    "editar_nota": editar_nota,
    "get_clipboard_content": get_clipboard_content,
    "set_clipboard_content": set_clipboard_content,
    "crear_recordatorio": crear_recordatorio,
    "listar_recordatorios": listar_recordatorios,
}


def _graph_rules(profile: str) -> str:
    """
    Reglas de construcción del GRAFO de conocimiento, compartidas por ambos workers
    (fuente única para que no se desincronicen). Enseñan a Lia a crear una nota por
    entidad, enlazarlas entre sí (no solo al perfil) y propagar las relaciones a
    todas las notas implicadas.
    """
    return (
        "GRAFO DE CONOCIMIENTO (muy importante):\n"
        "1) ENTIDAD = NOTA PROPIA. Cada persona, empresa u organización, proyecto o lugar "
        "relevante con el que el usuario tiene relación merece su PROPIA nota (`create_note`), "
        "no solo una etiqueta. Ej.: si menciona su empresa 'Ahora Soluciones Software', crea "
        "una nota para esa empresa. Antes de crear, usa `search_notes` para no duplicar; si ya "
        "existe, actualízala con `append_to_note`/`editar_nota`.\n"
        "2) ENLACES CRUZADOS ENTRE ENTIDADES. En el CONTENIDO de cada nota (nunca en tu respuesta) "
        "enlaza con `[[ ]]` a las OTRAS entidades relacionadas, no solo al perfil. Ej.: la nota de "
        f"un compañero enlaza a `[[su empresa]]` y a `[[{profile}]]`; la nota de la empresa enlaza "
        "a sus miembros; y esas notas enlazan de vuelta (bidireccional real, no solo hacia el perfil).\n"
        "3) PROPAGA LAS RELACIONES. Cuando el usuario aporte o CAMBIE una relación (jefe, amigo, "
        "compañero, pareja, cliente…), actualiza TODAS las notas implicadas, no una sola. Ej.: "
        "'Guille es mi jefe' → añade ese hecho tanto en el perfil del usuario como en la nota de "
        "Guille (con `append_to_note` o `editar_nota`). Una relación siempre vive en los dos nodos.\n"
        "4) DETECTA CONTRADICCIONES. Antes de guardar un dato sobre una entidad, lee lo que ya hay "
        "(`read_note`/`ficha_entidad`). Si el dato nuevo CONTRADICE lo guardado (ej.: antes "
        "'compañero', ahora 'jefe'; una fecha distinta; otra empresa), díselo brevemente al usuario "
        "('antes me dijiste X, ¿me quedo con Y?') y, cuando confirme, SUSTITUYE el dato viejo con "
        "`editar_nota` en TODAS las notas donde aparezca — nunca dejes las dos versiones conviviendo.\n"
    )


class GeminiWorker(QThread):
    """
    Trabajador asíncrono (Agente de Acción Rápida) en QThread que maneja el modelo Gemini Flash.
    Optimizado para responder rápidamente, ejecutar comandos de automatización y realizar guardados rápidos en Obsidian.
    """
    token_received = pyqtSignal(str)
    tool_call_detected = pyqtSignal(str, dict)
    tool_call_completed = pyqtSignal(str, str)
    tokens_consumed = pyqtSignal(int, int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt: str, image_path: str = None, history: list = None):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path
        self.history = history or []          # turnos previos (memoria conversacional)
        self.result_contents = []             # conversación actualizada tras este turno
        self._cancelled = False               # cancelación cooperativa (ver cancel())
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model

    def cancel(self):
        """Pide cancelar el turno en curso; el bucle de streaming lo respeta."""
        self._cancelled = True

    def run(self):
        if not self.api_key:
            self.error_occurred.emit("Error: La clave GEMINI_API_KEY no está configurada.")
            return

        try:
            # Timeout duro por petición (evita que la UI quede en "Pensando…" para
            # siempre si la conexión se cuelga) + 1 reintento ante errores
            # transitorios (408/429/5xx) con backoff.
            client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=120_000,  # ms
                    retry_options=types.HttpRetryOptions(attempts=2, initial_delay=1.0),
                ),
            )
            tools_list = [
                open_application, create_note, read_note, search_notes, search_notes_semantic,
                get_todays_activity, get_note_clusters, revisar_memoria,
                marcar_entidades_distintas, ignorar_nota_suelta,
                ficha_entidad, write_note, append_to_note, editar_nota,
                get_clipboard_content, set_clipboard_content,
                crear_recordatorio, listar_recordatorios,
            ]

            system_instruction = (
                f"Eres LIA, asistente virtual para {settings.user_name} (perfil: `{settings.user_profile}`).\n"
                "Objetivo: velocidad, precisión y gestión de memoria de ideas profesionales, proyectos de IA, tareas, estudios y temas personales. Sé breve, conversacional y muy natural.\n"
                "Habla siempre al usuario en segunda persona (tú). Habla de forma cercana y amigable.\n"
                "REGLA DE ORO: Nunca menciones Obsidian, archivos .md, notas, búsquedas, herramientas ni origen de datos en tus respuestas al usuario. Tampoco uses corchetes `[[Nota]]` en ellas. Confirma acciones de manera invisible y cotidiana.\n"
                f"Asocia la información en primera persona expresada por el usuario al perfil de {settings.user_name} y guárdala en su nota de perfil (evita crear notas paralelas como 'Yo').\n"
                "Antes de guardar, busca notas con `search_notes`. Si existen, actualízalas con `write_note` o `append_to_note` para no duplicar.\n"
                "Para cambiar un dato puntual de una nota existente (una fecha, un nombre, una línea), usa `editar_nota(title, buscar, reemplazar)` con el fragmento exacto a cambiar, en lugar de reescribir la nota entera con `write_note`. Si no conoces el texto exacto, léela antes con `read_note`.\n"
                "Siempre que te pregunten sobre algún proyecto, concepto, tarea o información del usuario, busca en su memoria antes de responder: usa `search_notes_semantic` para preguntas abiertas o conceptuales (temas, ideas, 'qué sé sobre...'), `search_notes` para palabras o títulos exactos, y `read_note` si conoces el nombre de la nota.\n"
                "Si pregunta por una entidad concreta (una persona, empresa, proyecto o lugar: 'cuéntame sobre X', 'qué sabes de X', 'quién es X'), usa `ficha_entidad` — agrega su nota, las menciones dispersas y lo relacionado — y redacta un retrato completo y natural.\n"
                "Si el usuario pide un resumen de su día, un diario o un repaso de lo que hizo: llama a `get_todays_activity`, y con esos datos redacta un resumen estructurado (temas, logros, ideas y conexiones con notas anteriores) que guardas con `create_note` titulada 'Diario AAAA-MM-DD' (fecha de hoy) enlazada al perfil. Confírmalo de forma cálida y cotidiana.\n"
                "Si pregunta qué temas tiene, en qué se repite, o quiere descubrir/organizar patrones en sus notas, usa `get_note_clusters` y preséntale los temas de forma natural.\n"
                "Si pide revisar, ordenar o limpiar su memoria: llama a `revisar_memoria`, cuéntale en lenguaje natural qué se reparó y qué encontraste, y para los posibles duplicados PREGUNTA antes de fusionar (si confirma que son la misma, junta el contenido en una nota con `write_note` y corrige los enlaces con `editar_nota`; si responde que son DISTINTAS, llama a `marcar_entidades_distintas` para no volver a preguntarlo). Si quiere dejar una nota sin conexiones, usa `ignorar_nota_suelta`.\n"
                # Redondeado a la hora (no al minuto): el system prompt se mantiene
                # idéntico durante la sesión y aprovecha el caching implícito de
                # Gemini 2.5 (activado por defecto; solo cachea si el inicio de la
                # petición es exactamente igual entre llamadas).
                f"Fecha y hora actuales (aprox.): {datetime.now().strftime('%Y-%m-%d %H:00')}. Para recordatorios con hora usa `crear_recordatorio` con `fecha_hora` 'YYYY-MM-DD HH:MM' (o `en_minutos`); usa `listar_recordatorios` para consultarlos.\n"
                "Si necesitas llamar a una función/herramienta, hazlo directamente sin generar texto explicativo en ese turno. Genera tu respuesta de texto únicamente cuando ya tengas todos los resultados de las herramientas.\n"
                f"En el contenido de los archivos creados/editados (NUNCA en tu respuesta), debes enlazar obligatoriamente al perfil usando la sintaxis `[[{settings.user_profile}]]` y, a su vez, enlazar desde la nota de perfil `{settings.user_profile}` a la nueva nota temática usando `[[Nombre Nota]]` (enlace bidireccional obligatorio con corchetes dobles).\n"
                + _graph_rules(settings.user_profile) +
                "Genera etiquetas (tags) sin '#' al crear/editar notas, combinando: (1) TEMAS (ej: profesional, tareas, ia, estudios) y (2) ENTIDADES concretas mencionadas con prefijo jerárquico — personas como `persona/Nombre`, proyectos como `proyecto/Nombre`, lugares como `lugar/Sitio`. Sin espacios ni acentos raros; usa solo las entidades realmente relevantes de la nota. Añade además (3) la ESFERA de la nota cuando sea clara: `contexto/trabajo` o `contexto/personal` (si es ambigua, omítela).\n"
                "Si la pregunta del usuario pertenece claramente a una esfera (su empresa/tareas → trabajo; amigos/casa/hobbies → personal), pasa `contexto='trabajo'` o `contexto='personal'` a `search_notes_semantic` para no mezclar mundos.\n"
                "Tienes acceso al portapapeles con `get_clipboard_content` y `set_clipboard_content`. Úsalos cuando te pidan leer/guardar info copiada o guardar resúmenes en el portapapeles.\n"
                "Si te piden abrir una aplicación, invoca 'open_application'.\n"
                "Al finalizar, da una confirmación natural y humana de una sola línea."
            )

            config = types.GenerateContentConfig(
                tools=tools_list,
                temperature=0.1,  # Muy baja para asegurar precisión
                system_instruction=system_instruction
            )

            import os
            parts = [types.Part.from_text(text=self.prompt)]
            if self.image_path and os.path.exists(self.image_path):
                try:
                    with open(self.image_path, "rb") as f:
                        img_bytes = f.read()
                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    print(f"[GeminiWorker] Contexto visual (imagen {self.image_path}) adjuntado correctamente.")
                except Exception as e:
                    print(f"[GeminiWorker] Error al cargar la imagen: {e}")
            contents = list(self.history) + [types.Content(role="user", parts=parts)]

            total_prompt_tokens = 0
            total_candidate_tokens = 0
            total_total_tokens = 0

            max_turns = 5
            for turn in range(max_turns):
                print(f"[GeminiWorker - Action] Streaming (Turno {turn + 1}) con {self.model_name}...")
                response_stream = client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )

                function_calls = []
                turn_usage = None
                turn_text = ""

                for chunk in response_stream:
                    if self._cancelled:
                        return  # turno cancelado por el usuario: sin más tokens ni herramientas
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        turn_usage = chunk.usage_metadata

                    if chunk.function_calls:
                        for call in chunk.function_calls:
                            function_calls.append(call)
                            self.tool_call_detected.emit(call.name, dict(call.args))

                    try:
                        if chunk.text:
                            turn_text += chunk.text
                            self.token_received.emit(chunk.text)
                    except Exception:
                        pass

                if self._cancelled:
                    return  # cancelado: no ejecutar herramientas pendientes

                if turn_usage:
                    total_prompt_tokens += getattr(turn_usage, 'prompt_token_count', 0) or 0
                    total_candidate_tokens += getattr(turn_usage, 'candidates_token_count', 0) or 0
                    total_total_tokens += getattr(turn_usage, 'total_token_count', 0) or 0

                if not function_calls:
                    if turn_text:
                        contents.append(types.Content(
                            role="model", parts=[types.Part.from_text(text=turn_text)]))
                    break

                model_parts = []
                if turn_text:
                    model_parts.append(types.Part.from_text(text=turn_text))
                tool_parts = []

                for call in function_calls:
                    model_parts.append(types.Part.from_function_call(name=call.name, args=dict(call.args)))
                    result = ""
                    if call.name in TOOL_MAP:
                        try:
                            result = TOOL_MAP[call.name](**call.args)
                        except Exception as e:
                            result = f"Error al ejecutar localmente {call.name}: {str(e)}"
                    else:
                        result = f"Error: La función {call.name} no existe."

                    self.tool_call_completed.emit(call.name, str(result))
                    tool_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))

                contents.append(types.Content(role="model", parts=model_parts))
                contents.append(types.Content(role="tool", parts=tool_parts))

            self.result_contents = contents
            self.tokens_consumed.emit(total_prompt_tokens, total_candidate_tokens, total_total_tokens)

        except Exception as e:
            self.error_occurred.emit(str(e))


class GeminiReasoningWorker(QThread):
    """
    Trabajador asíncrono (Agente de Razonamiento Profundo) en QThread que maneja el modelo Gemini Pro.
    Optimizado para responder preguntas complejas, formular planes de hobbies, rutinas y aconsejar
    al usuario sobre decisiones personales o profesionales leyendo y actualizando Obsidian de forma autónoma.
    """
    token_received = pyqtSignal(str)
    tool_call_detected = pyqtSignal(str, dict)
    tool_call_completed = pyqtSignal(str, str)
    tokens_consumed = pyqtSignal(int, int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt: str, image_path: str = None, history: list = None):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path
        self.history = history or []          # turnos previos (memoria conversacional)
        self.result_contents = []             # conversación actualizada tras este turno
        self._cancelled = False               # cancelación cooperativa (ver cancel())
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model_reasoning

    def cancel(self):
        """Pide cancelar el turno en curso; el bucle de streaming lo respeta."""
        self._cancelled = True

    def run(self):
        if not self.api_key:
            self.error_occurred.emit("Error: La clave GEMINI_API_KEY no está configurada.")
            return

        try:
            # Timeout duro por petición (evita que la UI quede en "Pensando…" para
            # siempre si la conexión se cuelga) + 1 reintento ante errores
            # transitorios (408/429/5xx) con backoff.
            client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=120_000,  # ms
                    retry_options=types.HttpRetryOptions(attempts=2, initial_delay=1.0),
                ),
            )
            tools_list = [
                open_application, create_note, read_note, search_notes, search_notes_semantic,
                get_todays_activity, get_note_clusters, revisar_memoria,
                marcar_entidades_distintas, ignorar_nota_suelta,
                ficha_entidad, write_note, append_to_note, editar_nota,
                get_clipboard_content, set_clipboard_content,
                crear_recordatorio, listar_recordatorios,
            ]

            system_instruction = (
                f"Eres LIA, asistente virtual y mentor personal de {settings.user_name} (perfil: `{settings.user_profile}`).\n"
                "Objetivo: consejos valiosos en temas de proyectos de IA, productividad profesional, estudios, toma de decisiones y desarrollo personal. Sé empática, natural y humana.\n"
                "Habla siempre al usuario en segunda persona (tú). Habla de forma cercana y amigable.\n"
                "REGLA DE ORO: Nunca menciones Obsidian, archivos .md, notas, búsquedas, herramientas ni origen de datos en tus respuestas al usuario. Tampoco uses corchetes `[[Nota]]` en ellas. Integra la info de manera invisible como si la recordaras tú misma.\n"
                f"Asocia la información en primera persona expresada por el usuario al perfil de {settings.user_name} y regístrala en su perfil (no crees notas 'Yo' o paralelas).\n"
                "Antes de guardar, busca notas con `search_notes`. Si existen, actualízalas con `write_note` o `append_to_note` para evitar duplicados.\n"
                "Para cambiar un dato puntual de una nota existente (una fecha, un nombre, una línea), usa `editar_nota(title, buscar, reemplazar)` con el fragmento exacto, en lugar de reescribir toda la nota. Si no sabes el texto exacto, léela antes con `read_note`.\n"
                "Siempre que te pregunten sobre algún proyecto, concepto, tarea o información del usuario, busca en su memoria antes de responder: usa `search_notes_semantic` para preguntas abiertas o conceptuales (temas, ideas, 'qué sé sobre...'), `search_notes` para palabras o títulos exactos, y `read_note` si conoces el nombre de la nota.\n"
                "Si pregunta por una entidad concreta (una persona, empresa, proyecto o lugar: 'cuéntame sobre X', 'qué sabes de X', 'quién es X'), usa `ficha_entidad` — agrega su nota, las menciones dispersas y lo relacionado — y redacta un retrato completo y natural.\n"
                "Si el usuario pide un resumen de su día, un diario o un repaso: llama a `get_todays_activity` y, con esos datos, redacta un resumen estructurado y reflexivo (temas, logros, ideas y conexiones con notas anteriores) que guardas con `create_note` titulada 'Diario AAAA-MM-DD' (fecha de hoy) enlazada al perfil. Confírmalo de forma cálida.\n"
                "Si pregunta qué temas tiene, en qué se repite, o quiere descubrir/organizar patrones en sus notas, usa `get_note_clusters` y preséntale los temas con una breve reflexión.\n"
                "Si pide revisar, ordenar o limpiar su memoria: llama a `revisar_memoria`, cuéntale qué se reparó y qué encontraste, y para los posibles duplicados PREGUNTA antes de fusionar (si confirma que son la misma, junta el contenido en una nota con `write_note` y corrige los enlaces con `editar_nota`; si responde que son DISTINTAS, llama a `marcar_entidades_distintas` para no volver a preguntarlo). Si quiere dejar una nota sin conexiones, usa `ignorar_nota_suelta`.\n"
                # Redondeado a la hora (no al minuto): el system prompt se mantiene
                # idéntico durante la sesión y aprovecha el caching implícito de
                # Gemini 2.5 (activado por defecto; solo cachea si el inicio de la
                # petición es exactamente igual entre llamadas).
                f"Fecha y hora actuales (aprox.): {datetime.now().strftime('%Y-%m-%d %H:00')}. Para recordatorios con hora usa `crear_recordatorio` con `fecha_hora` 'YYYY-MM-DD HH:MM' (o `en_minutos`); usa `listar_recordatorios` para consultarlos.\n"
                "Si necesitas llamar a una función/herramienta, hazlo directamente sin generar texto explicativo en ese turno. Genera tu respuesta de texto únicamente cuando ya tengas todos los resultados de las herramientas.\n"
                f"En el contenido de los archivos creados/editados (NUNCA en tu respuesta), debes enlazar obligatoriamente al perfil usando la sintaxis `[[{settings.user_profile}]]` y, a su vez, enlazar desde la nota de perfil `{settings.user_profile}` a la nueva nota temática usando `[[Nombre Nota]]` (enlace bidireccional obligatorio con corchetes dobles).\n"
                + _graph_rules(settings.user_profile) +
                "Genera etiquetas (tags) sin '#' al crear/editar notas, combinando: (1) TEMAS (ej: profesional, tareas, ia, estudios) y (2) ENTIDADES concretas mencionadas con prefijo jerárquico — personas como `persona/Nombre`, proyectos como `proyecto/Nombre`, lugares como `lugar/Sitio`. Sin espacios ni acentos raros; usa solo las entidades realmente relevantes de la nota. Añade además (3) la ESFERA de la nota cuando sea clara: `contexto/trabajo` o `contexto/personal` (si es ambigua, omítela).\n"
                "Si la pregunta del usuario pertenece claramente a una esfera (su empresa/tareas → trabajo; amigos/casa/hobbies → personal), pasa `contexto='trabajo'` o `contexto='personal'` a `search_notes_semantic` para no mezclar mundos.\n"
                "Tienes acceso al portapapeles con `get_clipboard_content` y `set_clipboard_content`. Úsalos cuando sea relevante para capturar o guardar información.\n"
                f"Si diseñas rutinas/planes/proyectos, guárdalos con `write_note` y enlázalos a `[[{settings.user_profile}]]` de forma invisible. Confírmalo en lenguaje cotidiano y cercano."
            )

            config = types.GenerateContentConfig(
                tools=tools_list,
                temperature=0.3,  # Ligeramente mayor para creatividad en consejos
                system_instruction=system_instruction
            )

            import os
            parts = [types.Part.from_text(text=self.prompt)]
            if self.image_path and os.path.exists(self.image_path):
                try:
                    with open(self.image_path, "rb") as f:
                        img_bytes = f.read()
                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    print(f"[GeminiReasoningWorker] Contexto visual (imagen {self.image_path}) adjuntado correctamente.")
                except Exception as e:
                    print(f"[GeminiReasoningWorker] Error al cargar la imagen: {e}")
            contents = list(self.history) + [types.Content(role="user", parts=parts)]

            total_prompt_tokens = 0
            total_candidate_tokens = 0
            total_total_tokens = 0

            max_turns = 5
            for turn in range(max_turns):
                print(f"[GeminiWorker - Reasoning] Streaming (Turno {turn + 1}) con {self.model_name}...")
                response_stream = client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )

                function_calls = []
                turn_usage = None
                turn_text = ""

                for chunk in response_stream:
                    if self._cancelled:
                        return  # turno cancelado por el usuario: sin más tokens ni herramientas
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        turn_usage = chunk.usage_metadata

                    if chunk.function_calls:
                        for call in chunk.function_calls:
                            function_calls.append(call)
                            self.tool_call_detected.emit(call.name, dict(call.args))

                    try:
                        if chunk.text:
                            turn_text += chunk.text
                            self.token_received.emit(chunk.text)
                    except Exception:
                        pass

                if self._cancelled:
                    return  # cancelado: no ejecutar herramientas pendientes

                if turn_usage:
                    total_prompt_tokens += getattr(turn_usage, 'prompt_token_count', 0) or 0
                    total_candidate_tokens += getattr(turn_usage, 'candidates_token_count', 0) or 0
                    total_total_tokens += getattr(turn_usage, 'total_token_count', 0) or 0

                if not function_calls:
                    if turn_text:
                        contents.append(types.Content(
                            role="model", parts=[types.Part.from_text(text=turn_text)]))
                    break

                model_parts = []
                if turn_text:
                    model_parts.append(types.Part.from_text(text=turn_text))
                tool_parts = []

                for call in function_calls:
                    model_parts.append(types.Part.from_function_call(name=call.name, args=dict(call.args)))
                    result = ""
                    if call.name in TOOL_MAP:
                        try:
                            result = TOOL_MAP[call.name](**call.args)
                        except Exception as e:
                            result = f"Error al ejecutar localmente {call.name}: {str(e)}"
                    else:
                        result = f"Error: La función {call.name} no existe."

                    self.tool_call_completed.emit(call.name, str(result))
                    tool_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))

                contents.append(types.Content(role="model", parts=model_parts))
                contents.append(types.Content(role="tool", parts=tool_parts))

            self.result_contents = contents
            self.tokens_consumed.emit(total_prompt_tokens, total_candidate_tokens, total_total_tokens)

        except Exception as e:
            self.error_occurred.emit(str(e))
