# Purpose

This directory contains the primary `oppo_control` Python package handling asynchronous Linux RFCOMM socket communication, OPO v1 frame building/parsing, battery and EQ decoders, device management, and the `oppoctl` CLI utility.

# Ownership

- Owner: Core Protocol & Transport Developers
- Scope: Bluetooth RFCOMM transport, OPO v1 framing, command enums, device API class, codecs, and CLI driver

# Local Contracts

- [transport.py](transport.py): Must implement non-blocking asynchronous socket communication via `asyncio` using Linux RFCOMM sockets (`AF_BLUETOOTH`, `SOCK_STREAM`, `BTPROTO_RFCOMM`).
- [protocol.py](protocol.py): Handles OPO v1 header verification (`0xAA` sync byte), payload length, command ID extraction, and CRC/checksum calculation.
- [commands.py](commands.py): Register definitions for battery levels, EQ profiles (`original`, `bass`, `vocal`, `bass_boost`), ANC modes, low-latency game mode, and touch gestures.
- [device.py](device.py): High-level asynchronous `OppoDevice` class exposing convenient async methods (`get_battery()`, `set_eq()`, `set_game_mode()`).
- [cli.py](cli.py): Entrypoint for the `oppoctl` command-line utility.

# Work Guidance

- Socket communication must handle connection dropouts, timeouts, and missing Bluetooth devices gracefully without crashing.
- Keep protocol frame magic bytes and command constants centralized in `commands.py` and `protocol.py`.
- Touch-gesture responses are `[status][count][records]`: read the count at payload offset 1 and records from offset 2 (see [../docs/PROTOCOL_NOTES.md](../docs/PROTOCOL_NOTES.md)).
- Desktop behavior contracts live in [../gui/AGENTS.md](../gui/AGENTS.md); [gui.py](gui.py) is the `oppogui` entrypoint.

# Verification

- Run `pytest tests/test_protocol.py` to verify protocol frame assembly, parsing, and checksum calculation.
- Run `pytest tests/test_gui.py` to verify GUI state machine, gesture Apply lifecycle, and layout breakpoints.
- Test CLI commands via `python3 -m oppo_control.cli info --help`.

# Child DOX Index

- [transport.py](transport.py): Async Linux RFCOMM socket transport wrapper.
- [protocol.py](protocol.py): OPO v1 protocol frame assembly, header verification, and checksum validation.
- [commands.py](commands.py): Register definitions, command IDs, and payload encoders/decoders.
- [device.py](device.py): High-level asynchronous `OppoDevice` API class.
- [cli.py](cli.py): Command-line driver utility (`oppoctl`).
- [gui.py](gui.py): Integrated desktop GUI entrypoint script.
- [codecs.py](codecs.py): Audio codec decoders and payload transformers.
- [devices.py](devices.py): Device configuration profiles and supported hardware definitions.
- [bluetooth_control.py](bluetooth_control.py): Low-level Bluetooth adapter control and pairing helpers.
- [exceptions.py](exceptions.py): Custom exception class definitions.
