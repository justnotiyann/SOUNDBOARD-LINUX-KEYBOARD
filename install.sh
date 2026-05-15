#!/bin/bash
# StreamBoard - Dependency Installer
# Supports: Ubuntu/Debian, Fedora, Arch Linux

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════╗"
echo "  ║   STREAMBOARD - INSTALLER        ║"
echo "  ║   Soundboard for Linux Streamers ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    DISTRO="unknown"
fi

echo -e "${BOLD}[1/4] Detecting system...${NC}"
echo "  Distro : $DISTRO"
echo "  Python : $(python3 --version 2>/dev/null || echo 'not found')"
echo ""

# System packages
echo -e "${BOLD}[2/4] Installing system dependencies...${NC}"

case $DISTRO in
    ubuntu|debian|linuxmint|pop)
        sudo apt update -qq
        sudo apt install -y \
            python3-gi \
            python3-gi-cairo \
            gir1.2-gtk-3.0 \
            gir1.2-appindicator3-0.1 \
            python3-pip \
            libcairo2-dev \
            libgirepository1.0-dev \
            pkg-config \
            python3-dev \
            libsdl2-mixer-2.0-0 \
            libsdl2-2.0-0 \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad \
            gstreamer1.0-libav \
            ffmpeg
        echo -e "${GREEN}  ✓ System packages installed${NC}"
        ;;
    fedora|rhel|centos)
        sudo dnf install -y \
            python3-gobject \
            python3-cairo \
            gtk3 \
            libappindicator-gtk3 \
            python3-pip \
            SDL2 \
            SDL2_mixer \
            ffmpeg
        echo -e "${GREEN}  ✓ System packages installed${NC}"
        ;;
    arch|manjaro|endeavouros)
        sudo pacman -Sy --noconfirm \
            python-gobject \
            python-cairo \
            gtk3 \
            libappindicator-gtk3 \
            python-pip \
            sdl2 \
            sdl2_mixer \
            ffmpeg
        echo -e "${GREEN}  ✓ System packages installed${NC}"
        ;;
    *)
        echo -e "${YELLOW}  ⚠ Unknown distro. Please install manually:${NC}"
        echo "    python3-gi, gir1.2-gtk-3.0, python3-pip, ffmpeg"
        ;;
esac

# Python packages
echo ""
echo -e "${BOLD}[3/4] Installing Python packages...${NC}"

# Try apt first (pygame, watchdog, pynput) — cleanest on Ubuntu 24.04+
APT_PYGAME=0
APT_WATCHDOG=0
APT_PYNPUT=0

if sudo apt install -y python3-pygame 2>/dev/null; then APT_PYGAME=1; fi
if sudo apt install -y python3-watchdog 2>/dev/null; then APT_WATCHDOG=1; fi
if sudo apt install -y python3-pynput 2>/dev/null; then APT_PYNPUT=1; fi

# For anything not available via apt, use pipx or venv fallback
MISSING=()
[ $APT_PYGAME -eq 0 ] && MISSING+=("pygame")
[ $APT_WATCHDOG -eq 0 ] && MISSING+=("watchdog")
[ $APT_PYNPUT -eq 0 ] && MISSING+=("pynput")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${YELLOW}  Some packages not in apt, installing via pip venv...${NC}"

    # Create a venv inside ~/StreamBoard
    python3 -m venv ~/StreamBoard/.venv --system-site-packages

    # Install missing packages into venv
    ~/StreamBoard/.venv/bin/pip install "${MISSING[@]}"

    # Update the run.sh launcher to use venv python
    USE_VENV=1
fi

echo -e "${GREEN}  ✓ Python packages installed${NC}"

# Create sounds folder
echo ""
echo -e "${BOLD}[4/4] Setting up folders...${NC}"
mkdir -p ~/StreamBoard/sounds
echo -e "${GREEN}  ✓ Created ~/StreamBoard/sounds${NC}"

# Create launcher script (use venv python if it was created)
if [ "${USE_VENV:-0}" -eq 1 ]; then
cat > ~/StreamBoard/run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python3 soundboard.py
EOF
else
cat > ~/StreamBoard/run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
python3 soundboard.py
EOF
fi
chmod +x ~/StreamBoard/run.sh

# Copy app to StreamBoard folder
cp "$(dirname "$0")/soundboard.py" ~/StreamBoard/soundboard.py

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✓ Installation complete!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}To run StreamBoard:${NC}"
echo -e "  ${CYAN}cd ~/StreamBoard && bash run.sh${NC}"
echo ""
echo -e "  ${BOLD}(atau langsung:)${NC}"
if [ "${USE_VENV:-0}" -eq 1 ]; then
echo -e "  ${CYAN}~/StreamBoard/.venv/bin/python3 ~/StreamBoard/soundboard.py${NC}"
else
echo -e "  ${CYAN}python3 ~/StreamBoard/soundboard.py${NC}"
fi
echo ""
echo -e "  ${BOLD}Sounds folder:${NC}"
echo -e "  ${CYAN}~/StreamBoard/sounds/${NC}"
echo ""
echo -e "${YELLOW}  NOTE: For global shortcuts, make sure you're"
echo -e "  running GNOME on X11 (not Wayland).${NC}"
echo ""
