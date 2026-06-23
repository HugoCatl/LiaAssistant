import sys
import ctypes

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


def get_active_window_title() -> str:
    """Devuelve el título de la ventana en primer plano (Windows). '' si falla."""
    if sys.platform != "win32":
        return ""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:
        return ""


def get_idle_seconds() -> float:
    """Segundos desde la última actividad de teclado/ratón del usuario (Windows)."""
    if sys.platform != "win32":
        return 0.0
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0.0, millis / 1000.0)
    except Exception:
        return 0.0


class SystemMonitor(QObject):
    """
    Observa el sistema en segundo plano y emite señales cuando detecta cambios
    relevantes para que el motor proactivo decida si vale la pena sugerir algo.

    Señales:
        clipboard_changed(str): el portapapeles tiene texto nuevo y sustancial.
        active_window_changed(str): cambió el título de la ventana en primer plano.
        tick(str, float): latido periódico con (ventana_activa, segundos_inactivo).
    """

    clipboard_changed = pyqtSignal(str)
    active_window_changed = pyqtSignal(str)
    tick = pyqtSignal(str, float)

    _MIN_CLIPBOARD_LEN = 40  # ignora copias triviales (una palabra, etc.)

    def __init__(self, poll_ms: int = 4000, parent=None):
        super().__init__(parent)
        self._poll_ms = poll_ms
        self._last_clipboard = None
        self._last_window = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self):
        # Inicializa el estado base sin emitir (evita disparar al arrancar)
        self._last_clipboard = self._read_clipboard()
        self._last_window = get_active_window_title()
        self._timer.start(self._poll_ms)

    def stop(self):
        self._timer.stop()

    def _read_clipboard(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste() or ""
        except Exception:
            return ""

    def _poll(self):
        # Ventana activa
        window = get_active_window_title()
        if window and window != self._last_window:
            self._last_window = window
            self.active_window_changed.emit(window)

        # Portapapeles
        clip = self._read_clipboard()
        if clip and clip != self._last_clipboard:
            self._last_clipboard = clip
            if len(clip.strip()) >= self._MIN_CLIPBOARD_LEN:
                self.clipboard_changed.emit(clip)

        # Latido con contexto
        self.tick.emit(self._last_window or "", get_idle_seconds())
