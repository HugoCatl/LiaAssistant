"""
Búsqueda semántica local sobre el vault de Obsidian (Fase 3 - cerebro).

Indexa las notas (.md) como vectores y permite buscarlas por *significado*, no
por palabra exacta. El embebedor es intercambiable: en producción usa fastembed
(ONNX, ligero, local, multilingüe); en tests se inyecta un stub determinista.

100% local: ni las notas ni las consultas salen de la máquina.
"""
import os
import re
import json
import numpy as np

# Modelo multilingüe ligero (excelente en español, 384 dim, ~0.22GB). ONNX vía fastembed.
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _clean_snippet(text: str, limit: int = 140) -> str:
    body = " ".join(_strip_frontmatter(text).split())
    return body[:limit] + ("…" if len(body) > limit else "")


class FastEmbedEmbedder:
    """Embebedor local basado en fastembed (ONNX). Carga el modelo de forma perezosa."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None

    def _ensure(self):
        if self._model is None:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)

    def embed(self, texts, is_query: bool = False) -> np.ndarray:
        self._ensure()
        # El modelo paraphrase-multilingual no requiere prefijos query:/passage:
        vectors = list(self._model.embed(list(texts)))
        return np.asarray(vectors, dtype=np.float32)


def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class SemanticIndex:
    """
    Índice vectorial de las notas del vault. Reconstrucción incremental por mtime
    y persistencia en disco para no recalcular en cada arranque.
    """

    def __init__(self, vault_path, embedder, cache_dir=None):
        self.vault_path = str(vault_path)
        self.embedder = embedder
        self.cache_dir = cache_dir or os.path.join(self.vault_path, ".lia_index")
        self._meta = []          # lista de dicts: {path, title, mtime, snippet}
        self._vectors = None     # np.ndarray (n, d) alineado con _meta
        self._loaded = False

    # ------------------------------------------------------------- persistencia

    @property
    def _meta_file(self):
        return os.path.join(self.cache_dir, "meta.json")

    @property
    def _vec_file(self):
        return os.path.join(self.cache_dir, "vectors.npy")

    def _load_cache(self):
        if self._loaded:
            return
        try:
            if os.path.exists(self._meta_file) and os.path.exists(self._vec_file):
                with open(self._meta_file, "r", encoding="utf-8") as f:
                    self._meta = json.load(f)
                self._vectors = np.load(self._vec_file)
        except Exception:
            self._meta, self._vectors = [], None
        self._loaded = True

    def _save_cache(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self._meta_file, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False)
        if self._vectors is not None:
            np.save(self._vec_file, self._vectors)

    # ------------------------------------------------------------------ scan

    def _iter_notes(self):
        """Genera (rel_title, abs_path, mtime) por cada .md, excluyendo ocultos."""
        for root, dirs, files in os.walk(self.vault_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                if not fn.endswith(".md") or fn.startswith("."):
                    continue
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, self.vault_path).replace("\\", "/")
                yield rel[:-3], p, os.path.getmtime(p)

    # ------------------------------------------------------------------ build

    def build(self, force: bool = False):
        """Reconstruye el índice de forma incremental (solo notas nuevas/cambiadas)."""
        self._load_cache()
        prev = {} if force else {m["path"]: (m, i) for i, m in enumerate(self._meta)}

        new_meta = []
        reuse_rows = []   # (índice_destino, fila_en_vectores_previos) para reusar
        to_embed = []     # (índice_destino, texto)

        for title, path, mtime in self._iter_notes():
            dest = len(new_meta)
            cached = prev.get(path)
            if cached and abs(cached[0].get("mtime", -1) - mtime) < 1e-6 and self._vectors is not None:
                meta = dict(cached[0])
                new_meta.append(meta)
                reuse_rows.append((dest, cached[1]))
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue
                text = f"{title}\n{_strip_frontmatter(content)}"[:2000]
                new_meta.append({
                    "path": path, "title": title, "mtime": mtime,
                    "snippet": _clean_snippet(content),
                })
                to_embed.append((dest, text))

        if not new_meta:
            self._meta, self._vectors = [], None
            self._save_cache()
            return 0

        dim = self._vectors.shape[1] if self._vectors is not None and len(self._vectors) else None
        new_vecs = None
        if to_embed:
            embedded = self.embedder.embed([t for _, t in to_embed])
            dim = embedded.shape[1]
        # Reserva la matriz final una vez conocida la dimensión
        if dim is None:
            self._meta, self._vectors = [], None
            self._save_cache()
            return 0
        new_vecs = np.zeros((len(new_meta), dim), dtype=np.float32)
        for (dest, _), row in zip(to_embed, range(len(to_embed))):
            new_vecs[dest] = embedded[row]
        for dest, src in reuse_rows:
            new_vecs[dest] = self._vectors[src]

        self._meta = new_meta
        self._vectors = new_vecs
        self._save_cache()
        return len(new_meta)

    # ------------------------------------------------------------------ search

    def search(self, query: str, top_k: int = 5):
        """Devuelve las notas más cercanas semánticamente: [{title, score, snippet}]."""
        # Build incremental en cada búsqueda: barato si nada cambió (solo stats de
        # mtime + reutiliza vectores), y mantiene el índice fresco ante notas nuevas.
        self.build()
        if self._vectors is None or not len(self._meta):
            return []

        qv = self.embedder.embed([query], is_query=True)
        qn = _normalize(qv)[0]
        mat = _normalize(self._vectors)
        scores = mat @ qn
        order = np.argsort(-scores)[:top_k]
        return [
            {
                "title": self._meta[i]["title"],
                "score": float(scores[i]),
                "snippet": self._meta[i]["snippet"],
            }
            for i in order
        ]
