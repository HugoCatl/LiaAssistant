import sys
from PyQt6.QtWidgets import QApplication
from dotenv import load_dotenv
from config.paths import env_path

# Load environmental variables from .env file (app-data si esta empaquetado)
load_dotenv(env_path())

from config import settings

def main():
    print("[Main] Initializing LIA Assistant base environment...")

    # Initialize PyQt application
    app = QApplication(sys.argv)

    # CRITICAL: Prevent application from quitting when the view window is hidden.
    # This allows the background daemon to capture global hotkeys in the background.
    app.setQuitOnLastWindowClosed(False)

    # Onboarding: si falta clave de Gemini o ruta del vault, pedirlas antes de
    # arrancar (en vez de reventar en silencio al primer mensaje).
    from src.gui.onboarding import ensure_configured
    if not ensure_configured(settings):
        print("[Main] Configuracion incompleta. Saliendo.")
        return

    # Pantalla de carga con barra (sin terminal). Cubre la carga de los modulos
    # pesados (Whisper, embeddings, servicios), que es lo que tarda.
    from src.gui.splash import LiaSplash
    splash = LiaSplash()
    splash.show()
    app.processEvents()

    splash.set_progress(20, "Cargando el nucleo…")
    from src.core import StateManager, Orchestrator
    from src.gui import View
    from src.gui.mascot_factory import make_mascot
    from src.gui.tray_icon import make_tray
    from src.io import KeyboardListener
    from src.services.tts_service import TTSService

    splash.set_progress(55, "Preparando la interfaz…")
    state_manager = StateManager()
    view = View()
    mascot = make_mascot()  # orbe minimalista
    keyboard_listener = KeyboardListener()

    splash.set_progress(80, "Conectando servicios…")
    orchestrator = Orchestrator(view, state_manager, keyboard_listener, mascot=mascot)

    # Ensure background listener resources are released on exit
    app.aboutToQuit.connect(keyboard_listener.stop)
    app.aboutToQuit.connect(lambda: TTSService.get_instance().stop())
    if orchestrator.system_monitor is not None:
        app.aboutToQuit.connect(orchestrator.system_monitor.stop)

    # Icono de bandeja del sistema: permite mostrar/ocultar y SALIR de verdad.
    tray = make_tray(app, orchestrator)

    splash.set_progress(100, "¡Listo!")
    orchestrator.start()

    # The mascot is the persistent desktop presence. The panel stays hidden
    # until the user clicks the mascot or presses the global hotkey.
    mascot.show()
    splash.close()

    # Start PyQt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
