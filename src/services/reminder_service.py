"""
Servicio que comprueba periodicamente los recordatorios y emite una senal
cuando uno vence, para que el orquestador lo muestre en la burbuja de la mascota.
"""
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.services.reminders import pop_due


class ReminderService(QObject):
    reminder_due = pyqtSignal(str)  # texto del recordatorio vencido

    def __init__(self, poll_ms: int = 30000, parent=None):
        super().__init__(parent)
        self._poll_ms = poll_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)

    def start(self):
        self._timer.start(self._poll_ms)
        self._check()

    def stop(self):
        self._timer.stop()

    def _check(self):
        for texto in pop_due():
            self.reminder_due.emit(texto)
