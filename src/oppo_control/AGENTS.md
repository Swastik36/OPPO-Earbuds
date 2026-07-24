# Purpose

This directory contains the primary `oppo_control` Python package handling asynchronous Linux RFCOMM socket communication, OPO v1 frame building/parsing, battery and EQ decoders, device management, and the `oppoctl` CLI utility.

# Ownership

- Owner: Core Protocol & Transport Developers
- Scope: Bluetooth RFCOMM transport, OPO v1 framing, command enums, device API class, codecs, and CLI driver

# Local Contracts

- [transport.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/transport.py): Must implement non-blocking asynchronous socket communication via `asyncio` using Linux RFCOMM sockets (`AF_BLUETOOTH`, `SOCK_STREAM`, `BTPROTO_RFCOMM`).
- [protocol.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/protocol.py): Handles OPO v1 header verification (`0x55`), payload length, command ID extraction, and CRC/checksum calculation.
- [commands.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/commands.py): Register definitions for battery levels, EQ profiles (`original`, `bass_boost`, `clear_vocals`), ANC modes, low-latency game mode, and touch gestures.
- [device.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/device.py): High-level asynchronous `OppoDevice` class exposing convenient async methods (`get_battery()`, `set_eq()`, `set_game_mode()`).
- [cli.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/cli.py): Entrypoint for the `oppoctl` command-line utility.

# Work Guidance

- Socket communication must handle connection dropouts, timeouts, and missing Bluetooth devices gracefully without crashing.
- Keep protocol frame magic bytes and command constants centralized in `commands.py` and `protocol.py`.

# Verification

- Run `pytest tests/test_protocol.py` to verify protocol frame assembly, parsing, and checksum calculation.
- Test CLI commands via `python3 -m oppo_control.cli info --help`.

# Child DOX Index

- [transport.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/transport.py): Async Linux RFCOMM socket transport wrapper.
- [protocol.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/protocol.py): OPO v1 protocol frame assembly, header verification, and checksum validation.
- [commands.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/commands.py): Register definitions, command IDs, and payload encoders/decoders.
- [device.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/device.py): High-level asynchronous `OppoDevice` API class.
- [cli.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/cli.py): Command-line driver utility (`oppoctl`).
- [gui.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/gui.py): Integrated desktop GUI entrypoint script.
- [codecs.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/codecs.py): Audio codec decoders and payload transformers.
- [devices.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/devices.py): Device configuration profiles and supported hardware definitions.
- [bluetooth_control.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/bluetooth_control.py): Low-level Bluetooth adapter control and pairing helpers.
- [exceptions.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/exceptions.py): Custom exception class definitions.
