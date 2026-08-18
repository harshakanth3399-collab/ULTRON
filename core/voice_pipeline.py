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

    # ── TTS helper ────────────────────────────────────────────────────────────

    def _say(self, text: str, lang: str = "en") -> None:
        """
        Speak text and BLOCK until audio fully finishes playing.
        Dynamically dispatches to male English or female Telugu voice.
        """
        if not text:
            return
        t_tts_0 = time.time()
        voice_state_manager.transition_to(VoiceState.SPEAKING, text[:80])
        self._chat("ULTRON", text)
        speak(text, lang=lang)
        
        from speech_engine import _ready_event
        t_gen_0 = time.time()
        _ready_event.wait(timeout=6.0)
        t_gen = int((time.time() - t_gen_0) * 1000)
        print(f"[TIME] TTS generation: {t_gen} ms")

        t_play_0 = time.time()
        wait_until_done(timeout=90.0)    # blocks here until audio truly done
        time.sleep(0.35)                 # speaker echo dissipation
        t_play = int((time.time() - t_play_0) * 1000)
        t_tts_total = int((time.time() - t_tts_0) * 1000)
        print(f"[TIME] audio playback: {t_play} ms")
        print(f"[TIME] TTS total: {t_tts_total} ms")


    # ── Wake-word detection ("Hey" trigger + inline command extraction) ───────

    def _is_wake(self, text: str) -> tuple[bool, str]:
        """
        Returns (is_wake_word, inline_command_if_any).
        Triggered by "hey", "hi", "hello", "ok", "okay", or "ultron".
        """
        clean = text.lower().strip()
        if not clean:
            return False, ""

        clean_norm = re.sub(r'[^\w\s]', '', clean)

        # Wake prefix triggers: "hey", "hi", "hello", "ok", "okay", "ultron", "altron", "tron"
        wake_prefixes = [
            r"^\s*(?:hey|hi|hello|ok|okay)\s+ultron\b",
            r"^\s*(?:hey|hi|hello|ok|okay)\b",
            r"^\s*(?:ultron|ultra|ultram|altron|alltron|outron|autron|eltron|oltron|hailtron|tron)\b",
        ]

        for pat in wake_prefixes:
            if re.search(pat, clean_norm):
                # Extract inline command after wake prefix
                cmd = re.sub(pat, '', clean_norm).strip()
                return True, cmd

        return False, ""

    # ── Main loop ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        router_process = _router()

        print("[BOOT] startup greeting starting", flush=True)
        from modules.friendly_assistant import get_dynamic_greeting
        # Play dynamic time-aware startup greeting using the approved voice
        self._say(get_dynamic_greeting("Harsha"))
        print("[BOOT] startup greeting finished", flush=True)


        voice_state_manager.transition_to(VoiceState.IDLE)
        print("[BOOT] wake listener active. Say 'Hey' or 'Hey, [command]'.", flush=True)

        in_session = False        # True when command session is open
        session_end = 0.0         # Epoch when session expires

        while self._running:
            try:
                # ── Session timeout ──────────────────────────────────────────
                if in_session and time.time() > session_end:
                    print("[VOICE] Session timed out. Returning to IDLE.")
                    in_session = False
                    voice_state_manager.transition_to(
                        VoiceState.IDLE, "Say 'Hey' to wake me."
                    )

                # ── Status label ─────────────────────────────────────────────
                if in_session:
                    voice_state_manager.transition_to(
                        VoiceState.LISTENING, "Listening for command..."
                    )
                else:
                    voice_state_manager.transition_to(
                        VoiceState.IDLE, "Say 'Hey' to begin"
                    )

                # ── Capture audio ────────────────────────────────────────────
                t_pipeline_0 = time.time()
                t_cap_0 = time.time()
                voice_state_manager.transition_to(VoiceState.RECORDING)
                audio_bytes = listen_for_audio(
                    timeout=6.0 if not in_session else 8.0,
                    phrase_time_limit=10.0
                )

                if not self._running:
                    break

                if not audio_bytes:
                    continue

                t_cap = int((time.time() - t_cap_0) * 1000)
                print(f"[TIME] mic capture: {t_cap} ms ({len(audio_bytes)} bytes)")

                # ── Transcribe ───────────────────────────────────────────────
                voice_state_manager.transition_to(VoiceState.TRANSCRIBING)
                t_trans_0 = time.time()
                transcript, detected_lang = transcribe_audio_bytes(audio_bytes)
                t_trans = int((time.time() - t_trans_0) * 1000)

                if not transcript or not transcript.strip():
                    print("[VOICE] Empty transcript — ignored.")
                    continue


                # ── Wake mode: check for 'Hey' wake trigger ──────────────────
                if not in_session:
                    is_wake, inline_cmd = self._is_wake(transcript)
                    if not is_wake:
                        print(f"[VOICE] Not a wake trigger: '{transcript}'. Ignoring.")
                        continue

                    print(f"[VOICE] Wake trigger detected: '{transcript}'")
                    voice_state_manager.transition_to(VoiceState.WAKE_DETECTED, transcript)

                    if inline_cmd and len(inline_cmd) > 1:
                        # Single-utterance "Hey + Command": Process command directly without 2-step greeting delay!
                        print(f"[VOICE] Single-utterance command: '{inline_cmd}'")
                        transcript = inline_cmd
                        in_session = True
                        session_end = time.time() + 45.0
                    else:
                        # User only said "Hey" -> Short local acknowledgement & open session
                        self._chat("USER", transcript)
                        voice_state_manager.transition_to(VoiceState.GREETING)
                        from modules.memory.profile_manager import get_profile_manager
                        pm = get_profile_manager()
                        pref_addr = pm.get_preferred_address() or "Harsha"
                        active_lang = pm.get_active_language()
                        self._say(f"Yes, {pref_addr}?", lang=active_lang)
                        in_session = True
                        session_end = time.time() + 45.0
                        continue


                # ── Command processing ────────────────────────────────────────
                self._chat("USER", transcript)
                voice_state_manager.transition_to(
                    VoiceState.PROCESSING, f"Processing: '{transcript}'"
                )

                t_rout_0 = time.time()
                try:
                    running_flag, response = router_process(transcript)
                except Exception as e:
                    print(f"[VOICE] Router error: {e}")
                    traceback.print_exc()
                    response = "Something went wrong, Harsha. Let me try again."
                    running_flag = True

                t_rout = int((time.time() - t_rout_0) * 1000)
                print(f"[TIME] router: {t_rout} ms")
                from modules.memory.profile_manager import get_profile_manager
                pm = get_profile_manager()
                active_lang = pm.get_active_language()
                print(f"[VOICE] Response ({active_lang}): {str(response)[:100]!r}")

                if not response:
                    response = "Done."

                self._say(response, lang=active_lang)

                t_total = int((time.time() - t_pipeline_0) * 1000)
                print(f"[TIME] TOTAL PIPELINE LATENCY: {t_total} ms")

                # Keep session active for follow-up commands
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
