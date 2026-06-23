import math
import random

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QPainterPath, QPolygonF
)

from src.core.state_manager import AssistantState
from src.gui.mascot_behavior import MascotBehaviorMixin, MascotMood, _Pose


# Pelaje del gato (tabby naranja) — constante; el mood solo cambia acentos/efectos.
FUR = "#E8A85C"
FUR_LIGHT = "#F7E2C4"
STRIPE = "#C77B3A"
OUTLINE = "#7A3F16"
EAR_INNER = "#F0997B"
EYE = "#2FA37A"
PUPIL = "#1A1411"
NOSE = "#D4537E"

# Acento (efectos y resplandor) por mood
_MOOD_ACCENT = {
    MascotMood.IDLE:      "#B4B2A9",
    MascotMood.CURIOUS:   "#1D9E75",
    MascotMood.REMINDER:  "#EF9F27",
    MascotMood.LISTENING: "#D85A30",
    MascotMood.THINKING:  "#BA7517",
    MascotMood.SPEAKING:  "#378ADD",
}


class MascotWidget(MascotBehaviorMixin, QWidget):
    """
    Mascota gato de Lia que vive en el borde inferior del escritorio.

    - Ventana frameless, translúcida, siempre visible.
    - Gato dibujado con QPainter (vista lateral): pose sentado y caminando.
    - Pasea por el borde inferior cuando está en reposo; se detiene al abrir el panel.
    - Cambia expresión según el estado de Lia.
    - Click -> abre el panel. Arrastre -> mover (con snap al borde).

    El comportamiento de ventana (paseo, clic/arrastre, snap) lo aporta
    MascotBehaviorMixin para compartirlo con la variante Live2D.
    """

    clicked = pyqtSignal()

    WIDGET_W = 170
    WIDGET_H = 140

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mood = MascotMood.IDLE
        self._pose = _Pose.SIT
        self._facing = -1  # -1 mira a la izquierda (esquina derecha), 1 a la derecha

        # Fases de animación
        self._phase = 0.0       # Respiración / bob
        self._wave_phase = 0.0  # Cola, patas, boca, efectos
        self._leg_phase = 0.0    # Ciclo de patas al caminar
        self._blinking = False
        self._ear_twitch = 0.0

        self._init_window()
        self._init_timers()
        self._init_behavior()  # paseo + clic/arrastre (mixin)

    # ------------------------------------------------------------------ setup

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDGET_W, self.WIDGET_H)
        self.setToolTip("Lia — clic para abrir, arrastra para mover")

    def _init_timers(self):
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(33)

        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._do_blink)
        self._schedule_blink()

    def _on_walk_changed(self, walking: bool):
        self._pose = _Pose.WALK if walking else _Pose.SIT

    # -------------------------------------------------------------- animation

    def _tick(self):
        self._phase = (self._phase + 0.045) % math.tau
        self._wave_phase = (self._wave_phase + 0.16) % math.tau
        self._ear_twitch = max(0.0, self._ear_twitch - 0.04)
        if self._walking:
            self._leg_phase = (self._leg_phase + 0.35) % math.tau
            self._advance_walk()
        self.update()

    def _schedule_blink(self):
        self._blink_timer.start(random.randint(2200, 5200))

    def _do_blink(self):
        self._blinking = True
        self.update()
        QTimer.singleShot(130, self._end_blink)

    def _end_blink(self):
        self._blinking = False
        if random.random() < 0.4:
            self._ear_twitch = 1.0  # de vez en cuando, mueve la oreja al parpadear
        self.update()
        self._schedule_blink()

    # ------------------------------------------------------------------ state

    def set_mood(self, mood: str):
        if mood != self._mood:
            self._mood = mood
            if mood != MascotMood.IDLE and self._walking:
                self._stop_walk()  # deja de pasear si Lia se pone a trabajar
            self.update()

    def set_state(self, state: AssistantState):
        mapping = {
            AssistantState.IDLE: MascotMood.IDLE,
            AssistantState.LISTENING: MascotMood.LISTENING,
            AssistantState.PROCESSING: MascotMood.THINKING,
            AssistantState.RESPONDING: MascotMood.SPEAKING,
        }
        self.set_mood(mapping.get(state, MascotMood.IDLE))

    # ---------------------------------------------------------------- painting

    def paintEvent(self, event):
        accent = QColor(_MOOD_ACCENT.get(self._mood, _MOOD_ACCENT[MascotMood.IDLE]))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Resplandor de mood (sutil, detrás del gato)
        if self._mood != MascotMood.IDLE:
            glow = QColor(accent)
            glow.setAlpha(34)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(self.width() / 2, self.height() / 2 + 6), 64, 60)

        # Espejar según dirección (dibujamos siempre mirando a la derecha)
        p.save()
        if self._facing == -1:
            p.translate(self.width(), 0)
            p.scale(-1, 1)

        if self._pose == _Pose.WALK:
            self._draw_cat_walk(p, accent)
        else:
            self._draw_cat_sit(p, accent)

        p.restore()
        p.end()

    # --- piezas comunes ----------------------------------------------------

    def _fur_pen(self, w=2.4):
        pen = QPen(QColor(OUTLINE))
        pen.setWidthF(w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _draw_tail(self, p, base_x, base_y, curl):
        """Cola curvada que ondea. 'curl' modula la punta."""
        sway = math.sin(self._wave_phase) * 7.0
        path = QPainterPath()
        path.moveTo(base_x, base_y)
        path.cubicTo(base_x - 26, base_y - 4,
                     base_x - 34, base_y - 34,
                     base_x - 18 + sway, base_y - 52 - curl)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Contorno oscuro (grueso) primero, luego relleno encima para dar volumen
        outline = QPen(QColor(OUTLINE), 12.0)
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(outline)
        p.drawPath(path)
        fur = QPen(QColor(FUR), 8.0)
        fur.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(fur)
        p.drawPath(path)
        # Punta clara
        tip = QPen(QColor(FUR_LIGHT), 6.0)
        tip.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(tip)
        tip_path = QPainterPath()
        tip_path.moveTo(base_x - 30 + sway, base_y - 44 - curl)
        tip_path.quadTo(base_x - 26 + sway, base_y - 50 - curl,
                        base_x - 18 + sway, base_y - 52 - curl)
        p.drawPath(tip_path)

    def _draw_head_and_face(self, p, hx, hy, hr, accent):
        # Orejas (triángulos) — la trasera y la delantera
        twitch = self._ear_twitch * 4.0
        perked = self._mood in (MascotMood.CURIOUS, MascotMood.REMINDER)
        ear_lift = 4.0 if perked else 0.0

        def ear(cx_base, tilt):
            apex = QPointF(cx_base + tilt, hy - hr - 14 - ear_lift - twitch)
            left = QPointF(cx_base - 11, hy - hr + 4)
            right = QPointF(cx_base + 12, hy - hr + 2)
            tri = QPolygonF([left, apex, right])
            p.setPen(self._fur_pen(2.2))
            p.setBrush(QBrush(QColor(FUR)))
            p.drawPolygon(tri)
            # interior rosa
            inner = QPolygonF([
                QPointF(cx_base - 5, hy - hr + 1),
                QPointF(apex.x(), apex.y() + 7),
                QPointF(cx_base + 6, hy - hr - 1),
            ])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(EAR_INNER)))
            p.drawPolygon(inner)

        ear(hx - 9, -3)   # oreja trasera
        ear(hx + 13, 3)   # oreja delantera

        # Cabeza
        p.setPen(self._fur_pen(2.4))
        p.setBrush(QBrush(QColor(FUR)))
        p.drawEllipse(QPointF(hx, hy), hr, hr * 0.94)

        # Hocico claro
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(FUR_LIGHT)))
        p.drawEllipse(QPointF(hx + hr * 0.45, hy + 6), hr * 0.5, hr * 0.42)

        # Rayas en la frente
        pen = self._fur_pen(2.0)
        pen.setColor(QColor(STRIPE))
        p.setPen(pen)
        p.drawLine(QPointF(hx - 4, hy - hr * 0.9), QPointF(hx - 6, hy - hr * 0.55))
        p.drawLine(QPointF(hx + 4, hy - hr * 0.92), QPointF(hx + 5, hy - hr * 0.55))

        # Ojo (vista lateral: uno visible) en el lado delantero
        eye_x = hx + hr * 0.32
        eye_y = hy - 2
        if self._blinking:
            pen = self._fur_pen(2.2)
            p.setPen(pen)
            p.drawLine(QPointF(eye_x - 5, eye_y), QPointF(eye_x + 5, eye_y))
        else:
            big = self._mood in (MascotMood.CURIOUS, MascotMood.REMINDER)
            rx, ry = (6.0, 7.5) if big else (5.2, 6.6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(EYE)))
            p.drawEllipse(QPointF(eye_x, eye_y), rx, ry)
            # Pupila (rendija felina)
            p.setBrush(QBrush(QColor(PUPIL)))
            slit_w = 2.6 if big else 1.8
            p.drawEllipse(QPointF(eye_x, eye_y), slit_w, ry - 0.5)
            # Brillo
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawEllipse(QPointF(eye_x + 1.6, eye_y - 2.4), 1.5, 1.5)

        # Nariz (triángulo rosa) en la punta del hocico
        nose_x = hx + hr * 0.9
        nose_y = hy + 4
        nose = QPolygonF([
            QPointF(nose_x - 3, nose_y - 2),
            QPointF(nose_x + 3, nose_y - 2),
            QPointF(nose_x, nose_y + 2),
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(NOSE)))
        p.drawPolygon(nose)

        # Boca
        pen = self._fur_pen(1.8)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self._mood == MascotMood.SPEAKING:
            open_amt = (math.sin(self._wave_phase) * 0.5 + 0.5) * 5 + 1.5
            p.setBrush(QBrush(QColor("#7A2E3E")))
            p.drawEllipse(QPointF(nose_x - 1, nose_y + 7), 3.0, open_amt / 2 + 1.0)
            p.setBrush(Qt.BrushStyle.NoBrush)
        else:
            mp = QPainterPath()
            mp.moveTo(nose_x, nose_y + 2)
            mp.quadTo(nose_x - 2, nose_y + 7, nose_x - 6, nose_y + 6)
            mp.moveTo(nose_x, nose_y + 2)
            mp.quadTo(nose_x + 2, nose_y + 7, nose_x + 5, nose_y + 6)
            p.drawPath(mp)

        # Bigotes
        pen = QPen(QColor(255, 255, 255, 180))
        pen.setWidthF(1.3)
        p.setPen(pen)
        for dy in (-2, 2, 6):
            p.drawLine(QPointF(nose_x - 1, nose_y + dy),
                       QPointF(nose_x + 20, nose_y + dy - 3 + dy * 0.3))

        # Efectos de mood sobre la cabeza
        self._draw_mood_effect(p, hx, hy - hr, accent)

    def _draw_mood_effect(self, p, cx, top_y, accent):
        if self._mood == MascotMood.THINKING:
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(3):
                ph = self._wave_phase + i * 0.7
                a = int(120 + 120 * (math.sin(ph) * 0.5 + 0.5))
                c = QColor(accent); c.setAlpha(min(255, a))
                p.setBrush(QBrush(c))
                p.drawEllipse(QPointF(cx + i * 9 - 4, top_y - 14 - i * 4), 3.0, 3.0)
        elif self._mood == MascotMood.REMINDER:
            bob = math.sin(self._wave_phase) * 2.0
            pen = QPen(QColor(accent)); pen.setWidthF(4.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(cx, top_y - 26 + bob), QPointF(cx, top_y - 14 + bob))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(accent)))
            p.drawEllipse(QPointF(cx, top_y - 8 + bob), 2.6, 2.6)
        elif self._mood == MascotMood.LISTENING:
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(3):
                t = (self._wave_phase / math.tau + i / 3.0) % 1.0
                a = int(150 * (1 - t))
                c = QColor(accent); c.setAlpha(max(0, a))
                pen = QPen(c); pen.setWidthF(2.0)
                p.setPen(pen)
                r = 10 + t * 20
                p.drawEllipse(QPointF(cx + 26, top_y + 18), r, r)

    def _body_stripes(self, p, rect: QRectF):
        """Rayas de tabby dentro del cuerpo (requiere clip al cuerpo)."""
        pen = self._fur_pen(2.4)
        pen.setColor(QColor(STRIPE))
        p.setPen(pen)
        x0 = rect.left() + rect.width() * 0.25
        for i in range(4):
            x = x0 + i * (rect.width() * 0.16)
            p.drawArc(QRectF(x - 10, rect.top() - 6, 20, rect.height() * 0.6),
                      30 * 16, 120 * 16)

    # --- pose sentado ------------------------------------------------------

    def _draw_cat_sit(self, p, accent):
        bob = math.sin(self._phase) * 1.6
        ground = self.WIDGET_H - 16

        # Sombra
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 40)))
        p.drawEllipse(QPointF(70, ground + 8), 52, 8)

        # Cola (detrás)
        self._draw_tail(p, 40, ground - 14, 0)

        # Silueta del cuerpo (ancas + torso) unidas para un contorno limpio
        body = QPainterPath()
        body.addEllipse(QRectF(28, ground - 64 + bob, 78, 70))      # ancas
        body.addEllipse(QRectF(70, ground - 92 + bob, 56, 80))      # torso hacia la cabeza
        body = body.simplified()
        p.setPen(self._fur_pen(2.4))
        p.setBrush(QBrush(QColor(FUR)))
        p.drawPath(body)

        # Vientre claro + rayas (clip al cuerpo)
        p.save()
        p.setClipPath(body)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(FUR_LIGHT)))
        p.drawEllipse(QRectF(74, ground - 70 + bob, 44, 78))
        self._body_stripes(p, QRectF(28, ground - 64 + bob, 78, 60))
        p.restore()

        # Patas delanteras (delante del pecho)
        p.setPen(self._fur_pen(2.2))
        p.setBrush(QBrush(QColor(FUR)))
        for lx in (84, 100):
            leg = QPainterPath()
            leg.addRoundedRect(QRectF(lx, ground - 30 + bob, 13, 34 - bob), 6, 6)
            p.drawPath(leg)
        # Patitas (paws)
        p.setBrush(QBrush(QColor(FUR_LIGHT)))
        for lx in (84, 100):
            p.drawEllipse(QRectF(lx - 1, ground - 2, 16, 8))

        # Cabeza y cara
        self._draw_head_and_face(p, 104, ground - 86 + bob, 26, accent)

    # --- pose caminando ----------------------------------------------------

    def _draw_cat_walk(self, p, accent):
        bob = abs(math.sin(self._leg_phase)) * 2.5
        ground = self.WIDGET_H - 16
        body_cy = ground - 42 - bob

        # Sombra
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 40)))
        p.drawEllipse(QPointF(80, ground + 8), 56, 7)

        # Cola (detrás), más horizontal al caminar
        self._draw_tail(p, 36, body_cy + 6, 6)

        # Patas (4) animadas, detrás del cuerpo
        p.setPen(self._fur_pen(5.0))
        leg_defs = [(58, 0.0), (70, math.pi), (108, math.pi), (120, 0.0)]
        for lx, off in leg_defs:
            swing = math.sin(self._leg_phase + off) * 7
            top = QPointF(lx, body_cy + 12)
            foot = QPointF(lx + swing, ground + 2)
            p.drawLine(top, foot)
            p.setPen(self._fur_pen(2.0))
            p.setBrush(QBrush(QColor(FUR_LIGHT)))
            p.drawEllipse(QPointF(foot.x(), foot.y()), 4, 3)
            p.setPen(self._fur_pen(5.0))

        # Cuerpo horizontal
        body = QPainterPath()
        body.addEllipse(QRectF(40, body_cy - 22, 92, 46))
        body = body.simplified()
        p.setPen(self._fur_pen(2.4))
        p.setBrush(QBrush(QColor(FUR)))
        p.drawPath(body)

        # Vientre + rayas
        p.save()
        p.setClipPath(body)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(FUR_LIGHT)))
        p.drawEllipse(QRectF(46, body_cy + 2, 80, 24))
        self._body_stripes(p, QRectF(40, body_cy - 22, 92, 40))
        p.restore()

        # Cabeza al frente
        self._draw_head_and_face(p, 132, body_cy - 16, 24, accent)

    # La interacción de ratón (clic/arrastre/snap) y el paseo los aporta
    # MascotBehaviorMixin.
