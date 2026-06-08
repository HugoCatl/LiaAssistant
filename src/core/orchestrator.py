from PyQt6.QtCore import QObject, QTimer
from src.core.state_manager import StateManager, AssistantState
from src.gui.view import View
from src.io.keyboard_listener import KeyboardListener

class Orchestrator(QObject):
    """
    Mediator coordinating UI events, global keyboard shortcut triggers,
    and state transitions.
    """
    def __init__(self, view: View, state_manager: StateManager, keyboard_listener: KeyboardListener):
        super().__init__()
        self.view = view
        self.state_manager = state_manager
        self.keyboard_listener = keyboard_listener

        # Setup signaling pipeline
        self.keyboard_listener.hotkey_triggered.connect(self.toggle_ui)
        self.state_manager.state_changed.connect(self.view.update_status_dot)
        self.view.input_field.returnPressed.connect(self.handle_input_submission)

    def start(self):
        """Starts the background listening thread."""
        self.keyboard_listener.start()
        print("[Orchestrator] Base system started successfully.")
        print("[Orchestrator] Press 'Shift_L + L' globally to show/hide the assistant overlay.")

    def toggle_ui(self):
        """Toggles the visibility of the frameless UI overlay window."""
        if self.view.isVisible():
            self.view.hide()
            self.state_manager.set_state(AssistantState.IDLE)
            print("[Orchestrator] UI Hidden. State: IDLE")
        else:
            self.view.show()
            self.view.raise_()
            self.view.activateWindow()
            self.view.input_field.setFocus()
            self.state_manager.set_state(AssistantState.LISTENING)
            print("[Orchestrator] UI Activated. State: LISTENING")

    def handle_input_submission(self):
        """Handles submission from the input field."""
        user_text = self.view.input_field.text().strip()
        if not user_text:
            return

        self.view.input_field.clear()
        self.view.output_display.append(f"<br/><b>Tú:</b> {user_text}")
        
        # Transition to PROCESSING state
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Simulate API logic or command processing asynchronously via a timer
        QTimer.singleShot(1500, lambda: self.simulate_response(user_text))

    def simulate_response(self, user_text):
        """Mock response handler simulating LLM generation."""
        self.state_manager.set_state(AssistantState.RESPONDING)
        
        response = f"Recibido: <i>\"{user_text}\"</i>. La integración de la API Gemini y la automatización se activarán en el siguiente Sprint."
        self.view.output_display.append(f"<b>Omega:</b> {response}")
        
        # Transition back to IDLE
        self.state_manager.set_state(AssistantState.IDLE)
