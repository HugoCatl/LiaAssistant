"""Tests del panel de info rediseñado y del atajo ↑ del campo de entrada."""
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent

from src.gui.components.info_panel import InfoPanel, _Row
from src.gui.components.input_field import InputField


def _sections(spy):
    return [
        ("Ejemplos", [
            {"emoji": "📸", "title": "Ver pantalla", "subtitle": "resume",
             "callback": lambda: spy.append("ver")},
        ]),
        ("Acciones", [
            {"emoji": "🚪", "title": "Cerrar", "subtitle": "salir",
             "callback": lambda: spy.append("cerrar"), "danger": True},
        ]),
    ]


def test_panel_builds_rows(qapp):
    panel = InfoPanel(_sections([]), footer="Esc cierra")
    rows = panel.findChildren(_Row)
    assert len(rows) == 2
    assert panel.width() == 320


def test_row_click_invokes_callback(qapp):
    spy = []
    panel = InfoPanel(_sections(spy))
    panel.show()
    rows = panel.findChildren(_Row)
    # Simula la liberación del ratón con botón izquierdo sobre la primera fila
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QPointF
    me = QMouseEvent(
        QEvent.Type.MouseButtonRelease, QPointF(5, 5),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    rows[0].mouseReleaseEvent(me)
    assert spy == ["ver"]


def test_input_up_arrow_emits_recall_when_empty(qapp):
    field = InputField()
    got = []
    field.recall_requested.connect(lambda: got.append(True))
    ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    field.keyPressEvent(ev)
    assert got == [True]


def test_input_up_arrow_ignored_when_text_present(qapp):
    field = InputField()
    field.setText("algo")
    got = []
    field.recall_requested.connect(lambda: got.append(True))
    ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    field.keyPressEvent(ev)
    assert got == []
