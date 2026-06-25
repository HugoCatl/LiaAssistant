import time
from datetime import datetime, date
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from src.services.feedback_store import FeedbackStore
from src.services.relevance_scorer import RelevanceScorer


def _looks_like_url(text: str) -> bool:
    t = text.strip().lower()
    return t.startswith("http://") or t.startswith("https://") or t.startswith("www.")


def _is_noteworthy_clip(text: str) -> bool:
    """
    ¿Merece la pena ofrecer guardar esto? Evita saltar con copias rutinarias
    (un trozo de código, una frase corta). Sí si: es una URL, es texto multilínea
    sustancial (lista/párrafo) o es texto largo de una línea.
    """
    t = text.strip()
    if not t:
        return False
    if _looks_like_url(t):
        return True
    if "\n" in t and len(t) >= 60:
        return True
    return len(t) >= 100


def _app_of(title: str) -> str:
    """
    Extrae el nombre de la app del título de ventana (lo que va tras el último
    separador). Así 'documento.py — VS Code' y 'otro.py — VS Code' cuentan como la
    MISMA app y el contador de foco no se reinicia al cambiar de pestaña/archivo.
    """
    for sep in (" — ", " – ", " - "):
        if sep in title:
            return title.rsplit(sep, 1)[-1].strip()
    return title.strip()


def _short(text: str, limit: int = 50) -> str:
    t = " ".join(text.split())
    return t if len(t) <= limit else t[: limit - 1] + "…"


def _now_features() -> dict:
    """Features contextuales comunes a toda sugerencia."""
    h = datetime.now().hour
    return {
        "hour_norm": h / 24.0,
        "is_work_hours": 1.0 if 9 <= h <= 18 else 0.0,
    }


class ProactiveEngine(QObject):
    """
    Decide CUÁNDO Lia debe sugerir algo de forma proactiva.

    Combina reglas explícitas (Fase 2) con un score de relevancia que aprende del
    feedback del usuario (Fase 3): si el modelo predice que el usuario probablemente
    rechazará una sugerencia de ese tipo/contexto, Lia se calla esta vez.

    Señal:
        suggestion(text, prefill, auto_submit, mood)
    """

    suggestion = pyqtSignal(str, str, bool, str)

    def __init__(
        self,
        global_cooldown_s: float = 300.0,
        note_gap_s: float = 60 * 60.0,
        focus_gap_s: float = 30 * 60.0,
        present_idle_max_s: float = 120.0,
        eod_hour: int = 19,
        feedback_store: Optional[FeedbackStore] = None,
        scorer: Optional[RelevanceScorer] = None,
        debug: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.global_cooldown_s = global_cooldown_s
        self.note_gap_s = note_gap_s
        self.focus_gap_s = focus_gap_s
        self.present_idle_max_s = present_idle_max_s
        self.eod_hour = eod_hour
        self.debug = debug

        # ML local: tienda + modelo (inyectables para tests)
        self.store = feedback_store if feedback_store is not None else FeedbackStore()
        self.scorer = scorer if scorer is not None else RelevanceScorer()
        self._retrain_from_store()

        # Etiqueta de la última sugerencia EMITIDA, para asociar el feedback al
        # (kind, features) correcto cuando el usuario decide.
        self._pending_label: Optional[tuple] = None

        now = time.monotonic()
        self._last_suggestion_at = 0.0
        self._last_activity_at = now

        self._last_clip_suggested = None

        self._focus_app = None
        self._focus_since = now
        self._focus_suggested_for = None

        self._today = date.today()
        self._captures_today = 0
        self._eod_suggested_date = None
        self._idle_note_suggested = False

    # ------------------------------------------------------------- aprendizaje

    def _retrain_from_store(self):
        examples = self.store.all_examples()
        self.scorer.fit(examples)
        if self.debug:
            print(f"[Proactive] Scorer entrenado con {len(examples)} ejemplos.")

    def record_feedback(self, accepted: bool):
        """Registra el resultado de la última sugerencia y reentrena el modelo."""
        if self._pending_label is None:
            return
        kind, features = self._pending_label
        self._pending_label = None
        self.store.record(kind, features, accepted)
        self._retrain_from_store()
        # Si rechaza, refuerza el cooldown global para no insistir
        if not accepted:
            self._last_suggestion_at = time.monotonic()

    # ------------------------------------------------------------- actividad

    def note_activity(self, is_capture: bool = False):
        self._roll_day()
        self._last_activity_at = time.monotonic()
        self._idle_note_suggested = False
        if is_capture:
            self._captures_today += 1

    # --------------------------------------------------------- manejadores

    def _clip_features(self, text: str) -> dict:
        f = _now_features()
        f["is_url"] = 1.0 if _looks_like_url(text) else 0.0
        f["clip_len_norm"] = min(1.0, len(text) / 500.0)
        return f

    def on_clipboard_changed(self, text: str):
        if text == self._last_clip_suggested:
            return
        # No molestar con copias rutinarias: solo si de verdad parece nota
        if not _is_noteworthy_clip(text):
            return
        if _looks_like_url(text):
            msg = "Copiaste un enlace. ¿Lo guardo en tu vault?"
            prefill = "Crea una nota con este enlace de mi portapapeles y etiquétalo."
        else:
            msg = f"Copiaste «{_short(text)}». ¿Quieres que lo guarde como nota?"
            prefill = "Crea una nota con lo que tengo en mi portapapeles."
        if self._emit("clipboard", self._clip_features(text), msg, prefill,
                      auto_submit=True, mood="curious"):
            self._last_clip_suggested = text

    def on_active_window_changed(self, title: str):
        # Reinicia el contador de foco solo si cambió la APP (no al cambiar de
        # pestaña/archivo dentro de la misma app).
        app = _app_of(title)
        if app != self._focus_app:
            self._focus_app = app
            self._focus_since = time.monotonic()
            self._focus_suggested_for = None

    def on_tick(self, window: str, idle_seconds: float):
        self._roll_day()
        now = time.monotonic()
        present = idle_seconds <= self.present_idle_max_s

        hour = datetime.now().hour
        if (hour >= self.eod_hour and self._captures_today == 0
                and self._eod_suggested_date != self._today and present):
            if self._emit(
                "eod", _now_features(),
                "Hoy no has anotado nada. ¿Hacemos un resumen rápido de tu día?",
                "Ayúdame a hacer un resumen rápido de lo que hice hoy.",
                auto_submit=False, mood="reminder",
            ):
                self._eod_suggested_date = self._today
                return

        cur_app = _app_of(window) if window else ""
        if (present and cur_app and cur_app == self._focus_app
                and self._focus_suggested_for != cur_app
                and now - self._focus_since >= self.focus_gap_s):
            app = _short(cur_app, 32)
            if self._emit(
                "focus", _now_features(),
                f"Llevas un buen rato en «{app}». ¿Anotamos en qué avanzaste?",
                "Quiero anotar en qué he avanzado en lo que estoy trabajando: ",
                auto_submit=False, mood="reminder",
            ):
                self._focus_suggested_for = cur_app
                return

        if (present and not self._idle_note_suggested
                and now - self._last_activity_at >= self.note_gap_s):
            if self._emit(
                "note_gap", _now_features(),
                "¿Alguna idea o nota que quieras guardar antes de seguir?",
                "", auto_submit=False, mood="reminder",
            ):
                self._idle_note_suggested = True
                return

    # ------------------------------------------------------------- internos

    def _roll_day(self):
        today = date.today()
        if today != self._today:
            self._today = today
            self._captures_today = 0
            self._eod_suggested_date = None

    def _emit(self, kind: str, features: dict, text: str, prefill: str,
              auto_submit: bool, mood: str) -> bool:
        """
        Decide si emitir: respeta el cooldown global y consulta al scorer.
        Devuelve si la sugerencia se emitió.
        """
        now = time.monotonic()
        if now - self._last_suggestion_at < self.global_cooldown_s:
            return False

        emit, score = self.scorer.should_emit(kind, features)
        if self.debug:
            print(f"[Proactive] kind={kind} score={score:.2f} -> "
                  f"{'EMITIR' if emit else 'silenciar'}")
        if not emit:
            # Lia se calla porque ha aprendido que no te gusta este patrón
            return False

        self._last_suggestion_at = now
        self._pending_label = (kind, features)
        self.suggestion.emit(text, prefill, auto_submit, mood)
        return True
