"""
focus_mode.py - ULTRON Study Zone DND & Contact Filter Subsystem
Manages "Keep Steady Environment" (Serious Study Zone) and "Study Zone" modes.
Sends DND / call filter commands via ADB phone bridge and updates local profile memory.
"""

from __future__ import annotations

import os
import json
from typing import Dict, List, Tuple
from modules.memory.profile_manager import get_profile_manager

MODE_NORMAL = "NORMAL"
MODE_SERIOUS_STUDY = "SERIOUS_STUDY"  # "keep steady environment" / "serious study zone"
MODE_STUDY_ZONE = "STUDY_ZONE"        # "just study zone" / "study zone"

ALLOWED_SERIOUS_STUDY = ["mom", "mother", "amma"]
ALLOWED_STUDY_ZONE = ["mom", "mother", "amma", "harsha", "ashok", "bharat"]


def set_focus_mode(mode: str) -> Tuple[str, str]:
    """
    Activates the specified focus mode, updates profile.json,
    sends ADB commands to set phone DND, and returns (mode, status_msg).
    """
    pm = get_profile_manager()
    pref_address = pm.data.get("preferences", {}).get("preferred_address", "Sir")

    mode_upper = mode.upper()
    if "SERIOUS" in mode_upper or "STEADY" in mode_upper or "KEEP_STUDY" in mode_upper:
        current_mode = MODE_SERIOUS_STUDY
        allowed = ALLOWED_SERIOUS_STUDY
        msg = f"Serious study zone activated, {pref_address}. Notifications muted. Only Amma can reach you now."

    elif "STUDY" in mode_upper:
        current_mode = MODE_STUDY_ZONE
        allowed = ALLOWED_STUDY_ZONE
        msg = f"Study zone activated, {pref_address}. Calls allowed from Amma, Harsha, Ashok, and Bharat."
    else:
        current_mode = MODE_NORMAL
        allowed = ["ALL"]
        msg = f"Study zone ended, {pref_address}. Normal notification mode restored."

    # Update local profile preference
    pm.set_preference("focus_mode", current_mode)
    pm.set_preference("focus_allowed_contacts", allowed)

    # Trigger ADB phone DND configuration if ADB is connected
    try:
        from modules.adb_bridge import run_adb
        if current_mode == MODE_NORMAL:
            run_adb(["shell", "settings", "put", "global", "zen_mode", "0"])
        else:
            # Set phone DND to Priority Only (zen_mode 1)
            run_adb(["shell", "settings", "put", "global", "zen_mode", "1"])
    except Exception as e:
        print(f"[FOCUS MODE NOTE] Phone ADB sync status: {e}")

    print(f"[FOCUS MODE] Mode locked to: {current_mode} | Allowed Contacts: {allowed}")
    return current_mode, msg


def get_focus_mode() -> Tuple[str, List[str]]:
    """Returns current active focus mode and allowed contact whitelist."""
    pm = get_profile_manager()
    mode = pm.data.get("preferences", {}).get("focus_mode", MODE_NORMAL)
    allowed = pm.data.get("preferences", {}).get("focus_allowed_contacts", ["ALL"])
    return mode, allowed


def is_contact_allowed(contact_name: str) -> bool:
    """Checks if incoming contact is permitted in the active focus mode."""
    mode, allowed = get_focus_mode()
    if mode == MODE_NORMAL or "ALL" in allowed:
        return True

    name_lower = contact_name.lower().strip()
    for allowed_name in allowed:
        if allowed_name in name_lower or name_lower in allowed_name:
            return True
    return False
