import pytest
from src.core.state_manager import StateManager, AssistantState
from config import settings

def test_settings_loading():
    """Verifies settings load environment variables properly."""
    assert settings.whisper_model_path == "small"
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


def test_orchestrator_ui_locking():
    """Verifica que el orquestador bloquee y desbloquee los inputs de la UI al cambiar de estado."""
    from src.core.orchestrator import Orchestrator
    from src.core.state_manager import AssistantState
    from unittest.mock import MagicMock, patch

    mock_view = MagicMock()
    mock_view.input_field = MagicMock()
    mock_view.mic_button = MagicMock()
    mock_view.output_display = MagicMock()
    
    mock_state = MagicMock()
    mock_kbd = MagicMock()
    
    with patch("sounddevice.default.device", (0, 0)):
        orch = Orchestrator(mock_view, mock_state, mock_kbd)
        
    # Mock isRunning for recorder
    orch.audio_recorder = MagicMock()
    orch.audio_recorder.isRunning.return_value = False
    
    # Test transitions
    # 1. State PROCESSING: both should be disabled
    orch.on_state_changed(AssistantState.PROCESSING)
    mock_view.input_field.setEnabled.assert_called_with(False)
    mock_view.mic_button.setEnabled.assert_called_with(False)
    
    # Reset mocks
    mock_view.input_field.setEnabled.reset_mock()
    mock_view.mic_button.setEnabled.reset_mock()
    
    # 2. State RESPONDING: both should be disabled
    orch.on_state_changed(AssistantState.RESPONDING)
    mock_view.input_field.setEnabled.assert_called_with(False)
    mock_view.mic_button.setEnabled.assert_called_with(False)
    
    # Reset mocks
    mock_view.input_field.setEnabled.reset_mock()
    mock_view.mic_button.setEnabled.reset_mock()
    
    # 3. State IDLE: both should be enabled
    orch.on_state_changed(AssistantState.IDLE)
    mock_view.input_field.setEnabled.assert_called_with(True)
    mock_view.mic_button.setEnabled.assert_called_with(True)
    mock_view.input_field.setFocus.assert_called_once()
    
    # Reset mocks
    mock_view.input_field.setEnabled.reset_mock()
    mock_view.mic_button.setEnabled.reset_mock()
    mock_view.input_field.setFocus.reset_mock()
    
    # 4. State LISTENING, recorder not running: input enabled, mic enabled
    orch.audio_recorder.isRunning.return_value = False
    orch.on_state_changed(AssistantState.LISTENING)
    mock_view.input_field.setEnabled.assert_called_with(True)
    mock_view.mic_button.setEnabled.assert_called_with(True)
    
    # Reset mocks
    mock_view.input_field.setEnabled.reset_mock()
    mock_view.mic_button.setEnabled.reset_mock()
    
    # 5. State LISTENING, recorder running (user speaking): input disabled, mic enabled
    orch.audio_recorder.isRunning.return_value = True
    orch.on_state_changed(AssistantState.LISTENING)
    mock_view.input_field.setEnabled.assert_called_with(False)
    mock_view.mic_button.setEnabled.assert_called_with(True)

