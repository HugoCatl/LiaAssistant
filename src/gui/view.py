from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QMenu
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor

from src.gui.components.input_field import InputField
from src.gui.components.output_display import OutputDisplay
from src.core.state_manager import AssistantState

class View(QWidget):
    """
    Main overlay view of the LIA Assistant.
    Frameless, translucent background, stays on top, supports window dragging.
    Styled with a sleek violet/purple glassmorphic theme.
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

        # Main glassmorphic card container (violet/purple tone)
        self.card = QFrame(self)
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet("""
            QFrame#MainCard {
                background-color: rgba(22, 16, 28, 0.88);
                border: 1px solid rgba(192, 132, 252, 0.32);
                border-radius: 16px;
            }
        """)

        # Glow effect (Purple drop shadow)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(192, 132, 252, 60))  # Soft purple aura
        shadow.setOffset(0, 0)
        self.card.setGraphicsEffect(shadow)

        # Layout inside the main card
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 20)
        card_layout.setSpacing(14)

        # Title bar & controls layout
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Brand name (LIA ASSISTANT)
        self.title_label = QLabel("✧ LIA ASSISTANT", self.card)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #C084FC;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-weight: 900;
                font-size: 13px;
                letter-spacing: 2.5px;
            }
        """)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # State Indicator Dot
        self.status_dot = QFrame(self.card)
        self.status_dot.setFixedSize(10, 10)
        self.update_status_dot(AssistantState.IDLE)
        header_layout.addWidget(self.status_dot)

        # Settings/Microphone Config Button (⚙)
        self.config_button = QPushButton("⚙", self.card)
        self.config_button.setFixedSize(22, 22)
        self.config_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.4);
                font-size: 16px;
                font-weight: bold;
                margin-top: -1px;
            }
            QPushButton:hover {
                color: #C084FC;
            }
        """)
        header_layout.addWidget(self.config_button)

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
                color: #F87171;
            }
        """)
        self.close_button.clicked.connect(self.close_requested)
        header_layout.addWidget(self.close_button)

        card_layout.addLayout(header_layout)

        # Output text browser
        self.output_display = OutputDisplay(self.card)
        self.output_display.setMinimumHeight(150)
        card_layout.addWidget(self.output_display)

        # Bottom row (Input Field + Mic Button)
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        # User Input field
        self.input_field = InputField(self.card)
        bottom_layout.addWidget(self.input_field)

        # Microphone Toggle Button
        self.mic_button = QPushButton("🎤", self.card)
        self.mic_button.setFixedSize(45, 45)  # Mapped to input_field height
        self.mic_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_recording_active(False)  # Apply base styles
        bottom_layout.addWidget(self.mic_button)

        card_layout.addLayout(bottom_layout)

        root_layout.addWidget(self.card)

        # New window dimensions (Wider, taller and sleeker)
        self.resize(580, 360)
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
            AssistantState.IDLE: "#C084FC",        # Light Purple / Lilac
            AssistantState.LISTENING: "#EC4899",   # Neon Pink / Fucsia
            AssistantState.PROCESSING: "#F59E0B",  # Amber / Yellow-Orange
            AssistantState.RESPONDING: "#3B82F6"   # Electric Blue
        }
        color = color_map.get(state, "#C084FC")
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 5px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        self.status_dot.setToolTip(f"Estado: {state.value}")

    def set_recording_active(self, active: bool):
        """Applies visual recording feedback to the microphone button."""
        if active:
            # Active state: pulsing pink/magenta neon border
            self.mic_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(236, 72, 153, 0.15);
                    border: 2px solid #EC4899;
                    border-radius: 12px;
                    color: #EC4899;
                    font-size: 18px;
                }
            """)
        else:
            # Standard glassmorphic state
            self.mic_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(25, 20, 30, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 12px;
                    color: #C084FC;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: rgba(192, 132, 252, 0.15);
                    border: 1px solid rgba(192, 132, 252, 0.4);
                }
                QPushButton:pressed {
                    background-color: rgba(192, 132, 252, 0.3);
                }
            """)

    def show_microphone_menu(self, devices: list, current_device_id, callback):
        """
        Dynamically generates and displays a context menu containing
        a list of available audio input devices.
        """
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(22, 16, 28, 0.95);
                border: 1px solid rgba(192, 132, 252, 0.4);
                border-radius: 8px;
                color: #E2E8F0;
                padding: 4px;
                font-family: 'Segoe UI', 'Outfit', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px 6px 24px;
                background-color: transparent;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(192, 132, 252, 0.25);
                color: #FFFFFF;
            }
        """)

        # Add an action for each device
        for dev_id, dev_name in devices:
            # Put a checkmark in front of the active device
            display_name = f"✓ {dev_name}" if dev_id == current_device_id else dev_name
            action = menu.addAction(display_name)
            # Route trigger to callback
            action.triggered.connect(lambda checked, d_id=dev_id: callback(d_id))

        # Position menu right below the gear button
        pos = self.config_button.mapToGlobal(QPoint(0, self.config_button.height()))
        menu.exec(pos)

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
