from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt

from src.gui import styles


class InputField(QLineEdit):
    """QLineEdit con estetica 'pill' translucida y foco indigo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Escribe a Lia o pulsa el micro para hablar…")
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles.INPUT_BG};
                border: 1px solid {styles.CARD_BORDER};
                border-radius: 22px;
                color: {styles.TEXT};
                padding: 12px 20px;
                font-family: {styles.FONT};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {styles.ACCENT};
                background-color: {styles.INPUT_BG_FOCUS};
            }}
            QLineEdit:disabled {{
                background-color: rgba(16, 18, 24, 0.4);
                color: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QLineEdit::placeholder {{ color: rgba(255, 255, 255, 0.32); }}
        """)
