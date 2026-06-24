import sys
from PyQt6.QtWidgets import QApplication
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

from config import settings
from src.core import StateManager, Orchestrator
from src.gui import View
from src.gui.mascot_factory import make_mascot
from src.gui.onboarding import ensure_configured
from src.gui.tray_icon import make_tray
from src.io import KeyboardListener
from src.services.tts_service import TTSService

def main():
    print("[Main] Initializing LIA Assistant base environment...")

    # Initialize PyQt application
    app = QApplication(sys.argv)

    # CRITICAL: Prevent application from quitting when the view window is hidden.
    # This allows the background daemon to capture global hotkeys in the background.
    app.setQuitOnLastWindowClosed(False)

    # Onboarding: si falta clave de Gemini o ruta del vault, pedirlas antes de
    # arrancar (en vez de reventar en silencio al primer mensaje).
    if not ensure_configured(settings):
        print("[Main] Configuracion incompleta. Saliendo.")
        return

    # Instantiate the system components
    state_manager = StateManager()
    view = View()
    mascot = make_mascot()  # orbe minimalista
    keyboard_listener = KeyboardListener()

    # Orchestrate using the Mediator pattern
    orchestrator = Orchestrator(view, state_manager, keyboard_listener, mascot=mascot)

    # Ensure background listener resources are released on exit
    app.aboutToQuit.connect(keyboard_listener.stop)
    app.aboutToQuit.connect(lambda: TTSService.get_instance().stop())
    if orchestrator.system_monitor is not None:
        app.aboutToQuit.connect(orchestrator.system_monitor.stop)

    # Icono de bandeja del sistema: permite mostrar/ocultar y SALIR de verdad.
    # Guardamos la referencia para que no lo recoja el recolector de basura.
    tray = make_tray(app, orchestrator)

    # Start the orchestrator (launches KeyboardListener thread)
    orchestrator.start()

    # The mascot is the persistent desktop presence. The panel stays hidden
    # until the user clicks the mascot or presses the global hotkey.
    mascot.show()

    # Start PyQt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
