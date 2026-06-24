"""
Verifica la memoria conversacional: el worker arranca con el historial previo y
el orquestador conserva/acota la conversación entre turnos.
"""
import os
import pytest
from google.genai import types

from src.services.gemini_service import GeminiWorker


def test_worker_seeds_contents_with_history():
    """El worker debe incluir los turnos previos antes del mensaje nuevo."""
    history = [
        types.Content(role="user", parts=[types.Part.from_text(text="Crea una nota con mi portapapeles")]),
        types.Content(role="model", parts=[types.Part.from_text(text="¿Qué título le pongo?")]),
    ]
    w = GeminiWorker("Ideas", history=history)
    assert w.history is history
    assert w.result_contents == []  # aún no ejecutado


def test_history_defaults_to_empty():
    w = GeminiWorker("hola")
    assert w.history == []


class _StubContent:
    def __init__(self, role):
        self.role = role


def test_trim_history_keeps_tail_and_starts_with_user():
    """_trim_history acota y nunca deja un 'tool'/'model' huérfano al inicio."""
    from src.core.orchestrator import Orchestrator
    # Evitamos construir un Orchestrator real: probamos el método como función no ligada
    trim = Orchestrator._trim_history
    convo = (
        [_StubContent("user"), _StubContent("model"), _StubContent("tool")] * 10
    )

    class _Self:
        pass

    out = trim(_Self(), convo, max_items=5)
    assert len(out) <= 5
    assert out[0].role == "user"  # no empieza por tool/model huérfano


def test_trim_history_drops_leading_orphans():
    from src.core.orchestrator import Orchestrator
    trim = Orchestrator._trim_history
    convo = [_StubContent("tool"), _StubContent("model"), _StubContent("user"), _StubContent("model")]

    class _Self:
        pass

    out = trim(_Self(), convo, max_items=4)
    assert out[0].role == "user"
    assert len(out) == 2
