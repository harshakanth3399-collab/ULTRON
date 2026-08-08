"""
core/voice_pipeline.py — Complete Voice State Machine for ULTRON.

ROOT CAUSES FIXED:
  1. Session timeout (8s) was expiring during greeting+listen combo — now 30s
  2. _speak_and_wait() had a race: now waits for thread to start before polling
  3. Pipeline loop now logs EVERY stage explicitly
  4. (True, None) response from router now triggers a fallback reply
  5. Wake-word detection extended with phonetic fuzzy matching
  6. State transitions are explicit and cover WAKE_LISTENING as a named state
"""

from __future__ import annotations

import re
import time
import threading
from typing import Callable, Optional

from core.voice_state import VoiceState, voice_state_manager
from speech import listen_for_audio, transcribe_audio_bytes, WAKE_WORDS
from speech_engine import speak, speaking


def _get_router():
    from router import process as router_process
    return router_process


class VoicePipeline:
    """
    Manages the complete ULTRON voice interaction loop.

    State Machine:
        IDLE → (wake detected) → WAKE_DETECTED → GREETING
             → LISTENING → RECORDING → TRANSCRIBING → PROCESSING
             → SPEAKING → LISTENING  (repeats)
             → (silence timeout) → IDLE
    """

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._chat_callback: Optional[Callable[[str, str], None]] = None

    def set_chat_callback(self, cb: Callable[[str, str], None]) -> None:
        self._chat_callback = cb

    def _notify_chat(self, speaker: str, text: str) -> None:
        if self._chat_callback and text:
            try:
                self._chat_callback(speaker, text)
            except Exception as e:
                print(f"[VOICE] Chat callback error: {e}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._pipeline_loop, daemon=True)
        self._thread.start()
        print("[VOICE] Pipeline started.")

    def stop(self) -> None:
        self._running = False
        print("[VOICE] Pipeline stopping.")

    # ── TTS helper ────────────────────────────────────────────────────────────

    def _speak_and_wait(self, text: str) -> None:
        """
        Speaks text and blocks until playback is complete.

        FIX: speak() now sets _is_speaking=True before thread starts,
        so we can safely sleep(0.1) and immediately begin polling.
        """
        if not text:
            return
        voice_state_manager.transition_to(VoiceState.SPEAKING, text[:60])
        self._notify_chat("ULTRON", text)
        speak(text)
        time.sleep(0.1)                         # tiny yield — thread is already running
        deadline = time.time() + 90.0           # max 90s safety timeout
        while time.time() < deadline:
            if not speaking():
                break
            time.sleep(0.05)
        time.sleep(0.35)                        # speaker echo dissipation

    # ── Wake-word detection ───────────────────────────────────────────────────

    def _is_wake_word(self, text: str) -> tuple[bool, str]:
        """
        Checks whether transcript contains a wake word.
        Returns (is_wake, remaining_command_if_any).
        """
        clean = text.lower().strip()
        if not clean:
            return False, ""

        # Exact and prefix matches from the WAKE_WORDS set
        for wake in sorted(WAKE_WORDS, key=len, reverse=True):
            if clean == wake:
                return True, ""
            if clean.startswith(wake + " "):
                return True, clean[len(wake):].strip()
            if clean.startswith(wake + ","):
                return True, clean[len(wake) + 1:].strip()

        # Fuzzy: any phonetic variant of ultron present anywhere
        triggers = ["ultron", "ultra", "ultram", "altron", "all tron", "ul tron"]
        for trig in triggers:
            if trig in clean:
                cmd = re.sub(
                    r'^\s*(hey|hi|hello|ok|okay|yo|bro)?\s*(ultron|ultra|ultram|altron|alltron|oldtron|tron|all tron|ul tron)\s*[,.]?\s*',
                    '', clean
                ).strip()
                return True, cmd

        return False, ""

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def _pipeline_loop(self) -> None:
        """
        Complete continuous voice pipeline.

        Modes:
          IDLE / WAKE_LISTENING: listening only for wake word (no session open)
          COMMAND_LISTENING:     session active, listening for user commands
        """
        router_process = _get_router()

        voice_state_manager.transition_to(VoiceState.IDLE)
        print("[VOICE] Wake listening started. Say 'Hey Ultron' or 'Ultron'.")

        # ── Variables ──────────────────────────────────────────────────────
        in_session = False          # True when a command session is open
        session_deadline = 0.0     # When to return to IDLE wake mode

        while self._running:
            try:
                # ── Session timeout check ──────────────────────────────────
                if in_session and time.time() > session_deadline:
                    print("[VOICE] Session timed out. Returning to wake-word listening.")
                    in_session = False
                    voice_state_manager.transition_to(
                        VoiceState.IDLE,
                        "Session closed — say 'Ultron' to wake me."
                    )

                # ── State label ───────────────────────────────────────────
                if in_session:
                    voice_state_manager.transition_to(VoiceState.LISTENING, "Waiting for your command...")
                    print("[VOICE] COMMAND mode — listening for command...")
                else:
                    voice_state_manager.transition_to(VoiceState.IDLE, "Say 'Hey Ultron' to activate...")
                    print("[VOICE] WAKE mode — listening for wake word...")

                # ── Capture audio ─────────────────────────────────────────
                voice_state_manager.transition_to(VoiceState.RECORDING)
                audio_bytes = listen_for_audio(
                    timeout=6.0,
                    phrase_time_limit=12.0
                )

                if not self._running:
                    break

                if not audio_bytes:
                    print("[VOICE] No audio captured (silence or timeout). Retrying.")
                    continue

                print(f"[VOICE] Audio captured: {len(audio_bytes)} bytes")

                # ── Transcribe ────────────────────────────────────────────
                voice_state_manager.transition_to(VoiceState.TRANSCRIBING)
                transcript = transcribe_audio_bytes(audio_bytes)

                if not transcript:
                    print("[VOICE] Empty transcription. Retrying.")
                    continue

                # ── Wake-word mode ────────────────────────────────────────
                if not in_session:
                    is_wake, inline_cmd = self._is_wake_word(transcript)
                    if not is_wake:
                        print(f"[VOICE] Not a wake word: '{transcript}'. Ignoring.")
                        continue

                    print(f"[VOICE] Wake word detected! Transcript: '{transcript}'")
                    voice_state_manager.transition_to(VoiceState.WAKE_DETECTED, transcript)
                    self._notify_chat("USER", transcript)

                    if inline_cmd:
                        # "Hey Ultron open YouTube" → process command directly
                        print(f"[VOICE] Inline command: '{inline_cmd}'")
                        transcript = inline_cmd
                        in_session = True
                        session_deadline = time.time() + 30.0
                        # fall through to command processing below
                    else:
                        # Just "Hey Ultron" → greet and open session
                        voice_state_manager.transition_to(VoiceState.GREETING)
                        greet = "Hey Harsha, what can I help you with?"
                        self._speak_and_wait(greet)
                        in_session = True
                        session_deadline = time.time() + 30.0   # FIX: was 8s
                        continue

                # ── Command processing ────────────────────────────────────
                self._notify_chat("USER", transcript)
                voice_state_manager.transition_to(VoiceState.PROCESSING, f"Processing: '{transcript}'")
                print(f"[VOICE] Sending to router: '{transcript}'")

                try:
                    running_flag, response = router_process(transcript)
                except Exception as re_err:
                    print(f"[VOICE] Router error: {re_err}")
                    response = "Something went wrong processing that command, Harsha. Try again."
                    running_flag = True

                print(f"[VOICE] Router response: {response!r}")

                # FIX: router returning (True, None) used to silently drop response
                if not response:
                    response = "Done, Harsha."

                self._speak_and_wait(response)

                # Extend session after each successful exchange
                in_session = True
                session_deadline = time.time() + 30.0

                if running_flag is False:
                    voice_state_manager.transition_to(VoiceState.IDLE, "Exit command received.")
                    self.stop()
                    break

            except Exception as exc:
                import traceback
                print(f"[VOICE] Pipeline exception:")
                traceback.print_exc()
                voice_state_manager.transition_to(VoiceState.ERROR, str(exc))
                time.sleep(1.5)
                in_session = False
                voice_state_manager.transition_to(VoiceState.IDLE, "Recovered from error.")


# Global singleton
voice_pipeline = VoicePipeline()
