"""
modules/desktop_recall.py - Lightweight Desktop Activity Recall Engine

Maintains a private, local SQLite log of active window titles and application usage.
Enables queries like:
  - "What was I doing 10 minutes ago?"
  - "What was that website I looked at earlier?"
  - "What did I work on today?"
"""

from __future__ import annotations

import ctypes
import os
import sqlite3
import threading
import time
from typing import List, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "activity_history.db")
user32 = ctypes.windll.user32


class DesktopRecall:
    """Logs active foreground window events and answers historical context queries."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()
        self._last_title = ""
        self._running = False
        self._thread: threading.Thread | None = None
        self.start_monitoring()

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    time_str TEXT,
                    window_title TEXT
                )
            """)
            conn.commit()

    def start_monitoring(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="DesktopRecallWatcher")
        self._thread.start()

    def _monitor_loop(self) -> None:
        buf = ctypes.create_unicode_buffer(512)
        while self._running:
            try:
                hwnd = user32.GetForegroundWindow()
                if hwnd:
                    user32.GetWindowTextW(hwnd, buf, 512)
                    title = buf.value.strip()
                    if title and title != self._last_title and title != "ULTRON":
                        self._last_title = title
                        now = time.time()
                        time_str = time.strftime("%I:%M %p", time.localtime(now))
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute(
                                "INSERT INTO activity_log (timestamp, time_str, window_title) VALUES (?, ?, ?)",
                                (now, time_str, title)
                            )
                            conn.commit()
            except Exception:
                pass
            time.sleep(3.0)  # Check every 3 seconds — virtually 0% CPU

    def get_recent_activity(self, limit: int = 5) -> str:
        """Returns the most recent desktop activities."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT time_str, window_title FROM activity_log ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                rows = cur.fetchall()

            if not rows:
                return "You just started up your workstation, Harsha. No prior activity logged yet."

            events = [f"at {r[0]}, you were on '{r[1]}'" for r in reversed(rows)]
            return "Here is your recent activity: " + "; ".join(events) + "."
        except Exception as e:
            return f"Activity recall error: {e}"

    def query_activity(self, keyword: str) -> str:
        """Finds specific applications, documents, or websites opened earlier."""
        clean_kw = keyword.strip().lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT time_str, window_title FROM activity_log WHERE LOWER(window_title) LIKE ? ORDER BY id DESC LIMIT 3",
                    (f"%{clean_kw}%",)
                )
                rows = cur.fetchall()

            if not rows:
                return f"I couldn't find any recent activity matching '{keyword}' in your log, Harsha."

            matches = [f"at {r[0]} ({r[1]})" for r in rows]
            return f"You were working on that: {'; '.join(matches)}."
        except Exception as e:
            return f"Search error: {e}"


# Global singleton
desktop_recall = DesktopRecall()
