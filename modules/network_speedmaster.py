"""
modules/network_speedmaster.py - ULTRON Network Speedmaster & Wi-Fi Controller

Measures real-time network latency, ping to DNS servers, Wi-Fi SSID, and signal
strength using native Windows netsh and socket pinging without external web bloat.
"""

from __future__ import annotations

import re
import socket
import subprocess
import time
from typing import Dict, Tuple


def get_network_diagnostics() -> Tuple[bool, str]:
    """Measures latency and active Wi-Fi profile info."""
    t0 = time.time()
    latency_ms = -1
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("8.8.8.8", 53))
        s.close()
        latency_ms = int((time.time() - t0) * 1000)
    except Exception:
        pass

    # Read Wi-Fi profile and signal via Windows netsh
    ssid = "Ethernet / Hotspot"
    signal = ""
    try:
        out = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=3.0).stdout
        m_ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
        if m_ssid:
            ssid = m_ssid.group(1).strip()
        m_sig = re.search(r"^\s*Signal\s*:\s*(.+)$", out, re.MULTILINE)
        if m_sig:
            signal = m_sig.group(1).strip()
    except Exception:
        pass

    if latency_ms >= 0:
        sig_str = f" with {signal} signal strength" if signal else ""
        return True, f"Network connection is stable on '{ssid}'{sig_str}. Ping latency is {latency_ms} milliseconds."
    else:
        return False, "Workstation is currently disconnected from the internet, Harsha."
