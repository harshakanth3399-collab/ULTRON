"""
speech.py - ULTRON Microphone Capture & Transcription Engine

REAL ROOT CAUSES FIXED (confirmed by hardware diagnostic):
  1. energy_threshold = 200 while ambient RMS = 1.0
     -> voice NEVER clears the threshold -> silence/timeout loop forever
     Fixed: auto-calibrate threshold at startup from real hardware measurement

  2. Default mic (Intel Smart Sound Array) native rate = 44100 Hz
     -> opening at 16000 Hz can fail silently on this driver
     Fixed: use native device sample rate, resample to 16000 for Whisper

  3. SpeechRecognition adjust_for_ambient_noise() was removing this fix
     Fixed: do NOT call adjust_for_ambient_noise()

  4. vad_filter=True dropped short phrases like "Hey Ultron"
     Fixed: vad_filter=False, rely on energy gate only
"""
from __future__ import annotations

import audioop
import io
import os
import struct
import tempfile
import threading
import time
import wave
from typing import Optional

import pyaudio
import speech_recognition as sr
from faster_whisper import WhisperModel

try:
    from corrector import correct
except Exception:
    def correct(text: str) -> str:
        return text

# ── Speaking guard (shared with speech_engine) ────────────────────────────────
_speaking_event = threading.Event()


def set_speaking(state: bool) -> None:
    if state:
        _speaking_event.set()
    else:
        _speaking_event.clear()


def speaking() -> bool:
    return _speaking_event.is_set()


# ── Wake words ────────────────────────────────────────────────────────────────
WAKE_WORDS = {
    "ultron", "hey ultron", "hi ultron", "ok ultron", "okay ultron",
    "hello ultron", "yo ultron", "bro ultron", "ultram", "ultra",
    "altron", "all tron", "ul tron", "hey ultra", "hi ultra", "hey altron"
}

# ── Faster-Whisper model ──────────────────────────────────────────────────────
print("[VOICE] Loading Faster-Whisper model...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
print("[VOICE] Faster-Whisper model ready.")

# ── Detect real hardware microphone parameters ─────────────────────────────────
def _probe_mic() -> tuple[int, int, int]:
    """
    Returns (device_index, native_rate, channels) for the default input device.
    Uses the device's NATIVE sample rate to avoid resampling errors.
    """
    try:
        p = pyaudio.PyAudio()
        info = p.get_default_input_device_info()
        idx      = int(info['index'])
        rate     = int(info['defaultSampleRate'])
        channels = min(int(info['maxInputChannels']), 2)
        p.terminate()
        print(f"[VOICE] Mic: device={idx}, native_rate={rate}Hz, channels={channels}")
        return idx, rate, channels
    except Exception as e:
        print(f"[VOICE] Mic probe failed: {e}. Using defaults.")
        return None, 44100, 1

def _measure_ambient_rms(device_idx: Optional[int], rate: int, channels: int) -> float:
    """
    Open mic for 0.5s and measure real ambient RMS.
    Returns the measured value so we can set energy_threshold appropriately.
    """
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_idx,
            frames_per_buffer=1024,
        )
        rms_vals = []
        for _ in range(int(rate / 1024 * 0.5)):  # 0.5 seconds
            data = stream.read(1024, exception_on_overflow=False)
            rms_vals.append(audioop.rms(data, 2))
        stream.stop_stream()
        stream.close()
        p.terminate()
        ambient = sum(rms_vals) / len(rms_vals) if rms_vals else 10.0
        print(f"[VOICE] Ambient RMS: {ambient:.1f}")
        return ambient
    except Exception as e:
        print(f"[VOICE] Ambient probe failed: {e}. Using safe default.")
        return 10.0

_MIC_IDX, _MIC_RATE, _MIC_CHANNELS = _probe_mic()
_AMBIENT_RMS = _measure_ambient_rms(_MIC_IDX, _MIC_RATE, _MIC_CHANNELS)

# ── SpeechRecognition setup with HARDWARE-CALIBRATED threshold ────────────────
recognizer = sr.Recognizer()

# KEY FIX: Set threshold based on REAL hardware measurement
# Use ambient * 3.5 (well above noise, well below normal speech)
# Minimum 4, maximum 300
_energy_threshold = max(4, min(300, int(_AMBIENT_RMS * 3.5)))
recognizer.energy_threshold        = _energy_threshold
recognizer.dynamic_energy_threshold = False   # Never auto-adjust
recognizer.pause_threshold          = 0.9
recognizer.non_speaking_duration    = 0.35
recognizer.phrase_threshold         = 0.2

print(f"[VOICE] energy_threshold set to {_energy_threshold} (ambient={_AMBIENT_RMS:.1f})")


# ── Audio normalization ────────────────────────────────────────────────────────
def _normalize_wav(wav_bytes: bytes) -> bytes:
    """Boost quiet recordings so Whisper can hear clearly."""
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            nch, sw, fr, nf = r.getparams()[:4]
            frames = r.readframes(nf)

        peak = audioop.max(frames, sw)
        if peak > 0:
            target = int((2 ** (8 * sw - 1) - 1) * 0.85)
            factor = min(float(target) / float(peak), 8.0)
            if abs(factor - 1.0) > 0.05:
                frames = audioop.mul(frames, sw, factor)

        out = io.BytesIO()
        with wave.open(out, 'wb') as w:
            w.setnchannels(nch)
            w.setsampwidth(sw)
            w.setframerate(fr)
            w.writeframes(frames)
        return out.getvalue()
    except Exception:
        return wav_bytes


def _wait_if_speaking() -> None:
    """Block microphone capture while ULTRON TTS is playing."""
    if _speaking_event.is_set():
        print("[VOICE] TTS active — pausing mic until playback finishes.")
        _speaking_event.wait()
        time.sleep(0.40)


# ── Transcription ──────────────────────────────────────────────────────────────
def transcribe_audio_bytes(wav_bytes: bytes) -> str:
    """
    Transcribes WAV to English using Faster-Whisper.
    vad_filter=False: do NOT drop short phrases like 'Hey Ultron'.
    """
    if not wav_bytes:
        return ""

    normalized = _normalize_wav(wav_bytes)
    filename = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized)
            filename = f.name

        print("[VOICE] Transcription start...")
        segments, _info = model.transcribe(
            filename,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            vad_filter=False,          # Do NOT drop short wake phrases
            condition_on_previous_text=False,
        )
        raw = " ".join(s.text.strip() for s in segments).strip()
        if not raw:
            print("[VOICE] Transcript: (empty)")
            return ""
        final = correct(raw)
        print(f"[VOICE] Transcript: '{final}'")
        return final
    except Exception as e:
        print(f"[VOICE] Transcription error: {e}")
        return ""
    finally:
        if filename:
            try:
                os.remove(filename)
            except Exception:
                pass


# ── Microphone audio capture ───────────────────────────────────────────────────
def listen_for_audio(timeout: float = 7.0, phrase_time_limit: float = 12.0) -> bytes:
    """
    Capture one phrase from microphone.

    KEY FIXES:
      1. Blocks until TTS finishes before opening mic (prevents self-hearing)
      2. Uses hardware native sample rate
      3. Logs actual device, rate, RMS received
    """
    _wait_if_speaking()

    try:
        # Use hardware native rate; SpeechRecognition handles the mic
        mic_kwargs = {"sample_rate": _MIC_RATE}
        if _MIC_IDX is not None:
            mic_kwargs["device_index"] = _MIC_IDX

        with sr.Microphone(**mic_kwargs) as source:
            print(f"[VOICE] Mic open: device={_MIC_IDX}, rate={_MIC_RATE}Hz, "
                  f"threshold={recognizer.energy_threshold}")
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
            wav = audio.get_wav_data()
            rms_val = audioop.rms(wav[:min(len(wav), 8192)], 2) if wav else 0
            print(f"[VOICE] Audio captured: {len(wav)} bytes, RMS={rms_val}")
            return wav

    except sr.WaitTimeoutError:
        print("[VOICE] No speech detected within timeout — retrying.")
        return b""
    except Exception as e:
        print(f"[VOICE] Mic capture error: {e}")
        return b""


def listen() -> str:
    """Backward-compatible single-shot listen."""
    wav = listen_for_audio()
    if not wav:
        return ""
    return transcribe_audio_bytes(wav)
