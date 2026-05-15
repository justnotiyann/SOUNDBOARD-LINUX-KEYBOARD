#!/bin/bash
# StreamBoard - AppImage Builder
# Requires: appimage-builder, Docker (optional)

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_NAME="StreamBoard"
APP_VERSION="1.0.0"
BUILD_DIR="$(pwd)/build"

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════╗"
echo "  ║   STREAMBOARD - AppImage Builder ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

# Install appimage-builder if needed
if ! command -v appimage-builder &> /dev/null; then
    echo -e "${BOLD}Installing appimage-builder...${NC}"
    pip3 install appimage-builder
fi

# Create AppDir structure
echo -e "${BOLD}[1/4] Creating AppDir structure...${NC}"
mkdir -p "$BUILD_DIR/AppDir/usr/bin"
mkdir -p "$BUILD_DIR/AppDir/usr/lib/python3"
mkdir -p "$BUILD_DIR/AppDir/usr/share/applications"
mkdir -p "$BUILD_DIR/AppDir/usr/share/icons"

# Copy app files
cp soundboard.py "$BUILD_DIR/AppDir/usr/bin/streamboard"
chmod +x "$BUILD_DIR/AppDir/usr/bin/streamboard"

# Create .desktop file
cat > "$BUILD_DIR/AppDir/usr/share/applications/streamboard.desktop" << EOF
[Desktop Entry]
Name=StreamBoard
Comment=Soundboard for Linux Streamers
Exec=streamboard
Icon=audio-x-generic
Type=Application
Categories=AudioVideo;Audio;
Keywords=soundboard;streamer;audio;shortcut;
StartupNotify=true
EOF

# Create AppRun
cat > "$BUILD_DIR/AppDir/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PYTHONPATH="$HERE/usr/lib/python3:$PYTHONPATH"
export PATH="$HERE/usr/bin:$PATH"
exec python3 "$HERE/usr/bin/streamboard" "$@"
EOF
chmod +x "$BUILD_DIR/AppDir/AppRun"

# Symlink desktop and icon
ln -sf usr/share/applications/streamboard.desktop "$BUILD_DIR/AppDir/streamboard.desktop"
ln -sf usr/share/icons/audio-x-generic.png "$BUILD_DIR/AppDir/.DirIcon" 2>/dev/null || true

echo -e "${GREEN}  ✓ AppDir structure created${NC}"

# Generate appimage-builder recipe
echo -e "${BOLD}[2/4] Generating build recipe...${NC}"

cat > "$BUILD_DIR/AppImageBuilder.yml" << EOF
version: 1
AppDir:
  path: ./AppDir
  app_info:
    id: io.streamboard.app
    name: StreamBoard
    icon: audio-x-generic
    version: $APP_VERSION
    exec: usr/bin/python3
    exec_args: "\$APPDIR/usr/bin/streamboard \$@"

  apt:
    arch: amd64
    sources:
      - sourceline: deb http://archive.ubuntu.com/ubuntu/ focal main restricted universe multiverse
    include:
      - python3
      - python3-gi
      - python3-gi-cairo
      - gir1.2-gtk-3.0
      - gir1.2-appindicator3-0.1
      - libcairo2
      - libgirepository-1.0-1
      - libsdl2-2.0-0
      - libsdl2-mixer-2.0-0
      - gstreamer1.0-plugins-good
      - gstreamer1.0-libav
    exclude:
      - humanity-icon-theme
      - hicolor-icon-theme
      - adwaita-icon-theme

  files:
    include: []
    exclude:
      - usr/share/man
      - usr/share/doc/*/README.*
      - usr/share/doc/*/changelog.*
      - usr/share/doc/*/NEWS.*
      - usr/share/doc/*/TODO.*

  pip:
    arch: x86_64
    requirements:
      - pygame
      - watchdog
      - pynput

  runtime:
    env:
      PYTHONPATH: \${APPDIR}/usr/lib/python3/dist-packages

AppImage:
  arch: x86_64
  file_name: StreamBoard-$APP_VERSION-x86_64.AppImage
  update-information: None
  sign-key: None
EOF

echo -e "${GREEN}  ✓ Recipe generated${NC}"

# Build
echo -e "${BOLD}[3/4] Building AppImage...${NC}"
echo -e "${YELLOW}  This may take a few minutes...${NC}"
cd "$BUILD_DIR"
appimage-builder --recipe AppImageBuilder.yml --skip-test

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✓ AppImage built successfully!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Output:${NC}"
echo -e "  ${CYAN}$BUILD_DIR/StreamBoard-$APP_VERSION-x86_64.AppImage${NC}"
echo ""
echo -e "  ${BOLD}To run:${NC}"
echo -e "  ${CYAN}chmod +x StreamBoard-$APP_VERSION-x86_64.AppImage${NC}"
echo -e "  ${CYAN}./StreamBoard-$APP_VERSION-x86_64.AppImage${NC}"
echo ""
