"""
speech.py - ULTRON Continuous PyAudio Capture & Whisper Transcription Engine

KEY ENGINEERING RECOVERY:
  1. Permanent PyAudio Stream: Bypasses SpeechRecognition's slow open/close mic latency.
     The microphone remains open continuously at its native hardware rate (44100Hz/48000Hz),
     minimizing startup and phrase response latency.
  2. Custom Energy-Gate VAD: Analyzes the audio stream in real-time, detecting speech
     and silence boundaries automatically.
  3. Dynamic Calibration: Automatically measures ambient floor, sets optimal threshold,
     and adjusts for quiet inputs (down to minimum 4 RMS).
  4. Speaker Echo Prevention: Pauses mic capture during TTS playback and aggressively
     flushes PyAudio input buffers right after speaking finishes.
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

import collections
import pyaudio
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


# ── Wake words (expanded with common Whisper phonetic variations) ──────────────
WAKE_WORDS = {
    "ultron", "hey ultron", "hi ultron", "ok ultron", "okay ultron",
    "hello ultron", "yo ultron", "bro ultron", "ultram", "ultra",
    "altron", "all tron", "ul tron", "hey ultra", "hi ultra", "hey altron",
    "hey outron", "hey autron", "hey eltron", "hey ol tron", "outron", "autron",
    "eltron", "oltron", "aultron", "haltron", "alteron", "outeron", "alltron",
    "hey assistant", "hey ul"
}

# ── Live Mic RMS for Visualizer ────────────────────────────────────────────────
_latest_mic_rms = 0.0
_rms_lock = threading.Lock()

def get_latest_mic_rms() -> float:
    with _rms_lock:
        return _latest_mic_rms

def _set_latest_mic_rms(val: float) -> None:
    global _latest_mic_rms
    with _rms_lock:
        _latest_mic_rms = val

# ── Faster-Whisper model ──────────────────────────────────────────────────────
print("[VOICE] Loading Faster-Whisper model...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
print("[VOICE] Faster-Whisper model ready.")

# ── Detect real hardware microphone parameters ─────────────────────────────────
def _probe_mic() -> tuple[int, int, int]:
    try:
        p = pyaudio.PyAudio()
        info = p.get_default_input_device_info()
        idx      = int(info['index'])
        rate     = int(info['defaultSampleRate'])
        channels = min(int(info['maxInputChannels']), 2)
        p.terminate()
        print(f"[VOICE] Mic detected: device={idx}, native_rate={rate}Hz, channels={channels}")
        return idx, rate, channels
    except Exception as e:
        print(f"[VOICE] Mic probe failed: {e}. Using safe defaults.")
        return None, 44100, 1

def _measure_ambient_rms(device_idx: Optional[int], rate: int, channels: int) -> float:
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=rate,
            input=True,
            input_device_index=device_idx,
            frames_per_buffer=1024,
        )
        rms_vals = []
        # Measure for 0.4 seconds
        for _ in range(int(rate / 1024 * 0.4)):
            data = stream.read(1024, exception_on_overflow=False)
            rms_vals.append(audioop.rms(data, 2))
        stream.stop_stream()
        stream.close()
        p.terminate()
        ambient = sum(rms_vals) / len(rms_vals) if rms_vals else 1.0
        print(f"[VOICE] Measured ambient noise floor RMS: {ambient:.1f}")
        return ambient
    except Exception as e:
        print(f"[VOICE] Ambient noise floor measurement failed: {e}. Using default.")
        return 1.0

_MIC_IDX, _MIC_RATE, _MIC_CHANNELS = _probe_mic()
_AMBIENT_RMS = _measure_ambient_rms(_MIC_IDX, _MIC_RATE, _MIC_CHANNELS)

# Dynamic threshold with sensitive multiplier for speech onset (1.2x ambient)
_energy_threshold = max(2, min(25, int(_AMBIENT_RMS * 1.2)))
print(f"[VOICE] Final calibrated energy threshold set to {_energy_threshold}")


# ── Permanent Audio Stream ─────────────────────────────────────────────────────
_pa_instance = None
_mic_stream = None


def init_mic() -> None:
    """Initialize the permanent input stream to bypass start/stop latencies."""
    global _pa_instance, _mic_stream
    if _mic_stream is not None:
        return
    try:
        _pa_instance = pyaudio.PyAudio()
        _mic_stream = _pa_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=_MIC_RATE,
            input=True,
            input_device_index=_MIC_IDX,
            frames_per_buffer=1024,
        )
        print(f"[VOICE] Permanent mic stream opened at {_MIC_RATE}Hz.")
    except Exception as e:
        print(f"[VOICE] ERROR: Failed to open permanent mic stream: {e}")


def flush_mic_stream() -> None:
    """Discards all accumulated buffered frames in PyAudio buffer."""
    global _mic_stream
    if _mic_stream is None:
        return
    try:
        avail = _mic_stream.get_read_available()
        if avail > 0:
            _mic_stream.read(avail, exception_on_overflow=False)
            print(f"[VOICE] Flushed {avail} frames from PyAudio buffer.")
    except Exception:
        pass


def _wait_if_speaking() -> None:
    """Block microphone capture while ULTRON TTS plays to prevent echo loops."""
    if _speaking_event.is_set():
        print("[VOICE] TTS active — pausing mic capture.")
        _speaking_event.wait()
        # Sleep briefly for speaker echo to dissipate, then flush
        time.sleep(0.42)
        flush_mic_stream()


# ── WAV Resampling ─────────────────────────────────────────────────────────────
def _resample_wav_16k(wav_bytes: bytes) -> bytes:
    """Resample input stream from native rates down to Whisper's 16000Hz mono."""
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            nch, sw, fr, nf = r.getparams()[:4]
            frames = r.readframes(nf)

        if fr == 16000:
            return wav_bytes

        # Resample frame rate
        state = None
        resampled_frames, state = audioop.ratecv(frames, sw, 1, fr, 16000, state)

        out = io.BytesIO()
        with wave.open(out, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(sw)
            w.setframerate(16000)
            w.writeframes(resampled_frames)
        return out.getvalue()
    except Exception as e:
        print(f"[VOICE] Audio resampling down to 16k failed: {e}")
        return wav_bytes


# ── Audio normalization ────────────────────────────────────────────────────────
def _normalize_wav(wav_bytes: bytes) -> bytes:
    """Boost voice audio gain so Whisper handles whispers cleanly."""
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


# ── Transcription ──────────────────────────────────────────────────────────────
def transcribe_audio_bytes(wav_bytes: bytes) -> str:
    """Transcribe WAV bytes using Faster-Whisper."""
    if not wav_bytes:
        return ""

    resampled = _resample_wav_16k(wav_bytes)
    normalized = _normalize_wav(resampled)

    filename = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized)
            filename = f.name

        print("[VOICE] [WHISPER] Starting model transcription...")
        segments, _info = model.transcribe(
            filename,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            vad_filter=True,   # Filter silence / hallucination
            condition_on_previous_text=False,
        )
        raw = " ".join(s.text.strip() for s in segments).strip()
        if not raw:
            print("[VOICE] [WHISPER] Transcript is empty.")
            return ""

        # ── Hallucination filter ──────────────────────────────────────────
        # Whisper commonly hallucinates these phrases on silence/noise.
        _HALLUCINATIONS = [
            "thank you for watching", "see you in the next video",
            "thanks for watching", "please subscribe", "like and subscribe",
            "don't forget to", "www.", "http", "subtitles by",
        ]
        raw_lower = raw.lower()
        if any(h in raw_lower for h in _HALLUCINATIONS):
            print(f"[VOICE] [WHISPER] Hallucination detected, ignoring: '{raw[:60]}'")
            return ""

        final = correct(raw)
        print(f"[VOICE] [WHISPER] Transcript: '{final}'")
        return final
    except Exception as e:
        print(f"[VOICE] [WHISPER] ERROR: Transcription failed: {e}")
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
    Listens continuously using the permanent PyAudio stream.
    Applies custom energy-gate VAD to detect phrase start/stop points.
    Uses pre-buffer ring buffer so onset speech ("Hey") is never clipped.
    """
    global _mic_stream
    _wait_if_speaking()

    if _mic_stream is None:
        init_mic()
        if _mic_stream is None:
            print("[VOICE ERROR] Microphone failed to initialize. Aborting audio capture.")
            time.sleep(1.0)
            return b""

    flush_mic_stream()
    print(f"[VOICE] Listening... Gate threshold={_energy_threshold}")

    speech_frames = []
    speaking_started = False

    # Ring buffer to preserve 4 chunks (~100ms) before onset detection
    pre_buffer = collections.deque(maxlen=4)

    # VAD limits
    silence_limit_chunks = int(_MIC_RATE / 1024 * 0.70)  # 0.70s of silence marks end
    silence_counter = 0
    max_chunks = int(_MIC_RATE / 1024 * phrase_time_limit)
    timeout_chunks = int(_MIC_RATE / 1024 * timeout)
    chunk_counter = 0

    while True:
        _wait_if_speaking()

        try:
            data = _mic_stream.read(1024, exception_on_overflow=False)
        except Exception as e:
            print(f"[VOICE] Mic stream read warning: {e}")
            time.sleep(0.01)
            continue

        rms_val = audioop.rms(data, 2)
        _set_latest_mic_rms(float(rms_val))

        if not speaking_started:
            # Maintain rolling ring buffer of quiet pre-speech audio
            pre_buffer.append(data)

            # Listening for speech onset
            if rms_val > _energy_threshold:
                print(f"[VOICE] Speech onset detected (RMS={rms_val} > threshold={_energy_threshold})")
                speaking_started = True
                # Include pre-buffer audio so start of utterance is preserved
                speech_frames.extend(pre_buffer)
            else:
                chunk_counter += 1
                if chunk_counter > timeout_chunks:
                    print("[VOICE] Silence timeout reached.")
                    return b""
        else:
            # Accumulating active speech
            speech_frames.append(data)
            if rms_val <= _energy_threshold:
                silence_counter += 1
                if silence_counter > silence_limit_chunks:
                    print("[VOICE] Speech offset detected (silence threshold met).")
                    break
            else:
                silence_counter = 0

            if len(speech_frames) > max_chunks:
                print("[VOICE] Phrase time limit exceeded.")
                break

    if not speech_frames:
        return b""

    # Package frames to WAV bytes
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_MIC_RATE)
        w.writeframes(b"".join(speech_frames))

    return out.getvalue()



def listen() -> str:
    wav = listen_for_audio()
    if not wav:
        return ""
    return transcribe_audio_bytes(wav)


# Eagerly initialize mic stream at startup to eliminate lag
init_mic()
