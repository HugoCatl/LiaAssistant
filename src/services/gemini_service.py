from PyQt6.QtCore import QThread, pyqtSignal
from google import genai
from google.genai import types
from config import settings
from src.services.os_automation import open_application
from src.storage.obsidian_manager import create_note, read_note, search_notes, write_note, append_to_note

# Map tool names to python functions for execution inside workers
TOOL_MAP = {
    "open_application": open_application,
    "create_note": create_note,
    "read_note": read_note,
    "search_notes": search_notes,
    "write_note": write_note,
    "append_to_note": append_to_note
}

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

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model

    def run(self):
        if not self.api_key:
            self.error_occurred.emit("Error: La clave GEMINI_API_KEY no está configurada.")
            return

        try:
            client = genai.Client(api_key=self.api_key)
            tools_list = [open_application, create_note, read_note, search_notes, write_note, append_to_note]
            
            system_instruction = (
                "Eres LIA Assistant, el Agente de Acción Rápida para Windows.\n"
                "Tu objetivo es velocidad pura, ejecución precisa y gestión de memoria directa. Sé breve y directo, pero proporciona siempre una respuesta corta de confirmación de lo realizado al usuario (nunca respondas con texto vacío o en blanco).\n"
                "Tienes acceso a la memoria local en la bóveda de Obsidian del usuario en C:\\LIAI.\n"
                "Si te piden abrir una aplicación, invoca 'open_application'.\n"
                "\n"
                "CRÍTICO - IDENTIDAD DEL USUARIO Y PRIMERA PERSONA:\n"
                "- El usuario con el que estás interactuando es Hugo Catalán. Él tiene 20 años y su nota de perfil principal es `Hugo Catalán`.\n"
                "- Cuando el usuario hable en primera persona (ej. 'yo', 'vivo en...', 'mi correo...', 'mi perro...'), debes razonar que se refiere siempre a **Hugo Catalán**.\n"
                "- Toda la información personal del usuario expresada en primera persona debe ser guardada, actualizada o integrada directamente en la nota `Hugo Catalán` (usando `write_note` o `append_to_note`), en lugar de crear notas paralelas o separadas.\n"
                "- Ejemplo: si el usuario dice 'vivo en Viver', debes deducir que Hugo Catalán reside en Viver y actualizar su nota `Hugo Catalán` añadiendo '- **Residencia:** Viver' (o actualizando la línea si ya existía), sin crear una nota independiente llamada Viver ni Yo.\n"
                "\n"
                "CRÍTICO - EVITAR DUPLICADOS Y RELACIONAR EN OBSIDIAN:\n"
                "1. Antes de crear o guardar cualquier información o responder a algo personal, siempre debes buscar notas relacionadas usando la herramienta `search_notes`.\n"
                "2. Si encuentras que ya existe una nota sobre el mismo tema o con un nombre similar, NO intentes crear una nota duplicada. Si llamas a `create_note` y ya existe un archivo con ese nombre (o similar), fallará con un error. En su lugar, debes actualizarla utilizando `write_note` (para reescribir o corregir completamente) o `append_to_note` (para adjuntar información al final).\n"
                "3. Para relacionar notas entre sí y que aparezcan conectadas en el gráfico de Obsidian, debes utilizar de forma obligatoria la sintaxis de doble corchete `[[Nombre de la Nota]]` en el contenido. Esto debe ser BIDIRECCIONAL: cuando crees o actualices una nota sobre un tema (ej. Hobbies), debes incluir `[[Hugo Catalán]]` en su contenido; y a su vez, debes actualizar la nota principal de `[[Hugo Catalán]]` (usando `append_to_note` o `write_note`) para añadir un enlace a la nueva nota (ej: `[[Hobbies]]` o `[[Amigos del Gimnasio]]`). Esto garantiza que el gráfico de Obsidian quede perfectamente enlazado.\n"
                "4. Generación de etiquetas (tags): Al crear o actualizar notas, genera etiquetas lógicas que describan el tema (por ejemplo: `personal`, `tareas`, `credenciales`, `salud`) y pásalas en el parámetro `tags` sin el símbolo '#'.\n"
                "5. Segmentación inteligente de temas: Si el usuario te habla de múltiples temas distintos en un mismo mensaje, debes separar la información de forma estructurada. Crea o actualiza notas individuales para cada tema independiente, vinculándolas entre sí mediante la sintaxis `[[Nota]]`.\n"
                "6. Síntesis limpia: Organiza el contenido dentro de las notas utilizando Markdown bien estructurado (viñetas, títulos con '#', textos en negrita) para que sea sumamente limpio y legible.\n"
                "\n"
                "Confirmación corta: Al terminar de ejecutar tus herramientas, responde siempre confirmando al usuario con un resumen ultra corto de 1 línea de lo guardado (ej. 'He guardado tu hobby de ir al gimnasio en [[Hobbies]] y lo he enlazado a tu perfil.')."
            )

            config = types.GenerateContentConfig(
                tools=tools_list,
                temperature=0.1,  # Muy baja para asegurar precisión
                system_instruction=system_instruction
            )

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=self.prompt)])]

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

                for chunk in response_stream:
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        turn_usage = chunk.usage_metadata

                    if chunk.function_calls:
                        for call in chunk.function_calls:
                            function_calls.append(call)
                            self.tool_call_detected.emit(call.name, dict(call.args))

                    try:
                        if chunk.text:
                            self.token_received.emit(chunk.text)
                    except Exception:
                        pass

                if turn_usage:
                    total_prompt_tokens += getattr(turn_usage, 'prompt_token_count', 0) or 0
                    total_candidate_tokens += getattr(turn_usage, 'candidates_token_count', 0) or 0
                    total_total_tokens += getattr(turn_usage, 'total_token_count', 0) or 0

                if not function_calls:
                    break

                model_parts = []
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

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model_reasoning

    def run(self):
        if not self.api_key:
            self.error_occurred.emit("Error: La clave GEMINI_API_KEY no está configurada.")
            return

        try:
            client = genai.Client(api_key=self.api_key)
            tools_list = [open_application, create_note, read_note, search_notes, write_note, append_to_note]
            
            system_instruction = (
                "Eres LIA Assistant, el Agente de Razonamiento Profundo y Mentor Personal del usuario en Windows.\n"
                "Tu objetivo es dar consejos altamente valiosos, analíticos y bien justificados sobre temas laborales, "
                "personales, toma de decisiones y recomendaciones de hobbies, deporte o estudio.\n"
                "Tienes acceso a la memoria local en la bóveda de Obsidian del usuario en C:\\LIAI.\n"
                "\n"
                "CRÍTICO - IDENTIDAD DEL USUARIO Y PRIMERA PERSONA:\n"
                "- El usuario con el que estás interactuando es Hugo Catalán. Él tiene 20 años y su nota de perfil principal es `Hugo Catalán`.\n"
                "- Cuando el usuario hable en primera persona (ej. 'yo', 'vivo en...', 'mi correo...', 'mi perro...'), debes razonar que se refiere siempre a **Hugo Catalán**.\n"
                "- Toda la información personal del usuario expresada en primera persona debe ser guardada, actualizada o integrada directamente en la nota `Hugo Catalán` (usando `write_note` o `append_to_note`), en lugar de crear notas paralelas o separadas.\n"
                "- Ejemplo: si el usuario dice 'vivo en Viver', debes deducir que Hugo Catalán reside en Viver y actualizar su nota `Hugo Catalán` añadiendo '- **Residencia:** Viver' (o actualizando la línea si ya existía), sin crear una nota independiente llamada Viver ni Yo.\n"
                "\n"
                "CRÍTICO - EVITAR DUPLICADOS Y RELACIONAR EN OBSIDIAN:\n"
                "1. Antes de crear o guardar cualquier información o responder a algo personal, siempre debes buscar notas relacionadas usando la herramienta `search_notes`.\n"
                "2. Si encuentras que ya existe una nota sobre el mismo tema o con un nombre similar, NO intentes crear una nota duplicada. Si llamas a `create_note` and ya existe un archivo con ese nombre (o similar), fallará con un error. En su lugar, debes actualizarla utilizando `write_note` (para reescribir o corregir completamente) o `append_to_note` (para adjuntar información al final).\n"
                "3. Para relacionar notas entre sí y que aparezcan conectadas en el gráfico de Obsidian, debes utilizar de forma obligatoria la sintaxis de doble corchete `[[Nombre de la Nota]]` en el contenido. Esto debe ser BIDIRECCIONAL: cuando crees o actualices una nota sobre un tema (ej. Hobbies), debes incluir `[[Hugo Catalán]]` en su contenido; y a su vez, debes actualizar la nota principal de `[[Hugo Catalán]]` (usando `append_to_note` o `write_note`) para añadir un enlace a la nueva nota (ej: `[[Hobbies]]` o `[[Amigos del Gimnasio]]`). Esto garantiza que el gráfico de Obsidian quede perfectamente enlazado.\n"
                "4. Generación de etiquetas (tags): Al crear o actualizar notas, genera etiquetas lógicas que describan el tema (por ejemplo: `personal`, `tareas`, `credenciales`, `salud`) y pásalas en el parámetro `tags` sin el símbolo '#'.\n"
                "5. Segmentación inteligente de temas: Si el usuario te habla de múltiples temas distintos en un mismo mensaje, debes separar la información de forma estructurada. Crea o actualiza notas individuales para cada tema independiente, vinculándolas entre sí mediante la sintaxis `[[Nota]]`. Puedes realizar múltiples llamadas a herramientas consecutivas en la misma respuesta si es necesario para segmentar los temas.\n"
                "6. Síntesis limpia: Organiza el contenido dentro de las notas utilizando Markdown bien estructurado (viñetas, títulos con '#', textos en negrita) para que sea sumamente limpio y legible.\n"
                "\n"
                "APLICACIÓN PRÁCTICA: Si el usuario te pide, por ejemplo, diseñar una rutina de gimnasio o un plan detallado, "
                "debes buscar en sus notas si hay antecedentes, redactar una rutina de altísima calidad adaptada a sus 20 años y "
                "guardarla de manera autónoma en Obsidian llamando a `write_note` (ej. creando `Rutina de Gimnasio.md` con enlaces internos `[[Hugo Catalán]]`). "
                "Luego, infórmale del diseño y de que la nota ya está guardada en su bóveda, asegurándote de actualizar la nota de `[[Hugo Catalán]]` para enlazarla."
            )

            config = types.GenerateContentConfig(
                tools=tools_list,
                temperature=0.3,  # Ligeramente mayor para creatividad en consejos
                system_instruction=system_instruction
            )

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=self.prompt)])]

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

                for chunk in response_stream:
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        turn_usage = chunk.usage_metadata

                    if chunk.function_calls:
                        for call in chunk.function_calls:
                            function_calls.append(call)
                            self.tool_call_detected.emit(call.name, dict(call.args))

                    try:
                        if chunk.text:
                            self.token_received.emit(chunk.text)
                    except Exception:
                        pass

                if turn_usage:
                    total_prompt_tokens += getattr(turn_usage, 'prompt_token_count', 0) or 0
                    total_candidate_tokens += getattr(turn_usage, 'candidates_token_count', 0) or 0
                    total_total_tokens += getattr(turn_usage, 'total_token_count', 0) or 0

                if not function_calls:
                    break

                model_parts = []
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

            self.tokens_consumed.emit(total_prompt_tokens, total_candidate_tokens, total_total_tokens)

        except Exception as e:
            self.error_occurred.emit(str(e))
