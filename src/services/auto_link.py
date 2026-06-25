"""
Enlazado automático de notas (segundo cerebro).

Cuando se crea una nota, busca por SIGNIFICADO las notas existentes más afines
(reutilizando el índice semántico) y añade una pequeña sección «Relacionado» con
enlaces `[[ ]]`. Así el vault teje conexiones solo, sin que el usuario las cree a
mano. En Obsidian, esos enlaces se ven también como backlinks en la nota destino
(navegación bidireccional gratis).
"""
import os

_MIN_SCORE = 0.40          # afinidad mínima (coseno) para considerar relacionada
_TOP_K = 3                 # cuántos enlaces añadir como máximo
_SECTION_HEADER = "## 🔗 Relacionado"


def _basename(title: str) -> str:
    return (title or "").rsplit("/", 1)[-1]


def find_related_titles(text, exclude_title=None, top_k=_TOP_K,
                        min_score=_MIN_SCORE, index=None):
    """Títulos de notas semánticamente afines a `text`, excluyendo la propia."""
    if os.getenv("LIA_DISABLE_AUTOLINK"):
        return []
    try:
        if index is None:
            from src.services.semantic_search import _get_index
            index = _get_index()
        index.build()
        results = index.search(text, top_k=top_k + 4)
    except Exception:
        return []

    ex = _basename(exclude_title).strip().lower()
    seen, out = set(), []
    for r in results:
        name = _basename(r.get("title", ""))
        key = name.lower()
        if not name or key == ex or key in seen:
            continue
        if r.get("score", 0.0) >= min_score:
            seen.add(key)
            out.append(name)
        if len(out) >= top_k:
            break
    return out


def related_section(titles) -> str:
    """Construye el bloque Markdown de notas relacionadas (vacío si no hay)."""
    if not titles:
        return ""
    links = "\n".join(f"- [[{t}]]" for t in titles)
    return f"\n\n{_SECTION_HEADER}\n{links}\n"


def append_related_links(title, content, index=None) -> str:
    """Devuelve `content` con la sección de relacionadas (o igual si no hay/ya está)."""
    if _SECTION_HEADER in content:
        return content
    titles = find_related_titles(f"{title}\n{content}", exclude_title=title, index=index)
    return content + related_section(titles)
