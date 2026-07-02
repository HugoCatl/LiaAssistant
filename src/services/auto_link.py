"""
Enlazado automático de notas (segundo cerebro).

Cuando se crea una nota, busca por SIGNIFICADO las notas existentes más afines
(reutilizando el índice semántico) y añade una pequeña sección «Relacionado» con
enlaces `[[ ]]`. Así el vault teje conexiones solo, sin que el usuario las cree a
mano. En Obsidian, esos enlaces se ven también como backlinks en la nota destino
(navegación bidireccional gratis).
"""
import os
import logging

_log = logging.getLogger("lia")
_warned_index_failure = False  # avisar una sola vez si el índice no funciona

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
    except Exception as e:
        # No romper la creación de la nota, pero dejar rastro (una vez): si el
        # modelo de embeddings no carga, el auto-enlazado deja de funcionar y
        # sin este log nadie se enteraría jamás.
        global _warned_index_failure
        if not _warned_index_failure:
            _warned_index_failure = True
            _log.warning("Auto-enlazado desactivado: el índice semántico falló (%s)", e)
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


def add_backlink(target_title: str, new_title: str) -> bool:
    """
    Añade `[[new_title]]` a la sección Relacionado de la nota destino, para que
    el enlace sea bidireccional DE VERDAD en el .md (no solo en el panel de
    backlinks de Obsidian). Idempotente; nunca lanza. Devuelve si escribió algo.
    """
    try:
        from src.storage.obsidian_manager import (
            get_vault_path, _resolve_note_path, _atomic_write,
        )
        path = _resolve_note_path(get_vault_path(), target_title)
        if path is None:
            return False
        body = path.read_text(encoding="utf-8")
        if f"[[{new_title}]]" in body:
            return False  # ya enlaza (en cualquier parte de la nota)
        bullet = f"- [[{new_title}]]"
        if _SECTION_HEADER in body:
            # Inserta el bullet justo debajo de la cabecera de la sección
            body = body.replace(_SECTION_HEADER, f"{_SECTION_HEADER}\n{bullet}", 1)
        else:
            body = body.rstrip("\n") + f"\n\n{_SECTION_HEADER}\n{bullet}\n"
        _atomic_write(path, body)
        return True
    except Exception as e:
        _log.warning("No pude añadir el backlink [[%s]] en '%s': %s", new_title, target_title, e)
        return False


def append_related_links(title, content, index=None) -> str:
    """
    Devuelve `content` con la sección de relacionadas (o igual si no hay/ya está)
    y, como efecto lateral, añade el enlace de VUELTA en cada nota destino.
    """
    if _SECTION_HEADER in content:
        return content
    titles = find_related_titles(f"{title}\n{content}", exclude_title=title, index=index)
    for t in titles:
        add_backlink(t, title)
    return content + related_section(titles)
