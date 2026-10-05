"""
modules/cross_device_sync.py - ULTRON Mobile Phone & Laptop Cross-Device Synergy Engine

Unifies mobile phone and laptop into a single cohesive ULTRON workstation:
- Bi-directional instant clipboard synchronization (Phone <-> Laptop)
- Wireless mobile touchpad & presentation remote (mouse move, click, scroll)
- Remote phone battery sentinel & "Find My Phone" ringer via ADB
- Bi-directional Drag-and-Drop file transfer (Phone <-> Laptop Downloads & Desktop)
- Remote laptop control (Volume, Media, Lock Workstation, Screenshot)
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from modules.human_controller import human_controller
from modules.smart_clipboard import smart_clipboard
from modules.system_paths import get_desktop_dir, get_downloads_dir


class CrossDeviceSync:
    """Manages real-time mobile and laptop cross-device automation."""

    def __init__(self) -> None:
        self._shared_clipboard: str = ""
        self._lock = threading.Lock()

    def get_laptop_clipboard_for_phone(self) -> str:
        """Returns the current laptop clipboard content for mobile devices."""
        return smart_clipboard._get_current_clipboard_text()

    def set_clipboard_from_phone(self, text: str, auto_paste: bool = False) -> Tuple[bool, str]:
        """Receives text from phone, copies to laptop clipboard, and optionally pastes."""
        if not text:
            return False, "No content received from phone."
        with self._lock:
            self._shared_clipboard = text
            smart_clipboard._set_clipboard_text(text)

        if auto_paste:
            human_controller.press_shortcut("paste")
            return True, "Synced text from phone and pasted into active laptop window."
        return True, "Synced text from phone directly into laptop clipboard."

    def handle_touchpad_input(self, dx: int, dy: int, action: str = "move") -> bool:
        """Translates mobile touchscreen gestures into laptop mouse movements."""
        try:
            user32 = ctypes.windll.user32
            if action == "move":
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                user32.SetCursorPos(pt.x + int(dx), pt.y + int(dy))
                return True
            elif action == "click":
                user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
                user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
                return True
            elif action == "right_click":
                user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
                return True
            elif action == "scroll":
                user32.mouse_event(0x0800, 0, 0, int(dy * 120), 0)  # MOUSEEVENTF_WHEEL
                return True
        except Exception as e:
            print(f"[CROSS DEVICE TOUCHPAD ERROR] {e}")
        return False

    def handle_remote_control(self, action: str) -> Tuple[bool, str]:
        """Handles remote multimedia and laptop commands from LiveLink."""
        try:
            user32 = ctypes.windll.user32
            action = (action or "").lower().strip()

            # Virtual Key Constants
            VK_VOLUME_MUTE = 0xAD
            VK_VOLUME_DOWN = 0xAE
            VK_VOLUME_UP = 0xAF
            VK_MEDIA_NEXT_TRACK = 0xB0
            VK_MEDIA_PREV_TRACK = 0xB1
            VK_MEDIA_PLAY_PAUSE = 0xB3
            VK_SPACE = 0x20
            KEYEVENTF_KEYUP = 0x0002

            def press_vk(code: int):
                user32.keybd_event(code, 0, 0, 0)
                user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)

            if action in ("vol_up", "volume_up"):
                for _ in range(3):
                    press_vk(VK_VOLUME_UP)
                return True, "Laptop volume raised."
            elif action in ("vol_down", "volume_down"):
                for _ in range(3):
                    press_vk(VK_VOLUME_DOWN)
                return True, "Laptop volume lowered."
            elif action in ("mute", "toggle_mute"):
                press_vk(VK_VOLUME_MUTE)
                return True, "Laptop mute toggled."
            elif action in ("play_pause", "pause", "play"):
                press_vk(VK_MEDIA_PLAY_PAUSE)
                return True, "Media playback toggled."
            elif action in ("next", "next_track"):
                press_vk(VK_MEDIA_NEXT_TRACK)
                return True, "Next track requested."
            elif action in ("prev", "prev_track"):
                press_vk(VK_MEDIA_PREV_TRACK)
                return True, "Previous track requested."
            elif action in ("space", "play_space"):
                press_vk(VK_SPACE)
                return True, "Spacebar triggered."
            elif action in ("lock", "lock_laptop", "lock_pc"):
                user32.LockWorkStation()
                return True, "Laptop locked successfully."
            elif action in ("screenshot", "take_screenshot"):
                from commands_daily import screenshot
                res = screenshot()
                return True, res or "Screenshot captured on laptop."
            else:
                return False, f"Unknown remote action: '{action}'"
        except Exception as e:
            return False, f"Remote control error: {e}"

    def save_file_from_phone(self, filename: str, data: bytes, target_dir_type: str = "downloads") -> Tuple[bool, str]:
        """Saves a file transmitted from phone directly to laptop Downloads or Desktop."""
        if target_dir_type == "desktop":
            dest_dir = str(get_desktop_dir())
        else:
            dest_dir = str(get_downloads_dir())

        safe_name = os.path.basename(filename) or f"phone_transfer_{int(time.time())}.bin"
        target_path = os.path.join(dest_dir, safe_name)

        try:
            with open(target_path, "wb") as f:
                f.write(data)

            # Announce arrival on laptop
            try:
                from speech_engine import speak
                speak(f"LiveLink file received: {safe_name}")
            except Exception:
                pass

            return True, f"Saved '{safe_name}' directly to laptop {target_dir_type.capitalize()} folder."
        except Exception as e:
            return False, f"Failed to save file from phone: {e}"

    def list_laptop_files(self, folder_type: str = "downloads", limit: int = 40) -> List[Dict[str, Any]]:
        """Lists files on laptop (Downloads subfolders & Desktop) available for LiveLink mobile download."""
        search_dirs = []
        if folder_type == "desktop":
            search_dirs.append((str(get_desktop_dir()), "desktop"))
        else:
            downloads_dir = str(get_downloads_dir())
            search_dirs.append((downloads_dir, "downloads"))
            # Also include Desktop so user sees all prominent laptop files
            search_dirs.append((str(get_desktop_dir()), "desktop"))

        entries = []
        seen_paths = set()

        for s_dir, f_tag in search_dirs:
            if not os.path.exists(s_dir):
                continue
            try:
                # Walk up to 2 subfolder levels
                for root, dirs, files in os.walk(s_dir):
                    # Skip hidden, system, or project code dirs
                    dirs[:] = [d for d in dirs if not d.startswith((".", "~$", "node_modules", "AppData", "Windows", "__pycache__", "venv")) and d != "ULTRON"]
                    # Calculate depth
                    rel_depth = len(os.path.relpath(root, s_dir).split(os.sep))
                    if rel_depth > 2:
                        continue

                    for item in files:
                        if item.startswith((".", "~$", "desktop.ini")) or item.endswith(".lnk"):
                            continue
                        full_path = os.path.join(root, item)
                        if full_path in seen_paths or not os.path.isfile(full_path):
                            continue
                        seen_paths.add(full_path)

                        try:
                            stat = os.stat(full_path)
                            size_bytes = stat.st_size
                            if size_bytes < 1024:
                                size_str = f"{size_bytes} B"
                            elif size_bytes < 1024 * 1024:
                                size_str = f"{size_bytes / 1024:.1f} KB"
                            elif size_bytes < 1024 * 1024 * 1024:
                                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                            else:
                                size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

                            ext = os.path.splitext(item)[1].lower()
                            rel_folder = os.path.relpath(root, s_dir)
                            display_sub = "" if rel_folder == "." else f" • {rel_folder}"

                            entries.append({
                                "name": item,
                                "path": full_path,
                                "size": size_bytes,
                                "size_human": size_str,
                                "mtime": stat.st_mtime,
                                "mtime_human": time.strftime("%b %d, %H:%M", time.localtime(stat.st_mtime)) + display_sub,
                                "folder": f_tag,
                                "ext": ext,
                            })
                        except Exception:
                            continue
            except Exception as e:
                print(f"[CROSS DEVICE FILE LIST ERROR] {e}")

        # Sort by most recently modified
        entries.sort(key=lambda x: x["mtime"], reverse=True)
        return entries[:limit]

    def get_file_path(self, filename: str, folder_type: str = "downloads") -> Optional[str]:
        """Safely resolves path for a file to download, checking Downloads, subfolders, and Desktop."""
        safe_name = os.path.basename(filename)
        if not safe_name:
            return None

        search_roots = [str(get_downloads_dir()), str(get_desktop_dir())]
        for s_root in search_roots:
            if not os.path.exists(s_root):
                continue
            # Direct check
            direct = os.path.join(s_root, safe_name)
            if os.path.isfile(direct):
                return direct
            # Subdirectory search
            for root, dirs, files in os.walk(s_root):
                dirs[:] = [d for d in dirs if not d.startswith((".", "~$", "node_modules", "AppData"))]
                if safe_name in files:
                    candidate = os.path.join(root, safe_name)
                    if os.path.isfile(candidate):
                        return candidate

        return None

    def ring_phone(self) -> Tuple[bool, str]:
        """Plays an audible alarm on connected Android phone to locate it."""
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3.0)
            if "device" in res.stdout and len(res.stdout.strip().split("\n")) > 1:
                cmd = ["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "content://media/internal/audio/media/1"]
                subprocess.Popen(cmd)
                return True, "Triggering alarm on your phone, Harsha. Listen for the sound."
        except Exception:
            pass
        return False, "Could not reach phone via ADB. Ensure USB debugging is enabled, or use the mobile web interface."


cross_device_sync = CrossDeviceSync()
