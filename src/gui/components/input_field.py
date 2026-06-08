from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt

class InputField(QLineEdit):
    """
    Custom QLineEdit designed with a glassmorphic aesthetic.
    Includes placeholder text and a custom focus border effect.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Escribe un mensaje para LIA o ejecuta un comando...")
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(25, 20, 30, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                color: #FFFFFF;
                padding: 14px 18px;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1.5px solid #C084FC;
                background-color: rgba(25, 20, 30, 0.88);
            }
        """)
