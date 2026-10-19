# Purpose

This directory contains the automated test suite powered by `pytest` for verifying RFCOMM protocol framing, header checks, CRC checksum calculation, battery payload decoders, and PySide6 GUI components.

# Ownership

- Owner: Test & Quality Assurance Engineers
- Scope: Automated pytest test cases, mock transport fixtures, protocol trace logs, and GUI testing

# Local Contracts

- All unit tests must be capable of running completely offline without requiring physical Bluetooth hardware (use mock socket transports and captured binary payloads).
- Test cases must assert correct behavior for edge cases, including corrupted CRC bytes, truncated packets, and unrecognized register codes.

# Work Guidance

- Execute the full test suite before committing changes to core library or GUI files.

# Verification

- Run `pytest tests/` or `python3 tests/run_tests.py`.

# Child DOX Index

- [test_protocol.py](test_protocol.py): RFCOMM frame assembly, header verification, checksum test suite, and touch-gesture matrix parsing (24-record hardware payload).
- [test_gui.py](test_gui.py): PySide6 GUI behavior tests (state machine, gesture Apply lifecycle, breakpoints).
- [test_cli.py](test_cli.py): CLI argument-to-enum mapping checks.
- [test_device.py](test_device.py): Device capability checks, including ANC rejection.
- [run_tests.py](run_tests.py): Custom standalone test runner script.
