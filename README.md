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
OPPO-Earbuds/
├── AGENTS.md                    # DOX work contracts
├── CHANGELOG.md
├── INSTALL.md
├── README.md
├── REVERSE_ENGINEERING.md
├── pyproject.toml               # Build-system configuration (PEP 517/518)
├── requirements.txt
├── install.sh                   # One-shot user-space installer (no root)
├── oppogui.desktop              # Desktop launcher template
├── docs/                        # Specifications and lab notes
│   ├── PROTOCOL.md              # Master OPO v1 RFCOMM specification
│   ├── GATT_PROFILE.md
│   ├── PROTOCOL_NOTES.md
│   ├── OPPO_PODS_COMPARE.md
│   └── PROJECT_STATUS.md
├── captures/                    # Ground-truth binary captures
├── examples/                    # Minimal API usage examples
├── scripts/                     # Logging, survey, and validation utilities
├── tests/                       # Offline automated test suite
│   ├── test_protocol.py
│   ├── test_gui.py
│   ├── test_cli.py
│   ├── test_device.py
│   └── run_tests.py
├── Old/                         # Superseded mockups and reference screenshots
└── src/
    ├── gui/                     # GUI package initializer
    ├── models/                  # Telemetry model package initializer
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
git clone https://github.com/Swastik36/OPPO-Earbuds.git
cd OPPO-Earbuds

# Create an isolated environment and install in editable mode
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
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

# Update Equalizer DSP profiles
# (original, bass, treble, vocal, bass_boost, treble_boost)
oppoctl eq bass_boost

# Acoustic control on supported hardware (on, off, transparency)
oppoctl anc on

# Toggle Low-Latency Game Mode (on, off)
oppoctl gamemode on

# Dump capacitive Touch Gestures configuration matrix
oppoctl gestures

# Remap one gesture record, verify the read-back, and report ignored writes
oppoctl gesture left basic single play_pause
oppoctl gesture right basic double next
oppoctl gesture left basic long volume_up
oppoctl gesture left custom double game_mode_toggle

# Preview a remap without writing
oppoctl gesture left basic single none --dry-run

# Query or set the alert prompt tone volume (0-100)
oppoctl volume 80

# Ring the earbuds to locate them (start, stop)
oppoctl find start

# Record a live session to a log, or replay a recorded one
oppoctl record session.log
oppoctl replay session.log
```

### Specifying Target MAC Address
By default, `oppoctl` targets the hardware address `60:55:56:22:49:A0`. You can override this using the `--mac` flag:
```bash
oppoctl --mac 00:11:22:33:44:55 battery
```

### Gesture Arguments
`oppoctl gesture` takes four positional arguments:
`ear` (`left`/`right`), `action` (`basic`/`custom`), `trigger`
(`single`/`double`/`triple`/`long`/`double_hold`/`slide`), and `function`
(`none`/`play_pause`/`voice_assistant`/`voice_assistant_alt`/`previous`/`next`/`volume_down`/`volume_up`/`game_mode`/`game_mode_toggle`/`game_mode_toggle_alt`).

The command writes one 4-byte record (like HeyMelody), re-reads the matrix,
and exits nonzero if the buds acknowledge but ignore the mapping. Some
trigger/function pairs are read-only on the Buds3 Pro firmware.

---

## 6. Desktop Companion (`oppogui`)

Launch **OPPO Companion** from your application menu, or run `oppogui` directly.

| Tab | What it does |
| :--- | :--- |
| **Dashboard** | Live battery for both buds and the case, equalizer preset, low-latency game mode, alert sound volume, and an acoustic-control card (shown only for hardware that supports it) |
| **Gestures** | Read the 24-record touch-gesture matrix, remap any Basic/Custom trigger, and **Apply to Buds**; writes only changed records and verifies the read-back |
| **Settings** | Firmware version, find-my-earbuds ring, and app theme |
| **Developer Tools** | Raw packet trace console and system-level Bluetooth link controls |

Behaviour worth knowing:
- **Auto-connects** to the last used earbuds on launch; use `oppogui --no-auto-connect` to start disconnected.
- **Tray residency** — closing the window hides it to the system tray (battery level in the tooltip). Quit from the tray menu. On a desktop without a tray host, closing the window exits instead.
- **Responsive layout** — the window adapts from mobile-sized single column to a two-column dashboard on wide screens; below 740px the tab bar switches to icons.
- **Theme is per-session** — the app always launches dark; the Settings toggle applies until you quit.
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

