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

# ── Locked voice config ────────────────────────────────────────────────────────
VOICE = "en-GB-RyanNeural"
RATE  = "-10%"
PITCH = "-14Hz"

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()

_lock         = threading.Lock()
_is_speaking  = False
_ready_event  = threading.Event()   # set when audio starts playing
_done_event   = threading.Event()   # set when playback finishes
_stop_flag    = threading.Event()   # set to interrupt current playback


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


def _play(text: str) -> None:
    """Generates and plays TTS. Runs in background thread."""
    global _is_speaking
    filename = ""
    _ready_event.clear()
    _done_event.clear()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            filename = f.name

        # ── Generate audio (this is the slow step: 1-3s on Jio hotspot) ──────
        try:
            clean = _fix_phonetics(text)
            communicate = edge_tts.Communicate(
                text=clean, voice=VOICE, rate=RATE, pitch=PITCH
            )
            # Use strict 6.0s timeout to prevent network hang deadlock
            asyncio.run(asyncio.wait_for(communicate.save(filename), timeout=6.0))
        except Exception as e:
            print(f"[TTS ERROR] edge-tts generation failed or timed out: {e}")
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
                print(f"[TTS] Playing: '{text[:60]}...'")
            except Exception as e:
                print(f"[TTS ERROR] Pygame play error: {e}")
                _set_speaking(False)
                _done_event.set()
                return

        # Signal that audio is NOW actually playing
        _ready_event.set()

        # Wait for playback to finish (with live voice barge-in detection)
        while pygame.mixer.music.get_busy():
            if _stop_flag.is_set():
                pygame.mixer.music.stop()
                break

            # Live voice barge-in: cut off TTS immediately if Harsha speaks over ULTRON
            try:
                from speech import get_latest_mic_rms, _energy_threshold
                rms = get_latest_mic_rms()
                if rms > max(35.0, float(_energy_threshold) * 2.5):
                    print(f"[TTS BARGE-IN] Harsha's voice detected (RMS={rms:.1f}) — stopping ULTRON speech!")
                    _stop_flag.set()
                    pygame.mixer.music.stop()
                    break
            except Exception:
                pass

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
                os.remove(filename)
            except Exception:
                pass


def speak(text: str) -> None:
    """
    Speak text using locked en-GB-RyanNeural voice.
    Returns immediately — playback happens in background thread.
    Call wait_until_done() to block until audio finishes.
    """
    if not text or not text.strip():
        return

    stop()  # Stop any existing playback first
    _stop_flag.clear()
    _set_speaking(True)  # Mark speaking before thread so pipeline waits

    thread = threading.Thread(target=_play, args=(text,), daemon=True)
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