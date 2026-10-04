"""
modules/system_paths.py - Canonical Windows User Shell Folders Resolver

Reliably resolves actual paths for Desktop, Documents, Downloads, even when
nested under OneDrive folder redirection, using the Windows Registry.
"""

import os
import winreg
from pathlib import Path


def get_desktop_dir() -> Path:
    """Returns the user's real Desktop directory path."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        expanded = os.path.expandvars(val)
        if os.path.exists(expanded):
            return Path(expanded)
    except Exception:
        pass

    # Fallback to parent of ULTRON if it matches Desktop
    curr = Path(__file__).resolve()
    for parent in curr.parents:
        if parent.name.lower() == "desktop" and parent.exists():
            return parent

    fallback = Path.home() / "Desktop"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_downloads_dir() -> Path:
    """Returns the user's real Downloads directory path."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        )
        val, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
        expanded = os.path.expandvars(val)
        if os.path.exists(expanded):
            return Path(expanded)
    except Exception:
        pass

    fallback = Path.home() / "Downloads"
    if fallback.exists():
        return fallback
    return Path.home()


def get_documents_dir() -> Path:
    """Returns the user's real Documents directory path."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        )
        val, _ = winreg.QueryValueEx(key, "Personal")
        expanded = os.path.expandvars(val)
        if os.path.exists(expanded):
            return Path(expanded)
    except Exception:
        pass

    fallback = Path.home() / "Documents"
    return fallback if fallback.exists() else Path.home()
