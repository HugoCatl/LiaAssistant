"""Tests de la normalización de etiquetas (auto-tags de entidades)."""
from src.storage.obsidian_manager import normalize_tags


def test_removes_hash_and_trims():
    assert normalize_tags(["#ia", "  tareas  "]) == ["ia", "tareas"]


def test_spaces_become_hyphens_for_entities():
    # Las tags de Obsidian no admiten espacios -> deben unirse con guion
    assert normalize_tags(["persona/Juan Pérez"]) == ["persona/Juan-Pérez"]
    assert normalize_tags(["proyecto/Lia Assistant"]) == ["proyecto/Lia-Assistant"]


def test_preserves_hierarchy_and_accents():
    res = normalize_tags(["persona/Ana", "lugar/España"])
    assert "persona/Ana" in res and "lugar/España" in res


def test_dedup_case_insensitive():
    assert normalize_tags(["IA", "ia", "Ia"]) == ["IA"]


def test_strips_invalid_chars():
    assert normalize_tags(["pro!yec@to"]) == ["proyecto"]


def test_handles_empty_and_none():
    assert normalize_tags(None) == []
    assert normalize_tags(["", "   ", "#"]) == []


def test_strips_stray_separators():
    assert normalize_tags(["/persona/Ana/"]) == ["persona/Ana"]
