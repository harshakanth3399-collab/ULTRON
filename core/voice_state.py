"""Voice State Machine and Logging for ULTRON."""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable, List, Optional


class VoiceState(Enum):
    IDLE = "IDLE"
    WAKE_LISTENING = "WAKE LISTENING"
    WAKE_DETECTED = "WAKE DETECTED"
    GREETING = "GREETING"
    LISTENING = "LISTENING"
    RECORDING = "RECORDING"
    TRANSCRIBING = "UNDERSTANDING"
    PROCESSING = "THINKING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


class VoiceStateManager:
    """Manages explicit voice pipeline state transitions and notifies UI listeners."""

    def __init__(self) -> None:
        self._state = VoiceState.IDLE
        self._listeners: List[Callable[[VoiceState, str], None]] = []

    @property
    def state(self) -> VoiceState:
        return self._state

    def add_listener(self, callback: Callable[[VoiceState, str], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def transition_to(self, new_state: VoiceState, message: str = "") -> None:
        if self._state != new_state or message:
            self._state = new_state
            log_msg = f"[VOICE] State: {new_state.value}"
            if message:
                log_msg += f" — {message}"
            print(log_msg)

            for listener in list(self._listeners):
                try:
                    listener(new_state, message)
                except Exception as e:
                    print(f"[VOICE] Listener exception: {e}")


# Global Voice State Manager instance
voice_state_manager = VoiceStateManager()
