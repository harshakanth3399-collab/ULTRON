"""
modules/livelink_stream.py - ULTRON LiveLink Low-Latency Event Stream & Telemetry Hub

Provides Server-Sent Events (SSE) streaming for real-time, low-latency (<10ms) synchronization:
1. Zero-delay Gatekeeper Approval broadcast (phone unlocks instantly when Harsha approves)
2. Instant Bi-directional Clipboard Sync
3. File transfer alerts & progress
4. Hardware Telemetry Broadcast (Laptop Battery %, AC status, RAM usage)
"""

from __future__ import annotations

import ctypes
import json
import queue
import threading
import time
from typing import Any, Dict, Set


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


class LiveLinkStreamHub:
    """Central real-time event router for LiveLink clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clients: Set[queue.Queue] = set()
        self._running = True
        self._telemetry_thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        self._telemetry_thread.start()

    def add_client(self) -> queue.Queue:
        """Subscribes an SSE connection to live events."""
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._clients.add(q)
        # Immediately push initial telemetry state
        init_telemetry = self.get_system_telemetry()
        q.put({"event": "system_telemetry", "data": init_telemetry})
        return q

    def remove_client(self, q: queue.Queue) -> None:
        """Unsubscribes a client on disconnect."""
        with self._lock:
            self._clients.discard(q)

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Dispatches an event payload to all connected LiveLink devices."""
        payload = {"event": event_type, "data": data}
        with self._lock:
            active_clients = list(self._clients)

        for q in active_clients:
            try:
                q.put_nowait(payload)
            except (queue.Full, Exception):
                pass

    def notify_approval(self, token: str, name: str, status: str) -> None:
        """Broadcasts authorization change so pending devices unlock instantly."""
        self.broadcast("approval_event", {
            "token": token,
            "name": name,
            "status": status,
            "timestamp": time.time(),
        })

    def notify_clipboard(self, text: str) -> None:
        """Broadcasts clipboard change to mobile devices."""
        self.broadcast("clipboard_sync", {
            "text": text,
            "timestamp": time.time(),
        })

    def notify_file_event(self, filename: str, action: str, folder: str = "downloads") -> None:
        """Broadcasts file transfer arrival or completion."""
        self.broadcast("file_event", {
            "filename": filename,
            "action": action,
            "folder": folder,
            "timestamp": time.time(),
        })

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Reads native Windows battery, power, and memory metrics with zero overhead."""
        telemetry: Dict[str, Any] = {
            "battery_percent": 100,
            "plugged_in": True,
            "ram_load_percent": 0,
            "ram_avail_gb": 0.0,
            "timestamp": time.time(),
        }

        try:
            sps = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
                pct = int(sps.BatteryLifePercent)
                telemetry["battery_percent"] = pct if pct <= 100 else 100
                telemetry["plugged_in"] = (sps.ACLineStatus == 1)
        except Exception:
            pass

        try:
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                telemetry["ram_load_percent"] = int(stat.dwMemoryLoad)
                telemetry["ram_avail_gb"] = round(stat.ullAvailPhys / (1024 ** 3), 1)
        except Exception:
            pass

        return telemetry

    def _telemetry_worker(self) -> None:
        """Pushes periodic telemetry heartbeat every 5 seconds to all connected phones."""
        while self._running:
            time.sleep(5.0)
            if self._clients:
                telemetry = self.get_system_telemetry()
                self.broadcast("system_telemetry", telemetry)


# Global Singleton
livelink_stream_hub = LiveLinkStreamHub()
