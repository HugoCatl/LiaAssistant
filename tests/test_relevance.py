"""Tests del RelevanceScorer y el FeedbackStore."""
import os
import tempfile
import pytest

from src.services.feedback_store import FeedbackStore
from src.services.relevance_scorer import (
    RelevanceScorer, featurize, FEATURE_DIM, KINDS, MIN_TRAIN,
)


# -------- FeedbackStore -------------------------------------------------------

def test_store_persists_and_recovers(tmp_path):
    db = str(tmp_path / "fb.db")
    s = FeedbackStore(db)
    s.record("clipboard", {"is_url": 1.0}, True)
    s.record("eod", {"hour_norm": 0.8}, False)
    assert s.count() == 2

    # Reabrir: los ejemplos persisten
    s2 = FeedbackStore(db)
    rows = s2.all_examples()
    assert len(rows) == 2
    kinds = [r[0] for r in rows]
    assert "clipboard" in kinds and "eod" in kinds


# -------- Featurización -------------------------------------------------------

def test_featurize_has_fixed_dim_and_onehot():
    v = featurize("clipboard", {"is_url": 1.0, "hour_norm": 0.5})
    assert v.shape == (FEATURE_DIM,)
    # one-hot del kind
    clip_idx = KINDS.index("clipboard")
    assert v[clip_idx] == 1.0
    assert sum(v[: len(KINDS)]) == 1.0


def test_featurize_unknown_kind_yields_zero_onehot():
    v = featurize("desconocido", {})
    assert sum(v[: len(KINDS)]) == 0.0


# -------- Aprendizaje ---------------------------------------------------------

def test_warmup_does_not_filter():
    """Con menos del mínimo, todo debe emitirse (Lia se comporta como antes)."""
    s = RelevanceScorer()
    # Sin entrenar: predict = 1.0, should_emit = True
    emit, score = s.should_emit("clipboard", {"is_url": 1.0})
    assert emit and score == 1.0


def test_learns_to_reject_pattern_user_dislikes():
    """
    Escenario: el usuario rechaza SIEMPRE los recordatorios EOD y ACEPTA
    siempre los del portapapeles. Tras entrenar, el scorer debe silenciar EOD
    y dejar pasar clipboard.
    """
    examples = []
    for _ in range(8):
        examples.append(("clipboard", {"is_url": 1.0}, True))
        examples.append(("eod", {"hour_norm": 0.8}, False))

    s = RelevanceScorer()
    s.fit(examples)

    p_clip = s.predict("clipboard", {"is_url": 1.0})
    p_eod = s.predict("eod", {"hour_norm": 0.8})

    assert p_clip > 0.7, f"esperaba alto para clipboard, fue {p_clip:.2f}"
    assert p_eod < 0.3, f"esperaba bajo para eod, fue {p_eod:.2f}"

    # Decisión: emite clipboard, silencia eod
    assert s.should_emit("clipboard", {"is_url": 1.0})[0]
    assert not s.should_emit("eod", {"hour_norm": 0.8})[0]


def test_learns_numeric_feature_within_kind():
    """
    Aprende a diferenciar por features numéricas dentro del mismo kind:
    acepta clipboards que son URL, rechaza los que no.
    """
    examples = []
    for _ in range(10):
        examples.append(("clipboard", {"is_url": 1.0}, True))
        examples.append(("clipboard", {"is_url": 0.0}, False))

    s = RelevanceScorer()
    s.fit(examples)

    p_url = s.predict("clipboard", {"is_url": 1.0})
    p_text = s.predict("clipboard", {"is_url": 0.0})
    assert p_url > p_text + 0.3, f"no aprendió el patrón is_url ({p_url:.2f} vs {p_text:.2f})"


def test_no_filter_below_min_train():
    """Con MIN_TRAIN-1 ejemplos sigue sin filtrar."""
    s = RelevanceScorer()
    s.fit([("eod", {}, False)] * (MIN_TRAIN - 1))
    assert s.predict("eod", {}) == 1.0
