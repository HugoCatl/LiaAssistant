import sys
from PyQt6.QtWidgets import QApplication
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

from config import settings
from src.core import StateManager, Orchestrator
from src.gui import View
from src.gui.mascot_factory import make_mascot
from src.io import KeyboardListener
from src.services.tts_service import TTSService

def main():
    print("[Main] Initializing LIA Assistant base environment...")

    # Configura el formato OpenGL con canal alfa ANTES de crear la QApplication,
    # por si la mascota Live2D necesita una ventana transparente. Inofensivo si
    # finalmente se usa el gato dibujado.
    try:
        from src.gui.live2d_mascot import configure_surface_format
        configure_surface_format()
    except Exception:
        pass

    # Initialize PyQt application
    app = QApplication(sys.argv)

    # CRITICAL: Prevent application from quitting when the view window is hidden.
    # This allows the background daemon to capture global hotkeys in the background.
    app.setQuitOnLastWindowClosed(False)

    # Instantiate the system components
    state_manager = StateManager()
    view = View()
    mascot = make_mascot()  # Live2D si está disponible; si no, el gato dibujado
    keyboard_listener = KeyboardListener()

    # Orchestrate using the Mediator pattern
    orchestrator = Orchestrator(view, state_manager, keyboard_listener, mascot=mascot)

    # Ensure background listener resources are released on exit
    app.aboutToQuit.connect(keyboard_listener.stop)
    app.aboutToQuit.connect(lambda: TTSService.get_instance().stop())
    if orchestrator.system_monitor is not None:
        app.aboutToQuit.connect(orchestrator.system_monitor.stop)
    # Libera recursos de Live2D si se usó esa mascota
    try:
        from src.gui.live2d_mascot import dispose as live2d_dispose
        app.aboutToQuit.connect(live2d_dispose)
    except Exception:
        pass

    # Start the orchestrator (launches KeyboardListener thread)
    orchestrator.start()

    # The mascot is the persistent desktop presence. The panel stays hidden
    # until the user clicks the mascot or presses the global hotkey.
    mascot.show()

    # Start PyQt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
