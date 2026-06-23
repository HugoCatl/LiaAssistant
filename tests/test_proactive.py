"""Tests del motor proactivo (Fase 2) y los helpers del monitor de sistema."""
from src.services.proactive_engine import ProactiveEngine, _looks_like_url, _short
from src.services.system_monitor import get_active_window_title, get_idle_seconds


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

    eng.on_clipboard_changed("x" * 60)
    assert len(got) == 1
    text, prefill, auto_submit, mood = got[0]
    assert "portapapeles" in prefill.lower()
    assert auto_submit is True
    assert mood == "curious"

    # El mismo texto no se vuelve a sugerir
    got.clear()
    eng.on_clipboard_changed("x" * 60)
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
    eng.on_clipboard_changed("a" * 60)
    eng.on_clipboard_changed("b" * 60)
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
    eng = ProactiveEngine(global_cooldown_s=0)
    got = _collect(eng)
    eng.global_cooldown_s = 300  # activa cooldown tras el rechazo
    eng.record_feedback(accepted=False)
    eng.on_clipboard_changed("c" * 60)
    assert got == []  # bloqueado por el cooldown reforzado


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


def test_system_monitor_helpers_are_safe():
    # No deben lanzar excepción en ningún SO; devuelven tipos esperados
    assert isinstance(get_active_window_title(), str)
    assert isinstance(get_idle_seconds(), float)
