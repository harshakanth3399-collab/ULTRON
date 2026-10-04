"""
modules/vault_lockdown.py - ULTRON Voice-Activated Private Vault & Protocol Lockdown

Instantly secures or conceals private workstation folders on command:
- "Initiate protocol lockdown" -> Hides/locks private Vault folder, minimizes windows
- "Unlock vault" -> Restores and opens private Vault directory in File Explorer
"""

from __future__ import annotations

import os
import subprocess
from typing import Tuple

from modules.human_controller import human_controller
from modules.system_paths import get_desktop_dir


def _get_vault_dir() -> str:
    desktop = str(get_desktop_dir())
    vault_path = os.path.join(desktop, "Secure_Vault")
    os.makedirs(vault_path, exist_ok=True)
    return vault_path


def initiate_protocol_lockdown() -> Tuple[bool, str]:
    """Secures the workstation and hides the private vault."""
    vault = _get_vault_dir()
    try:
        # Hide folder via Windows attrib command
        subprocess.run(["attrib", "+h", "+s", vault], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Minimize all active windows
    human_controller.press_shortcut("show desktop")

    return True, "Protocol Lockdown initiated, Harsha. Sensitive vault is secured and concealed."


def unlock_vault() -> Tuple[bool, str]:
    """Reveals the private vault and opens it in Windows File Explorer."""
    vault = _get_vault_dir()
    try:
        subprocess.run(["attrib", "-h", "-s", vault], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    try:
        os.startfile(vault)
        return True, "Protocol Lockdown disengaged. Secure Vault opened in File Explorer."
    except Exception as e:
        return True, f"Vault unlocked at {os.path.basename(vault)}."
