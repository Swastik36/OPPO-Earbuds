# Changelog: OPPO Linux Companion

All notable changes to this project are documented in this file.

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
