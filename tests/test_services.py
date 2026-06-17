import sys
from unittest.mock import MagicMock, patch
import pytest

from src.services.os_automation import open_application
from src.services.gemini_service import GeminiWorker, GeminiReasoningWorker
from src.services.tts_service import TTSService
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
    assert orch.detect_reasoning_intent("analiza a fondo mi situación laboral") is True
    assert orch.detect_reasoning_intent("necesito tu mentoría en este tema") is True
    assert orch.detect_reasoning_intent("reflexiona sobre la decisión compleja que debo tomar") is True
    
    # Assert action prompts route to action worker
    assert orch.detect_reasoning_intent("abre el paint 3d") is False
    assert orch.detect_reasoning_intent("guarda la nota Tareas") is False
    assert orch.detect_reasoning_intent("¿cuál es el estado de mi perfil?") is False
    assert orch.detect_reasoning_intent("hazme una rutina de gimnasio") is False


def test_tts_sanitization():
    """Verifies that markdown, HTML, Obsidian links, code blocks and system tags are correctly cleaned."""
    text_with_markdown = "Hola **Usuario**, esto es *importante* y _italica_."
    assert TTSService.sanitize_text_for_speech(text_with_markdown) == "Hola Usuario, esto es importante y italica."

    text_with_code = "Mira este codigo: ```python\nprint('hello')\n``` y `x = 5`."
    assert TTSService.sanitize_text_for_speech(text_with_code) == "Mira este codigo: y ."

    text_with_html = "Hola <br/> Nombre <span>Usuario</span>"
    assert TTSService.sanitize_text_for_speech(text_with_html) == "Hola Nombre Usuario"

    text_with_links = "Revisa la nota [[Nombre Usuario]] y la de [[Tareas]]"
    assert TTSService.sanitize_text_for_speech(text_with_links) == "Revisa la nota Nombre Usuario y la de Tareas"

    text_with_lists = "# Titulo Principal\n- Primera idea\n* Segunda idea"
    assert TTSService.sanitize_text_for_speech(text_with_lists) == "Titulo Principal. Primera idea. Segunda idea"

    text_with_system = "[Tokens usados - Entrada: 50 | Salida: 20 | Total: 70]\n[Ejecutando comando: open_application]\n[Sistema: Notepad iniciado]\nTodo listo."
    assert TTSService.sanitize_text_for_speech(text_with_system) == "Todo listo."


@patch("pyperclip.paste")
@patch("pyperclip.copy")
def test_clipboard_automation(mock_copy, mock_paste):
    """Verifies that get_clipboard_content and set_clipboard_content interact with pyperclip correctly."""
    from src.services.os_automation import get_clipboard_content, set_clipboard_content
    
    # Test get_clipboard_content with text
    mock_paste.return_value = "Hola LIA"
    assert get_clipboard_content() == "Hola LIA"
    mock_paste.assert_called_once()
    
    # Test get_clipboard_content empty/whitespace
    mock_paste.reset_mock()
    mock_paste.return_value = "   "
    assert "vacío o no contiene texto legible" in get_clipboard_content()
    mock_paste.assert_called_once()
    
    # Test set_clipboard_content
    result = set_clipboard_content("Prueba LIA")
    assert "Texto copiado al portapapeles correctamente" in result
    mock_copy.assert_called_once_with("Prueba LIA")


@patch("google.genai.Client")
@patch("os.path.exists", return_value=True)
@patch("builtins.open")
def test_gemini_worker_multimodal(mock_open, mock_exists, mock_client_class):
    """Verifies that GeminiWorker appends the screenshot bytes when an image path is supplied."""
    # Mock file read for image bytes
    mock_file = MagicMock()
    mock_file.read.return_value = b"fake_png_data"
    mock_open.return_value.__enter__.return_value = mock_file
    
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content_stream.return_value = []
    
    worker = GeminiWorker("mira mi pantalla", image_path="fake_screenshot.png")
    worker.api_key = "mock_key"
    worker.run()
    
    # Verify generate_content_stream call contents contains Part with image bytes
    args, kwargs = mock_client.models.generate_content_stream.call_args
    contents = kwargs.get("contents")
    assert contents is not None
    user_content = contents[0]
    parts = user_content.parts
    assert len(parts) == 2
    assert parts[0].text == "mira mi pantalla"
    assert parts[1].inline_data.data == b"fake_png_data"
    assert parts[1].inline_data.mime_type == "image/png"



