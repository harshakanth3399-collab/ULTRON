"""ULTRON holographic graphics pipeline."""

from graphics.state import StateManager, UltronState

__all__ = ["UltronState", "StateManager", "UltronRenderer"]


def __getattr__(name: str):
    if name == "UltronRenderer":
        from graphics.renderer import UltronRenderer

        return UltronRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
