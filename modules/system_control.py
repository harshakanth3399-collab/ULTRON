"""
modules/system_control.py - Native Windows OS Hardware & Media Control Engine
Zero-dependency, sub-millisecond system telemetry (RAM, Battery) and Virtual Key media controls.
"""

from __future__ import annotations

import ctypes
from typing import Optional, Tuple

# ── Windows Virtual Key Codes ──────────────────────────────────────────────────
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3


def _send_vk(code: int) -> None:
    """Dispatches a Windows Virtual Key down/up event via user32."""
    ctypes.windll.user32.keybd_event(code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(code, 0, 2, 0)


# ── System Telemetry (RAM & Battery) ──────────────────────────────────────────
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength', ctypes.c_ulong),
        ('dwMemoryLoad', ctypes.c_ulong),
        ('ullTotalPhys', ctypes.c_ulonglong),
        ('ullAvailPhys', ctypes.c_ulonglong),
        ('ullTotalPageFile', ctypes.c_ulonglong),
        ('ullAvailPageFile', ctypes.c_ulonglong),
        ('ullTotalVirtual', ctypes.c_ulonglong),
        ('ullAvailVirtual', ctypes.c_ulonglong),
        ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
    ]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', ctypes.c_ubyte),
        ('BatteryFlag', ctypes.c_ubyte),
        ('BatteryLifePercent', ctypes.c_ubyte),
        ('SystemStatusFlag', ctypes.c_ubyte),
        ('BatteryLifeTime', ctypes.c_ulong),
        ('BatteryFullLifeTime', ctypes.c_ulong),
    ]


def get_memory_status() -> Tuple[int, int, int]:
    """Returns (ram_percent, used_mb, total_mb) via Windows C API."""
    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))

    total_mb = int(mem.ullTotalPhys // (1024 * 1024))
    avail_mb = int(mem.ullAvailPhys // (1024 * 1024))
    used_mb = total_mb - avail_mb
    ram_percent = int(mem.dwMemoryLoad)

    return ram_percent, used_mb, total_mb


def get_battery_status() -> Tuple[Optional[int], bool]:
    """Returns (battery_percent, is_plugged_in) via Windows C API."""
    status = SYSTEM_POWER_STATUS()
    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        percent = int(status.BatteryLifePercent) if status.BatteryLifePercent <= 100 else None
        plugged = status.ACLineStatus == 1
        return percent, plugged
    return None, False


# ── OS Control Handlers ───────────────────────────────────────────────────────
def control_volume(action: str) -> str:
    """Adjusts Windows system volume."""
    act = action.lower().strip()
    if "up" in act:
        for _ in range(5):
            _send_vk(VK_VOLUME_UP)
        return "Increased system volume."
    elif "down" in act:
        for _ in range(5):
            _send_vk(VK_VOLUME_DOWN)
        return "Decreased system volume."
    elif "mute" in act or "unmute" in act:
        _send_vk(VK_VOLUME_MUTE)
        return "Toggled system mute."
    return "Volume command processed."


def control_media(action: str) -> str:
    """Controls media playback (play/pause/next/previous)."""
    act = action.lower().strip()
    if any(k in act for k in ["pause", "play", "resume"]):
        _send_vk(VK_MEDIA_PLAY_PAUSE)
        return "Toggled media playback."
    elif "next" in act:
        _send_vk(VK_MEDIA_NEXT_TRACK)
        return "Skipped to next track."
    elif any(k in act for k in ["previous", "prev", "back"]):
        _send_vk(VK_MEDIA_PREV_TRACK)
        return "Returned to previous track."
    return "Media control command processed."
