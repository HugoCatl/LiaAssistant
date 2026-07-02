"""
Score de relevancia que aprende del feedback proactivo.

Regresión logística simple sobre features interpretables. Predice P(aceptar) para
una sugerencia candidata; el motor proactivo la silencia si el score baja del
umbral. 100% local, sin dependencias nuevas (solo numpy).

Diseño:
- Vector de features fijo: one-hot del tipo de sugerencia + features numéricas.
- Warmup: con <MIN_TRAIN ejemplos devuelve 1.0 (no filtra). Esto evita decisiones
  arbitrarias con datos pobres.
- Reentrenamiento por gradient descent cada vez que se añade feedback.
"""
import math
from typing import Dict, List, Tuple
import numpy as np


# Tipos de sugerencia conocidos (orden canónico para el one-hot)
KINDS = ("clipboard", "focus", "note_gap", "eod", "demo")

# Features numéricas opcionales (en [0,1]). 0 si la sugerencia no tiene esa feature.
NUMERIC_FEATURES = ("hour_norm", "clip_len_norm", "is_url", "is_work_hours")

# Mínimo de ejemplos antes de empezar a filtrar. 6 en vez de 10: con 10 el
# aprendizaje tardaba días en activarse (arrancaba "ciego"); con 6 y la
# regularización L2 el modelo ya filtra patrones claramente rechazados antes.
MIN_TRAIN = 6
DEFAULT_THRESHOLD = 0.35  # P(aceptar) por debajo -> silenciar


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def featurize(kind: str, features: Dict) -> np.ndarray:
    """Convierte (kind, features_dict) en un vector denso de tamaño fijo."""
    vec = []
    # One-hot del tipo
    for k in KINDS:
        vec.append(1.0 if k == kind else 0.0)
    # Features numéricas (rellenadas con 0 si faltan)
    for name in NUMERIC_FEATURES:
        v = float(features.get(name, 0.0) or 0.0)
        vec.append(max(0.0, min(1.0, v)))
    return np.asarray(vec, dtype=np.float32)


FEATURE_DIM = len(KINDS) + len(NUMERIC_FEATURES)


class RelevanceScorer:
    """Regresión logística que aprende qué sugerencias aceptas tú."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold
        # Pesos + bias (inicialmente sesgados positivamente: no filtrar al arrancar)
        self.w = np.zeros(FEATURE_DIM, dtype=np.float32)
        self.b = np.float32(2.0)  # bias alto -> sigmoid≈0.88 sin entrenamiento
        self._n_examples = 0

    # ---------------------------------------------------------------- predicción

    def predict(self, kind: str, features: Dict) -> float:
        """Devuelve P(aceptar) en [0,1]. Durante warmup devuelve 1.0."""
        if self._n_examples < MIN_TRAIN:
            return 1.0
        x = featurize(kind, features)
        return float(_sigmoid(x @ self.w + self.b))

    def should_emit(self, kind: str, features: Dict) -> Tuple[bool, float]:
        """Decide si emitir la sugerencia. Devuelve (emitir, score)."""
        score = self.predict(kind, features)
        return score >= self.threshold, score

    # ---------------------------------------------------------------- entrenamiento

    def fit(self, examples: List[Tuple[str, Dict, bool]], iters: int = 60, lr: float = 0.25):
        """
        Entrena desde cero con los ejemplos dados. Coste despreciable con cientos.

        examples: lista de (kind, features_dict, accepted_bool).
        """
        self._n_examples = len(examples)
        if self._n_examples < MIN_TRAIN:
            return  # mantenemos pesos por defecto; predict() devolverá 1.0

        X = np.stack([featurize(k, f) for k, f, _ in examples])
        y = np.asarray([1.0 if a else 0.0 for _, _, a in examples], dtype=np.float32)
        n = len(y)

        # Regularización L2 suave para no sobreajustar a 10-20 ejemplos
        w = np.zeros(FEATURE_DIM, dtype=np.float32)
        b = np.float32(0.0)
        reg = 0.01

        for _ in range(iters):
            z = X @ w + b
            p = _sigmoid(z)
            err = p - y
            grad_w = (X.T @ err) / n + reg * w
            grad_b = float(err.mean())
            w -= lr * grad_w
            b -= lr * grad_b

        self.w = w.astype(np.float32)
        self.b = np.float32(b)
