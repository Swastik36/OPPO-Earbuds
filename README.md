# OPPO Enco Buds3 Pro Linux Companion

An open-source Linux implementation library and Command-Line Interface (CLI) driver for the **OPPO Enco Buds3 Pro** earbuds.

Built on top of the reverse-engineered **RFCOMM DLCI 30 (Server Channel 15)** Bluetooth Classic protocol.

---

## 1. Directory Structure

```text
oppo-control/
├── pyproject.toml               # Build-system configuration (PEP 517/518)
├── README.md                    # Technical installation manual
├── docs/                        # Specifications and references
│   └── PROTOCOL.md
├── captures/                    # Ground-truth binary captures
│   └── README.md
├── tests/                       # Offline automated test suite
│   └── test_protocol.py
└── src/
    └── oppo_control/
        ├── __init__.py
        ├── transport.py         # Async Linux RFCOMM socket wrapper
        ├── protocol.py          # Frame assembly and parsing engine
        ├── commands.py          # Command registers, enums, and decoders
        ├── device.py            # High-level asynchronous API class
        ├── cli.py               # Command-line interface driver
        └── exceptions.py        # System-wide custom exception definitions
```

---

## 2. Installation

Install the package in editable mode within your virtual environment:

```bash
# Clone and enter the repository
cd "oppo gui"

# Install in editable mode with development dependencies
./.venv/bin/pip install -e .[dev]
```

---

## 3. Running Tests

Verify the protocol framing, equalizer codecs, and battery decoders offline:

```bash
./.venv/bin/pytest tests/
```

---

## 4. Command-Line Utility (`oppoctl`)

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
```

### Specifying Target MAC Address
By default, `oppoctl` targets the hardware address `60:55:56:22:49:A0`. You can override this using the `--mac` flag:
```bash
oppoctl --mac 00:11:22:33:44:55 battery
```

---

## 5. Python API Usage

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

## 6. Acknowledgements & Inspiration

Special thanks and recognition to:
* **[Aasheesh](https://aasheesh.vercel.app/)**: Author of the pioneering reverse engineering analysis on OnePlus/OPPO TWS earbuds protocols. His research and writeups provided vital insights into the OPO protocol framing and architecture.

