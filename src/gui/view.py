from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor

from src.gui.components.input_field import InputField
from src.gui.components.output_display import OutputDisplay
from src.core.state_manager import AssistantState

class View(QWidget):
    """
    Main overlay view of the Omega Assistant.
    Frameless, translucent background, stays on top, supports window dragging.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Configure OS-level window flags for an overlay widget
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Root layout with padding to accommodate the shadow blur
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(15, 15, 15, 15)

        # Main glassmorphic card container
        self.card = QFrame(self)
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet("""
            QFrame#MainCard {
                background-color: rgba(20, 20, 25, 0.85);
                border: 1px solid rgba(0, 243, 255, 0.25);
                border-radius: 16px;
            }
        """)

        # Glow effect (Cyan drop shadow)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 243, 255, 50))  # Alpha 50 for a clean cyberpunk glow
        shadow.setOffset(0, 0)
        self.card.setGraphicsEffect(shadow)

        # Layout inside the main card
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 14, 18, 18)
        card_layout.setSpacing(12)

        # Title bar & controls layout
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Brand name
        self.title_label = QLabel("Ω OMEGA ASSISTANT", self.card)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #00F3FF;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-weight: 900;
                font-size: 12px;
                letter-spacing: 2px;
            }
        """)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # State Indicator Dot
        self.status_dot = QFrame(self.card)
        self.status_dot.setFixedSize(10, 10)
        self.update_status_dot(AssistantState.IDLE)
        header_layout.addWidget(self.status_dot)

        # Minimize/Hide Button (represented as close 'x')
        self.close_button = QPushButton("×", self.card)
        self.close_button.setFixedSize(22, 22)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.4);
                font-size: 20px;
                font-weight: bold;
                margin-top: -2px;
            }
            QPushButton:hover {
                color: #FF5A5A;
            }
        """)
        self.close_button.clicked.connect(self.close_requested)
        header_layout.addWidget(self.close_button)

        card_layout.addLayout(header_layout)

        # Output text browser
        self.output_display = OutputDisplay(self.card)
        self.output_display.setMinimumHeight(130)
        card_layout.addWidget(self.output_display)

        # User Input field
        self.input_field = InputField(self.card)
        card_layout.addWidget(self.input_field)

        root_layout.addWidget(self.card)

        # Window settings
        self.resize(520, 320)
        self.center_on_screen()

        # Window drag status variables
        self._drag_pos = QPoint()

    def center_on_screen(self):
        """Centers the assistant overlay on the active screen."""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        # Position slightly above center for better ergonomics
        y = (screen.height() - size.height()) // 3
        self.move(x, y)

    def update_status_dot(self, state: AssistantState):
        """Updates the status dot color to reflect the assistant's state."""
        color_map = {
            AssistantState.IDLE: "#00F3FF",        # Cyan
            AssistantState.LISTENING: "#FF007F",   # Hot Pink
            AssistantState.PROCESSING: "#FF8C00",  # Dark Orange
            AssistantState.RESPONDING: "#7C4DFF"   # Deep Purple
        }
        color = color_map.get(state, "#00F3FF")
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 5px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        self.status_dot.setToolTip(f"Estado actual: {state.value}")

    def close_requested(self):
        """Hides the assistant overlay, keeping the background process alive."""
        self.hide()

    # Drag-to-move implementation for Frameless Window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
