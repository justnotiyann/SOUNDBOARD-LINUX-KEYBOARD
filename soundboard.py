#!/usr/bin/env python3
"""
StreamBoard - Soundboard for Streamers on Linux
Supports: MP3, WAV, OGG | Global Shortcuts | Auto-refresh folder
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
try:
    from gi.repository import AppIndicator3
    HAS_INDICATOR = True
except:
    HAS_INDICATOR = False

import os
import json
import threading
import time
import sys
import subprocess
import shutil
from pathlib import Path

# Audio — pakai subprocess + ffplay, support MP3/WAV/OGG/FLAC + multiple playback simultan
import subprocess
import shutil

HAS_FFPLAY = shutil.which("ffplay") is not None
HAS_PYGAME = False  # tidak dipakai lagi

# File watcher
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

# Global shortcut
try:
    from pynput import keyboard as pynput_keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# ─── Paths ───────────────────────────────────────────────────────────────────
HOME = Path.home()
APP_DIR = HOME / ".config" / "streamboard"
SOUNDS_DIR = HOME / "StreamBoard" / "sounds"
CONFIG_FILE = APP_DIR / "config.json"

APP_DIR.mkdir(parents=True, exist_ok=True)
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_FORMATS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a'}

# ─── Config ──────────────────────────────────────────────────────────────────
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"shortcuts": {}, "volume": 80, "sounds_dir": str(SOUNDS_DIR)}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ─── Audio Engine ─────────────────────────────────────────────────────────────
class AudioEngine:
    def __init__(self):
        self.volume = 80  # 0-100
        self._procs = []
        self._lock = threading.Lock()

    def set_volume(self, vol):
        self.volume = int(vol)

    def play(self, filepath):
        if not HAS_FFPLAY:
            print("[Audio] ffplay not found. Install: sudo apt install ffmpeg")
            return

        def _play():
            try:
                proc = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                     "-volume", str(self.volume), filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                with self._lock:
                    self._procs.append(proc)
                proc.wait()
                with self._lock:
                    if proc in self._procs:
                        self._procs.remove(proc)
            except Exception as e:
                print(f"[Audio] Error playing {filepath}: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def stop_all(self):
        with self._lock:
            for proc in list(self._procs):
                try:
                    proc.terminate()
                except Exception:
                    pass
            self._procs.clear()

audio = AudioEngine()

# ─── File Watcher ─────────────────────────────────────────────────────────────
class SoundFolderHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self._last_trigger = 0

    def _trigger(self):
        now = time.time()
        if now - self._last_trigger > 0.5:
            self._last_trigger = now
            GLib.idle_add(self.callback)

    def on_created(self, event):
        if not event.is_directory:
            ext = Path(event.src_path).suffix.lower()
            if ext in SUPPORTED_FORMATS:
                self._trigger()

    def on_deleted(self, event):
        self._trigger()

    def on_moved(self, event):
        self._trigger()

# ─── Shortcut Listener ────────────────────────────────────────────────────────
class ShortcutListener:
    def __init__(self):
        self.shortcuts = {}  # key_str -> filepath
        self.listener = None
        self.recording = False
        self.record_callback = None
        self.current_keys = set()

    def key_to_str(self, key):
        try:
            return key.char
        except AttributeError:
            return str(key).replace('Key.', '<') + '>'

    def combo_to_str(self, keys):
        parts = sorted(str(k).replace('Key.', '') for k in keys)
        return '+'.join(parts)

    def start(self, shortcuts, play_callback):
        self.shortcuts = shortcuts
        self.play_callback = play_callback
        if not HAS_PYNPUT:
            return

        def on_press(key):
            self.current_keys.add(key)
            if self.recording:
                return
            # Check combinations
            combo = self.combo_to_str(self.current_keys)
            if combo in self.shortcuts:
                GLib.idle_add(self.play_callback, self.shortcuts[combo])

        def on_release(key):
            if self.recording and self.current_keys:
                combo = self.combo_to_str(self.current_keys)
                GLib.idle_add(self.record_callback, combo)
                self.recording = False
                self.current_keys.discard(key)
                return
            self.current_keys.discard(key)

        if self.listener:
            self.listener.stop()

        self.listener = pynput_keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self.listener.daemon = True
        self.listener.start()

    def start_recording(self, callback):
        self.current_keys.clear()
        self.record_callback = callback
        self.recording = True

    def stop(self):
        if self.listener:
            self.listener.stop()

shortcut_listener = ShortcutListener()

# ─── CSS ──────────────────────────────────────────────────────────────────────
CSS = b"""
* {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

window {
    background-color: #0d0d0f;
}

.header-bar {
    background: linear-gradient(135deg, #0d0d0f 0%, #1a1a2e 100%);
    padding: 16px 20px;
    border-bottom: 1px solid #1e1e2e;
}

.app-title {
    color: #e0e0ff;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
}

.app-subtitle {
    color: #555577;
    font-size: 10px;
    letter-spacing: 3px;
}

.sound-list {
    background-color: #0d0d0f;
    padding: 8px;
}

.sound-row {
    background-color: #111118;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    margin: 4px 8px;
    padding: 0px;
    transition: all 200ms ease;
}

.sound-row:hover {
    background-color: #1a1a2e;
    border-color: #3a3a6e;
}

.sound-name {
    color: #c8c8e8;
    font-size: 13px;
    font-weight: 600;
}

.sound-format {
    color: #444466;
    font-size: 10px;
    letter-spacing: 1px;
}

.shortcut-badge {
    background-color: #1e1e3a;
    color: #7878cc;
    border: 1px solid #3a3a6e;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}

.shortcut-badge-none {
    background-color: #1a1a1a;
    color: #333355;
    border: 1px solid #222233;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 10px;
    letter-spacing: 1px;
}

.play-btn {
    background: linear-gradient(135deg, #2a2a5e, #1a1a3e);
    color: #9090ee;
    border: 1px solid #3a3a7e;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 16px;
    min-width: 40px;
}

.play-btn:hover {
    background: linear-gradient(135deg, #3a3a8e, #2a2a6e);
    color: #b0b0ff;
}

.assign-btn {
    background-color: transparent;
    color: #445566;
    border: 1px solid #223344;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 10px;
    letter-spacing: 1px;
}

.assign-btn:hover {
    background-color: #1a2233;
    color: #6688aa;
    border-color: #334455;
}

.stop-btn {
    background: linear-gradient(135deg, #3e1a1a, #2e1010);
    color: #cc6666;
    border: 1px solid #7e3a3a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 14px;
}

.stop-btn:hover {
    background: linear-gradient(135deg, #5e2a2a, #4e1a1a);
    color: #ee8888;
}

.volume-scale trough {
    background-color: #1e1e2e;
    border-radius: 4px;
    min-height: 4px;
}

.volume-scale highlight {
    background: linear-gradient(90deg, #3a3a8e, #6a6aee);
    border-radius: 4px;
}

.volume-scale slider {
    background-color: #8888ee;
    border-radius: 50%;
    min-width: 14px;
    min-height: 14px;
}

.folder-btn {
    background-color: #111118;
    color: #555577;
    border: 1px solid #1e1e2e;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    letter-spacing: 1px;
}

.folder-btn:hover {
    background-color: #1a1a2e;
    color: #8888aa;
}

.status-bar {
    background-color: #080810;
    border-top: 1px solid #1e1e2e;
    padding: 6px 16px;
}

.status-text {
    color: #333355;
    font-size: 10px;
    letter-spacing: 1px;
}

.status-dot {
    color: #4a4a9e;
    font-size: 8px;
}

.empty-state {
    color: #222244;
    font-size: 13px;
    letter-spacing: 1px;
}

.empty-icon {
    color: #1a1a33;
    font-size: 48px;
}

.recording-label {
    color: #ee4444;
    font-size: 12px;
    letter-spacing: 1px;
    font-weight: 700;
}

scrolledwindow {
    background-color: #0d0d0f;
}

scrollbar {
    background-color: #0d0d0f;
    min-width: 6px;
}

scrollbar slider {
    background-color: #1e1e3e;
    border-radius: 3px;
    min-height: 40px;
}

scrollbar slider:hover {
    background-color: #3a3a6e;
}
"""

# ─── Main Window ──────────────────────────────────────────────────────────────
class StreamBoardApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="StreamBoard")
        self.config = load_config()
        self.sounds_dir = Path(self.config.get("sounds_dir", str(SOUNDS_DIR)))
        self.sound_files = []
        self.recording_for = None

        self._apply_css()
        self._build_ui()
        self._setup_tray()
        self._start_file_watcher()
        self._start_shortcut_listener()
        self._refresh_sounds()

        self.connect("delete-event", self._on_delete)
        self.set_default_size(520, 600)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # ── Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.get_style_context().add_class("header-bar")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label="STREAMBOARD")
        title.get_style_context().add_class("app-title")
        title.set_xalign(0)

        subtitle = Gtk.Label(label="SOUNDBOARD FOR STREAMERS")
        subtitle.get_style_context().add_class("app-subtitle")
        subtitle.set_xalign(0)

        # Controls row
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_row.set_margin_top(10)

        # Volume
        vol_icon = Gtk.Label(label="🔊")
        vol_icon.set_margin_end(4)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_value(self.config.get("volume", 80))
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_size_request(120, -1)
        self.vol_scale.get_style_context().add_class("volume-scale")
        self.vol_scale.connect("value-changed", self._on_volume_change)

        self.vol_label = Gtk.Label(label=f"{int(self.config.get('volume', 80))}%")
        self.vol_label.get_style_context().add_class("status-text")
        self.vol_label.set_size_request(38, -1)

        stop_btn = Gtk.Button(label="⏹ STOP ALL")
        stop_btn.get_style_context().add_class("stop-btn")
        stop_btn.connect("clicked", lambda _: audio.stop_all())

        folder_btn = Gtk.Button(label="📁 SOUNDS FOLDER")
        folder_btn.get_style_context().add_class("folder-btn")
        folder_btn.connect("clicked", self._open_sounds_folder)

        ctrl_row.pack_start(vol_icon, False, False, 0)
        ctrl_row.pack_start(self.vol_scale, False, False, 0)
        ctrl_row.pack_start(self.vol_label, False, False, 0)
        ctrl_row.pack_end(folder_btn, False, False, 0)
        ctrl_row.pack_end(stop_btn, False, False, 4)

        top_row.pack_start(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1), False, False, 0)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        vbox.pack_start(title, False, False, 0)
        vbox.pack_start(subtitle, False, False, 0)
        top_row.pack_start(vbox, True, True, 0)

        header.pack_start(top_row, False, False, 0)
        header.pack_start(ctrl_row, False, False, 0)
        main_box.pack_start(header, False, False, 0)

        # ── Sound List
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.get_style_context().add_class("sound-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.list_box)
        main_box.pack_start(scroll, True, True, 0)

        # ── Status Bar
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_bar.get_style_context().add_class("status-bar")
        status_bar.set_margin_top(0)

        dot = Gtk.Label(label="●")
        dot.get_style_context().add_class("status-dot")

        self.status_label = Gtk.Label(label="READY  •  WATCHING FOLDER")
        self.status_label.get_style_context().add_class("status-text")
        self.status_label.set_xalign(0)

        self.count_label = Gtk.Label(label="0 SOUNDS")
        self.count_label.get_style_context().add_class("status-text")

        status_bar.pack_start(dot, False, False, 0)
        status_bar.pack_start(self.status_label, True, True, 0)
        status_bar.pack_end(self.count_label, False, False, 0)
        main_box.pack_end(status_bar, False, False, 0)

        audio.set_volume(self.config.get("volume", 80))

    def _setup_tray(self):
        if not HAS_INDICATOR:
            return
        try:
            self.indicator = AppIndicator3.Indicator.new(
                "streamboard",
                "audio-x-generic",
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

            menu = Gtk.Menu()
            show_item = Gtk.MenuItem(label="Show StreamBoard")
            show_item.connect("activate", lambda _: self.present())
            menu.append(show_item)

            sep = Gtk.SeparatorMenuItem()
            menu.append(sep)

            stop_item = Gtk.MenuItem(label="Stop All Sounds")
            stop_item.connect("activate", lambda _: audio.stop_all())
            menu.append(stop_item)

            sep2 = Gtk.SeparatorMenuItem()
            menu.append(sep2)

            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", self._quit)
            menu.append(quit_item)

            menu.show_all()
            self.indicator.set_menu(menu)
        except Exception as e:
            print(f"[Tray] Could not setup tray: {e}")

    def _start_file_watcher(self):
        if not HAS_WATCHDOG:
            return
        handler = SoundFolderHandler(self._refresh_sounds)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.sounds_dir), recursive=False)
        self.observer.daemon = True
        self.observer.start()

    def _start_shortcut_listener(self):
        if not HAS_PYNPUT:
            return
        shortcuts = {v: k for k, v in self.config.get("shortcuts", {}).items()}
        shortcut_listener.start(shortcuts, self._play_sound)

    def _refresh_sounds(self):
        # Clear list
        for child in self.list_box.get_children():
            self.list_box.remove(child)

        # Scan folder
        self.sound_files = []
        if self.sounds_dir.exists():
            for f in sorted(self.sounds_dir.iterdir()):
                if f.suffix.lower() in SUPPORTED_FORMATS:
                    self.sound_files.append(f)

        if not self.sound_files:
            self._show_empty_state()
        else:
            for sound_file in self.sound_files:
                row = self._make_sound_row(sound_file)
                self.list_box.add(row)

        self.list_box.show_all()
        n = len(self.sound_files)
        self.count_label.set_text(f"{n} SOUND{'S' if n != 1 else ''}")
        return False

    def _show_empty_state(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(60)
        box.set_margin_bottom(60)

        icon = Gtk.Label(label="🎵")
        icon.get_style_context().add_class("empty-icon")

        msg = Gtk.Label(label="NO SOUNDS FOUND")
        msg.get_style_context().add_class("empty-state")

        hint = Gtk.Label(label=f"Add MP3 / WAV / OGG files to:\n{self.sounds_dir}")
        hint.get_style_context().add_class("status-text")
        hint.set_justify(Gtk.Justification.CENTER)
        hint.set_line_wrap(True)

        box.pack_start(icon, False, False, 0)
        box.pack_start(msg, False, False, 0)
        box.pack_start(hint, False, False, 0)

        row = Gtk.ListBoxRow()
        row.add(box)
        self.list_box.add(row)

    def _make_sound_row(self, sound_file):
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("sound-row")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(10)
        hbox.set_margin_bottom(10)
        hbox.set_margin_start(14)
        hbox.set_margin_end(14)

        # Play button
        play_btn = Gtk.Button(label="▶")
        play_btn.get_style_context().add_class("play-btn")
        play_btn.connect("clicked", lambda _, f=sound_file: self._play_sound(str(f)))

        # Name info
        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_label = Gtk.Label(label=sound_file.stem.upper())
        name_label.get_style_context().add_class("sound-name")
        name_label.set_xalign(0)
        name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        name_label.set_max_width_chars(28)

        fmt_label = Gtk.Label(label=sound_file.suffix.upper().lstrip('.'))
        fmt_label.get_style_context().add_class("sound-format")
        fmt_label.set_xalign(0)

        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(fmt_label, False, False, 0)

        # Shortcut badge
        shortcuts = self.config.get("shortcuts", {})
        shortcut_str = shortcuts.get(str(sound_file), None)

        shortcut_badge = Gtk.Label()
        if shortcut_str:
            shortcut_badge.set_text(shortcut_str.upper())
            shortcut_badge.get_style_context().add_class("shortcut-badge")
        else:
            shortcut_badge.set_text("NO SHORTCUT")
            shortcut_badge.get_style_context().add_class("shortcut-badge-none")

        # Assign button
        assign_btn = Gtk.Button(label="ASSIGN KEY")
        assign_btn.get_style_context().add_class("assign-btn")
        assign_btn.connect("clicked", lambda _, f=sound_file, b=shortcut_badge: self._assign_shortcut(f, b))

        # Clear button (only if has shortcut)
        if shortcut_str:
            clear_btn = Gtk.Button(label="✕")
            clear_btn.get_style_context().add_class("assign-btn")
            clear_btn.connect("clicked", lambda _, f=sound_file, b=shortcut_badge: self._clear_shortcut(f, b))
            hbox.pack_end(clear_btn, False, False, 0)

        hbox.pack_start(play_btn, False, False, 0)
        hbox.pack_start(name_box, True, True, 0)
        hbox.pack_end(assign_btn, False, False, 0)
        hbox.pack_end(shortcut_badge, False, False, 4)

        row.add(hbox)
        return row

    def _play_sound(self, filepath):
        audio.play(filepath)
        name = Path(filepath).stem
        self.status_label.set_text(f"▶  PLAYING: {name.upper()}")
        GLib.timeout_add(2000, lambda: self.status_label.set_text("READY  •  WATCHING FOLDER"))

    def _assign_shortcut(self, sound_file, badge_label):
        if self.recording_for:
            return

        self.recording_for = sound_file
        self.status_label.set_text("⏺  PRESS ANY KEY COMBO...")

        def on_recorded(combo):
            shortcuts = self.config.setdefault("shortcuts", {})
            # Remove old mapping for same combo
            for k, v in list(shortcuts.items()):
                if v == combo:
                    del shortcuts[k]
            shortcuts[str(sound_file)] = combo
            save_config(self.config)
            self.recording_for = None
            self._start_shortcut_listener()
            badge_label.set_text(combo.upper())
            badge_label.get_style_context().remove_class("shortcut-badge-none")
            badge_label.get_style_context().add_class("shortcut-badge")
            self.status_label.set_text(f"✓  SHORTCUT SET: {combo.upper()}")
            GLib.timeout_add(2000, lambda: self.status_label.set_text("READY  •  WATCHING FOLDER"))
            # Refresh to show clear button
            GLib.timeout_add(100, self._refresh_sounds)

        shortcut_listener.start_recording(on_recorded)

    def _clear_shortcut(self, sound_file, badge_label):
        shortcuts = self.config.get("shortcuts", {})
        shortcuts.pop(str(sound_file), None)
        save_config(self.config)
        self._start_shortcut_listener()
        self._refresh_sounds()

    def _on_volume_change(self, scale):
        vol = int(scale.get_value())
        self.vol_label.set_text(f"{vol}%")
        audio.set_volume(vol)  # langsung update, efektif di playback berikutnya
        self.config["volume"] = vol
        save_config(self.config)

    def _open_sounds_folder(self, _=None):
        os.system(f'xdg-open "{self.sounds_dir}" &')

    def _on_delete(self, win, event):
        win.hide()
        return True  # Prevent actual close, just hide to tray

    def _quit(self, _=None):
        if hasattr(self, 'observer'):
            self.observer.stop()
        shortcut_listener.stop()
        Gtk.main_quit()

# ─── Entry Point ──────────────────────────────────────────────────────────────
def main():
    if not HAS_FFPLAY:
        print("[ERROR] ffplay tidak ditemukan.")
        print("  Install dengan: sudo apt install ffmpeg")
        sys.exit(1)

    app = StreamBoardApp()
    app.show_all()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
