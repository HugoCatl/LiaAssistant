from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QMenu
from PyQt6.QtCore import Qt, QPoint, QSize, QRectF, QPointF
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QPainterPath, QPen, QBrush

from src.gui.components.input_field import InputField
from src.gui.components.output_display import OutputDisplay
from src.core.state_manager import AssistantState

def parse_color(color_str: str) -> QColor:
    if color_str.startswith("rgba"):
        # Format: rgba(r, g, b, a)
        parts = color_str.replace("rgba(", "").replace(")", "").split(",")
        r = int(parts[0].strip())
        g = int(parts[1].strip())
        b = int(parts[2].strip())
        a = float(parts[3].strip())
        return QColor(r, g, b, int(a * 255))
    return QColor(color_str)

def create_vector_icon(icon_type: str, color_hex: str, size: int = 32) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = parse_color(color_hex)
    pen = QPen(color)
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    if icon_type == "settings":
        painter.save()
        # Translate to exact center
        painter.translate(size / 2.0, size / 2.0)
        
        # Teeth
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        tooth_w = size * 0.14
        tooth_h = size * 0.25
        for i in range(8):
            painter.save()
            painter.rotate(i * 45.0)
            painter.drawRect(QRectF(-tooth_w / 2.0, -size / 2.0, tooth_w, tooth_h))
            painter.restore()
            
        # Central ring on top
        pen.setWidthF(size * 0.10)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        r_inner = size * 0.20
        painter.drawEllipse(QPointF(0.0, 0.0), r_inner, r_inner)
        painter.restore()
            
    elif icon_type == "close":
        painter.save()
        painter.translate(size / 2.0, size / 2.0)
        half = size / 2.0
        margin = size * 0.28
        start = -half + margin
        end = half - margin
        painter.drawLine(QPointF(start, start), QPointF(end, end))
        painter.drawLine(QPointF(end, start), QPointF(start, end))
        painter.restore()
        
    elif icon_type in ("mic", "mic_active"):
        painter.save()
        painter.translate(size / 2.0, size / 2.0)
        
        capsule_w = size * 0.26
        capsule_h = size * 0.46
        capsule_x = -capsule_w / 2.0
        capsule_y = -size * 0.32
        
        if icon_type == "mic_active":
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(capsule_x, capsule_y, capsule_w, capsule_h), capsule_w / 2.0, capsule_w / 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            painter.drawRoundedRect(QRectF(capsule_x, capsule_y, capsule_w, capsule_h), capsule_w / 2.0, capsule_w / 2.0)
            
        # Stand arc
        stand_w = size * 0.46
        stand_h = size * 0.46
        stand_x = -stand_w / 2.0
        stand_y = -size * 0.21
        
        stand_path = QPainterPath()
        stand_path.arcMoveTo(QRectF(stand_x, stand_y, stand_w, stand_h), 180.0)
        stand_path.arcTo(QRectF(stand_x, stand_y, stand_w, stand_h), 180.0, 180.0)
        painter.drawPath(stand_path)
        
        # Vertical connector removed to avoid looking like a hyphen
        # Base horizontal line removed to avoid looking like a hyphen
        painter.restore()

    elif icon_type == "sparkles":
        painter.save()
        painter.translate(size / 2.0, size / 2.0)
        
        path = QPainterPath()
        path.moveTo(0.0, -size * 0.35)
        path.quadTo(0.0, 0.0, size * 0.35, 0.0)
        path.quadTo(0.0, 0.0, 0.0, size * 0.35)
        path.quadTo(0.0, 0.0, -size * 0.35, 0.0)
        path.quadTo(0.0, 0.0, 0.0, -size * 0.35)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.restore()
        
    painter.end()
    return QIcon(pixmap)

class IconButton(QPushButton):
    """A QPushButton that automatically swaps between normal and hover QIcons."""
    def __init__(self, icon_type: str, normal_color: str, hover_color: str, size: int = 24, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.icon_size = size
        
        self.normal_icon = create_vector_icon(icon_type, normal_color, size)
        self.hover_icon = create_vector_icon(icon_type, hover_color, size)
        
        self.setIcon(self.normal_icon)
        self.setIconSize(QSize(size, size))
        
    def enterEvent(self, event):
        self.setIcon(self.hover_icon)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setIcon(self.normal_icon)
        super().leaveEvent(event)

class MicButton(QPushButton):
    """Encapsulates Microphone active (recording) and hover state with vector icons."""
    def __init__(self, size: int = 24, parent=None):
        super().__init__(parent)
        self.is_active = False
        self.normal_icon = create_vector_icon("mic", "#C084FC", size)
        self.hover_icon = create_vector_icon("mic", "#E9D5FF", size)
        self.active_icon = create_vector_icon("mic_active", "#EC4899", size)
        
        self.setIcon(self.normal_icon)
        self.setIconSize(QSize(size, size))
        
    def set_active(self, active: bool):
        self.is_active = active
        if active:
            self.setIcon(self.active_icon)
        else:
            self.setIcon(self.normal_icon)
            
    def enterEvent(self, event):
        if not self.is_active and self.isEnabled():
            self.setIcon(self.hover_icon)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if not self.is_active and self.isEnabled():
            self.setIcon(self.normal_icon)
        super().leaveEvent(event)

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
        header_layout.setSpacing(8)

        # Brand name (LIA ASSISTANT)
        self.title_label = QLabel("LIA ASSISTANT", self.card)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #C084FC;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-weight: 900;
                font-size: 13px;
                letter-spacing: 2.5px;
                background: transparent;
            }
        """)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # State Indicator Dot
        self.status_dot = QFrame(self.card)
        self.status_dot.setFixedSize(10, 10)
        self.update_status_dot(AssistantState.IDLE)
        header_layout.addWidget(self.status_dot)

        # Settings/Microphone Config Button (Gear vector icon)
        self.config_button = IconButton("settings", "rgba(255, 255, 255, 0.45)", "#C084FC", 16, self.card)
        self.config_button.setFixedSize(24, 24)
        self.config_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        header_layout.addWidget(self.config_button)

        # Minimize/Hide Button (X vector icon)
        self.close_button = IconButton("close", "rgba(255, 255, 255, 0.45)", "#F87171", 16, self.card)
        self.close_button.setFixedSize(24, 24)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
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
        self.mic_button = MicButton(24, self.card)
        self.mic_button.setFixedSize(42, 42)  # Mapped to input_field height
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
        self.mic_button.set_active(active)
        if active:
            # Active state: pulsing pink/magenta neon border
            self.mic_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(236, 72, 153, 0.15);
                    border: 2px solid #EC4899;
                    border-radius: 12px;
                }
            """)
        else:
            # Standard glassmorphic state
            self.mic_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(25, 20, 30, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(192, 132, 252, 0.15);
                    border: 1px solid rgba(192, 132, 252, 0.4);
                }
                QPushButton:pressed {
                    background-color: rgba(192, 132, 252, 0.3);
                }
                QPushButton:disabled {
                    background-color: rgba(20, 15, 25, 0.4);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
            """)

    def show_config_menu(self, devices: list, current_device_id, tts_enabled: bool, tts_callback, mic_callback):
        """
        Dynamically generates and displays a context menu containing
        a toggle for TTS and a list of available audio input devices.
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
            QMenu::separator {
                height: 1px;
                background: rgba(192, 132, 252, 0.2);
                margin: 4px 8px;
            }
        """)

        # Add TTS option
        tts_label = f"✓ Voz Activa (TTS)" if tts_enabled else "Voz Activa (TTS)"
        tts_action = menu.addAction(tts_label)
        tts_action.triggered.connect(tts_callback)

        menu.addSeparator()

        # Add an action for each device
        for dev_id, dev_name in devices:
            display_name = f"✓ {dev_name}" if dev_id == current_device_id else dev_name
            action = menu.addAction(display_name)
            action.triggered.connect(lambda checked, d_id=dev_id: mic_callback(d_id))

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
