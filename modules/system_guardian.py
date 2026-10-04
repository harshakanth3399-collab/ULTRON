"""
modules/system_guardian.py - ULTRON Proactive Hardware, Battery & System Sentinel

Continuously monitors battery level, AC charging status, CPU/RAM utilization
using zero-dependency native Windows kernel32 C APIs. Proactively notifies
the user via speech before critical power or memory exhaustion occurs.
"""

from __future__ import annotations

import ctypes
import threading
import time
from typing import Dict, Optional, Tuple


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class SystemGuardian:
    """Proactive background monitor for battery, power, and system memory."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_alert_time: float = 0.0
        self._alert_cooldown: float = 300.0  # 5 minutes between proactive voice alerts

    def get_battery_info(self) -> Dict[str, Any]:
        """Reads real-time battery and power status via Windows kernel32."""
        sps = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
            ac_plugged = (sps.ACLineStatus == 1)
            percent = int(sps.BatteryLifePercent)
            if percent == 255:
                percent = -1  # Battery status unknown / desktop PC
            return {
                "plugged_in": ac_plugged,
                "percent": percent,
                "flag": sps.BatteryFlag,
            }
        return {"plugged_in": True, "percent": -1, "flag": 0}

    def get_memory_info(self) -> Dict[str, Any]:
        """Reads real-time RAM usage via Windows GlobalMemoryStatusEx."""
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total_gb = round(stat.ullTotalPhys / (1024 ** 3), 1)
            avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 1)
            used_gb = round(total_gb - avail_gb, 1)
            load_pct = int(stat.dwMemoryLoad)
            return {
                "load_percent": load_pct,
                "used_gb": used_gb,
                "total_gb": total_gb,
                "avail_gb": avail_gb,
            }
        return {"load_percent": 0, "used_gb": 0, "total_gb": 0, "avail_gb": 0}

    def get_health_report(self) -> Tuple[bool, str]:
        """Returns a natural language summary of system vitals for Harsha."""
        bat = self.get_battery_info()
        mem = self.get_memory_info()

        lines = []
        if bat["percent"] >= 0:
            status_str = "plugged in and charging" if bat["plugged_in"] else "on battery power"
            lines.append(f"Battery is at {bat['percent']}%, {status_str}.")
        else:
            lines.append("Running on steady AC wall power.")

        lines.append(f"Memory load is {mem['load_percent']}% ({mem['used_gb']} GB used out of {mem['total_gb']} GB).")

        if bat["percent"] >= 0 and bat["percent"] <= 20 and not bat["plugged_in"]:
            lines.append("Warning: Battery is low, please connect your laptop charger.")

        return True, " ".join(lines)

    def _monitor_loop(self) -> None:
        """Background daemon polling vitals every 30 seconds."""
        print("[SYSTEM GUARDIAN] Sentinel active.")
        while self._running:
            time.sleep(30)
            now = time.time()
            if now - self._last_alert_time < self._alert_cooldown:
                continue

            bat = self.get_battery_info()
            mem = self.get_memory_info()

            alert_msg = ""
            if bat["percent"] >= 0 and bat["percent"] <= 15 and not bat["plugged_in"]:
                alert_msg = f"Harsha, your laptop battery has dropped to {bat['percent']} percent. Please plug in the charger."
            elif mem["load_percent"] >= 92:
                alert_msg = f"Harsha, system memory usage is very high at {mem['load_percent']} percent. Consider closing heavy background tasks."

            if alert_msg:
                self._last_alert_time = now
                try:
                    from speech_engine import speak
                    print(f"[SYSTEM GUARDIAN PROACTIVE] {alert_msg}")
                    speak(alert_msg)
                except Exception as e:
                    print(f"[SYSTEM GUARDIAN SPEAK ERROR] {e}")

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "System Guardian is already active and monitoring your laptop."
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        return True, "System Guardian activated. Monitoring battery, thermals, and memory in the background."

    def stop(self) -> Tuple[bool, str]:
        if not self._running:
            return True, "System Guardian is not running."
        self._running = False
        return True, "System Guardian deactivated."


system_guardian = SystemGuardian()
