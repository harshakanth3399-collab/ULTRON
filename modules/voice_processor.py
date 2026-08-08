"""James Spader / MCU Movie Ultron Metallic Voice Processing Engine."""

from __future__ import annotations

import io
import wave
import numpy as np


def apply_ultron_metallic_filter(raw_wav_bytes: bytes) -> bytes:
    """Applies James Spader MCU Ultron metallic ring-modulation and dual-voice effect to speech audio."""
    try:
        bio = io.BytesIO(raw_wav_bytes)
        with wave.open(bio, 'rb') as r:
            params = r.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            frames = r.readframes(nframes)

        # Convert to numpy array
        if sampwidth == 2:
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        else:
            return raw_wav_bytes

        # Metallic Ring Modulation (Subtle 35Hz carrier frequency for cybernetic robotic undertone)
        t = np.arange(len(samples)) / float(framerate)
        ring_mod = np.sin(2.0 * np.pi * 35.0 * t) * 0.12
        metallic_samples = samples * (1.0 + ring_mod)

        # Dual Voice Pitch/Echo Layer (14ms delayed robotic metallic resonance)
        delay_samples = int(framerate * 0.014)
        delayed_samples = np.zeros_like(metallic_samples)
        delayed_samples[delay_samples:] = metallic_samples[:-delay_samples] * 0.35

        final_samples = np.clip(metallic_samples + delayed_samples, -32768.0, 32767.0).astype(np.int16)

        out_bio = io.BytesIO()
        with wave.open(out_bio, 'wb') as w:
            w.setnchannels(nchannels)
            w.setsampwidth(sampwidth)
            w.setframerate(framerate)
            w.writeframes(final_samples.tobytes())

        return out_bio.getvalue()
    except Exception as e:
        print("Ultron Voice Effect Note:", e)
        return raw_wav_bytes
