"""
modules/head_tracker.py - ULTRON Touchless Head & Eye Tracking Cursor Control Engine

Uses Google MediaPipe FaceLandmarker to translate head and nose movements into
real-time mouse cursor position on your laptop screen.
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


class HeadTracker:
    """Manages touchless head-driven cursor navigation via laptop camera."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._detector: Optional[vision.FaceLandmarker] = None
        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)
        self._smooth_x = float(self.screen_w // 2)
        self._smooth_y = float(self.screen_h // 2)

    def _init_detector(self) -> bool:
        if self._detector is not None:
            return True

        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "models", "face_landmarker.task"
        )
        if not os.path.exists(model_path):
            print(f"[HEAD TRACKER ERROR] Model file not found at: {model_path}")
            return False

        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=1,
                min_face_detection_confidence=0.6,
                min_face_presence_confidence=0.6,
                min_tracking_confidence=0.6,
            )
            self._detector = vision.FaceLandmarker.create_from_options(options)
            return True
        except Exception as e:
            print(f"[HEAD TRACKER INIT ERROR] {e}")
            return False

    def is_active(self) -> bool:
        return self._running

    def start(self) -> Tuple[bool, str]:
        """Activates head-tracking mouse navigation."""
        if self._running:
            return True, "Head-tracking mouse is already active, Harsha."

        if not self._init_detector():
            return False, "Failed to load face tracking model."

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="HeadTrackerLoop")
        self._thread.start()
        print("[HEAD TRACKER] Head navigation cursor active.")
        return True, "Head-tracking mouse is now active, Harsha. Move your head to guide the cursor."

    def stop(self) -> Tuple[bool, str]:
        """Deactivates head-tracking mouse navigation."""
        if not self._running:
            return True, "Head tracking is already offline."

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        print("[HEAD TRACKER] Head navigation deactivated.")
        return True, "Head-tracking mouse has been deactivated."

    def _loop(self) -> None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(1)
            if not cap.isOpened():
                print("[HEAD TRACKER] Could not open webcam.")
                self._running = False
                return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Baseline calibration
        base_x = 0.5
        base_y = 0.5
        calibrated = False

        while self._running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Flip horizontally for mirrored head tracking
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            try:
                res = self._detector.detect(mp_img)
                if res.face_landmarks:
                    face = res.face_landmarks[0]
                    # Landmark 1: Nose tip
                    nose = face[1]

                    if not calibrated:
                        base_x = nose.x
                        base_y = nose.y
                        calibrated = True

                    # Calculate offset from center with sensitivity factor
                    dx = (nose.x - base_x) * 3.2
                    dy = (nose.y - base_y) * 3.2

                    target_x = max(0, min(self.screen_w - 1, int(self.screen_w * (0.5 + dx))))
                    target_y = max(0, min(self.screen_h - 1, int(self.screen_h * (0.5 + dy))))

                    # Exponential smoothing to prevent mouse jitter
                    self._smooth_x = 0.65 * self._smooth_x + 0.35 * target_x
                    self._smooth_y = 0.65 * self._smooth_y + 0.35 * target_y

                    user32.SetCursorPos(int(self._smooth_x), int(self._smooth_y))
            except Exception:
                pass

            time.sleep(0.03)  # ~30 FPS loop

        cap.release()


# Global singleton
head_tracker = HeadTracker()
