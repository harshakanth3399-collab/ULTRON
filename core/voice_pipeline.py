"""Voice Pipeline Controller managing the complete Voice State Machine."""

from __future__ import annotations

import time
import threading
from typing import Callable, Optional

from core.voice_state import VoiceState, voice_state_manager
from speech import listen_for_audio, transcribe_audio_bytes, WAKE_WORDS
from speech_engine import speak, speaking
from router import process as router_process


class VoicePipeline:
    """Manages the continuous voice interaction loop, wake-word detection, and UI state synchronization."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._chat_callback: Optional[Callable[[str, str], None]] = None

    def set_chat_callback(self, callback: Callable[[str, str], None]) -> None:
        """Sets UI callback for displaying USER and ULTRON chat messages."""
        self._chat_callback = callback

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
        print("[VOICE] Pipeline stopping...")

    def _speak_and_wait(self, text: str) -> None:
        """Speaks text using locked TTS voice and waits for completion."""
        if not text:
            return

        voice_state_manager.transition_to(VoiceState.SPEAKING, text)
        speak(text)

        time.sleep(0.3)
        deadline = time.time() + 60.0
        while time.time() < deadline:
            if not speaking():
                break
            time.sleep(0.05)

        time.sleep(0.2)  # Echo grace period

    def _extract_wake_word_and_command(self, text: str) -> tuple[bool, str]:
        """Checks if text contains any wake word or phonetic variant for instant awakening."""
        clean = text.lower().strip()
        if not clean:
            return False, ""

        for wake in WAKE_WORDS:
            if clean == wake:
                return True, ""
            if clean.startswith(wake + " "):
                cmd = clean[len(wake):].strip()
                return True, cmd

        import re
        wake_triggers = ["ultron", "ultra", "ultram", "altron", "alltron", "oldtron", "tron"]
        for trig in wake_triggers:
            if trig in clean:
                cmd = re.sub(r'^(hey|hi|hello|ok|okay|yo|bro)?\s*(ultron|ultra|ultram|altron|alltron|oldtron|tron)\s*', '', clean).strip()
                return True, cmd

        return False, ""

    def _pipeline_loop(self) -> None:
        """Main continuous background voice loop."""
        voice_state_manager.transition_to(VoiceState.IDLE)

        # Initial startup greeting on launch
        time.sleep(0.6)
        greeting_text = "Hey Harsha, what can I help you with?"
        self._notify_chat("ULTRON", greeting_text)
        self._speak_and_wait(greeting_text)

        in_active_session = True
        session_timeout = 0.0

        while self._running:
            try:
                # If active session timed out (6s silence), return to IDLE wake-word mode
                if in_active_session and time.time() > session_timeout and session_timeout > 0:
                    in_active_session = False
                    voice_state_manager.transition_to(VoiceState.IDLE, "Session timed out — listening for wake word.")

                current_mode = "COMMAND" if in_active_session else "WAKE"
                voice_state_manager.transition_to(
                    VoiceState.LISTENING if in_active_session else VoiceState.IDLE,
                    f"Listening for {'Command' if in_active_session else 'Wake Word (Hey Ultron)'}..."
                )

                # Capture microphone audio
                voice_state_manager.transition_to(VoiceState.RECORDING, "Recording microphone input...")
                audio_bytes = listen_for_audio(
                    timeout=5.0 if in_active_session else 4.0,
                    phrase_time_limit=8.0
                )

                if not self._running:
                    break

                if not audio_bytes:
                    continue

                # Transcribe audio to English
                voice_state_manager.transition_to(VoiceState.TRANSCRIBING, "Transcribing English speech...")
                transcript = transcribe_audio_bytes(audio_bytes)

                if not transcript:
                    continue

                print(f"[VOICE] Transcription result: '{transcript}'")

                # If in WAKE mode, check for wake word
                if not in_active_session:
                    is_wake, command = self._extract_wake_word_and_command(transcript)
                    if not is_wake:
                        continue

                    voice_state_manager.transition_to(VoiceState.WAKE_DETECTED, transcript)
                    self._notify_chat("USER", transcript)

                    if command:
                        # Direct command: "Hey Ultron open YouTube"
                        transcript = command
                        in_active_session = True
                        session_timeout = time.time() + 8.0
                    else:
                        # Just "Hey Ultron" -> speak greeting and open command mode
                        voice_state_manager.transition_to(VoiceState.GREETING)
                        greet = "Hey Harsha, what can I help you with?"
                        self._notify_chat("ULTRON", greet)
                        self._speak_and_wait(greet)
                        in_active_session = True
                        session_timeout = time.time() + 8.0
                        continue

                # Process Command
                self._notify_chat("USER", transcript)
                voice_state_manager.transition_to(VoiceState.PROCESSING, f"Executing: '{transcript}'")

                running_flag, response = router_process(transcript)

                if response:
                    self._notify_chat("ULTRON", response)
                    self._speak_and_wait(response)

                in_active_session = True
                session_timeout = time.time() + 8.0

                if running_flag is False:
                    voice_state_manager.transition_to(VoiceState.IDLE, "Exit command received.")
                    self.stop()
                    break

            except Exception as e:
                print(f"[VOICE] Pipeline Exception: {e}")
                voice_state_manager.transition_to(VoiceState.ERROR, str(e))
                time.sleep(1.0)
                voice_state_manager.transition_to(VoiceState.IDLE, "Recovered from error.")


# Global Voice Pipeline instance
voice_pipeline = VoicePipeline()
