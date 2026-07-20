# Installation Guide: OPPO Linux Companion

This guide walks you through setting up system dependencies and installing the `oppo-control` Python library, CLI, and GUI connector.

---

## 1. System Pre-requisites

The application relies on Linux Bluetooth Classic RFCOMM communication:

### A. Install Bluetooth System Utilities
Ensure the Bluetooth stack (`bluez`) and development headers are installed on your Linux distribution:

*   **Debian/Ubuntu/Pop!_OS:**
    ```bash
    sudo apt update
    sudo apt install bluez bluez-tools python3-dev python3-pip
    ```
*   **Fedora/RHEL:**
    ```bash
    sudo dnf install bluez python3-devel python3-pip
    ```
*   **Arch Linux:**
    ```bash
    sudo pacman -S bluez bluez-utils python-pip
    ```

### B. Start Bluetooth Daemon
Verify that the Bluetooth service is running on your host:
```bash
sudo systemctl enable --now bluetooth
```

---

## 2. Virtual Environment Installation

It is recommended to install the package within a local Python virtual environment to isolate dependencies:

1.  **Clone the Repository & Initialize Environment:**
    ```bash
    git clone https://github.com/your-username/oppo-control.git
    cd oppo-control
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install the Package:**
    *   **User/Production Install:**
        ```bash
        pip install .
        ```
    *   **Developer Editable Install:**
        ```bash
        pip install -e .
        ```

This registers the binary shortcuts `oppoctl` and `oppogui` inside your virtual environment's binary path.

---

## 3. Desktop Application Shortcut Integration

To register the graphical utility in your desktop menu (so it can be launched via GNOME Shell or KDE Application launcher):

```bash
cp oppogui.desktop ~/.local/share/applications/
```

This binds the launcher to the virtual environment binary path (`/home/swastik/new-project/oppo gui/.venv/bin/oppogui`). If your virtual environment is located elsewhere, edit the `Exec=` path inside `~/.local/share/applications/oppogui.desktop` accordingly.
