# Purpose

This directory contains telemetry models, device state dataclasses, battery status schemas, and EQ preset objects for OPPO Bluetooth TWS devices.

# Ownership

- Owner: Data Schema / Model Engineers
- Scope: Telemetry dataclasses, state schemas, and device model definitions

# Local Contracts

- Data models must use Python `@dataclass` or Pydantic definitions with explicit type hints.
- Battery level structures must safely support missing/offline earbud states (e.g. left earbud disconnected, case in standby).

# Verification

- Validate model instantiation in unit tests.

# Child DOX Index

- [__init__.py](file:///home/swastik/new-project/oppo%20gui/src/models/__init__.py): Models package initializer.
