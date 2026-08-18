"""
modules/file_search.py - Fast Local Personal File & Document Search Engine
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple


def search_local_files(query: str, max_results: int = 5) -> Tuple[bool, str, List[str]]:
    """
    Searches user's Desktop, Documents, Downloads, and Workspace directories for files matching query.
    Returns (success, message, file_paths).
    """
    clean_query = re.sub(r"^(find|search|look for|where is|locate)\s+(file|pdf|document|script)?\s*", "", query.lower().strip()).strip()
    clean_query = re.sub(r"[^\w\s\.-]", "", clean_query).strip()

    if not clean_query:
        return False, "Please specify a file name or extension to search.", []

    user_home = os.path.expanduser("~")
    search_dirs = [
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Downloads"),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ]

    matches: List[str] = []

    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d):
            # Skip hidden and cache folders
            dirs[:] = [sub for sub in dirs if not sub.startswith((".", "__")) and sub not in ["node_modules", ".venv", "site-packages"]]
            for f in files:
                if clean_query in f.lower():
                    matches.append(os.path.join(root, f))
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                break
        if len(matches) >= max_results:
            break

    if matches:
        basenames = [os.path.basename(m) for m in matches]
        names_str = ", ".join(basenames[:3])
        print(f"[FILE SEARCH] Found {len(matches)} files matching '{clean_query}': {names_str}")
        return True, f"Found {len(matches)} matching file{'s' if len(matches) > 1 else ''}: {names_str}.", matches
    else:
        return False, f"Could not find any files matching '{clean_query}'.", []
