from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt

class InputField(QLineEdit):
    """
    Custom QLineEdit designed with a glassmorphic aesthetic.
    Includes placeholder text and a custom focus border effect.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Pregúntame algo o escribe un comando...")
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 35, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #FFFFFF;
                padding: 12px 16px;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1.5px solid #00F3FF;
                background-color: rgba(30, 30, 35, 0.85);
            }
        """)
