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

- [test_protocol.py](file:///home/swastik/new-project/oppo%20gui/tests/test_protocol.py): RFCOMM frame assembly, header verification, and checksum test suite.
- [test_gui.py](file:///home/swastik/new-project/oppo%20gui/tests/test_gui.py): PySide6 GUI component instantiation test suite.
- [run_tests.py](file:///home/swastik/new-project/oppo%20gui/tests/run_tests.py): Custom standalone test runner script.
