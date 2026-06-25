"""Tests de la edición fina de notas (editar_nota)."""
from unittest.mock import patch

import pytest

from config import settings
from src.storage.obsidian_manager import editar_nota


def test_replaces_only_target_fragment(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        note = tmp_path / "Proyecto cámaras.md"
        note.write_text(
            "---\ntags:\n  - proyecto\n---\n\n"
            "Resumen del proyecto.\nentrega: febrero\nEquipo: Ana y Juan.\n",
            encoding="utf-8",
        )
        res = editar_nota("Proyecto cámaras", "entrega: febrero", "entrega: marzo")
        assert "editada" in res
        body = note.read_text(encoding="utf-8")
        assert "entrega: marzo" in body
        assert "entrega: febrero" not in body
        assert "Equipo: Ana y Juan." in body   # el resto intacto
        assert "tags:" in body                  # frontmatter intacto


def test_fragment_not_found_changes_nothing(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        note = tmp_path / "Notas.md"
        note.write_text("contenido original", encoding="utf-8")
        res = editar_nota("Notas", "no existe", "x")
        assert "No se encontró el fragmento" in res
        assert note.read_text(encoding="utf-8") == "contenido original"


def test_note_not_found(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        assert "No se encontró la nota" in editar_nota("Inexistente", "a", "b")


def test_reports_multiple_occurrences(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        note = tmp_path / "Lista.md"
        note.write_text("foo\nfoo\nfoo", encoding="utf-8")
        res = editar_nota("Lista", "foo", "bar")
        assert "3 coincidencias" in res
        assert note.read_text(encoding="utf-8") == "bar\nbar\nbar"


def test_case_insensitive_title_match(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        note = tmp_path / "Diario.md"
        note.write_text("hola mundo", encoding="utf-8")
        res = editar_nota("diario", "mundo", "Hugo")
        assert "editada" in res
        assert note.read_text(encoding="utf-8") == "hola Hugo"


def test_empty_search_is_rejected(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        assert "no puede estar vacío" in editar_nota("X", "", "y")
