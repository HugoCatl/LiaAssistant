from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

class AssistantState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"

class StateManager(QObject):
    """
    Manages the current operational state of the assistant (e.g. Idle, Listening, Processing, Responding).
    Uses PyQt6 signals to notify interested observers of state changes.
    """
    state_changed = pyqtSignal(AssistantState)

    def __init__(self):
        super().__init__()
        self._state = AssistantState.IDLE

    @property
    def state(self) -> AssistantState:
        return self._state

    def set_state(self, new_state: AssistantState):
        """Transitions the assistant to a new state and emits a signal."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self.state_changed.emit(new_state)
            if self.recipe_logs_enabled():
                print(f"[StateManager] Transitioned: {old_state.value} -> {new_state.value}")

    def recipe_logs_enabled(self) -> bool:
        # Helper to avoid extra prints if unnecessary, but standard logging is good.
        return True
