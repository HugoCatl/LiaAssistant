"""
Resumen diario (Fase 4 - cierre del bucle del segundo cerebro).

Recopila las notas que el usuario ha capturado HOY y, usando la búsqueda
semántica, descubre con qué notas anteriores conectan. Devuelve un informe de
texto estructurado.

Patrón de diseño: esta es una HERRAMIENTA que da DATOS al LLM. No llama al modelo
de lenguaje (eso sería recursión/coste): es Gemini quien, con estos datos, redacta
el digest final y lo guarda como nota 'Diario AAAA-MM-DD'.
"""
import os
from datetime import date

from src.storage.obsidian_manager import get_vault_path
from src.services.semantic_index import _clean_snippet

# Máximo de conexiones sugeridas por nota (para no saturar el contexto del LLM)
_MAX_LINKS_PER_NOTE = 2


def _collect_todays_notes(vault_path: str, on_date: date = None) -> list:
    """Devuelve las notas .md cuyo mtime cae en la fecha dada (hoy por defecto)."""
    on = on_date or date.today()
    notes = []
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("."):
                continue
            p = os.path.join(root, fn)
            try:
                mtime = os.path.getmtime(p)
                if date.fromtimestamp(mtime) != on:
                    continue
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            rel = os.path.relpath(p, vault_path).replace("\\", "/")
            notes.append({
                "title": rel[:-3],
                "snippet": _clean_snippet(content),
                "mtime": mtime,
            })
    notes.sort(key=lambda n: n["mtime"])
    return notes


def build_activity_report(vault_path: str, index, on_date: date = None) -> str:
    """
    Construye el informe de actividad del día: notas capturadas + conexiones
    semánticas con notas anteriores. 'index' puede ser None (sin conexiones).
    """
    notes = _collect_todays_notes(vault_path, on_date)
    if not notes:
        return "No has capturado ninguna nota hoy."

    today_titles = {n["title"] for n in notes}
    lines = [f"NOTAS CAPTURADAS HOY ({len(notes)}):"]
    for n in notes:
        lines.append(f"- {n['title']}: {n['snippet']}")

    connections = []
    seen_pairs = set()
    if index is not None:
        for n in notes:
            try:
                related = index.search(f"{n['title']} {n['snippet']}", top_k=4)
            except Exception:
                related = []
            added = 0
            for r in related:
                if r["title"] in today_titles or added >= _MAX_LINKS_PER_NOTE:
                    continue
                pair = tuple(sorted((n["title"], r["title"])))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                connections.append(
                    f"- «{n['title']}» conecta con «{r['title']}» "
                    f"(afinidad {r['score']:.2f})"
                )
                added += 1

    if connections:
        lines.append("\nCONEXIONES CON NOTAS ANTERIORES:")
        lines.extend(connections)

    return "\n".join(lines)


def get_todays_activity() -> str:
    """
    Devuelve un informe con las notas que el usuario ha capturado HOY y sus
    conexiones con notas anteriores. Úsala cuando el usuario pida un resumen de su
    día, un diario o un repaso de lo que hizo. Tras llamarla, redacta un resumen
    estructurado (temas, logros, conexiones) y guárdalo como una nota de diario.

    Returns:
        Informe de texto con las notas de hoy y sus conexiones semánticas.
    """
    try:
        vault = str(get_vault_path())
    except Exception as e:
        return f"No puedo acceder al vault: {e}"

    index = None
    try:
        from src.services.semantic_search import _get_index
        index = _get_index()
        index.build()  # incremental: barato si nada cambió
    except Exception:
        index = None  # sin conexiones si los embeddings no están disponibles

    return build_activity_report(vault, index)
