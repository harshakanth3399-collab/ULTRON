"""
modules/window_manager.py - Native Windows Desktop Window Management Engine
"""

from __future__ import annotations

import ctypes
import time

VK_LWIN = 0x5B
VK_D = 0x44
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9


def _send_key_combo(vk1: int, vk2: int) -> None:
    """Dispatches a key combo press."""
    user32 = ctypes.windll.user32
    user32.keybd_event(vk1, 0, 0, 0)
    user32.keybd_event(vk2, 0, 0, 0)
    user32.keybd_event(vk2, 0, 2, 0)
    user32.keybd_event(vk1, 0, 2, 0)


def minimize_all_windows() -> str:
    """Toggles desktop view / minimizes all windows."""
    print("[WINDOW MANAGER] Minimizing all windows (Show Desktop)...")
    _send_key_combo(VK_LWIN, VK_D)
    return "Minimized all open windows."


def minimize_active_window() -> str:
    """Minimizes the currently active foreground window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            return "Minimized active window."
    except Exception as e:
        print(f"[WINDOW MANAGER ERROR] {e}")
    return "Could not minimize window."


def maximize_active_window() -> str:
    """Maximizes the currently active foreground window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            return "Maximized active window."
    except Exception as e:
        print(f"[WINDOW MANAGER ERROR] {e}")
    return "Could not maximize window."
