import pytest
from src.core.state_manager import StateManager, AssistantState
from config import settings

def test_settings_loading():
    """Verifies settings load environment variables properly."""
    assert settings.whisper_model_path == "base"
    assert settings.debug is True

def test_state_manager_transitions():
    """Validates the state machine and state signal emission."""
    manager = StateManager()
    assert manager.state == AssistantState.IDLE

    # Track signal emission
    transitions = []
    manager.state_changed.connect(transitions.append)

    # Transition 1
    manager.set_state(AssistantState.LISTENING)
    assert manager.state == AssistantState.LISTENING
    assert len(transitions) == 1
    assert transitions[-1] == AssistantState.LISTENING

    # Transition 2
    manager.set_state(AssistantState.PROCESSING)
    assert manager.state == AssistantState.PROCESSING
    assert len(transitions) == 2
    assert transitions[-1] == AssistantState.PROCESSING

    # Re-setting same state should not trigger signal
    manager.set_state(AssistantState.PROCESSING)
    assert len(transitions) == 2
