"""
scheduler.py - ULTRON Voice Reminders & Scheduler Engine
Manages SQLite-backed voice reminders and background timer alerts.
"""

from __future__ import annotations

import datetime
import re
import threading
import time
from typing import Optional, Tuple
from modules.database import get_connection
from speech_engine import speak


def add_voice_reminder(task: str, minutes_from_now: float) -> str:
    """Saves a voice reminder in memory/ultron.db due in N minutes."""
    due_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes_from_now)
    due_str = due_time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (task, due_time, status) VALUES (?, ?, 'pending')",
                (task.strip(), due_str)
            )
            conn.commit()
        return f"Reminder set for '{task}' in {int(minutes_from_now)} minutes."
    except Exception as e:
        return f"Failed to set reminder: {e}"


def _poll_reminders() -> None:
    """Background polling worker checking for due reminders every 10 seconds."""
    while True:
        try:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            due_items = []
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, task FROM reminders WHERE status = 'pending' AND due_time <= ?",
                    (now_str,)
                )
                due_items = cursor.fetchall()

                for row in due_items:
                    r_id, r_task = row["id"], row["task"]
                    cursor.execute("UPDATE reminders SET status = 'completed' WHERE id = ?", (r_id,))
                    conn.commit()

                    from modules.memory.profile_manager import get_profile_manager
                    pref_addr = get_profile_manager().data.get("preferences", {}).get("preferred_address", "Sir")
                    alert_msg = f"{pref_addr}, reminder alert: {r_task}!"
                    print(f"[SCHEDULER ALERT] {alert_msg}")
                    speak(alert_msg)

        except Exception as e:
            pass
        time.sleep(10)


# Start background scheduler thread automatically
_scheduler_thread = threading.Thread(target=_poll_reminders, daemon=True)
_scheduler_thread.start()
