"""Tests del clustering de temas (Fase 3B)."""
import numpy as np
from src.services.topic_clusters import cluster_notes, _suggest_k


def _meta(titles):
    return [{"title": t} for t in titles]


def test_separates_two_clear_groups():
    # Dos grupos bien separados en el espacio vectorial
    g1 = np.array([[1.0, 0.0, 0.0]] * 3) + np.random.default_rng(1).normal(0, 0.01, (3, 3))
    g2 = np.array([[0.0, 1.0, 0.0]] * 3) + np.random.default_rng(2).normal(0, 0.01, (3, 3))
    vectors = np.vstack([g1, g2]).astype(np.float32)
    meta = _meta(["A1", "A2", "A3", "B1", "B2", "B3"])

    clusters = cluster_notes(meta, vectors, k=2)
    assert len(clusters) == 2

    # Cada cluster debe contener solo miembros de su grupo
    groups = [set(c["titles"]) for c in clusters]
    a = {"A1", "A2", "A3"}
    b = {"B1", "B2", "B3"}
    assert a in groups and b in groups


def test_label_is_a_member_title():
    vectors = np.array([[1, 0], [0.99, 0.01], [0, 1], [0.01, 0.99]], dtype=np.float32)
    meta = _meta(["uno", "dos", "tres", "cuatro"])
    clusters = cluster_notes(meta, vectors, k=2)
    for c in clusters:
        assert c["label"] in c["titles"]


def test_too_few_notes_returns_empty():
    assert cluster_notes(_meta(["sola"]), np.array([[1.0, 0.0]], dtype=np.float32)) == []
    assert cluster_notes([], None) == []


def test_suggest_k_bounds():
    assert _suggest_k(2) == 2
    assert _suggest_k(50) >= 2
    assert _suggest_k(8) <= 8


def test_clusters_sorted_by_size():
    # Grupo grande (4) + grupo pequeño (1, separado)
    big = np.array([[1.0, 0.0]] * 4, dtype=np.float32)
    small = np.array([[0.0, 1.0]], dtype=np.float32)
    vectors = np.vstack([big, small]).astype(np.float32)
    meta = _meta(["G1", "G2", "G3", "G4", "P1"])
    clusters = cluster_notes(meta, vectors, k=2)
    assert clusters[0]["size"] >= clusters[-1]["size"]
