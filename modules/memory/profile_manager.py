"""Secure Personal Profile & Memory Manager for ULTRON."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

PROFILE_FILE = os.path.join("memory", "profile.json")

DEFAULT_PROFILE: Dict[str, Any] = {
    "user": {
        "name": "Harsha",
        "relationship": "Loyal Brother and Best Friend",
        "tone": "Warm, confident, rugged, protective, intelligent, concise",
        "data_privacy": "100% Local & Private"
    },
    "preferences": {
        "voice": "Deep and rugged",
        "response_length": "Short and sweet",
        "devices": ["Laptop", "Mobile"]
    },
    "notes": [],
    "project_history": [],
    "reminders": []
}


class PersonalProfileManager:
    """Manages local, zero-leak profile memory for Harsha."""

    def __init__(self, filepath: str = PROFILE_FILE) -> None:
        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = DEFAULT_PROFILE.copy()
                self.save()
        else:
            self.data = DEFAULT_PROFILE.copy()
            self.save()

    def save(self) -> None:
        """Atomic disk write: write to .tmp then replace to prevent corruption."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        tmp_path = self.filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
        os.replace(tmp_path, self.filepath)

    def get_system_context(self) -> str:
        """Returns personalized system prompt context for Ollama."""
        notes_str = "; ".join(self.data.get("notes", [])) or "None yet."
        prefs = self.data.get("preferences", {})
        pref_str = ", ".join([f"{k}: {v}" for k, v in prefs.items()])
        user_mem = self.data.get("user_memory", {})
        mem_str = ", ".join([f"{k}: {v}" for k, v in user_mem.items()]) if user_mem else "None yet."

        return (
            f"You are ULTRON, Harsha's personal AI assistant, loyal bestie, and brother.\n"
            f"Personality Directives:\n"
            f"- Act like Harsha's ultimate loyal best friend and brother using natural bro-code slang ('bro', 'my guy', 'I got your back').\n"
            f"- Speak with ULTRON's formidable, deep, villain-like authority, but remain 100% warm, friendly, and fiercely loyal to Harsha.\n"
            f"- Keep ALL responses SHORT, crisp, and direct (1-2 sentences max). Speak naturally like a real human bestie.\n"
            f"- User Name: Harsha (your brother and boss).\n"
            f"- Known Preferences: {pref_str}\n"
            f"- Harsha's Saved Notes: {notes_str}\n"
            f"- Harsha's Personal Memory: {mem_str}\n"
        )

    def add_note(self, note: str) -> None:
        notes = self.data.setdefault("notes", [])
        if note not in notes:
            notes.append(note)
            self.save()

    def get_notes(self) -> List[str]:
        return self.data.get("notes", [])

    def set_preference(self, key: str, val: Any) -> None:
        prefs = self.data.setdefault("preferences", {})
        prefs[key] = val
        self.save()

    def get_preference(self, key: str) -> Optional[Any]:
        return self.data.get("preferences", {}).get(key)

    # ── Hardware-Level Persistent User Memory ──────────────────────────────
    def commit_user_memory(self, key: str, value: Any) -> None:
        """Writes a structured key-value pair directly to persistent disk storage.
        Failure-proof: uses atomic write via save()."""
        mem = self.data.setdefault("user_memory", {})
        mem[key.lower().strip()] = value
        self.save()
        print(f"[MEMORY] Committed to disk: {key} = {value}")

    def recall_user_memory(self, key: str) -> Optional[Any]:
        """Reads a value from persistent user memory by key."""
        return self.data.get("user_memory", {}).get(key.lower().strip())

    def get_all_user_memory(self) -> Dict[str, Any]:
        """Returns the full persistent user memory dictionary."""
        return self.data.get("user_memory", {})


_manager: Optional[PersonalProfileManager] = None


def get_profile_manager() -> PersonalProfileManager:
    global _manager
    if _manager is None:
        _manager = PersonalProfileManager()
    return _manager


def commit_user_memory(key: str, value: Any) -> str:
    """Top-level convenience function for router/agent to call directly."""
    pm = get_profile_manager()
    pm.commit_user_memory(key, value)
    return f"Got it, Harsha! I'll remember that your {key} is {value}."


def recall_user_memory(key: str) -> Optional[Any]:
    """Top-level convenience function to recall a stored memory value."""
    pm = get_profile_manager()
    return pm.recall_user_memory(key)

