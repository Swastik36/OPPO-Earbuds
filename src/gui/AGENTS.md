# Purpose

This directory contains the PySide6 Desktop GUI application views, custom widgets, system tray integrations, and visual layout components for the OPPO Enco Buds3 Pro companion.

# Ownership

- Owner: Desktop App / UI Developers
- Scope: PySide6 (Qt6 for Python) visual widgets, theme engines, earbud status cards, and tray notifications

# Local Contracts

- Desktop interface must be built using PySide6 (Qt6 for Python).
- Background Bluetooth RFCOMM operations must not block the main Qt event loop; execute async socket queries via background worker threads (`QThread` / `asyncio`).
- Custom styling must respect Linux system dark/light theme preferences and match the glassmorphic card design.

# Work Guidance

- Refer to [gui.py](file:///home/swastik/new-project/oppo%20gui/src/oppo_control/gui.py) for the main window entrypoint and widget layout integration.

# Verification

- Verify GUI window instantiation offline via `pytest tests/test_gui.py`.

# Child DOX Index

- [__init__.py](file:///home/swastik/new-project/oppo%20gui/src/gui/__init__.py): GUI package initializer.
