"""
Gaming Taskbar Overlay GUI
Built with PySide6:
- Frameless, translucent, always-on-top
- Docks at the top of the laptop screen
- Real-time CPU & GPU usage, temperatures, RAM, VRAM, and power
- Ghost Mode (Click-Through while gaming)
- Drag and snap support
- Compact Mini-HUD and Expanded mode
"""

import sys
import ctypes
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QCursor, QScreen, QPainter, QBrush, QPen, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QSizePolicy, QMenu,
    QSlider, QStyle, QWidgetAction
)

# Win32 Constants for Click-Through & Topmost
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.windll.user32

class OpacitySlider(QSlider):
    """Interactive drag-dot slider with anti-aliased round handle and neon track."""
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setRange(20, 100)
        self.setFixedWidth(130)
        self.setFixedHeight(22)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._update_val_from_x(event.position().x())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_val_from_x(event.position().x())
        super().mouseMoveEvent(event)

    def _update_val_from_x(self, x):
        padding = 8.0
        track_w = self.width() - (2 * padding)
        frac = max(0.0, min(1.0, (x - padding) / track_w))
        val = int(self.minimum() + frac * (self.maximum() - self.minimum()))
        self.setValue(val)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cy = h / 2.0
        track_h = 3.5
        handle_outer_r = 7.0  # 14px outer circle
        handle_inner_r = 4.5  # 9px inner glowing circle

        pad = 8.0
        track_w = w - (2 * pad)
        frac = (self.value() - self.minimum()) / float(self.maximum() - self.minimum())
        hx = pad + frac * track_w

        # 1. Inactive track (right side - muted gray)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#71717a"))
        painter.drawRoundedRect(QRectF(hx, cy - track_h/2.0, (w - pad) - hx, track_h), track_h/2.0, track_h/2.0)

        # 2. Active track (left side - glowing neon gradient)
        grad = QLinearGradient(pad, cy, hx, cy)
        grad.setColorAt(0.0, QColor("#C654C3"))
        grad.setColorAt(1.0, QColor("#ED96D7"))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(QRectF(pad, cy - track_h/2.0, hx - pad, track_h), track_h/2.0, track_h/2.0)

        # 3. Handle Outer Ring (dark charcoal rim, exactly like the image)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#27272a"))
        painter.drawEllipse(QPointF(hx, cy), handle_outer_r, handle_outer_r)

        # 4. Handle Inner Dot (bright glowing pastel pink)
        painter.setBrush(QColor("#FFC0DE"))
        painter.drawEllipse(QPointF(hx, cy), handle_inner_r, handle_inner_r)

class GamingTaskbarOverlay(QWidget):
    def __init__(self, hardware_monitor, parent=None):
        super().__init__(parent)
        self.hw = hardware_monitor

        # States
        self.is_ghost_mode = False
        self.is_compact_mode = False
        self.drag_position = QPoint()
        self.opacity_level = 0.90
        self.separators = []

        # Window Flags: Frameless, Always on Top, Tool (hidden from Alt-Tab/Taskbar)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        # Build UI
        self._init_ui()

        # Update Timer (1 Hz for ultra-low CPU overhead)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(1000)

        # Enforce Topmost Timer (every 3 seconds to keep above borderless games)
        self.topmost_timer = QTimer(self)
        self.topmost_timer.timeout.connect(self._reassert_topmost)
        self.topmost_timer.start(3000)

        # Initial snap to top screen center
        self.snap_to_top()

    def _init_ui(self):
        # Outer Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 4, 6, 4)
        self.main_layout.setSpacing(0)

        # Background Container Card
        self.card = QFrame(self)
        self.card.setObjectName("card")
        self._apply_card_style()

        # Neon Glow Effect (Synthwave Pink/Magenta Bloom)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(22)
        self.shadow.setColor(QColor(198, 84, 195, 175))  # #C654C3 neon glow
        self.shadow.setOffset(0, 2)
        self.card.setGraphicsEffect(self.shadow)

        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(12, 4, 12, 4)
        self.card_layout.setSpacing(10)

        # ================= 1. Grip / Branding =================
        self.grip_btn = QLabel("⠿", self.card)
        self.grip_btn.setObjectName("grip")
        self.grip_btn.setToolTip("Click and drag to reposition | Double click to snap to top")
        self.grip_btn.setCursor(Qt.SizeAllCursor)
        self.card_layout.addWidget(self.grip_btn)

        self.brand_label = QLabel("TRACE HUD", self.card)
        self.brand_label.setObjectName("brand")
        self.card_layout.addWidget(self.brand_label)

        self._add_separator()

        # ================= 2. CPU Section =================
        self.cpu_frame = QFrame(self.card)
        cpu_layout = QHBoxLayout(self.cpu_frame)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(6)

        cpu_tag = QLabel("CPU", self.cpu_frame)
        cpu_tag.setObjectName("tag_cpu")
        cpu_layout.addWidget(cpu_tag)

        self.cpu_model_lbl = QLabel(self._shorten_cpu(self.hw.cpu_name), self.cpu_frame)
        self.cpu_model_lbl.setObjectName("sub_lbl")
        cpu_layout.addWidget(self.cpu_model_lbl)

        self.cpu_usage_lbl = QLabel("0%", self.cpu_frame)
        self.cpu_usage_lbl.setObjectName("val_cpu")
        cpu_layout.addWidget(self.cpu_usage_lbl)

        self.cpu_bar = QProgressBar(self.cpu_frame)
        self.cpu_bar.setObjectName("bar_cpu")
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setFixedWidth(50)
        self.cpu_bar.setFixedHeight(6)
        self.cpu_bar.setTextVisible(False)
        cpu_layout.addWidget(self.cpu_bar)

        self.cpu_temp_lbl = QLabel("--°C", self.cpu_frame)
        self.cpu_temp_lbl.setObjectName("temp_lbl")
        cpu_layout.addWidget(self.cpu_temp_lbl)

        self.card_layout.addWidget(self.cpu_frame)

        self._add_separator()

        # ================= 3. GPU Section =================
        self.gpu_frame = QFrame(self.card)
        gpu_layout = QHBoxLayout(self.gpu_frame)
        gpu_layout.setContentsMargins(0, 0, 0, 0)
        gpu_layout.setSpacing(6)

        gpu_tag = QLabel("GPU", self.gpu_frame)
        gpu_tag.setObjectName("tag_gpu")
        gpu_layout.addWidget(gpu_tag)

        self.gpu_model_lbl = QLabel(self._shorten_gpu(self.hw.gpu_name), self.gpu_frame)
        self.gpu_model_lbl.setObjectName("sub_lbl")
        gpu_layout.addWidget(self.gpu_model_lbl)

        self.gpu_usage_lbl = QLabel("0%", self.gpu_frame)
        self.gpu_usage_lbl.setObjectName("val_gpu")
        gpu_layout.addWidget(self.gpu_usage_lbl)

        self.gpu_bar = QProgressBar(self.gpu_frame)
        self.gpu_bar.setObjectName("bar_gpu")
        self.gpu_bar.setRange(0, 100)
        self.gpu_bar.setValue(0)
        self.gpu_bar.setFixedWidth(50)
        self.gpu_bar.setFixedHeight(6)
        self.gpu_bar.setTextVisible(False)
        gpu_layout.addWidget(self.gpu_bar)

        self.gpu_temp_lbl = QLabel("--°C", self.gpu_frame)
        self.gpu_temp_lbl.setObjectName("temp_lbl")
        gpu_layout.addWidget(self.gpu_temp_lbl)

        self.gpu_vram_lbl = QLabel("0/4 GB", self.gpu_frame)
        self.gpu_vram_lbl.setObjectName("sub_lbl")
        gpu_layout.addWidget(self.gpu_vram_lbl)

        self.gpu_pwr_lbl = QLabel("-- W", self.gpu_frame)
        self.gpu_pwr_lbl.setObjectName("pwr_lbl")
        gpu_layout.addWidget(self.gpu_pwr_lbl)

        self.card_layout.addWidget(self.gpu_frame)

        self._add_separator()

        # ================= 4. RAM Section =================
        self.ram_frame = QFrame(self.card)
        ram_layout = QHBoxLayout(self.ram_frame)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(6)

        ram_tag = QLabel("RAM", self.ram_frame)
        ram_tag.setObjectName("tag_ram")
        ram_layout.addWidget(ram_tag)

        self.ram_val_lbl = QLabel("-- / -- GB", self.ram_frame)
        self.ram_val_lbl.setObjectName("val_ram")
        ram_layout.addWidget(self.ram_val_lbl)

        self.ram_bar = QProgressBar(self.ram_frame)
        self.ram_bar.setObjectName("bar_ram")
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setValue(0)
        self.ram_bar.setFixedWidth(40)
        self.ram_bar.setFixedHeight(6)
        self.ram_bar.setTextVisible(False)
        ram_layout.addWidget(self.ram_bar)

        self.card_layout.addWidget(self.ram_frame)

        # ================= 5. Compact Mode Summary Label =================
        self.compact_label = QLabel("", self.card)
        self.compact_label.setObjectName("compact_lbl")
        self.compact_label.setVisible(False)
        self.card_layout.addWidget(self.compact_label)

        # ================= 6. Ghost Mode Banner =================
        self.ghost_banner = QLabel("👻 GHOST [Ctrl+Shift+G]", self.card)
        self.ghost_banner.setObjectName("ghost_banner")
        self.ghost_banner.setVisible(False)
        self.card_layout.addWidget(self.ghost_banner)

        # ================= 7. Interactive Controls =================
        self.controls_frame = QFrame(self.card)
        controls_layout = QHBoxLayout(self.controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        # Ghost Mode Button
        self.btn_ghost = QPushButton("👻", self.controls_frame)
        self.btn_ghost.setObjectName("ctrl_btn")
        self.btn_ghost.setToolTip("Toggle Ghost Mode (Click-Through while gaming)\nHotkey: Ctrl + Shift + G")
        self.btn_ghost.clicked.connect(self.toggle_ghost_mode)
        controls_layout.addWidget(self.btn_ghost)

        # Compact Mode Button
        self.btn_compact = QPushButton("⤢", self.controls_frame)
        self.btn_compact.setObjectName("ctrl_btn")
        self.btn_compact.setToolTip("Toggle Compact Mini-HUD\nHotkey: Ctrl + Shift + M")
        self.btn_compact.clicked.connect(self.toggle_compact_mode)
        controls_layout.addWidget(self.btn_compact)

        # Snap to Top Button
        self.btn_snap = QPushButton("⤒", self.controls_frame)
        self.btn_snap.setObjectName("ctrl_btn")
        self.btn_snap.setToolTip("Snap back to Top Center")
        self.btn_snap.clicked.connect(self.snap_to_top)
        controls_layout.addWidget(self.btn_snap)

        # Menu Button (Opacity & Options)
        self.btn_menu = QPushButton("⚙", self.controls_frame)
        self.btn_menu.setObjectName("ctrl_btn")
        self.btn_menu.setToolTip("Settings & Opacity")
        self.btn_menu.clicked.connect(self._show_settings_menu)
        controls_layout.addWidget(self.btn_menu)

        # Minimize / Hide Button
        self.btn_close = QPushButton("✕", self.controls_frame)
        self.btn_close.setObjectName("close_btn")
        self.btn_close.setToolTip("Hide Overlay\nHotkey to restore: Ctrl + Shift + O")
        self.btn_close.clicked.connect(self.hide)
        controls_layout.addWidget(self.btn_close)

        self.card_layout.addWidget(self.controls_frame)

        self.main_layout.addWidget(self.card)

    def _add_separator(self):
        sep = QFrame(self.card)
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet("background-color: rgba(237, 150, 215, 0.30); width: 1px; max-height: 20px;")
        self.separators.append(sep)
        self.card_layout.addWidget(sep)

    def _apply_card_style(self):
        self.card.setStyleSheet(f"""
            QFrame#card {{
                background-color: rgba(18, 10, 26, {self.opacity_level});
                border: 1.5px solid #ED96D7;
                border-radius: 10px;
            }}
            QLabel {{
                color: #FFC0DE;
                font-family: 'Segoe UI', 'Consolas', sans-serif;
                font-size: 11px;
            }}
            QLabel#brand {{
                font-weight: bold;
                font-size: 11px;
                color: #FFC0DE;
                letter-spacing: 1.5px;
            }}
            QLabel#grip {{
                color: #C654C3;
                font-size: 13px;
                padding-right: 2px;
            }}
            QLabel#grip:hover {{
                color: #FFC0DE;
            }}
            QLabel#tag_cpu {{
                background-color: rgba(142, 30, 162, 0.45);
                color: #FFC0DE;
                border: 1px solid #C654C3;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QLabel#val_cpu {{
                font-weight: bold;
                color: #FFC0DE;
                min-width: 30px;
            }}
            QLabel#tag_gpu {{
                background-color: rgba(198, 84, 195, 0.45);
                color: #FFFFFF;
                border: 1px solid #ED96D7;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QLabel#val_gpu {{
                font-weight: bold;
                color: #ED96D7;
                min-width: 30px;
            }}
            QLabel#tag_ram {{
                background-color: rgba(142, 30, 162, 0.35);
                color: #ED96D7;
                border: 1px solid rgba(198, 84, 195, 0.6);
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QLabel#val_ram {{
                font-weight: bold;
                color: #FFC0DE;
            }}
            QLabel#sub_lbl {{
                color: #ED96D7;
                font-size: 10px;
            }}
            QLabel#temp_lbl {{
                font-weight: bold;
                min-width: 35px;
            }}
            QLabel#pwr_lbl {{
                color: #FFC0DE;
                font-size: 10px;
                font-weight: 500;
            }}
            QLabel#ghost_banner {{
                background-color: rgba(198, 84, 195, 0.60);
                color: #FFC0DE;
                border: 1px solid #FFC0DE;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QLabel#compact_lbl {{
                color: #FFC0DE;
                font-weight: bold;
                font-size: 11px;
            }}
            QProgressBar#bar_cpu {{
                background-color: rgba(142, 30, 162, 0.25);
                border: 1px solid rgba(198, 84, 195, 0.35);
                border-radius: 3px;
            }}
            QProgressBar#bar_cpu::chunk {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #8E1EA2, stop:0.5 #C654C3, stop:1 #ED96D7);
                border-radius: 3px;
            }}
            QProgressBar#bar_gpu {{
                background-color: rgba(142, 30, 162, 0.25);
                border: 1px solid rgba(237, 150, 215, 0.35);
                border-radius: 3px;
            }}
            QProgressBar#bar_gpu::chunk {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #C654C3, stop:0.5 #ED96D7, stop:1 #FFC0DE);
                border-radius: 3px;
            }}
            QProgressBar#bar_ram {{
                background-color: rgba(142, 30, 162, 0.25);
                border: 1px solid rgba(198, 84, 195, 0.35);
                border-radius: 3px;
            }}
            QProgressBar#bar_ram::chunk {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #8E1EA2, stop:1 #C654C3);
                border-radius: 3px;
            }}
            QPushButton#ctrl_btn {{
                background-color: rgba(142, 30, 162, 0.25);
                color: #ED96D7;
                border: 1px solid rgba(198, 84, 195, 0.45);
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
            }}
            QPushButton#ctrl_btn:hover {{
                background-color: rgba(198, 84, 195, 0.50);
                border: 1px solid #FFC0DE;
                color: #FFFFFF;
            }}
            QPushButton#close_btn {{
                background-color: rgba(142, 30, 162, 0.30);
                color: #FFC0DE;
                border: 1px solid rgba(237, 150, 215, 0.45);
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
            }}
            QPushButton#close_btn:hover {{
                background-color: rgba(239, 68, 68, 0.65);
                border: 1px solid #ef4444;
                color: #FFFFFF;
            }}
        """)

    def _shorten_cpu(self, name):
        if "Ryzen" in name:
            parts = name.split()
            for i, p in enumerate(parts):
                if p == "Ryzen":
                    return " ".join(parts[i:i+3])
        return name[:15]

    def _shorten_gpu(self, name):
        if "RTX" in name:
            idx = name.find("RTX")
            return name[idx:idx+8]
        return name[:12]

    def update_telemetry(self):
        """Timer callback: polls hardware monitor and refreshes HUD."""
        data = self.hw.get_all_metrics()

        cpu = data["cpu"]
        gpu = data["gpu"]
        ram = data["ram"]

        # CPU
        self.cpu_usage_lbl.setText(f"{int(cpu['usage'])}%")
        self.cpu_bar.setValue(int(cpu["usage"]))
        self.cpu_temp_lbl.setText(f"{int(cpu['temp'])}°C")
        self._style_temp(self.cpu_temp_lbl, cpu["temp"])

        # GPU
        self.gpu_usage_lbl.setText(f"{int(gpu['usage'])}%")
        self.gpu_bar.setValue(int(gpu["usage"]))
        self.gpu_temp_lbl.setText(f"{gpu['temp']}°C")
        self._style_temp(self.gpu_temp_lbl, gpu["temp"])
        self.gpu_vram_lbl.setText(f"{gpu['vram_used']:.1f}/{gpu['vram_total']:.0f}G")
        self.gpu_pwr_lbl.setText(f"{int(gpu['power'])}W")

        # RAM
        self.ram_val_lbl.setText(f"{ram['used_gb']:.1f}/{ram['total_gb']:.0f}G ({ram['percent']}%)")
        self.ram_bar.setValue(ram["percent"])

        # Compact label update
        if self.is_compact_mode:
            summary = (
                f"CPU {int(cpu['usage'])}% {int(cpu['temp'])}°C  |  "
                f"GPU {int(gpu['usage'])}% {gpu['temp']}°C  |  "
                f"RAM {ram['percent']}%"
            )
            self.compact_label.setText(summary)

    def _style_temp(self, label: QLabel, temp: float):
        if temp >= 85:
            # Overheat alert (Neon Crimson)
            label.setStyleSheet("color: #ff0055; font-weight: bold;")
        elif temp >= 75:
            # Warm load (Neon Amber)
            label.setStyleSheet("color: #fbbf24; font-weight: bold;")
        else:
            # Cool / Normal (Neon Highlight Pink)
            label.setStyleSheet("color: #FFC0DE; font-weight: bold;")

    # ================= Interaction & Movement =================

    def snap_to_top(self):
        """Center the overlay at the top edge of the current screen."""
        screen = self.screen() or QScreen()
        geom = screen.availableGeometry()
        x = geom.x() + (geom.width() - self.width()) // 2
        y = geom.y() + 4
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_ghost_mode:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.is_ghost_mode:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_ghost_mode:
            self.snap_to_top()
            event.accept()

    # ================= Ghost Mode (Click-Through for Gaming) =================

    def toggle_ghost_mode(self):
        """
        Toggles Click-Through mode using Win32 WS_EX_TRANSPARENT.
        When enabled, all mouse clicks pass straight into full-screen games!
        Press Ctrl + Shift + G to toggle off.
        """
        self.is_ghost_mode = not self.is_ghost_mode
        hwnd = int(self.winId())

        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if self.is_ghost_mode:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
            self.ghost_banner.setVisible(True)
            self.btn_ghost.setStyleSheet("background-color: #C654C3; border: 1px solid #FFC0DE; color: #FFFFFF;")
            self.card.setStyleSheet(self.card.styleSheet() + "\nQFrame#card { border: 1.5px solid #FFC0DE; }")
            self.shadow.setColor(QColor(237, 150, 215, 230))
        else:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
            self.ghost_banner.setVisible(False)
            self.btn_ghost.setStyleSheet("")
            self.shadow.setColor(QColor(198, 84, 195, 175))
            self._apply_card_style()

    # ================= Compact Mini-HUD Mode =================

    def toggle_compact_mode(self):
        """Switch between full detailed taskbar and minimalist floating pill."""
        self.is_compact_mode = not self.is_compact_mode

        # Toggle section visibility
        self.cpu_frame.setVisible(not self.is_compact_mode)
        self.gpu_frame.setVisible(not self.is_compact_mode)
        self.ram_frame.setVisible(not self.is_compact_mode)
        for sep in self.separators:
            sep.setVisible(not self.is_compact_mode)
        self.compact_label.setVisible(self.is_compact_mode)

        if self.is_compact_mode:
            self.btn_compact.setText("⤢")
            self.btn_compact.setToolTip("Expand to Full Taskbar\nHotkey: Ctrl + Shift + M")
        else:
            self.btn_compact.setText("⤡")
            self.btn_compact.setToolTip("Collapse to Mini-HUD\nHotkey: Ctrl + Shift + M")

        self.adjustSize()
        self.snap_to_top()

    def toggle_overlay_visible(self):
        """Toggle Show / Hide overlay."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self._reassert_topmost()

    def _reassert_topmost(self):
        """Ensure overlay remains on top of full-screen borderless games."""
        if self.isVisible():
            hwnd = int(self.winId())
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )

    # ================= Settings Menu =================

    def _show_settings_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #140a1c;
                color: #FFC0DE;
                border: 1px solid #C654C3;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #8E1EA2;
                color: #FFFFFF;
            }
        """)

        op_menu = menu.addMenu("Translucency / Opacity")
        for val, label in [(0.95, "95% (Solid)"), (0.85, "85% (Balanced)"), (0.65, "65% (Translucent)"), (0.45, "45% (Ghostly)")]:
            action = op_menu.addAction(label)
            action.triggered.connect(lambda checked=False, v=val: self._set_opacity(v))

        op_menu.addSeparator()

        # Add "Custom" with the Drag-Dot Slider moved here
        custom_menu = op_menu.addMenu("Custom")
        custom_menu.setStyleSheet(menu.styleSheet())

        slider_widget = QWidget(custom_menu)
        slider_layout = QVBoxLayout(slider_widget)
        slider_layout.setContentsMargins(12, 8, 12, 8)
        slider_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_title = QLabel("Custom Opacity", slider_widget)
        header_title.setStyleSheet("color: #FFC0DE; font-size: 11px; font-weight: bold;")
        pct_lbl = QLabel(f"{int(self.opacity_level * 100)}%", slider_widget)
        pct_lbl.setStyleSheet("color: #ED96D7; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(pct_lbl)
        slider_layout.addLayout(header_layout)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        eye_lbl = QLabel("👁", slider_widget)
        eye_lbl.setStyleSheet("color: #ED96D7; font-size: 11px;")
        slider_row.addWidget(eye_lbl)

        slider = OpacitySlider(slider_widget)
        slider.setValue(int(self.opacity_level * 100))
        slider_row.addWidget(slider)
        slider_layout.addLayout(slider_row)

        def on_slide(val):
            self.opacity_level = val / 100.0
            pct_lbl.setText(f"{val}%")
            self._apply_card_style()

        slider.valueChanged.connect(on_slide)

        slider_action = QWidgetAction(custom_menu)
        slider_action.setDefaultWidget(slider_widget)
        custom_menu.addAction(slider_action)

        snap_act = menu.addAction("Snap to Top Edge")
        snap_act.triggered.connect(self.snap_to_top)

        ghost_act = menu.addAction("Toggle Ghost Mode (Ctrl+Shift+G)")
        ghost_act.triggered.connect(self.toggle_ghost_mode)

        compact_act = menu.addAction("Toggle Mini-HUD (Ctrl+Shift+M)")
        compact_act.triggered.connect(self.toggle_compact_mode)

        menu.addSeparator()
        exit_act = menu.addAction("Exit TRACE HUD")
        exit_act.triggered.connect(lambda: sys.exit(0))

        menu.exec(QCursor.pos())

    def _set_opacity(self, val):
        self.opacity_level = val
        self._apply_card_style()
