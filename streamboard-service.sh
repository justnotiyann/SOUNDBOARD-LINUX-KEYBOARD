#!/bin/bash
# StreamBoard - Service Manager
# Install / uninstall / status systemd user service

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_DIR="$HOME/StreamBoard"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/streamboard.service"
PYTHON_BIN="$(which python3)"

# Pakai venv kalau ada
if [ -f "$APP_DIR/.venv/bin/python3" ]; then
    PYTHON_BIN="$APP_DIR/.venv/bin/python3"
fi

# ─── Header ──────────────────────────────────────────────────────────────────
print_header() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════╗"
    echo "  ║   STREAMBOARD - SERVICE MANAGER  ║"
    echo "  ╚══════════════════════════════════╝"
    echo -e "${NC}"
}

# ─── Install service ─────────────────────────────────────────────────────────
install_service() {
    print_header
    echo -e "${BOLD}Installing StreamBoard as background service...${NC}"
    echo ""

    # Cek app ada
    if [ ! -f "$APP_DIR/soundboard.py" ]; then
        echo -e "${RED}  ✗ $APP_DIR/soundboard.py tidak ditemukan.${NC}"
        echo -e "    Jalankan install.sh dulu."
        exit 1
    fi

    # Buat direktori systemd user
    mkdir -p "$SERVICE_DIR"

    # Detect display — wajib untuk GTK app
    DISPLAY_VAL="${DISPLAY:-:0}"
    DBUS_VAL="${DBUS_SESSION_BUS_ADDRESS:-}"

    # Tulis service file
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=StreamBoard - Soundboard for Streamers
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$PYTHON_BIN $APP_DIR/soundboard.py
WorkingDirectory=$APP_DIR
Restart=on-failure
RestartSec=3

# Variabel environment untuk GTK/display
Environment=DISPLAY=$DISPLAY_VAL
Environment=DBUS_SESSION_BUS_ADDRESS=$DBUS_VAL
Environment=XDG_RUNTIME_DIR=/run/user/%U
Environment=HOME=$HOME
Environment=PATH=$PATH

# Jangan kill saat terminal ditutup
KillMode=process

[Install]
WantedBy=default.target
EOF

    echo -e "${GREEN}  ✓ Service file dibuat: $SERVICE_FILE${NC}"

    # ── Pakai logo.png dari folder StreamBoard ────────────────────────────
    LOGO_SRC="$APP_DIR/logo.png"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
    mkdir -p "$ICON_DIR"

    if [ -f "$LOGO_SRC" ]; then
        cp "$LOGO_SRC" "$ICON_DIR/streamboard.png"
        echo -e "${GREEN}  ✓ Icon diambil dari $LOGO_SRC${NC}"
    else
        echo -e "${YELLOW}  ⚠ logo.png tidak ditemukan di $APP_DIR, icon default dipakai${NC}"
    fi
    gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true

    # ── Buat .desktop file (GNOME app launcher + desktop shortcut) ─────────
    DESKTOP_APP_DIR="$HOME/.local/share/applications"
    DESKTOP_DIR="$HOME/Desktop"
    mkdir -p "$DESKTOP_APP_DIR"

    DESKTOP_CONTENT="[Desktop Entry]
Name=StreamBoard
GenericName=Soundboard
Comment=Soundboard for Linux Streamers - Global shortcuts, auto-refresh folder
Exec=$PYTHON_BIN $APP_DIR/soundboard.py
Icon=$APP_DIR/logo.png
Type=Application
Categories=AudioVideo;Audio;Utility;
Keywords=soundboard;streamer;audio;shortcut;sound;keyboard;
StartupNotify=true
Terminal=false
X-GNOME-Autostart-enabled=false"

    # Install ke app launcher (GNOME Activities / search)
    echo "$DESKTOP_CONTENT" > "$DESKTOP_APP_DIR/streamboard.desktop"
    chmod +x "$DESKTOP_APP_DIR/streamboard.desktop"
    echo -e "${GREEN}  ✓ App launcher terdaftar (GNOME Activities)${NC}"

    # Install ke Desktop juga
    if [ -d "$DESKTOP_DIR" ]; then
        echo "$DESKTOP_CONTENT" > "$DESKTOP_DIR/streamboard.desktop"
        chmod +x "$DESKTOP_DIR/streamboard.desktop"
        # Trust desktop file di GNOME
        gio set "$DESKTOP_DIR/streamboard.desktop" metadata::trusted true 2>/dev/null || true
        echo -e "${GREEN}  ✓ Desktop shortcut dibuat${NC}"
    fi

    # Update desktop database agar langsung muncul di search
    update-desktop-database "$DESKTOP_APP_DIR" 2>/dev/null || true

    # Reload systemd user daemon
    systemctl --user daemon-reload
    echo -e "${GREEN}  ✓ Systemd daemon reloaded${NC}"

    # Enable agar auto-start saat login
    systemctl --user enable streamboard.service
    echo -e "${GREEN}  ✓ Auto-start saat login: aktif${NC}"

    # Start sekarang
    systemctl --user start streamboard.service
    sleep 1

    # Cek status
    if systemctl --user is-active --quiet streamboard.service; then
        echo -e "${GREEN}  ✓ StreamBoard berjalan di background!${NC}"
    else
        echo -e "${YELLOW}  ⚠ Service started tapi mungkin butuh display.${NC}"
        echo -e "    Cek log: ${CYAN}journalctl --user -u streamboard -n 20${NC}"
    fi

    echo ""
    echo -e "${GREEN}${BOLD}════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  ✓ Instalasi service selesai!${NC}"
    echo -e "${GREEN}${BOLD}════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Perintah berguna:${NC}"
    echo -e "  ${CYAN}bash streamboard-service.sh status${NC}   — cek status"
    echo -e "  ${CYAN}bash streamboard-service.sh stop${NC}     — hentikan"
    echo -e "  ${CYAN}bash streamboard-service.sh start${NC}    — jalankan"
    echo -e "  ${CYAN}bash streamboard-service.sh restart${NC}  — restart"
    echo -e "  ${CYAN}bash streamboard-service.sh log${NC}      — lihat log"
    echo -e "  ${CYAN}bash streamboard-service.sh remove${NC}   — hapus service"
    echo ""
    echo -e "  ${BOLD}StreamBoard sekarang bisa di-search di GNOME Activities (tekan Super)${NC}"
    echo -e "  ${BOLD}dan ada shortcut di Desktop.${NC}"
    echo ""
}

# ─── Remove service ──────────────────────────────────────────────────────────
remove_service() {
    print_header
    echo -e "${BOLD}Removing StreamBoard service...${NC}"

    systemctl --user stop streamboard.service 2>/dev/null || true
    systemctl --user disable streamboard.service 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo -e "${GREEN}  ✓ Service dihapus${NC}"

    # Hapus .desktop dan icon juga
    rm -f "$HOME/.local/share/applications/streamboard.desktop"
    rm -f "$HOME/Desktop/streamboard.desktop"
    rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/streamboard.png"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
    echo -e "${GREEN}  ✓ App launcher & desktop shortcut dihapus${NC}"
    echo ""
}

# ─── Status ──────────────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo -e "${BOLD}Status StreamBoard Service:${NC}"
    echo ""
    systemctl --user status streamboard.service --no-pager || true
    echo ""
}

# ─── Log ─────────────────────────────────────────────────────────────────────
show_log() {
    echo ""
    echo -e "${BOLD}Log StreamBoard (50 baris terakhir):${NC}"
    echo ""
    journalctl --user -u streamboard.service -n 50 --no-pager
    echo ""
}

# ─── Main ────────────────────────────────────────────────────────────────────
case "${1:-install}" in
    install)   install_service ;;
    remove)    remove_service ;;
    start)     systemctl --user start streamboard.service && echo -e "${GREEN}✓ Started${NC}" ;;
    stop)      systemctl --user stop streamboard.service && echo -e "${GREEN}✓ Stopped${NC}" ;;
    restart)   systemctl --user restart streamboard.service && echo -e "${GREEN}✓ Restarted${NC}" ;;
    status)    show_status ;;
    log)       show_log ;;
    *)
        echo "Usage: $0 {install|remove|start|stop|restart|status|log}"
        exit 1
        ;;
esac
