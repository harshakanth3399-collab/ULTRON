"""Animation state machine for the holographic sphere."""

from enum import Enum, auto


class UltronState(Enum):
    IDLE = auto()
    LISTENING = auto()
    SPEAKING = auto()


class StateManager:
    """Tracks current mode and smooth cross-fade between state profiles."""

    __slots__ = ("_state", "_blend", "_target_blend")

    def __init__(self) -> None:
        self._state = UltronState.IDLE
        self._blend = 0.0
        self._target_blend = 0.0

    @property
    def state(self) -> UltronState:
        return self._state

    def set_state(self, state: UltronState) -> None:
        if state != self._state:
            self._state = state
            self._target_blend = 0.0

    def update(self, dt: float) -> None:
        speed = 3.5 if self._state != UltronState.IDLE else 2.0
        if self._blend < self._target_blend:
            self._blend = min(self._target_blend, self._blend + dt * speed)
        elif self._blend > self._target_blend:
            self._blend = max(self._target_blend, self._blend - dt * speed)

        # Each state transition resets blend to ramp up effects
        if self._blend >= 1.0:
            return
        self._target_blend = 1.0
        self._blend = min(1.0, self._blend + dt * speed)

    def activation(self) -> float:
        """0..1 envelope indicating how fully the active state has engaged."""
        return self._blend

    def is_idle(self) -> bool:
        return self._state == UltronState.IDLE

    def is_listening(self) -> bool:
        return self._state == UltronState.LISTENING

    def is_speaking(self) -> bool:
        return self._state == UltronState.SPEAKING
