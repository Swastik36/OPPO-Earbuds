#!/usr/bin/env bash
set -e

echo "===================================================="
echo " Installing OPPO Enco Buds3 Pro Linux Companion"
echo "===================================================="

# Target directories
INSTALL_DIR="$HOME/.local/share/oppo-control"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

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
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

echo "[3/5] Setting up isolated Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"

echo "[4/5] Installing package and dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR" -q

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
Icon=bluetooth
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
