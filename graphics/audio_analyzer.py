"""Real-time audio level analysis for reactive holographic animation."""

from __future__ import annotations

import math
import threading
from typing import Optional

import numpy as np

from graphics.constants import AUDIO_ATTACK, AUDIO_GAIN, AUDIO_RELEASE
from graphics.state import UltronState


class AudioAnalyzer:
    """Captures microphone RMS when listening; synthesizes speech envelope when speaking."""

    __slots__ = (
        "_level",
        "_stream",
        "_lock",
        "_running",
        "_speak_phase",
        "_speak_energy",
    )

    def __init__(self) -> None:
        self._level = 0.0
        self._stream: Optional[object] = None
        self._lock = threading.Lock()
        self._running = False
        self._speak_phase = 0.0
        self._speak_energy = 0.0

    def _mic_callback(self, indata, frames, time_info, status) -> None:
        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
        with self._lock:
            self._level = rms * AUDIO_GAIN

    def start_listening(self) -> None:
        self.stop()
        self._running = True

        def _pyaudio_thread():
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=512
                )
                self._stream = (p, stream)
                while self._running:
                    try:
                        data = stream.read(512, exception_on_overflow=False)
                        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                        rms = float(np.sqrt(np.mean(samples ** 2))) / 32768.0
                        with self._lock:
                            self._level = min(1.0, rms * AUDIO_GAIN * 12.0)
                    except Exception:
                        pass
                stream.stop_stream()
                stream.close()
                p.terminate()
            except Exception:
                # Fallback synthetic pulse if pyaudio mic busy
                while self._running:
                    with self._lock:
                        self._level = 0.2 + 0.15 * math.sin(threading.get_ident() * 0.1)
                    threading.Event().wait(0.03)

        t = threading.Thread(target=_pyaudio_thread, daemon=True)
        t.start()

    def stop(self) -> None:
        self._running = False
        self._stream = None

    def update(self, dt: float, state: UltronState, speaking_fn) -> float:
        """Return smoothed 0..1 audio level for the current state."""
        target = 0.0

        if state == UltronState.LISTENING:
            if not self._running:
                self.start_listening()
            with self._lock:
                target = min(1.0, self._level)
        else:
            if self._running:
                self.stop()

            if state == UltronState.SPEAKING and speaking_fn():
                self._speak_phase += dt * 9.0
                syllable = abs(math.sin(self._speak_phase * 1.7)) ** 0.55
                bass = (math.sin(self._speak_phase * 0.85) * 0.5 + 0.5) * 0.35
                burst = max(0.0, math.sin(self._speak_phase * 4.3)) ** 2.0 * 0.4
                self._speak_energy = min(1.0, syllable * 0.55 + bass + burst + 0.12)
                target = self._speak_energy
            elif state == UltronState.IDLE:
                self._speak_phase += dt * 0.6
                target = 0.06 + 0.04 * math.sin(self._speak_phase * 1.2)
                self._speak_energy *= 0.92
            else:
                self._speak_energy *= 0.85

        coeff = AUDIO_ATTACK if target > self._level else AUDIO_RELEASE
        self._level += (target - self._level) * min(1.0, coeff * dt * 60.0)
        return float(np.clip(self._level, 0.0, 1.0))

    @property
    def level(self) -> float:
        return self._level

    def shutdown(self) -> None:
        self.stop()
