"""
modules/adb_bridge.py - ULTRON Wireless ADB Phone Control & Persistent Wi-Fi Bridge

Allows ULTRON to wirelessly control your Android smartphone via ADB (Android Debug Bridge) over local Wi-Fi:
  - Persistent background auto-reconnect
  - Real-time phone battery level & charging status
  - Phone app launching (Instagram, WhatsApp, YouTube, Camera, Settings)
  - Phone key events (Home, Back, Lock, Volume)
  - Remote phone screenshot capture
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import threading
import time
from typing import Optional


class ADBBridge:
    """Persistent Wireless ADB Connection Manager & Phone Controller."""

    def __init__(self, default_port: int = 5555) -> None:
        self.port = default_port
        self.connected_ip: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _run_adb(self, *args: str) -> str:
        """Executes an adb command line and returns clean stdout output."""
        cmd = ["adb"] + list(args)
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=8.0, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return res.stdout.strip()
        except Exception as e:
            return f"ADB Error: {e}"

    def get_connected_devices(self) -> list[str]:
        """Returns list of currently connected ADB device identifiers."""
        out = self._run_adb("devices")
        devices = []
        for line in out.splitlines():
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])
        return devices

    def connect_phone(self, phone_ip: Optional[str] = None) -> tuple[bool, str]:
        """Connects to Android phone over Wi-Fi ADB on port 5555."""
        if not phone_ip:
            # Auto-detect subnet IP if not specified
            phone_ip = self._find_phone_ip()

        if not phone_ip:
            return False, "Could not auto-detect phone IP. Please specify your phone's Wi-Fi IP address."

        out = self._run_adb("connect", f"{phone_ip}:{self.port}")
        if "connected" in out.lower():
            self.connected_ip = phone_ip
            self._start_persistent_keepalive()
            return True, f"Successfully connected wirelessly to your phone at {phone_ip}:{self.port}!"
        
        # Check if already connected via USB/Wi-Fi
        devices = self.get_connected_devices()
        if devices:
            self.connected_ip = devices[0]
            self._start_persistent_keepalive()
            return True, f"Connected to device {devices[0]} via ADB."

        return False, f"ADB Connection response: '{out}'. Ensure Wireless Debugging is ON on your phone."

    def _find_phone_ip(self) -> Optional[str]:
        """Attempts to discover phone IP on local subnet."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            laptop_ip = s.getsockname()[0]
            s.close()

            subnet = ".".join(laptop_ip.split(".")[:3])
            # Quick probe common phone IP slots on subnet
            for i in [100, 101, 102, 103, 104, 105, 150, 2, 3, 4, 5]:
                target = f"{subnet}.{i}"
                out = self._run_adb("connect", f"{target}:{self.port}")
                if "connected" in out.lower():
                    return target
        except Exception:
            pass
        return None

    def _start_persistent_keepalive(self) -> None:
        """Maintains persistent connection in background."""
        if self._running:
            return
        self._running = True

        def _keepalive_loop():
            while self._running:
                time.sleep(30)
                if self.connected_ip:
                    devs = self.get_connected_devices()
                    if not devs or not any(self.connected_ip in d for d in devs):
                        print(f"[ADB] Connection lost. Reconnecting to {self.connected_ip}...")
                        self._run_adb("connect", f"{self.connected_ip}:{self.port}")

        self._thread = threading.Thread(target=_keepalive_loop, daemon=True, name="ADB-KeepAlive")
        self._thread.start()

    # ── Phone Action Methods ──────────────────────────────────────────────────

    def get_battery_level(self) -> str:
        """Queries real-time battery percentage from Android phone."""
        out = self._run_adb("shell", "dumpsys", "battery")
        level_match = re.search(r"level:\s*(\d+)", out)
        status_match = re.search(r"status:\s*(\d+)", out)

        if level_match:
            pct = level_match.group(1)
            is_charging = status_match and status_match.group(1) in ("2", "5")
            chg_str = " (Charging ⚡)" if is_charging else " (On Battery)"
            return f"Your phone battery is at {pct}%{chg_str}, Harsha!"
        return "Couldn't read phone battery. Ensure Wireless Debugging ADB is connected."

    def press_key(self, key: str) -> str:
        """Sends key event to phone (home, back, power, volume_up, volume_down)."""
        keys = {
            "home": "3",
            "back": "4",
            "power": "26",
            "volume_up": "24",
            "volume_down": "25",
            "play_pause": "85",
        }
        code = keys.get(key.lower().strip(), "3")
        self._run_adb("shell", "input", "keyevent", code)
        return f"Executed {key} keypress on your phone, bro."

    def open_app(self, app_name: str) -> str:
        """Launches requested Android application on phone."""
        packages = {
            "instagram": "com.instagram.android",
            "whatsapp": "com.whatsapp",
            "youtube": "com.google.android.youtube",
            "chrome": "com.android.chrome",
            "spotify": "com.spotify.music",
            "settings": "com.android.settings",
            "camera": "com.android.camera",
        }
        pkg = packages.get(app_name.lower().strip())
        if pkg:
            self._run_adb("shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
            return f"Launched {app_name.capitalize()} on your smartphone, Harsha!"
        
        # Generic launcher attempt
        self._run_adb("shell", "input", "keyevent", "3")
        return f"Attempted to open {app_name} on your phone."

    def take_screenshot(self, save_path: str = "phone_screenshot.png") -> str:
        """Captures phone screen and saves to laptop."""
        self._run_adb("shell", "screencap", "-p", "/sdcard/screen.png")
        self._run_adb("pull", "/sdcard/screen.png", save_path)
        return f"Phone screenshot captured and saved to {save_path}, Harsha!"


# Global Singleton
adb_bridge = ADBBridge()
