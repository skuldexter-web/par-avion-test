#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: PAR AVION currently supports Debian-family systems with apt (Kali/Debian/Raspberry Pi OS)." >&2
  exit 1
fi

. /etc/os-release || true
ARCH="$(dpkg --print-architecture 2>/dev/null || uname -m)"
if [[ "${ID:-}" == "kali" || "${ID_LIKE:-}" == *debian* || "${ID:-}" == "debian" || "${ID:-}" == "raspbian" ]]; then
  echo "Detected Debian-family OS: ${PRETTY_NAME:-unknown} (${ARCH})"
else
  echo "WARNING: ${PRETTY_NAME:-unknown} is not explicitly recognized; continuing because apt is available."
fi

if [[ $EUID -eq 0 ]]; then SUDO=""; REAL_USER="${SUDO_USER:-root}"; else SUDO="sudo"; REAL_USER="$USER"; fi

echo "[1/6] Updating apt package lists…"
$SUDO apt-get update -qq

echo "[2/6] Installing system dependencies…"
$SUDO apt-get install -y \
  python3 python3-dev python3-tk python3-pip python3-venv \
  rtl-sdr librtlsdr-dev hackrf libhackrf-dev libusb-1.0-0-dev pkg-config \
  gpsd gpsd-clients sox libsox-fmt-all alsa-utils pulseaudio-utils \
  portaudio19-dev libsndfile1 usbutils build-essential git

if command -v apt-cache >/dev/null 2>&1; then
  if apt-cache policy dump1090-mutability 2>/dev/null | grep -q '^  Candidate:' && \
     ! apt-cache policy dump1090-mutability 2>/dev/null | grep -q 'Candidate: (none)'; then
    $SUDO apt-get install -y dump1090-mutability || true
  elif apt-cache policy dump1090-fa 2>/dev/null | grep -q '^  Candidate:' && \
       ! apt-cache policy dump1090-fa 2>/dev/null | grep -q 'Candidate: (none)'; then
    $SUDO apt-get install -y dump1090-fa || true
  fi
fi

if ! command -v rtl_ais >/dev/null 2>&1; then
  echo "  rtl_ais not found; Maritime mode will report this until rtl_ais is installed."
fi

echo "[3/6] Configuring non-root SDR access…"
UDEV=/etc/udev/rules.d/20-par-avion-sdr.rules
$SUDO tee "$UDEV" >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6089", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1209", ATTRS{idProduct}=="6089", GROUP="plugdev", MODE="0666"
EOF
$SUDO udevadm control --reload-rules 2>/dev/null || true
$SUDO udevadm trigger 2>/dev/null || true
if getent group plugdev >/dev/null 2>&1 && [[ "$REAL_USER" != "root" ]]; then
  $SUDO usermod -aG plugdev "$REAL_USER" || true
fi

echo "[4/6] Preventing DVB driver conflicts…"
$SUDO tee /etc/modprobe.d/20-par-avion-blacklist-rtl.conf >/dev/null <<'EOF'
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist rtl2830
EOF
if lsmod 2>/dev/null | grep -q dvb_usb_rtl28xxu; then
  $SUDO modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true
fi

echo "[5/6] Preparing Python virtual environment (.venv)…"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

echo "[6/6] Installing Python dependencies inside .venv…"
python -m pip install -r requirements.txt

mkdir -p "$HOME/.local/share/applications"
cat > assets/par-avion.desktop <<EOF
[Desktop Entry]
Name=PAR AVION
Comment=Tactical RF & Telemetry Suite
Exec=$ROOT/.venv/bin/python $ROOT/main.py
Icon=$ROOT/assets/par-avion.svg
Terminal=false
Type=Application
Categories=Utility;Science;HamRadio;
StartupNotify=true
EOF
cp assets/par-avion.desktop "$HOME/.local/share/applications/par-avion.desktop"
chmod +x "$HOME/.local/share/applications/par-avion.desktop"

if command -v systemctl >/dev/null 2>&1; then
  $SUDO systemctl enable gpsd.socket >/dev/null 2>&1 || true
fi

echo
 echo "Installation complete."
echo "Launch with: $ROOT/.venv/bin/python $ROOT/main.py"
echo "Log out/in after installation if plugdev group membership was changed."
