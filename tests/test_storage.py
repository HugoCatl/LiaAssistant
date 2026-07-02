import os
import pytest
from unittest.mock import patch
from pathlib import Path
from config import settings
from src.storage.obsidian_manager import (
    sanitize_filename,
    create_note,
    read_note,
    search_notes,
    write_note,
    append_to_note
)

def test_sanitize_filename():
    assert sanitize_filename("Nota: Especial *") == "Nota Especial"
    assert sanitize_filename('¿Qué es esto? "LIA"') == "¿Qué es esto LIA"
    assert sanitize_filename("../../../malicioso") == "......malicioso"

def test_create_note_lifecycle(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        res = create_note("Prueba", "Contenido de la nota", ["test", "lia"])
        assert "Nota creada exitosamente" in res
        
        note_file = tmp_path / "Prueba.md"
        assert note_file.exists()
        
        content = note_file.read_text(encoding="utf-8")
        assert "tags:" in content
        assert "  - test" in content
        assert "  - lia" in content
        assert "Contenido de la nota" in content

def test_create_note_duplicate_safeguard(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("Duplicado", "Original")
        res = create_note("Duplicado", "Nuevo")
        assert "Error:" in res
        assert "ya existe" in res

        files = list(tmp_path.glob("Duplicado*"))
        assert len(files) == 1

def test_read_note_case_insensitive(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("MiNotaEspecial", "Texto secreto")
        
        content = read_note("minotaespecial")
        assert "Texto secreto" in content

def test_search_notes(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("Receta Cafe", "Comprar granos de cafe molido")
        create_note("Lista de Compras", "Comprar leche y huevos")
        create_note("Apuntes", "Aprender desarrollo de software")

        # Búsqueda coincidente con minúsculas/mayúsculas
        res = search_notes("cafe")
        assert len(res) == 1
        assert "Receta Cafe" in res[0]
        
        res_comprar = search_notes("Comprar")
        assert len(res_comprar) == 2

def test_write_note_overwrite(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        # Write initial note
        res = write_note("TestOver", "Contenido inicial", ["v1"])
        assert "escrita/actualizada con éxito" in res
        
        # Overwrite note
        res2 = write_note("testover", "Contenido modificado", ["v2"])
        assert "escrita/actualizada con éxito" in res2
        
        # Verify content has changed and we still have only 1 file
        files = list(tmp_path.glob("TestOver*"))
        assert len(files) == 1
        
        content = read_note("TestOver")
        assert "Contenido modificado" in content
        assert "  - v2" in content
        assert "Contenido inicial" not in content

def test_append_to_note(tmp_path):
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        # Append to non-existing note (should create it)
        res = append_to_note("TestAppend", "Primera linea")
        assert "Nota creada exitosamente" in res
        
        # Append to existing note
        res2 = append_to_note("testappend", "Segunda linea")
        assert "Contenido añadido con éxito" in res2
        
        # Try appending duplicate text (should block it)
        res3 = append_to_note("TestAppend", "Primera linea")
        assert "Información ya presente" in res3
        
        # Verify segments exist in note and no duplication occurred
        content = read_note("TestAppend")
        assert "Primera linea" in content
        assert "Segunda linea" in content
        assert content.count("Primera linea") == 1


def test_atomic_write_leaves_no_tmp_and_preserves_content(tmp_path):
    """La escritura atómica no deja temporales y el append conserva lo previo."""
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("Atomica", "linea original")
        append_to_note("Atomica", "linea nueva")
        body = (tmp_path / "Atomica.md").read_text(encoding="utf-8")
        assert "linea original" in body and "linea nueva" in body
        leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []


def test_create_note_blocks_similar_title(tmp_path):
    """'Guillermo' con 'Guille' existente -> avisa en vez de duplicar la entidad."""
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("Guille", "Mi amigo del trabajo")
        res = create_note("Guillermo", "Jefe de departamento")
        assert "muy parecido" in res and "Guille" in res
        assert not (tmp_path / "Guillermo.md").exists()


def test_create_note_similar_escape_hatch(tmp_path):
    """permitir_similar=True crea la nota aunque haya una parecida."""
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("Guille", "persona A")
        res = create_note("Guillermo", "persona B", permitir_similar=True)
        assert "exitosamente" in res
        assert (tmp_path / "Guillermo.md").exists()


def test_create_note_distinct_titles_not_blocked(tmp_path):
    """Títulos realmente distintos (Ana vs Mariana) no se bloquean."""
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        create_note("Ana", "amiga")
        res = create_note("Mariana", "compañera")
        assert "exitosamente" in res


def test_note_context_reads_frontmatter_tag(tmp_path):
    from src.storage.obsidian_manager import _note_context
    with patch.object(settings, "obsidian_vault_path", tmp_path):
        (tmp_path / "Empresa.md").write_text(
            "---\ntags:\n  - contexto/trabajo\n---\ncontenido", encoding="utf-8")
        (tmp_path / "Hobby.md").write_text("sin frontmatter", encoding="utf-8")
        assert _note_context(tmp_path, "Empresa") == "trabajo"
        assert _note_context(tmp_path, "Hobby") is None
        assert _note_context(tmp_path, "NoExiste") is None
