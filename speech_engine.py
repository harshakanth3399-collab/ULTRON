"""
speech_engine.py - ULTRON TTS Engine

LOCKED VOICE: en-GB-RyanNeural (Deep British) - DO NOT CHANGE.

ROOT CAUSE FIX:
  The previous version set _is_speaking=True before the audio even started
  generating, then the pipeline polled speaking() which was still False during
  edge-tts network call (1-3s on Jio hotspot), returned prematurely, opened
  microphone WHILE greeting was still playing -> self-hearing -> silent failure.

FIX:
  1. _ready_event: set only when pygame.mixer.music.play() is CONFIRMED called.
  2. _done_event: set when playback ends.
  3. speak() signals _is_speaking=True immediately so pipeline knows to wait,
     but _ready_event gates the actual poll.
  4. wait_until_done() blocks pipeline until playback truly finishes.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading

import edge_tts
import pygame

# ── Dual Voice Configuration ──────────────────────────────────────────────────
VOICE_EN = "en-GB-RyanNeural"
RATE_EN  = "-3%"     # Natural human speed — friendly & conversational
PITCH_EN = "-4Hz"    # Warm & natural tone

VOICE_TE = "te-IN-ShrutiNeural"
RATE_TE  = "+0%"
PITCH_TE = "+0Hz"


# Backward compatibility alias
VOICE = VOICE_EN
RATE  = RATE_EN
PITCH = PITCH_EN

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()

_lock         = threading.Lock()
_is_speaking  = False
_ready_event  = threading.Event()   # set when audio starts playing
_done_event   = threading.Event()   # set when playback finishes
_stop_flag    = threading.Event()   # set to interrupt current playback


def _is_telugu(text: str) -> bool:
    """Checks if text contains Telugu Unicode characters."""
    return any('\u0C00' <= char <= '\u0C7F' for char in text)


def _fix_phonetics(text: str) -> str:
    """Smooth single-breath 'Harsha' in British TTS."""
    return text.replace("Harsha", "Hur-sha").replace("harsha", "hur-sha")


def _set_speaking(state: bool) -> None:
    global _is_speaking
    _is_speaking = state
    try:
        import speech
        speech.set_speaking(state)
    except Exception:
        pass


import re

def _clean_text_for_speech(text: str) -> str:
    """Removes raw HTTP links and IP addresses so TTS never reads 'http colon slash slash' out loud."""
    # Remove http:// or https:// URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove raw IP addresses (e.g. 10.83.134.102:8000)
    text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b', '', text)
    return text.strip()


def _play(text: str, lang: str = "en") -> None:
    """Generates and plays TTS. Runs in background thread."""
    global _is_speaking
    filename = ""
    _ready_event.clear()
    _done_event.clear()

    try:
        spoken_text = _clean_text_for_speech(text)
        if not spoken_text:
            spoken_text = "Check your screen, Sir."

        from ai import validate_and_correct_address
        from modules.memory.profile_manager import get_profile_manager
        pm = get_profile_manager()
        pref_addr = pm.data.get("preferences", {}).get("preferred_address", "Sir")
        spoken_text = validate_and_correct_address(spoken_text, target_address=pref_addr)

        _stop_flag.clear()


        # Create temporary file and close handle immediately to prevent WinError 32 on Windows
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            filename = f.name
            f.close()

        active_lang = pm.get_active_language()

        # Determine voice & prosody based on language & script
        if active_lang == "te" or (lang == "te" and _is_telugu(spoken_text)):
            voice_id, rate_val, pitch_val = VOICE_TE, RATE_TE, PITCH_TE
            clean = spoken_text
            print(f"[TTS] Mode: TELUGU FEMALE ({voice_id})")
        else:
            voice_id, rate_val, pitch_val = VOICE_EN, RATE_EN, PITCH_EN
            clean = _fix_phonetics(spoken_text)
            print(f"[TTS] Mode: ENGLISH MALE FRIENDLY ({voice_id})")


        edge_ok = False
        try:
            communicate = edge_tts.Communicate(
                text=clean, voice=voice_id, rate=rate_val, pitch=pitch_val
            )
            asyncio.run(asyncio.wait_for(communicate.save(filename), timeout=8.0))
            if os.path.exists(filename) and os.path.getsize(filename) > 1024:
                edge_ok = True
        except Exception as e:
            print(f"[TTS NOTE] edge-tts network note ({e}). Using offline fallback.")

        if not edge_ok:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 165)
                voices = engine.getProperty('voices')
                for v in voices:
                    if any(k in v.name.lower() for k in ['david', 'male', 'george', 'hazel', 'uk', 'english']):
                        engine.setProperty('voice', v.id)
                        break
                engine.save_to_file(clean, filename)
                engine.runAndWait()
            except Exception as pyttsx_err:
                print(f"[TTS ERROR] Offline pyttsx3 fallback failed: {pyttsx_err}")
                _set_speaking(False)
                _done_event.set()
                return


        if _stop_flag.is_set():
            _set_speaking(False)
            _done_event.set()
            return

        # ── Load and play ──────────────────────────────────────────────────
        with _lock:
            try:
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                print(f"[TTS] Playing ({voice_id}): '{spoken_text[:60]}...'")
            except Exception as e:
                print(f"[TTS ERROR] Pygame play error: {e}")
                _set_speaking(False)
                _done_event.set()
                return

        _ready_event.set()

        # Wait for playback to finish cleanly
        while pygame.mixer.music.get_busy():
            if _stop_flag.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.Clock().tick(30)

        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    except Exception as e:
        print(f"[TTS ERROR] Unexpected error: {e}")
    finally:
        _set_speaking(False)
        _done_event.set()
        if filename:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                os.remove(filename)
            except Exception:
                pass


def speak(text: str, lang: str = "en") -> None:
    """
    Speak text using locked friendly male (English) or natural female (Telugu) voice.
    Returns immediately — playback happens in background thread.
    Call wait_until_done() to block until audio finishes.
    """
    if not text or not text.strip():
        return

    stop()  # Stop any existing playback first
    _stop_flag.clear()
    _set_speaking(True)  # Mark speaking before thread so pipeline waits

    thread = threading.Thread(target=_play, args=(text, lang), daemon=True)
    thread.start()



def wait_until_done(timeout: float = 25.0) -> None:
    """
    Block caller until TTS playback is fully complete.
    First waits for audio to start playing (timeout 6.0s), then waits for it to finish (timeout 25.0s).
    This eliminates the race condition where the pipeline resumed before audio played.
    """
    # Wait for audio to actually start (survives slow edge-tts generation on Jio)
    if not _ready_event.wait(timeout=6.0):
        print("[TTS ERROR] wait_until_done: timed out waiting for audio to start (network issue?)")
        _set_speaking(False)
        return
    # Now wait for playback to finish
    if not _done_event.wait(timeout=timeout):
        print("[TTS ERROR] wait_until_done: timed out waiting for audio to finish")
        _set_speaking(False)


def stop() -> None:
    """Immediately stop current playback."""
    _stop_flag.set()
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass
    _set_speaking(False)
    _done_event.set()


def speaking() -> bool:
    """Returns True while TTS audio is actively playing."""
    return _is_speaking