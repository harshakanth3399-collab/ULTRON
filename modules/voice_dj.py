"""
modules/voice_dj.py - ULTRON Background Voice DJ & Media Controller

Plays songs, lo-fi beats, and soundtracks. Directly manipulates system media
controls (Play, Pause, Skip, Volume) via native Windows Win32 virtual key events.
"""

from __future__ import annotations

import ctypes
import re
import urllib.parse
import webbrowser
from typing import Tuple

user32 = ctypes.windll.user32

# Win32 Virtual Key Codes for Multimedia
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

KEYEVENTF_KEYUP = 0x0002


def _send_media_key(vk_code: int) -> None:
    user32.keybd_event(vk_code, 0, 0, 0)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def play_music(query: str) -> Tuple[bool, str]:
    """Searches and starts music playback on YouTube or system."""
    clean_q = re.sub(r"^(?:play|start|put\s+on|stream)\s+(?:music|song|track)?\s*", "", query.lower().strip()).strip()
    if not clean_q:
        clean_q = "lofi hip hop radio beats to relax"

    encoded = urllib.parse.quote(clean_q)
    # YouTube search & autoplay first result
    url = f"https://www.youtube.com/results?search_query={encoded}"

    try:
        from commands import play_youtube
        ok, msg = play_youtube(clean_q)
        if ok:
            return True, msg
    except Exception:
        pass

    try:
        webbrowser.open(url)
        return True, f"Now playing {clean_q}."
    except Exception as e:
        return False, f"Could not launch music: {e}"


def toggle_play_pause() -> Tuple[bool, str]:
    _send_media_key(VK_MEDIA_PLAY_PAUSE)
    return True, "Toggled media playback."


def next_track() -> Tuple[bool, str]:
    _send_media_key(VK_MEDIA_NEXT_TRACK)
    return True, "Skipped to next track."


def prev_track() -> Tuple[bool, str]:
    _send_media_key(VK_MEDIA_PREV_TRACK)
    return True, "Went back to previous track."


def volume_up() -> Tuple[bool, str]:
    for _ in range(5):
        _send_media_key(VK_VOLUME_UP)
    return True, "Volume increased."


def volume_down() -> Tuple[bool, str]:
    for _ in range(5):
        _send_media_key(VK_VOLUME_DOWN)
    return True, "Volume decreased."
