import os
import sounddevice as sd
from PyQt6.QtCore import QObject
from src.core.state_manager import StateManager, AssistantState
from src.gui.view import View
from src.services.gemini_service import GeminiWorker
from src.services.os_automation import open_application
from src.io.audio_recorder import AudioRecorder
from src.services.whisper_local import TranscriptionWorker

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
        self.state_manager.state_changed.connect(self.view.update_status_dot)
        self.view.input_field.returnPressed.connect(self.handle_input_submission)

        # Wire settings config wheel and microphone recording buttons
        self.view.config_button.clicked.connect(self.show_config_menu)
        self.view.mic_button.clicked.connect(self.toggle_recording)

        # Wire audio recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped)
        self.audio_recorder.error_occurred.connect(self.on_audio_error)

    def start(self):
        """Starts the background listening thread."""
        self.keyboard_listener.start()
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
            print("[Orchestrator] Panel activado. Estado: LISTENING")

    def handle_input_submission(self):
        """Handles user text submission and spawns the background Gemini worker."""
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
        self.view.output_display.append(f"<br/><b>Tú:</b> {user_text}")
        self.view.output_display.append("<b>LIA:</b> ")
        self.view.output_display.ensureCursorVisible()

        # Set UI state to processing
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Create the background thread worker for the Gemini stream
        self.worker = GeminiWorker(user_text)
        
        # Connect signals
        self.worker.token_received.connect(self.on_token_received)
        self.worker.tool_call_detected.connect(self.on_tool_call_detected)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.finished.connect(self.on_generation_finished)

        # Start background thread execution
        self.worker.start()

    def on_token_received(self, token: str):
        """Streams text tokens inline directly into the output display."""
        if self.state_manager.state == AssistantState.PROCESSING:
            self.state_manager.set_state(AssistantState.RESPONDING)

        # Move text cursor to end and insert token inline (produces character-by-character animation)
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self.view.output_display.ensureCursorVisible()

    def on_tool_call_detected(self, name: str, args: dict):
        """Routes detected tool calls to local OS automation functions."""
        if name == "open_application":
            app_name = args.get("app_name")
            if app_name:
                # Append information log to the output display
                cursor = self.view.output_display.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.insertHtml(f"<br/><span style='color: #C084FC;'><i>[Ejecutando comando: Abrir {app_name}...]</i></span>")
                self.view.output_display.ensureCursorVisible()

                # Execute automation natively
                result = open_application(app_name)

                # Show command results in output display
                cursor.insertHtml(f"<br/><span style='color: #00FF7F;'><i>[Sistema: {result}]</i></span><br/>")
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
        cursor.insertHtml("<br/><span style='color: #F59E0B;'><i>[LIA: Procesando grabación de voz...]</i></span>")
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
            cursor.insertHtml("<br/><span style='color: #F87171;'><i>[LIA: No se detectó voz clara. Intente de nuevo.]</i></span><br/>")
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

            # Display the selection dropdown in the view
            self.view.show_microphone_menu(input_devices, self.active_mic_id, self.select_microphone)
        except Exception as e:
            print(f"[Orchestrator] Error al listar los micrófonos del sistema: {e}")

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
