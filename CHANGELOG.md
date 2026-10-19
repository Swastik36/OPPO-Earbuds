# Changelog: OPPO Linux Companion

All notable changes to this project are documented in this file.

---

## [1.1.0] - 2026-10-19
Desktop companion overhaul.

### Added
*   **Coffee Theme:** Espresso dark / Latte light stylesheets replacing the previous GitHub-dark palette, with semantic status colours (battery bands: red → caramel → green at 90–100%).
*   **Sliding Tab Bar:** Four fixed tabs with a caramel pill that animates position only (no stretch), switching to hand-drawn vector icons below 740px.
*   **Editable Touch Gestures:** Every trigger can be remapped from the GUI and written back to the buds with **Apply to Buds** (read-back confirmed).
*   **System Tray Residency:** Closing the window hides it to the tray with a live battery tooltip; explicit Quit from the tray menu.
*   **Auto-Connect:** Connects to the last used earbuds on launch (`--no-auto-connect` to opt out); `--mac` overrides the target device.
*   **Responsive Layout:** Mobile → floating → laptop → fullscreen breakpoints, with a fixed visual panel and a scrolling control column, plus a centred column on wide screens.
*   **Alert Sound Volume** moved from Settings to the dashboard.

### Changed
*   Device MAC, window geometry, and theme are persisted through `QSettings`; the app always launches dark and the theme toggle is per-session.
*   `oppogui` now accepts `--mac` and `--no-auto-connect` instead of a bare positional MAC argument.

### Fixed
*   ANC requests on hardware without ANC no longer appear to succeed silently.
*   Removed duplicated mockup files from the repository root.

### Documentation
*   README rewritten: corrected installer URL and repository links, accurate directory map, full CLI command reference, and a new desktop-companion section.
*   `docs/PROJECT_STATUS.md` Stage 4/5 brought in line with the shipped application.

---

## [1.0.0] - 2026-07-18
Initial release of the `oppo-control` companion library and toolset.

### Added
*   **Layered Architecture:** Decoupled RFCOMM transport socket management, Varint stream framing, feature codecs, and capability-based device profiles.
*   **Dual-Format Decoders:** Universal ASCII and Binary decoders for battery telemetry and firmware information.
*   **Features:** Mapped controls for battery levels, EQ presets, Game Mode, Find My Device, touch panel gestures, and alert volume.
*   **Command Line Tool (`oppoctl`):** Interactive shell utility supporting queries, control writes, and `--trace` debugging modes.
*   **Session Oplogs:** Record and replay subcommands (`oppoctl record` / `replay`) to save, inspect, and parse binary socket data offline.
*   **Graphical Companion app (`oppogui`):** Modern PySide6 sidebar dashboard with vector silhouette battery widgets, connection state indicators, and developer trace consoles.
*   **System Integration:** Desktop launcher shortcut (`oppogui.desktop`) for GNOME Shell and KDE desktops.
*   **Verification Matrix:** Full experimental compatibility details (Verified vs. Implemented).
*   **Unit Tests:** Pytest tests covering protocol parser roundtrips and headless Qt capability-aware widget layouts.
