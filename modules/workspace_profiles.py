"""
modules/workspace_profiles.py - ULTRON Contextual Workspace Profiles (God-Mode Presets)

Orchestrates multi-application setups in a single command:
- Study / Coding Mode: VS Code + Documentation + Lo-Fi Beats + Clean Snapping
- Work Mode: Inbox + Desktop Cleanup + Focus Environment
- Chill Mode: Relaxing Music + Entertainment + Minimized Editors
- Gaming Mode: RAM Purge + High-Priority Optimization
"""

from __future__ import annotations

import os
import subprocess
import time
import webbrowser
from typing import Tuple

from modules.human_controller import human_controller
from modules.self_optimizer import self_optimizer
from modules.voice_dj import play_music


def activate_study_mode() -> Tuple[bool, str]:
    """Sets up optimal coding & deep study environment."""
    # 1. Launch VS Code in current workspace
    try:
        subprocess.Popen(["code", "."], shell=True)
    except Exception:
        pass

    # 2. Play lo-fi background beats
    play_music("lofi study beats to focus and relax")

    # 3. Open helpful documentation
    webbrowser.open("https://github.com/harshakanth3399-collab/ULTRON")

    return True, "Study Mode activated. VS Code launched, documentation opened, and focus beats streaming."


def activate_work_mode() -> Tuple[bool, str]:
    """Sets up professional productivity workspace."""
    # 1. Open Gmail / Inbox
    webbrowser.open("https://mail.google.com")

    # 2. Organize Desktop cleanly
    try:
        from modules.folder_organizer import clean_desktop
        clean_desktop()
    except Exception:
        pass

    # 3. Snap windows
    try:
        from modules.window_snapper import split_screen
        split_screen()
    except Exception:
        pass

    return True, "Work Mode activated. Inbox opened, desktop organized, and workspace aligned."


def activate_chill_mode() -> Tuple[bool, str]:
    """Switches laptop into relaxed entertainment mode."""
    # 1. Minimize coding windows
    human_controller.press_shortcut("show desktop")
    time.sleep(0.5)

    # 2. Play chill music
    play_music("best chill synthwave relax music")

    return True, "Chill Mode activated. Windows minimized and relaxing music queued."


def activate_gaming_mode() -> Tuple[bool, str]:
    """Optimizes system resources and closes distractions for maximum performance."""
    # 1. Free process and system RAM
    self_optimizer.optimize_memory()

    # 2. Minimize non-gaming background apps
    human_controller.press_shortcut("show desktop")

    return True, "Gaming Mode activated. Memory purged and background windows minimized for peak performance."


def dispatch_profile(command: str) -> Tuple[bool, str]:
    """Routes voice profile requests."""
    cmd = command.lower()
    if any(k in cmd for k in ["study mode", "coding mode", "developer mode"]):
        return activate_study_mode()
    elif any(k in cmd for k in ["work mode", "office mode", "productivity mode"]):
        return activate_work_mode()
    elif any(k in cmd for k in ["chill mode", "relax mode", "movie mode", "music mode"]):
        return activate_chill_mode()
    elif any(k in cmd for k in ["gaming mode", "game mode", "turbo mode"]):
        return activate_gaming_mode()
    return False, "Unknown workspace profile."
