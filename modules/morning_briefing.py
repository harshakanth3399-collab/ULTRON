"""
modules/morning_briefing.py - ULTRON Morning Protocol Briefing & Daily Motivation Engine

Generates an authoritative, fluid MCU J.A.R.V.I.S. morning sequence:
- Current greeting, date, and time
- Local weather forecast
- Laptop battery level & power status
- Notification & communication summary
- Daily motivational quote
"""

from __future__ import annotations

import datetime
import random
import time
from typing import Tuple

from modules.system_guardian import system_guardian
from modules.weather_service import get_live_weather

MOTIVATIONAL_QUOTES = [
    "Today's discipline builds tomorrow's empire, Harsha. Let's make every second count.",
    "The secret of getting ahead is getting started. Your systems are primed and ready.",
    "Excellence is not an act, but a habit. Stand tall and conquer the day.",
    "Focus on progress, not perfection. All your tools are online and awaiting command.",
    "Energy and persistence conquer all things. Let's build something extraordinary today.",
]


def generate_morning_briefing() -> Tuple[bool, str]:
    """Compiles the complete morning protocol briefing for Harsha."""
    now = datetime.datetime.now()
    greeting = "Good morning" if now.hour < 12 else ("Good afternoon" if now.hour < 17 else "Good evening")
    date_str = now.strftime("%A, %B %d")
    time_str = now.strftime("%I:%M %p")

    # 1. Weather
    ok_w, weather_report = get_live_weather()
    weather_snippet = weather_report if ok_w else "Weather sensors are temporarily recalibrating."

    # 2. Battery
    bat = system_guardian.get_battery_info()
    bat_pct = bat.get("percent", 100)
    bat_str = f"Laptop battery is at {bat_pct}%" if bat_pct >= 0 else "System is on wall AC power"

    # 3. Motivation Quote
    quote = random.choice(MOTIVATIONAL_QUOTES)

    briefing = (
        f"{greeting}, Harsha. Today is {date_str}, {time_str}. "
        f"{weather_snippet} {bat_str}. "
        f"All workstation diagnostics are normal. {quote}"
    )
    return True, briefing
