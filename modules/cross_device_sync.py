"""
modules/cross_device_sync.py - ULTRON Mobile Phone & Laptop Cross-Device Synergy Engine

Unifies mobile phone and laptop into a single cohesive Jarvis workstation:
- Bi-directional instant clipboard synchronization (Phone <-> Laptop)
- Wireless mobile touchpad & presentation remote (mouse move, click, scroll)
- Remote phone battery sentinel & "Find My Phone" ringer via ADB
- Instant Phone-to-Laptop AirDrop file receiver
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Dict, Optional, Tuple

from modules.human_controller import human_controller
from modules.smart_clipboard import smart_clipboard
from modules.system_paths import get_downloads_dir


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
            import ctypes
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

    def save_file_from_phone(self, filename: str, data: bytes) -> Tuple[bool, str]:
        """Saves a file transmitted from phone directly to laptop Downloads folder."""
        dest_dir = str(get_downloads_dir())
        safe_name = os.path.basename(filename) or f"phone_transfer_{int(time.time())}.bin"
        target_path = os.path.join(dest_dir, safe_name)

        try:
            with open(target_path, "wb") as f:
                f.write(data)
            return True, f"Saved '{safe_name}' from your phone directly to Downloads."
        except Exception as e:
            return False, f"Failed to save file from phone: {e}"

    def ring_phone(self) -> Tuple[bool, str]:
        """Plays an audible alarm on connected Android phone to locate it."""
        try:
            # Check ADB devices
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3.0)
            if "device" in res.stdout and len(res.stdout.strip().split("\n")) > 1:
                # Dispatch alarm tone intent via ADB
                cmd = ["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "content://media/internal/audio/media/1"]
                subprocess.Popen(cmd)
                return True, "Triggering alarm on your phone, Harsha. Listen for the sound."
        except Exception:
            pass
        return False, "Could not reach phone via ADB. Ensure USB debugging is enabled, or use the mobile web interface."


cross_device_sync = CrossDeviceSync()
