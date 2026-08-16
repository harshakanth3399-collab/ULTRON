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
        "relationship": "Loyal Assistant & Intelligent Companion",
        "tone": "Respectful, confident, intelligent, warm, highly concise",
        "data_privacy": "100% Local & Private",
        "location": "Anantapur, Andhra Pradesh",
        "mother": "Narmada"
    },
    "preferences": {
        "preferred_address": "Sir",
        "voice": "Deep and friendly",
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

        # Sanitize & enforce single consolidated standard profile keys
        user_mem = self.data.setdefault("user_memory", {})
        user_mem["address"] = "Anantapur, Andhra Pradesh"
        user_mem["mother_name"] = "Narmada"
        
        # Remove legacy duplicate keys
        for dup in ["mother", "mom", "mother's name", "mom's name", "location", "city", "state", "hometown"]:
            user_mem.pop(dup, None)

        # Clean out hallucinated/outdated notes
        notes = self.data.setdefault("notes", [])
        clean_notes = [
            n for n in notes
            if not any(bad in n.lower() for bad in ["padma", "vijayawada", "anandapur in bia"])
        ]
        self.data["notes"] = clean_notes

    def save_sync(self) -> None:
        """Internal synchronous atomic write with retry on file locks."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                tmp_path = self.filepath + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4)
                
                for _attempt in range(5):
                    try:
                        os.replace(tmp_path, self.filepath)
                        break
                    except (PermissionError, OSError):
                        import time
                        time.sleep(0.5)
                print("[MEMORY] Async disk write completed successfully.")
            except Exception as e:
                print(f"[MEMORY ERROR] Disk write failed: {e}")

    def save(self) -> None:
        """Asynchronous disk write: executes in a background thread to prevent blocking voice loop."""
        thread = threading.Thread(target=self.save_sync, daemon=True)
        thread.start()

    def get_preferred_address(self) -> str:
        prefs = self.data.get("preferences", {})
        addr = prefs.get("preferred_address", "Sir")
        if not addr or addr.lower() in ["none", "no_sir", "off", "dont_call_sir", "don't call me sir", "harsha"]:
            return ""
        return addr

    def get_address_suffix(self, prefix: str = ", ") -> str:
        addr = self.get_preferred_address()
        if not addr:
            return ""
        return f"{prefix}{addr}"

    def get_active_language(self) -> str:
        prefs = self.data.get("preferences", {})
        return prefs.get("active_language", "en")

    def set_active_language(self, lang: str) -> None:
        valid_lang = "te" if lang.lower() in ["te", "telugu"] else "en"
        self.set_preference("active_language", valid_lang)

    def get_system_context(self) -> str:
        """Returns personalized system prompt context for Ollama/Groq."""
        notes_str = "; ".join(self.data.get("notes", [])) or "None yet."
        prefs = self.data.get("preferences", {})
        preferred_address = self.get_preferred_address()
        active_lang = self.get_active_language()
        pref_str = ", ".join([f"{k}: {v}" for k, v in prefs.items()])
        user_mem = self.data.get("user_memory", {})
        mem_str = ", ".join([f"{k}: {v}" for k, v in user_mem.items()]) if user_mem else "None yet."

        addr_instruction = f"Address the user as '{preferred_address}'." if preferred_address else "Respond naturally without forcing titles like 'Sir'."

        if active_lang == "te":
            lang_instruction = (
                "STRICT LANGUAGE DIRECTIVE: The user has explicitly requested to speak in Telugu. "
                "Respond in clear, natural, colloquial Andhra Pradesh / Rayalaseema (Anantapur) Telugu phrasing."
            )
        else:
            lang_instruction = (
                "STRICT LANGUAGE DIRECTIVE: ALWAYS respond entirely in English. "
                "Do NOT respond in Telugu, Hindi, or any other language unless the user explicitly commands 'Switch to Telugu'. "
                "Merely mentioning the word 'Telugu', locations like Anantapur, or profile details MUST NOT make you switch language."
            )

        return (
            f"You are ULTRON, Harsha's personal AI assistant and loyal companion.\n"
            f"Personality Directives:\n"
            f"- Speak with ULTRON's formidable intelligence and warm, natural tone.\n"
            f"- {addr_instruction}\n"
            f"- {lang_instruction}\n"
            f"- Keep ALL responses extremely CONCISE, crisp, and direct (1 short sentence max, 2 sentences max if necessary).\n"
            f"- User Name: Harsha\n"
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
    def _normalize_key(self, key: str) -> str:
        """Consolidate key variations into standard unified keys."""
        k = key.lower().strip()
        if k in ["mother", "mom", "mother's name", "mom's name", "mother_name"]:
            return "mother_name"
        if k in ["address", "location", "city", "state", "hometown"]:
            return "address"
        if k in ["favorite_song", "favorite song", "fav song", "song"]:
            return "favorite_song"
        return k

    def commit_user_memory(self, key: str, value: Any) -> None:
        """Writes structured memory with key consolidation and synchronous disk write."""
        mem = self.data.setdefault("user_memory", {})
        norm_key = self._normalize_key(key)
        cleaned_val = str(value).strip()
        mem[norm_key] = cleaned_val
        self.save_sync()
        print(f"[MEMORY] Committed to disk: {norm_key} = {cleaned_val}")

    def delete_user_memory(self, key: str) -> bool:
        """Permanently removes key from user_memory dictionary and flushes to disk."""
        mem = self.data.setdefault("user_memory", {})
        norm_key = self._normalize_key(key)
        deleted = False
        if norm_key in mem:
            del mem[norm_key]
            deleted = True
        
        # Check notes list as well
        notes = self.data.get("notes", [])
        new_notes = [n for n in notes if norm_key not in n.lower() and key.lower() not in n.lower()]
        if len(new_notes) != len(notes):
            self.data["notes"] = new_notes
            deleted = True

        if deleted:
            self.save_sync()
            print(f"[MEMORY] Deleted memory for: '{norm_key}'")
            return True
        return False

    def recall_user_memory(self, key: str) -> Optional[Any]:
        """Hardware fallback lookup: reads directly from disk/memory using consolidated keys."""
        norm_key = self._normalize_key(key)
        
        # Explicit Hardware Fallbacks
        if norm_key == "address":
            return self.data.get("user_memory", {}).get("address", "Anantapur, Andhra Pradesh")
        if norm_key == "mother_name":
            return self.data.get("user_memory", {}).get("mother_name", "Narmada")

        return self.data.get("user_memory", {}).get(norm_key)

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
    """Top-level function: updates memory synchronously on disk and returns confirmation."""
    pm = get_profile_manager()
    pm.commit_user_memory(key, value)
    pref_addr = pm.data.get("preferences", {}).get("preferred_address", "Sir")
    return f"Done, {pref_addr}. Your {key} is now {value}."


def recall_user_memory(key: str) -> Optional[Any]:
    """Top-level convenience function for hardware-first memory lookup."""
    pm = get_profile_manager()
    return pm.recall_user_memory(key)


def delete_user_memory(key: str) -> bool:
    """Top-level convenience function to delete memory key permanently."""
    pm = get_profile_manager()
    return pm.delete_user_memory(key)


