import os
import re
import asyncio
from PyQt6.QtCore import QObject, QThread, pyqtSignal
import edge_tts
from config import settings
from config.paths import runtime_file

class TTSWorker(QThread):
    """
    Trabajador en hilo secundario (QThread) para descargar y guardar
    la síntesis de voz de edge-tts de forma asíncrona y no bloqueante.
    """
    finished = pyqtSignal(str)  # Emite la ruta absoluta del archivo guardado
    error = pyqtSignal(str)     # Emite un mensaje de error si ocurre un fallo

    def __init__(self, text: str, output_path: str):
        super().__init__()
        self.text = text
        self.output_path = output_path
        # Recuperar la voz configurada desde settings (por defecto es-ES-ElviraNeural)
        self.voice = getattr(settings, "tts_voice", "es-ES-ElviraNeural")

    def run(self):
        try:
            # Crear y ejecutar la corrutina de edge-tts dentro del bucle de eventos de asyncio
            communicate = edge_tts.Communicate(self.text, self.voice)
            asyncio.run(communicate.save(self.output_path))
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


class TTSService(QObject):
    """
    Servicio de Respuestas de Voz Activas (TTS) de LIA.
    Gestiona la obtención asíncrona de archivos de voz usando edge-tts y emite
    señales cuando el audio está listo para ser reproducido por el cliente.
    """
    speech_ready = pyqtSignal(str)     # Señal que indica que el MP3 está listo
    error_occurred = pyqtSignal(str)   # Señal en caso de error de obtención

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.enabled = settings.tts_enabled
        self.worker = None
        # Definir la ruta del archivo MP3 temporal en el directorio raíz del proyecto
        self.output_path = runtime_file("temp_response.mp3")

    def set_enabled(self, enabled: bool):
        """Activa o desactiva dinámicamente el servicio de voz."""
        self.enabled = enabled
        if not enabled:
            self.stop()

    def speak(self, text: str):
        """Sanitiza el texto e inicia el hilo secundario para descargar el audio."""
        if not self.enabled or not text:
            return
        
        # Detener cualquier descarga o hilo anterior
        self.stop()
        
        # Limpiar markdown, HTML y metadatos del texto
        cleaned_text = self.sanitize_text_for_speech(text)
        if not cleaned_text:
            return
            
        print(f"[TTSService] Solicitando síntesis de voz edge-tts para: \"{cleaned_text}\"")
        self.worker = TTSWorker(cleaned_text, self.output_path)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def stop(self):
        """Cancela inmediatamente el hilo de descarga si está activo."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        self.worker = None

    def _on_worker_finished(self, path: str):
        self.speech_ready.emit(path)

    def _on_worker_error(self, err_msg: str):
        print(f"[TTSService] Error en síntesis de voz: {err_msg}")
        self.error_occurred.emit(err_msg)

    @staticmethod
    def sanitize_text_for_speech(text: str) -> str:
        """
        Limpia markdown, etiquetas HTML, referencias a archivos y bloques de código.
        """
        if not text:
            return ""
            
        # 1. Eliminar bloques de código markdown: ```código```
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
        # 2. Eliminar código en línea: `código`
        text = re.sub(r'`[^`]+`', '', text)
        
        # 3. Eliminar etiquetas HTML como <br/> o <span>
        text = re.sub(r'<[^>]+>', '', text)
        
        # 4. Resolver enlaces bidireccionales Obsidian: [[Nota]] -> Nota
        text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
        
        # 5. Eliminar asteriscos y guiones bajos de énfasis: **, *, __, _
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # 6. Eliminar viñetas de lista al inicio de línea
        text = re.sub(r'^[ \t]*[-*+]\s+', '', text, flags=re.MULTILINE)
        
        # 7. Eliminar títulos markdown (headers) al inicio de línea: # Título
        text = re.sub(r'^[ \t]*#+\s+', '', text, flags=re.MULTILINE)
        
        # 8. Limpiar bloques informativos/metadatos entre corchetes rectangulares del sistema
        text = re.sub(r'\[Tokens usados.*?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Ejecutando comando.*?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Sistema:.*?\]', '', text, flags=re.IGNORECASE)
        
        # 9. Reemplazar saltos de línea por puntos para forzar pausas del sintetizador
        text = re.sub(r'\n+', '. ', text)
        
        # 10. Eliminar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        text = text.strip()
        # 11. Eliminar posibles puntos, comas o espacios al inicio del texto
        text = re.sub(r'^[. ,\s]+', '', text)
        
        return text.strip()
