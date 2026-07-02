"""
Jardinero del vault (Fase 7): revisa y repara el grafo de conocimiento.

El grafo se construye turno a turno con el LLM; si un turno se corta a mitad o
el modelo olvida un paso, el grafo queda incoherente en silencio. Este módulo
hace un pase de mantenimiento SIN LLM (determinista, sin tokens):

  - REPARA solo: enlaces de un solo sentido (A→B sin B→A) añadiendo el backlink.
  - REPORTA lo que requiere criterio: enlaces rotos, títulos casi duplicados
    (posible misma entidad) y notas huérfanas (sin conexiones).

Se expone como herramienta `revisar_memoria()` para que Gemini la invoque cuando
el usuario pida revisar/ordenar/limpiar su memoria, y presente el informe.
"""
import os
import re
import json
import logging
from difflib import SequenceMatcher

from config.paths import app_data_dir
from src.storage.obsidian_manager import get_vault_path, _fold

_log = logging.getLogger("lia")


# ------------------------- memoria de decisiones del usuario -------------------------
# Cuando el usuario ya respondió ("Guille y Guillermo son personas distintas",
# "deja esa nota sin conexiones"), el jardinero NO debe volver a preguntarlo.

def _decisions_file():
    return app_data_dir() / "graph_decisions.json"


def _load_decisions() -> dict:
    try:
        f = _decisions_file()
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            return {
                "distintas": {tuple(sorted(p)) for p in data.get("distintas", [])},
                "sueltas_ok": set(data.get("sueltas_ok", [])),
            }
    except Exception:
        pass
    return {"distintas": set(), "sueltas_ok": set()}


def _save_decisions(d: dict):
    try:
        _decisions_file().write_text(json.dumps({
            "distintas": [list(p) for p in sorted(d["distintas"])],
            "sueltas_ok": sorted(d["sueltas_ok"]),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        _log.warning("No pude guardar las decisiones del grafo: %s", e)


def marcar_entidades_distintas(nombre_a: str, nombre_b: str) -> str:
    """
    Registra que dos notas con nombre parecido son ENTIDADES DISTINTAS (lo
    confirmó el usuario), para que la revisión de memoria no vuelva a preguntar
    por ese par. Úsala cuando, ante un posible duplicado, el usuario diga que
    son personas/cosas diferentes.

    Args:
        nombre_a: Título de la primera nota.
        nombre_b: Título de la segunda nota.
    """
    d = _load_decisions()
    d["distintas"].add(tuple(sorted((_fold(nombre_a), _fold(nombre_b)))))
    _save_decisions(d)
    return (f"Anotado: «{nombre_a}» y «{nombre_b}» son entidades distintas; "
            "no volveré a preguntarlo.")


def ignorar_nota_suelta(titulo: str) -> str:
    """
    Registra que el usuario quiere dejar una nota SIN conexiones a propósito,
    para que la revisión de memoria deje de señalarla como suelta.

    Args:
        titulo: Título de la nota que debe quedarse sin conexiones.
    """
    d = _load_decisions()
    d["sueltas_ok"].add(_fold(titulo))
    _save_decisions(d)
    return f"Anotado: la nota «{titulo}» se queda sin conexiones a propósito."

# [[Titulo]], [[Titulo|alias]], [[Titulo#seccion]] -> captura solo el título
_LINK_RE = re.compile(r"\[\[([^\]|#]+)")

_SIMILAR_THRESHOLD = 0.78


def _scan(vault) -> dict:
    """Lee el vault: {titulo: {"path": Path, "links": set de títulos enlazados}}."""
    notes = {}
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("."):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    body = f.read()
            except Exception:
                continue
            title = fn[:-3]
            links = {m.strip() for m in _LINK_RE.findall(body) if m.strip()}
            notes[title] = {"path": path, "links": links}
    return notes


def analyze(notes: dict) -> dict:
    """
    Analiza el grafo. Devuelve:
      broken:   [(nota, enlace_roto)]     — [[X]] hacia una nota que no existe
      oneway:   [(origen, destino)]       — A enlaza a B pero B no enlaza a A
      similar:  [(titulo_a, titulo_b)]    — títulos casi idénticos (¿misma entidad?)
      orphans:  [titulo]                  — sin enlaces de entrada ni salida
    """
    by_fold = {_fold(t): t for t in notes}
    linked_from = {t: set() for t in notes}  # quién enlaza a cada nota

    broken, oneway = [], []
    for title, info in notes.items():
        for link in info["links"]:
            real = by_fold.get(_fold(link))
            if real is None:
                broken.append((title, link))
            elif real != title:
                linked_from[real].add(title)

    for title, info in notes.items():
        for link in info["links"]:
            real = by_fold.get(_fold(link))
            if real and real != title and title not in {
                by_fold.get(_fold(l)) for l in notes[real]["links"]
            }:
                oneway.append((title, real))

    titles = sorted(notes)
    similar = []
    for i, a in enumerate(titles):
        for b in titles[i + 1:]:
            if SequenceMatcher(None, _fold(a), _fold(b)).ratio() >= _SIMILAR_THRESHOLD:
                similar.append((a, b))

    orphans = [
        t for t in titles
        if not notes[t]["links"] and not linked_from[t]
    ]
    return {"broken": broken, "oneway": oneway, "similar": similar, "orphans": orphans}


def revisar_memoria() -> str:
    """
    Revisa y repara la memoria del usuario (su red de notas). Úsala cuando pida
    revisar, ordenar, limpiar u organizar su memoria/notas/conexiones.

    Repara automáticamente los enlaces de un solo sentido y devuelve un informe
    con lo que requiere decisión: enlaces rotos, posibles notas duplicadas de la
    misma entidad y notas sin conexiones.

    Returns:
        Informe en texto del estado del grafo y de las reparaciones hechas.
    """
    try:
        vault = get_vault_path()
        notes = _scan(vault)
    except Exception as e:
        return f"No pude revisar la memoria: {e}"

    if len(notes) < 2:
        return "La memoria aún tiene muy pocas notas; no hay nada que revisar."

    report = analyze(notes)

    # Respetar las decisiones previas del usuario (no volver a preguntar)
    decisions = _load_decisions()
    report["similar"] = [
        (a, b) for a, b in report["similar"]
        if tuple(sorted((_fold(a), _fold(b)))) not in decisions["distintas"]
    ]
    report["orphans"] = [
        t for t in report["orphans"] if _fold(t) not in decisions["sueltas_ok"]
    ]

    # Reparación automática segura: completar enlaces de un solo sentido
    fixed = 0
    from src.services.auto_link import add_backlink
    for origen, destino in report["oneway"]:
        if add_backlink(destino, origen):
            fixed += 1

    lines = [f"REVISIÓN DE LA MEMORIA ({len(notes)} notas):"]
    if fixed:
        lines.append(f"- Reparados automáticamente {fixed} enlaces que solo iban en un sentido.")
    if report["broken"]:
        det = "; ".join(f"'{n}' enlaza a «{l}» que no existe" for n, l in report["broken"][:8])
        lines.append(f"- ENLACES ROTOS ({len(report['broken'])}): {det}. "
                     "Sugiere crear la nota que falta o corregir el enlace con editar_nota.")
    if report["similar"]:
        det = "; ".join(f"«{a}» y «{b}»" for a, b in report["similar"][:8])
        lines.append(f"- POSIBLES DUPLICADOS ({len(report['similar'])}): {det}. "
                     "Pregunta al usuario si son la misma entidad antes de fusionar.")
    if report["orphans"]:
        det = ", ".join(report["orphans"][:10])
        lines.append(f"- NOTAS SIN CONEXIONES ({len(report['orphans'])}): {det}. "
                     "Ofrece enlazarlas a las notas relacionadas.")
    if len(lines) == 1 or (len(lines) == 2 and fixed):
        lines.append("- El grafo está sano: sin enlaces rotos, duplicados ni notas sueltas.")

    _log.info("Jardinero: %d notas, %d backlinks reparados, %d rotos, %d similares, %d huérfanas",
              len(notes), fixed, len(report["broken"]), len(report["similar"]),
              len(report["orphans"]))
    return "\n".join(lines)
