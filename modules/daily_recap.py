"""
modules/daily_recap.py - ULTRON Autonomous End-of-Day Productivity Recap

Aggregates activity logs from SQLite memory, analyzes active windows, application
usage distribution, and delivers an executive voice summary of Harsha's day.
"""

from __future__ import annotations

import collections
import datetime
import os
import sqlite3
import time
from typing import Dict, List, Tuple

from ai import ask_ai


class DailyRecapEngine:
    """Computes daily productivity analytics and executive summaries."""

    def __init__(self) -> None:
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory", "activity_history.db"
        )

    def _get_todays_records(self) -> List[Tuple[str, str, str]]:
        if not os.path.exists(self.db_path):
            return []

        today_start = time.mktime(datetime.date.today().timetuple())
        records = []
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            c = conn.cursor()
            c.execute(
                "SELECT timestamp, time_str, window_title FROM activity_log WHERE timestamp >= ? ORDER BY id ASC",
                (today_start,)
            )
            records = c.fetchall()
            conn.close()
        except Exception as e:
            print(f"[DAILY RECAP ERROR] {e}")

        return records

    def generate_recap(self) -> Tuple[bool, str]:
        records = self._get_todays_records()

        if not records:
            return True, "You haven't logged any active window tasks yet today, Harsha. Start working and I will track your progress."

        total_samples = len(records)
        # Each transition sample is roughly 2 minutes of active focus
        estimated_active_minutes = max(1, total_samples * 2)
        hours = estimated_active_minutes // 60
        mins = estimated_active_minutes % 60

        # Extract app names from window titles (e.g. "file.py - Visual Studio Code" -> "Visual Studio Code")
        def _extract_app(title: str) -> str:
            parts = title.split(" - ")
            return parts[-1].strip() if len(parts) > 1 else title.strip()

        app_counter = collections.Counter(_extract_app(r[2]) for r in records if r[2])
        top_apps = [app for app, _ in app_counter.most_common(3)]
        top_apps_str = ", ".join(top_apps) if top_apps else "Development Tools"

        time_str = f"{hours} hour{'s' if hours > 1 else ''} and {mins} minutes" if hours > 0 else f"{mins} minutes"

        raw_summary = (
            f"Harsha logged approximately {time_str} of active computer time today. "
            f"The most used applications were: {top_apps_str}. "
            f"Total window activity events recorded: {total_samples}."
        )

        # Synthesize via Ask AI if available, else deliver direct report
        prompt = (
            "You are ULTRON, Harsha's personal AI assistant. "
            f"Deliver this daily productivity recap to Harsha in 2 crisp, human sentences:\n{raw_summary}"
        )
        ai_summary = ask_ai(prompt)
        if ai_summary:
            return True, str(ai_summary)

        return True, f"Today you logged {time_str} of active computer time, Harsha. Your primary focus was on {top_apps_str}."


daily_recap = DailyRecapEngine()
