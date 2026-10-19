# OPPO Enco Buds3 Pro Linux Companion

![Linux Compatible](https://img.shields.io/badge/OS-Linux-blue?logo=linux)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Protocol](https://img.shields.io/badge/Protocol-OPO%20v1%20RFCOMM-orange)
![License](https://img.shields.io/badge/License-GPLv3-green)

An open-source Linux implementation library, Qt6 Desktop GUI, and CLI driver for **OPPO Enco Buds3 Pro** (and OPO v1 protocol earbuds).

> **Keywords / Tags**: `oppo-telemetry-control` • `earbud-control` • `heymelody-linux` • `oppo-enco-buds3-pro` • `tws-control` • `bluetooth-rfcomm` • `bluez` • `pyside6-gui`

Built on top of the reverse-engineered **RFCOMM DLCI 30 (Server Channel 15)** Bluetooth Classic protocol.

---

## 1. Directory Structure

```text
oppo-control/
├── pyproject.toml               # Build-system configuration (PEP 517/518)
├── README.md                    # Technical installation manual
├── install.sh                   # One-shot user-space installer (no root)
├── oppogui.desktop              # Desktop launcher template
├── docs/                        # Specifications and lab notes
│   ├── PROTOCOL.md              # Master OPO v1 RFCOMM specification
│   ├── GATT_PROFILE.md
│   ├── PROTOCOL_NOTES.md
│   ├── OPPO_PODS_COMPARE.md
│   └── PROJECT_STATUS.md
├── captures/                    # Ground-truth binary captures
│   └── README.md
├── examples/                    # Minimal API usage examples
├── tests/                       # Offline automated test suite
│   ├── test_protocol.py
│   └── test_gui.py
├── Old/                         # Superseded mockups and reference screenshots
└── src/
    └── oppo_control/
        ├── __init__.py
        ├── transport.py         # Async Linux RFCOMM socket wrapper
        ├── protocol.py          # Frame assembly and parsing engine
        ├── commands.py          # Command registers, enums, and decoders
        ├── codecs.py            # Binary/ASCII payload decoders
        ├── devices.py           # Hardware capability profiles
        ├── device.py            # High-level asynchronous API class
        ├── bluetooth_control.py # BlueZ link control helpers
        ├── cli.py               # Command-line interface driver
        ├── gui.py               # PySide6 desktop application
        └── exceptions.py        # System-wide custom exception definitions
```

---

## 2. Fast 1-Line Installation (For End Users)

Install automatically and register `OPPO Companion` directly in your **Linux Application / Start Menu**:

```bash
curl -fsSL https://raw.githubusercontent.com/Swastik36/OPPO-Earbuds/main/install.sh | bash
```

Or run locally:
```bash
chmod +x ./install.sh && ./install.sh
```

The installer is user-space only: it creates an isolated virtualenv, symlinks `oppoctl` and `oppogui` into `~/.local/bin`, and registers the **OPPO Companion** launcher in your application menu. No root required.

---

## 3. Developer / Manual Setup

If you wish to work on the codebase in editable mode:

```bash
# Clone and enter the repository
cd OPPO-Earbuds

# Install in editable mode with development dependencies
./.venv/bin/pip install -e .[dev]
```

---

## 4. Running Tests

Verify the protocol framing, equalizer codecs, battery decoders, and GUI instantiation offline:

```bash
./.venv/bin/pytest tests/
```

---

## 5. Command-Line Utility (`oppoctl`)

The CLI utility `oppoctl` is automatically registered in your environment path upon installation.

### Usage:
```bash
# Query hardware specifications & firmware
oppoctl info

# Query real-time battery status
oppoctl battery

# Update Equalizer DSP profiles (original, bass_boost, clear_vocals)
oppoctl eq bass_boost

# Toggle Low-Latency Game Mode (on, off)
oppoctl gamemode on

# Dump capacitive Touch Gestures configuration matrix
oppoctl gestures

# Query or set the alert prompt tone volume (0-100)
oppoctl volume 80

# Ring the earbuds to locate them
oppoctl find on

# Record a live session to a log, or replay a recorded one
oppoctl record session.log
oppoctl replay session.log
```

### Specifying Target MAC Address
By default, `oppoctl` targets the hardware address `60:55:56:22:49:A0`. You can override this using the `--mac` flag:
```bash
oppoctl --mac 00:11:22:33:44:55 battery
```

---

## 6. Desktop Companion (`oppogui`)

Launch **OPPO Companion** from your application menu, or run `oppogui` directly.

| Tab | What it does |
| :--- | :--- |
| **Dashboard** | Live battery for both buds and the case, equalizer preset, low-latency game mode, alert sound volume, and an acoustic-control card (shown only for hardware that supports it) |
| **Gestures** | Read the touch-gesture matrix from the buds, remap any trigger, and **Apply to Buds** to write the new mapping back |
| **Settings** | Firmware version, find-my-earbuds ring, and app theme |
| **Developer Tools** | Raw packet trace console and system-level Bluetooth link controls |

Behaviour worth knowing:
- **Auto-connects** to the last used earbuds on launch; use `oppogui --no-auto-connect` to start disconnected.
- **Tray residency** — closing the window hides it to the system tray (battery level in the tooltip). Quit from the tray menu.
- **Responsive layout** — the window adapts from mobile-sized single column to a two-column dashboard on wide screens; below 740px the tab bar switches to icons.
- Target a different device with `oppogui --mac 00:11:22:33:44:55`.

---

## 7. Python API Usage

Exposes a clean asynchronous API that handles sockets, packet streams, transaction matching, and pushes.

```python
import asyncio
from oppo_control import OppoDevice, EQPreset

async def main():
    # Connect using context manager
    async with OppoDevice(mac_address="60:55:56:22:49:A0") as device:
        # Get battery levels
        battery = await device.get_battery()
        print(f"Left: {battery.left}% [Charging={battery.left.is_charging}]")
        
        # Enable Game Mode
        await device.set_game_mode(True)
        
        # Set EQ preset
        await device.set_eq(EQPreset.BASS)

        # Register callback for pushes (e.g. EQ changed directly on buds)
        def on_push(event, data):
            print(f"Push Notification: {event} -> {data}")
        device.register_callback(on_push)
        
        # Keep alive briefly to listen
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8. Acknowledgements & Inspiration

Special thanks and recognition to:
* **[Aasheesh](https://aasheesh.vercel.app/)**: Author of the pioneering reverse engineering analysis on OnePlus/OPPO TWS earbuds protocols. His research and writeups provided vital insights into the OPO protocol framing and architecture.

---

## 9. Search Tags & Discoverability

`oppo-telemetry-control` • `earbud-control` • `oppo-enco-buds3-pro` • `heymelody-linux` • `heymelody-alternative` • `oppo-earbuds-linux` • `oneplus-buds-linux` • `realme-buds-linux` • `tws-telemetry` • `bluetooth-rfcomm-channel-15` • `bluez-oppo-driver` • `pyside6-oppo-gui`

