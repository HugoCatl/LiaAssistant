"""
Vista de grafo del vault dentro de la propia app (Fase 10).

Hasta ahora el grafo solo se "veía" abriendo Obsidian; esta ventana lo dibuja
con los medios de la casa: scan del jardinero para nodos/aristas, layout de
fuerzas (Fruchterman-Reingold) en numpy puro y render QPainter con la estética
indigo. Sin dependencias nuevas.
"""
import math

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient

from src.gui import styles


def build_graph(notes: dict):
    """
    A partir del scan del jardinero ({titulo: {links}}) devuelve
    (titles, edges) con solo aristas entre notas existentes (sin rotas).
    """
    from src.storage.obsidian_manager import _fold
    by_fold = {_fold(t): t for t in notes}
    titles = sorted(notes)
    edges = set()
    for title, info in notes.items():
        for link in info["links"]:
            real = by_fold.get(_fold(link))
            if real and real != title:
                edges.add(tuple(sorted((title, real))))
    return titles, sorted(edges)


def layout_graph(titles, edges, iters: int = 120, seed: int = 1) -> dict:
    """
    Layout de fuerzas (Fruchterman-Reingold) determinista en el cuadrado unidad.
    Devuelve {titulo: (x, y)} con x,y en [0.03, 0.97].
    """
    n = len(titles)
    if n == 0:
        return {}
    if n == 1:
        return {titles[0]: (0.5, 0.5)}

    rng = np.random.default_rng(seed)
    pos = rng.uniform(0.15, 0.85, (n, 2))
    idx = {t: i for i, t in enumerate(titles)}
    k = 0.35 / math.sqrt(n)   # distancia "ideal" entre nodos
    temp = 0.12               # paso máximo, se enfría por iteración

    for _ in range(iters):
        # Repulsión entre todos los pares
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(delta, axis=2) + 1e-9
        disp = ((k * k / dist)[:, :, None] * (delta / dist[:, :, None])).sum(axis=1)

        # Atracción por arista
        for a, b in edges:
            i, j = idx[a], idx[b]
            d = pos[i] - pos[j]
            dd = float(np.linalg.norm(d)) + 1e-9
            f = (dd * dd / k) * (d / dd)
            disp[i] -= f
            disp[j] += f

        length = np.linalg.norm(disp, axis=1, keepdims=True) + 1e-9
        pos += (disp / length) * np.minimum(length, temp)
        pos = np.clip(pos, 0.03, 0.97)
        temp *= 0.97

    # Reescalar para aprovechar todo el lienzo (el FR tiende a agruparse)
    mins, maxs = pos.min(axis=0), pos.max(axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    pos = 0.06 + 0.88 * (pos - mins) / span

    return {titles[i]: (float(pos[i, 0]), float(pos[i, 1])) for i in range(n)}


class _GraphCanvas(QWidget):
    """
    Lienzo dinámico: los nodos "se asientan" con una animación al abrir y
    después se pueden ARRASTRAR con el ratón (las aristas siguen al nodo).
    """

    _MARGIN = 34
    _HIT_RADIUS = 14  # px de tolerancia para agarrar un nodo

    def __init__(self, titles, edges, positions, parent=None):
        super().__init__(parent)
        self.titles = titles
        self.edges = edges
        self.positions = dict(positions)   # destino (y estado final editable)
        self.degree = {t: 0 for t in titles}
        for a, b in edges:
            self.degree[a] += 1
            self.degree[b] += 1
        self.setMinimumSize(420, 320)
        self.setMouseTracking(True)        # cursor de mano al pasar por un nodo
        self._drag_node = None

        # Animación de asentado: de un punto cercano al centro a su posición
        import random
        rnd = random.Random(7)
        self._start = {
            t: (0.5 + (rnd.random() - 0.5) * 0.16, 0.5 + (rnd.random() - 0.5) * 0.16)
            for t in titles
        }
        self._t = 0.0
        from PyQt6.QtCore import QTimer
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick)
        self._anim.start(16)

    # ------------------------------------------------------------- animación

    def _tick(self):
        self._t = min(1.0, self._t + 0.035)
        if self._t >= 1.0:
            self._anim.stop()
        self.update()

    def _now(self, title):
        """Posición actual del nodo (interpolada durante el asentado)."""
        if self._t >= 1.0:
            return self.positions[title]
        e = 1.0 - (1.0 - self._t) ** 3   # ease-out cúbico
        sx, sy = self._start[title]
        fx, fy = self.positions[title]
        return (sx + (fx - sx) * e, sy + (fy - sy) * e)

    # ------------------------------------------------------------- coordenadas

    def _to_px(self, xy):
        m = self._MARGIN
        w, h = self.width() - 2 * m, self.height() - 2 * m
        return QPointF(m + xy[0] * w, m + xy[1] * h)

    def _to_unit(self, point):
        m = self._MARGIN
        w, h = max(1, self.width() - 2 * m), max(1, self.height() - 2 * m)
        return (
            min(1.0, max(0.0, (point.x() - m) / w)),
            min(1.0, max(0.0, (point.y() - m) / h)),
        )

    def _node_at(self, point):
        """Título del nodo bajo el cursor, o None."""
        best, best_d = None, self._HIT_RADIUS
        for t in self.titles:
            c = self._to_px(self._now(t))
            d = math.hypot(c.x() - point.x(), c.y() - point.y())
            if d <= best_d:
                best, best_d = t, d
        return best

    # ------------------------------------------------------------- interacción

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            node = self._node_at(event.position())
            if node:
                if self._t < 1.0:
                    # Congela la animación donde está (sin saltos al agarrar)
                    for t in self.titles:
                        self.positions[t] = self._now(t)
                self._anim.stop()
                self._t = 1.0            # fija el layout y permite manipular
                self._drag_node = node
                event.accept()
                return
        event.ignore()                   # deja que la ventana se arrastre

    def mouseMoveEvent(self, event):
        if self._drag_node is not None:
            self.positions[self._drag_node] = self._to_unit(event.position())
            self.update()
            event.accept()
            return
        # Cursor de mano sobre los nodos
        over = self._node_at(event.position())
        self.setCursor(Qt.CursorShape.OpenHandCursor if over
                       else Qt.CursorShape.ArrowCursor)
        event.ignore()

    def mouseReleaseEvent(self, event):
        if self._drag_node is not None:
            self._drag_node = None
            event.accept()
            return
        event.ignore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Aristas
        pen = QPen(QColor(129, 140, 248, 70))
        pen.setWidthF(1.2)
        p.setPen(pen)
        for a, b in self.edges:
            p.drawLine(self._to_px(self._now(a)), self._to_px(self._now(b)))

        # Nodos (radio según conexiones) + etiquetas
        max_deg = max(self.degree.values(), default=0) or 1
        font = p.font()
        font.setPointSize(8)
        p.setFont(font)
        for t in self.titles:
            c = self._to_px(self._now(t))
            r = 5.0 + 6.0 * (self.degree[t] / max_deg)
            g = QRadialGradient(c, r * 1.6)
            hub = self.degree[t] == max_deg and max_deg > 0
            g.setColorAt(0.0, QColor(199, 210, 254) if hub else QColor(165, 180, 252))
            g.setColorAt(1.0, QColor(79, 70, 229) if hub else QColor(55, 48, 163))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawEllipse(c, r, r)

            p.setPen(QColor(205, 210, 228, 200))
            label = t if len(t) <= 22 else t[:21] + "…"
            p.drawText(
                QRectF(c.x() - 70, c.y() + r + 2, 140, 14),
                Qt.AlignmentFlag.AlignHCenter, label,
            )
        p.end()


class GraphWindow(QWidget):
    """Ventana glassmorphic con el grafo de la memoria."""

    def __init__(self, notes: dict, parent=None):
        super().__init__(parent)
        self._drag = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        card = QFrame(self)
        card.setObjectName("GlassCard")
        card.setStyleSheet(styles.card_style())
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(26)
        shadow.setColor(QColor(99, 102, 241, 70))
        shadow.setOffset(0, 0)
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 12, 18, 14)

        header = QHBoxLayout()
        title = QLabel("TU GRAFO", card)
        title.setStyleSheet(styles.title_style(13))
        header.addWidget(title)
        header.addStretch(1)
        close = QLabel("✕", card)
        close.setStyleSheet(
            f"QLabel {{ color: {styles.TEXT_DIM}; font-size: 13px; }}")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.mousePressEvent = lambda e: self.close()
        header.addWidget(close)
        lay.addLayout(header)

        titles, edges = build_graph(notes)
        if len(titles) < 2:
            empty = QLabel("Aún hay muy pocas notas para dibujar el grafo.", card)
            empty.setStyleSheet(styles.label_style(dim=True))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumSize(420, 200)
            lay.addWidget(empty)
        else:
            positions = layout_graph(titles, edges)
            lay.addWidget(_GraphCanvas(titles, edges, positions, card))

        sub = QLabel(f"{len(titles)} notas · {len(edges)} conexiones", card)
        sub.setStyleSheet(styles.label_style(dim=True))
        lay.addWidget(sub)

        self.resize(560, 460)

    # Arrastre de la ventana sin marco
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, event):
        self._drag = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
