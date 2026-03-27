#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Watson Voice Installer ==="
echo

# --- Check system dependencies ---

echo "Checking system dependencies..."

check_cmd() {
    if ! command -v "$1" &> /dev/null; then
        echo "  [MISSING] $1 - $2"
        return 1
    else
        echo "  [OK] $1"
        return 0
    fi
}

missing=0

check_cmd python3 "sudo apt install python3" || missing=1
check_cmd pip "sudo apt install python3-pip" || missing=1
check_cmd cmake "sudo apt install cmake" || missing=1

check_cmd notify-send "sudo apt install libnotify-bin" || true

# PortAudio
if ! pkg-config --exists portaudio-2.0 2>/dev/null; then
    if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
        echo "  [MISSING] libportaudio - sudo apt install libportaudio2 portaudio19-dev"
        missing=1
    else
        echo "  [OK] libportaudio"
    fi
else
    echo "  [OK] portaudio"
fi

# fcitx5 development headers
if pkg-config --exists Fcitx5Core 2>/dev/null; then
    echo "  [OK] fcitx5 development headers"
else
    echo "  [MISSING] fcitx5 dev - sudo apt install libfcitx5core-dev extra-cmake-modules"
    missing=1
fi

# NVIDIA GPU
echo
echo "Checking NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "  [OK] NVIDIA driver detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | while read -r line; do
        echo "  GPU: $line"
    done
else
    echo "  [WARNING] nvidia-smi not found. GPU acceleration will not be available."
fi

if [ "$missing" -eq 1 ]; then
    echo
    echo "Please install missing dependencies first."
    echo
    echo "For Debian/Ubuntu:"
    echo "  sudo apt install python3 python3-pip cmake extra-cmake-modules \\"
    echo "    libfcitx5core-dev libportaudio2 portaudio19-dev \\"
    echo "    libnotify-bin"
    echo
    exit 1
fi

# --- Build fcitx5 addon ---

echo
echo "Building fcitx5 addon..."
BUILD_DIR="$SCRIPT_DIR/build"
mkdir -p "$BUILD_DIR"
cmake -S "$SCRIPT_DIR" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build "$BUILD_DIR"

echo
echo "Installing fcitx5 addon (requires sudo)..."
sudo cmake --install "$BUILD_DIR"

# --- Install Python package ---

echo
echo "Installing watson-voice Python package..."
pip install -e "$SCRIPT_DIR" --break-system-packages 2>/dev/null \
    || pip install -e "$SCRIPT_DIR"

# --- Install systemd user service ---

echo
echo "Installing systemd user service..."
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/watson-voice.service << UNIT
[Unit]
Description=Watson Voice - Voice Input Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=$(command -v watson-voice) --backend voxtral
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
echo "  Installed: ~/.config/systemd/user/watson-voice.service"

echo
echo "=== Installation complete! ==="
echo
echo "Step 1: Start the daemon"
echo "  systemctl --user start watson-voice"
echo "  systemctl --user enable watson-voice   # auto-start on login"
echo
echo "Step 2: Add '語音輸入 (Watson Voice)' in fcitx5 settings"
echo "  Open: fcitx5-configtool → Input Method → Add → Watson Voice"
echo
echo "Step 3: Switch to '語音輸入' to start recording, switch away to transcribe"
echo
echo "Logs: journalctl --user -u watson-voice -f"
echo "First run will download the model (~3GB)."
