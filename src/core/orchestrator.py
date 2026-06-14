import os
import sounddevice as sd
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.core.state_manager import StateManager, AssistantState
from src.gui.view import View
from src.services.gemini_service import GeminiWorker, GeminiReasoningWorker
from src.services.os_automation import open_application
from src.io.audio_recorder import AudioRecorder
from src.services.whisper_local import TranscriptionWorker
from src.services.tts_service import TTSService

class Orchestrator(QObject):
    """
    Mediator coordinating UI events, global keyboard shortcut triggers,
    state transitions, hardware audio recording, local Whisper STT,
    and background asynchronous Gemini API execution.
    """
    def __init__(self, view: View, state_manager: StateManager, keyboard_listener):
        super().__init__()
        self.view = view
        self.state_manager = state_manager
        self.keyboard_listener = keyboard_listener
        self.worker = None
        self.current_response_text = ""

        # Setup QMediaPlayer for TTS responses
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Connect speech ready signal to playback handler
        TTSService.get_instance().speech_ready.connect(self.play_speech_audio)

        # Hardware Perception components
        self.audio_recorder = AudioRecorder()
        self.transcription_worker = None

        # Retrieve default microphone index
        try:
            self.active_mic_id = sd.default.device[0]  # Standard input device index
        except Exception:
            self.active_mic_id = None
            print("[Orchestrator] Advertencia: No se detectó ningún micrófono por defecto.")

        # Setup GUI & keyboard signaling pipelines
        self.keyboard_listener.hotkey_triggered.connect(self.toggle_ui)
        self.state_manager.state_changed.connect(self.on_state_changed)
        self.view.input_field.returnPressed.connect(self.handle_input_submission)

        # Wire settings config wheel and microphone recording buttons
        self.view.config_button.clicked.connect(self.show_config_menu)
        self.view.mic_button.clicked.connect(self.toggle_recording)

        # Wire audio recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped)
        self.audio_recorder.error_occurred.connect(self.on_audio_error)

    def show_welcome_greeting(self):
        """Muestra un saludo proactivo e inspirador en el display si está vacío, incitando a registrar ideas o tareas."""
        if not self.view.output_display.toPlainText().strip():
            import random
            greetings = [
                "¡Hola Hugo! ¿Qué idea se te ha ocurrido hoy? 💡",
                "Hola Hugo, ¿en qué tarea o proyecto profesional vamos a trabajar hoy? 🚀",
                "¡Buenas! Cuéntame, ¿qué hay de nuevo hoy en tus notas o estudios? 🧠",
                "Hola Hugo, ¿tienes alguna idea o nota profesional para enlazar hoy? ✨",
                "¡Hola! ¿Qué se te pasa por la cabeza hoy? Estoy lista para anotarlo todo. 📝"
            ]
            greeting = random.choice(greetings)
            self.view.output_display.setHtml(
                f"<span style='color: #A78BFA; font-weight: bold;'>LIA:</span> "
                f"<span style='color: #F1F5F9;'>{greeting}</span>"
            )

    def start(self):
        """Starts the background listening thread and displays startup greeting."""
        self.keyboard_listener.start()
        self.show_welcome_greeting()
        print("[Orchestrator] Sistema de LIA Assistant iniciado.")
        print("[Orchestrator] Presione 'Shift_L + L' globalmente para mostrar/ocultar el panel.")

    def toggle_ui(self):
        """Toggles the visibility of the frameless UI overlay window."""
        if self.view.isVisible():
            self.view.hide()
            self.state_manager.set_state(AssistantState.IDLE)
            print("[Orchestrator] Panel oculto. Estado: IDLE")
        else:
            self.view.show()
            self.view.raise_()
            self.view.activateWindow()
            self.view.input_field.setFocus()
            self.state_manager.set_state(AssistantState.LISTENING)
            self.show_welcome_greeting()
            print("[Orchestrator] Panel activado. Estado: LISTENING")

    def on_state_changed(self, state: AssistantState):
        """Maneja el comportamiento y la interfaz de usuario al cambiar de estado."""
        self.view.update_status_dot(state)

        # Bloquear o desbloquear controles según el estado actual
        if state in (AssistantState.PROCESSING, AssistantState.RESPONDING):
            self.view.input_field.setEnabled(False)
            self.view.mic_button.setEnabled(False)
        else:
            self.view.mic_button.setEnabled(True)
            # Deshabilitar entrada de texto solo si el grabador de audio está activo
            is_recording = self.audio_recorder.isRunning()
            self.view.input_field.setEnabled(not is_recording)
            
            if state == AssistantState.IDLE:
                self.view.input_field.setFocus()

    def detect_reasoning_intent(self, text: str) -> bool:
        """
        Analiza si el texto ingresado por el usuario requiere el modelo Pro de razonamiento profundo
        (petición explícita de análisis a fondo, mentoría, consejo o decisión compleja),
        de lo contrario se usa el modelo Flash por velocidad y ahorro de tokens.
        """
        keywords = [
            "analiza a fondo", "analiza en profundidad", "razonamiento profundo",
            "razona", "consejo complejo", "decisión compleja", "mentoría", "reflexiona sobre"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def handle_input_submission(self):
        """Handles user text submission and spawns the background Gemini worker."""
        # Stop any ongoing speech before starting a new transaction
        self.player.stop()
        TTSService.get_instance().stop()
        self.current_response_text = ""

        # Prevent starting a new request if one is already running
        if self.worker and self.worker.isRunning():
            print("[Orchestrator] Advertencia: Ya hay una consulta en proceso.")
            return

        user_text = self.view.input_field.text().strip()
        if not user_text:
            return

        # Clear input field
        self.view.input_field.clear()

        # Update display logs
        self.view.output_display.append(f"<span style='color: #C084FC; font-weight: bold;'>Tú:</span> <span style='color: #F1F5F9;'>{user_text}</span>")
        self.view.output_display.append("<span style='color: #A78BFA; font-weight: bold;'>LIA:</span> ")
        self.view.output_display.ensureCursorVisible()

        # Set UI state to processing
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Enrutar inteligentemente según la intención
        if self.detect_reasoning_intent(user_text):
            print(f"[Orchestrator] Enrutando '{user_text}' al Agente de Razonamiento (Gemini Pro)...")
            self.worker = GeminiReasoningWorker(user_text)
        else:
            print(f"[Orchestrator] Enrutando '{user_text}' al Agente de Acción Rápida (Gemini Flash)...")
            self.worker = GeminiWorker(user_text)
        
        # Connect signals
        self.worker.token_received.connect(self.on_token_received)
        self.worker.tool_call_detected.connect(self.on_tool_call_detected)
        self.worker.tool_call_completed.connect(self.on_tool_call_completed)
        self.worker.tokens_consumed.connect(self.on_tokens_consumed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.finished.connect(self.on_generation_finished)

        # Start background thread execution
        self.worker.start()

    def on_token_received(self, token: str):
        """Streams text tokens inline directly into the output display."""
        if self.state_manager.state == AssistantState.PROCESSING:
            self.state_manager.set_state(AssistantState.RESPONDING)

        self.current_response_text += token

        # Move text cursor to end and insert token inline (produces character-by-character animation)
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self.view.output_display.ensureCursorVisible()

    def on_tool_call_detected(self, name: str, args: dict):
        """Muestra en la interfaz visual que una herramienta está siendo ejecutada."""
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        prefix = "" if not self.view.output_display.toPlainText().strip() else "<br/>"
        
        info_msg = ""
        if name == "open_application":
            app_name = args.get("app_name", "")
            info_msg = f"Abrir {app_name}"
        elif name == "create_note":
            title = args.get("title", "")
            info_msg = f"Crear nota '{title}'"
        elif name == "read_note":
            title = args.get("title", "")
            info_msg = f"Leer nota '{title}'"
        elif name == "search_notes":
            query = args.get("query", "")
            info_msg = f"Buscar notas sobre '{query}'"
        elif name == "write_note":
            title = args.get("title", "")
            info_msg = f"Editar/Escribir nota '{title}'"
        elif name == "append_to_note":
            title = args.get("title", "")
            info_msg = f"Añadir a nota '{title}'"
        else:
            info_msg = f"Ejecutar {name}"
            
        cursor.insertHtml(f"{prefix}<span style='color: #C084FC;'><i>[Ejecutando comando: {info_msg}...]</i></span>")
        self.view.output_display.ensureCursorVisible()

    def on_tool_call_completed(self, name: str, result: str):
        """Muestra en la interfaz visual el resultado de la ejecución de la herramienta."""
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #00FF7F;'><i>[Sistema: {result}]</i></span>")
        self.view.output_display.ensureCursorVisible()

    def on_tokens_consumed(self, prompt_tokens: int, candidate_tokens: int, total_tokens: int):
        """Muestra en la interfaz el consumo de tokens de la interacción."""
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(
            f"<br/><span style='color: #6B7280; font-size: 11px; font-style: italic;'>"
            f"[Tokens usados - Entrada: {prompt_tokens} | Salida: {candidate_tokens} | Total: {total_tokens}]"
            f"</span><br/>"
        )
        self.view.output_display.ensureCursorVisible()

    def on_error_occurred(self, err_msg: str):
        """Displays errors on the output panel."""
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #F87171;'><b>Error:</b> {err_msg}</span><br/>")
        self.view.output_display.ensureCursorVisible()

    def on_generation_finished(self):
        """Restores the UI state to idle when the generation ends."""
        self.state_manager.set_state(AssistantState.IDLE)

        # Trigger text to speech on the generated text
        if self.current_response_text:
            TTSService.get_instance().speak(self.current_response_text)

        # Safely mark QThread for garbage collection
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    # --- Hardware Audio & STT Handlers ---

    def toggle_recording(self):
        """Starts or stops hardware recording based on current worker state."""
        # Ignore mic interaction if we are currently waiting for LLM responses
        if self.worker and self.worker.isRunning():
            return

        if self.audio_recorder.isRunning():
            # Stop the audio recorder (this triggers recording_stopped)
            self.audio_recorder.stop_recording()
        else:
            # Pass selected device index and start recording
            self.audio_recorder.set_device(self.active_mic_id)
            self.audio_recorder.start()

    def on_recording_started(self):
        """Handles visual UI feedback when microphone recording starts."""
        self.player.stop()
        TTSService.get_instance().stop()
        self.state_manager.set_state(AssistantState.LISTENING)
        self.view.set_recording_active(True)
        print("[Orchestrator] Capturando audio desde micrófono...")

    def on_recording_stopped(self, audio_path: str):
        """Transitions state and triggers background Whisper transcription when audio is ready."""
        self.view.set_recording_active(False)
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Notify user on UI
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        prefix = "" if not self.view.output_display.toPlainText().strip() else "<br/>"
        cursor.insertHtml(f"{prefix}<span style='color: #F59E0B;'><i>[LIA: Procesando grabación de voz...]</i></span>")
        self.view.output_display.ensureCursorVisible()

        # Launch background transcription QThread
        self.transcription_worker = TranscriptionWorker(audio_path)
        self.transcription_worker.transcription_completed.connect(self.on_transcription_completed)
        self.transcription_worker.error_occurred.connect(self.on_transcription_error)
        self.transcription_worker.start()

    def on_transcription_completed(self, text: str):
        """Fills in the user text and auto-submits once transcription completes."""
        if self.transcription_worker:
            self.transcription_worker.deleteLater()
            self.transcription_worker = None

        if not text:
            # Fallback to idle if silence or audio couldn't resolve
            cursor = self.view.output_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            prefix = "" if not self.view.output_display.toPlainText().strip() else "<br/>"
            cursor.insertHtml(f"{prefix}<span style='color: #F87171;'><i>[LIA: No se detectó voz clara. Intente de nuevo.]</i></span>")
            self.view.output_display.ensureCursorVisible()
            self.state_manager.set_state(AssistantState.IDLE)
            return

        # Write transcribed query to input and trigger submission
        self.view.input_field.setText(text)
        self.handle_input_submission()

    def on_transcription_error(self, err_msg: str):
        """Cleans transcription worker reference and calls base error handler."""
        if self.transcription_worker:
            self.transcription_worker.deleteLater()
            self.transcription_worker = None
        self.on_audio_error(err_msg)

    def on_audio_error(self, err_msg: str):
        """Displays audio errors on UI and resets state."""
        self.view.set_recording_active(False)
        self.state_manager.set_state(AssistantState.IDLE)

        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #F87171;'><b>Error de Audio:</b> {err_msg}</span><br/>")
        self.view.output_display.ensureCursorVisible()

    def show_config_menu(self):
        """Queries connected input devices and requests view to spawn selector QMenu."""
        try:
            # Query active hardware devices
            devices = sd.query_devices()
            input_devices = []
            seen_names = set()
            for idx, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0:
                    name = dev.get('name', f"Micrófono {idx}")
                    if name not in seen_names:
                        seen_names.add(name)
                        input_devices.append((idx, name))

            # Retrieve active status of TTS
            tts_enabled = TTSService.get_instance().enabled

            # Display the selection dropdown in the view
            self.view.show_config_menu(
                input_devices,
                self.active_mic_id,
                tts_enabled,
                self.toggle_tts,
                self.select_microphone
            )
        except Exception as e:
            print(f"[Orchestrator] Error al listar los micrófonos del sistema: {e}")

    def toggle_tts(self):
        """Toggles the active state of TTS service and logs status on UI."""
        service = TTSService.get_instance()
        new_state = not service.enabled
        service.set_enabled(new_state)

        status_msg = "activada" if new_state else "desactivada"
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #C084FC;'><i>[Sistema: Respuesta por voz {status_msg}]</i></span><br/>")
        self.view.output_display.ensureCursorVisible()
        print(f"[Orchestrator] Respuesta por voz (TTS) cambiada a: {new_state}")

    def select_microphone(self, device_id):
        """Updates active microphone configuration index and logs status on UI."""
        self.active_mic_id = device_id
        
        try:
            info = sd.query_devices(device_id, 'input')
            name = info.get('name', f"Dispositivo {device_id}")
        except Exception:
            name = f"Dispositivo {device_id}"

        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #C084FC;'><i>[Sistema: Micrófono activo cambiado a '{name}']</i></span><br/>")
        self.view.output_display.ensureCursorVisible()
        print(f"[Orchestrator] Micrófono de entrada cambiado a ID {device_id} ({name})")

    def play_speech_audio(self, path: str):
        """Plays the generated speech MP3 file using QMediaPlayer."""
        if os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
