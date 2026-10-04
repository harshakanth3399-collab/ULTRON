"""
modules/face_presence.py - ULTRON Face Presence Auto-Wake & Walk-Away Lock Sentinel

Uses Google MediaPipe Face Landmarker via laptop webcam in low-power intervals.
- When user returns to laptop: greets user ("Welcome back, Harsha").
- When user walks away for >30 seconds: automatically locks Windows workstation to protect privacy.
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from typing import Optional, Tuple

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

user32 = ctypes.windll.user32


class FacePresenceSentinel:
    """Monitors user presence in front of laptop webcam and auto-locks on absence."""

    def __init__(self, absence_timeout_seconds: float = 30.0) -> None:
        self.absence_timeout = absence_timeout_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._detector: Optional[vision.FaceLandmarker] = None
        self._last_seen_time: float = time.time()
        self._was_present = True
        self._locked = False

    def _init_detector(self) -> bool:
        if self._detector is not None:
            return True
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "models", "face_landmarker.task"
        )
        if not os.path.exists(model_path):
            print(f"[FACE PRESENCE] Model not found: {model_path}")
            return False
        try:
            base_opts = python.BaseOptions(model_asset_path=model_path)
            opts = vision.FaceLandmarkerOptions(
                base_options=base_opts,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
            )
            self._detector = vision.FaceLandmarker.create_from_options(opts)
            return True
        except Exception as e:
            print(f"[FACE PRESENCE INIT ERROR] {e}")
            return False

    def check_face_once(self) -> bool:
        """Grabs a single webcam frame and checks if a face is present."""
        if not self._init_detector():
            return False

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return False

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self._detector.detect(mp_img)

        return bool(res.face_landmarks and len(res.face_landmarks) > 0)

    def _loop(self) -> None:
        print("[FACE PRESENCE] Background presence sentinel running...")
        if not self._init_detector():
            self._running = False
            return

        cap = cv2.VideoCapture(0)
        self._last_seen_time = time.time()

        while self._running:
            if not cap.isOpened():
                cap.open(0)
                time.sleep(1.0)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(2.0)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            try:
                res = self._detector.detect(mp_img)
                face_detected = bool(res.face_landmarks and len(res.face_landmarks) > 0)
            except Exception:
                face_detected = False

            now = time.time()
            if face_detected:
                self._last_seen_time = now
                if not self._was_present:
                    self._was_present = True
                    self._locked = False
                    print("[FACE PRESENCE] User returned!")
                    try:
                        from speech_engine import speak
                        speak("Welcome back, Harsha.")
                    except Exception:
                        pass
            else:
                elapsed_away = now - self._last_seen_time
                if elapsed_away >= self.absence_timeout and self._was_present and not self._locked:
                    self._was_present = False
                    self._locked = True
                    print(f"[FACE PRESENCE] User absent for {int(elapsed_away)}s. Locking workstation...")
                    try:
                        user32.LockWorkStation()
                    except Exception as e:
                        print(f"[LOCK ERROR] {e}")

            # Sample every 3 seconds to keep CPU usage < 0.5%
            time.sleep(3.0)

        cap.release()

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "Presence Sentinel is already active."
        self._running = True
        self._locked = False
        self._was_present = True
        self._last_seen_time = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True, "Presence Sentinel active. I will welcome you when you return and lock Windows if you walk away."

    def stop(self) -> Tuple[bool, str]:
        if not self._running:
            return True, "Presence Sentinel is not running."
        self._running = False
        return True, "Presence Sentinel deactivated."

    def status(self) -> str:
        state = "active" if self._running else "inactive"
        return f"Presence Sentinel is currently {state}."


face_presence = FacePresenceSentinel()
