"""Tests del enlazado automático de notas, con índice semántico stub."""
import os
import numpy as np
import pytest

from src.services.semantic_index import SemanticIndex
from src.services import auto_link


class StubEmbedder:
    """Bolsa de palabras determinista sobre un vocabulario fijo (sin fastembed)."""
    VOCAB = ["camara", "foto", "proyecto", "viaje", "japon", "receta", "cocina"]

    def embed(self, texts, is_query: bool = False) -> np.ndarray:
        out = []
        for t in texts:
            tl = t.lower()
            out.append([float(tl.count(w)) for w in self.VOCAB])
        return np.asarray(out, dtype=np.float32)


@pytest.fixture
def index(tmp_path, monkeypatch):
    # Reactiva el enlazado (conftest lo desactiva globalmente)
    monkeypatch.delenv("LIA_DISABLE_AUTOLINK", raising=False)
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Camaras IA.md").write_text("Proyecto de camara con foto inteligente.", encoding="utf-8")
    (vault / "Viaje Japon.md").write_text("Notas del viaje a japon.", encoding="utf-8")
    (vault / "Receta.md").write_text("Una receta de cocina.", encoding="utf-8")
    idx = SemanticIndex(str(vault), StubEmbedder(), cache_dir=str(tmp_path / "cache"))
    idx.build()
    return idx


def test_finds_related_by_meaning(index):
    titles = auto_link.find_related_titles(
        "Otra nota sobre una camara y su foto", exclude_title="Nueva", index=index)
    assert "Camaras IA" in titles
    assert "Receta" not in titles      # tema distinto, por debajo del umbral


def test_excludes_self(index):
    titles = auto_link.find_related_titles(
        "camara foto proyecto", exclude_title="Camaras IA", index=index)
    assert "Camaras IA" not in titles


def test_section_format(index):
    section = auto_link.related_section(["Camaras IA", "Otra"])
    assert "## 🔗 Relacionado" in section
    assert "- [[Camaras IA]]" in section
    assert "- [[Otra]]" in section


def test_append_is_idempotent(index):
    body = "Texto sobre camara y foto."
    once = auto_link.append_related_links("Nueva", body, index=index)
    twice = auto_link.append_related_links("Nueva", once, index=index)
    assert once == twice                # no duplica la sección
    assert once.count("## 🔗 Relacionado") == 1


def test_no_related_returns_unchanged(index):
    body = "xyz contenido sin relación alguna con el vocabulario."
    out = auto_link.append_related_links("Nueva", body, index=index)
    assert out == body                  # nada que enlazar


def test_disabled_by_env(index, monkeypatch):
    monkeypatch.setenv("LIA_DISABLE_AUTOLINK", "1")
    assert auto_link.find_related_titles("camara foto", index=index) == []


def test_backlink_written_into_target(index, tmp_path, monkeypatch):
    """append_related_links deja el enlace de vuelta en la nota destino."""
    from unittest.mock import patch as _patch
    from config import settings
    vault = tmp_path / "vault"
    with _patch.object(settings, "obsidian_vault_path", vault):
        out = auto_link.append_related_links(
            "Nueva camara", "Nota sobre una camara y su foto.", index=index)
        assert "[[Camaras IA]]" in out
        target = (vault / "Camaras IA.md").read_text(encoding="utf-8")
        assert "[[Nueva camara]]" in target          # enlace de vuelta real


def test_backlink_is_idempotent(index, tmp_path):
    from unittest.mock import patch as _patch
    from config import settings
    vault = tmp_path / "vault"
    with _patch.object(settings, "obsidian_vault_path", vault):
        assert auto_link.add_backlink("Camaras IA", "Otra nota") is True
        assert auto_link.add_backlink("Camaras IA", "Otra nota") is False  # ya estaba
        body = (vault / "Camaras IA.md").read_text(encoding="utf-8")
        assert body.count("[[Otra nota]]") == 1


def test_backlink_missing_target_is_safe(index, tmp_path):
    from unittest.mock import patch as _patch
    from config import settings
    with _patch.object(settings, "obsidian_vault_path", tmp_path / "vault"):
        assert auto_link.add_backlink("No Existe", "X") is False
