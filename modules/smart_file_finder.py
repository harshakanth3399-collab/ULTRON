"""
modules/smart_file_finder.py - ULTRON Natural Language & Content-Aware File Finder

Searches the user's Desktop, Documents, Downloads, and project directories.
Matches filenames as well as text file contents (.txt, .py, .md, .json, .csv).
Can locate or open files directly upon voice request.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import List, Optional, Tuple


def _get_search_roots() -> List[str]:
    user_home = os.path.expanduser("~")
    roots = [
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Downloads"),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ]
    # Check OneDrive synced folders as well
    onedrive = os.environ.get("OneDrive")
    if onedrive and os.path.exists(onedrive):
        for sub in ["Desktop", "Documents"]:
            p = os.path.join(onedrive, sub)
            if os.path.exists(p) and p not in roots:
                roots.append(p)
    return [r for r in roots if os.path.exists(r)]


def search_files(query: str, search_content: bool = True, max_results: int = 5) -> Tuple[bool, str, List[str]]:
    """
    Finds files matching query in name or contents.
    Returns (success, speech_summary, list_of_paths).
    """
    clean_q = re.sub(r"^(?:find|search\s+for|search|look\s+for|locate|open)\s+(?:file|document|pdf|code|notes|script)?\s*", "", query.lower().strip()).strip()
    clean_q = re.sub(r"^(?:my|the)\s+", "", clean_q).strip()

    if not clean_q:
        return False, "Please specify what file or topic you want me to search for.", []

    roots = _get_search_roots()
    matches: List[Tuple[int, str]] = []  # (score, path)
    seen_paths = set()

    TEXT_EXTS = {".txt", ".py", ".md", ".json", ".csv", ".log", ".html", ".css", ".js"}

    for root_dir in roots:
        for root, dirs, files in os.walk(root_dir, onerror=lambda e: None):
            dirs[:] = [d for d in dirs if not d.startswith((".", "__")) and d not in ["node_modules", ".venv", "site-packages", "AppData", "Local"]]
            for fname in files:
                fpath = os.path.join(root, fname)
                if fpath in seen_paths:
                    continue

                fname_lower = fname.lower()
                score = 0

                # Check exact or partial name match
                if clean_q == fname_lower:
                    score += 100
                elif clean_q in fname_lower:
                    score += 50
                else:
                    # Token matching
                    tokens = clean_q.split()
                    token_matches = sum(1 for t in tokens if t in fname_lower)
                    if token_matches == len(tokens) and len(tokens) > 0:
                        score += 30

                # Content search for text files if not yet matched by name
                if score == 0 and search_content:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in TEXT_EXTS:
                        try:
                            # Quick inspect first 64KB
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                chunk = f.read(65536)
                                if clean_q in chunk.lower():
                                    score += 20
                        except Exception:
                            pass

                if score > 0:
                    seen_paths.add(fpath)
                    matches.append((score, fpath))
                    if len(matches) >= 20:
                        break
            if len(matches) >= 20:
                break

    if not matches:
        return False, f"I could not find any files related to '{clean_q}'.", []

    # Sort descending by score
    matches.sort(key=lambda x: x[0], reverse=True)
    top_matches = [m[1] for m in matches[:max_results]]
    names = [os.path.basename(p) for p in top_matches]

    summary = f"Found {len(top_matches)} matching file{'s' if len(top_matches) > 1 else ''}: {', '.join(names[:3])}."
    return True, summary, top_matches


def find_and_open(query: str) -> Tuple[bool, str]:
    """Finds the best matching file and opens it immediately."""
    ok, msg, paths = search_files(query, search_content=True, max_results=1)
    if not ok or not paths:
        return False, msg

    target = paths[0]
    try:
        os.startfile(target)
        return True, f"Found and opened {os.path.basename(target)}."
    except Exception as e:
        return False, f"Found {os.path.basename(target)}, but could not open it: {e}"
