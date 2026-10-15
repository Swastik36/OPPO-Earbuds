import os
# Override numeric locale to force Western digits in Qt widgets.
# Keep LC_CTYPE as UTF-8 so Qt's platform plugin doesn't complain.
os.environ["LC_NUMERIC"] = "C"
os.environ["LC_CTYPE"] = "C.UTF-8"
# Do NOT set LC_ALL — that overrides LC_CTYPE and breaks Qt's UTF-8 check.
import sys
import logging
import asyncio
import math
import time
from typing import Dict, List, Optional
from PySide6.QtCore import (
    Qt, QThread, Signal, Slot, QSize, QRectF, QPointF, QSettings,
    QPropertyAnimation, QEasingCurve,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QCheckBox, QPushButton, QFrame, QDialog,
    QScrollArea, QStackedWidget, QListWidget, QProgressBar, QSlider,
    QButtonGroup, QTextEdit, QSizePolicy, QMessageBox, QMenu,
    QSystemTrayIcon, QStyle, QBoxLayout
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QIcon, QPainterPath, QAction,
    QPixmap,
)

from .device import OppoDevice, get_friendly_description
from .commands import EQPreset, EarbudsBattery, TouchGesture
from .protocol import OppoFrame
from .exceptions import OppoConnectionError

# App identity (QSettings persistence) + connection defaults.
# The MAC below is only the last-resort fallback: --mac flag wins,
# then the remembered value in QSettings, then this constant.
ORG_NAME = "Swastik36"
APP_NAME = "OPPOCompanion"
DEFAULT_MAC = "60:55:56:22:49:A0"

# Gesture function IDs (mirrors TouchGesture func map in commands.py).
GESTURE_FUNCTIONS: Dict[int, str] = {
    0x00: "No Action",
    0x01: "Play/Pause",
    0x05: "Previous Track",
    0x06: "Next Track",
    0x0B: "Volume Down",
    0x0C: "Volume Up",
    0x1C: "Game Mode Toggle",
}
TRIGGER_NAMES = {
    1: "Single Tap", 2: "Double Tap", 3: "Triple Tap",
    4: "Long Press", 5: "Double & Hold", 6: "Slide",
}

# Coffee palette (Espresso Crema): shared by stylesheets + custom painters.
COFFEE = {
    "dark_bg": "#211510",
    "dark_header": "#2B1B14",
    "dark_card": "#33231A",
    "dark_field": "#3A261D",
    "dark_text": "#F3E7D6",
    "dark_sub": "#C9B19C",
    "light_bg": "#F6F1E7",
    "light_card": "#FFFDF8",
    "light_border": "#E3D5C0",
    "light_text": "#3A241D",
    "light_sub": "#8B6A55",
    "accent": "#D9A441",
    "accent_hi": "#E8B85C",
    "accent_dim": "#A96B1F",
    "ok": "#7FB069",
    "warn": "#D9A441",
    "err": "#C0564B",
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oppo_control.gui")

# --- Battery Shell Widget (Mockup v4 Style) ---

class BatteryWidget(QWidget):
    def __init__(self, parent=None, scale=1.0):
        super().__init__(parent)
        self.level = 0
        self.is_charging = False
        self.theme_mode = "dark"
        self.scale = scale
        self.setFixedSize(int(22 * scale), int(12 * scale))

    def set_state(self, level, is_charging, theme_mode="dark"):
        self.level = max(0, min(100, level))
        self.is_charging = is_charging
        self.theme_mode = theme_mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        s = self.scale

        # Coffee battery bands: warm red when low, caramel mid,
        # leaf green at 90-100% (full feels rewarding).
        if self.level <= 20:
            color = QColor("#C0564B")
        elif self.level >= 90:
            color = QColor("#7FB069") if self.theme_mode == "dark" else QColor("#5F8F52")
        else:
            color = QColor("#D9A441") if self.theme_mode == "dark" else QColor("#A96B1F")

        # Draw battery border
        pen = QPen(color, 1.4 * s)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # Rect for battery shell
        painter.drawRoundedRect(int(1 * s), int(1 * s), int(16 * s), int(10 * s), 2 * s, 2 * s)

        # Draw dynamic fill
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))

        fill_w = max(0, min(12 * s, int(12 * s * (self.level / 100.0))))
        if fill_w > 0:
            painter.drawRect(int(3 * s), int(3 * s), int(fill_w), int(6 * s))

        # Draw the right battery tip
        painter.drawRoundedRect(QRectF(18 * s, 4 * s, 2 * s, 4 * s), 0.5 * s, 0.5 * s)


# --- Custom Vector Silhouettes Widget (Mockup v4 Style) ---

class SilhouetteWidget(QWidget):
    def __init__(self, item_type="left", parent=None):
        super().__init__(parent)
        self.item_type = item_type  # "left", "right", "case"
        self.battery_level = 0
        self.is_charging = False
        self.is_connected = False
        self.theme_mode = "dark"
        self.setMinimumSize(70, 90)

    def set_theme(self, theme_mode: str):
        # Silhouettes stay cream-white in every theme by design.
        self.update()

    def update_state(self, is_connected, level=0, is_charging=False):
        self.is_connected = is_connected
        self.battery_level = level
        self.is_charging = is_charging
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Cream-white buds on every theme; disconnected dims via opacity.
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


# --- Hand-drawn vector tab icons (no emoji, no assets) ---

def paint_tab_icon(kind: str, color: QColor, size: int = 20) -> QIcon:
    """Minimal 2px line icon for the compact nav bar."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    c = size / 2.0

    if kind == "dashboard":
        m, gap = 3.0, 2.0
        cell = (size - 2 * m - gap) / 2
        for ix in (m, m + cell + gap):
            for iy in (m, m + cell + gap):
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(ix, iy, cell, cell), 1.5, 1.5)
    elif kind == "gestures":
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(QPointF(c, c), 2.2, 2.2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(c - 5.5, c - 5.5, 11, 11), 0, 360 * 16)
        p.drawArc(QRectF(c - 8, c - 8, 16, 16), 30 * 16, 300 * 16)
    elif kind == "settings":
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(c, c), 4.0, 4.0)
        for k in range(8):
            a = math.radians(k * 45)
            p.drawLine(
                QPointF(c + 5.5 * math.cos(a), c + 5.5 * math.sin(a)),
                QPointF(c + 8.0 * math.cos(a), c + 8.0 * math.sin(a)),
            )
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(QPointF(c, c), 1.6, 1.6)
    elif kind == "dev":
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        left, right = c - 5, c + 5
        p.drawLine(QPointF(left + 3, c - 4), QPointF(left - 1, c))
        p.drawLine(QPointF(left - 1, c), QPointF(left + 3, c + 4))
        p.drawLine(QPointF(right - 3, c - 4), QPointF(right + 1, c))
        p.drawLine(QPointF(right + 1, c), QPointF(right - 3, c + 4))
        p.drawLine(QPointF(c + 1.5, c - 5), QPointF(c - 1.5, c + 5))
    p.end()
    return QIcon(pix)


# --- Segmented Tabs (4 fixed pills, sliding active indicator, no scroll) ---

class SegmentedTabs(QWidget):
    """Four equal tabs with a caramel pill that slides to the active one.

    Same navigation API as the QListWidget it replaced
    (setCurrentRow / currentChanged) so callers stay untouched.
    """

    currentChanged = Signal(int)

    def __init__(self, labels, icons=None, parent=None):
        super().__init__(parent)
        self.setObjectName("top-nav-list")
        self._labels = list(labels)
        self._icons = list(icons) if icons else [None] * len(labels)
        self._current = 0
        self._compact = False
        self._active_color = QColor("#211510")
        self._inactive_color = QColor("#C9B19C")
        self._anim = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(0)

        self._buttons = []
        for idx, text in enumerate(labels):
            btn = QPushButton(text)
            btn.setObjectName("nav-tab")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda _checked=False, i=idx: self.setCurrentRow(i))
            lay.addWidget(btn)
            self._buttons.append(btn)
        self._buttons[0].setChecked(True)

        self._indicator = QWidget(self)
        self._indicator.setObjectName("nav-indicator")
        self._indicator.lower()

    def count(self) -> int:
        return len(self._buttons)

    def currentRow(self) -> int:
        return self._current

    def setCurrentRow(self, row: int):
        row = max(0, min(row, len(self._buttons) - 1))
        if row == self._current:
            self._snap_indicator()
            return
        self._current = row
        for i, btn in enumerate(self._buttons):
            btn.blockSignals(True)
            btn.setChecked(i == row)
            btn.blockSignals(False)
        self._refresh_tabs()
        self._animate_indicator()
        self.currentChanged.emit(row)

    def set_compact(self, compact: bool):
        """Icon-only pills when True, text pills when False."""
        if compact != self._compact:
            self._compact = compact
            self._refresh_tabs()

    def set_colors(self, active: QColor, inactive: QColor):
        """Icon tones: active sits on the caramel pill, inactive on the bar."""
        self._active_color = active
        self._inactive_color = inactive
        self._refresh_tabs()

    def _refresh_tabs(self):
        for i, btn in enumerate(self._buttons):
            kind = self._icons[i] if i < len(self._icons) else None
            if self._compact and kind:
                btn.setText("")
                color = self._active_color if i == self._current else self._inactive_color
                btn.setIcon(paint_tab_icon(kind, color))
                btn.setToolTip(self._labels[i])
            else:
                btn.setText(self._labels[i])
                btn.setIcon(QIcon())
                btn.setToolTip("")

    def _indicator_rect(self) -> "QRect":
        from PySide6.QtCore import QRect
        btn = self._buttons[self._current]
        return QRect(btn.x(), 4, btn.width(), max(0, self.height() - 8))

    def _snap_indicator(self):
        if self._anim is not None:
            self._anim.stop()
        self._indicator.setGeometry(self._indicator_rect())

    def _animate_indicator(self):
        # Tabs are equal-width by construction, so only the position ever
        # changes — animating `pos` (never `geometry`) avoids stretch jank.
        if self._anim is not None:
            self._anim.stop()
        target = self._indicator_rect()
        self._indicator.resize(target.width(), target.height())
        self._anim = QPropertyAnimation(self._indicator, b"pos", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(self._indicator.pos())
        self._anim.setEndValue(target.topLeft())
        self._anim.start()

    def showEvent(self, event):
        super().showEvent(event)
        self._snap_indicator()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._snap_indicator()


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

    def __init__(self, mac_address=DEFAULT_MAC):
        super().__init__()
        self.mac_address = mac_address
        self.loop = None
        self.device = None
        self._running = True
        self.trace_mode = False
        self._retry_count = 0
        self._connect_event = None  # created once the event loop exists
        self._auto_connect = True  # connect once on startup without a click

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
        if self._auto_connect:
            # Fresh launch: try the remembered device immediately so the app
            # shows live data instead of waiting for a click.
            self._connect_event.set()

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
    def set_auto_connect(self, enable: bool):
        """Connect once on worker startup (True) or wait for a click (False)."""
        self._auto_connect = enable

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

    def save_gestures(self, gestures):
        """Write an edited gesture map back to the buds, then re-read it."""
        if self.device and self.loop:
            async def _task():
                try:
                    await self.device.set_gestures(gestures)
                    updated = await self.device.get_gestures()
                    self.gestures_updated.emit(updated)
                except Exception as e:
                    logger.error(f"Error saving gestures: {e}")
                    self.error_occurred.emit(f"Failed to save gestures: {e}")
            asyncio.run_coroutine_threadsafe(_task(), self.loop)

    def set_anc_mode(self, mode: str):
        """ANC via the worker so failures surface in the UI, not the void."""
        if self.device and self.loop:
            async def _task():
                try:
                    await self.device.set_anc_mode(mode)
                except Exception as e:
                    logger.error(f"Error setting ANC mode: {e}")
                    self.error_occurred.emit(f"Failed to set ANC mode: {e}")
            asyncio.run_coroutine_threadsafe(_task(), self.loop)


# --- Stylesheets ---

DARK_STYLESHEET = """
    QWidget {
        font-family: 'DejaVu Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    QMainWindow {
        background-color: #211510;
    }
    QWidget#top-header-widget {
        background-color: #2B1B14;
        border-bottom: 1px solid rgba(243, 231, 214, 0.08);
    }
    QWidget#top-nav-list {
        background-color: #33231A;
        border: 1px solid rgba(243, 231, 214, 0.12);
        border-radius: 18px;
    }
    QPushButton#nav-tab {
        background: transparent;
        border: none;
        border-radius: 13px;
        padding: 5px 6px;
        color: #C9B19C;
        font-size: 11px;
        font-weight: 600;
    }
    QPushButton#nav-tab:checked {
        font-weight: 700;
        color: #211510;
    }
    QPushButton#nav-tab:hover:!checked {
        color: #F3E7D6;
    }
    QWidget#nav-indicator {
        background-color: #D9A441;
        border: 1px solid #D9A441;
        border-radius: 13px;
    }
    QFrame#card {
        background-color: #33231A;
        border: 1px solid rgba(243, 231, 214, 0.09);
        border-radius: 14px;
    }
    QLabel {
        color: #F3E7D6;
    }
    QLabel#section-title {
        font-size: 12px;
        font-weight: 700;
        color: #F3E7D6;
        letter-spacing: 0.2px;
    }
    QLabel#section-subtitle {
        font-size: 11px;
        color: #C9B19C;
    }
    QComboBox {
        background-color: #3A261D;
        border: 1px solid rgba(243, 231, 214, 0.14);
        border-radius: 8px;
        padding: 5px 10px;
        color: #F3E7D6;
        font-size: 11px;
        font-weight: 500;
    }
    QComboBox:hover {
        border: 1px solid rgba(217, 164, 65, 0.6);
        background-color: #453022;
    }
    QComboBox::drop-down {
        border: none;
        width: 18px;
    }
    QComboBox QAbstractItemView {
        background-color: #33231A;
        color: #F3E7D6;
        selection-background-color: rgba(217, 164, 65, 0.25);
        selection-color: #E8B85C;
        border: 1px solid rgba(243, 231, 214, 0.14);
        border-radius: 8px;
        padding: 4px;
    }
    QCheckBox {
        spacing: 10px;
        color: #F3E7D6;
        font-weight: 500;
    }
    QCheckBox::indicator {
        width: 17px;
        height: 17px;
        border: 1px solid rgba(243, 231, 214, 0.22);
        border-radius: 5px;
        background-color: #3A261D;
    }
    QCheckBox::indicator:hover {
        border: 1px solid #D9A441;
    }
    QCheckBox::indicator:checked {
        background-color: #D9A441;
        border: 1px solid #D9A441;
    }
    QPushButton {
        background-color: #3A261D;
        border: 1px solid rgba(243, 231, 214, 0.12);
        border-radius: 8px;
        padding: 6px 14px;
        color: #F3E7D6;
        font-weight: 600;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #4A3123;
        border: 1px solid rgba(217, 164, 65, 0.5);
    }
    QPushButton:pressed {
        background-color: #2B1B14;
    }
    QPushButton:checked {
        background-color: #D9A441;
        color: #211510;
        font-weight: 700;
        border: 1px solid #D9A441;
    }
    QPushButton:disabled {
        background-color: rgba(58, 38, 29, 0.5);
        color: #8B6A55;
        border: 1px solid rgba(243, 231, 214, 0.05);
    }
    QPushButton#primary-btn {
        background-color: #D9A441;
        color: #211510;
        border: 1px solid #D9A441;
        font-weight: 700;
    }
    QPushButton#primary-btn:hover {
        background-color: #E8B85C;
        border: 1px solid #E8B85C;
    }
    QPushButton#danger-btn {
        background-color: #C0564B;
        border: 1px solid #C0564B;
        color: #FFF6EC;
    }
    QProgressBar {
        border: 1px solid rgba(243, 231, 214, 0.1);
        border-radius: 5px;
        text-align: center;
        background-color: #211510;
        color: #F3E7D6;
        font-size: 9px;
        height: 12px;
    }
    QProgressBar::chunk {
        background-color: #D9A441;
        border-radius: 4px;
    }
    QSlider::groove:horizontal {
        border: none;
        height: 6px;
        background: #3A261D;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #D9A441;
        border: 2px solid #211510;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #E8B85C;
    }
    QTextEdit {
        background-color: #211510;
        border: 1px solid rgba(243, 231, 214, 0.1);
        color: #D9A441;
        font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
        font-size: 11px;
        border-radius: 10px;
        padding: 8px;
    }
    QScrollArea#gesture-scroll {
        border: 1px solid rgba(243, 231, 214, 0.08);
        background-color: #2B1B14;
        border-radius: 12px;
    }
    QWidget#gesture-content {
        background: transparent;
    }
    /* Modern Slim Faded Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 7px;
        margin: 4px 2px 4px 2px;
    }
    QScrollBar::handle:vertical {
        background: rgba(217, 164, 65, 0.25);
        min-height: 24px;
        border-radius: 3px;
    }
    QScrollBar::handle:vertical:hover {
        background: rgba(217, 164, 65, 0.5);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QScrollBar:horizontal {
        border: none;
        background: transparent;
        height: 7px;
        margin: 2px 4px 2px 4px;
    }
    QScrollBar::handle:horizontal {
        background: rgba(217, 164, 65, 0.25);
        min-width: 24px;
        border-radius: 3px;
    }
    QScrollBar::handle:horizontal:hover {
        background: rgba(217, 164, 65, 0.5);
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
        background: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }
"""

LIGHT_STYLESHEET = """
    QWidget {
        font-family: 'DejaVu Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    QMainWindow {
        background-color: #F6F1E7;
    }
    QWidget#top-header-widget {
        background-color: #FFFDF8;
        border-bottom: 1px solid #E3D5C0;
    }
    QWidget#top-nav-list {
        background-color: #EFE4D2;
        border: 1px solid #D9C6A9;
        border-radius: 18px;
    }
    QPushButton#nav-tab {
        background: transparent;
        border: none;
        border-radius: 13px;
        padding: 5px 6px;
        color: #8B6A55;
        font-size: 11px;
        font-weight: 600;
    }
    QPushButton#nav-tab:checked {
        font-weight: 700;
        color: #FFFDF8;
    }
    QPushButton#nav-tab:hover:!checked {
        color: #3A241D;
    }
    QWidget#nav-indicator {
        background-color: #A96B1F;
        border: 1px solid #A96B1F;
        border-radius: 13px;
    }
    QFrame#card {
        background-color: #FFFDF8;
        border: 1px solid #E3D5C0;
        border-radius: 14px;
    }
    QLabel {
        color: #3A241D;
    }
    QLabel#section-title {
        font-size: 12px;
        font-weight: 700;
        color: #3A241D;
        letter-spacing: 0.2px;
    }
    QLabel#section-subtitle {
        font-size: 11px;
        color: #8B6A55;
    }
    QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #D9C6A9;
        border-radius: 8px;
        padding: 5px 10px;
        color: #3A241D;
        font-size: 11px;
        font-weight: 500;
    }
    QComboBox:hover {
        border: 1px solid #A96B1F;
        background-color: #FFFDF8;
    }
    QComboBox::drop-down {
        border: none;
        width: 18px;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFDF8;
        color: #3A241D;
        selection-background-color: rgba(169, 107, 31, 0.14);
        selection-color: #A96B1F;
        border: 1px solid #E3D5C0;
        border-radius: 8px;
        padding: 4px;
    }
    QCheckBox {
        spacing: 10px;
        color: #3A241D;
        font-weight: 500;
    }
    QCheckBox::indicator {
        width: 17px;
        height: 17px;
        border: 1px solid #D9C6A9;
        border-radius: 5px;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:hover {
        border: 1px solid #A96B1F;
    }
    QCheckBox::indicator:checked {
        background-color: #A96B1F;
        border: 1px solid #A96B1F;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D9C6A9;
        border-radius: 8px;
        padding: 6px 14px;
        color: #3A241D;
        font-weight: 600;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #F6F1E7;
        border: 1px solid #A96B1F;
    }
    QPushButton:pressed {
        background-color: #EFE4D2;
    }
    QPushButton:checked {
        background-color: #A96B1F;
        color: #FFFDF8;
        font-weight: 700;
        border: 1px solid #A96B1F;
    }
    QPushButton:disabled {
        background-color: #F6F1E7;
        color: #B8947B;
        border: 1px solid #EFE4D2;
    }
    QPushButton#primary-btn {
        background-color: #A96B1F;
        color: #FFFDF8;
        border: 1px solid #A96B1F;
        font-weight: 700;
    }
    QPushButton#primary-btn:hover {
        background-color: #8F5A19;
        border: 1px solid #8F5A19;
    }
    QPushButton#danger-btn {
        background-color: #C0564B;
        border: 1px solid #C0564B;
        color: #FFF6EC;
    }
    QProgressBar {
        border: 1px solid #E3D5C0;
        border-radius: 5px;
        text-align: center;
        background-color: #EFE4D2;
        color: #3A241D;
        font-size: 9px;
        height: 12px;
    }
    QProgressBar::chunk {
        background-color: #A96B1F;
        border-radius: 4px;
    }
    QSlider::groove:horizontal {
        border: none;
        height: 6px;
        background: #EFE4D2;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #A96B1F;
        border: 2px solid #FFFDF8;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #8F5A19;
    }
    QTextEdit {
        background-color: #FFFDF8;
        border: 1px solid #E3D5C0;
        color: #A96B1F;
        font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
        font-size: 11px;
        border-radius: 10px;
        padding: 8px;
    }
    QScrollArea#gesture-scroll {
        border: 1px solid #E3D5C0;
        background-color: #F6F1E7;
        border-radius: 12px;
    }
    QWidget#gesture-content {
        background: transparent;
    }
    /* Modern Slim Faded Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 7px;
        margin: 4px 2px 4px 2px;
    }
    QScrollBar::handle:vertical {
        background: rgba(169, 107, 31, 0.25);
        min-height: 24px;
        border-radius: 3px;
    }
    QScrollBar::handle:vertical:hover {
        background: rgba(169, 107, 31, 0.5);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QScrollBar:horizontal {
        border: none;
        background: transparent;
        height: 7px;
        margin: 2px 4px 2px 4px;
    }
    QScrollBar::handle:horizontal {
        background: rgba(169, 107, 31, 0.25);
        min-width: 24px;
        border-radius: 3px;
    }
    QScrollBar::handle:horizontal:hover {
        background: rgba(169, 107, 31, 0.5);
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
        background: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }
"""


# --- Main UI Window ---

class MainWindow(QMainWindow):
    def __init__(self, mac_address=None, auto_connect=True):
        super().__init__()
        # MAC priority: explicit arg (--mac) > remembered QSettings > fallback.
        self.settings = QSettings(ORG_NAME, APP_NAME)
        remembered_mac = str(self.settings.value("device/mac", DEFAULT_MAC))
        self.mac_address = mac_address or remembered_mac
        if self.mac_address != remembered_mac:
            self.settings.setValue("device/mac", self.mac_address)
        self.is_connected = False
        # Always launch dark; the Settings toggle is per-session only.
        self.theme_mode = "dark"
        self._auto_connect = auto_connect
        self._quit_requested = False
        self._tray_notice_shown = bool(self.settings.value("ui/tray_notice_shown", False))
        self._gestures = []  # last confirmed TouchGesture list from the buds

        self.setWindowTitle("OPPO Linux Companion")
        self.setMinimumSize(360, 480)
        self.resize(820, 560)

        # Main Layout (Vertical: Top Header Bar + Page Stack)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Header Navigation Bar
        top_header_widget = QWidget()
        top_header_widget.setObjectName("top-header-widget")
        top_header_layout = QHBoxLayout(top_header_widget)
        top_header_layout.setContentsMargins(16, 8, 16, 8)
        top_header_layout.setSpacing(12)

        self.app_title_label = QLabel("OPPO Companion")
        self.app_title_label.setFont(QFont("DejaVu Sans", 11, QFont.Bold))
        top_header_layout.addWidget(self.app_title_label)

        top_header_layout.addStretch()

        self.sidebar = SegmentedTabs(
            ["Dashboard", "Gestures", "Settings", "Developer Tools"],
            icons=["dashboard", "gestures", "settings", "dev"],
        )
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentChanged.connect(self._on_navigation_changed)
        self.sidebar.setFixedHeight(36)
        top_header_layout.addWidget(self.sidebar)

        top_header_layout.addStretch()

        # Status & Connection Controls (Right)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(4)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #C0564B; font-size: 13px;")
        status_layout.addWidget(self.status_dot)
        self.status_lbl = QLabel("Offline")
        self.status_lbl.setStyleSheet("color: #8B6A55; font-size: 10px;")
        status_layout.addWidget(self.status_lbl)
        top_header_layout.addLayout(status_layout)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(84)
        self.connect_btn.clicked.connect(self._on_connect_button_clicked)
        top_header_layout.addWidget(self.connect_btn)

        main_layout.addWidget(top_header_widget)

        # 2. Page Stack — centered column so wide screens don't stretch
        # cards edge to edge; side stretches collapse on narrow screens.
        body = QWidget()
        self._body_layout = QHBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        self._body_layout.addStretch(0)
        self.stacked_pages = QStackedWidget()
        self._body_layout.addWidget(self.stacked_pages, 1)
        self._body_layout.addStretch(0)
        main_layout.addWidget(body)

        # Initialize state-tracking for verified non-optimistic updates
        self._confirmed_eq = 0
        self._confirmed_game_mode = False
        self._confirmed_volume = 50

        # Page layouts for responsive margin tweaks (collected after init).
        self._page_layouts = []

        # Initialize pages
        self._init_dashboard_page()
        self._init_gestures_page()
        self._init_settings_page()
        self._init_dev_page()
        self._page_layouts = [
            self.stacked_pages.widget(i).layout()
            for i in range(self.stacked_pages.count())
        ]

        # Disable telemetry controls by default until connection
        self._set_controls_enabled(False)

        # Apply remembered theme (also persists it back to settings)
        self.apply_theme(self.theme_mode)

        # Restore window geometry from last session
        geometry = self.settings.value("ui/geometry")
        if geometry is not None:
            try:
                self.restoreGeometry(geometry)
            except Exception:
                pass

        # Initialize Worker Thread
        self.worker = OppoDeviceWorker(self.mac_address)
        self.worker.set_auto_connect(self._auto_connect)
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

        self._setup_tray()

        self.worker.start()

    # --- System Tray (residency: close hides, quit is explicit) ---

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        icon = QIcon.fromTheme("audio-headset")
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("OPPO Companion — Offline")

        menu = QMenu(self)
        self.tray_show_action = QAction("Show", self)
        self.tray_show_action.triggered.connect(self._on_tray_show)
        menu.addAction(self.tray_show_action)
        self.tray_conn_action = QAction("Connect", self)
        self.tray_conn_action.triggered.connect(self._on_connect_button_clicked)
        menu.addAction(self.tray_conn_action)
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_tray_quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._on_tray_show()

    def _on_tray_quit(self):
        self._quit_requested = True
        self.close()

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

        # Two-column body: battery visual left, controls right on wide
        # screens; stacked vertically on narrow ones (see _apply_layout_mode).
        self._dash_body = QBoxLayout(QBoxLayout.TopToBottom)
        self._dash_body.setSpacing(12)
        self._dash_left = QWidget()
        left_lay = QVBoxLayout(self._dash_left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        self._dash_right = QWidget()
        right_lay = QVBoxLayout(self._dash_right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        # Right column scrolls when controls overflow; left visual stays fixed.
        self.dash_scroll = QScrollArea()
        self.dash_scroll.setFrameShape(QFrame.NoFrame)
        self.dash_scroll.setWidgetResizable(True)
        self.dash_scroll.viewport().setAutoFillBackground(False)
        self.dash_scroll_content = QWidget()
        self.dash_scroll_content.setObjectName("gesture-content")
        self.dash_scroll_lay = QVBoxLayout(self.dash_scroll_content)
        self.dash_scroll_lay.setContentsMargins(0, 0, 0, 0)
        self.dash_scroll_lay.setSpacing(12)
        self.dash_scroll.setWidget(self.dash_scroll_content)
        right_lay.addWidget(self.dash_scroll)
        self._dash_body.addWidget(self._dash_left)
        self._dash_body.addWidget(self._dash_right)
        layout.addLayout(self._dash_body)

        # Silhouettes Display Card
        sil_card = QFrame()
        sil_card.setObjectName("card")
        sil_layout = QHBoxLayout(sil_card)
        sil_layout.setContentsMargins(10, 80, 10, 80)

        # Left Column
        left_layout = QVBoxLayout()
        self.left_silhouette = SilhouetteWidget("left")
        self.left_silhouette.setMinimumSize(104, 132)
        left_layout.addWidget(self.left_silhouette, 0, Qt.AlignCenter)
        
        left_batt_row = QHBoxLayout()
        left_batt_row.setSpacing(4)
        left_batt_row.setAlignment(Qt.AlignCenter)
        self.left_bolt_lbl = QLabel("⚡")
        self.left_bolt_lbl.setStyleSheet("color: #7FB069; font-size: 11px; font-weight: bold;")
        self.left_bolt_lbl.setVisible(False)
        left_batt_row.addWidget(self.left_bolt_lbl)
        
        self.left_battery_widget = BatteryWidget(scale=1.5)
        left_batt_row.addWidget(self.left_battery_widget)
        
        self.left_battery_lbl = QLabel("--%")
        self.left_battery_lbl.setFont(QFont("DejaVu Sans", 12, QFont.Bold))
        left_batt_row.addWidget(self.left_battery_lbl)
        left_layout.addLayout(left_batt_row)
        
        left_label = QLabel("Left")
        left_label.setObjectName("section-subtitle")
        left_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_label)
        left_layout.addStretch(1)
        sil_layout.addLayout(left_layout)

        # Right Column
        right_layout = QVBoxLayout()
        self.right_silhouette = SilhouetteWidget("right")
        self.right_silhouette.setMinimumSize(104, 132)
        right_layout.addWidget(self.right_silhouette, 0, Qt.AlignCenter)
        
        right_batt_row = QHBoxLayout()
        right_batt_row.setSpacing(4)
        right_batt_row.setAlignment(Qt.AlignCenter)
        self.right_bolt_lbl = QLabel("⚡")
        self.right_bolt_lbl.setStyleSheet("color: #7FB069; font-size: 11px; font-weight: bold;")
        self.right_bolt_lbl.setVisible(False)
        right_batt_row.addWidget(self.right_bolt_lbl)
        
        self.right_battery_widget = BatteryWidget(scale=1.5)
        right_batt_row.addWidget(self.right_battery_widget)
        
        self.right_battery_lbl = QLabel("--%")
        self.right_battery_lbl.setFont(QFont("DejaVu Sans", 12, QFont.Bold))
        right_batt_row.addWidget(self.right_battery_lbl)
        right_layout.addLayout(right_batt_row)
        
        right_label = QLabel("Right")
        right_label.setObjectName("section-subtitle")
        right_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_label)
        right_layout.addStretch(1)
        sil_layout.addLayout(right_layout)

        # Case Column
        case_layout = QVBoxLayout()
        self.case_silhouette = SilhouetteWidget("case")
        self.case_silhouette.setMinimumSize(104, 132)
        case_layout.addWidget(self.case_silhouette, 0, Qt.AlignCenter)
        
        case_batt_row = QHBoxLayout()
        case_batt_row.setSpacing(4)
        case_batt_row.setAlignment(Qt.AlignCenter)
        self.case_bolt_lbl = QLabel("⚡")
        self.case_bolt_lbl.setStyleSheet("color: #7FB069; font-size: 11px; font-weight: bold;")
        self.case_bolt_lbl.setVisible(False)
        case_batt_row.addWidget(self.case_bolt_lbl)
        
        self.case_battery_widget = BatteryWidget(scale=1.5)
        case_batt_row.addWidget(self.case_battery_widget)
        
        self.case_battery_lbl = QLabel("--%")
        self.case_battery_lbl.setFont(QFont("DejaVu Sans", 12, QFont.Bold))
        case_batt_row.addWidget(self.case_battery_lbl)
        case_layout.addLayout(case_batt_row)
        
        case_label = QLabel("Case")
        case_label.setObjectName("section-subtitle")
        case_label.setAlignment(Qt.AlignCenter)
        case_layout.addWidget(case_label)
        case_layout.addStretch(1)
        sil_layout.addLayout(case_layout)

        left_lay.addWidget(sil_card)
        left_lay.addStretch(1)

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
        self.dash_scroll_lay.addWidget(self.anc_card)

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
        self.dash_scroll_lay.addWidget(self.eq_card)

        # Game Mode Card
        self.gm_card = QFrame()
        self.gm_card.setObjectName("card")
        gm_layout = QHBoxLayout(self.gm_card)
        gm_layout.setContentsMargins(12, 12, 12, 12)

        self.game_mode_cb = QCheckBox("Low-Latency Game Mode")
        self.game_mode_cb.setFont(QFont("DejaVu Sans", 10))
        self.game_mode_cb.stateChanged.connect(self._on_game_mode_ui_changed)
        gm_layout.addWidget(self.game_mode_cb)
        self.dash_scroll_lay.addWidget(self.gm_card)

        # Alert Sound Volume (moved here from Settings so all sound
        # controls live on the dashboard).
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
        self.vol_value_lbl.setStyleSheet("color: #8B6A55;")
        vol_header.addWidget(self.vol_value_lbl)
        vol_layout.addLayout(vol_header)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(10, 100)
        self.vol_slider.setValue(10)
        self.vol_slider.valueChanged.connect(self._on_volume_slider_changed)
        self.vol_slider.sliderReleased.connect(self._on_volume_slider_released)
        vol_layout.addWidget(self.vol_slider)
        self.dash_scroll_lay.addWidget(self.vol_card)
        self.dash_scroll_lay.addStretch(1)

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
        self.btn_apply_gestures = QPushButton("Apply to Buds")
        self.btn_apply_gestures.setObjectName("primary-btn")
        self.btn_apply_gestures.setToolTip("Write the edited mapping below back to the earbuds")
        self.btn_apply_gestures.clicked.connect(self._on_apply_gestures)
        header.addWidget(self.btn_apply_gestures)
        self.btn_refresh_gestures = QPushButton("Refresh")
        self.btn_refresh_gestures.clicked.connect(self._refresh_gestures)
        header.addWidget(self.btn_refresh_gestures)
        layout.addLayout(header)

        hint = QLabel("Tap a function to remap it, then Apply to Buds. Refresh discards edits.")
        hint.setObjectName("section-subtitle")
        layout.addWidget(hint)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("gesture-scroll")
        self.scroll.setWidgetResizable(True)
        # Viewport would otherwise paint the platform default (white).
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("gesture-content")
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
        self.fw_version_lbl.setStyleSheet("color: #8B6A55;")
        fw_layout.addWidget(self.fw_version_lbl)
        layout.addWidget(fw_card)

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
            self.status_dot.setStyleSheet("color: #7FB069; font-size: 14px;")
            self.status_lbl.setText("Connected")
            self.status_lbl.setStyleSheet("color: #7FB069; font-size: 10px;")
            self.subtitle_label.setText(f"Connected · {self.mac_address}")
            self._set_controls_enabled(True)
            self.btn_refresh_gestures.setEnabled(True)
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            if hasattr(self, "tray") and self.tray is not None:
                self.tray_conn_action.setText("Disconnect")
                self.tray.setToolTip("OPPO Companion — Connected")
            self._refresh_gestures()
        elif state == "connecting":
            self.is_connected = False
            self.status_dot.setStyleSheet("color: #D9A441; font-size: 14px;")
            self.status_lbl.setText("Connecting...")
            self.status_lbl.setStyleSheet("color: #D9A441; font-size: 10px;")
            self.subtitle_label.setText("Connecting...")
            self._set_controls_enabled(False)
            self.btn_refresh_gestures.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
        elif state == "disconnected":
            # Auto-retry still in progress — no action needed from the user yet.
            self.is_connected = False
            self.status_dot.setStyleSheet("color: #D9A441; font-size: 14px;")
            self.status_lbl.setText("Reconnecting...")
            self.status_lbl.setStyleSheet("color: #D9A441; font-size: 10px;")
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
            self.status_dot.setStyleSheet("color: #C0564B; font-size: 14px;")
            self.status_lbl.setText("Offline")
            self.status_lbl.setStyleSheet("color: #8B6A55; font-size: 10px;")
            self.subtitle_label.setText("Offline")
            self._set_controls_enabled(False)
            self.btn_refresh_gestures.setEnabled(False)
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            if hasattr(self, "tray") and self.tray is not None:
                self.tray_conn_action.setText("Connect")
                self.tray.setToolTip("OPPO Companion — Offline")
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
        if hasattr(self, "tray") and self.tray is not None:
            try:
                self.tray.setToolTip(
                    f"OPPO Companion — L {int(battery.left)}% · "
                    f"R {int(battery.right)}%"
                )
            except Exception:
                pass
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
        self.status_lbl.setStyleSheet("color: #7FB069; font-size: 10px;")

    @Slot(bool)
    def _on_game_mode_received(self, enable: bool):
        self._confirmed_game_mode = enable
        self.game_mode_cb.blockSignals(True)
        self.game_mode_cb.setChecked(enable)
        self.game_mode_cb.blockSignals(False)
        self.game_mode_cb.setEnabled(True)
        self.status_lbl.setText("Connected")
        self.status_lbl.setStyleSheet("color: #7FB069; font-size: 10px;")

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
        self.status_lbl.setStyleSheet("color: #7FB069; font-size: 10px;")

    @Slot(list)
    def _on_gestures_received(self, gestures: list):
        self._gestures = list(gestures)
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not gestures:
            lbl = QLabel("No gesture configurations mapped.")
            lbl.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(lbl)
            return

        func_ids = sorted(GESTURE_FUNCTIONS.keys())
        for row_idx, gesture in enumerate(gestures):
            row = QFrame()
            row.setObjectName("card")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 4, 10, 4)

            ear = "Left" if gesture.earbud_id == 1 else "Right"
            trig = TRIGGER_NAMES.get(gesture.trigger_id, f"Trig-{gesture.trigger_id}")
            lbl = QLabel(f"{ear} · {trig}")
            lbl.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
            lbl.setStyleSheet("border: none; background: transparent;")
            row_layout.addWidget(lbl)
            row_layout.addStretch()

            combo = QComboBox()
            for fid in func_ids:
                combo.addItem(GESTURE_FUNCTIONS[fid], fid)
            try:
                combo.setCurrentIndex(func_ids.index(gesture.function_id))
            except ValueError:
                combo.addItem(f"Unknown ({hex(gesture.function_id)})", gesture.function_id)
                combo.setCurrentIndex(combo.count() - 1)
            combo.setProperty("gesture_index", row_idx)
            combo.currentIndexChanged.connect(self._on_gesture_combo_changed)
            row_layout.addWidget(combo)

            self.scroll_layout.addWidget(row)

    def _on_gesture_combo_changed(self, _idx: int):
        """Stage an edit locally; nothing touches the buds until Apply."""
        combo = self.sender()
        if combo is None:
            return
        row_idx = combo.property("gesture_index")
        if row_idx is None or row_idx >= len(self._gestures):
            return
        self._gestures[row_idx].function_id = combo.currentData()

    def _on_apply_gestures(self):
        if self.is_connected and self._gestures:
            self.status_lbl.setText("Applying...")
            self.status_lbl.setStyleSheet(f"color: {COFFEE['warn']}; font-size: 10px;")
            self.btn_apply_gestures.setEnabled(False)
            self.worker.save_gestures(list(self._gestures))

    @Slot(str, str, str)
    def _on_packet_traced(self, direction: str, raw_hex: str, desc: str):
        ts = time.strftime('%H:%M:%S')
        line = f"[{ts}] {direction} ➔ {raw_hex} | {desc}\n"
        self.console.append(line)

    @Slot(str)
    def _on_worker_error(self, err_msg: str):
        logger.error(f"Worker Error: {err_msg}")
        self.status_lbl.setText("Apply Failed")
        self.status_lbl.setStyleSheet("color: #C0564B; font-size: 10px;")
        
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

    # --- Responsive breakpoints: mobile / floating / laptop / fullscreen ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout_mode()

    def _apply_layout_mode(self):
        # Side spacers stay weightless (stretch 0): the column takes
        # everything up to its cap; spacers only absorb leftover width.
        w = self.width()
        if w < 560:
            # Mobile: compact everything, header keeps dot + Connect only.
            margins, maxw = 8, 16777215
            self.app_title_label.setVisible(False)
            self.status_lbl.setVisible(False)
            self._dash_body.setDirection(QBoxLayout.TopToBottom)
        elif w < 860:
            # Floating/small window: comfortable default, stacked cards.
            margins, maxw = 12, 16777215
            self.app_title_label.setVisible(True)
            self.status_lbl.setVisible(True)
            self._dash_body.setDirection(QBoxLayout.TopToBottom)
        elif w < 1240:
            # Laptop: breathing room, capped column, still stacked.
            margins, maxw = 14, 1000
            self.app_title_label.setVisible(True)
            self.status_lbl.setVisible(True)
            self._dash_body.setDirection(QBoxLayout.TopToBottom)
        else:
            # Fullscreen: wide canvas — battery left, controls right.
            margins, maxw = 18, 1400
            self.app_title_label.setVisible(True)
            self.status_lbl.setVisible(True)
            self._dash_body.setDirection(QBoxLayout.LeftToRight)
            self._dash_body.setStretch(0, 3)
            self._dash_body.setStretch(1, 2)
        # Icon pills take over at 60% of the laptop breakpoint (740px):
        # tab text starts clipping long before the mobile layout kicks in.
        self.sidebar.set_compact(w < 740)
        for lay in self._page_layouts:
            if lay is not None:
                lay.setContentsMargins(margins, margins, margins, margins)
        self.stacked_pages.setMaximumWidth(maxw)
        self._body_layout.setStretch(0, 0)
        self._body_layout.setStretch(2, 0)

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
            self.status_lbl.setStyleSheet("color: #D9A441; font-size: 10px;")
            self.eq_dropdown.setEnabled(False)
            self.worker.change_eq(idx)

    def _on_game_mode_ui_changed(self, state: int):
        if self.is_connected:
            # stateChanged emits an int; Qt.Checked is a CheckState enum in
            # PySide6, so comparing them directly always evaluates False.
            enable = state == Qt.Checked.value
            self.status_lbl.setText("Applying...")
            self.status_lbl.setStyleSheet("color: #D9A441; font-size: 10px;")
            self.game_mode_cb.setEnabled(False)
            self.worker.toggle_game_mode(enable)

    def _on_anc_changed(self, btn, checked):
        if checked and self.is_connected:
            self.worker.set_anc_mode(btn.text().lower())

    def _on_volume_slider_changed(self, val: int):
        self.vol_value_lbl.setText(f"{val}%")

    def _on_volume_slider_released(self):
        if self.is_connected:
            val = self.vol_slider.value()
            self.status_lbl.setText("Applying...")
            self.status_lbl.setStyleSheet("color: #D9A441; font-size: 10px;")
            self.vol_slider.setEnabled(False)
            self.worker.change_volume(val)

    def _on_ring_toggled(self, checked):
        if self.is_connected:
            self.worker.trigger_ring(checked)
            if checked:
                self.btn_ring.setText("Stop Ringing")
                self.btn_ring.setStyleSheet("""
                    QPushButton {
                        background-color: #C0564B;
                        border: 1px solid #C0564B;
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
        self.btn_apply_gestures.setEnabled(enable)

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
            self.sidebar.set_colors(QColor("#FFFDF8"), QColor("#6B4A3A"))
            self.theme_dropdown.blockSignals(True)
            self.theme_dropdown.setCurrentIndex(1)
            self.theme_dropdown.blockSignals(False)
        else:
            self.setStyleSheet(DARK_STYLESHEET)
            self.sidebar.set_colors(QColor("#211510"), QColor("#C9B19C"))
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
            self.left_silhouette.set_theme(mode)
        if hasattr(self, 'right_silhouette'):
            self.right_silhouette.set_theme(mode)
        if hasattr(self, 'case_silhouette'):
            self.case_silhouette.set_theme(mode)

    def closeEvent(self, event):
        self.settings.setValue("ui/geometry", self.saveGeometry())
        # Tray residency: X hides to tray (once explained), Quit is explicit.
        if (
            hasattr(self, "tray") and self.tray is not None
            and self.tray.isVisible() and not self._quit_requested
        ):
            event.ignore()
            self.hide()
            if not self._tray_notice_shown:
                self._tray_notice_shown = True
                self.settings.setValue("ui/tray_notice_shown", True)
                self.tray.showMessage(
                    "OPPO Companion",
                    "Still running in the tray. Right-click the icon to Quit.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
            return
        self.worker.stop()
        self.worker.wait()
        event.accept()


# --- CLI / Main Entry ---

def main(argv=None):
    import argparse
    from PySide6.QtCore import QLocale
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

    parser = argparse.ArgumentParser(description="OPPO Enco Buds Linux companion")
    parser.add_argument("--mac", default=None,
                        help="Buds Bluetooth MAC (defaults to remembered device)")
    parser.add_argument("--no-auto-connect", action="store_true",
                        help="Wait for the Connect button instead of connecting on launch")
    args = parser.parse_args(argv)

    app = QApplication(sys.argv if argv is None else [sys.argv[0]])
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName("OPPO Companion")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(mac_address=args.mac, auto_connect=not args.no_auto_connect)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
