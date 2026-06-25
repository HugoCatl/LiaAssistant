"""
Panel de información/acciones rápidas (sustituye al QMenu plano).

Popup glassmorphic con secciones y filas de icono + título + subtítulo, en el
mismo lenguaje visual que el resto de la app. Se cierra al hacer clic fuera o al
elegir una opción.
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor

from src.gui import styles


class _Row(QFrame):
    """Fila clicable: emoji + título + subtítulo, con resaltado al pasar el ratón."""

    def __init__(self, emoji, title, subtitle, callback, danger=False, parent=None):
        super().__init__(parent)
        self._callback = callback
        self.setObjectName("InfoRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QFrame#InfoRow { background: transparent; border-radius: 9px; }"
            "QFrame#InfoRow:hover { background-color: rgba(99,102,241,0.16); }"
        )
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 7, 12, 7)
        h.setSpacing(11)

        icon = QLabel(emoji)
        icon.setStyleSheet("QLabel { background: transparent; font-size: 16px; }")
        icon.setFixedWidth(22)
        icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        h.addWidget(icon)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        ttl = QLabel(title)
        ttl_color = styles.DANGER if danger else styles.TEXT
        ttl.setStyleSheet(
            f"QLabel {{ color: {ttl_color}; background: transparent;"
            f" font-family: {styles.FONT}; font-size: 13px; font-weight: 600; }}"
        )
        col.addWidget(ttl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(
                f"QLabel {{ color: {styles.TEXT_DIM}; background: transparent;"
                f" font-family: {styles.FONT}; font-size: 11px; }}"
            )
            col.addWidget(sub)
        h.addLayout(col)
        h.addStretch(1)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            if self._callback:
                self._callback()
            win.close()
        event.accept()


class InfoPanel(QFrame):
    """Popup de acciones rápidas anclado bajo un botón."""

    def __init__(self, sections, footer=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        card = QFrame(self)
        card.setObjectName("InfoCard")
        card.setStyleSheet(
            f"QFrame#InfoCard {{ background-color: {styles.CARD_BG};"
            f" border: 1px solid {styles.CARD_BORDER}; border-radius: 14px; }}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(99, 102, 241, 70))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        v = QVBoxLayout(card)
        v.setContentsMargins(8, 10, 8, 10)
        v.setSpacing(2)

        for i, (header, items) in enumerate(sections):
            if i > 0:
                v.addWidget(self._divider())
            if header:
                v.addWidget(self._section_label(header))
            for it in items:
                v.addWidget(_Row(
                    it["emoji"], it["title"], it.get("subtitle"),
                    it.get("callback"), danger=it.get("danger", False),
                ))

        if footer:
            v.addWidget(self._divider())
            foot = QLabel(footer)
            foot.setWordWrap(True)
            foot.setStyleSheet(
                f"QLabel {{ color: {styles.TEXT_DIM}; background: transparent;"
                f" font-family: {styles.FONT}; font-size: 10px; padding: 2px 10px; }}"
            )
            v.addWidget(foot)

        root.addWidget(card)
        self.setFixedWidth(320)

    def _section_label(self, text):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            f"QLabel {{ color: {styles.ACCENT_SOFT}; background: transparent;"
            f" font-family: {styles.FONT}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1.5px; padding: 6px 10px 2px 10px; }}"
        )
        return lbl

    def _divider(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("QFrame { background-color: rgba(99,102,241,0.18); border: none; }")
        return line

    def show_below(self, anchor):
        """Muestra el popup alineado bajo (y a la derecha de) un widget ancla."""
        self.adjustSize()
        top_right = anchor.mapToGlobal(QPoint(anchor.width(), anchor.height()))
        x = top_right.x() - self.width() + 12
        y = top_right.y() + 2
        self.move(max(0, x), y)
        self.show()
