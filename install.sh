#!/usr/bin/env bash
# Par-Avion GUI Installer for Kali Linux & Raspberry Pi OS

set -e

echo "========================================"
echo "  Par-Avion GUI System Installer"
echo "========================================"

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    echo "[*] Detected OS: $PRETTY_NAME"
else
    echo "[!] Cannot detect OS. Assuming Debian-based."
    OS="debian"
fi

# 2. Install System Packages
echo "[*] Installing system dependencies via apt..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-tk

# 3. Setup Python Virtual Environment (PEP 668 Compliant)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

echo "[*] Setting up Python Virtual Environment in $VENV_DIR..."
python3 -m venv "$VENV_DIR"

# 4. Install PyPI Modules
echo "[*] Installing Python requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

# 5. Create Desktop Launcher (.desktop)
DESKTOP_FILE="$HOME/.local/share/applications/par-avion.desktop"
mkdir -p "$HOME/.local/share/applications"

echo "[*] Creating Desktop Launcher..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Name=Par-Avion GUI
Comment=High-Performance SDR & Telemetry Suite
Exec=$VENV_DIR/bin/python $APP_DIR/main.py
Icon=$APP_DIR/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;Network;HamRadio;
EOF

chmod +x "$DESKTOP_FILE"

echo "========================================"
echo "[+] Installation Complete!"
echo "[+] You can now launch 'Par-Avion GUI' from your application menu,"
echo "[+] or run it manually via: source .venv/bin/activate && python main.py"
echo "========================================"
