"""
Ficha de entidad (Fase 10): todo lo que se sabe de una persona/empresa/proyecto.

La información de una entidad vive dispersa: su propia nota, menciones sueltas en
otras notas y notas afines por significado. Esta herramienta la agrega en un solo
informe (determinista, sin LLM) para que Gemini la sintetice al estilo
"cuéntame sobre Guille".
"""
import os
import re
import logging

from src.storage.obsidian_manager import (
    get_vault_path, _resolve_note_path, _similar_existing_title, _fold,
)

_log = logging.getLogger("lia")

_MAX_NOTES = 10        # máx. de notas con menciones a incluir
_MAX_LINES_PER_NOTE = 3


def _mentions(vault, entity_title: str):
    """Líneas de OTRAS notas que mencionan a la entidad (por nombre o [[enlace]])."""
    needle = _fold(entity_title)
    found = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("."):
                continue
            title = fn[:-3]
            if _fold(title) == needle:
                continue  # su propia nota va aparte
            try:
                with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                    body = f.read()
            except Exception:
                continue
            lines = [
                ln.strip() for ln in body.splitlines()
                if ln.strip() and needle in _fold(ln)
            ][:_MAX_LINES_PER_NOTE]
            if lines:
                found.append((title, lines))
            if len(found) >= _MAX_NOTES:
                return found
    return found


def ficha_entidad(nombre: str) -> str:
    """
    Reúne TODO lo que el usuario sabe sobre una persona, empresa, proyecto o
    lugar concreto: su nota propia, las menciones en el resto de notas y las
    notas relacionadas por significado. Úsala cuando pregunte por una entidad
    concreta: "cuéntame sobre X", "qué sabes de X", "quién es X".

    Args:
        nombre: El nombre de la entidad (persona, empresa, proyecto, lugar).

    Returns:
        Informe agregado para redactar la respuesta.
    """
    try:
        vault = get_vault_path()
    except Exception as e:
        return f"No pude acceder a la memoria: {e}"

    # Resolver la nota propia (exacta o casi: 'Guille' encuentra 'Guillermo')
    path = _resolve_note_path(vault, nombre)
    resolved = path.stem if path else _similar_existing_title(vault, nombre)
    if path is None and resolved:
        path = _resolve_note_path(vault, resolved)
    title = path.stem if path else nombre

    lines = [f"FICHA DE «{title}»:"]
    found = False

    if path is not None:
        try:
            body = path.read_text(encoding="utf-8")
            body = re.sub(r"^---\n.*?\n---\n", "", body, count=1, flags=re.DOTALL)
            lines.append(f"SU NOTA:\n{body.strip()[:1500]}")
            found = True
        except Exception:
            pass

    mentions = _mentions(vault, title)
    if mentions:
        det = "\n".join(
            f"- En '{note}': " + " | ".join(ls) for note, ls in mentions
        )
        lines.append(f"MENCIONES EN OTRAS NOTAS:\n{det}")
        found = True

    # Afines por significado (contexto extra que no la menciona literalmente)
    try:
        from src.services.semantic_search import _get_index
        related = _get_index().search(title, top_k=4, min_score=0.35)
        rel = [r["title"] for r in related if _fold(r["title"]) != _fold(title)]
        if rel:
            lines.append("NOTAS RELACIONADAS POR SIGNIFICADO: " + ", ".join(rel))
    except Exception:
        pass

    if not found:
        return (f"No encontré nada sobre «{nombre}» en la memoria del usuario. "
                "Dile que aún no le ha contado nada de esa entidad.")
    return "\n\n".join(lines)
