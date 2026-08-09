"""
core/voice_pipeline.py - Complete ULTRON Voice State Machine

State Machine:
    IDLE (wake listening)
    -> WAKE_DETECTED
    -> GREETING
    -> LISTENING (command mode)
    -> RECORDING
    -> TRANSCRIBING
    -> PROCESSING
    -> SPEAKING
    -> LISTENING (loops back)
    -> (30s silence) -> IDLE

PRIMARY BUG FIXED:
    speak() + wait_until_done() now correctly blocks until TTS audio
    ACTUALLY FINISHES PLAYING (not just starts generating).
    This prevents microphone from opening while ULTRON is still speaking.
"""
from __future__ import annotations

import re
import time
import traceback
import threading
from typing import Callable, Optional

from core.voice_state import VoiceState, voice_state_manager
from speech import listen_for_audio, transcribe_audio_bytes, WAKE_WORDS
from speech_engine import speak, speaking, wait_until_done


def _router():
    from router import process
    return process


class VoicePipeline:
    """ULTRON voice interaction loop. Singleton via module-level voice_pipeline."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._chat_cb: Optional[Callable[[str, str], None]] = None

    def set_chat_callback(self, cb: Callable[[str, str], None]) -> None:
        self._chat_cb = cb

    def _chat(self, speaker: str, text: str) -> None:
        if self._chat_cb and text:
            try:
                self._chat_cb(speaker, text)
            except Exception as e:
                print(f"[VOICE] Chat callback error: {e}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        print("[BOOT] audio engine initialized", flush=True)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="VoicePipeline")
        self._thread.start()
        print("[BOOT] voice worker started", flush=True)
        print("[VOICE] Pipeline thread started.", flush=True)

    def stop(self) -> None:
        self._running = False
        print("[VOICE] Pipeline stopping.", flush=True)

    # ── TTS helper — THE CRITICAL FIX ──────────────────────────────────────────

    def _say(self, text: str) -> None:
        """
        Speak text and BLOCK until audio fully finishes playing.

        This is the fix for the primary bug:
          - speak() launches background thread, returns immediately
          - wait_until_done() blocks until:
              a) edge-tts generates the audio file
              b) pygame plays it to completion
          - Only then does microphone reopen
        """
        if not text:
            return
        voice_state_manager.transition_to(VoiceState.SPEAKING, text[:80])
        self._chat("ULTRON", text)
        speak(text)
        wait_until_done(timeout=90.0)    # blocks here until audio truly done
        time.sleep(0.40)                 # 400ms speaker echo dissipation

    # ── Wake-word detection ────────────────────────────────────────────────────

    def _is_wake(self, text: str) -> tuple[bool, str]:
        """Returns (is_wake_word, inline_command_if_any)."""
        clean = text.lower().strip()
        if not clean:
            return False, ""

        clean_norm = re.sub(r'[^\w\s]', '', clean)

        # Triggers: any phrase containing ultron, ultra, altron, outron, autron, hail, tron, hey, hi, hello, etc.
        wake_tokens = [
            "ultron", "ultra", "ultram", "altron", "alltron", "ul tron",
            "outron", "autron", "eltron", "oltron", "aultron", "haltron",
            "hail", "tron", "hey", "hi", "hello", "ok", "okay", "bro", "yo", "assistant"
        ]

        for tok in wake_tokens:
            if tok in clean_norm:
                cmd = re.sub(
                    r'^\s*(hey|hi|hello|ok|okay|yo|bro)?\s*'
                    r'(ultron|ultra|ultram|altron|alltron|all\s+tron|ul\s+tron|outron|autron|eltron|oltron|aultron|ol\s+tron|haltron|alteron|outeron|hail\s*tron|hailtron|hail|hay\s*tron|haytron|hell\s*tron|heil\s*tron|tron)?\s*',
                    '', clean_norm
                ).strip()
                return True, cmd

        # Fallback: any short spoken input (1-5 words) while waiting in wake mode triggers session!
        words = clean_norm.split()
        if len(words) <= 5:
            return True, clean_norm

        return False, ""



    # ── Main loop ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        router_process = _router()

        print("[BOOT] startup greeting starting", flush=True)
        # Play startup greeting using the approved voice
        self._say("Hey Harsha, what can I help you with?")
        print("[BOOT] startup greeting finished", flush=True)

        voice_state_manager.transition_to(VoiceState.IDLE)
        print("[BOOT] wake-word listener started", flush=True)
        print("[VOICE] === Wake listening started. Say 'Hey Ultron' or 'Ultron'. ===", flush=True)

        in_session = False        # True when command session is open
        session_end = 0.0         # Epoch when session expires

        while self._running:
            try:
                # ── Session timeout ──────────────────────────────────────────
                if in_session and time.time() > session_end:
                    print("[VOICE] Session timed out. Back to wake-word mode.")
                    in_session = False
                    voice_state_manager.transition_to(
                        VoiceState.IDLE, "Say 'Ultron' to wake me."
                    )

                # ── Status label ─────────────────────────────────────────────
                if in_session:
                    voice_state_manager.transition_to(
                        VoiceState.LISTENING, "Listening for command..."
                    )
                    print("[VOICE] COMMAND mode — listening...")
                else:
                    voice_state_manager.transition_to(
                        VoiceState.IDLE, "Waiting for wake word..."
                    )
                    print("[VOICE] WAKE mode — listening for 'Hey Ultron'...")

                # ── Capture audio ────────────────────────────────────────────
                voice_state_manager.transition_to(VoiceState.RECORDING)
                audio_bytes = listen_for_audio(
                    timeout=6.0 if not in_session else 8.0,
                    phrase_time_limit=12.0
                )

                if not self._running:
                    break

                if not audio_bytes:
                    print("[VOICE] No audio captured (silence/timeout). Retrying.")
                    continue

                print(f"[VOICE] Audio captured: {len(audio_bytes)} bytes")

                # ── Transcribe ───────────────────────────────────────────────
                voice_state_manager.transition_to(VoiceState.TRANSCRIBING)
                transcript = transcribe_audio_bytes(audio_bytes)

                if not transcript:
                    print("[VOICE] Empty transcript. Retrying.")
                    continue

                print(f"[VOICE] Transcript: '{transcript}'")

                # ── Wake mode: check for wake word ───────────────────────────
                if not in_session:
                    is_wake, inline_cmd = self._is_wake(transcript)
                    if not is_wake:
                        print(f"[VOICE] Not a wake word: '{transcript}'. Ignoring.")
                        continue

                    print(f"[VOICE] Wake detected: '{transcript}'")
                    voice_state_manager.transition_to(VoiceState.WAKE_DETECTED, transcript)
                    self._chat("USER", transcript)

                    if inline_cmd:
                        # "Ultron open YouTube" → process inline
                        print(f"[VOICE] Inline command: '{inline_cmd}'")
                        transcript = inline_cmd
                        in_session = True
                        session_end = time.time() + 45.0
                        # fall through to command processing
                    else:
                        # Just "Hey Ultron" → greet, open session
                        voice_state_manager.transition_to(VoiceState.GREETING)
                        self._say("Hey Harsha, what can I help you with?")
                        in_session = True
                        session_end = time.time() + 45.0  # 45s to respond
                        continue

                # ── Command processing ────────────────────────────────────────
                self._chat("USER", transcript)
                voice_state_manager.transition_to(
                    VoiceState.PROCESSING, f"Processing: '{transcript}'"
                )
                print(f"[VOICE] Sending to router: '{transcript}'")

                try:
                    running_flag, response = router_process(transcript)
                except Exception as e:
                    print(f"[VOICE] Router error: {e}")
                    traceback.print_exc()
                    response = "Something went wrong, Harsha. Let me try again."
                    running_flag = True

                print(f"[VOICE] Response: {str(response)[:100]!r}")

                # Fallback: router returned None response (e.g. command executed silently)
                if not response:
                    response = "Done, bro."

                self._say(response)

                # Keep session alive, extend deadline after each exchange
                in_session = True
                session_end = time.time() + 45.0

                if running_flag is False:
                    voice_state_manager.transition_to(VoiceState.IDLE, "Session ended.")
                    self.stop()
                    break

            except Exception as exc:
                print(f"[VOICE] Pipeline exception:")
                traceback.print_exc()
                voice_state_manager.transition_to(VoiceState.ERROR, str(exc))
                time.sleep(2.0)
                in_session = False
                voice_state_manager.transition_to(VoiceState.IDLE, "Recovered.")


# Global singleton
voice_pipeline = VoicePipeline()
