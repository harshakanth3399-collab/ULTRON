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

    # ── Microphone thread ──────────────────────────────────────────────────────

    def _mic_thread(self) -> None:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            # Open at NATIVE rate to match hardware
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,                  # mono for analysis
                rate=self._mic_rate,
                input=True,
                input_device_index=self._mic_idx,
                frames_per_buffer=512,
            )
            self._stream_obj = (p, stream)

            while self._running:
                try:
                    data = stream.read(512, exception_on_overflow=False)
                    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                    rms = float(np.sqrt(np.mean(samples ** 2))) / 32768.0
                    with self._lock:
                        # Normalize: speech is typically 0.01-0.2 RMS normalized
                        self._level = min(1.0, rms * AUDIO_GAIN * 15.0)
                except Exception:
                    pass

            stream.stop_stream()
            stream.close()
            p.terminate()

        except Exception:
            # Fallback: synthesize a gentle pulse if mic can't be opened for particles
            while self._running:
                with self._lock:
                    self._level = 0.15 + 0.12 * math.sin(time.time() * 2.0)
                time.sleep(0.03)

    def start_listening(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._mic_thread, daemon=True, name="AudioAnalyzer-Mic"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stream_obj = None
        self._thread = None

    # ── Main update (called every frame) ──────────────────────────────────────

    def update(self, dt: float, state: UltronState, speaking_fn) -> float:
        """
        Returns smoothed 0..1 audio level for the particle engine.

        LISTENING: drives from real mic
        SPEAKING:  drives from TTS syllable envelope (no mic feedback)
        IDLE:      gentle autonomous breath
        """
        target = 0.0

        if state == UltronState.LISTENING:
            if not self._running:
                self.start_listening()
            with self._lock:
                target = min(1.0, self._level)

        else:
            # Stop mic capture in non-listening states
            if self._running:
                self.stop()

            if state == UltronState.SPEAKING and speaking_fn():
                # Synthesized syllable model: approximates natural speech rhythm
                self._speak_phase += dt * 9.5
                syllable = abs(math.sin(self._speak_phase * 1.65)) ** 0.5
                bass     = (math.sin(self._speak_phase * 0.82) * 0.5 + 0.5) * 0.30
                burst    = max(0.0, math.sin(self._speak_phase * 4.1)) ** 2.0 * 0.35
                self._speak_energy = min(1.0, syllable * 0.55 + bass + burst + 0.14)
                target = self._speak_energy

            elif state == UltronState.IDLE:
                # Gentle breathe: slow sinusoidal with subtle variation
                self._idle_phase += dt * 0.55
                target = 0.07 + 0.05 * math.sin(self._idle_phase * 1.15)
                target += 0.02 * math.sin(self._idle_phase * 3.1)
                self._speak_energy *= 0.90

            else:
                # PROCESSING / TRANSCRIBING: steady low pulse
                self._idle_phase += dt * 1.8
                target = 0.18 + 0.10 * abs(math.sin(self._idle_phase))
                self._speak_energy *= 0.85

        # Smooth with attack/release
        coeff = AUDIO_ATTACK if target > self._smoothed else AUDIO_RELEASE
        self._smoothed += (target - self._smoothed) * min(1.0, coeff * dt * 60.0)
        self._smoothed = float(np.clip(self._smoothed, 0.0, 1.0))
        return self._smoothed

    @property
    def level(self) -> float:
        return self._smoothed

    def shutdown(self) -> None:
        self.stop()
