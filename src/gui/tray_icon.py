"""
Icono de bandeja del sistema (system tray) de LIA.

Da por fin una forma limpia de mostrar/ocultar el panel y, sobre todo, de
SALIR de verdad (antes `close_button` solo ocultaba la ventana y la app quedaba
viva en memoria). El icono se genera con QPainter (orbe morado), sin assets.
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QRadialGradient, QColor
from PyQt6.QtCore import Qt, QPointF


def _make_orb_icon(size: int = 64) -> QIcon:
    """Genera un orbe morado como icono de bandeja (mismo lenguaje visual que la mascota)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center = QPointF(size / 2.0, size / 2.0)
    grad = QRadialGradient(center, size / 2.0)
    grad.setColorAt(0.0, QColor(199, 210, 254))   # indigo claro (núcleo)
    grad.setColorAt(1.0, QColor(55, 48, 163))      # indigo profundo (borde)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(grad)
    painter.drawEllipse(center, size * 0.42, size * 0.42)
    painter.end()

    return QIcon(pixmap)


_MENU_STYLE = """
    QMenu {
        background-color: rgba(22, 16, 28, 0.96);
        border: 1px solid rgba(192, 132, 252, 0.4);
        border-radius: 8px;
        color: #E2E8F0;
        padding: 4px;
        font-family: 'Segoe UI', 'Outfit', sans-serif;
        font-size: 12px;
    }
    QMenu::item { padding: 6px 18px; background-color: transparent; border-radius: 4px; }
    QMenu::item:selected { background-color: rgba(192, 132, 252, 0.25); color: #FFFFFF; }
    QMenu::separator { height: 1px; background: rgba(192, 132, 252, 0.2); margin: 4px 8px; }
"""


def make_tray(app, orchestrator) -> QSystemTrayIcon:
    """
    Crea y muestra el icono de bandeja con menú Mostrar/Ocultar y Salir.

    Devuelve el QSystemTrayIcon; el llamante (main) debe conservar la referencia
    para que no lo recoja el recolector de basura.
    """
    tray = QSystemTrayIcon(_make_orb_icon(), app)
    tray.setToolTip("LIA Assistant")

    def _open_config():
        from config import settings
        from src.gui.onboarding import open_config
        open_config(settings)

    menu = QMenu()
    menu.setStyleSheet(_MENU_STYLE)

    show_action = menu.addAction("Mostrar / Ocultar Lia")
    show_action.triggered.connect(orchestrator.toggle_ui)

    config_action = menu.addAction("Configurar…")
    config_action.triggered.connect(_open_config)

    menu.addSeparator()

    quit_action = menu.addAction("Salir")
    quit_action.triggered.connect(orchestrator.quit_app)

    tray.setContextMenu(menu)

    # Cl