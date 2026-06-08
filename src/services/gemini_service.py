from PyQt6.QtCore import QThread, pyqtSignal
from google import genai
from google.genai import types
from config import settings
from src.services.os_automation import open_application

class GeminiWorker(QThread):
    """
    Asynchronous QThread worker that handles streaming requests to the Gemini API.
    Integrates system automation functions as Gemini Tools.
    Emits signals for token chunks and detected tool calls.
    """
    token_received = pyqtSignal(str)
    tool_call_detected = pyqtSignal(str, dict)
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
            # Initialize the modern google-genai Client
            client = genai.Client(api_key=self.api_key)

            # Register open_application function directly as a tool
            # The SDK automatically uses type hints and docstrings to build the JSON schema
            config = types.GenerateContentConfig(
                tools=[open_application],
                temperature=0.2,  # Low temperature for reliable logical routing
                system_instruction=(
                    "Eres LIA Assistant, un asistente virtual de escritorio para Windows.\n"
                    "Si el usuario te pide abrir una aplicación (como bloc de notas, calculadora, chrome, etc.), "
                    "debes invocar la herramienta 'open_application' proporcionando el nombre de la aplicación. "
                    "No des explicaciones adicionales a menos que falle la herramienta o que el usuario haga preguntas generales."
                )
            )

            print(f"[GeminiWorker] Iniciando streaming con {self.model_name}...")
            response_stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=self.prompt,
                config=config
            )

            for chunk in response_stream:
                # 1. Parse function calls if present in the chunk
                if chunk.function_calls:
                    for call in chunk.function_calls:
                        print(f"[GeminiWorker] Llamada a función detectada: {call.name} con argumentos: {call.args}")
                        self.tool_call_detected.emit(call.name, dict(call.args))

                # 2. Parse text content if present in the chunk
                try:
                    if chunk.text:
                        self.token_received.emit(chunk.text)
                except Exception:
                    # Safely skip if chunk does not contain accessible text
                    pass

        except Exception as e:
            print(f"[GeminiWorker] Error en el flujo de la API de Gemini: {e}")
            self.error_occurred.emit(str(e))
