import os
from typing import TYPE_CHECKING
import sounddevice as sd
from PyQt6.QtCore import QObject, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from config import settings
from src.core.state_manager import StateManager, AssistantState
from src.services.gemini_service import GeminiWorker, GeminiReasoningWorker
from src.services.os_automation import open_application
from src.io.audio_recorder import AudioRecorder
from src.services.whisper_local import TranscriptionWorker
from src.services.tts_service import TTSService
from src.services.system_monitor import SystemMonitor
from src.services.proactive_engine import ProactiveEngine
from src.gui.components.mascot_bubble import MascotBubble

if TYPE_CHECKING:
    from src.gui.view import View

class Orchestrator(QObject):
    """
    Mediator coordinating UI events, global keyboard shortcut triggers,
    state transitions, hardware audio recording, local Whisper STT,
    and background asynchronous Gemini API execution.
    """
    def __init__(self, view: "View", state_manager: StateManager, keyboard_listener, mascot=None):
        super().__init__()
        self.view = view
        self.state_manager = state_manager
        self.keyboard_listener = keyboard_listener
        self.mascot = mascot
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
        self.view.info_button.clicked.connect(self.show_info_menu)
        self.view.mic_button.clicked.connect(self.toggle_recording)

        # Wire audio recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped)
        self.audio_recorder.error_occurred.connect(self.on_audio_error)

        # Wire the desktop mascot: clicking it toggles the panel
        if self.mascot is not None:
            self.mascot.clicked.connect(self.toggle_ui)

        # --- Sistema proactivo (Fase 2): solo activo si hay mascota en escritorio ---
        self.system_monitor = None
        self.proactive_engine = None
        self.bubble = None
        self._pending_suggestion = ("", False)  # (prefill, auto_submit)

        if self.mascot is not None and settings.proactive_enabled:
            debug = settings.proactive_debug
            # En modo debug los tiempos bajan a segundos para validar en vivo
            poll_ms = 1500 if debug else 4000
            self.system_monitor = SystemMonitor(poll_ms=poll_ms)
            if debug:
                self.proactive_engine = ProactiveEngine(
                    global_cooldown_s=8.0, note_gap_s=30.0,
                    focus_gap_s=30.0, eod_hour=0, debug=True,
                )
                print("[Orchestrator] Sistema proactivo en MODO DEBUG (tiempos cortos).")
            else:
                self.proactive_engine = ProactiveEngine()
            self.bubble = MascotBubble()

            # Monitor -> Motor
            self.system_monitor.clipboard_changed.connect(self.proactive_engine.on_clipboard_changed)
            self.system_monitor.active_window_changed.connect(self.proactive_engine.on_active_window_changed)
            self.system_monitor.tick.connect(self.proactive_engine.on_tick)

            # Motor -> UI (burbuja + expresión de la mascota)
            self.proactive_engine.suggestion.connect(self.on_proactive_suggestion)
            self.bubble.accepted.connect(self.on_suggestion_accepted)
            self.bubble.dismissed.connect(self.on_suggestion_dismissed)

    def show_welcome_greeting(self):
        """Muestra un saludo proactivo e inspirador en el display si está vacío, incitando a registrar ideas o tareas."""
        if not self.view.output_display.toPlainText().strip():
            import random
            greetings = [
                f"¡Hola {settings.user_name}! ¿Qué idea se te ha ocurrido hoy? 💡",
                f"Hola {settings.user_name}, ¿en qué tarea o proyecto profesional vamos a trabajar hoy? 🚀",
                "¡Buenas! Cuéntame, ¿qué hay de nuevo hoy en tus notas o estudios? 🧠",
                f"Hola {settings.user_name}, ¿tienes alguna idea o nota profesional para enlazar hoy? ✨",
                "¡Hola! ¿Qué se te pasa por la cabeza hoy? Estoy lista para anotarlo todo. 📝"
            ]
            greeting = random.choice(greetings)
            self.view.output_display.setHtml(
                f"<span style='color: #A78BFA; font-weight: bold;'>LIA:</span> "
                f"<span style='color: #F1F5F9;'>{greeting}</span>"
            )

    def show_info_menu(self):
        """Muestra un menú desplegable con guías rápidas y ejemplos interactivos que autocompletan el input."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtCore import QPoint
        
        menu = QMenu(self.view)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(22, 16, 28, 0.96);
                border: 1px solid rgba(192, 132, 252, 0.4);
                border-radius: 8px;
                color: #E2E8F0;
                padding: 4px;
                font-family: 'Segoe UI', 'Outfit', sans-serif;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 14px;
                background-color: transparent;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(192, 132, 252, 0.25);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(192, 132, 252, 0.2);
                margin: 4px 8px;
            }
        """)

        # Visión de pantalla
        vision_action = menu.addAction("📸 Ver Pantalla: \"Mira mi pantalla y resume...\"")
        vision_action.triggered.connect(lambda: self.view.input_field.setText("Mira mi pantalla y resume lo que ves."))

        # Portapapeles
        clip_action = menu.addAction("📋 Portapapeles: \"Crea una nota con mi portapapeles\"")
        clip_action.triggered.connect(lambda: self.view.input_field.setText("Crea una nota con lo que tengo en mi portapapeles."))

        # Cerebro
        brain_action = menu.addAction("🧠 Segundo Cerebro: \"Busca en mis notas...\"")
        brain_action.triggered.connect(lambda: self.view.input_field.setText("Busca en mis notas sobre "))

        # Separator
        menu.addSeparator()

        # Help info item (non-clickable info)
        help_item = menu.addAction("🎙️ Micro: haz clic para hablar | Atajo: Shift_L + L")
        help_item.setEnabled(False)

        # Position menu right below the info button
        pos = self.view.info_button.mapToGlobal(QPoint(0, self.view.info_button.height()))
        menu.exec(pos)



    def start(self):
        """Starts the background listening thread and displays startup greeting."""
        self.keyboard_listener.start()
        if self.system_monitor is not None:
            self.system_monitor.start()
        # En modo debug, lanza una sugerencia de ejemplo a los 4s para ver el flujo
        if self.proactive_engine is not None and settings.proactive_debug:
            QTimer.singleShot(4000, self._show_demo_suggestion)
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

        # Reflejar el estado en la expresión de la mascota
        if self.mascot is not None:
            self.mascot.set_state(state)

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

    def detect_vision_intent(self, text: str) -> bool:
        """
        Analiza si el texto ingresado requiere captura de pantalla como contexto visual.
        """
        keywords = [
            "pantalla", "pantallazo", "error", "consola", "mira", "ve", "captura",
            "visualiza", "abierto", "abierta", "codigo", "código", "portada", "interfaz"
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

        # Registrar actividad: el usuario interactuó con Lia (resetea inactividad)
        if self.proactive_engine is not None:
            self.proactive_engine.note_activity(is_capture=True)

        # Clear input field
        self.view.input_field.clear()

        # Update display logs
        self.view.output_display.append(f"<span style='color: #C084FC; font-weight: bold;'>Tú:</span> <span style='color: #F1F5F9;'>{user_text}</span>")
        self.view.output_display.append("<span style='color: #A78BFA; font-weight: bold;'>LIA:</span> ")
        self.view.output_display.ensureCursorVisible()

        # Set UI state to processing
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Capturar pantalla si el usuario tiene intención visual
        screenshot_path = None
        if self.detect_vision_intent(user_text):
            try:
                from PIL import ImageGrab
                screenshot_path = "temp_screenshot.png"
                screenshot = ImageGrab.grab()
                screenshot.save(screenshot_path, "PNG")
                print(f"[Orchestrator] Capturando pantalla para contexto visual: {screenshot_path}")
            except Exception as e:
                print(f"[Orchestrator] Error al capturar pantalla: {e}")
                screenshot_path = None

        # Enrutar inteligentemente según la intención
        if self.detect_reasoning_intent(user_text):
            print(f"[Orchestrator] Enrutando '{user_text}' al Agente de Razonamiento (Gemini Pro)...")
            self.worker = GeminiReasoningWorker(user_text, image_path=screenshot_path)
        else:
            print(f"[Orchestrator] Enrutando '{user_text}' al Agente de Acción Rápida (Gemini Flash)...")
            self.worker = GeminiWorker(user_text, image_path=screenshot_path)
        
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
        """Muestra en consola que una herramienta está siendo ejecutada."""
        print(f"[Orchestrator - Tool Call] Detectado: {name} con argumentos {args}")

    def on_tool_call_completed(self, name: str, result: str):
        """Muestra en consola el resultado de la ejecución de la herramienta."""
        print(f"[Orchestrator - Tool Call] Completado: {name} -> {result}")

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

        # Clean up screenshot if it exists
        if os.path.exists("temp_screenshot.png"):
            try:
                os.remove("temp_screenshot.png")
            except Exception as e:
                print(f"[Orchestrator] Error al eliminar temp_screenshot.png: {e}")

    # --- Sistema Proactivo (Fase 2) ---

    def _show_demo_suggestion(self):
        """[debug] Muestra una sugerencia de ejemplo para validar el flujo visual."""
        self.on_proactive_suggestion(
            f"¡Hola {settings.user_name}! Soy Lia. Cuando vea algo que merezca la "
            f"pena anotar, te avisaré así. ¿Probamos a crear una nota?",
            "Crea una nota de prueba titulada 'Mi primera nota con Lia'.",
            False, "reminder",
        )

    def on_proactive_suggestion(self, text: str, prefill: str, auto_submit: bool, mood: str):
        """Muestra una sugerencia proactiva de Lia mediante la burbuja de la mascota."""
        # No interrumpir si el panel está abierto o Lia está ocupada
        if self.view.isVisible() or (self.worker and self.worker.isRunning()):
            return
        if self.audio_recorder.isRunning():
            return

        self._pending_suggestion = (prefill, auto_submit)
        if self.mascot is not None:
            self.mascot.set_mood(mood)
            self.bubble.show_message(text, self.mascot, with_actions=True)

    def on_suggestion_accepted(self):
        """El usuario aceptó la sugerencia: abre el panel y precarga/ejecuta la acción."""
        prefill, auto_submit = self._pending_suggestion
        self._pending_suggestion = ("", False)
        if self.proactive_engine is not None:
            self.proactive_engine.record_feedback(True)

        if not self.view.isVisible():
            self.toggle_ui()

        if prefill:
            self.view.input_field.setText(prefill)
            if auto_submit:
                self.handle_input_submission()
            else:
                self.view.input_field.setFocus()

    def on_suggestion_dismissed(self):
        """El usuario descartó la sugerencia (o expiró). Reduce la insistencia."""
        self._pending_suggestion = ("", False)
        if self.proactive_engine is not None:
            self.proactive_engine.record_feedback(False)
        if self.mascot is not None:
            from src.gui.mascot_behavior import MascotMood
            self.mascot.set_mood(MascotMood.IDLE)

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
