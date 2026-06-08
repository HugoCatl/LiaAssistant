import sys
from PyQt6.QtWidgets import QApplication
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

from config import settings
from src.core import StateManager, Orchestrator
from src.gui import View
from src.io import KeyboardListener

def main():
    print("[Main] Initializing LIA Assistant base environment...")

    # Initialize PyQt application
    app = QApplication(sys.argv)

    # CRITICAL: Prevent application from quitting when the view window is hidden.
    # This allows the background daemon to capture global hotkeys in the background.
    app.setQuitOnLastWindowClosed(False)

    # Instantiate the system components
    state_manager = StateManager()
    view = View()
    keyboard_listener = KeyboardListener()

    # Orchestrate using the Mediator pattern
    orchestrator = Orchestrator(view, state_manager, keyboard_listener)

    # Ensure background listener resources are released on exit
    app.aboutToQuit.connect(keyboard_listener.stop)

    # Start the orchestrator (launches KeyboardListener thread)
    orchestrator.start()

    # Show the main view on startup so the user has immediate visual feedback
    view.show()

    # Start PyQt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
