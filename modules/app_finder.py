"""
modules/app_finder.py - Dynamic Windows Application & Shortcut Discovery Engine
Scans Windows Start Menu shortcuts (.lnk) and Registry App Paths to launch ANY installed application dynamically.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import time
from typing import Dict, Optional, Tuple


class DynamicAppFinder:
    """Discovers and caches all installed Windows applications for dynamic launching."""

    def __init__(self) -> None:
        self.apps_cache: Dict[str, str] = {}
        self.last_scan_time: float = 0.0
        self.refresh_index()

    def refresh_index(self) -> None:
        """Scans Start Menu folders and populates the dynamic app dictionary."""
        start_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs"),
        ]

        new_cache: Dict[str, str] = {}

        for d in start_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        app_name = f[:-4].lower().strip()
                        # Ignore unhelpful uninstallation/help shortcuts
                        if any(skip in app_name for skip in ["uninstall", "help", "readme", "website", "documentation"]):
                            continue
                        # Clean up punctuation
                        clean_name = re.sub(r"[^\w\s]", "", app_name).strip()
                        if clean_name and clean_name not in new_cache:
                            new_cache[clean_name] = os.path.join(root, f)
                            new_cache[app_name] = os.path.join(root, f)

        self.apps_cache = new_cache
        self.last_scan_time = time.time()
        print(f"[APP FINDER] Indexed {len(self.apps_cache)} dynamic Windows application shortcuts.")

    def find_app(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Fuzzy matches a user query against discovered app names.
        Returns (matched_app_name, shortcut_or_exe_path) or None.
        """
        raw_target = re.sub(r"^(open|launch|start|go to|visit)\s+", "", query.lower().strip()).strip()
        raw_target = re.sub(r"[^\w\s]", "", raw_target).strip()

        if not raw_target:
            return None

        # 1. Exact match
        if raw_target in self.apps_cache:
            return raw_target, self.apps_cache[raw_target]

        # 2. Match starting with query word
        for app_name, path in self.apps_cache.items():
            if app_name.startswith(raw_target) or raw_target.startswith(app_name):
                return app_name, path

        # 3. Substring match
        for app_name, path in self.apps_cache.items():
            if raw_target in app_name:
                return app_name, path

        return None

    def launch(self, query: str) -> Tuple[bool, str]:
        """
        Finds and launches the requested application dynamically.
        """
        match = self.find_app(query)
        if not match:
            return False, f"Could not find installed application matching '{query}'."

        app_name, path = match
        display_name = app_name.title()
        print(f"[APP FINDER] Dynamic match found: '{query}' -> '{display_name}' ({path})")

        try:
            os.startfile(path)
            time.sleep(1.0)
            return True, f"{display_name} launched successfully."
        except Exception as e:
            try:
                subprocess.Popen(f'start "" "{path}"', shell=True)
                time.sleep(1.0)
                return True, f"{display_name} launched."
            except Exception as ex:
                print(f"[APP FINDER ERROR] Failed to launch '{path}': {ex}")
                return False, f"Failed to launch {display_name}."


# Global Singleton
app_finder = DynamicAppFinder()
