from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QGuiApplication


class MascotMood:
    """Estados expresivos de la mascota Lia, independientes del estado interno."""
    IDLE = "idle"
    CURIOUS = "curious"
    REMINDER = "reminder"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class MascotBehaviorMixin:
    """
    Comportamiento de ventana compartido por la mascota de escritorio: colocación
    en el borde inferior, distinción clic/arrastre y snap al borde más cercano.

    La clase concreta debe:
      - definir la señal `clicked` (pyqtSignal),
      - llamar a `self._init_behavior()` al final de su __init__.
    """

    _DRAG_THRESHOLD = 6
    _EDGE_MARGIN = 12

    def _init_behavior(self):
        self._is_dragging = False
        self._press_global = QPoint()
        self._press_origin = QPoint()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._move_to_default_corner()

    # --------------------------------------------------------- posicionamiento

    def _bottom_y(self, screen) -> int:
        return screen.bottom() - self.height() + 8

    def _move_to_default_corner(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - self._EDGE_MARGIN
        self.move(x, self._bottom_y(screen))

    # ------------------------------------------------------- ratón: clic/arrastre

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_origin = self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        delta = event.globalPosition().toPoint() - self._press_global
        if not self._is_dragging and delta.manhattanLength() > self._DRAG_THRESHOLD:
            self._is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        if self._is_dragging:
            self.move(self._press_origin + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._is_dragging:
            self._snap_to_edge()
        else:
            self.clicked.emit()
        self._is_dragging = False
        event.accept()

    def _snap_to_edge(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = self.frameGeometry().x()
        if x + self.width() / 2 < screen.center().x():
            x = screen.left() + self._EDGE_MARGIN
        else:
            x = screen.right() - self.width() - self._EDGE_MARGIN
        self.move(x, self._bottom_y(screen))
