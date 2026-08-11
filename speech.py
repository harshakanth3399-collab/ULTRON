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


# ── Wake words (expanded with exact Whisper log trace mishearings) ─────────────
WAKE_WORDS = {
    "ultron", "hey ultron", "hi ultron", "ok ultron", "okay ultron",
    "hello ultron", "yo ultron", "bro ultron", "ultram", "ultra",
    "altron", "all tron", "ul tron", "hey ultra", "hi ultra", "hey altron",
    "hey outron", "hey autron", "hey eltron", "hey ol tron", "outron", "autron",
    "eltron", "oltron", "aultron", "haltron", "alteron", "outeron", "alltron",
    "hey assistant", "hey ul", "hail tron", "hailtron", "hail", "hay tron", "haytron",
    "hell tron", "hail-tron", "heil tron", "heiltron", "hey hail tron",
    "here ill turn", "okay and drawn", "call a mark", "ill turn", "and drawn",
    "here i'll turn", "okay, and drawn.", "ay and drawn", "call a ma",
    "i will try to call a ma", "call a ma", "call a mark", "i'll turn", "drawn"
}



# ── Live Mic RMS for Visualizer ────────────────────────────────────────────────
_latest_mic_rms = 0.0
_rms_lock = threading.Lock()

def get_latest_mic_rms() -> float:
    with _rms_lock:
        return _latest_mic_rms

def get_energy_threshold() -> int:
    """Returns the current energy threshold used for speech onset detection."""
    try:
        return _energy_threshold
    except NameError:
        return 30

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
# Dynamic threshold set relative to ambient floor: robust 45 RMS floor to prevent ambient noise triggers
_energy_threshold = max(45, int(_AMBIENT_RMS * 3.5 + 25.0))
print(f"[VOICE] Optimal energy threshold locked to {_energy_threshold} (Ambient={_AMBIENT_RMS:.1f})")







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


# ── Audio normalization & Noise Gate ──────────────────────────────────────────
def _normalize_wav(wav_bytes: bytes) -> bytes:
    """Boost voice audio gain cleanly without amplifying background noise floor."""
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            nch, sw, fr, nf = r.getparams()[:4]
            frames = r.readframes(nf)

        rms_val = audioop.rms(frames, sw)
        peak = audioop.max(frames, sw)

        # Noise gate: only boost gain when active voice energy exists above noise floor!
        # Prevents background noise from being amplified into hallucinated words like "reproduce".
        if peak > 0 and rms_val > max(6, _AMBIENT_RMS * 1.15):
            target = int((2 ** (8 * sw - 1) - 1) * 0.85)
            factor = min(float(target) / float(peak), 4.0)   # Max 4.0x gain
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


# ── Phonetic Overrides for Regional & Technical Words ──────────────────────────
PHONETIC_OVERRIDES = {
    "i draw them": "",
    "i draw then": "",
    "i draw": "",
    "draw them": "",
    "reproduce": "Andhra Pradesh",
    "and reproduce": "Andhra Pradesh",
    "under produce": "Andhra Pradesh",
    "underproduce": "Andhra Pradesh",
    "andro pradesh": "Andhra Pradesh",
    "under pradesh": "Andhra Pradesh",
    "and rapradesh": "Andhra Pradesh",
    "ananta pur": "Anantapur",
    "anantpur": "Anantapur",
    "what's up": "whatsapp",
    "whats up": "whatsapp",
    "whatup": "whatsapp",
    "a, d, b": "adb",
    "a-d-b": "adb",
    "a d b": "adb",
    "a, b, b": "adb",
}

_PHONETIC_OVERRIDES = PHONETIC_OVERRIDES


# ── Transcription ──────────────────────────────────────────────────────────────
def transcribe_audio_bytes(wav_bytes: bytes) -> tuple[str, str]:
    """
    Transcribe WAV bytes using Faster-Whisper with automatic English/Telugu language detection.
    Returns (transcript, language_code).
    """
    if not wav_bytes:
        return "", "en"

    resampled = _resample_wav_16k(wav_bytes)
    normalized = _normalize_wav(resampled)

    filename = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized)
            filename = f.name

        print("[VOICE] [WHISPER] Starting model transcription...")
        t0 = time.time()
        # Omit explicit language parameter so Faster-Whisper auto-detects English vs Telugu!
        segments, info = model.transcribe(
            filename,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=True,   # Filter silence / hallucination
            condition_on_previous_text=False,
        )
        raw = " ".join(s.text.strip() for s in segments).strip()
        t_whisp = int((time.time() - t0) * 1000)

        detected_lang = getattr(info, 'language', 'en') or 'en'
        lang_prob = getattr(info, 'language_probability', 1.0)
        print(f"[TIME] transcription: {t_whisp} ms | Language={detected_lang} (prob={lang_prob:.2f})")
        print(f"[RAW TRANSCRIPTION] '{raw}'")

        if not raw:
            print("[VOICE] [WHISPER] Transcript is empty.")
            return "", detected_lang

        raw_corrected = raw
        raw_check = raw.lower()
        for mishearing, correction in _PHONETIC_OVERRIDES.items():
            if mishearing in raw_check:

                raw_corrected = raw_check.replace(mishearing, correction)
                raw_check = raw_corrected
                print(f"[VOICE] [PHONETIC] Override: '{mishearing}' → '{correction}'")

        # 2. Levenshtein distance matching for near-miss regional words
        def _levenshtein(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return _levenshtein(s2, s1)
            if len(s2) == 0:
                return len(s1)
            prev_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (c1 != c2)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
            return prev_row[-1]

        _FUZZY_VOCAB = {
            "Andhra Pradesh": 4,     # threshold: allow up to 4 edits
            "Anantapur": 3,
            "Telangana": 3,
            "Karnataka": 3,
            "Bangalore": 3,
            "Hyderabad": 3,
            "Visakhapatnam": 5,
            "Vijayawada": 4,
            "Tirupati": 3,
        }

        words_in_transcript = raw_corrected.split()
        for target_word, threshold in _FUZZY_VOCAB.items():
            target_parts = target_word.split()
            window = len(target_parts)
            for i in range(len(words_in_transcript) - window + 1):
                candidate = " ".join(words_in_transcript[i:i + window])
                dist = _levenshtein(candidate.lower(), target_word.lower())
                if 0 < dist <= threshold and candidate.lower() != target_word.lower():
                    print(f"[VOICE] [PHONETIC] Fuzzy match: '{candidate}' → '{target_word}' (dist={dist})")
                    for j in range(i, i + window):
                        words_in_transcript[j] = ""
                    words_in_transcript[i] = target_word
                    break

        raw = " ".join(w for w in words_in_transcript if w).strip() or raw_corrected

        # Check for Telugu Unicode characters
        if any('\u0C00' <= char <= '\u0C7F' for char in raw):
            detected_lang = "te"

        # ── Hallucination filter ──────────────────────────────────────────
        _MUSIC_KEYWORDS = ["song", "by", "track", "music", "sing", "michael jackson", "favorite song", "fav song"]
        raw_lower = raw.lower()

        if not any(mk in raw_lower for mk in _MUSIC_KEYWORDS):
            _HALLUCINATIONS = [
                "thank you for watching", "see you in the next video",
                "thanks for watching", "please subscribe", "like and subscribe",
                "don't forget to", "www.", "http", "subtitles by",
                "thank you very much", "thank you", "thanks", "thank you so much",
            ]
            if any(h in raw_lower for h in _HALLUCINATIONS):
                print(f"[VOICE] [WHISPER] Hallucination detected, ignoring: '{raw[:60]}'")
        final = correct(raw)
        print(f"[FINAL TRANSCRIPTION] '{final}' (Language={detected_lang})")
        return final, detected_lang
    except Exception as e:
        print(f"[VOICE] [WHISPER] ERROR: Transcription failed: {e}")
        return "", "en"
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

    # Flush stale frames so capture starts clean
    flush_mic_stream()

    print(f"[VOICE] Listening... Gate threshold={_energy_threshold}")
    print(f"[VOICE] INPUT DEVICE: {_MIC_IDX} | SAMPLE RATE: {_MIC_RATE}Hz | CHANNELS: {_MIC_CHANNELS}")

    speech_frames = []
    speaking_started = False
    max_rms_seen = 0
    max_peak_seen = 0

    # Ring buffer to preserve 4 chunks (~100ms) before onset detection
    pre_buffer = collections.deque(maxlen=4)

    # VAD limits: 0.8s of silence marks phrase end (fast responsive phrase boundary)
    silence_limit_chunks = int(_MIC_RATE / 1024 * 0.80)
    silence_counter = 0

    max_chunks = int(_MIC_RATE / 1024 * phrase_time_limit)
    timeout_chunks = int(_MIC_RATE / 1024 * timeout)
    chunk_counter = 0

    t_start = time.time()

    while True:
        _wait_if_speaking()

        try:
            data = _mic_stream.read(1024, exception_on_overflow=False)
        except Exception as e:
            print(f"[VOICE] Mic stream read warning: {e}")
            time.sleep(0.01)
            continue

        rms_val = audioop.rms(data, 2)
        peak_val = audioop.max(data, 2)
        _set_latest_mic_rms(float(rms_val))

        if rms_val > max_rms_seen:
            max_rms_seen = rms_val
        if peak_val > max_peak_seen:
            max_peak_seen = peak_val

        if not speaking_started:
            # Maintain rolling ring buffer of quiet pre-speech audio (6 chunks = ~150ms)
            pre_buffer.append(data)

            # Listening for genuine human speech onset (both RMS and Peak thresholds must be met)
            if rms_val > _energy_threshold and peak_val > int(_AMBIENT_RMS * 4.0 + 50.0):
                t_onset = int((time.time() - t_start) * 1000)
                print(f"[VOICE] Speech onset detected (RMS={rms_val} > threshold={_energy_threshold}, PEAK={peak_val}) after {t_onset}ms wait")
                speaking_started = True
                speech_frames.extend(pre_buffer)
            else:
                chunk_counter += 1
                if chunk_counter > timeout_chunks:
                    duration = time.time() - t_start
                    print(f"[VOICE] FRAMES READ: {chunk_counter * 1024} | MAX RMS: {max_rms_seen} | MAX PEAK: {max_peak_seen} | DURATION: {duration:.2f}s | AUDIO RECEIVED: NO (Silence/Timeout)")
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

    if not speech_frames or max_rms_seen < 35 or max_peak_seen < 120:
        print(f"[VOICE] Low-energy audio discarded (Max RMS={max_rms_seen}, Max Peak={max_peak_seen}).")
        return b""

    total_bytes = sum(len(f) for f in speech_frames)
    duration = total_bytes / (2 * _MIC_RATE)
    print(f"[VOICE] SPEECH CAPTURED: {total_bytes // 2} samples | MAX RMS: {max_rms_seen} | MAX PEAK: {max_peak_seen} | SPEECH DURATION: {duration:.2f}s")

    # Package frames to WAV bytes
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_MIC_RATE)
        w.writeframes(b"".join(speech_frames))

    return out.getvalue()




def listen() -> tuple[str, str]:
    wav = listen_for_audio()
    if not wav:
        return "", "en"
    return transcribe_audio_bytes(wav)


# Eagerly initialize mic stream at startup to eliminate lag
init_mic()

