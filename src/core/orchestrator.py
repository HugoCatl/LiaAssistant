from PyQt6.QtCore import QObject
from src.core.state_manager import StateManager, AssistantState
from src.gui.view import View
from src.services.gemini_service import GeminiWorker
from src.services.os_automation import open_application

class Orchestrator(QObject):
    """
    Mediator coordinating UI events, global keyboard shortcut triggers,
    state transitions, and background asynchronous Gemini API execution.
    """
    def __init__(self, view: View, state_manager: StateManager, keyboard_listener):
        super().__init__()
        self.view = view
        self.state_manager = state_manager
        self.keyboard_listener = keyboard_listener
        self.worker = None

        # Setup signaling pipeline
        self.keyboard_listener.hotkey_triggered.connect(self.toggle_ui)
        self.state_manager.state_changed.connect(self.view.update_status_dot)
        self.view.input_field.returnPressed.connect(self.handle_input_submission)

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
                cursor.insertHtml(f"<br/><span style='color: #00F3FF;'><i>[Ejecutando comando: Abrir {app_name}...]</i></span>")
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
        cursor.insertHtml(f"<br/><span style='color: #FF5A5A;'><b>Error:</b> {err_msg}</span><br/>")
        self.view.output_display.ensureCursorVisible()

    def on_generation_finished(self):
        """Restores the UI state to idle when the generation ends."""
        self.state_manager.set_state(AssistantState.IDLE)
        # Safely mark QThread for garbage collection
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
