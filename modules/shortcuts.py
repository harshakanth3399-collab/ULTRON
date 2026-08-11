"""
shortcuts.py - ULTRON Media Control & Workspace Shortcuts Subsystem
Native Windows Virtual Key media controls and multi-app workspace presets.
"""

from __future__ import annotations

import os
import subprocess
import time
import ctypes

# Windows VK Key Codes
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE      = 0xAD
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_UP        = 0xAF


def _press_key(vk_code: int) -> None:
    """Sends native Windows VK key press event."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


def media_play_pause() -> str:
    _press_key(VK_MEDIA_PLAY_PAUSE)
    return "Toggled media playback."


def media_next() -> str:
    _press_key(VK_MEDIA_NEXT_TRACK)
    return "Skipped to next track."


def media_previous() -> str:
    _press_key(VK_MEDIA_PREV_TRACK)
    return "Skipped to previous track."


def volume_up() -> str:
    for _ in range(3):
        _press_key(VK_VOLUME_UP)
    return "Volume increased."


def volume_down() -> str:
    for _ in range(3):
        _press_key(VK_VOLUME_DOWN)
    return "Volume decreased."


def launch_coding_workspace() -> str:
    """Launches VS Code, Command Prompt, and Chrome browser in split workspace."""
    try:
        subprocess.Popen(["code", "."], shell=True)
        subprocess.Popen(["cmd.exe", "/k", "title ULTRON Workspace"], shell=True)
        return "Python development workspace launched, Sir."
    except Exception as e:
        return f"Workspace setup note: {e}"
