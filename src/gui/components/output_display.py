from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

class OutputDisplay(QTextBrowser):
    """
    Custom QTextBrowser designed for displaying Markdown or plain text responses.
    Has a transparent background and clean, modern typography.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Las respuestas de LIA Assistant aparecerán aquí...")
        self.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #E2E8F0;
                font-family: 'Segoe UI', 'Outfit', 'Inter', sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.1);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(192, 132, 252, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        self.setOpenExternalLinks(True)
        # Automatic scroll to bottom on new content
        self.textChanged.connect(self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.moveCursor(QTextCursor.MoveOperation.End)
