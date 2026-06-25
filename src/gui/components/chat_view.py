"""
Vista de conversacion con burbujas reales (estilo WhatsApp / ChatGPT).

Cada mensaje es su propia tarjeta redondeada: los del usuario a la derecha en
indigo; los de Lia a la izquierda con su mini-orbe. Mantiene el streaming token a
token y el render Markdown al cerrar el turno. Pulido: indicador "escribiendo…"
mientras Lia piensa y marca de tiempo discreta bajo cada mensaje.
"""
from datetime import datetime

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QRadialGradient, QColor, QBrush

from src.gui import styles
from src.gui.md_render import markdown_to_html


def _now_hm() -> str:
    return datetime.now().strftime("%H:%M")


def _orb_pixmap(size: int = 20) -> QPixmap:
    """Mini-orbe indigo como avatar de Lia (mismo lenguaje visual que la mascota)."""
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


class ChatBubble(QFrame):
    """Una burbuja de mensaje. role: 'user' | 'lia'."""

    def __init__(self, role: str, parent=None):
        super().__init__(parent)
        self.role = role
        self._raw = ""
        self._typing = False
        self._typing_timer = None
        self._dots = 0
        self.setObjectName("UserBubble" if role == "user" else "LiaBubble")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setOpenExternalLinks(True)
        self.label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(13, 9, 13, 9)
        lay.setSpacing(0)
        lay.addWidget(self.label)
        self.setStyleSheet(self._style())

    def _style(self) -> str:
        if self.role == "user":
            return (
                f"QFrame#UserBubble {{ background-color: {styles.BUBBLE_USER_BG};"
                f" border: 1px solid {styles.BUBBLE_USER_BORDER};"
                f" border-radius: 14px; }}"
                f" QLabel {{ color: {styles.TEXT}; background: transparent;"
                f" font-family: {styles.FONT}; font-size: 14px; }}"
            )
        return (
            f"QFrame#LiaBubble {{ background-color: {styles.BUBBLE_LIA_BG};"
            f" border: 1px solid {styles.BUBBLE_LIA_BORDER};"
            f" border-radius: 14px; }}"
            f" QLabel {{ color: {styles.TEXT}; background: transparent;"
            f" font-family: {styles.FONT}; font-size: 14px; }}"
        )

    def set_plain(self, text: str):
        self._raw = text
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setText(text)

    def append_plain(self, token: str):
        self._raw += token
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setText(self._raw)

    def set_markdown(self, text: str):
        self._raw = text
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setText(markdown_to_html(text))

    def is_empty(self) -> bool:
        return not self._raw.strip()

    # --------------------------------------------------------- "escribiendo…"

    def start_typing(self):
        """Muestra puntos animados mientras Lia aún no ha emitido texto."""
        self._typing = True
        self._dots = 0
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self._typing_timer = QTimer(self)
        self._typing_timer.timeout.connect(self._tick_typing)
        self._typing_timer.start(380)
        self._tick_typing()

    def _tick_typing(self):
        self._dots = (self._dots % 3) + 1
        visibles = "•" * self._dots
        # puntos ocultos para que el ancho no salte mientras animan
        ocultos = "•" * (3 - self._dots)
        self.label.setText(
            f"<span style='color:{styles.ACCENT_BRIGHT};letter-spacing:3px;'>{visibles}"
            f"<span style='color:rgba(0,0,0,0);'>{ocultos}</span></span>"
        )

    def stop_typing(self):
        if self._typing_timer is not None:
            self._typing_timer.stop()
            self._typing_timer.deleteLater()
            self._typing_timer = None
        self._typing = False
        self._raw = ""
        self.label.setText("")


class ChatView(QScrollArea):
    """Contenedor scrollable de burbujas. API de alto nivel para el orquestador."""

    _MAX_WIDTH_RATIO = 0.74

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container.setObjectName("ChatContainer")
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(2, 6, 10, 6)
        self._vbox.setSpacing(9)
        self._vbox.addStretch(1)  # ancla los mensajes hacia abajo cuando hay pocos
        self.setWidget(self._container)

        self._rows = []      # filas (QWidget) en orden
        self._bubbles = []   # solo las ChatBubble (para acotar el ancho)
        self._current = None  # burbuja de Lia en streaming

        self.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QWidget#ChatContainer { background: transparent; }
            QScrollBar:vertical {
                border: none; background: rgba(0,0,0,0.12);
                width: 6px; margin: 0px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(129,140,248,0.35); min-height: 20px; border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover { background: rgba(99,102,241,0.6); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none; background: none;
            }
        """)

    # ------------------------------------------------------------- composicion

    def _append_row(self, row: QWidget):
        # Insertar antes del stretch final para que el ancla inferior funcione
        self._vbox.insertWidget(self._vbox.count() - 1, row)
        self._rows.append(row)
        self._scroll_to_bottom()

    def _register_bubble(self, bubble: ChatBubble):
        self._bubbles.append(bubble)
        bubble.setMaximumWidth(self._bubble_max_width())

    def _time_label(self, text: str, side: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"QLabel {{ color: {styles.TEXT_DIM}; background: transparent;"
            f" font-family: {styles.FONT}; font-size: 10px; }}"
        )
        return lbl

    def _column(self, bubble: ChatBubble, side: str, timestamp: str) -> QWidget:
        """Apila la burbuja con su marca de tiempo, alineada a su lado."""
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(bubble)
        if timestamp:
            align = Qt.AlignmentFlag.AlignRight if side == "right" else Qt.AlignmentFlag.AlignLeft
            v.addWidget(self._time_label(timestamp, side), 0, align)
        col.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        return col

    def _user_row(self, bubble: ChatBubble, timestamp: str) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addStretch(1)
        h.addWidget(self._column(bubble, "right", timestamp), 0, Qt.AlignmentFlag.AlignTop)
        return row

    def _lia_row(self, bubble: ChatBubble, timestamp: str) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(7)
        avatar = QLabel()
        avatar.setPixmap(_orb_pixmap(20))
        avatar.setFixedSize(20, 20)
        h.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        h.addWidget(self._column(bubble, "left", timestamp), 0, Qt.AlignmentFlag.AlignTop)
        h.addStretch(1)
        return row

    # ---------------------------------------------------------------- API alta

    def add_user(self, text: str, timestamp: str = None):
        bubble = ChatBubble("user")
        bubble.set_plain(text)
        self._register_bubble(bubble)
        self._append_row(self._user_row(bubble, timestamp if timestamp is not None else _now_hm()))

    def add_lia(self, text: str, timestamp: str = None):
        """Burbuja de Lia completa (saludo, historial restaurado) con Markdown."""
        bubble = ChatBubble("lia")
        bubble.set_markdown(text)
        self._register_bubble(bubble)
        self._append_row(self._lia_row(bubble, timestamp))

    def begin_lia(self):
        """Crea la burbuja de Lia, muestra 'escribiendo…' y la marca para el streaming."""
        bubble = ChatBubble("lia")
        self._current = bubble
        self._register_bubble(bubble)
        self._append_row(self._lia_row(bubble, _now_hm()))
        bubble.start_typing()

    def stream_lia(self, token: str):
        if self._current is None:
            self.begin_lia()
        if self._current._typing:
            self._current.stop_typing()
        self._current.append_plain(token)
        self._scroll_to_bottom()

    def end_lia(self, markdown_text: str):
        """Cierra el turno de Lia: render Markdown o elimina la burbuja si quedo vacia."""
        if self._current is None:
            return
        self._current.stop_typing()
        if markdown_text and markdown_text.strip():
            self._current.set_markdown(markdown_text)
        elif self._current.is_empty():
            if self._current in self._bubbles:
                self._bubbles.remove(self._current)
            self._remove_last_row()
        self._current = None
        self._scroll_to_bottom()

    def add_system(self, text: str, kind: str = "info"):
        """Linea de sistema centrada y discreta (TTS, microfono, estado, tokens)."""
        colors = {
            "info": styles.ACCENT_BRIGHT,
            "warning": "#F59E0B",
            "error": styles.DANGER,
            "meta": styles.TEXT_DIM,
        }
        color = colors.get(kind, styles.ACCENT_BRIGHT)
        size = "11px" if kind == "meta" else "12px"
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"QLabel {{ color: {color}; background: transparent;"
            f" font-family: {styles.FONT}; font-size: {size}; font-style: italic; }}"
        )
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        h.addWidget(lbl)
        h.addStretch(1)
        self._append_row(row)

    def clear(self):
        if self._current is not None:
            self._current.stop_typing()
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self._bubbles.clear()
        self._current = None

    def is_empty(self) -> bool:
        return len(self._rows) == 0

    # ------------------------------------------------------------------ helpers

    def _remove_last_row(self):
        if not self._rows:
            return
        row = self._rows.pop()
        row.setParent(None)
        row.deleteLater()

    def _bubble_max_width(self) -> int:
        return max(180, int(self.viewport().width() * self._MAX_WIDTH_RATIO))

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        QTimer.singleShot(0, lambda: sb.setValue(sb.maximum()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self._bubble_max_width()
        for b in self._bubbles:
            b.setMaximumWidth(w)
