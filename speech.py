"""Speech Recognition & Wake Word Detection Engine for ULTRON."""

from __future__ import annotations

import io
import os
import time
import wave
import audioop
import tempfile
import speech_recognition as sr
from faster_whisper import WhisperModel

try:
    from corrector import correct
except Exception:
    def correct(text: str) -> str:
        return text

try:
    from speech_engine import speaking
except Exception:
    def speaking() -> bool:
        return False


# Faster-Whisper Model locked to English only
print("[VOICE] Loading Faster-Whisper English model...")
model = WhisperModel(
    "tiny.en",
    device="cpu",
    compute_type="int8"
)
print("[VOICE] Faster-Whisper English model ready.")

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.6
recognizer.non_speaking_duration = 0.2
recognizer.phrase_threshold = 0.3

WAKE_WORDS = {"ultron", "hey ultron", "hi ultron", "ok ultron", "okay ultron", "hello ultron"}


def _normalize_wav_bytes(wav_bytes: bytes) -> bytes:
    """Normalize WAV audio amplitude safely."""
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            params = r.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            frames = r.readframes(nframes)

        current_peak = audioop.max(frames, sampwidth)
        max_possible = (2 ** (8 * sampwidth - 1) - 1)
        desired_peak = int(max_possible * 0.95)

        factor = float(desired_peak) / float(current_peak) if current_peak > 0 else 1.0
        if factor > 8.0:
            factor = 8.0

        if abs(factor - 1.0) > 0.01:
            frames = audioop.mul(frames, sampwidth, factor)

        out_bio = io.BytesIO()
        with wave.open(out_bio, 'wb') as w:
            w.setnchannels(nchannels)
            w.setsampwidth(sampwidth)
            w.setframerate(framerate)
            w.writeframes(frames)
        return out_bio.getvalue()
    except Exception:
        return wav_bytes


def _wait_if_speaking() -> None:
    """Prevents ULTRON from hearing its own TTS voice."""
    if speaking():
        print("[VOICE] TTS playback active — pausing microphone capture.")
        while speaking():
            time.sleep(0.05)
        time.sleep(0.25)  # 250ms grace period for speaker echo to dissipate


def transcribe_audio_bytes(wav_bytes: bytes) -> str:
    """Transcribes audio bytes strictly to English using Faster-Whisper."""
    if not wav_bytes:
        return ""

    normalized = _normalize_wav_bytes(wav_bytes)
    filename = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized)
            filename = f.name

        segments, info = model.transcribe(
            filename,
            language="en",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False
        )

        raw_text = "".join(segment.text for segment in segments).strip()
        final_text = correct(raw_text)
        return final_text
    except Exception as e:
        print(f"[VOICE] Transcription exception: {e}")
        return ""
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass


def listen_for_audio(timeout: float = 6.0, phrase_time_limit: float = 8.0) -> bytes:
    """Captures microphone audio safely with TTS self-hearing protection."""
    _wait_if_speaking()

    try:
        with sr.Microphone(sample_rate=16000) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.1)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            return audio.get_wav_data()
    except sr.WaitTimeoutError:
        return b""
    except Exception as e:
        print(f"[VOICE] Microphone capture error: {e}")
        return b""


def listen() -> str:
    """Backward-compatible single-shot listen function."""
    wav_bytes = listen_for_audio(timeout=6.0, phrase_time_limit=8.0)
    if not wav_bytes:
        return ""
    return transcribe_audio_bytes(wav_bytes)
