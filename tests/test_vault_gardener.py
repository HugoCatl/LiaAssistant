"""Tests del jardinero del vault (análisis y reparación del grafo)."""
from unittest.mock import patch

import pytest

from config import settings
import src.services.vault_gardener as vg
from src.services.vault_gardener import _scan, analyze, revisar_memoria


@pytest.fixture(autouse=True)
def _isolated_decisions(tmp_path, monkeypatch):
    """Las decisiones del grafo van a un app-data temporal (no al real)."""
    d = tmp_path / "appdata"
    d.mkdir()
    monkeypatch.setattr(vg, "app_data_dir", lambda: d)


def _vault(tmp_path, notes: dict):
    """Crea un vault temporal a partir de {titulo: contenido}."""
    for title, body in notes.items():
        (tmp_path / f"{title}.md").write_text(body, encoding="utf-8")
    return tmp_path


def test_detects_broken_links(tmp_path):
    _vault(tmp_path, {
        "Hugo": "Trabajo con [[Fantasma]].",
        "Guille": "Compañero de [[Hugo]].",
    })
    report = analyze(_scan(tmp_path))
    assert ("Hugo", "Fantasma") in report["broken"]


def test_detects_and_repairs_oneway_links(tmp_path):
    _vault(tmp_path, {
        "Hugo": "Mi jefe es [[Guille]].",
        "Guille": "Jefe de departamento.",   # no enlaza de vuelta
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        report = analyze(_scan(tmp_path))
        assert ("Hugo", "Guille") in report["oneway"]

        out = revisar_memoria()
        assert "Reparados automáticamente 1" in out
        # El backlink quedó escrito de verdad
        assert "[[Hugo]]" in (tmp_path / "Guille.md").read_text(encoding="utf-8")
        # Segunda pasada: ya no hay nada que reparar
        assert "Reparados" not in revisar_memoria()


def test_detects_similar_titles(tmp_path):
    _vault(tmp_path, {
        "Guille": "[[Hugo]]", "Guillermo": "[[Hugo]]", "Hugo": "[[Guille]]",
    })
    report = analyze(_scan(tmp_path))
    assert ("Guille", "Guillermo") in report["similar"]


def test_detects_orphans(tmp_path):
    _vault(tmp_path, {
        "Hugo": "Enlaza a [[Guille]].",
        "Guille": "Enlaza a [[Hugo]].",
        "Suelta": "Nadie me enlaza y no enlazo a nadie.",
    })
    report = analyze(_scan(tmp_path))
    assert report["orphans"] == ["Suelta"]


def test_healthy_graph_reports_clean(tmp_path):
    _vault(tmp_path, {
        "Hugo": "Amigo: [[Guille]].",
        "Guille": "Amigo: [[Hugo]].",
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        out = revisar_memoria()
        assert "sano" in out


def test_links_with_alias_and_anchor(tmp_path):
    _vault(tmp_path, {
        "Hugo": "Ver [[Guille|mi jefe]] y [[Guille#Rol]].",
        "Guille": "[[Hugo]]",
    })
    report = analyze(_scan(tmp_path))
    assert report["broken"] == []       # alias y anclas no cuentan como rotos


def test_tiny_vault_short_circuits(tmp_path):
    _vault(tmp_path, {"Sola": "hola"})
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        assert "muy pocas notas" in revisar_memoria()


def test_distinct_decision_silences_duplicate_question(tmp_path):
    """Tras confirmar que son distintas, la siguiente revisión no lo pregunta."""
    _vault(tmp_path, {
        "Guille": "[[Hugo]]", "Guillermo": "[[Hugo]]", "Hugo": "[[Guille]] [[Guillermo]]",
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        assert "POSIBLES DUPLICADOS" in revisar_memoria()

        msg = vg.marcar_entidades_distintas("Guille", "Guillermo")
        assert "no volveré a preguntarlo" in msg

        assert "POSIBLES DUPLICADOS" not in revisar_memoria()


def test_orphan_decision_silences_orphan_report(tmp_path):
    _vault(tmp_path, {
        "Hugo": "[[Guille]]", "Guille": "[[Hugo]]",
        "Suelta": "sin conexiones a propósito",
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        assert "SIN CONEXIONES" in revisar_memoria()
        vg.ignorar_nota_suelta("Suelta")
        assert "SIN CONEXIONES" not in revisar_memoria()


def test_decisions_persist_across_loads(tmp_path):
    vg.marcar_entidades_distintas("Ana María", "Ana Maria")  # con y sin acento
    d = vg._load_decisions()
    assert ("ana maria", "ana maria") in d["distintas"] or len(d["distintas"]) == 1
    # El archivo existe y es JSON válido
    assert vg._decisions_file().exists()


def test_decision_matching_ignores_case_and_accents(tmp_path):
    _vault(tmp_path, {
        "Óscar": "[[Hugo]]", "Oscar": "[[Hugo]]", "Hugo": "[[Óscar]]",
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        vg.marcar_entidades_distintas("oscar", "óscar")   # en minúsculas
        assert "POSIBLES DUPLICADOS" not in revisar_memoria()
