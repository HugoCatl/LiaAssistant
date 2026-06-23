import time
from datetime import datetime, date

from PyQt6.QtCore import QObject, pyqtSignal


def _looks_like_url(text: str) -> bool:
    t = text.strip().lower()
    return t.startswith("http://") or t.startswith("https://") or t.startswith("www.")


def _short(text: str, limit: int = 50) -> str:
    t = " ".join(text.split())
    return t if len(t) <= limit else t[: limit - 1] + "…"


class ProactiveEngine(QObject):
    """
    Decide CUÁNDO Lia debe sugerir algo de forma proactiva, a partir de las
    señales del SystemMonitor. Aplica reglas simples con cooldowns para no agobiar.

    Esta es la base (Fase 2) sin ML: reglas explícitas. En la Fase 3 el score de
    relevancia se aprenderá del feedback (accepted/dismissed) que ya registramos.

    Señal:
        suggestion(text, prefill, auto_submit, mood)
            text: mensaje a mostrar en la burbuja.
            prefill: texto para precargar en el input al aceptar ('' = nada).
            auto_submit: si True, envía el prefill automáticamente al aceptar.
            mood: expresión sugerida para la mascota ('reminder' | 'curious').
    """

    suggestion = pyqtSignal(str, str, bool, str)

    def __init__(
        self,
        global_cooldown_s: float = 300.0,
        note_gap_s: float = 45 * 60.0,
        focus_gap_s: float = 30 * 60.0,
        present_idle_max_s: float = 120.0,
        eod_hour: int = 19,
        parent=None,
    ):
        super().__init__(parent)
        self.global_cooldown_s = global_cooldown_s
        self.note_gap_s = note_gap_s
        self.focus_gap_s = focus_gap_s
        self.present_idle_max_s = present_idle_max_s
        self.eod_hour = eod_hour

        now = time.monotonic()
        self._last_suggestion_at = 0.0
        self._last_activity_at = now

        self._last_clip_suggested = None

        self._focus_window = None
        self._focus_since = now
        self._focus_suggested_for = None

        self._today = date.today()
        self._captures_today = 0
        self._eod_suggested_date = None
        self._idle_note_suggested = False

    # ------------------------------------------------------------- actividad

    def note_activity(self, is_capture: bool = False):
        """El usuario interactuó con Lia. Resetea temporizadores de inactividad."""
        self._roll_day()
        self._last_activity_at = time.monotonic()
        self._idle_note_suggested = False
        if is_capture:
            self._captures_today += 1

    def record_feedback(self, accepted: bool):
        """Registra el feedback del usuario (hook para el aprendizaje de Fase 3)."""
        # Por ahora solo refuerza el cooldown si se rechaza, para no insistir.
        if not accepted:
            self._last_suggestion_at = time.monotonic()

    # --------------------------------------------------------- manejadores

    def on_clipboard_changed(self, text: str):
        if text == self._last_clip_suggested:
            return
        if _looks_like_url(text):
            msg = f"Copiaste un enlace. ¿Lo guardo en tu vault?"
            prefill = f"Crea una nota con este enlace de mi portapapeles y etiquétalo."
        else:
            msg = f"Copiaste «{_short(text)}». ¿Quieres que lo guarde como nota?"
            prefill = "Crea una nota con lo que tengo en mi portapapeles."
        if self._emit(msg, prefill, auto_submit=True, mood="curious"):
            self._last_clip_suggested = text

    def on_active_window_changed(self, title: str):
        # Reinicia el cronómetro de foco para la regla de "llevas mucho en lo mismo"
        self._focus_window = title
        self._focus_since = time.monotonic()
        self._focus_suggested_for = None

    def on_tick(self, window: str, idle_seconds: float):
        self._roll_day()
        now = time.monotonic()
        present = idle_seconds <= self.present_idle_max_s

        # Regla fin de día: ha caído la tarde y no anotaste nada hoy
        hour = datetime.now().hour
        if (hour >= self.eod_hour and self._captures_today == 0
                and self._eod_suggested_date != self._today and present):
            if self._emit(
                "Hoy no has anotado nada. ¿Hacemos un resumen rápido de tu día?",
                "Ayúdame a hacer un resumen rápido de lo que hice hoy.",
                auto_submit=False, mood="reminder",
            ):
                self._eod_suggested_date = self._today
                return

        # Regla foco prolongado: mucho tiempo en la misma app
        if (present and window and window == self._focus_window
                and self._focus_suggested_for != window
                and now - self._focus_since >= self.focus_gap_s):
            app = _short(window, 32)
            if self._emit(
                f"Llevas un buen rato en «{app}». ¿Anotamos en qué avanzaste?",
                "Quiero anotar en qué he avanzado en lo que estoy trabajando: ",
                auto_submit=False, mood="reminder",
            ):
                self._focus_suggested_for = window
                return

        # Regla inactividad de notas: mucho sin capturar, pero presente
        if (present and not self._idle_note_suggested
                and now - self._last_activity_at >= self.note_gap_s):
            if self._emit(
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

    def _emit(self, text, prefill, auto_submit, mood) -> bool:
        """Emite una sugerencia si no estamos en cooldown global. Devuelve si emitió."""
        now = time.monotonic()
        if now - self._last_suggestion_at < self.global_cooldown_s:
            return False
        self._last_suggestion_at = now
        self.suggestion.emit(text, prefill, auto_submit, mood)
        return True
