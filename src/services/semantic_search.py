"""
Herramienta de búsqueda semántica para el asistente: envuelve SemanticIndex con
el embebedor real (fastembed) y un singleton por vault. Si el modelo no está
disponible, cae a la búsqueda por palabra clave.
"""
from src.storage.obsidian_manager import get_vault_path, search_notes
from src.services.semantic_index import SemanticIndex, FastEmbedEmbedder

_index = None


def _get_index() -> SemanticIndex:
    global _index
    if _index is None:
        _index = SemanticIndex(str(get_vault_path()), FastEmbedEmbedder())
    return _index


def search_notes_semantic(query: str) -> list:
    """
    Busca en las notas del usuario por SIGNIFICADO (búsqueda semántica), no por
    coincidencia literal de palabras. Úsala para preguntas conceptuales, sinónimos
    o cuando 'search_notes' no encuentre nada por palabra exacta.

    Args:
        query: La pregunta o tema a buscar en la memoria del usuario.

    Returns:
        Lista de notas relevantes, cada una con su título y un fragmento.
    """
    try:
        idx = _get_index()
        idx.build()  # incremental: barato si no hay notas nuevas/cambiadas
        # Umbral de relevancia: mejor decir "no encontré nada" que presentar
        # como relevantes las notas menos lejanas de un vault que no habla de eso.
        results = idx.search(query, top_k=5, min_score=0.30)
        if not results:
            return ["No se encontraron notas relevantes sobre eso en la memoria del usuario."]
        return [
            f"Nota: '{r['title']}' (afinidad {r['score']:.2f}) - {r['snippet']}"
            for r in results
        ]
    except Exception as e:
        # Fallback robusto: si fastembed/el modelo no está, usa búsqueda por palabra
        try:
            return search_notes(query)
        except Exception:
            return [f"Error en la búsqueda semántica: {e}"]
