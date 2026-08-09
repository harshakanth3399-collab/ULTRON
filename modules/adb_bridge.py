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


def _get_adb_executable() -> str:
    """Returns path to adb executable, preferring local bundled tools/platform-tools/adb.exe."""
    local_adb = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "platform-tools", "adb.exe")
    if os.path.exists(local_adb):
        return local_adb
    return "adb"


class ADBBridge:
    """Persistent Wireless ADB Connection Manager & Phone Controller."""

    def __init__(self, default_port: int = 5555) -> None:
        self.port = default_port
        self.connected_ip: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _run_adb(self, *args: str) -> str:
        """Executes an adb command line and returns clean stdout output."""
        adb_exe = _get_adb_executable()
        cmd = [adb_exe] + list(args)
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=8.0, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return res.stdout.strip()
        except Exception as e:
            return f"ADB Error: {e}"


    def get_connected_devices(self) -> tuple[list[str], bool]:
        """Returns list of currently connected ADB device identifiers and authorization status."""
        out = self._run_adb("devices")
        if "daemon not running" in out or not out:
            self._run_adb("kill-server")
            self._run_adb("start-server")
            out = self._run_adb("devices")

        devices = []
        is_unauthorized = False
        for line in out.splitlines():
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])
            elif "\tunauthorized" in line:
                is_unauthorized = True

        return devices, is_unauthorized

    def connect_phone(self, phone_ip: Optional[str] = None) -> tuple[bool, str]:
        """Connects to Android phone via USB Debugging or Wi-Fi ADB on port 5555."""
        # 1. Check if device is connected via USB Debugging cable
        devices, is_unauthorized = self.get_connected_devices()

        if is_unauthorized:
            return False, "Phone detected via USB! Unlock your phone and tap 'ALWAYS ALLOW USB DEBUGGING' on your phone screen."

        if devices:
            # Enable Wireless ADB port 5555 automatically on the USB device!
            self._run_adb("tcpip", str(self.port))
            self.connected_ip = devices[0]
            self._start_persistent_keepalive()
            return True, f"USB Debugging detected! Activated Wireless ADB on port {self.port}. Your phone is now fully connected to ULTRON!"

        # 2. If phone_ip specified or auto-discovered over Hotspot / Wi-Fi
        if not phone_ip:
            phone_ip = self._find_phone_ip()

        if phone_ip:
            out = self._run_adb("connect", f"{phone_ip}:{self.port}")
            if "connected" in out.lower() or "already" in out.lower():
                self.connected_ip = phone_ip
                self._start_persistent_keepalive()
                return True, f"Successfully connected wirelessly to your phone at {phone_ip}:{self.port}!"

        return False, (
            "No phone detected yet, Harsha. Please check these 3 steps on your phone:\n"
            "1. Unlock your phone screen -> pull down notification shade -> change USB mode from 'Charging' to 'File Transfer (MTP)'.\n"
            "2. Ensure 'USB Debugging' is turned ON in Developer Options.\n"
            "3. Look for a popup on your phone screen asking 'Allow USB Debugging?' and tap ALLOW!"
        )



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
                    devs, _ = self.get_connected_devices()

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
            "gallery": "com.google.android.apps.photos",
            "photos": "com.google.android.apps.photos",
            "maps": "com.google.android.apps.maps",
        }
        name_clean = app_name.lower().strip()
        pkg = packages.get(name_clean)
        if pkg:
            self._run_adb("shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
            return f"Opening {app_name.capitalize()} on your smartphone screen right now, Harsha!"

        
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
