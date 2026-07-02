"""Tests de la ficha de entidad (agregación de todo lo sabido sobre X)."""
from unittest.mock import patch

from config import settings
from src.services.entity_card import ficha_entidad, _mentions


def _vault(tmp_path, notes: dict):
    for title, body in notes.items():
        (tmp_path / f"{title}.md").write_text(body, encoding="utf-8")
    return tmp_path


def test_aggregates_note_and_mentions(tmp_path):
    _vault(tmp_path, {
        "Guille": "Jefe de departamento en [[Ahora Soluciones]].",
        "Hugo": "Mi jefe es [[Guille]] y es buen tío.",
        "Reunion lunes": "Guille pidió el informe para el viernes.",
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        out = ficha_entidad("Guille")
    assert "FICHA DE «Guille»" in out
    assert "Jefe de departamento" in out          # su nota
    assert "Mi jefe es [[Guille]]" in out         # mención con enlace
    assert "pidió el informe" in out              # mención sin enlace, por nombre


def test_fuzzy_resolution_finds_similar(tmp_path):
    _vault(tmp_path, {"Guillermo": "Compañero de trabajo."})
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        out = ficha_entidad("Guille")
    assert "FICHA DE «Guillermo»" in out
    assert "Compañero de trabajo" in out


def test_unknown_entity(tmp_path):
    _vault(tmp_path, {"Hugo": "hola"})
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        out = ficha_entidad("Voldemort")
    assert "No encontré nada" in out


def test_mentions_skip_own_note_and_respect_limits(tmp_path):
    _vault(tmp_path, {
        "Ana": "Ana es diseñadora.",           # su propia nota: no cuenta como mención
        "Proyecto": "Ana lidera el diseño.\nAna revisó los mockups.\n"
                    "Ana aprobó la paleta.\nAna hizo otra cosa más.",
    })
    found = _mentions(tmp_path, "Ana")
    assert len(found) == 1
    title, lines = found[0]
    assert title == "Proyecto"
    assert len(lines) == 3                     # tope de líneas por nota


def test_strips_frontmatter_from_own_note(tmp_path):
    _vault(tmp_path, {
        "Nisa": "---\ndate: 2026-01-01\ntags:\n  - persona\n---\n\nCompañera de equipo.",
        "Hugo": "Trabajo con [[Nisa]].",
    })
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        out = ficha_entidad("Nisa")
    assert "Compañera de equipo" in out
    assert "date: 2026" not in out
