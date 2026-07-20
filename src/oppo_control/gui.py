import os
# Override numeric locale to force Western digits in Qt widgets.
# Keep LC_CTYPE as UTF-8 so Qt's platform plugin doesn't complain.
os.environ["LC_NUMERIC"] = "C"
os.environ["LC_CTYPE"] = "C.UTF-8"
# Do NOT set LC_ALL — that overrides LC_CTYPE and breaks Qt's UTF-8 check.
import sys
import logging
import asyncio
import time
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize, QRectF
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QCheckBox, QPushButton, QFrame, QDialog,
    QScrollArea, QStackedWidget, QListWidget, QProgressBar, QSlider,
    QButtonGroup, QTextEdit, QSizePolicy, QMessageBox
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QIcon, QPainterPath

from .device import OppoDevice, get_friendly_description
from .commands import EQPreset, EarbudsBattery, TouchGesture
from .protocol import OppoFrame
from .exceptions import OppoConnectionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oppo_control.gui")

# --- Battery Shell Widget (Mockup v4 Style) ---

class BatteryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0
        self.is_charging = False
        self.theme_mode = "dark"
        self.setFixedSize(22, 12)

    def set_state(self, level, is_charging, theme_mode="dark"):
        self.level = max(0, min(100, level))
        self.is_charging = is_charging
        self.theme_mode = theme_mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Color matching based on status and theme
        if self.level <= 20:
            color = QColor(255, 149, 0) if self.theme_mode == "light" else QColor(255, 159, 10) # Orange/Red
        else:
            color = QColor(52, 199, 89) if self.theme_mode == "light" else QColor(48, 209, 88) # Green
            
        # Draw battery border
        pen = QPen(color, 1.4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # Rect for battery shell
        painter.drawRoundedRect(1, 1, 16, 10, 2, 2)
        
        # Draw dynamic fill
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        
        fill_w = max(0, min(12, int(12 * (self.level / 100.0))))
        if fill_w > 0:
            painter.drawRect(3, 3, fill_w, 6)
            
        # Draw the right battery tip
        painter.drawRoundedRect(QRectF(18, 4, 2, 4), 0.5, 0.5)


# --- Custom Vector Silhouettes Widget (Mockup v4 Style) ---

class SilhouetteWidget(QWidget):
    def __init__(self, item_type="left", parent=None):
        super().__init__(parent)
        self.item_type = item_type  # "left", "right", "case"
        self.battery_level = 0
        self.is_charging = False
        self.is_connected = False
        self.setMinimumSize(70, 90)

    def update_state(self, is_connected, level=0, is_charging=False):
        self.is_connected = is_connected
        self.battery_level = level
        self.is_charging = is_charging
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # In v4, the earbud icons stay light/white regardless of theme, but they have subtle gradients/colors.
        # If disconnected/offline, we draw them with lower opacity.
        if self.is_connected:
            painter.setOpacity(1.0)
            fill_color = QColor("#f5f5f7")
            stroke_color = QColor("#c8c8cc")
            shade_color = QColor("#dcdce0")
        else:
            painter.setOpacity(0.3)
            fill_color = QColor("#cccccc")
            stroke_color = QColor("#aaaaaa")
            shade_color = QColor("#bbbbbb")

        width = self.width()
        height = self.height()

        # Center the SVG coordinate space (34x58 for bud, 42x58 for case)
        svg_w = 42 if self.item_type == "case" else 34
        svg_h = 58
        
        scale = min(width / svg_w, height / svg_h) * 0.95
        
        # Center coordinates
        dx = (width - (svg_w * scale)) / 2.0
        dy = (height - (svg_h * scale)) / 2.0
        
        painter.translate(dx, dy)
        painter.scale(scale, scale)

        pen = QPen(stroke_color, 1.2)
        painter.setPen(pen)

        if self.item_type in ["left", "right"]:
            # Draw earbud path
            path = QPainterPath()
            path.moveTo(17, 2)
            path.cubicTo(24, 2, 28, 8, 28, 16)
            path.cubicTo(28, 22, 25, 25, 25, 30)
            path.lineTo(25, 46)
            path.cubicTo(25, 52, 21, 56, 17, 56)
            path.cubicTo(13, 56, 9, 52, 9, 46)
            path.lineTo(9, 30)
            path.cubicTo(9, 25, 6, 22, 6, 16)
            path.cubicTo(6, 8, 10, 2, 17, 2)
            path.closeSubpath()

            painter.setBrush(QBrush(fill_color))
            painter.drawPath(path)

            # Draw inner shade ellipse
            painter.setBrush(QBrush(shade_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(10, 6, 14, 18)) # cx=17, cy=15, rx=7, ry=9 -> rect: x=10, y=6, w=14, h=18

        elif self.item_type == "case":
            # Draw case outer shape: rect x=6, y=16, w=30, h=38, rx=13, ry=13
            path_case = QPainterPath()
            path_case.addRoundedRect(QRectF(6, 16, 30, 38), 13, 13)
            
            # Draw top cap: rect x=15, y=8, w=12, h=12, rx=3, ry=3
            path_cap = QPainterPath()
            path_cap.addRoundedRect(QRectF(15, 8, 12, 12), 3, 3)

            # Draw top cap and case body
            painter.setBrush(QBrush(fill_color))
            painter.drawPath(path_cap)
            painter.drawPath(path_case)

            # Draw lid line: x1=6, y1=35, x2=36, y2=35
            painter.setPen(pen)
            painter.drawLine(6, 35, 36, 35)


# --- Asynchronous Worker Thread ---

class OppoDeviceWorker(QThread):
    connection_status = Signal(str)       # "connected", "connecting", "disconnected"
    profile_detected = Signal(object)     # DeviceProfile
    battery_updated = Signal(object)
    eq_updated = Signal(int)
    game_mode_updated = Signal(bool)
    firmware_updated = Signal(str)
    gestures_updated = Signal(list)
    volume_updated = Signal(int)
    packet_traced = Signal(str, str, str) # direction, hex_string, friendly_description
    error_occurred = Signal(str)

    # Hybrid retry policy: auto-retry a fixed number of times with backoff,
    # then stop and wait for the user to press Connect.
    MAX_AUTO_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 2  # multiplied by attempt number: 2s, 4s, 6s...

    def __init__(self, mac_address="60:55:56:22:49:A0"):
        super().__init__()
        self.mac_address = mac_address
        self.loop = None
        self.device = None
        self._running = True
        self.trace_mode = False
        self._retry_count = 0
        self._connect_event = None  # created once the event loop exists

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.device = OppoDevice(self.mac_address)
        self.device.register_callback(self._on_device_push)
        self.device._transport.record_callback = self._on_trace_packet
        self.device._transport.trace_mode = self.trace_mode

        # Gate on a manual "Connect" click for the very first attempt, and
        # again after auto-retries are exhausted. Set (not cleared) whenever
        # we're allowed to try connecting right now.
        self._connect_event = asyncio.Event()

        async def main_task():
            while self._running:
                if not self.device.is_connected:
                    await self._connect_event.wait()
                    if not self._running:
                        break

                    self.connection_status.emit("connecting")
                    try:
                        logger.info("Attempting connection to RFCOMM socket...")
                        await self.device.connect()
                        self._retry_count = 0
                        self.connection_status.emit("connected")
                        
                        # Query startup states
                        try:
                            bat = await self.device.get_battery()
                            self.battery_updated.emit(bat)
                            
                            # Profile resolved after battery check
                            if self.device.profile:
                                self.profile_detected.emit(self.device.profile)
                        except Exception as e:
                            logger.error(f"Error fetching battery: {e}")
                            
                        try:
                            fw = await self.device.get_firmware()
                            self.firmware_updated.emit(fw)
                        except Exception as e:
                            logger.error(f"Error fetching firmware: {e}")

                        try:
                            eq = await self.device.get_eq()
                            self.eq_updated.emit(int(eq))
                        except Exception as e:
                            logger.error(f"Error fetching EQ: {e}")

                        try:
                            gm = await self.device.get_game_mode()
                            self.game_mode_updated.emit(gm)
                        except Exception as e:
                            logger.error(f"Error fetching game mode: {e}")

                        try:
                            vol = await self.device.get_volume()
                            self.volume_updated.emit(vol)
                        except Exception as e:
                            logger.error(f"Error fetching volume: {e}")
                            
                    except Exception as e:
                        logger.warning(f"Connection attempt failed: {e}")
                        self._retry_count += 1
                        if self._retry_count >= self.MAX_AUTO_RETRIES:
                            # Give up automatically retrying; wait for a manual Connect click.
                            self._connect_event.clear()
                            self.connection_status.emit("disconnected_manual")
                        else:
                            self.connection_status.emit("disconnected")
                            await asyncio.sleep(self.RETRY_BACKOFF_SECONDS * self._retry_count)
                        continue
                else:
                    # Connected poller loop
                    try:
                        bat = await self.device.get_battery()
                        self.battery_updated.emit(bat)
                    except Exception as e:
                        logger.error(f"Error in battery poll: {e}")
                        # Socket closed or failed, reset loop
                        await self.device.disconnect()
                        self._retry_count = 0  # fresh retry budget after a stable connection drops
                        self.connection_status.emit("disconnected")
                    await asyncio.sleep(5)
                    
        self.main_task_obj = self.loop.create_task(main_task())
        try:
            self.loop.run_until_complete(self.main_task_obj)
        except asyncio.CancelledError:
            pass
        finally:
            self.loop.close()

    def _on_device_push(self, event, data):
        if event == "eq_changed":
            self.eq_updated.emit(int(data))
        elif event == "game_mode_changed":
            self.game_mode_updated.emit(data)
        elif event == "battery_changed":
            self.battery_updated.emit(data)

    def _on_trace_packet(self, direction: str, raw_data: bytes):
        desc = "Unparsed Bytes"
        try:
            frame = OppoFrame.from_bytes(raw_data)
            desc = get_friendly_description(frame, self.device.profile)
        except Exception:
            pass
        self.packet_traced.emit(direction, raw_data.hex().upper(), desc)

    def stop(self):
        self._running = False
        if self.loop and self.loop.is_running():
            # Schedule disconnect then cancel main task — ensures disconnect finishes before loop exits
            async def _shutdown():
                if self.device:
                    try:
                        await self.device.disconnect()
                    except Exception:
                        pass
                if hasattr(self, 'main_task_obj') and self.main_task_obj:
                    self.main_task_obj.cancel()
            asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)

    # Manual connect/disconnect control (called from the GUI thread)
    def request_connect(self):
        """Reset the retry budget and allow the main loop to attempt a connection."""
        if self.loop and self._connect_event:
            def _do():
                self._retry_count = 0
                self._connect_event.set()
            self.loop.call_soon_threadsafe(_do)

    def request_disconnect(self):
        """Cleanly close the socket and stop any further auto-retry until the user reconnects."""
        if self.loop and self.device:
            async def _do():
                if self._connect_event:
                    self._connect_event.clear()
                if self.device.is_connected:
                    await self.device.disconnect()
                self.connection_status.emit("disconnected_manual")
            asyncio.run_coroutine_threadsafe(_do(), self.loop)

    # Administrative/troubleshooting: OS-level Bluetooth control (BlueZ), distinct
    # from the app-level RFCOMM connect/disconnect above. Also drops audio.
    def force_bt_disconnect(self):
        if not self.loop:
            return
        async def _do():
            from .bluetooth_control import bt_disconnect, BluetoothControlError
            # Stop our own app-level socket and auto-retry first so the worker
            # isn't fighting to reconnect while we're tearing down the BT link.
            if self._connect_event:
                self._connect_event.clear()
            if self.device and self.device.is_connected:
                try:
                    await self.device.disconnect()
                except Exception:
                    pass
            self.connection_status.emit("disconnected_manual")
            try:
                await self.loop.run_in_executor(None, bt_disconnect, self.mac_address)
            except BluetoothControlError as e:
                logger.error(f"Force Bluetooth Disconnect failed: {e}")
                self.error_occurred.emit(f"Force Bluetooth Disconnect failed: {e}")
        asyncio.run_coroutine_threadsafe(_do(), self.loop)

    def force_bt_reconnect(self):
        if not self.loop:
            return
        async def _do():
            from .bluetooth_control import bt_connect, BluetoothControlError
            try:
                await self.loop.run_in_executor(None, bt_connect, self.mac_address)
            except BluetoothControlError as e:
                logger.error(f"Force Bluetooth Reconnect failed: {e}")
                self.error_occurred.emit(f"Force Bluetooth Reconnect failed: {e}")
                return
            # BT link is back — let the app's own connect flow (with its normal
            # retry policy) re-establish the RFCOMM control channel.
            self.request_connect()
        asyncio.run_coroutine_threadsafe(_do(), self.loop)

    # Slot triggers
    def change_eq(self, preset: int):
        if self.device and self.loop:
            async def _task():
                try:
                    await self.device.set_eq(EQPreset(preset))
                    eq = await self.device.get_eq()
                    self.eq_updated.emit(int(eq))
                except Exception as e:
                    logger.error(f"Error setting and reading EQ: {e}")
                    self.error_occurred.emit(f"Failed to set EQ preset: {e}")
            asyncio.run_coroutine_threadsafe(_task(), self.loop)

    def toggle_game_mode(self, enable: bool):
        if self.device and self.loop:
            async def _task():
                try:
                    await self.device.set_game_mode(enable)
                    gm = await self.device.get_game_mode()
                    self.game_mode_updated.emit(gm)
                except Exception as e:
                    logger.error(f"Error setting and reading game mode: {e}")
                    self.error_occurred.emit(f"Failed to toggle Game Mode: {e}")
            asyncio.run_coroutine_threadsafe(_task(), self.loop)
            
    def trigger_ring(self, start: bool):
        if self.device and self.loop:
            asyncio.run_coroutine_threadsafe(self.device.find_device(start), self.loop)

    def change_volume(self, volume: int):
        if self.device and self.loop:
            async def _task():
                try:
                    await self.device.set_volume(volume)
                    vol = await self.device.get_volume()
                    self.volume_updated.emit(vol)
                except Exception as e:
                    logger.error(f"Error setting and reading volume: {e}")
                    self.error_occurred.emit(f"Failed to set prompt volume: {e}")
            asyncio.run_coroutine_threadsafe(_task(), self.loop)

    def set_trace_mode(self, enable: bool):
        self.trace_mode = enable
        if self.device:
            self.device._transport.trace_mode = enable
            
    def fetch_gestures(self):
        async def fetch():
            try:
                gestures = await self.device.get_gestures()
                self.gestures_updated.emit(gestures)
            except Exception as e:
                self.error_occurred.emit(f"Failed to fetch gestures: {e}")
        if self.loop:
            asyncio.run_coroutine_threadsafe(fetch(), self.loop)


# --- Stylesheets ---

DARK_STYLESHEET = """
    QWidget {
        font-family: 'DejaVu Sans', sans-serif;
    }
    QMainWindow {
        background-color: #121212;
    }
    QWidget#sidebar-widget {
        background-color: #181818;
        border-right: 0.5px solid #282828;
    }
    QListWidget {
        background-color: transparent;
        border: none;
        color: #888888;
        font-family: 'DejaVu Sans', sans-serif;
        font-size: 11px;
        font-weight: bold;
    }
    QListWidget::item {
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 4px;
    }
    QListWidget::item:selected {
        background-color: #262626;
        color: #FFFFFF;
    }
    QListWidget::item:hover {
        background-color: #202020;
        color: #CCCCCC;
    }
    QFrame#card {
        background-color: #1A1A1A;
        border: 0.5px solid #282828;
        border-radius: 12px;
    }
    QLabel {
        color: #FFFFFF;
        font-family: 'DejaVu Sans', sans-serif;
    }
    QLabel#section-title {
        font-size: 12px;
        font-weight: bold;
        color: #E0E0E0;
    }
    QLabel#section-subtitle {
        font-size: 11px;
        color: #8E8E93;
    }
    QComboBox {
        background-color: #262626;
        border: 1px solid #383838;
        border-radius: 6px;
        padding: 4px 8px;
        color: #FFFFFF;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #262626;
        color: #FFFFFF;
        selection-background-color: #383838;
    }
    QCheckBox {
        spacing: 8px;
        color: #FFFFFF;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #383838;
        border-radius: 4px;
        background-color: #262626;
    }
    QCheckBox::indicator:checked {
        background-color: #30D158;
        border: 1px solid #30D158;
    }
    QPushButton {
        background-color: #262626;
        border: 1px solid #383838;
        border-radius: 6px;
        padding: 6px 12px;
        color: #FFFFFF;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #323232;
    }
    QPushButton:pressed {
        background-color: #404040;
    }
    QPushButton:checked {
        background-color: #30D158;
        color: #121212;
        font-weight: bold;
        border: 1px solid #30D158;
    }
    QProgressBar {
        border: 0.5px solid #383838;
        border-radius: 4px;
        text-align: center;
        background-color: #181818;
        color: #FFFFFF;
        font-size: 9px;
        height: 12px;
    }
    QProgressBar::chunk {
        border-radius: 3px;
    }
    QSlider::groove:horizontal {
        border: 1px solid #3A3A3A;
        height: 6px;
        background: #242424;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #30D158;
        border: 1px solid #30D158;
        width: 14px;
        height: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QTextEdit {
        background-color: #181818;
        border: 0.5px solid #282828;
        color: #30D158;
        font-family: 'monospace';
        font-size: 11px;
        border-radius: 8px;
    }
    QScrollArea {
        border: 0.5px solid #2B2B2B;
        background-color: #1C1C1C;
        border-radius: 10px;
    }
"""

LIGHT_STYLESHEET = """
    QWidget {
        font-family: 'DejaVu Sans', sans-serif;
    }
    QMainWindow {
        background-color: #F5F5F7;
    }
    QWidget#sidebar-widget {
        background-color: #EAEAEA;
        border-right: 0.5px solid #DCDCE0;
    }
    QListWidget {
        background-color: transparent;
        border: none;
        color: #666666;
        font-family: 'DejaVu Sans', sans-serif;
        font-size: 11px;
        font-weight: bold;
    }
    QListWidget::item {
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 4px;
    }
    QListWidget::item:selected {
        background-color: #D2D2D7;
        color: #000000;
    }
    QListWidget::item:hover {
        background-color: #E3E3E8;
        color: #333333;
    }
    QFrame#card {
        background-color: #FFFFFF;
        border: 0.5px solid #E5E5EA;
        border-radius: 12px;
    }
    QLabel {
        color: #1C1C1E;
        font-family: 'DejaVu Sans', sans-serif;
    }
    QLabel#section-title {
        font-size: 12px;
        font-weight: bold;
        color: #1C1C1E;
    }
    QLabel#section-subtitle {
        font-size: 11px;
        color: #8A8A8E;
    }
    QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #D2D2D7;
        border-radius: 6px;
        padding: 4px 8px;
        color: #1C1C1E;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        color: #1C1C1E;
        selection-background-color: #E5E5EA;
    }
    QCheckBox {
        spacing: 8px;
        color: #1C1C1E;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #D2D2D7;
        border-radius: 4px;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:checked {
        background-color: #34C759;
        border: 1px solid #34C759;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D2D2D7;
        border-radius: 6px;
        padding: 6px 12px;
        color: #1C1C1E;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #F5F5F7;
    }
    QPushButton:pressed {
        background-color: #E5E5EA;
    }
    QPushButton:checked {
        background-color: #34C759;
        color: #FFFFFF;
        font-weight: bold;
        border: 1px solid #34C759;
    }
    QProgressBar {
        border: 0.5px solid #D2D2D7;
        border-radius: 4px;
        text-align: center;
        background-color: #E5E5EA;
        color: #1C1C1E;
        font-size: 9px;
        height: 12px;
    }
    QProgressBar::chunk {
        border-radius: 3px;
    }
    QSlider::groove:horizontal {
        border: 1px solid #D2D2D7;
        height: 6px;
        background: #E5E5EA;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #34C759;
        border: 1px solid #34C759;
        width: 14px;
        height: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QTextEdit {
        background-color: #FFFFFF;
        border: 0.5px solid #D2D2D7;
        color: #34C759;
        font-family: 'monospace';
        font-size: 11px;
        border-radius: 8px;
    }
    QScrollArea {
        border: 0.5px solid #D2D2D7;
        background-color: #FFFFFF;
        border-radius: 10px;
    }
"""


# --- Main UI Window ---

class MainWindow(QMainWindow):
    def __init__(self, mac_address="60:55:56:22:49:A0"):
        super().__init__()
        self.mac_address = mac_address
        self.is_connected = False
        self.theme_mode = "dark"

        self.setWindowTitle("OPPO Linux Companion")
        self.setFixedSize(620, 500)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sidebar Navigation
        sidebar_widget = QWidget()
        sidebar_widget.setObjectName("sidebar-widget")
        sidebar_widget.setFixedWidth(160)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)

        app_title = QLabel("OPPO Companion")
        app_title.setFont(QFont("DejaVu Sans", 11, QFont.Bold))
        app_title.setStyleSheet("margin-bottom: 20px; padding-left: 6px;")
        sidebar_layout.addWidget(app_title)

        self.sidebar = QListWidget()
        self.sidebar.addItem("🎛️  Dashboard")
        self.sidebar.addItem("👆  Gestures")
        self.sidebar.addItem("⚙️  Settings")
        self.sidebar.addItem("🛠️  Developer Tools")
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._on_navigation_changed)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_layout.addWidget(self.sidebar)
        
        sidebar_layout.addStretch()

        # Manual Connect/Disconnect control
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_button_clicked)
        sidebar_layout.addWidget(self.connect_btn)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(6, 0, 6, 0)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #D32F2F; font-size: 14px;")
        status_layout.addWidget(self.status_dot)
        self.status_lbl = QLabel("Offline")
        self.status_lbl.setStyleSheet("color: #888888; font-size: 10px;")
        status_layout.addWidget(self.status_lbl)
        status_layout.addStretch()
        sidebar_layout.addLayout(status_layout)

        layout.addWidget(sidebar_widget)

        # 2. Page Stack
        self.stacked_pages = QStackedWidget()
        layout.addWidget(self.stacked_pages)

        # Initialize state-tracking for verified non-optimistic updates
        self._confirmed_eq = 0
        self._confirmed_game_mode = False
        self._confirmed_volume = 50

        # Initialize pages
        self._init_dashboard_page()
        self._init_gestures_page()
        self._init_settings_page()
        self._init_dev_page()

        # Disable telemetry controls by default until connection
        self._set_controls_enabled(False)

        # Apply default theme
        self.apply_theme("dark")

        # Initialize Worker Thread
        self.worker = OppoDeviceWorker(self.mac_address)
        self.worker.connection_status.connect(self._on_connection_changed)
        self.worker.profile_detected.connect(self._on_profile_detected)
        self.worker.battery_updated.connect(self._on_battery_received)
        self.worker.eq_updated.connect(self._on_eq_received)
        self.worker.game_mode_updated.connect(self._on_game_mode_received)
        self.worker.firmware_updated.connect(self._on_firmware_received)
        self.worker.gestures_updated.connect(self._on_gestures_received)
        self.worker.volume_updated.connect(self._on_volume_received)
        self.worker.packet_traced.connect(self._on_packet_traced)
        self.worker.error_occurred.connect(self._on_worker_error)

        # Synchronize default trace mode state to worker after worker instantiation
        self.worker.set_trace_mode(self.trace_cb.isChecked())

        self.worker.start()

    # --- UI Layout Generation ---

    def _init_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title Block
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self.title_label = QLabel("OPPO Enco Buds3 Pro")
        self.title_label.setFont(QFont("DejaVu Sans", 13, QFont.Bold))
        title_block.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Offline")
        self.subtitle_label.setObjectName("section-subtitle")
        title_block.addWidget(self.subtitle_label)
        layout.addLayout(title_block)

        # Silhouettes Display Card
        sil_card = QFrame()
        sil_card.setObjectName("card")
        sil_layout = QHBoxLayout(sil_card)
        sil_layout.setContentsMargins(10, 10, 10, 10)

        # Left Column
        left_layout = QVBoxLayout()
        self.left_silhouette = SilhouetteWidget("left")
        left_layout.addWidget(self.left_silhouette, 0, Qt.AlignCenter)
        
        left_batt_row = QHBoxLayout()
        left_batt_row.setSpacing(4)
        left_batt_row.setAlignment(Qt.AlignCenter)
        self.left_bolt_lbl = QLabel("⚡")
        self.left_bolt_lbl.setStyleSheet("color: #30D158; font-size: 11px; font-weight: bold;")
        self.left_bolt_lbl.setVisible(False)
        left_batt_row.addWidget(self.left_bolt_lbl)
        
        self.left_battery_widget = BatteryWidget()
        left_batt_row.addWidget(self.left_battery_widget)
        
        self.left_battery_lbl = QLabel("--%")
        self.left_battery_lbl.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        left_batt_row.addWidget(self.left_battery_lbl)
        left_layout.addLayout(left_batt_row)
        
        left_label = QLabel("Left")
        left_label.setObjectName("section-subtitle")
        left_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_label)
        sil_layout.addLayout(left_layout)

        # Right Column
        right_layout = QVBoxLayout()
        self.right_silhouette = SilhouetteWidget("right")
        right_layout.addWidget(self.right_silhouette, 0, Qt.AlignCenter)
        
        right_batt_row = QHBoxLayout()
        right_batt_row.setSpacing(4)
        right_batt_row.setAlignment(Qt.AlignCenter)
        self.right_bolt_lbl = QLabel("⚡")
        self.right_bolt_lbl.setStyleSheet("color: #30D158; font-size: 11px; font-weight: bold;")
        self.right_bolt_lbl.setVisible(False)
        right_batt_row.addWidget(self.right_bolt_lbl)
        
        self.right_battery_widget = BatteryWidget()
        right_batt_row.addWidget(self.right_battery_widget)
        
        self.right_battery_lbl = QLabel("--%")
        self.right_battery_lbl.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        right_batt_row.addWidget(self.right_battery_lbl)
        right_layout.addLayout(right_batt_row)
        
        right_label = QLabel("Right")
        right_label.setObjectName("section-subtitle")
        right_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_label)
        sil_layout.addLayout(right_layout)

        # Case Column
        case_layout = QVBoxLayout()
        self.case_silhouette = SilhouetteWidget("case")
        case_layout.addWidget(self.case_silhouette, 0, Qt.AlignCenter)
        
        case_batt_row = QHBoxLayout()
        case_batt_row.setSpacing(4)
        case_batt_row.setAlignment(Qt.AlignCenter)
        self.case_bolt_lbl = QLabel("⚡")
        self.case_bolt_lbl.setStyleSheet("color: #30D158; font-size: 11px; font-weight: bold;")
        self.case_bolt_lbl.setVisible(False)
        case_batt_row.addWidget(self.case_bolt_lbl)
        
        self.case_battery_widget = BatteryWidget()
        case_batt_row.addWidget(self.case_battery_widget)
        
        self.case_battery_lbl = QLabel("--%")
        self.case_battery_lbl.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        case_batt_row.addWidget(self.case_battery_lbl)
        case_layout.addLayout(case_batt_row)
        
        case_label = QLabel("Case")
        case_label.setObjectName("section-subtitle")
        case_label.setAlignment(Qt.AlignCenter)
        case_layout.addWidget(case_label)
        sil_layout.addLayout(case_layout)

        layout.addWidget(sil_card)

        # ANC Control Card
        self.anc_card = QFrame()
        self.anc_card.setObjectName("card")
        anc_layout = QVBoxLayout(self.anc_card)
        anc_layout.setContentsMargins(12, 12, 12, 12)
        
        anc_title = QLabel("Acoustic Noise Control")
        anc_title.setObjectName("section-title")
        anc_layout.addWidget(anc_title)

        anc_buttons_layout = QHBoxLayout()
        anc_buttons_layout.setSpacing(10)

        self.anc_group = QButtonGroup(self)
        self.anc_group.setExclusive(True)

        self.btn_anc = QPushButton("ANC")
        self.btn_anc.setCheckable(True)
        self.anc_group.addButton(self.btn_anc)
        anc_buttons_layout.addWidget(self.btn_anc)

        self.btn_anc_off = QPushButton("Normal (Off)")
        self.btn_anc_off.setCheckable(True)
        self.btn_anc_off.setChecked(True)
        self.anc_group.addButton(self.btn_anc_off)
        anc_buttons_layout.addWidget(self.btn_anc_off)

        self.btn_transparency = QPushButton("Transparency")
        self.btn_transparency.setCheckable(True)
        self.anc_group.addButton(self.btn_transparency)
        anc_buttons_layout.addWidget(self.btn_transparency)

        self.anc_group.buttonToggled.connect(self._on_anc_changed)
        anc_layout.addLayout(anc_buttons_layout)
        layout.addWidget(self.anc_card)

        # EQ Control Card
        self.eq_card = QFrame()
        self.eq_card.setObjectName("card")
        eq_layout = QHBoxLayout(self.eq_card)
        eq_layout.setContentsMargins(12, 12, 12, 12)

        eq_lbl = QLabel("Equalizer Master Preset")
        eq_lbl.setObjectName("section-title")
        eq_layout.addWidget(eq_lbl)
        eq_layout.addStretch()

        self.eq_dropdown = QComboBox()
        self.eq_dropdown.addItems(["Original (Balanced)", "Clear Vocals", "Bass Boost"])
        self.eq_dropdown.currentIndexChanged.connect(self._on_eq_ui_changed)
        eq_layout.addWidget(self.eq_dropdown)
        layout.addWidget(self.eq_card)

        # Game Mode Card
        self.gm_card = QFrame()
        self.gm_card.setObjectName("card")
        gm_layout = QHBoxLayout(self.gm_card)
        gm_layout.setContentsMargins(12, 12, 12, 12)

        self.game_mode_cb = QCheckBox("Low-Latency Game Mode")
        self.game_mode_cb.setFont(QFont("DejaVu Sans", 10))
        self.game_mode_cb.stateChanged.connect(self._on_game_mode_ui_changed)
        gm_layout.addWidget(self.game_mode_cb)
        layout.addWidget(self.gm_card)

        self.stacked_pages.addWidget(page)

    def _init_gestures_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Touch Controls Mapping")
        title.setFont(QFont("DejaVu Sans", 13, QFont.Bold))
        header.addWidget(title)
        
        header.addStretch()
        self.btn_refresh_gestures = QPushButton("Refresh")
        self.btn_refresh_gestures.clicked.connect(self._refresh_gestures)
        header.addWidget(self.btn_refresh_gestures)
        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: 0.5px solid #2B2B2B;
                background-color: #1C1C1C;
                border-radius: 10px;
            }
        """)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.stacked_pages.addWidget(page)

    def _init_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("Device Settings")
        header.setFont(QFont("DejaVu Sans", 13, QFont.Bold))
        layout.addWidget(header)

        # Firmware
        fw_card = QFrame()
        fw_card.setObjectName("card")
        fw_layout = QHBoxLayout(fw_card)
        fw_layout.setContentsMargins(12, 12, 12, 12)

        fw_lbl = QLabel("Firmware Version")
        fw_lbl.setObjectName("section-title")
        fw_layout.addWidget(fw_lbl)
        fw_layout.addStretch()

        self.fw_version_lbl = QLabel("Fetching...")
        self.fw_version_lbl.setStyleSheet("color: #888888;")
        fw_layout.addWidget(self.fw_version_lbl)
        layout.addWidget(fw_card)

        # Prompt Tone Volume
        self.vol_card = QFrame()
        self.vol_card.setObjectName("card")
        vol_layout = QVBoxLayout(self.vol_card)
        vol_layout.setContentsMargins(12, 12, 12, 12)

        vol_header = QHBoxLayout()
        vol_lbl = QLabel("Alert Sound Volume")
        vol_lbl.setObjectName("section-title")
        vol_header.addWidget(vol_lbl)
        vol_header.addStretch()
        self.vol_value_lbl = QLabel("--%")
        self.vol_value_lbl.setStyleSheet("color: #888888;")
        vol_header.addWidget(self.vol_value_lbl)
        vol_layout.addLayout(vol_header)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(10, 100)
        self.vol_slider.setValue(10)
        self.vol_slider.valueChanged.connect(self._on_volume_slider_changed)
        self.vol_slider.sliderReleased.connect(self._on_volume_slider_released)
        vol_layout.addWidget(self.vol_slider)
        layout.addWidget(self.vol_card)

        # Find Buds Locator
        self.ring_card = QFrame()
        self.ring_card.setObjectName("card")
        ring_layout = QHBoxLayout(self.ring_card)
        ring_layout.setContentsMargins(12, 12, 12, 12)

        ring_lbl = QLabel("Find My Earbuds")
        ring_lbl.setObjectName("section-title")
        ring_layout.addWidget(ring_lbl)
        ring_layout.addStretch()

        self.btn_ring = QPushButton("Ring Earbuds")
        self.btn_ring.setMinimumWidth(120)
        self.btn_ring.setCheckable(True)
        self.btn_ring.clicked.connect(self._on_ring_toggled)
        ring_layout.addWidget(self.btn_ring)
        layout.addWidget(self.ring_card)

        # App Theme Selector Card
        theme_card = QFrame()
        theme_card.setObjectName("card")
        theme_layout = QHBoxLayout(theme_card)
        theme_layout.setContentsMargins(12, 12, 12, 12)

        theme_lbl = QLabel("App Theme")
        theme_lbl.setObjectName("section-title")
        theme_layout.addWidget(theme_lbl)
        theme_layout.addStretch()

        self.theme_dropdown = QComboBox()
        self.theme_dropdown.addItems(["Dark Mode", "Light Mode"])
        self.theme_dropdown.currentIndexChanged.connect(self._on_theme_dropdown_changed)
        theme_layout.addWidget(self.theme_dropdown)
        layout.addWidget(theme_card)

        layout.addStretch()
        self.stacked_pages.addWidget(page)

    def _init_dev_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("Developer Diagnostics")
        header.setFont(QFont("DejaVu Sans", 13, QFont.Bold))
        layout.addWidget(header)

        # Enable Tracing Checkbox (checked by default for immediate diagnostic visibility)
        self.trace_cb = QCheckBox("Enable raw packet tracing")
        self.trace_cb.setFont(QFont("DejaVu Sans", 10))
        self.trace_cb.setChecked(True)
        self.trace_cb.stateChanged.connect(self._on_trace_mode_changed)
        layout.addWidget(self.trace_cb)

        # Administrative / troubleshooting: OS-level Bluetooth control card.
        # Distinct from the sidebar Connect/Disconnect button, which only
        # affects this app's own RFCOMM control channel.
        bt_card = QFrame()
        bt_card.setObjectName("card")
        bt_layout = QVBoxLayout(bt_card)
        bt_layout.setContentsMargins(12, 12, 12, 12)

        bt_title = QLabel("Bluetooth Link (System-Level)")
        bt_title.setObjectName("section-title")
        bt_layout.addWidget(bt_title)

        bt_subtitle = QLabel(
            "Forces the OS Bluetooth pairing itself to drop or reconnect — "
            "not just this app. This also disconnects audio (A2DP/HSP). "
            "Use for troubleshooting a bad earbud/case link, not routine use."
        )
        bt_subtitle.setObjectName("section-subtitle")
        bt_subtitle.setWordWrap(True)
        bt_layout.addWidget(bt_subtitle)

        bt_buttons_layout = QHBoxLayout()
        bt_buttons_layout.setSpacing(10)

        self.btn_force_bt_disconnect = QPushButton("Force Bluetooth Disconnect")
        self.btn_force_bt_disconnect.clicked.connect(self._on_force_bt_disconnect_clicked)
        bt_buttons_layout.addWidget(self.btn_force_bt_disconnect)

        self.btn_force_bt_reconnect = QPushButton("Force Bluetooth Reconnect")
        self.btn_force_bt_reconnect.clicked.connect(self._on_force_bt_reconnect_clicked)
        bt_buttons_layout.addWidget(self.btn_force_bt_reconnect)

        bt_layout.addLayout(bt_buttons_layout)
        layout.addWidget(bt_card)

        # Tracing Output Log console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Tracing disabled. Click checkbox to trace transactions...")
        layout.addWidget(self.console)

        # Clear button
        clear_btn = QPushButton("Clear Trace Log")
        clear_btn.clicked.connect(self.console.clear)
        layout.addWidget(clear_btn)

        self.stacked_pages.addWidget(page)

    # --- Worker Thread Signal Handlers ---

    @Slot(str)
    def _on_connection_changed(self, state: str):
        if state == "connected":
            self.is_connected = True
            self.status_dot.setStyleSheet("color: #30D158; font-size: 14px;")
            self.status_lbl.setText("Connected")
            self.status_lbl.setStyleSheet("color: #30D158; font-size: 10px;")
            self.subtitle_label.setText("Connected")
            self._set_controls_enabled(True)
            self.btn_refresh_gestures.setEnabled(True)
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self._refresh_gestures()
        elif state == "connecting":
            self.is_connected = False
            self.status_dot.setStyleSheet("color: #FF9F0A; font-size: 14px;")
            self.status_lbl.setText("Connecting...")
            self.status_lbl.setStyleSheet("color: #FF9F0A; font-size: 10px;")
            self.subtitle_label.setText("Connecting...")
            self._set_controls_enabled(False)
            self.btn_refresh_gestures.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
        elif state == "disconnected":
            # Auto-retry still in progress — no action needed from the user yet.
            self.is_connected = False
            self.status_dot.setStyleSheet("color: #FF9F0A; font-size: 14px;")
            self.status_lbl.setText("Reconnecting...")
            self.status_lbl.setStyleSheet("color: #FF9F0A; font-size: 10px;")
            self.subtitle_label.setText("Reconnecting...")
            self._set_controls_enabled(False)
            self.btn_refresh_gestures.setEnabled(False)
            self.connect_btn.setText("Reconnecting...")
            self.connect_btn.setEnabled(False)
            self._reset_telemetry_ui()
        else:
            # "disconnected_manual" — auto-retries exhausted (or user disconnected):
            # give control back to the user via the button.
            self.is_connected = False
            self.status_dot.setStyleSheet("color: #FF453A; font-size: 14px;")
            self.status_lbl.setText("Offline")
            self.status_lbl.setStyleSheet("color: #888888; font-size: 10px;")
            self.subtitle_label.setText("Offline")
            self._set_controls_enabled(False)
            self.btn_refresh_gestures.setEnabled(False)
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self._reset_telemetry_ui()

    @Slot(object)
    def _on_profile_detected(self, profile):
        """DYNAMICAL capability-aware show/hide of widgets based on target profile."""
        logger.info(f"Applying profile layout for: {profile.name}")
        self.title_label.setText(profile.name)
        
        # Show or hide widgets conditionally
        self.anc_card.setVisible(profile.supports_anc)
        self.eq_card.setVisible(profile.supports_eq)
        self.gm_card.setVisible(profile.supports_game_mode)
        self.vol_card.setVisible(profile.supports_volume)
        self.ring_card.setVisible(profile.supports_find)

    @Slot(object)
    def _on_battery_received(self, battery: EarbudsBattery):
        self.left_battery_lbl.setText(f"{battery.left}%")
        self.right_battery_lbl.setText(f"{battery.right}%")
        
        self.left_bolt_lbl.setVisible(battery.left.is_charging)
        self.right_bolt_lbl.setVisible(battery.right.is_charging)
        
        self.left_battery_widget.set_state(battery.left, battery.left.is_charging, self.theme_mode)
        self.right_battery_widget.set_state(battery.right, battery.right.is_charging, self.theme_mode)

        if battery.case != -1:
            self.case_battery_lbl.setText(f"{battery.case}%")
            self.case_bolt_lbl.setVisible(battery.case.is_charging)
            self.case_battery_widget.set_state(battery.case, battery.case.is_charging, self.theme_mode)
            self.case_battery_widget.setVisible(True)
        else:
            self.case_battery_lbl.setText("Disconnected")
            self.case_bolt_lbl.setVisible(False)
            self.case_battery_widget.setVisible(False)

        self.left_silhouette.update_state(self.is_connected, battery.left, battery.left.is_charging)
        self.right_silhouette.update_state(self.is_connected, battery.right, battery.right.is_charging)
        self.case_silhouette.update_state(self.is_connected and battery.case != -1, battery.case, battery.case.is_charging)

    @Slot(int)
    def _on_eq_received(self, preset_idx: int):
        self._confirmed_eq = preset_idx
        self.eq_dropdown.blockSignals(True)
        self.eq_dropdown.setCurrentIndex(preset_idx)
        self.eq_dropdown.blockSignals(False)
        self.eq_dropdown.setEnabled(True)
        self.status_lbl.setText("Connected")
        self.status_lbl.setStyleSheet("color: #30D158; font-size: 10px;")

    @Slot(bool)
    def _on_game_mode_received(self, enable: bool):
        self._confirmed_game_mode = enable
        self.game_mode_cb.blockSignals(True)
        self.game_mode_cb.setChecked(enable)
        self.game_mode_cb.blockSignals(False)
        self.game_mode_cb.setEnabled(True)
        self.status_lbl.setText("Connected")
        self.status_lbl.setStyleSheet("color: #00E676; font-size: 10px;")

    @Slot(str)
    def _on_firmware_received(self, version: str):
        self.fw_version_lbl.setText(version)

    @Slot(int)
    def _on_volume_received(self, volume: int):
        volume = max(10, volume)
        self._confirmed_volume = volume
        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(volume)
        self.vol_slider.blockSignals(False)
        self.vol_slider.setEnabled(True)
        self.vol_value_lbl.setText(f"{volume}%")
        self.status_lbl.setText("Connected")
        self.status_lbl.setStyleSheet("color: #30D158; font-size: 10px;")

    @Slot(list)
    def _on_gestures_received(self, gestures: list):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not gestures:
            lbl = QLabel("No gesture configurations mapped.")
            lbl.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(lbl)
            return

        for gesture in gestures:
            row = QFrame()
            row.setObjectName("card")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 4, 10, 4)

            lbl = QLabel(str(gesture))
            lbl.setFont(QFont("DejaVu Sans", 9))
            lbl.setStyleSheet("border: none; background: transparent;")
            row_layout.addWidget(lbl)

            self.scroll_layout.addWidget(row)

    @Slot(str, str, str)
    def _on_packet_traced(self, direction: str, raw_hex: str, desc: str):
        ts = time.strftime('%H:%M:%S')
        line = f"[{ts}] {direction} ➔ {raw_hex} | {desc}\n"
        self.console.append(line)

    @Slot(str)
    def _on_worker_error(self, err_msg: str):
        logger.error(f"Worker Error: {err_msg}")
        self.status_lbl.setText("Apply Failed")
        self.status_lbl.setStyleSheet("color: #D32F2F; font-size: 10px;")
        
        # Restore control states to their last confirmed configurations
        self.eq_dropdown.blockSignals(True)
        self.eq_dropdown.setCurrentIndex(self._confirmed_eq)
        self.eq_dropdown.blockSignals(False)
        self.eq_dropdown.setEnabled(True)

        self.game_mode_cb.blockSignals(True)
        self.game_mode_cb.setChecked(self._confirmed_game_mode)
        self.game_mode_cb.blockSignals(False)
        self.game_mode_cb.setEnabled(True)

        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(self._confirmed_volume)
        self.vol_slider.blockSignals(False)
        self.vol_slider.setEnabled(True)
        self.vol_value_lbl.setText(f"{self._confirmed_volume}%")

    # --- UI Slot Interaction triggers ---

    def _on_navigation_changed(self, idx: int):
        self.stacked_pages.setCurrentIndex(idx)

    def _on_connect_button_clicked(self):
        if self.is_connected:
            self.connect_btn.setEnabled(False)
            self.worker.request_disconnect()
        else:
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            self.worker.request_connect()

    def _on_force_bt_disconnect_clicked(self):
        reply = QMessageBox.question(
            self,
            "Force Bluetooth Disconnect",
            "This will drop the earbuds' Bluetooth connection at the system level "
            "(including audio), not just this app. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.worker.force_bt_disconnect()

    def _on_force_bt_reconnect_clicked(self):
        self.worker.force_bt_reconnect()

    def _on_eq_ui_changed(self, idx: int):
        if self.is_connected:
            self.status_lbl.setText("Applying...")
            self.status_lbl.setStyleSheet("color: #FFC107; font-size: 10px;")
            self.eq_dropdown.setEnabled(False)
            self.worker.change_eq(idx)

    def _on_game_mode_ui_changed(self, state: int):
        if self.is_connected:
            # stateChanged emits an int; Qt.Checked is a CheckState enum in
            # PySide6, so comparing them directly always evaluates False.
            enable = state == Qt.Checked.value
            self.status_lbl.setText("Applying...")
            self.status_lbl.setStyleSheet("color: #FFC107; font-size: 10px;")
            self.game_mode_cb.setEnabled(False)
            self.worker.toggle_game_mode(enable)

    def _on_anc_changed(self, btn, checked):
        if checked and self.is_connected:
            mode = btn.text().lower()
            asyncio.run_coroutine_threadsafe(self.worker.device.set_anc_mode(mode), self.worker.loop)

    def _on_volume_slider_changed(self, val: int):
        self.vol_value_lbl.setText(f"{val}%")

    def _on_volume_slider_released(self):
        if self.is_connected:
            val = self.vol_slider.value()
            self.status_lbl.setText("Applying...")
            self.status_lbl.setStyleSheet("color: #FFC107; font-size: 10px;")
            self.vol_slider.setEnabled(False)
            self.worker.change_volume(val)

    def _on_ring_toggled(self, checked):
        if self.is_connected:
            self.worker.trigger_ring(checked)
            if checked:
                self.btn_ring.setText("Stop Ringing")
                self.btn_ring.setStyleSheet("""
                    QPushButton {
                        background-color: #D32F2F;
                        border: 1px solid #D32F2F;
                        color: #FFFFFF;
                    }
                """)
            else:
                self.btn_ring.setText("Ring Earbuds")
                self.btn_ring.setStyleSheet("")

    def _on_trace_mode_changed(self, state: int):
        enable = state == Qt.Checked.value
        if hasattr(self, 'worker') and self.worker:
            self.worker.set_trace_mode(enable)
        if enable:
            self.console.append("[Trace Enabled]\n")
        else:
            self.console.append("[Trace Disabled]\n")

    def _refresh_gestures(self):
        if self.is_connected:
            self.worker.fetch_gestures()

    def _set_controls_enabled(self, enable: bool):
        """Enable or disable telemetry editing widgets based on connection state."""
        self.eq_dropdown.setEnabled(enable)
        self.game_mode_cb.setEnabled(enable)
        self.vol_slider.setEnabled(enable)
        self.btn_ring.setEnabled(enable)
        self.btn_anc.setEnabled(enable)
        self.btn_anc_off.setEnabled(enable)
        self.btn_transparency.setEnabled(enable)

    def _reset_telemetry_ui(self):
        self.title_label.setText("OPPO Enco Buds3 Pro")
        self.subtitle_label.setText("Offline")
        self.left_battery_lbl.setText("--%")
        self.right_battery_lbl.setText("--%")
        self.case_battery_lbl.setText("--%")
        self.fw_version_lbl.setText("Fetching...")
        self.vol_value_lbl.setText("--%")
        
        self.left_bolt_lbl.setVisible(False)
        self.right_bolt_lbl.setVisible(False)
        self.case_bolt_lbl.setVisible(False)
        
        self.left_battery_widget.set_state(0, False, self.theme_mode)
        self.right_battery_widget.set_state(0, False, self.theme_mode)
        self.case_battery_widget.set_state(0, False, self.theme_mode)
        
        self.left_silhouette.update_state(False)
        self.right_silhouette.update_state(False)
        self.case_silhouette.update_state(False)

        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def _on_theme_dropdown_changed(self, idx: int):
        mode = "dark" if idx == 0 else "light"
        self.apply_theme(mode)

    def apply_theme(self, mode: str):
        self.theme_mode = mode
        if mode == "light":
            self.setStyleSheet(LIGHT_STYLESHEET)
            self.theme_dropdown.blockSignals(True)
            self.theme_dropdown.setCurrentIndex(1)
            self.theme_dropdown.blockSignals(False)
        else:
            self.setStyleSheet(DARK_STYLESHEET)
            self.theme_dropdown.blockSignals(True)
            self.theme_dropdown.setCurrentIndex(0)
            self.theme_dropdown.blockSignals(False)
            
        # Update custom battery widgets
        if hasattr(self, 'left_battery_widget'):
            self.left_battery_widget.theme_mode = mode
            self.left_battery_widget.update()
        if hasattr(self, 'right_battery_widget'):
            self.right_battery_widget.theme_mode = mode
            self.right_battery_widget.update()
        if hasattr(self, 'case_battery_widget'):
            self.case_battery_widget.theme_mode = mode
            self.case_battery_widget.update()
            
        # Trigger updates
        if hasattr(self, 'left_silhouette'):
            self.left_silhouette.update()
        if hasattr(self, 'right_silhouette'):
            self.right_silhouette.update()
        if hasattr(self, 'case_silhouette'):
            self.case_silhouette.update()

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait()
        event.accept()


# --- CLI / Main Entry ---

def main():
    from PySide6.QtCore import QLocale
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

    mac = "60:55:56:22:49:A0"
    if len(sys.argv) > 1 and ":" in sys.argv[1]:
        mac = sys.argv[1]
        
    app = QApplication(sys.argv)
    window = MainWindow(mac)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
