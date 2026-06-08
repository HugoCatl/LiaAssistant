from PyQt6.QtCore import QThread, pyqtSignal
from pynput import keyboard

class KeyboardListener(QThread):
    """
    Background QThread that captures global keyboard shortcuts.
    When Shift_L + L is pressed, it fires hotkey_triggered.
    Uses pynput.keyboard underneath.
    """
    hotkey_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._pressed_keys = set()
        self._listener = None

    def run(self):
        # Create and start the pynput listener
        # By default, keyboard.Listener inherits from threading.Thread, which runs in background.
        # Running it inside QThread's run method keeps the lifetime tied to this QThread.
        self._listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self._listener.start()
        
        # Start QThread event loop (blocking run() so thread remains active)
        self.exec()

    def on_press(self, key):
        # Track the pressed key
        self._pressed_keys.add(key)
        
        # Check if Shift_L and 'L' are pressed simultaneously
        has_shift_l = False
        has_l = False

        for k in self._pressed_keys:
            # Match left shift key
            if k == keyboard.Key.shift_l:
                has_shift_l = True
            
            # Match 'L' or 'l' key
            if hasattr(k, 'char') and k.char in ('l', 'L'):
                has_l = True

        if has_shift_l and has_l:
            print("[KeyboardListener] Global Hotkey (Shift_L + L) triggered!")
            self.hotkey_triggered.emit()
            # Clear pressed keys to prevent repeated triggers on hold
            self._pressed_keys.clear()

    def on_release(self, key):
        # Remove from pressed keys set if present
        if key in self._pressed_keys:
            try:
                self._pressed_keys.remove(key)
            except KeyError:
                pass

    def stop(self):
        # Stop the listener and quit the event loop
        if self._listener:
            self._listener.stop()
        self.quit()
        self.wait()
