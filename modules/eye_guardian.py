"""
modules/eye_guardian.py - ULTRON Smart 20-20-20 Eye-Strain & Posture Health Guardian

Monitors continuous screen time. Every 20-30 minutes of uninterrupted work,
delivers a gentle spoken reminder to look 20 feet away for 20 seconds and adjust posture.
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Tuple


class EyeStrainGuardian:
    """Proactive health sentinel enforcing the clinical 20-20-20 visual rest rule."""

    def __init__(self, interval_minutes: float = 20.0) -> None:
        self.interval_seconds = interval_minutes * 60.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_break_time = time.time()

    def _loop(self) -> None:
        print("[EYE GUARDIAN] Health sentinel active (20-20-20 rule).")
        self._last_break_time = time.time()
        while self._running:
            time.sleep(30.0)
            now = time.time()
            if now - self._last_break_time >= self.interval_seconds:
                self._last_break_time = now
                try:
                    from speech_engine import speak
                    speak("Harsha, you have been focused for 20 minutes. Please look 20 feet away for 20 seconds to relax your eyes and adjust your posture.")
                except Exception:
                    pass

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "Eye Strain Guardian is already active."
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True, "Eye Strain Guardian activated. I will remind you every 20 minutes to rest your eyes."

    def stop(self) -> Tuple[bool, str]:
        self._running = False
        return True, "Eye Strain Guardian deactivated."

    def status(self) -> str:
        state = "active" if self._running else "inactive"
        return f"Eye Strain Guardian is currently {state}."


eye_guardian = EyeStrainGuardian()
