"""
Burbuja de recordatorio: una notificacion calmada junto a la mascota.

Aparece cuando vence un recordatorio, con el texto y dos acciones: "Listo"
(confirmar que se ha leido) y "Posponer 5 min". No se repite ni parpadea: se
queda en silencio hasta que el usuario actua (con un auto-posponer de seguridad
si se ignora un buen rato).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QPixmap, QPainter, QPen, QGuiApplication

from src.gui import styles


def _clock_icon(size: int = 18) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(styles.ACCENT_SOFT))
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    m = size * 0.12
    p.drawEllipse(QPointF(size / 2, size / 2), size / 2 - m, size / 2 - m)
    p.drawLine(QPointF(size / 2, size / 2), QPointF(size / 2, size * 0.30))
    p.drawLine(QPointF(size / 2, size / 2), QPointF(size * 0.66, size / 2))
    p.end()
    return pm


class ReminderBubble(QWidget):
    done = pyqtSignal()    # el usuario confirma ("Listo")
    snooze = pyqtSignal()  # posponer 5 min

    _AUTO_SNOOZE_MS = 90000  # si se ignora 90s, se pospone solo (no bloquea)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(290)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        card = QFrame(self)
        card.setObjectName("GlassCard")
        card.setStyleSheet(styles.card_style(radius=14))
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(26)
        shadow.setColor(QColor(40, 45, 90, 160))
        shadow.setOffset(0, 3)
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 13, 16, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(7)
        icon = QLabel(card)
        icon.setPixmap(_clock_icon(18))
        icon.setFixedSize(18, 18)
        head.addWidget(icon)
        tag = QLabel("RECORDATORIO", card)
        tag.setStyleSheet(
            "QLabel { color: %s; font-family: %s; font-size: 10px; font-weight: 700;"
            " letter-spacing: 2px; background: transparent; }" % (styles.ACCENT_SOFT, styles.FONT))
        head.addWidget(tag)
        head.addStretch()
        lay.addLayout(head)

        self.message = QLabel("", card)
        self.message.setWordWrap(True)
        self.message.setStyleSheet(
            "QLabel { color: %s; font-family: %s; font-size: 13.5px;"
            " background: transparent; }" % (styles.TEXT, styles.FONT))
        lay.addWidget(self.message)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        self.snooze_btn = QPushButton("Posponer 5 min", card)
        self.snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snooze_btn.setStyleSheet(styles.secondary_button_style())
        self.snooze_btn.clicked.connect(self._on_snooze)
        row.addWidget(self.snooze_btn)
        self.done_btn = QPushButton("Listo", card)
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.setStyleSheet(styles.primary_button_style())
        self.done_btn.clicked.connect(self._on_done)
        row.addWidget(self.done_btn)
        lay.addLayout(row)

        self._auto = QTimer(self)
        self._auto.setSingleShot(True)
        self._auto.timeout.connect(self._on_snooze)

    def show_for(self, text: str, near_widget: QWidget):
        self.message.setText(text)
        self.adjustSize()
        self._position_near(near_widget)
        self.show()
        self.raise_()
        self._auto.start(self._AUTO_SNOOZE_MS)

    def _position_near(self, mascot: QWidget):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        g = mascot.frameGeometry()
        x = g.center().x() - self.width() // 2
        y = g.top() - self.height() - 8
        x = max(screen.left() + 8, min(x, screen.right() - self.width() - 8))
        if y < screen.top() + 8:
            y = g.bottom() + 8
        self.move(x, y)

    def _on_done(self):
        self._auto.stop()
        self.hide()
        self.done.emit()

    def _on_snooze(self):
        self._auto.stop()
        self.hide()
        self.snooze.emit()
