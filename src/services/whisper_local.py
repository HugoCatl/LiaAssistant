import os
from PyQt6.QtCore import QThread, pyqtSignal
from faster_whisper import WhisperModel
from config import settings

# Global singleton to cache model weights in memory
_cached_whisper_model = None

def get_whisper_model(model_size: str) -> WhisperModel:
    """
    Lazily instantiates and caches the Whisper model in memory.
    Enforces CPU execution with INT8 quantization to avoid CUDA DLL loading errors
    and ensure stable, fast transcription across all systems.
    """
    global _cached_whisper_model
    if _cached_whisper_model is None:
        try:
            device = "cpu"
            compute_type = "int8"
            print(f"[WhisperLocal] Cargando modelo Whisper '{model_size}' en CPU (int8)...")
            _cached_whisper_model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=4
            )
            print("[WhisperLocal] Modelo Whisper cargado con éxito en CPU (int8).")
        except Exception as e:
            print(f"[WhisperLocal] Error cargando el modelo Whisper en CPU: {e}")
            raise e
    return _cached_whisper_model


class TranscriptionWorker(QThread):
    """
    Background QThread worker for transcribing a WAV file.
    Emits transcription_completed with the transcribed text.
    """
    transcription_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, audio_path: str):
        super().__init__()
        self.audio_path = audio_path
        self.model_size = settings.whisper_model_path

    def run(self):
        if not os.path.exists(self.audio_path):
            self.error_occurred.emit(f"Error: Archivo de audio no encontrado en {self.audio_path}")
            return

        try:
            # Load (or get cached) model
            model = get_whisper_model(self.model_size)

            print(f"[TranscriptionWorker] Transcribiendo {self.audio_path}...")
            # Transcribe audio file (forcing language="es" or letting it auto-detect)
            segments, info = model.transcribe(
                self.audio_path,
                beam_size=3,
                language="es"  # Standard spanish input
            )

            # Reconstruct transcription text from segments
            text_parts = [segment.text for segment in segments]
            transcription = "".join(text_parts).strip()

            print(f"[TranscriptionWorker] Transcripción completada: \"{transcription}\"")
            self.transcription_completed.emit(transcription)

        except Exception as e:
            print(f"[TranscriptionWorker] Error durante transcripción: {e}")
            self.error_occurred.emit(str(e))
