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
    git clone https://github.com/Swastik36/OPPO-Earbuds.git
    cd OPPO-Earbuds
    python3 -m venv .venv
    source .venv/bin/activate
    ```

    Alternatively, run `./install.sh` for a user-space install (virtualenv + `~/.local/bin` symlinks + menu entry) without creating one manually.

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
mkdir -p ~/.local/share/applications
sed "s|^Exec=.*|Exec=$PWD/.venv/bin/oppogui|" oppogui.desktop \
    > ~/.local/share/applications/oppogui.desktop
```

This points the launcher at the virtual environment's `oppogui` binary. If you used `./install.sh`, the installer already writes a correct entry pointing at `~/.local/bin/oppogui`, so this step is unnecessary.
