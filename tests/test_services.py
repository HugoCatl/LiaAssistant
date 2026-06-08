import sys
from unittest.mock import MagicMock, patch
import pytest

from src.services.os_automation import open_application
from src.services.gemini_service import GeminiWorker

def test_os_automation_win32_mappings():
    """Verifies that common application names map to Windows executables and use os.startfile."""
    with patch("sys.platform", "win32"), patch("os.startfile") as mock_startfile:
        result = open_application("bloc de notas")
        assert "iniciada correctamente en Windows" in result
        mock_startfile.assert_called_once_with("notepad.exe")

        mock_startfile.reset_mock()
        result_calc = open_application("calculadora")
        assert "iniciada correctamente en Windows" in result_calc
        mock_startfile.assert_called_once_with("calc.exe")

def test_os_automation_file_not_found():
    """Verifies that os_automation handles missing binaries gracefully without raising exceptions."""
    with patch("os.startfile", side_effect=FileNotFoundError):
        result = open_application("programa_inexistente")
        assert "Error: No se pudo encontrar el archivo ejecutable" in result

@patch("google.genai.Client")
def test_gemini_worker_streaming_and_tools(mock_client_class):
    """
    Verifies that GeminiWorker processes stream chunks correctly,
    emitting text tokens and tool calls via PyQt6 signals.
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

    # Mock stream response
    mock_client.models.generate_content_stream.return_value = [chunk_1, chunk_2]

    # Initialize worker with mock environment
    worker = GeminiWorker("abre el bloc de notas")
    worker.api_key = "mock_key"

    # Track emitted signals
    received_tokens = []
    received_tools = []

    worker.token_received.connect(received_tokens.append)
    worker.tool_call_detected.connect(lambda name, args: received_tools.append((name, args)))

    # Execute QThread's run method synchronously for testing
    worker.run()

    # Validate results
    assert received_tokens == ["Claro, abriendo "]
    assert len(received_tools) == 1
    assert received_tools[0] == ("open_application", {"app_name": "notepad"})
