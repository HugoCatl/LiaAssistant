"""
Pantalla de carga (splash) de LIA.

Ventana pequena, sin marco y con la identidad indigo: orbe + titulo "LIA",
un texto de estado y una barra que se va rellenando mientras se cargan los
modulos pesados (Whisper, embeddings, servicios). Sin terminal.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QFrame, QGraphicsDropShadowEffect, QApplication,
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPixmap, QPainter, QRadialGradient, QBrush, QGuiApplication

from src.gui import styles


def _orb_pixmap(size: int = 30) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QPointF(size / 2.0, size / 2.0)
    g = QRadialGradient(c, size / 2.0)
    g.setColorAt(0.0, QColor(199, 210, 254))
    g.setColorAt(1.0, QColor(55, 48, 163))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(g))
    p.drawEllipse(c, size * 0.46, size * 0.46)
    p.end()
    return pm


class LiaSplash(QWidget):
    """Splash con barra de progreso. Usa set_progress() para avanzar."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 168)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        card = QFrame(self)
        card.setObjectName("GlassCard")
        card.setStyleSheet(styles.card_style())
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(40, 45, 90, 150))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(11)
        orb = QLabel(card)
        orb.setPixmap(_orb_pixmap(30))
        orb.setFixedSize(30, 30)
        row.addWidget(orb)
        col = QVBoxLayout()
        col.setSpacing(0)
        title = QLabel("LIA", card)
        title.setStyleSheet(styles.title_style(20))
        sub = QLabel("ASSISTANT", card)
        sub.setStyleSheet(
            "QLabel { color: %s; font-family: %s; font-size: 9px;"
            " letter-spacing: 3px; background: transparent; }" % (styles.TEXT_DIM, styles.FONT))
        col.addWidget(title)
        col.addWidget(sub)
        row.addLayout(col)
        row.addStretch()
        lay.addLayout(row)

        self.status = QLabel("Iniciando…", card)
        self.status.setStyleSheet(styles.label_style(dim=True))
        lay.addWidget(self.status)

        self.bar = QProgressBar(card)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setStyleSheet(
            "QProgressBar { background-color: rgba(255,255,255,0.08);"
            " border: none; border-radius: 3px; }"
            " QProgressBar::chunk { background-color: %s; border-radius: 3px; }" % styles.ACCENT)
        lay.addWidget(self.bar)

        self._center()

    def _center(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2 + screen.left(),
            (screen.height() - self.height()) // 2 + screen.top(),
        )

    def set_progress(self, value: int, text: str = None):
        self.bar.setValue(value)
        if text:
            self.status.setText(text)
        QApplication.processEvents()
