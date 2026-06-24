"""
Clustering de temas (Fase 3 - cerebro, parte B).

Agrupa las notas del vault en temas latentes reutilizando los embeddings que ya
calcula el índice semántico. Descubre patrones que el usuario no ve ("tienes N
notas dispersas sobre X"). KMeans implementado en numpy puro — sin dependencias
nuevas, sin sklearn.
"""
import numpy as np

from src.services.semantic_index import _normalize


def _kmeans(X: np.ndarray, k: int, iters: int = 50, seed: int = 0):
    """KMeans esférico (coseno) sobre vectores. Devuelve (labels, centroids)."""
    rng = np.random.default_rng(seed)
    n = len(X)
    Xn = _normalize(X)
    centroids = Xn[rng.choice(n, size=k, replace=False)].copy()
    labels = np.full(n, -1)

    for it in range(iters):
        sims = Xn @ _normalize(centroids).T          # (n, k)
        new_labels = sims.argmax(axis=1)
        if it > 0 and np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            members = Xn[labels == c]
            if len(members):
                centroids[c] = members.mean(axis=0)
            else:  # reinicia un centroide vacío a un punto aleatorio
                centroids[c] = Xn[rng.integers(n)]
    return labels, _normalize(centroids)


def _suggest_k(n: int) -> int:
    """Heurística para el número de temas: ~sqrt(n/2), acotado a [2, n]."""
    return max(2, min(n, int(round((n / 2) ** 0.5))))


def cluster_notes(meta: list, vectors: np.ndarray, k: int = None) -> list:
    """
    Agrupa las notas en temas. Devuelve una lista de clusters ordenada por tamaño:
        [{label, size, titles}]
    donde 'label' es el título de la nota más representativa (cercana al centroide).
    """
    if vectors is None or len(meta) < 2:
        return []
    n = len(meta)
    k = min(k or _suggest_k(n), n)

    labels, centroids = _kmeans(vectors, k)
    Xn = _normalize(vectors)

    clusters = []
    for c in range(k):
        idxs = [i for i in range(n) if labels[i] == c]
        if not idxs:
            continue
        sims = Xn[idxs] @ centroids[c]
        rep = idxs[int(np.argmax(sims))]
        clusters.append({
            "label": meta[rep]["title"],
            "size": len(idxs),
            "titles": [meta[i]["title"] for i in idxs],
        })
    clusters.sort(key=lambda c: -c["size"])
    return clusters


def get_note_clusters() -> str:
    """
    Descubre los TEMAS latentes en las notas del usuario agrupándolas por
    significado. Úsala cuando pregunte qué temas tiene, en qué se repite, o quiera
    organizar/descubrir patrones en su memoria.

    Returns:
        Texto con los temas descubiertos, su tamaño y notas de ejemplo.
    """
    try:
        from src.services.semantic_search import _get_index
        meta, vectors = _get_index().get_matrix()
    except Exception as e:
        return f"No pude analizar los temas: {e}"

    if vectors is None or len(meta) < 4:
        return "Aún no hay suficientes notas para descubrir temas (necesito al menos 4)."

    clusters = cluster_notes(meta, vectors)
    lines = [f"TEMAS DESCUBIERTOS ({len(clusters)}):"]
    for c in clusters:
        sample = ", ".join(c["titles"][:5])
        more = "…" if c["size"] > 5 else ""
        lines.append(f"- «{c['label']}» — {c['size']} notas: {sample}{more}")
    return "\n".join(lines)
