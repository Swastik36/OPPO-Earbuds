# Purpose

This directory contains the PySide6 Desktop GUI application views, custom widgets, system tray integrations, and visual layout components for the OPPO Enco Buds3 Pro companion.

# Ownership

- Owner: Desktop App / UI Developers
- Scope: PySide6 (Qt6 for Python) visual widgets, theme engines, earbud status cards, and tray notifications

# Local Contracts

- Desktop interface must be built using PySide6 (Qt6 for Python).
- Background Bluetooth RFCOMM operations must not block the main Qt event loop; execute async socket queries via background worker threads (`QThread` / `asyncio`).
- Custom styling uses the coffee palette (Espresso dark / Latte light, caramel accent) in both themes; semantic colors only for status (ok/warn/err).
- Bud/case silhouettes always paint cream-white in every theme.
- App always launches dark; the Settings theme toggle is per-session only (not persisted).
- No Bluetooth MAC is hardcoded: `--mac` flag wins, then the QSettings-remembered device, then the fallback constant.
- The app auto-connects on launch to the remembered device; `--no-auto-connect` restores click-to-connect.
- Gesture mapping is editable (per-gesture function dropdown + Apply writes via `device.set_gestures()`); nothing is sent until Apply.
- Window closes to the system tray (one-time notice); Quit is explicit via the tray menu. No tray on headless/offscreen.
- Navigation is a 4-tab SegmentedTabs bar (Dashboard / Gestures / Settings / Developer Tools): fixed equal tabs, no scroll, caramel pill slides via 220ms QPropertyAnimation. API: setCurrentRow / currentChanged.
- Below 740px (60% of the laptop breakpoint) the tabs go icon-only: hand-drawn 1.8px vector line icons (grid, touch-ripple, gear, code brackets via `paint_tab_icon`), two-tone per theme, text moves to tooltips.
- Pill animates `pos` only (equal tabs never change size) — no stretch jank.
- Fullscreen 1240+ uses a two-column dashboard (battery visual left 3:2 controls right) capped at 1400; narrower modes stack vertically. Column contents are top-pinned with stretches.
- Gesture scroll viewport is transparent (`gesture-content`); rows never paint platform white.
- Battery bands: 0-20 warm red, 21-89 caramel, 90-100 leaf green.
- Responsive breakpoints on window width: mobile <560 (8px margins, title + status text hidden), floating 560-860 (12px), laptop 860-1240 (14px, capped 1000 column), fullscreen 1240+ (18px, capped 1400, two-column dashboard).
- Window geometry and device MAC persist via QSettings (`Swastik36/OPPOCompanion`).
- Dashboard is a fixed left visual (enlarged silhouettes + battery, never scrolls) plus a right control column (EQ, game mode, alert volume) inside a borderless scroll area; alert volume lives here, not in Settings.
- Fullscreen 1240+ uses a two-column dashboard (battery visual left 3:2 controls right) capped at 1400; narrower modes stack vertically. Column contents are top-pinned with stretches. Center-column side spacers stay weightless so wide screens never squeeze the content.

# Work Guidance

- Refer to [gui.py](../oppo_control/gui.py) for the main window entrypoint and widget layout integration.
- Gesture function IDs must stay in sync with the func map in `../oppo_control/commands.py`.

# Verification

- Verify GUI window instantiation offline via `pytest tests/test_gui.py` (uses `auto_connect=False`).
- Verify offscreen rendering via `QT_QPA_PLATFORM=offscreen` grab smoke test.

# Child DOX Index

- [__init__.py](./__init__.py): GUI package initializer.
