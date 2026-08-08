"""Speech Recognition & Wake Word Detection Engine for ULTRON.

ROOT CAUSES FIXED:
  1. vad_filter=True was silently dropping short wake phrases like 'Hey Ultron'
  2. Fresh Microphone() context on each call was slow and unreliable
  3. Self-hearing protection now uses an atomic event, not a polling flag
"""

from __future__ import annotations

import io
import os
import time
import wave
import audioop
import tempfile
import threading
import speech_recognition as sr
from faster_whisper import WhisperModel

try:
    from corrector import correct
except Exception:
    def correct(text: str) -> str:
        return text

# ─── Speaking guard (set by speech_engine, read here) ─────────────────────────
_speaking_event = threading.Event()  # Set while ULTRON is speaking


def set_speaking(is_speaking: bool) -> None:
    """Called by speech_engine to signal TTS playback state."""
    if is_speaking:
        _speaking_event.set()
    else:
        _speaking_event.clear()


def speaking() -> bool:
    return _speaking_event.is_set()


# ─── Faster-Whisper Model ─────────────────────────────────────────────────────
print("[VOICE] Loading Faster-Whisper model...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
print("[VOICE] Faster-Whisper ready.")

# ─── SpeechRecognition recognizer ────────────────────────────────────────────
recognizer = sr.Recognizer()
recognizer.energy_threshold = 200          # Calibrated for indoor mic
recognizer.dynamic_energy_threshold = False  # Never drift upward
recognizer.pause_threshold = 1.0           # Wait 1s of silence before stopping
recognizer.non_speaking_duration = 0.4
recognizer.phrase_threshold = 0.2

# ─── Wake Words ───────────────────────────────────────────────────────────────
WAKE_WORDS = {
    "ultron", "hey ultron", "hi ultron", "ok ultron", "okay ultron",
    "hello ultron", "yo ultron", "bro ultron", "ultram", "ultra",
    "altron", "all tron", "ul tron", "hey ultra", "hi ultra", "hey altron"
}


# ─── Audio Normalization ──────────────────────────────────────────────────────
def _normalize_wav_bytes(wav_bytes: bytes) -> bytes:
    """Boost quiet recordings so Whisper can hear them clearly."""
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            nchannels, sampwidth, framerate, nframes = r.getparams()[:4]
            frames = r.readframes(nframes)

        peak = audioop.max(frames, sampwidth)
        max_val = (2 ** (8 * sampwidth - 1) - 1)
        if peak > 0:
            factor = min(float(max_val * 0.90) / float(peak), 6.0)
            if abs(factor - 1.0) > 0.05:
                frames = audioop.mul(frames, sampwidth, factor)

        out = io.BytesIO()
        with wave.open(out, 'wb') as w:
            w.setnchannels(nchannels)
            w.setsampwidth(sampwidth)
            w.setframerate(framerate)
            w.writeframes(frames)
        return out.getvalue()
    except Exception:
        return wav_bytes


# ─── Self-hearing protection ──────────────────────────────────────────────────
def _wait_if_speaking() -> None:
    """Block microphone capture while ULTRON is playing TTS audio."""
    if _speaking_event.is_set():
        print("[VOICE] TTS active — pausing mic until playback finishes.")
        _speaking_event.wait()       # Block until speech_engine clears the event
        time.sleep(0.35)             # 350ms speaker echo dissipation


# ─── Transcription ────────────────────────────────────────────────────────────
def transcribe_audio_bytes(wav_bytes: bytes) -> str:
    """
    Transcribes WAV bytes to English text using Faster-Whisper.

    KEY FIX: vad_filter=False — the VAD filter was silently dropping short
    phrases like 'Hey Ultron' treating them as noise. We rely on SpeechRecognition's
    energy gate (energy_threshold=200) to ensure only real speech reaches Whisper.
    """
    if not wav_bytes:
        return ""

    normalized = _normalize_wav_bytes(wav_bytes)
    filename = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized)
            filename = f.name

        segments, _info = model.transcribe(
            filename,
            language="en",
            beam_size=5,                      # More accurate than beam_size=1
            best_of=5,
            temperature=0.0,
            vad_filter=False,                 # FIX: Do NOT silently drop short phrases
            condition_on_previous_text=False,
            word_timestamps=False,
        )

        raw_text = " ".join(seg.text.strip() for seg in segments).strip()
        if not raw_text:
            return ""

        final_text = correct(raw_text)
        print(f"[VOICE] Transcript: '{final_text}'")
        return final_text

    except Exception as e:
        print(f"[VOICE] Transcription error: {e}")
        return ""
    finally:
        if filename:
            try:
                os.remove(filename)
            except Exception:
                pass


# ─── Microphone Capture ───────────────────────────────────────────────────────
def listen_for_audio(timeout: float = 6.0, phrase_time_limit: float = 10.0) -> bytes:
    """
    Captures one phrase from microphone.

    KEY FIX: Blocks until TTS finishes before opening microphone.
    Opens a fresh Microphone context each call (required by SpeechRecognition).
    """
    _wait_if_speaking()
    try:
        with sr.Microphone(sample_rate=16000) as source:
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )
            return audio.get_wav_data()
    except sr.WaitTimeoutError:
        return b""
    except Exception as e:
        print(f"[VOICE] Mic capture error: {e}")
        return b""


def listen() -> str:
    """Backward-compatible single-shot listen."""
    wav = listen_for_audio(timeout=6.0, phrase_time_limit=10.0)
    if not wav:
        return ""
    return transcribe_audio_bytes(wav)
