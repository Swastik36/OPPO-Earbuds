# Purpose

This directory contains the core application source code for the OPPO Enco Buds3 Pro Linux companion, including the `oppo_control` library package, PySide6 desktop GUI views, and telemetry models.

# Ownership

- Owner: Core Python Developers / Reverse Engineers
- Scope: All application logic, RFCOMM communication drivers, GUI widgets, CLI commands, and data models

# Local Contracts

- All Python code must be written for Python 3.10+ and include type hints (`typing`).
- Core protocol logic must remain completely decoupled from PySide6 GUI views to enable standalone headless CLI usage via `oppoctl`.
- System exceptions must inherit from custom exceptions defined in [exceptions.py](oppo_control/exceptions.py).

# Work Guidance

- Refer to the individual child directories for package-specific contracts.

# Verification

- Verify that all Python modules compile and pass syntax checks with `python3 -m py_compile src/oppo_control/*.py`.
- Run pytest suite with `pytest tests/`.

# Child DOX Index

- [oppo_control](oppo_control/AGENTS.md): Asynchronous RFCOMM transport, OPO v1 protocol parser, command definitions, device controller API, and `oppoctl` CLI.
- [gui](gui/AGENTS.md): PySide6 desktop GUI behavior contracts; the `oppogui` entrypoint lives in `oppo_control/gui.py`.
- [models](models/AGENTS.md): Device telemetry data models, battery schemas, and state objects.
