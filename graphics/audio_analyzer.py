"""
graphics/audio_analyzer.py - Real-time Audio Level for Reactive Particles

AUDIO SOURCES:
  A. MICROPHONE (while LISTENING): reads real mic input and drives particles
  B. TTS ENVELOPE (while SPEAKING): synthesized syllable model drives particles
     (We do NOT re-capture from mic during SPEAKING to avoid feedback)

HARDWARE NOTE:
  Reads native device rate (44100Hz) to match Intel Smart Sound Array.
  RMS is normalized to 0..1 for the particle engine.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Optional

import numpy as np

from graphics.constants import AUDIO_ATTACK, AUDIO_GAIN, AUDIO_RELEASE
from graphics.state import UltronState


class AudioAnalyzer:
    """
    Drives particle audio reactivity.

    LISTENING mode: captures real microphone RMS and feeds particles.
    SPEAKING mode:  uses a TTS syllable envelope model (no mic feedback loop).
    IDLE mode:      gentle autonomous breathe.
    """

    __slots__ = (
        "_level", "_smoothed",
        "_stream_obj", "_lock",
        "_running", "_thread",
        "_speak_phase", "_speak_energy",
        "_idle_phase",
        "_mic_idx", "_mic_rate", "_mic_ch",
    )

    def __init__(self) -> None:
        self._level        = 0.0
        self._smoothed     = 0.0
        self._lock         = threading.Lock()
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._stream_obj   = None

        self._speak_phase  = 0.0
        self._speak_energy = 0.0
        self._idle_phase   = 0.0

        # Import hardware parameters from speech module if available
        self._mic_idx  = None
        self._mic_rate = 44100
        self._mic_ch   = 1
        try:
            from speech import _MIC_IDX, _MIC_RATE, _MIC_CHANNELS
            self._mic_idx  = _MIC_IDX
            self._mic_rate = _MIC_RATE
            self._mic_ch   = _MIC_CHANNELS
        except Exception:
            pass

    # ── Microphone level reader (powered directly by speech.py) ───────────────

    def start_listening(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._stream_obj = None
        self._thread = None

    # ── Main update (called every frame) ──────────────────────────────────────

    def update(self, dt: float, state: UltronState, speaking_fn) -> float:
        """
        Returns smoothed 0..1 audio level for the particle engine.

        SPEAKING:  drives from TTS syllable envelope (ULTRON's voice notes)
        USER (IDLE/LISTENING/RECORDING): drives from live mic RMS (Harsha's voice notes)
        """
        target = 0.0

        if state == UltronState.SPEAKING and speaking_fn():
            # ULTRON IS SPEAKING: Synthesized syllable model matching speech rhythm
            self._speak_phase += dt * 10.5
            syllable = abs(math.sin(self._speak_phase * 1.75)) ** 0.5
            bass     = (math.sin(self._speak_phase * 0.85) * 0.5 + 0.5) * 0.35
            burst    = max(0.0, math.sin(self._speak_phase * 4.2)) ** 2.0 * 0.40
            self._speak_energy = min(1.0, syllable * 0.60 + bass + burst + 0.15)
            target = self._speak_energy

        else:
            # HARSHA IS SPEAKING (or listening/recording/idle): Read live mic RMS directly
            mic_rms = 0.0
            try:
                from speech import get_latest_mic_rms
                mic_rms = get_latest_mic_rms()
            except Exception:
                pass

            if mic_rms > 3.0:
                # Map mic RMS (typically 5..200) to 0.1..1.0 particle energy scale
                target = min(1.0, (mic_rms / 75.0) * AUDIO_GAIN)
            else:
                # Gentle breathe baseline pulse when silent
                self._idle_phase += dt * 0.65
                target = 0.08 + 0.05 * math.sin(self._idle_phase * 1.2)
                target += 0.02 * math.sin(self._idle_phase * 3.2)
                self._speak_energy *= 0.85

        # Smooth with fast attack / natural release
        coeff = AUDIO_ATTACK * 1.4 if target > self._smoothed else AUDIO_RELEASE * 1.2
        self._smoothed += (target - self._smoothed) * min(1.0, coeff * dt * 60.0)
        self._smoothed = float(np.clip(self._smoothed, 0.0, 1.0))
        return self._smoothed


    @property
    def level(self) -> float:
        return self._smoothed

    def shutdown(self) -> None:
        self.stop()
