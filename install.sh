#!/usr/bin/env bash
set -eo pipefail

echo "===================================================="
echo " Installing OPPO Enco Buds3 Pro Linux Companion"
echo "===================================================="

# Target directories
INSTALL_DIR="$HOME/.local/share/oppo-control"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
FETCH_DIR=""

cleanup() {
    if [ -n "$FETCH_DIR" ] && [ -d "$FETCH_DIR" ]; then
        rm -rf "$FETCH_DIR"
    fi
}
trap cleanup EXIT

# Resolve the source tree. BASH_SOURCE is empty when this script is piped
# from curl, so fetch the repository tarball first in that case.
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [ -n "$SCRIPT_PATH" ] && [ -f "$SCRIPT_PATH" ]; then
    SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
else
    if ! command -v curl >/dev/null || ! command -v tar >/dev/null; then
        echo "Error: curl and tar are required for a piped install." >&2
        exit 1
    fi
    echo "[+] Fetching source from GitHub..."
    FETCH_DIR="$(mktemp -d)"
    curl -fsSL "https://github.com/Swastik36/OPPO-Earbuds/archive/refs/heads/main.tar.gz" \
        | tar -xz -C "$FETCH_DIR" --strip-components=1
    SCRIPT_DIR="$FETCH_DIR"
fi

# Check Python 3 availability
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed." >&2
    exit 1
fi

echo "[1/5] Creating installation directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"

echo "[2/5] Copying application files..."
tar -C "$SCRIPT_DIR" \
    --exclude=.git \
    --exclude=.venv \
    --exclude=__pycache__ \
    --exclude=.pytest_cache \
    --exclude='*.egg-info' \
    --exclude='*.pyc' \
    -cf - . | tar -C "$INSTALL_DIR" -xf -

echo "[3/5] Setting up isolated Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"

echo "[4/5] Installing package and dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR" -q

# Ensure libxcb-cursor is available for Qt 6.5+ XCB plugin
if ! ldconfig -p 2>/dev/null | grep -q "libxcb-cursor.so.0"; then
    if [ -f "$HOME/.local/lib/libxcb-cursor.so.0" ]; then
        cp "$HOME/.local/lib/libxcb-cursor.so"* "$INSTALL_DIR/.venv/lib/python"*/site-packages/PySide6/Qt/lib/ 2>/dev/null || true
    fi
fi

echo "[5/5] Creating executable symlinks and desktop launcher..."
ln -sf "$INSTALL_DIR/.venv/bin/oppoctl" "$BIN_DIR/oppoctl"
ln -sf "$INSTALL_DIR/.venv/bin/oppogui" "$BIN_DIR/oppogui"

# Install .desktop entry
cat <<EOF > "$APP_DIR/oppogui.desktop"
[Desktop Entry]
Type=Application
Name=OPPO Companion
GenericName=Earbud Control & Telemetry
Comment=Linux companion application for OPPO Enco Buds3 Pro earbuds
Exec=$BIN_DIR/oppogui
Icon=audio-headphones
Terminal=false
Categories=AudioVideo;Audio;Settings;HardwareSettings;
Keywords=oppo;enco;earbuds;heymelody;bluetooth;telemetry;
EOF

chmod +x "$APP_DIR/oppogui.desktop"

echo ""
echo "===================================================="
echo " Installation Complete!"
echo " You can now launch 'OPPO Companion' from your"
echo " Linux Application Menu, or run 'oppogui' in terminal."
echo "===================================================="
