"""Tests de la vista de grafo (construcción del grafo, layout y ventana)."""
import math

from src.gui.graph_view import build_graph, layout_graph


def _notes(**kw):
    return {t: {"path": t, "links": set(links)} for t, links in kw.items()}


def test_build_graph_ignores_broken_links():
    notes = _notes(Hugo=["Guille", "Fantasma"], Guille=["Hugo"])
    titles, edges = build_graph(notes)
    assert titles == ["Guille", "Hugo"]
    assert edges == [("Guille", "Hugo")]      # sin duplicados ni rotas


def test_layout_positions_in_bounds_and_deterministic():
    notes = _notes(A=["B"], B=["C"], C=["A"], D=[])
    titles, edges = build_graph(notes)
    pos1 = layout_graph(titles, edges)
    pos2 = layout_graph(titles, edges)
    assert pos1 == pos2                        # determinista (misma semilla)
    for x, y in pos1.values():
        assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0


def test_layout_pulls_connected_nodes_closer():
    # A-B conectados; C suelto: A debe quedar más cerca de B que de C
    notes = _notes(A=["B"], B=["A"], C=[])
    titles, edges = build_graph(notes)
    pos = layout_graph(titles, edges, iters=200)

    def d(p, q):
        return math.dist(pos[p], pos[q])

    assert d("A", "B") < d("A", "C")
    assert d("A", "B") < d("B", "C")


def test_singleton_and_empty():
    assert layout_graph([], []) == {}
    assert layout_graph(["Solo"], []) == {"Solo": (0.5, 0.5)}


def test_window_builds_offscreen(qapp):
    from src.gui.graph_view import GraphWindow
    notes = _notes(Hugo=["Guille"], Guille=["Hugo"], Nisa=["Hugo"])
    w = GraphWindow(notes)
    assert w is not None
    w_small = GraphWindow(_notes(Sola=[]))     # vault diminuto: mensaje, no crash
    assert w_small is not None


def test_canvas_node_drag_updates_position(qapp):
    from src.gui.graph_view import _GraphCanvas
    from PyQt6.QtCore import QPointF, QEvent, Qt
    from PyQt6.QtGui import QMouseEvent

    titles = ["A", "B"]
    canvas = _GraphCanvas(titles, [("A", "B")], {"A": (0.2, 0.2), "B": (0.8, 0.8)})
    canvas.resize(500, 400)

    def press(pos):
        return QMouseEvent(QEvent.Type.MouseButtonPress, pos,
                           Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier)

    # Agarra el nodo A donde está AHORA (puede seguir asentándose) y arrástralo
    a_px = canvas._to_px(canvas._now("A"))
    canvas.mousePressEvent(press(a_px))
    assert canvas._drag_node == "A"
    assert canvas._t == 1.0                      # el arrastre fija el layout

    center = QPointF(canvas.width() / 2, canvas.height() / 2)
    move = QMouseEvent(QEvent.Type.MouseMove, center,
                       Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)
    canvas.mouseMoveEvent(move)
    x, y = canvas.positions["A"]
    assert abs(x - 0.5) < 0.1 and abs(y - 0.5) < 0.1

    release = QMouseEvent(QEvent.Type.MouseButtonRelease, center,
                          Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier)
    canvas.mouseReleaseEvent(release)
    assert canvas._drag_node is None


def test_canvas_click_off_node_ignored(qapp):
    from src.gui.graph_view import _GraphCanvas
    from PyQt6.QtCore import QPointF, QEvent, Qt
    from PyQt6.QtGui import QMouseEvent

    canvas = _GraphCanvas(["A"], [], {"A": (0.1, 0.1)})
    canvas.resize(500, 400)
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(450, 350),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier)
    canvas.mousePressEvent(ev)
    assert canvas._drag_node is None
    assert not ev.isAccepted()                   # propaga: la ventana se arrastra


def test_canvas_settling_animation_converges(qapp):
    from src.gui.graph_view import _GraphCanvas
    canvas = _GraphCanvas(["A"], [], {"A": (0.9, 0.9)})
    assert canvas._now("A") != (0.9, 0.9)        # arranca cerca del centro
    for _ in range(60):
        canvas._tick()
    assert canvas._t == 1.0
    assert canvas._now("A") == (0.9, 0.9)        # asentado en su posición final
