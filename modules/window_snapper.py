"""
modules/window_snapper.py - ULTRON Smart Window Snapping & Split-Screen Multi-Tasking Engine

Enables hands-free desktop window arrangement:
  - Snap Left (Win + Left Arrow)
  - Snap Right (Win + Right Arrow)
  - Maximize (Win + Up Arrow)
  - Tile / Split-Screen
"""

from __future__ import annotations

import ctypes
import time
from typing import Tuple

user32 = ctypes.windll.user32

VK_LWIN = 0x5B
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_UP = 0x26
VK_DOWN = 0x28


def _send_win_combo(vk_key: int) -> None:
    user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(vk_key, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk_key, 0, 2, 0)
    time.sleep(0.04)
    user32.keybd_event(VK_LWIN, 0, 2, 0)


def snap_left() -> Tuple[bool, str]:
    """Snaps the active foreground window to the left half of the display."""
    _send_win_combo(VK_LEFT)
    return True, "Snapped active window to the left."


def snap_right() -> Tuple[bool, str]:
    """Snaps the active foreground window to the right half of the display."""
    _send_win_combo(VK_RIGHT)
    return True, "Snapped active window to the right."


def maximize_window() -> Tuple[bool, str]:
    _send_win_combo(VK_UP)
    return True, "Maximized active window."


def split_screen() -> Tuple[bool, str]:
    """Tiles the two most recent windows side-by-side."""
    # Snap current window to left
    _send_win_combo(VK_LEFT)
    time.sleep(0.2)
    # Switch to previous window (Alt+Tab) and snap to right
    user32.keybd_event(0x12, 0, 0, 0)   # Alt
    user32.keybd_event(0x09, 0, 0, 0)   # Tab
    time.sleep(0.05)
    user32.keybd_event(0x09, 0, 2, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.25)
    _send_win_combo(VK_RIGHT)
    return True, "Arranged your workspace in split-screen mode, Harsha."
