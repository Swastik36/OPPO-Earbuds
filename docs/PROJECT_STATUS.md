# OPPO Enco Buds3 Pro Linux Companion

## Current Project Status

### Objective
Develop a fully open-source Linux companion application for the **OPPO Enco Buds3 Pro** that replicates the core functionality of the Android **HeyMelody** app.

Target features:
* Battery levels (Left / Right / Case)
* ANC controls
* Transparency mode
* EQ presets
* Touch gesture configuration
* Firmware information
* Device information
* Earbud locator (if supported)
* Automatic device detection

---

# Development Philosophy
The project will be developed in layers instead of immediately creating a GUI:
```
Hardware
        ↓
Bluetooth (BLE)
        ↓
Reverse-engineered protocol
        ↓
Python library
        ↓
GUI
```
The GUI is intentionally the last step.

---

# Device Information

* **Device:** OPPO Enco Buds3 Pro
* **Bluetooth Address:** `60:55:56:22:49:A0`
* **Bluetooth Device ID:** `bluetooth:v02B0p0000d001F`
  * Vendor ID: `0x02B0` (OPPO)
  * Product: `0x0000`
  * Device Version: `0x001F`
* **Bluetooth Class:** `0x240404`

---

# Services Identified

### Standard Services
* `00001800` Generic Access
* `00001801` Generic Attribute
* `00001000` Service Discovery
* `0000110B Audio Sink
* `0000110C` AVRCP Target
* `0000110E` AVRCP Controller
* `0000110F` Video Conferencing
* `0000111E` Handsfree
* `00001200` PnP Information
* `00001203` Generic Audio

### Proprietary Services
* `0000079A`
* `0000079C`
* `01000100`
* `df21fe2c`
* `99999999`

These proprietary services almost certainly contain ANC controls, battery information, touch configuration, EQ settings, firmware communication, and other vendor-specific features.

---

# Linux Compatibility

### Working
* Bluetooth pairing
* Audio playback
* Microphone
* Automatic reconnection
* Standard Bluetooth profiles
* Battery reporting through UPower
  * Verified: `upower -e` returns `/org/freedesktop/UPower/devices/headset_dev_60_55_56_22_49_A0`
  * Battery information can be queried using `upower -i /org/freedesktop/UPower/devices/headset_dev_60_55_56_22_49_A0`

---

# Current Limitation
Linux currently has **no official support** for:
* ANC
* Transparency
* Equalizer
* Touch controls
* Firmware updates

*Reason:* OPPO has never documented the proprietary BLE protocol used by these features.

---

# Planned Architecture
```
encobuds-linux/
├── docs/
│   ├── PROJECT_STATUS.md
│   └── GATT_PROFILE.md
├── output/
│   └── (Saved scans and raw GATT output)
├── scripts/
│   ├── survey.py
│   ├── notify_logger.py
│   └── packet_logger.py
├── src/
│   ├── bluetooth/
│   │   ├── scanner.py
│   │   ├── transport.py
│   │   ├── protocol.py
│   │   ├── commands.py
│   │   └── battery.py
│   ├── models/
│   │   └── enco_buds3_pro.py
│   ├── gui/
│   │   └── main_window.py
│   └── app.py
└── tests/
```

---

# Planned Development Stages

## Stage 1: Device Discovery
* **Goal:** Produce a complete GATT map.
* **Deliverables:** Services, Characteristics, Descriptors, Handles, Properties, Initial values.
* **Status:** Completed. Fully mapped all services and characteristics, including the Custom Data Path and Google Fast Pair channels, and successfully resolved initial values.

## Stage 2: Protocol Reverse Engineering
* **Goal:** Discover proprietary commands.
* **Method:** Observe BLE/RFCOMM communication while using Android (e.g. Wireshark/btsnoop).
* **Expected Output:** Command-to-meaning mapping (e.g., `0101` -> ANC ON).
* **Status:** Completed. Discovered custom RFCOMM DLCI 30 protocol with Sync byte `0xAA`. Decoded and mapped command payloads for EQ Preset changes (Original, Bass Boost, Clear Vocals) and Game Mode (ON/OFF).

## Stage 2.5: Protocol Validation
* **Goal:** Verify that Linux can establish RFCOMM sockets and validate packet replay/decoding.
* **Status:** Completed. Confirmed RFCOMM port 15 (DLCI 30) is listening, validated read queries (Battery, version, EQ), and successfully set EQ preset (Bass Boost, Original) and Game Mode (ON/OFF), capturing asynchronous telemetry notifications.

## Stage 3: Python Library
* **Goal:** Create a reusable API.
* **Status:** Completed. Implemented a decoupled asynchronous Python package `oppo_control` containing native RFCOMM transport, packet stream framing, and command codecs.

## Stage 3.5: Hardening, Verification & Specification
* **Goal:** Audit protocol specifications, check open-source implementations, build offline tests, and create a power-user CLI.
* **Status:** Completed. 
  * Validated our custom protocol definitions against `OppoPods` and `BudsLink` repositories, discovering a critical binary/ASCII telemetry format swap between generations.
  * Implemented dual-format universal decoders for battery and firmware tracking.
  * Mapped touch gesture write commands (`0x0401`), Find My Device alerts (`0x0400`), and prompt tone volumes (`0x0130`/`0x0427`).
  * Created an offline automated test suite (`tests/test_protocol.py`) and a production CLI driver (`oppoctl`). All tests passed successfully.

## Stage 4: GUI
* **Preferred Toolkit:** PySide6 (Qt)
* **Status:** Not started. Replicate the glassmorphic `earbuds_connect_popup_v3.html` template.

## Stage 5: Packaging
* **Potential Formats:** pip, Flatpak, AppImage.

