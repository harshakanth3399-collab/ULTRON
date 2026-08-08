"""
speech_engine.py — TTS Engine for ULTRON.

LOCKED VOICE: en-GB-RyanNeural (Deep British J.A.R.V.I.S.)
DO NOT CHANGE THE VOICE.

FIXES:
  - Race condition: _is_speaking now set to True BEFORE thread starts,
    cleared only when _play() finishes. This ensures _speak_and_wait()
    cannot return prematurely.
  - speech.set_speaking() syncs the atomic event in speech.py
    so microphone blocks reliably while TTS is playing.
"""

import asyncio
import threading
import edge_tts
import pygame
import os
import tempfile

# ─── Locked Voice Configuration ──────────────────────────────────────────────
VOICE = "en-GB-RyanNeural"
RATE = "-10%"
PITCH = "-14Hz"

pygame.mixer.init()

_lock = threading.Lock()
_is_speaking = False
_current_thread: threading.Thread | None = None


def _fix_phonetics(text: str) -> str:
    """Forces correct single-breath 'Harsha' pronunciation in British TTS."""
    return text.replace("Harsha", "Hur-sha").replace("harsha", "hur-sha")


def _set_speaking_state(state: bool) -> None:
    """Atomically updates speaking state and notifies speech.py."""
    global _is_speaking
    _is_speaking = state
    try:
        import speech
        speech.set_speaking(state)
    except Exception:
        pass


async def _generate(text: str, filename: str) -> None:
    clean = _fix_phonetics(text)
    communicate = edge_tts.Communicate(text=clean, voice=VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(filename)


def _play(text: str) -> None:
    """Generates and plays TTS audio. Runs in background thread."""
    filename = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            filename = f.name

        asyncio.run(_generate(text, filename))

        with _lock:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(30)

        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    except Exception as e:
        print(f"[TTS] Error: {e}")
    finally:
        _set_speaking_state(False)
        if filename:
            try:
                os.remove(filename)
            except Exception:
                pass


def speak(text: str) -> None:
    """
    Speaks text using LOCKED en-GB-RyanNeural voice.

    FIX: Sets _is_speaking=True BEFORE launching the thread so that
    _speak_and_wait() in voice_pipeline cannot return prematurely.
    """
    global _current_thread

    if not text or not text.strip():
        return

    # Stop any existing playback
    stop()

    # Mark speaking TRUE before thread starts (eliminates race condition)
    _set_speaking_state(True)

    _current_thread = threading.Thread(target=_play, args=(text,), daemon=True)
    _current_thread.start()


def stop() -> None:
    """Stops current TTS playback immediately."""
    global _is_speaking
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass
    _set_speaking_state(False)


def speaking() -> bool:
    """Returns True while TTS audio is actively playing."""
    return _is_speaking