"""
Trace Gaming Taskbar & Telemetry HUD
Main Entry Point
"""

import sys
import os

# Ensure current folder is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from hardware_monitor import HardwareMonitor
from overlay_window import GamingTaskbarOverlay
from hotkey_manager import HotkeyManager

def main():
    # Enable high-DPI scaling for sharp text on laptop displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Trace HUD")
    app.setQuitOnLastWindowClosed(False)

    print("[*] Initializing Hardware Monitor...")
    hw = HardwareMonitor()
    print(f"[+] CPU: {hw.cpu_name}")
    print(f"[+] GPU: {hw.gpu_name}")

    print("[*] Launching  Taskbar Overlay...")
    overlay = GamingTaskbarOverlay(hardware_monitor=hw)
    overlay.show()

    print("[*] Registering Global Hotkeys:")
    print("    [Ctrl + Shift + O] : Show / Hide Overlay")
    print("    [Ctrl + Shift + G] : Toggle Ghost Mode (Click-Through for Gaming)")
    print("    [Ctrl + Shift + M] : Toggle Compact Mini-HUD / Full Taskbar")

    hotkeys = HotkeyManager()
    hotkeys.signals.toggle_visible.connect(overlay.toggle_overlay_visible)
    hotkeys.signals.toggle_ghost.connect(overlay.toggle_ghost_mode)
    hotkeys.signals.toggle_compact.connect(overlay.toggle_compact_mode)
    hotkeys.start()

    print("\n[+] TRACE HUD is live! Docked at the top of your screen.")
    try:
        sys.exit(app.exec())
    finally:
        hotkeys.stop()

if __name__ == "__main__":
    main()
