"""Tests del resumen diario (Fase 4)."""
import os
import time
from datetime import date, timedelta

from src.services.daily_summary import _collect_todays_notes, build_activity_report


class StubIndex:
    """Índice falso: devuelve una conexión fija hacia una nota 'anterior'."""
    def __init__(self, related_title="Proyecto IA anterior", score=0.81):
        self.related_title = related_title
        self.score = score

    def search(self, query, top_k=4):
        return [{"title": self.related_title, "score": self.score, "snippet": "..."}]


def _write(vault, name, content, days_ago=0):
    path = os.path.join(vault, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if days_ago:
        t = time.time() - days_ago * 86400
        os.utime(path, (t, t))
    return path


def test_collect_only_todays_notes(tmp_path):
    v = tmp_path / "vault"; v.mkdir(); v = str(v)
    _write(v, "Hoy1.md", "Idea capturada hoy.")
    _write(v, "Hoy2.md", "Otra de hoy.")
    _write(v, "Vieja.md", "De hace una semana.", days_ago=7)

    notes = _collect_todays_notes(v)
    titles = {n["title"] for n in notes}
    assert titles == {"Hoy1", "Hoy2"}


def test_report_includes_notes_and_connections(tmp_path):
    v = tmp_path / "vault"; v.mkdir(); v = str(v)
    _write(v, "Embeddings.md", "Probé embeddings locales con ONNX.")

    report = build_activity_report(v, StubIndex())
    assert "NOTAS CAPTURADAS HOY (1)" in report
    assert "Embeddings" in report
    assert "CONEXIONES CON NOTAS ANTERIORES" in report
    assert "Proyecto IA anterior" in report


def test_report_without_index_has_no_connections(tmp_path):
    v = tmp_path / "vault"; v.mkdir(); v = str(v)
    _write(v, "Sola.md", "Una nota sin índice semántico.")
    report = build_activity_report(v, None)
    assert "NOTAS CAPTURADAS HOY" in report
    assert "CONEXIONES" not in report


def test_connections_exclude_today_and_dedup(tmp_path):
    v = tmp_path / "vault"; v.mkdir(); v = str(v)
    _write(v, "A.md", "nota a de hoy")
    _write(v, "B.md", "nota b de hoy")
    # El índice 'relaciona' todo con A (que es de hoy) -> debe excluirse
    report = build_activity_report(v, StubIndex(related_title="A"))
    assert "CONEXIONES" not in report  # la única conexión apuntaba a una nota de hoy


def test_empty_day(tmp_path):
    v = tmp_path / "vault"; v.mkdir(); v = str(v)
    _write(v, "Vieja.md", "antigua", days_ago=3)
    assert build_activity_report(v, StubIndex()) == "No has capturado ninguna nota hoy."
