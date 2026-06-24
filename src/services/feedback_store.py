"""
Almacén local del feedback proactivo (Sí/Ahora no) — base del modelo que aprende.

Persiste en SQLite bajo el directorio de datos del usuario, fuera del código, así
sobrevive a actualizaciones de la app. 100% local.

Esquema:
    suggestions(id, ts, kind, features_json, accepted)
        kind: 'clipboard'|'focus'|'note_gap'|'eod'|'demo'
        features_json: JSON con las features simples (hora, longitud, etc.)
        accepted: 1 si aceptó, 0 si descartó
"""
import os
import json
import sqlite3
import time
from typing import Optional


def _default_db_path() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "LiaAssistant")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "feedback.db")


class FeedbackStore:
    """Persistencia ligera del feedback de sugerencias proactivas."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _default_db_path()
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self):
        with self._connect() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    kind TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    accepted INTEGER NOT NULL
                )
            """)

    def record(self, kind: str, features: dict, accepted: bool) -> int:
        with self._connect() as c:
            cur = c.execute(
                "INSERT INTO suggestions(ts, kind, features_json, accepted) VALUES (?, ?, ?, ?)",
                (time.time(), kind, json.dumps(features, ensure_ascii=False), int(bool(accepted))),
            )
            return cur.lastrowid

    def all_examples(self):
        """Devuelve [(kind, features_dict, accepted_bool)] ordenados por ts ascendente."""
        with self._connect() as c:
            rows = c.execute(
                "SELECT kind, features_json, accepted FROM suggestions ORDER BY ts ASC"
            ).fetchall()
        return [(k, json.loads(fj), bool(a)) for k, fj, a in rows]

    def count(self) -> int:
        with self._connect() as c:
            return c.execute("SELECT COUNT(*) FROM suggestions").fetchone()[0]
