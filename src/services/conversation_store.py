"""
Persistencia del historial conversacional entre sesiones.

Guarda los turnos como [{role, text}] en JSON (app-data). No persiste las
llamadas a herramientas, solo el texto de usuario y de Lia, suficiente para
recuperar el contexto reciente al reabrir.
"""
import json

from config.paths import app_data_dir

_FILE = app_data_dir() / "history.json"


def save_turns(turns: list):
    try:
        _FILE.write_text(json.dumps(turns, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_turns() -> list:
    if _FILE.exists():
        try:
            data = json.loads(_FILE.read_text(encoding="utf-8"))
            return [t for t in data if t.get("role") in ("user", "model") and t.get("text")]
        except Exception:
            return []
    return []


def clear():
    try:
        if _FILE.exists():
            _FILE.unlink()
    except Exception:
        pass
