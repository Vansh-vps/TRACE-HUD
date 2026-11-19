# TRACE HUD — Interactive Neon Gaming Taskbar Overlay

A sleek, translucent **Synthwave/Cyberpunk Neon** gaming taskbar overlay designed for Windows laptops with dedicated GPUs (NVIDIA RTX & AMD Ryzen). Docks seamlessly at the top edge of your screen to monitor hardware thermals and system performance in real time while gaming.

---

##  Key Features

- **Top-of-Screen Dock**: Sits cleanly at the top of your screen with an outer neon bloom and translucent dark-glass aesthetic.
- **Cyberpunk Neon Palette**:
  - `#8E1EA2` : Deep Neon Purple
  - `#C654C3` : Vivid Orchid / Magenta
  - `#ED96D7` : Luminous Soft Pink
  - `#FFC0DE` : Pastel Cotton Candy Pink
- **Real-Time Telemetry**:
  - **CPU**: Live usage %, core temperature (°C) with thermal alerts, clock frequency (GHz), and dynamic load bar.
  - **GPU**: Dedicated NVIDIA GPU utilization %, direct hardware core diode temp (°C) via NVML, VRAM consumption (e.g. `1.2 / 4.0 GB`), and real-time wattage (`W`).
  - **RAM**: Consumed vs. total system memory (`GB` & `%`).
- **👻 Ghost Mode (Click-Through for Gamers)**:
  - Press **`Ctrl + Shift + G`** or click the ghost icon to let all mouse clicks pass straight through the bar into your game.
- **⤢ Compact Mini-HUD**:
  - Press **`Ctrl + Shift + M`** or click **⤢** to shrink into an ultra-slim, distraction-free floating pill.
- **Interactive Drag-Dot Opacity Slider**:
  - Access **Settings (`⚙`) $\rightarrow$ Translucency / Opacity $\rightarrow$ Custom** to drag the anti-aliased circular dot and set any opacity between 20% and 100% with live preview.
- **Zero FPS Drop**:
  - Built with native Win32 APIs, ctypes, and NVML. Queries take under 0.5ms with near-zero CPU/GPU overhead.

---

##  In-Game Global Hotkeys

| Shortcut | Action |
|---|---|
| **Ctrl + Shift + O** | Show / Hide Taskbar Overlay |
| **Ctrl + Shift + G** | Toggle **Ghost Mode** (Click-Through) |
| **Ctrl + Shift + M** | Toggle **Compact Mini-HUD** vs Full Bar |
| **Double-Click Grip `⠿`** | Snap back to Top-Center |

---

##  Quick Start

### Prerequisites
- Windows 10 / 11
- Python 3.10+
- Dependencies: `PySide6`, `pynput`

### Launch Options
- **Silent Launch (No console window)**:
  Double-click `run_taskbar_silent.bat`
- **Standard Launch (With debug console)**:
  Double-click `run_taskbar.bat`

---

##  Project Structure

```
TRACE-HUD/
├── gaming_taskbar/
│   ├── hardware_monitor.py   # Telemetry engine (Win32, NVML, CPU/GPU/RAM)
│   ├── hotkey_manager.py     # Global background hotkey listeners
│   ├── main.py               # Main application entry point
│   ├── overlay_window.py     # PySide6 HUD GUI & custom slider
│   └── README.md
├── run_taskbar.bat           # 1-click launcher with console
├── run_taskbar_silent.bat    # 1-click headless launcher
├── .gitignore
└── README.md
```

---

##  License
MIT License. Free to use and customize!
