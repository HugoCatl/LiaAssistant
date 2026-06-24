from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication


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
    Comportamiento de ventana compartido por la mascota de escritorio: colocacion
    en el borde inferior, distincion clic/arrastre y snap al borde mas cercano.

    La clase concreta debe:
      - definir las senales `clicked` y `double_clicked` (pyqtSignal),
      - llamar a `self._init_behavior()` al final de su __init__.

    Distingue clic simple de doble clic: el clic simple se emite tras el
    intervalo de doble clic del sistema; si llega un doble clic antes, se
    cancela el simple y se emite `double_clicked`.
    """

    _DRAG_THRESHOLD = 6
    _EDGE_MARGIN = 12

    def _init_behavior(self):
        self._is_dragging = False
        self._double = False
        self._press_global = QPoint()
        self._press_origin = QPoint()
        # Temporizador para no confundir clic simple con la primera mitad de un doble clic
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.clicked.emit)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._move_to_default_corner()

    # --------------------------------------------------------- posicionamiento

    def _bottom_y(self, screen) -> int:
        return screen.bottom() - self.height() + 8

    def _move_to_default_corner(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - self._EDGE_MARGIN
        self.move(x, self._bottom_y(screen))

    # ------------------------------------------------------- raton: clic/arrastre

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
        elif self._double:
            # Es el release de la segunda pulsacion del doble clic: consumirlo
            self._double = False
        else:
            # Esperar al posible doble clic antes de confirmar el clic simple
            self._click_timer.start(QApplication.doubleClickInterval())
        self._is_dragging = False
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._click_timer.stop()   # cancela el clic simple pendiente
        self._double = True
        self.double_clicked.emit()
        event.accept()

    def _snap_to_edge(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = self.frameGeometry().x()
        if x + self.width() / 2 < screen.center().x():
            x = screen.left() + self._EDGE_MARGIN
        else:
            x = screen.right() - self.width() - self._EDGE_MARGIN
        self.move(x, self._bottom_y(screen))
