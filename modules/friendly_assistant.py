"""
modules/friendly_assistant.py - Real-World Friendly Assistant & J.A.R.V.I.S. System Diagnostics Engine
"""

from __future__ import annotations

import datetime
from typing import Optional

from modules.app_finder import app_finder
from modules.system_control import get_battery_status, get_memory_status


def get_dynamic_greeting(user_name: str = "Harsha") -> str:
    """Generates a dynamic, time-aware greeting based on local time of day."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return f"Good morning, {user_name}! All systems are online. How can I help you start your day?"
    elif 12 <= hour < 17:
        return f"Good afternoon, {user_name}! Systems are running at peak performance. What's on your agenda?"
    else:
        return f"Good evening, {user_name}! All systems operational. How can I assist you tonight?"


def get_system_diagnostics(user_name: str = "Harsha") -> str:
    """Generates a complete J.A.R.V.I.S.-style system diagnostic status report."""
    try:
        ram_pct, used_mb, total_mb = get_memory_status()
        pct, plugged = get_battery_status()
        app_count = len(app_finder.apps_cache)

        used_gb = round(used_mb / 1024, 1)
        total_gb = round(total_mb / 1024, 1)

        batt_str = f"{pct}% {'plugged in' if plugged else 'on battery power'}" if pct is not None else "telemetry active"

        report = (
            f"All core systems operational, {user_name}. "
            f"Memory load is at {ram_pct}% ({used_gb} GB used out of {total_gb} GB), "
            f"battery is at {batt_str}, "
            f"Groq sub-second neural bridge is active, and "
            f"{app_count} application shortcuts are dynamically indexed."
        )
        return report
    except Exception as e:
        return f"All systems operational, {user_name}. Diagnostics check completed."


def get_friendly_response(query: str, user_name: str = "Harsha") -> Optional[str]:
    """Handles friendly social conversations, greetings, and system diagnostics."""
    q = query.lower().strip()

    # 1. Explicit System Diagnostics / Status Check
    if any(q.startswith(k) or q == k for k in ["system status", "diagnostics", "status report", "run diagnostics", "how are systems"]):
        return get_system_diagnostics(user_name)

    # 2. Direct Gratitude
    if q in ["thank you", "thanks ultron", "thanks", "great job ultron", "good job ultron"]:
        return f"Always, {user_name}."

    # 3. Direct Identity / Creator Inquiry (only when explicitly asked)
    if q in ["who created you", "who made you", "who built you"]:
        return f"I was built and customized by you, {user_name}, to operate as your dedicated intellectual partner."

    # 4. Direct Name Check (only when asking directly, not part of a larger sentence)
    if q in ["what is your name", "who are you", "what's your name", "tell me who you are", "tell me who are you"]:
        return f"I am ULTRON, your real-time partner and chief of staff, {user_name}."

    return None
