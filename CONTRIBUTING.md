# Contributing Guide: OPPO Linux Companion

Thank you for contributing to the OPPO Linux Companion project! This document outlines guidelines for contributing code, testing changes, and recording protocol logs.

---

## 1. Local Development Setup

To initialize a development sandbox:

```bash
# Clone and enter repo
git clone https://github.com/your-username/oppo-control.git
cd oppo-control

# Create virtualenv and install with dev dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

---

## 2. Code Structure Guidelines

Keep the architecture separated:
*   **Transport Layer:** Sockets and raw reads/writes (`transport.py`).
*   **Protocol Layer:** Framing, checksums, and stream feeding (`protocol.py`).
*   **Codecs:** Parsing and encoding logic for individual features (`codecs.py`).
*   **Device Profiles:** Capabilities mapping and metadata (`devices.py`).
*   **Main Interface:** The high-level API wrapper (`device.py`).

---

## 3. Running Unit Tests

We use `pytest` for unit testing. The test suite includes offline protocol roundtrip checks and headless GUI capability visibility checks:

```bash
# Run all tests
pytest tests/

# Run specific tests with verbose logs
pytest tests/ -v
```

---

## 4. Contributing Protocol Logs (Oplogs)

If you own a model not currently marked as **Verified** in the compatibility matrix:
1.  Connect to your earbuds using `oppoctl`.
2.  Record a session trace:
    ```bash
    oppoctl record my_model.oplog
    ```
3.  Exercise touch actions, toggle Game Mode, or change EQ presets.
4.  Submit the resulting `my_model.oplog` log file in an issue or PR to expand the auto-detection and capability profiles!
