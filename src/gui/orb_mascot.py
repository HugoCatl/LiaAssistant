import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient, QConicalGradient
)

from src.core.state_manager import AssistantState
from src.gui.mascot_behavior import MascotBehaviorMixin, MascotMood


# Paleta por mood: (núcleo claro, color base, acento/halo). Marca Lia = violeta.
_MOOD_COLORS = {
    MascotMood.IDLE:      ("#C9C5FF", "#7F77DD", "#534AB7"),
    MascotMood.CURIOUS:   ("#9FE1CB", "#1D9E75", "#0F6E56"),
    MascotMood.REMINDER:  ("#FAD79A", "#EF9F27", "#854F0B"),
    MascotMood.LISTENING: ("#F3B79E", "#D85A30", "#993C1D"),
    MascotMood.THINKING:  ("#F0C77A", "#BA7517", "#633806"),
    MascotMood.SPEAKING:  ("#A9CEF2", "#378ADD", "#0C447C"),
}


class OrbMascot(MascotBehaviorMixin, QWidget):
    """
    Presencia minimalista y profesional de Lia: un orbe luminoso que late y
    reacciona al estado (estilo Siri/Raycast). No es un personaje ni anda; se
    acopla discreto en una esquina.

    - Núcleo con degradado radial (esfera con profundidad).
    - Halo cónico que rota lentamente (el elemento hipnótico).
    - Respiración continua y efectos por estado (ondas, spinner, anillos).
    - Click -> abre el panel. Arrastre -> mover (con snap al borde).
    """

    clicked = pyqtSignal()

    WIDGET_W = 92
    WIDGET_H = 92

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mood = MascotMood.IDLE

        self._breath = 0.0   # respiración
        self._spin = 0.0     # rotación del halo
        self._fx = 0.0       # fase de efectos (ondas/anillos/spinner)

        self._init_window()
        self._init_timer()
        self._init_behavior()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDGET_W, self.WIDGET_H)
        self.setToolTip("Lia — clic para abrir, arrastra para mover")

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps para una rotación suave

    def _tick(self):
        self._breath = (self._breath + 0.03) % math.tau
        self._fx = (self._fx + 0.06) % math.tau
        # El halo gira más rápido cuando Lia está activa
        speed = 0.010 if self._mood == MascotMood.IDLE else 0.028
        self._spin = (self._spin + speed) % math.tau
        self.update()

    # ------------------------------------------------------------------ estado

    def set_mood(self, mood: str):
        if mood != self._mood:
            self._mood = mood
            self.update()

    def set_state(self, state: AssistantState):
        mapping = {
            AssistantState.IDLE: MascotMood.IDLE,
            AssistantState.LISTENING: MascotMood.LISTENING,
            AssistantState.PROCESSING: MascotMood.THINKING,
            AssistantState.RESPONDING: MascotMood.SPEAKING,
        }
        self.set_mood(mapping.get(state, MascotMood.IDLE))

    # ---------------------------------------------------------------- pintado

    def paintEvent(self, event):
        light_hex, base_hex, accent_hex = _MOOD_COLORS.get(
            self._mood, _MOOD_COLORS[MascotMood.IDLE]
        )
        light, base, accent = QColor(light_hex), QColor(base_hex), QColor(accent_hex)

        cx, cy = self.width() / 2.0, self.height() / 2.0
        breath = math.sin(self._breath)
        R = self.width() * 0.235 + breath * 1.4  # radio del núcleo (relativo) con respiración

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        # 1) Resplandor exterior (bloom) que late
        glow_r = R * 1.95
        glow = QRadialGradient(cx, cy, glow_r)
        g0 = QColor(accent); g0.setAlpha(int(70 + 35 * (breath * 0.5 + 0.5)))
        gmid = QColor(accent); gmid.setAlpha(28)
        gend = QColor(accent); gend.setAlpha(0)
        glow.setColorAt(0.0, g0)
        glow.setColorAt(0.5, gmid)
        glow.setColorAt(1.0, gend)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # 2) Efectos por estado detrás del núcleo
        self._draw_state_effects(p, cx, cy, R, accent, base)

        # 3) Halo cónico rotatorio (elemento hipnótico)
        self._draw_rotating_halo(p, cx, cy, R * 1.28, light, accent)

        # 4) Núcleo: esfera con degradado radial (foco desplazado = volumen)
        core = QRadialGradient(cx - R * 0.32, cy - R * 0.34, R * 1.5)
        core.setColorAt(0.0, light)
        core.setColorAt(0.55, base)
        edge = QColor(accent); edge.setAlpha(255)
        core.setColorAt(1.0, edge)
        p.setBrush(QBrush(core))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # 5) Brillo especular sutil
        spec = QRadialGradient(cx - R * 0.34, cy - R * 0.4, R * 0.7)
        s0 = QColor(255, 255, 255, 150); s1 = QColor(255, 255, 255, 0)
        spec.setColorAt(0.0, s0)
        spec.setColorAt(1.0, s1)
        p.setBrush(QBrush(spec))
        p.drawEllipse(QPointF(cx - R * 0.3, cy - R * 0.34), R * 0.5, R * 0.42)

        # 6) Pip de notificación para recordatorio/curiosidad
        if self._mood in (MascotMood.REMINDER, MascotMood.CURIOUS):
            self._draw_pip(p, cx + R * 0.72, cy - R * 0.72, accent)

        p.end()

    def _draw_rotating_halo(self, p, cx, cy, radius, light, accent):
        conical = QConicalGradient(cx, cy, math.degrees(self._spin))
        bright = QColor(light); bright.setAlpha(230)
        dim = QColor(accent); dim.setAlpha(40)
        faint = QColor(accent); faint.setAlpha(10)
        conical.setColorAt(0.0, bright)
        conical.setColorAt(0.25, dim)
        conical.setColorAt(0.5, faint)
        conical.setColorAt(0.75, dim)
        conical.setColorAt(1.0, bright)
        pen = QPen(QBrush(conical), 4.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radius, radius)
        p.setPen(Qt.PenStyle.NoPen)

    def _draw_state_effects(self, p, cx, cy, R, accent, base):
        if self._mood == MascotMood.LISTENING:
            # Ondas concéntricas expansivas (sensación de "escuchando")
            for i in range(3):
                t = (self._fx / math.tau + i / 3.0) % 1.0
                rr = R * 1.1 + t * R * 1.6
                a = int(120 * (1.0 - t))
                c = QColor(accent); c.setAlpha(max(0, a))
                pen = QPen(c, 2.0); p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)
            p.setPen(Qt.PenStyle.NoPen)
        elif self._mood == MascotMood.THINKING:
            # Arco-spinner girando rápido alrededor del núcleo
            rr = R * 1.5
            pen = QPen(QColor(accent), 3.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            start = int(math.degrees(self._fx * 3.0)) % 360
            p.drawArc(QRectF(cx - rr, cy - rr, rr * 2, rr * 2),
                      start * 16, 100 * 16)
            p.setPen(Qt.PenStyle.NoPen)
        elif self._mood == MascotMood.SPEAKING:
            # Anillos que laten con el habla
            for i in range(2):
                pulse = math.sin(self._fx * 2.2 + i * 1.4) * 0.5 + 0.5
                rr = R * (1.12 + i * 0.22) + pulse * 4
                a = int(150 - i * 60)
                c = QColor(accent); c.setAlpha(max(0, a))
                pen = QPen(c, 2.5); p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)
            p.setPen(Qt.PenStyle.NoPen)

    def _draw_pip(self, p, x, y, accent):
        pulse = math.sin(self._fx * 2.0) * 0.5 + 0.5
        # halo del pip
        h = QColor(accent); h.setAlpha(int(80 * pulse))
        p.setBrush(QBrush(h))
        p.drawEllipse(QPointF(x, y), 9, 9)
        # punto sólido
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QPointF(x, y), 5.2, 5.2)
        p.setBrush(QBrush(accent))
        p.drawEllipse(QPointF(x, y), 3.4, 3.4)
