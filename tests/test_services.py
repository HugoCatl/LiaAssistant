import sys
from unittest.mock import MagicMock, patch
import pytest

from src.services.os_automation import open_application
from src.services.gemini_service import GeminiWorker, GeminiReasoningWorker
from src.core.orchestrator import Orchestrator

def test_os_automation_win32_mappings():
    """Verifies that common application names map to Windows executables and use os.startfile."""
    with patch("os.startfile") as mock_startfile:
        result = open_application("bloc de notas")
        assert "iniciada correctamente en Windows" in result
        mock_startfile.assert_called_once_with("notepad.exe")

        mock_startfile.reset_mock()
        result_calc = open_application("calculadora")
        assert "iniciada correctamente en Windows" in result_calc
        mock_startfile.assert_called_once_with("calc.exe")

def test_os_automation_paint3d():
    """Verifies that Paint 3D triggers ms-paint: protocol."""
    with patch("os.startfile") as mock_startfile:
        result = open_application("paint 3d")
        assert "Paint 3D" in result
        mock_startfile.assert_called_once_with("ms-paint:")

def test_os_automation_teams():
    """Verifies that Teams triggers ms-teams: UWP protocol."""
    with patch("os.startfile") as mock_startfile:
        result = open_application("teams")
        assert "Microsoft Teams (UWP) iniciado" in result
        mock_startfile.assert_called_once_with("ms-teams:")

def test_os_automation_discord_fallback():
    """Verifies Discord fallback triggers shell start when LocalAppData is missing."""
    with patch("os.path.exists", return_value=False), patch("os.startfile") as mock_startfile:
        result = open_application("discord")
        assert "Discord invocado" in result
        mock_startfile.assert_called_once_with("discord")

def test_os_automation_file_not_found():
    """Verifies that os_automation handles missing binaries gracefully without raising exceptions."""
    with patch("os.startfile", side_effect=FileNotFoundError):
        result = open_application("programa_inexistente")
        assert "Error: No se pudo encontrar el archivo ejecutable" in result

@patch("google.genai.Client")
@patch("os.startfile")
def test_gemini_worker_streaming_and_tools(mock_startfile, mock_client_class):
    """
    Verifies that GeminiWorker processes stream chunks correctly,
    emitting text tokens and tool calls via PyQt6 signals, and executing tools.
    """
    # Create mock client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Define stream chunks: chunk 1 has text, chunk 2 has function call
    chunk_1 = MagicMock()
    chunk_1.text = "Claro, abriendo "
    chunk_1.function_calls = None

    chunk_2 = MagicMock()
    chunk_2.text = None
    mock_call = MagicMock()
    mock_call.name = "open_application"
    mock_call.args = {"app_name": "notepad"}
    chunk_2.function_calls = [mock_call]

    # Mock stream response to return chunks in first call and empty list in second call
    mock_client.models.generate_content_stream.side_effect = [
        [chunk_1, chunk_2],
        []
    ]

    # Initialize worker with mock environment
    worker = GeminiWorker("abre el bloc de notas")
    worker.api_key = "mock_key"

    # Track emitted signals
    received_tokens = []
    received_tools = []
    completed_tools = []

    worker.token_received.connect(received_tokens.append)
    worker.tool_call_detected.connect(lambda name, args: received_tools.append((name, args)))
    worker.tool_call_completed.connect(lambda name, result: completed_tools.append((name, result)))

    # Execute QThread's run method synchronously for testing
    worker.run()

    # Validate results
    assert received_tokens == ["Claro, abriendo "]
    assert len(received_tools) == 1
    assert received_tools[0] == ("open_application", {"app_name": "notepad"})
    
    # Verify tool execution signal was emitted and os.startfile was called
    assert len(completed_tools) == 1
    assert completed_tools[0][0] == "open_application"
    assert "iniciada correctamente en Windows" in completed_tools[0][1]
    mock_startfile.assert_called_once_with("notepad.exe")

def test_orchestrator_intent_routing():
    """Validates that the orchestrator routes conversational/reasoning inputs to Pro and actions to Flash."""
    # Mock view and controller dependencies
    mock_view = MagicMock()
    # Stub return values for input field and dot indicator
    mock_view.input_field = MagicMock()
    mock_view.output_display = MagicMock()
    
    mock_state = MagicMock()
    mock_kbd = MagicMock()
    
    # We patch sounddevice.default.device to avoid querying system hardware during tests
    with patch("sounddevice.default.device", (0, 0)):
        orch = Orchestrator(mock_view, mock_state, mock_kbd)
    
    # Assert reasoning keywords route to reasoning agent
    assert orch.detect_reasoning_intent("¿Qué me aconsejas hacer en mi trabajo?") is True
    assert orch.detect_reasoning_intent("Hazme una rutina de gimnasio por favor") is True
    assert orch.detect_reasoning_intent("cuál es el estado de mi perfil") is True
    
    # Assert action prompts route to action worker
    assert orch.detect_reasoning_intent("abre el paint 3d") is False
    assert orch.detect_reasoning_intent("guarda la nota Tareas") is False


