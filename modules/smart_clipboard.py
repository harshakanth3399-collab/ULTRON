"""
modules/smart_clipboard.py - ULTRON Smart Voice Clipboard & Semantic History Stack

Monitors Windows clipboard history in the background, keeping track of text,
code snippets, and URLs copied throughout the day. Allows Harsha to recall,
search, and paste previous clipboard items hands-free.
"""

from __future__ import annotations

import collections
import threading
import time
from typing import Dict, List, Optional, Tuple

import win32clipboard


class SmartClipboard:
    """Manages active clipboard tracking and multi-item voice recall."""

    def __init__(self, max_history: int = 30) -> None:
        self.max_history = max_history
        self._history: collections.deque = collections.deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_text = ""

    def _get_current_clipboard_text(self) -> str:
        """Reads Unicode text directly from Windows clipboard via win32clipboard."""
        try:
            win32clipboard.OpenClipboard()
            text = ""
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return text or ""
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            return ""

    def _set_clipboard_text(self, text: str) -> bool:
        """Writes Unicode text directly to Windows clipboard via win32clipboard."""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            return False

    def _watcher_loop(self) -> None:
        """Polls clipboard changes every 0.8 seconds."""
        while self._running:
            try:
                curr = self._get_current_clipboard_text().strip()
                if curr and curr != self._last_text:
                    self._last_text = curr
                    with self._lock:
                        entry = {
                            "text": curr,
                            "time": time.time(),
                            "preview": curr[:100] + ("..." if len(curr) > 100 else ""),
                            "is_url": curr.startswith(("http://", "https://", "www.")),
                        }
                        self._history = collections.deque(
                            [h for h in self._history if h["text"] != curr],
                            maxlen=self.max_history
                        )
                        self._history.appendleft(entry)
            except Exception:
                pass
            time.sleep(0.8)

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "Clipboard memory is already running."
        self._running = True
        self._thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._thread.start()
        # Seed with current clipboard
        seed = self._get_current_clipboard_text().strip()
        if seed:
            self._last_text = seed
            self._history.appendleft({
                "text": seed,
                "time": time.time(),
                "preview": seed[:100],
                "is_url": seed.startswith(("http://", "https://")),
            })
        return True, "Smart Clipboard memory active."

    def stop(self) -> Tuple[bool, str]:
        self._running = False
        return True, "Smart Clipboard memory stopped."

    def get_last_copied(self) -> Tuple[bool, str]:
        """Returns the most recently copied item."""
        with self._lock:
            if not self._history:
                curr = self._get_current_clipboard_text().strip()
                if curr:
                    return True, f"The last copied text is: '{curr[:120]}'."
                return False, "Your clipboard history is currently empty."
            top = self._history[0]
            return True, f"The last item you copied is: '{top['preview']}'."

    def search_clipboard(self, query: str) -> Tuple[bool, str]:
        """Finds any copied item matching query."""
        q = query.lower().strip()
        with self._lock:
            for item in self._history:
                if q in item["text"].lower():
                    self._set_clipboard_text(item["text"])
                    return True, f"Found and restored to clipboard: '{item['preview']}'."
        return False, f"No clipboard item found matching '{query}'."

    def paste_previous(self) -> Tuple[bool, str]:
        """Restores the second most recent clipboard item and triggers paste."""
        with self._lock:
            if len(self._history) < 2:
                return False, "Not enough items in clipboard history to go back."
            prev_item = self._history[1]
            self._set_clipboard_text(prev_item["text"])

        try:
            from modules.human_controller import human_controller
            human_controller.press_shortcut("paste")
            return True, f"Restored and pasted: '{prev_item['preview']}'."
        except Exception:
            return True, f"Restored previous item to clipboard: '{prev_item['preview']}'."

    def clear(self) -> Tuple[bool, str]:
        with self._lock:
            self._history.clear()
            self._last_text = ""
        return True, "Clipboard history cleared."


smart_clipboard = SmartClipboard()
smart_clipboard.start()
