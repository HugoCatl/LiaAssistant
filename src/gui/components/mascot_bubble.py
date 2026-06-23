from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor


class MascotBubble(QWidget):
    """
    Burbuja de diálogo proactiva que aparece junto a la mascota.

    Lia la usa para sugerir acciones sin interrumpir: muestra un texto y,
    opcionalmente, botones "Sí / Ahora no". Se autodescarta tras unos segundos
    si el usuario no interactúa.

    Señales:
        accepted: el usuario aceptó la sugerencia.
        dismissed: el usuario la descartó (o expiró el temporizador).
    """

    accepted = pyqtSignal()
    dismissed = pyqtSignal()

    _AUTO_HIDE_MS = 9000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_window()
        self._build_ui()

        self._auto_hide = QTimer(self)
        self._auto_hide.setSingleShot(True)
        self._auto_hide.timeout.connect(self._on_timeout)

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(260)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        self.card = QFrame(self)
        self.card.setObjectName("BubbleCard")
        self.card.setStyleSheet("""
            QFrame#BubbleCard {
                background-color: rgba(22, 16, 28, 0.94);
                border: 1px solid rgba(192, 132, 252, 0.35);
                border-radius: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(192, 132, 252, 70))
        shadow.setOffset(0, 2)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        self.message_label = QLabel("", self.card)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #F1F5F9;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-size: 13px;
                background: transparent;
            }
        """)
        card_layout.addWidget(self.message_label)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(8)
        self.button_row.addStretch()

        self.no_button = QPushButton("Ahora no", self.card)
        self.no_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.no_button.setStyleSheet(self._secondary_btn_style())
        self.no_button.clicked.connect(self._on_dismiss)
        self.button_row.addWidget(self.no_button)

        self.yes_button = QPushButton("Sí", self.card)
        self.yes_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.yes_button.setStyleSheet(self._primary_btn_style())
        self.yes_button.clicked.connect(self._on_accept)
        self.button_row.addWidget(self.yes_button)

        card_layout.addLayout(self.button_row)
        root.addWidget(self.card)

    def _primary_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: rgba(192, 132, 252, 0.22);
                border: 1px solid rgba(192, 132, 252, 0.55);
                border-radius: 9px;
                color: #E9D5FF;
                font-size: 12px;
                font-weight: 600;
                padding: 5px 16px;
            }
            QPushButton:hover { background-color: rgba(192, 132, 252, 0.38); }
            QPushButton:pressed { background-color: rgba(192, 132, 252, 0.5); }
        """

    def _secondary_btn_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 9px;
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #F1F5F9;
            }
        """

    # --------------------------------------------------------------- public API

    def show_message(self, text: str, near_widget: QWidget, with_actions: bool = True):
        """
        Muestra la burbuja con el texto dado, posicionada junto a la mascota.

        Args:
            text: mensaje a mostrar.
            near_widget: la mascota; se usa para posicionar la burbuja.
            with_actions: si False, oculta los botones (solo notificación).
        """
        self.message_label.setText(text)
        self.yes_button.setVisible(with_actions)
        self.no_button.setVisible(with_actions)

        self.adjustSize()
        self._position_near(near_widget)
        self.show()
        self.raise_()
        self._auto_hide.start(self._AUTO_HIDE_MS)

    def _position_near(self, mascot: QWidget):
        """Coloca la burbuja encima de la mascota, alineada a su lado interior."""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        m_geo = mascot.frameGeometry()

        # Encima de la mascota por defecto, con un pequeño hueco
        x = m_geo.center().x() - self.width() // 2
        y = m_geo.top() - self.height() - 8

        # Mantener dentro de la pantalla horizontalmente
        x = max(screen.left() + 8, min(x, screen.right() - self.width() - 8))
        # Si no cabe arriba, colócala debajo de la mascota
        if y < screen.top() + 8:
            y = m_geo.bottom() + 8
        self.move(x, y)

    # ---------------------------------------------------------------- handlers

    def _on_accept(self):
        self._auto_hide.stop()
        self.hide()
        self.accepted.emit()

    def _on_dismiss(self):
        self._auto_hide.stop()
        self.hide()
        self.dismissed.emit()

    def _on_timeout(self):
        self.hide()
        self.dismissed.emit()
