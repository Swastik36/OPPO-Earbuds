# Purpose

This directory contains developer utility scripts for real-time Bluetooth packet logging, protocol validation, notification tracing, and hardware survey diagnostics.

# Ownership

- Owner: Developer Tooling / Automation Maintainers
- Scope: Packet logging scripts, protocol validation utilities, notification loggers, and device discovery tools

# Local Contracts

- All utility scripts must handle CLI parameters flexibly using `argparse` (`--mac`, `--port`, `--verbose`).
- Diagnostic scripts must log errors to stdout/stderr without corrupting captured binary outputs.

# Work Guidance

- Use [packet_logger.py](file:///home/swastik/new-project/oppo%20gui/scripts/packet_logger.py) for capturing live RFCOMM traffic during protocol analysis.

# Verification

- Verify script argument handling by running each script with `--help`.

# Child DOX Index

- [packet_logger.py](file:///home/swastik/new-project/oppo%20gui/scripts/packet_logger.py): Real-time Bluetooth RFCOMM packet logging tool.
- [survey.py](file:///home/swastik/new-project/oppo%20gui/scripts/survey.py): Bluetooth device capability discovery utility.
- [validate_oppo_protocol.py](file:///home/swastik/new-project/oppo%20gui/scripts/validate_oppo_protocol.py): Offline protocol validation script.
- [notify_logger.py](file:///home/swastik/new-project/oppo%20gui/scripts/notify_logger.py): Notification and telemetry capture logger.
- [demo_oppo_control.py](file:///home/swastik/new-project/oppo%20gui/scripts/demo_oppo_control.py): Demonstration entrypoint for device library.
