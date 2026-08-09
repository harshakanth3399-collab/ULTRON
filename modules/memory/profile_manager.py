"""Secure Personal Profile & Memory Manager for ULTRON."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

PROFILE_FILE = os.path.join("memory", "profile.json")

DEFAULT_PROFILE: Dict[str, Any] = {
    "user": {
        "name": "Harsha",
        "relationship": "Loyal Brother and Best Friend",
        "tone": "Warm, confident, rugged, protective, intelligent, concise",
        "data_privacy": "100% Local & Private",
        "location": "Anantapur, Andhra Pradesh",
        "mother": "Narmada"
    },
    "preferences": {
        "voice": "Deep and rugged",
        "response_length": "Short and sweet",
        "devices": ["Laptop", "Mobile"]
    },
    "notes": [],
    "project_history": [],
    "reminders": [],
    "user_memory": {
        "address": "Anantapur, Andhra Pradesh",
        "location": "Anantapur, Andhra Pradesh",
        "city": "Anantapur",
        "state": "Andhra Pradesh",
        "hometown": "Anantapur, Andhra Pradesh",
        "mother": "Narmada",
        "mom": "Narmada",
        "mother's name": "Narmada",
        "mom's name": "Narmada"
    }
}


class PersonalProfileManager:
    """Manages local, zero-leak profile memory for Harsha."""

    def __init__(self, filepath: str = PROFILE_FILE) -> None:
        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._recent_turns: List[Dict[str, str]] = []
        self.load()

    def load(self) -> None:
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = DEFAULT_PROFILE.copy()
                self.save_sync()
        else:
            self.data = DEFAULT_PROFILE.copy()
            self.save_sync()

        # Sanitize & enforce hardware baseline profile values
        user_mem = self.data.setdefault("user_memory", {})
        user_mem["address"] = "Anantapur, Andhra Pradesh"
        user_mem["location"] = "Anantapur, Andhra Pradesh"
        user_mem["city"] = "Anantapur"
        user_mem["state"] = "Andhra Pradesh"
        user_mem["mother"] = "Narmada"
        user_mem["mom"] = "Narmada"
        user_mem["mother's name"] = "Narmada"
        user_mem["mom's name"] = "Narmada"

        # Clean out hallucinated/outdated notes
        notes = self.data.setdefault("notes", [])
        clean_notes = [
            n for n in notes
            if not any(bad in n.lower() for bad in ["padma", "vijayawada", "anandapur in bia"])
        ]
        self.data["notes"] = clean_notes

    def save_sync(self) -> None:
        """Internal synchronous atomic write."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                tmp_path = self.filepath + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4)
                os.replace(tmp_path, self.filepath)
                print("[MEMORY] Async disk write completed successfully.")
            except Exception as e:
                print(f"[MEMORY ERROR] Disk write failed: {e}")

    def save(self) -> None:
        """Asynchronous disk write: executes in a background thread to prevent blocking voice loop."""
        thread = threading.Thread(target=self.save_sync, daemon=True)
        thread.start()

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
            f"- Keep ALL responses SHORT, crisp, and direct (1-2 sentences max).\n"
            f"- User Name: Harsha (your brother and boss).\n"
            f"- User Location: Anantapur, Andhra Pradesh\n"
            f"- Mother's Name: Narmada\n"
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
        """Writes structured memory asynchronously in background thread."""
        mem = self.data.setdefault("user_memory", {})
        k = key.lower().strip()
        v = str(value).strip()
        mem[k] = v
        self.save()
        print(f"[MEMORY] Committed asynchronously: {k} = {v}")

    def recall_user_memory(self, key: str) -> Optional[Any]:
        """Hardware fallback lookup: reads directly from disk/memory before LLM."""
        k = key.lower().strip()
        
        # Explicit Hardware Fallbacks
        if k in ["address", "location", "city", "state", "hometown"]:
            return "Anantapur, Andhra Pradesh"
        if k in ["mother", "mom", "mother's name", "mom's name"]:
            return "Narmada"

        return self.data.get("user_memory", {}).get(k)

    def get_all_user_memory(self) -> Dict[str, Any]:
        return self.data.get("user_memory", {})

    # ── Conversational Context Buffer ──────────────────────────────────────
    def add_turn(self, user_msg: str, ai_reply: str) -> None:
        """Stores recent conversation turn in memory buffer."""
        if user_msg and ai_reply:
            self._recent_turns.append({"user": user_msg.strip(), "ai": ai_reply.strip()})
            if len(self._recent_turns) > 10:
                self._recent_turns.pop(0)

    def get_last_turn(self) -> Optional[Dict[str, str]]:
        """Returns the most recent conversation turn."""
        return self._recent_turns[-1] if self._recent_turns else None


_manager: Optional[PersonalProfileManager] = None


def get_profile_manager() -> PersonalProfileManager:
    global _manager
    if _manager is None:
        _manager = PersonalProfileManager()
    return _manager


def commit_user_memory(key: str, value: Any) -> str:
    """Top-level function: returns instant spoken reply while save runs in background."""
    pm = get_profile_manager()
    pm.commit_user_memory(key, value)
    return "Saving that to my memory now!"


def recall_user_memory(key: str) -> Optional[Any]:
    """Top-level convenience function for hardware-first memory lookup."""
    pm = get_profile_manager()
    return pm.recall_user_memory(key)

