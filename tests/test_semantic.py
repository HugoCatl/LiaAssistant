"""Tests del índice semántico (Fase 3) con un embebedor stub determinista."""
import os
import numpy as np
from src.services.semantic_index import SemanticIndex


class StubEmbedder:
    """Embebedor determinista: bolsa de palabras sobre un vocabulario fijo.

    Permite verificar la maquinaria (indexado, búsqueda por coseno, incremental)
    sin depender de fastembed ni descargar modelos.
    """
    VOCAB = ["receta", "cocina", "viaje", "japon", "python", "modelo", "ia"]

    def __init__(self):
        self.calls = 0
        self.embedded_count = 0

    def embed(self, texts, is_query: bool = False) -> np.ndarray:
        self.calls += 1
        self.embedded_count += len(texts)
        out = []
        for t in texts:
            tl = t.lower()
            out.append([float(tl.count(w)) for w in self.VOCAB])
        return np.asarray(out, dtype=np.float32)


def _write(vault, name, content):
    path = os.path.join(vault, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _make_vault(tmp_path):
    v = tmp_path / "vault"
    v.mkdir()
    _write(str(v), "Cocina.md", "---\ntags:\n  - casa\n---\nUna receta de cocina sencilla.")
    _write(str(v), "Japon.md", "Notas de mi viaje a japon el proximo verano.")
    _write(str(v), "Proyecto.md", "Un modelo de ia entrenado en python.")
    return str(v)


def test_search_ranks_semantically_closest(tmp_path):
    vault = _make_vault(tmp_path)
    idx = SemanticIndex(vault, StubEmbedder(), cache_dir=str(tmp_path / "cache"))
    idx.build()

    res = idx.search("quiero una receta para cocinar", top_k=3)
    assert res, "no devolvió resultados"
    assert res[0]["title"] == "Cocina"

    res2 = idx.search("entrenar un modelo con python", top_k=3)
    assert res2[0]["title"] == "Proyecto"


def test_snippet_strips_frontmatter(tmp_path):
    vault = _make_vault(tmp_path)
    idx = SemanticIndex(vault, StubEmbedder(), cache_dir=str(tmp_path / "cache"))
    idx.build()
    res = idx.search("receta cocina", top_k=1)
    assert "---" not in res[0]["snippet"]
    assert "receta" in res[0]["snippet"].lower()


def test_incremental_reuses_unchanged(tmp_path):
    vault = _make_vault(tmp_path)
    emb = StubEmbedder()
    idx = SemanticIndex(vault, emb, cache_dir=str(tmp_path / "cache"))
    n = idx.build()
    assert n == 3
    assert emb.embedded_count == 3

    # Segunda construcción sin cambios: no debe volver a embeber nada
    emb.embedded_count = 0
    idx2 = SemanticIndex(vault, emb, cache_dir=str(tmp_path / "cache"))
    idx2.build()
    assert emb.embedded_count == 0, "reembebió notas sin cambios"


def test_incremental_picks_up_changes(tmp_path):
    vault = _make_vault(tmp_path)
    emb = StubEmbedder()
    idx = SemanticIndex(vault, emb, cache_dir=str(tmp_path / "cache"))
    idx.build()

    # Modifica una nota y fuerza un mtime más reciente
    path = _write(vault, "Japon.md", "Cambié de idea: una receta de cocina japonesa.")
    os.utime(path, (os.path.getmtime(path) + 10, os.path.getmtime(path) + 10))

    emb.embedded_count = 0
    idx2 = SemanticIndex(vault, emb, cache_dir=str(tmp_path / "cache"))
    idx2.build()
    assert emb.embedded_count == 1, "debería reembeber solo la nota cambiada"


def test_empty_vault_returns_no_results(tmp_path):
    v = tmp_path / "empty"
    v.mkdir()
    idx = SemanticIndex(str(v), StubEmbedder(), cache_dir=str(tmp_path / "cache"))
    assert idx.search("lo que sea") == []
