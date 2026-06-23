"""
Mascota Lia renderizada con un modelo Live2D (Cubism 3) en una ventana OpenGL
transparente. Comparte el comportamiento de escritorio (paseo, clic, arrastre)
con el gato dibujado a mano vía MascotBehaviorMixin.

Requiere: live2d-py y PyOpenGL instalados, y un modelo .model3.json válido.
Si algo falla, main.py cae automáticamente al gato QPainter (MascotWidget).
"""
import math

from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QSurfaceFormat, QCursor

import live2d.v2 as live2d_v2
import live2d.v3 as live2d_v3
from OpenGL.GL import glEnable, glBlendFunc, GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA

from src.core.state_manager import AssistantState
from src.gui.mascot_behavior import MascotBehaviorMixin, MascotMood


# Estado de inicialización por módulo (v2 / v3 se inicializan por separado)
_initialized = {}


def _pick_module(model_path: str):
    """Elige el runtime según la versión del modelo: .model3.json -> v3, .model.json -> v2."""
    return live2d_v3 if model_path.endswith(".model3.json") else live2d_v2


def configure_surface_format():
    """Configura el formato OpenGL por defecto con canal alfa (transparencia)."""
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)


def _ensure_live2d_init(module):
    if not _initialized.get(id(module)):
        module.init()
        _initialized[id(module)] = True


def dispose():
    """Libera los recursos de Live2D al cerrar la app."""
    for module in (live2d_v2, live2d_v3):
        if _initialized.get(id(module)):
            try:
                module.dispose()
            except Exception:
                pass
            _initialized[id(module)] = False


class Live2DMascot(MascotBehaviorMixin, QOpenGLWidget):
    """Mascota Live2D con la misma API pública que MascotWidget."""

    clicked = pyqtSignal()

    def __init__(self, model_path: str, width: int = 260, height: int = 340, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self._model_path = model_path
        self._l2d = _pick_module(model_path)  # runtime v2 o v3 según el modelo
        self._model = None
        self._scale = scale
        self._mood = MascotMood.IDLE
        self._facing = -1
        self._mouth_phase = 0.0

        self._init_window(width, height)
        self._init_timers()
        self._init_behavior()

    # ------------------------------------------------------------------ setup

    def _init_window(self, width, height):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setAutoFillBackground(False)
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)
        self.setFixedSize(width, height)
        self.setToolTip("Lia — clic para abrir, arrastra para mover")

    def _init_timers(self):
        # Render ~60fps
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._tick)
        self._render_timer.start(16)

        # Seguimiento del cursor (look-at), más relajado
        self._look_timer = QTimer(self)
        self._look_timer.timeout.connect(self._update_look)
        self._look_timer.start(33)

    def _on_walk_changed(self, walking: bool):
        # Al empezar a caminar, intenta lanzar una animación de movimiento si existe
        if walking and self._model is not None:
            self._try_random_motion()

    # ---------------------------------------------------------------- OpenGL

    def initializeGL(self):
        try:
            _ensure_live2d_init(self._l2d)
            self._l2d.glInit()
            self._model = self._l2d.LAppModel()
            self._model.LoadModelJson(self._model_path)
            self._model.Resize(self.width(), self.height())
            self._safe(lambda: self._model.SetAutoBlinkEnable(True))
            self._safe(lambda: self._model.SetAutoBreathEnable(True))
            self._safe(lambda: self._model.SetScale(self._scale))
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            print(f"[Live2DMascot] Modelo cargado: {self._model_path}")
        except Exception as e:
            print(f"[Live2DMascot] Error al inicializar el modelo: {e}")
            self._model = None

    def resizeGL(self, w, h):
        if self._model is not None:
            self._safe(lambda: self._model.Resize(w, h))

    def paintGL(self):
        self._l2d.clearBuffer()
        if self._model is None:
            return
        self._drive_mouth()
        self._safe(self._model.Update)
        self._safe(self._model.Draw)

    # --------------------------------------------------------------- animación

    def _tick(self):
        if self._walking:
            self._advance_walk()
        self.update()

    def _update_look(self):
        """El modelo sigue el cursor con la mirada (cuando no se está arrastrando)."""
        if self._model is None or self._is_dragging:
            return
        local = self.mapFromGlobal(QCursor.pos())
        self._safe(lambda: self._model.Drag(local.x(), local.y()))

    def _drive_mouth(self):
        """Mueve la boca cuando Lia está hablando (lip-sync simple)."""
        if self._mood != MascotMood.SPEAKING:
            return
        self._mouth_phase = (self._mouth_phase + 0.5) % math.tau
        opening = (math.sin(self._mouth_phase) * 0.5 + 0.5)
        try:
            self._model.SetParameterValue(self._l2d.StandardParams.ParamMouthOpenY, opening)
        except Exception:
            pass

    # ------------------------------------------------------------------ estado

    def set_mood(self, mood: str):
        if mood != self._mood:
            self._mood = mood
            if mood != MascotMood.IDLE and self._walking:
                self._stop_walk()
            self._apply_mood(mood)

    def set_state(self, state: AssistantState):
        mapping = {
            AssistantState.IDLE: MascotMood.IDLE,
            AssistantState.LISTENING: MascotMood.LISTENING,
            AssistantState.PROCESSING: MascotMood.THINKING,
            AssistantState.RESPONDING: MascotMood.SPEAKING,
        }
        self.set_mood(mapping.get(state, MascotMood.IDLE))

    def _apply_mood(self, mood: str):
        """Refleja el mood en el modelo mediante una expresión, si el modelo las trae."""
        if self._model is None:
            return
        if mood == MascotMood.IDLE:
            self._safe(self._model.ResetExpression)
        else:
            # Usa una expresión aleatoria como reacción; los modelos varían, así que
            # se intenta y si no hay expresiones simplemente no pasa nada.
            self._safe(self._model.SetRandomExpression)

    # ------------------------------------------------------------------ utils

    def _try_random_motion(self):
        self._safe(lambda: self._model.StartRandomMotion())

    @staticmethod
    def _safe(fn):
        try:
            fn()
        except Exception:
            pass
