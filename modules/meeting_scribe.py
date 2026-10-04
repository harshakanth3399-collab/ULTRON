"""
modules/meeting_scribe.py - ULTRON Live Meeting & Lecture Scribe

Records audio during Google Meet, Zoom, lectures, or conversations.
Transcribes speech in real time using Groq Whisper / Faster-Whisper,
and writes structured notes and an executive summary to Desktop/Meeting_Notes.txt.
"""

from __future__ import annotations

import datetime
import io
import os
import threading
import time
import wave
from typing import List, Optional, Tuple

import pyaudio
import requests

from ai import ask_ai


class MeetingScribe:
    """Background audio recorder and transcription scribe for meetings & lectures."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._notes_file: str = ""
        self._transcript_lines: List[str] = []
        self._lock = threading.Lock()

    def _get_notes_path(self) -> str:
        from modules.system_paths import get_desktop_dir
        desktop_dir = str(get_desktop_dir())
        return os.path.join(desktop_dir, f"Meeting_Notes_{datetime.datetime.now().strftime('%Y%m%d')}.txt")

    def _record_and_transcribe_loop(self) -> None:
        print("[MEETING SCRIBE] Recording session started...")
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip()

        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024,
            )
        except Exception as e:
            print(f"[MEETING SCRIBE ERROR] Could not open microphone stream: {e}")
            self._running = False
            pa.terminate()
            return

        chunk_seconds = 10  # Transcribe every 10 seconds of speech
        frames_per_chunk = int(16000 / 1024 * chunk_seconds)

        while self._running:
            frames = []
            for _ in range(frames_per_chunk):
                if not self._running:
                    break
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    frames.append(data)
                except Exception:
                    pass

            if not frames or not self._running:
                break

            # Check if there is audio energy
            raw_bytes = b"".join(frames)
            import audioop
            rms = audioop.rms(raw_bytes, 2)
            if rms < 250:  # Silence or ambient background
                continue

            # Transcribe chunk via Groq Whisper API
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(raw_bytes)
            wav_buf.seek(0)

            chunk_text = ""
            if groq_api_key:
                try:
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {groq_api_key}"},
                        files={"file": ("chunk.wav", wav_buf.read(), "audio/wav")},
                        data={"model": "whisper-large-v3-turbo", "language": "en"},
                        timeout=5.0,
                    )
                    if resp.status_code == 200:
                        chunk_text = resp.json().get("text", "").strip()
                except Exception as e:
                    print(f"[MEETING SCRIBE TRANSCRIBE ERROR] {e}")

            if chunk_text and len(chunk_text) > 3:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                entry = f"[{timestamp}] {chunk_text}"
                print(f"[MEETING SCRIBE] {entry}")
                with self._lock:
                    self._transcript_lines.append(entry)
                    try:
                        with open(self._notes_file, "a", encoding="utf-8") as f:
                            f.write(entry + "\n")
                    except Exception:
                        pass

        try:
            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception:
            pass

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "Meeting Scribe is already listening and recording."
        self._running = True
        self._notes_file = self._get_notes_path()
        with self._lock:
            self._transcript_lines.clear()

        # Initialize file with header
        try:
            with open(self._notes_file, "a", encoding="utf-8") as f:
                f.write(f"\n=== ULTRON MEETING NOTES SESSION [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n\n")
        except Exception:
            pass

        self._thread = threading.Thread(target=self._record_and_transcribe_loop, daemon=True)
        self._thread.start()
        return True, f"Meeting Scribe activated. Recording and transcribing live notes to {os.path.basename(self._notes_file)}."

    def stop(self) -> Tuple[bool, str]:
        if not self._running:
            return True, "Meeting Scribe is not active."
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

        # Generate summary if notes were recorded
        with self._lock:
            total_lines = len(self._transcript_lines)
            full_text = "\n".join(self._transcript_lines)

        if total_lines > 0 and len(full_text) > 30:
            ok, summary = ask_ai(f"Provide an executive summary and bulleted key action items from these meeting notes:\n\n{full_text}")
            if ok and summary:
                try:
                    with open(self._notes_file, "a", encoding="utf-8") as f:
                        f.write("\n\n--- EXECUTIVE SUMMARY & ACTION ITEMS ---\n")
                        f.write(summary + "\n")
                except Exception:
                    pass
                return True, f"Meeting finished. Generated executive summary with {total_lines} transcribed segments in {os.path.basename(self._notes_file)}."

        return True, f"Meeting session concluded. Saved to {os.path.basename(self._notes_file)}."


meeting_scribe = MeetingScribe()
