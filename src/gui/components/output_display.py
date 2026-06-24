from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

from src.gui import styles
from src.gui.md_render import markdown_to_html


class OutputDisplay(QTextBrowser):
    """
    Area de conversacion. Muestra el dialogo en streaming (texto plano mientras
    Lia escribe) y, al terminar el turno, sustituye la respuesta por su version
    en Markdown renderizado (negritas, listas, codigo...).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Las respuestas de LIA aparecerán aquí...")
        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: {styles.TEXT};
                font-family: {styles.FONT};
                font-size: 14px;
                line-height: 1.5;
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(0, 0, 0, 0.12);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(129, 140, 248, 0.35);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(99, 102, 241, 0.6);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)
        self.setOpenExternalLinks(True)
        self.textChanged.connect(self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.moveCursor(QTextCursor.MoveOperation.End)

    def finalize_response(self, anchor_pos: int, raw_text: str):
        """
        Sustituye el texto plano que se transmitio (desde anchor_pos hasta el
        final) por su version Markdown renderizada en HTML.
        """
        if anchor_pos is None or not raw_text:
            return
        cursor = self.textCursor()
        cursor.setPosition(anchor_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(markdown_to_html(raw_text))
        self.moveCursor(QTextCursor.MoveOperation.End)
