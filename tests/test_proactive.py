"""Tests del motor proactivo (Fase 2) y los helpers del monitor de sistema."""
import os
import tempfile
import pytest

import src.services.proactive_engine as _pe_mod
from src.services.proactive_engine import ProactiveEngine, _looks_like_url, _short
from src.services.system_monitor import get_active_window_title, get_idle_seconds
from src.services.feedback_store import FeedbackStore


@pytest.fixture(autouse=True)
def _isolated_feedback_store(tmp_path, monkeypatch):
    """Cada test usa un FeedbackStore aislado en tmp_path (no contamina datos reales)."""
    db = str(tmp_path / "fb.db")
    original = _pe_mod.FeedbackStore
    monkeypatch.setattr(_pe_mod, "FeedbackStore", lambda: original(db))


def _collect(engine):
    got = []
    engine.suggestion.connect(lambda *a: got.append(a))
    return got


def test_url_detection_and_shorten():
    assert _looks_like_url("https://anthropic.com")
    assert _looks_like_url("www.python.org")
    assert not _looks_like_url("solo texto normal")
    assert _short("a" * 100, 20).endswith("…")
    assert _short("corto", 20) == "corto"


def test_clipboard_suggestion_and_dedup():
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)

    eng.on_clipboard_changed("x" * 120)
    assert len(got) == 1
    text, prefill, auto_submit, mood = got[0]
    assert "portapapeles" in prefill.lower()
    assert auto_submit is True
    assert mood == "curious"

    # El mismo texto no se vuelve a sugerir
    got.clear()
    eng.on_clipboard_changed("x" * 120)
    assert got == []


def test_clipboard_url_phrasing():
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)
    eng.on_clipboard_changed("https://example.com/" + "a" * 50)
    assert len(got) == 1
    assert "enlace" in got[0][0].lower()


def test_global_cooldown_blocks_second_suggestion():
    eng = ProactiveEngine(global_cooldown_s=300)
    got = _collect(eng)
    eng.on_clipboard_changed("a" * 120)
    eng.on_clipboard_changed("b" * 120)
    assert len(got) == 1  # la segunda queda bloqueada por el cooldown


def test_end_of_day_rule_fires_once_when_no_captures():
    eng = ProactiveEngine(global_cooldown_s=0, eod_hour=0)  # eod_hour=0 => siempre tarde
    got = _collect(eng)
    eng.on_tick("Editor", idle_seconds=0)
    assert len(got) == 1
    assert "resumen" in got[0][0].lower()

    # No se repite el mismo día
    got.clear()
    eng.on_tick("Editor", idle_seconds=0)
    assert got == []


def test_end_of_day_suppressed_after_capture():
    eng = ProactiveEngine(global_cooldown_s=0, eod_hour=0)
    got = _collect(eng)
    eng.note_activity(is_capture=True)  # ya anotó algo hoy
    eng.on_tick("Editor", idle_seconds=0)
    assert got == []


def test_focus_rule_fires_after_long_focus():
    eng = ProactiveEngine(global_cooldown_s=0, focus_gap_s=10, eod_hour=99)
    got = _collect(eng)
    eng.on_active_window_changed("VS Code")
    eng._focus_since -= 20  # simula 20s de foco continuo
    eng.on_tick("VS Code", idle_seconds=0)
    assert len(got) == 1
    assert got[0][3] == "reminder"


def test_idle_note_rule_requires_presence():
    eng = ProactiveEngine(global_cooldown_s=0, note_gap_s=10, eod_hour=99)
    got = _collect(eng)
    eng._last_activity_at -= 20  # mucho sin anotar

    # Usuario ausente (idle alto) => no molesta
    eng.on_tick("App", idle_seconds=999)
    assert got == []

    # Usuario presente => sugiere
    eng.on_tick("App", idle_seconds=0)
    assert len(got) == 1
    assert got[0][3] == "reminder"


def test_dismiss_feedback_extends_cooldown():
    """Tras una sugerencia emitida y rechazada, el cooldown global se refuerza."""
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)
    # Primera sugerencia: se emite y se asocia un _pending_label
    eng.on_clipboard_changed("a" * 120)
    assert len(got) == 1
    # Rechazo → refuerza cooldown
    eng.global_cooldown_s = 300
    eng.record_feedback(accepted=False)
    eng.on_clipboard_changed("b" * 120)
    assert len(got) == 1  # la segunda queda bloqueada por el cooldown reforzado


def test_note_activity_resets_idle_flag():
    eng = ProactiveEngine(global_cooldown_s=0, note_gap_s=10, eod_hour=99)
    got = _collect(eng)
    eng._last_activity_at -= 20
    eng.on_tick("App", idle_seconds=0)
    assert len(got) == 1  # primera sugerencia de inactividad

    eng.note_activity()  # el usuario interactúa: resetea
    got.clear()
    eng.on_tick("App", idle_seconds=0)
    assert got == []  # ya no insiste porque hubo actividad reciente


def test_clipboard_ignores_routine_short_copy():
    """Copiar texto corto de una línea (no URL) ya no dispara sugerencia."""
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)
    eng.on_clipboard_changed("def suma(a, b): return a + b")  # < 100 chars, una línea
    assert got == []


def test_clipboard_multiline_is_noteworthy():
    """Texto multilínea sustancial (lista/párrafo) sí merece sugerencia."""
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)
    eng.on_clipboard_changed("- comprar pan\n- llamar a Ana\n- terminar informe del proyecto")
    assert len(got) == 1


def test_short_url_is_noteworthy():
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)
    eng.on_clipboard_changed("https://x.io")  # URL corta
    assert len(got) == 1
    assert "enlace" in got[0][0].lower()


def test_focus_survives_tab_change_same_app():
    """Cambiar de pestaña/archivo dentro de la misma app no reinicia el foco."""
    eng = ProactiveEngine(global_cooldown_s=0, focus_gap_s=10, eod_hour=99)
    got = _collect(eng)
    eng.on_active_window_changed("main.py — VS Code")
    eng._focus_since -= 20                       # 20s de foco
    eng.on_active_window_changed("otro.py — VS Code")  # misma app, otra pestaña
    eng.on_tick("otro.py — VS Code", idle_seconds=0)
    assert len(got) == 1                         # el contador NO se reinició


def test_focus_resets_on_real_app_change():
    eng = ProactiveEngine(global_cooldown_s=0, focus_gap_s=10, eod_hour=99)
    got = _collect(eng)
    eng.on_active_window_changed("main.py — VS Code")
    eng._focus_since -= 20
    eng.on_active_window_changed("Bandeja — Chrome")  # app distinta -> reinicia
    eng.on_tick("Bandeja — Chrome", idle_seconds=0)
    assert got == []                             # aún no lleva tiempo en la nueva app


def test_system_monitor_helpers_are_safe():
    # No deben lanzar excepción en ningún SO; devuelven tipos esperados
    assert isinstance(get_active_window_title(), str)
    assert isinstance(get_idle_seconds(), float)
