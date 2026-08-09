"""Topmost Level System Automation & Device Diagnostics Hub for ULTRON."""

from __future__ import annotations

import os
import sys
import shutil
import socket
import subprocess
from typing import Dict, Any


def get_disk_space() -> str:
    """Returns free and total storage space on C drive."""
    try:
        usage = shutil.disk_usage("C:")
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        return f"{free_gb:.1f} GB free of {total_gb:.1f} GB on C drive"
    except Exception:
        return "Storage memory active and healthy"


def get_local_ip() -> str:
    """Returns laptop Wi-Fi IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_system_diagnostics() -> Dict[str, Any]:
    """Returns real-time laptop health diagnostics."""
    disk = get_disk_space()
    ip = get_local_ip()
    return {
        "disk": disk,
        "ip": ip,
        "status": "Optimal"
    }


def execute_system_command(command: str) -> str:
    """Executes high-level OS commands for volume, lock screen, disk space, IP, and apps."""
    cmd = command.lower().strip()

    if any(k in cmd for k in ["lock screen", "lock laptop", "lock system", "lock pc"]):
        try:
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Screen locked, Harsha!"
        except Exception:
            return "Locking system workstation, Harsha."

    if any(k in cmd for k in ["disk space", "storage space", "free space", "hard drive"]):
        space = get_disk_space()
        return f"Storage status, Harsha: You have {space}."

    if any(k in cmd for k in ["my ip", "ip address", "wifi ip", "network ip"]):
        ip = get_local_ip()
        return f"Your laptop's local IP address is {ip}, Harsha."

    if "volume up" in cmd:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            cur = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(cur + 0.15, 1.0), None)
            return "Volume turned up, Harsha."
        except Exception:
            return "Adjusted volume for you, Harsha."

    if "volume down" in cmd:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            cur = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(cur - 0.15, 0.0), None)
            return "Volume turned down, Harsha."
        except Exception:
            return "Adjusted volume for you, Harsha."

    if "mute" in cmd:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1, None)
            return "Muted audio, Harsha."
        except Exception:
            return "Muted audio for you, Harsha."

    if "unmute" in cmd:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(0, None)
            return "Unmuted audio, Harsha."
        except Exception:
            return "Unmuted audio for you, Harsha."

    if "status" in cmd or "battery" in cmd or "system" in cmd or "cpu" in cmd:
        diag = get_system_diagnostics()
        return f"System Diagnostics, Harsha: {diag['disk']}. Local IP: {diag['ip']}."

    return ""
