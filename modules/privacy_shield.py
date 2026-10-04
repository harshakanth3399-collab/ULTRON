"""
modules/privacy_shield.py - ULTRON Shoulder-Surfing Privacy Shield (Anti-Spy Sentinel)

Uses MediaPipe Face Landmarker via laptop webcam to detect multiple faces in the background.
If an unauthorized person looks over Harsha's shoulder:
- Instantly minimizes windows or shows desktop to conceal private content
- Speaks a voice alert: "Harsha, someone is looking over your shoulder."
"""

from __future__ import annotations

import os
import threading
import time
from typing import Optional, Tuple

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from modules.human_controller import human_controller


class PrivacyShield:
    """Monitors behind-the-user space for shoulder surfers and conceals sensitive display."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._detector: Optional[vision.FaceLandmarker] = None
        self._last_alert_time = 0.0
        self._cooldown = 15.0  # seconds between alerts

    def _init_detector(self) -> bool:
        if self._detector is not None:
            return True
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "models", "face_landmarker.task"
        )
        if not os.path.exists(model_path):
            print(f"[PRIVACY SHIELD] Model not found at: {model_path}")
            return False
        try:
            base_opts = python.BaseOptions(model_asset_path=model_path)
            opts = vision.FaceLandmarkerOptions(
                base_options=base_opts,
                num_faces=2,  # Configured to track multiple people
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
            )
            self._detector = vision.FaceLandmarker.create_from_options(opts)
            return True
        except Exception as e:
            print(f"[PRIVACY SHIELD INIT ERROR] {e}")
            return False

    def check_presence_faces(self) -> int:
        """Captures a single frame and returns count of faces detected."""
        if not self._init_detector():
            return 0

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return 0

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return 0

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        try:
            res = self._detector.detect(mp_img)
            return len(res.face_landmarks) if res.face_landmarks else 0
        except Exception:
            return 0

    def _loop(self) -> None:
        print("[PRIVACY SHIELD] Anti-spy shoulder sentinel active.")
        if not self._init_detector():
            self._running = False
            return

        cap = cv2.VideoCapture(0)

        while self._running:
            # Yield camera if gesture engine or head tracker is active
            try:
                from modules.gesture_engine import gesture_engine
                from modules.head_tracker import head_tracker
                if gesture_engine._running or head_tracker._running:
                    if cap.isOpened():
                        cap.release()
                    time.sleep(2.0)
                    continue
            except Exception:
                pass

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
                face_count = len(res.face_landmarks) if res.face_landmarks else 0
            except Exception:
                face_count = 0

            now = time.time()
            if face_count >= 2 and (now - self._last_alert_time > self._cooldown):
                self._last_alert_time = now
                print("[PRIVACY SHIELD ALERT] Multiple faces detected! Concealing screen...")
                # Conceal display
                human_controller.press_shortcut("show desktop")
                try:
                    from speech_engine import speak
                    speak("Harsha, someone is looking over your shoulder. I minimized your screen.")
                except Exception:
                    pass

            time.sleep(2.5)

        cap.release()

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "Privacy Shield is already active."
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True, "Privacy Shield activated. I will protect your screen if someone looks over your shoulder."

    def stop(self) -> Tuple[bool, str]:
        if not self._running:
            return True, "Privacy Shield is not running."
        self._running = False
        return True, "Privacy Shield deactivated."

    def status(self) -> str:
        state = "active" if self._running else "inactive"
        return f"Privacy Shield is currently {state}."


privacy_shield = PrivacyShield()
