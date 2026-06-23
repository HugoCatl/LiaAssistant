import random

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QGuiApplication


class MascotMood:
    """Estados expresivos de la mascota Lia, independientes del estado interno."""
    IDLE = "idle"
    CURIOUS = "curious"
    REMINDER = "reminder"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class _Pose:
    SIT = "sit"
    WALK = "walk"


class MascotBehaviorMixin:
    """
    Comportamiento de ventana compartido por cualquier mascota de escritorio
    (gato dibujado en QPainter o modelo Live2D): colocación en el borde, paseo
    autónomo, y distinción clic/arrastre con snap al borde.

    La clase concreta debe:
      - definir la señal `clicked` (pyqtSignal),
      - tener atributo `_mood` (str de MascotMood) y `_facing` (int: -1 izq, 1 der),
      - llamar a `self._init_behavior()` al final de su __init__,
      - opcionalmente sobreescribir `_on_walk_changed(walking: bool)` para reflejar
        visualmente el caminar (cambiar pose, lanzar una animación, etc.).
    """

    _DRAG_THRESHOLD = 6
    _WALK_SPEED = 2.4
    _WANDER_MIN_MS = 9000
    _WANDER_MAX_MS = 20000
    _EDGE_MARGIN = 12
    _wander_enabled = True  # las mascotas que no andan (orbe) lo ponen a False

    def _init_behavior(self):
        if not hasattr(self, "_facing"):
            self._facing = -1
        self._walking = False
        self._is_dragging = False
        self._target_x = None
        self._press_global = QPoint()
        self._press_origin = QPoint()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._wander_timer = QTimer(self)
        self._wander_timer.setSingleShot(True)
        self._wander_timer.timeout.connect(self._start_wander)

        self._move_to_default_corner()
        if self._wander_enabled:
            self._schedule_wander()

    # --------------------------------------------------------- posicionamiento

    def _bottom_y(self, screen) -> int:
        return screen.bottom() - self.height() + 8

    def _move_to_default_corner(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - self._EDGE_MARGIN
        self.move(x, self._bottom_y(screen))

    # ----------------------------------------------------------------- paseo

    def _can_wander(self) -> bool:
        return getattr(self, "_mood", MascotMood.IDLE) == MascotMood.IDLE and not self._is_dragging

    def _schedule_wander(self):
        self._wander_timer.start(random.randint(self._WANDER_MIN_MS, self._WANDER_MAX_MS))

    def _start_wander(self):
        if not self._can_wander():
            self._schedule_wander()
            return
        screen = QGuiApplication.primaryScreen().availableGeometry()
        min_x = screen.left() + self._EDGE_MARGIN
        max_x = screen.right() - self.width() - self._EDGE_MARGIN
        target = random.randint(min_x, max_x)
        if abs(target - self.x()) < 140:  # asegura que el paseo se note
            target = min_x if self.x() > screen.center().x() else max_x
        self._target_x = target
        self._facing = 1 if target > self.x() else -1
        self._set_walking(True)

    def _advance_walk(self):
        """Avanza un paso hacia el destino. La clase concreta la llama cada frame."""
        if self._target_x is None or not self._can_wander():
            self._stop_walk()
            return
        dx = self._target_x - self.x()
        if abs(dx) <= self._WALK_SPEED:
            self.move(self._target_x, self.y())
            self._stop_walk()
            return
        step = self._WALK_SPEED * (1 if dx > 0 else -1)
        self.move(self.x() + int(step), self.y())

    def _stop_walk(self):
        self._target_x = None
        self._set_walking(False)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self._facing = -1 if self.x() > screen.center().x() else 1
        self._schedule_wander()

    def _set_walking(self, walking: bool):
        self._walking = walking
        self._on_walk_changed(walking)

    def _on_walk_changed(self, walking: bool):
        """Hook para que la mascota concreta refleje el caminar. Override opcional."""
        pass

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
            self._target_x = None
            self._set_walking(False)
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
            self._facing = 1
        else:
            x = screen.right() - self.width() - self._EDGE_MARGIN
            self._facing = -1
        self.move(x, self._bottom_y(screen))
