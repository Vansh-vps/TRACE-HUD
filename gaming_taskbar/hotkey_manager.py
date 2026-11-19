"""
Global Hotkey Manager
Listens for system-wide gaming hotkeys even when in full-screen games:
- Ctrl + Shift + O : Toggle Overlay Visible / Hidden
- Ctrl + Shift + G : Toggle Ghost Mode (Click-Through)
- Ctrl + Shift + M : Toggle Compact / Expanded Mini-Bar
"""

import threading
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

class HotkeySignals(QObject):
    toggle_visible = Signal()
    toggle_ghost = Signal()
    toggle_compact = Signal()

class HotkeyManager:
    def __init__(self):
        self.signals = HotkeySignals()
        self._listener = None
        self._thread = None

    def start(self):
        def _listen():
            try:
                with keyboard.GlobalHotKeys({
                    '<ctrl>+<shift>+o': self.signals.toggle_visible.emit,
                    '<ctrl>+<shift>+g': self.signals.toggle_ghost.emit,
                    '<ctrl>+<shift>+m': self.signals.toggle_compact.emit,
                }) as h:
                    self._listener = h
                    h.join()
            except Exception as e:
                print(f"[!] Hotkey listener warning: {e}")

        self._thread = threading.Thread(target=_listen, daemon=True)
        self._thread.start()

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
