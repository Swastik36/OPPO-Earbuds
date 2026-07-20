# Reverse Engineering Report: OPPO Enco Buds 3 Pro (ETEK1) & OPO v1 Protocol

## Executive Summary

This document details the complete reverse engineering process, protocol specifications, technical hurdles, and software architecture behind the **OPPO Enco Buds 3 Pro (ETEK1)** Linux companion application (`oppo-control`).

Through packet inspection of Android BTSnoop HCI logs and empirical RFCOMM socket probing on Linux, we discovered that runtime telemetry, ANC, EQ, and touch controls do **not** run over BLE GATT attributes. Instead, OPPO devices utilize a custom binary protocol (**OPO v1**) over **Bluetooth Classic RFCOMM (Channel 15 / DLCI 30)**.

---

## 1. Environment & Target Diagnostic Setup

### Hardware & Operating Environment
* **Target Hardware**: OPPO Enco Buds 3 Pro (Model: `ETEK1`)
* **Host OS**: Linux Mint 22 (Ubuntu 24.04 LTS base, Linux Kernel 6.8+)
* **Bluetooth Stack**: BlueZ `5.72` (`bluetoothctl --version`)
* **Runtime**: Python `3.12+` with `PySide6` (Qt6), `dbus-python`, `dbus-next`, `bleak`, and `pytest`
* **Earbud Firmware**: Stock HeyMelody stream v1.x
* **Primary Analysis Tools**: Wireshark, BTSnoop HCI logs (`/var/lib/bluetooth`), `sdptool`, custom async RFCOMM socket probes

---

## 2. The Initial Misconception & The BLE-to-RFCOMM Pivot

### 2.1 The BLE GATT Trap
Initially, reverse engineering focused on Bluetooth Low Energy (BLE) GATT services under the assumption that modern TWS earbuds use BLE characteristics for app interaction. 

Scanning GATT services (`gatt_profile_*.md`, `gatt_survey_*.json`) revealed generic data pipe attributes (e.g., handles `0x000c`, `0x000e`). However, writing standard configuration values produced no state changes in ANC or EQ, and payload structures lacked identifiable battery or telemetry headers.

### 2.2 The Breakthrough Discovery
By capturing Android BTSnoop HCI logs while toggling settings in the official Android **HeyMelody** app, we traced the active traffic to **Bluetooth Classic RFCOMM Channel 15 (DLCI 30)**.

```
+-----------------------------------------------------------+
|                   HeyMelody Mobile App                    |
+-----------------------------------------------------------+
                              │
               Bluetooth Classic RFCOMM
                              │
                     Channel 15 / DLCI 30
                              │
               OPO v1 Binary Protocol (0xAA)
                              │
+-----------------------------------------------------------+
|              OPPO Enco Buds 3 Pro Hardware                |
+-----------------------------------------------------------+
```

> **Channel vs. DLCI Technical Note**: In Bluetooth RFCOMM multiplexing, the Data Link Connection Identifier (DLCI) is related to the server channel by $DLCI = Channel \times 2$. Thus, RFCOMM Channel 15 corresponds directly to DLCI 30 in lower-level HCI/RFCOMM frames.

---

## 3. OPO v1 Protocol Specification

The runtime protocol uses a consistent framing structure starting with a fixed magic byte (`0xAA`).

### 3.1 Frame Layout

```
 0       1       2       3       4       5       6        7...           N
+-------+-------+-------+-------+-------+-------+-------+---------------+-------+
| 0xAA  | Length| Session (H/L) | Group | CmdID |  Seq  | Payload...    | Check |
+-------+-------+-------+-------+-------+-------+-------+---------------+-------+
```

* **Header (`0xAA`)**: Start-of-Frame indicator.
* **Length Byte**: Total count of bytes following the length byte (excluding `0xAA` and `Length` itself).
* **Session ID (`2 bytes`)**: Session framing indicator (typically `0x00 0x00`).
* **Command Group (`1 byte`)**: Functional subsystem identifier.
* **Command ID (`1 byte`)**: Operation type.
* **Sequence Byte (`Seq`)**: Monotonically incrementing transaction ID echoing back in responses.
* **Payload**: Parameter bytes specific to the command group.

### 3.2 Command ID Semantics

| Command ID | Meaning | Description |
| :--- | :--- | :--- |
| `0x01` | Read Request | Queries state or settings from earbuds |
| `0x04` | Write Request | Sends control parameters (EQ, Game Mode, ANC) |
| `0x05` / `0x02` | Push / Telemetry | Unsolicited state updates (charging, placement) |
| `0x81` | Read Response | ACK / Data returned from a `0x01` read query |
| `0x84` | Write Response | ACK returned from a `0x04` write command |

---

## 4. Command Groups & Payload Decodes

### 4.1 Group `0x01` / `0x81`: Battery Telemetry Queries

#### ASCII CSV Query (`0x0105` - Legacy Fallback)
* **Request**: `AA 07 00 00 01 05 [Seq]`
* **Response (`0x8105`)**: ASCII CSV string where capacity $= \text{raw} - 28$.

#### Binary Query (`0x0106` / `0x8106` - Primary Standard)
* **Request**: `AA 07 00 00 01 06 [Seq]`
* **Response (`0x8106`)**: 3-byte payload `[Left_Raw] [Right_Raw] [Case_Raw]`.
* **Battery Level**: $\text{percentage} = \text{raw\_byte} \ \& \ 0x7F$.

### 4.2 Group `0x04`: Touch Gestures & Placement Telemetry

#### Placement Report (`Cmd 0x02`, Report Type `0x02`)
* **Payload Structure**: `02 02 01 [Left_Placement] 02 [Right_Placement]`
* **Values**: `01` = Out of Case, `00` = In Case.

#### Real-Time Charging Push (`Cmd 0x04`, Report Type `0x02`)
* **Payload Structure**: `01 03 01/02/03 [Charging_State]`
* **States**: `0x00` = Discharging, `0x01` = Charging, `0x02` = Full.

#### Touch Gesture Tap Events
* **Payload Prefix**: `F1 02 01 [Tap_Count]`
* **Tap Count**: `01` = Single-Tap, `02` = Double-Tap, `03` = Triple-Tap.
* **Live Volume Adjustments**: Incremental trailing bytes (e.g., `4200` $\rightarrow$ `4400`) tracking real-time volume change telemetry.

### 4.3 Group `0x06` / `0x0F`: Equalizer (Sound Master EQ)
* **Read Request (`Group 0x0F, Cmd 0x01`)**: `AA 08 00 00 0F 01 [Seq] 01 00 01`
* **Write Command (`Group 0x06, Cmd 0x04`)**: `AA 08 00 00 06 04 [Seq] 01 00 [Preset]`
* **Presets**:
  * `0x00`: Original (Balanced)
  * `0x01`: Clear Vocals
  * `0x02`: Bass Boost

### 4.4 Group `0x03` / `0x0D`: Low-Latency Game Mode
* **Read Request (`Group 0x0D, Cmd 0x01`)**: `AA 07 00 00 0D 01 [Seq]`
* **Write Command (`Group 0x03, Cmd 0x04`)**: `AA 08 00 00 03 04 [Seq] 01 00 [State]`
* **State**: `0x01` = Enabled (Low Latency), `0x00` = Disabled.

---

## 5. Key Technical Breakthroughs & Hardware Quirks

### 5.1 Case Charging Bit-7 Extraction
During battery testing, we observed that polled battery responses (`0x8106`) encode charging status in Bit 7 (`value & 0x80`). However:
* **Bit 7 ONLY fires for the Case (`ID=03`)**, turning `0x64` (100%) into `0xE4` when plugged into USB power.
* **Bit 7 NEVER fires for Left or Right earbud bytes in polled responses**. Earbud charging states are exclusively sent via unsolicited `0x0204` push notifications.
* **Resolution**: Updated `BatteryBinaryCodec` to extract Bit 7 only for Case, while `device.py` merges polled capacities with active earbud push states to prevent UI flickering.

### 5.2 Hardware Connection Resets (`Errno 104`)
Plugging the earbud case into USB power or closing the case lid causes the hardware to briefly power-cycle its Bluetooth radio, returning `Errno 104: Connection reset by peer`.
* **Diagnosis**: Identified as hardware/firmware behavior (shared power rail reset), not an application crash.
* **Resolution**: Built resilient `OppoDeviceWorker` reconnection logic paired with D-Bus system controls (`bluetooth_control.py`) to manage connection state transitions gracefully.

### 5.3 Sequence Matching & Concurrent Request Bottlenecks
Firing rapid query batches (firmware, EQ, game mode, battery) back-to-back caused sequence byte mismatches (`Seq 66, 67, 68...`) and request timeouts.
* **Resolution**: Enforced sequence-ID tracking and serialized command dispatches over the RFCOMM socket.

---

## 6. Software Architecture & GUI Engineering

The project was structured into a clean, modular Python package (`oppo-control`):

```
oppo-control/
├── .github/
│   └── workflows/ci.yml         # Automated GitHub Actions Pytest CI
├── src/
│   └── oppo_control/
│       ├── __init__.py
│       ├── assets.py            # Dynamic SVG vector graphics generator
│       ├── bluetooth_control.py # BlueZ D-Bus system disconnect/reconnect
│       ├── codecs.py            # Binary & ASCII frame parsers
│       ├── commands.py          # OPO v1 command encoders
│       ├── device.py            # Device state machine & capability profiles
│       ├── gui.py               # PySide6 Desktop GUI (HeyMelody theme)
│       └── packet_logger.py     # Packet inspection & tracing tools
├── tests/
│   └── test_gui.py              # Pytest automated test suite (17/17 pass)
├── pyproject.toml
└── README.md
```

### 6.1 HeyMelody Aesthetic & Vector SVG Engine
The Desktop GUI ([gui.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/gui.py)) mirrors the official HeyMelody design aesthetic:
* **Vector SVG Graphics ([assets.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/assets.py))**: Generates crisp, scale-free vector silhouettes rendered via PySide6 `QSvgRenderer`.
* **Inline Battery Badges**: Displays compact battery indicators (`L: 90% | R: 90% | Case: 100%`) directly below the main title header.
* **Hero Product Display**: Displays centered earbud and case artwork cleanly without layout overlap.
* **Scroll-Free Layout**: Optimized padding and spacing so all controls fit within standard window dimensions without scrollbars.

---

## 7. Verification & Release Status

* **Test Suite**: 17/17 automated unit tests passing (`.venv/bin/python -m pytest -q`).
* **CI/CD Pipeline**: GitHub Actions workflow enabled with Python 3.12 and pip caching.
* **Repository**: Hosted publicly on GitHub at [Swastik36/OPPO-Gui](https://github.com/Swastik36/OPPO-Gui).

---

## 8. Summary Timeline

```text
[Phase 1: GATT Discovery] ──> Scanned BLE GATT ──> Discovered no control attributes
                                       │
[Phase 2: RFCOMM Pivot]  ──> BTSnoop HCI trace ──> Identified RFCOMM Ch. 15 (DLCI 30) & 0xAA framing
                                       │
[Phase 3: Protocol Decodes]─> Decoded 0x0106 battery, 0x0604 EQ, 0x0304 Game Mode & 0x0402 gestures
                                       │
[Phase 4: Hardware Fixes]  ──> Handled Errno 104 BT reset, Case bit-7 charging & TWS Master/Slave sync
                                       │
[Phase 5: Desktop GUI]     ──> Built PySide6 App, SVG vector rendering & HeyMelody design system
```

---

## 9. Acknowledgements & Prior Art

Special thanks and technical credit to:
* **[Aasheesh](https://aasheesh.vercel.app/)**: For his foundational research, blog posts, and open reverse engineering work on OnePlus and OPPO TWS earbud protocols. His protocol teardowns provided key context for understanding the OPO framing structure and command layout.

