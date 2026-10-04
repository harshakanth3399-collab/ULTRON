"""
modules/gesture_engine.py - ULTRON Real-Time 3D Hand Gesture Control Engine

Uses Google MediaPipe HandLandmarker & OpenCV on your laptop webcam to provide
touchless, natural human hand gestures:
  🖐️ Open Palm     -> Toggle Play / Pause / Mute
  👍 Thumbs Up      -> Press Enter (Confirm)
  ✌️ Peace Sign     -> Switch Window / App (Alt+Tab)
  ✊ Fist           -> Show Desktop (Minimize All)
  🤏 Pinch          -> Mouse Click
  👈 Swipe Left     -> Close Active Tab (Ctrl+W)
  👉 Swipe Right    -> New Tab (Ctrl+T)
"""

from __future__ import annotations

import math
import os
import threading
import time
from typing import Optional, Tuple

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from modules.human_controller import human_controller


class GestureEngine:
    """Manages real-time background webcam hand tracking and gesture execution."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._detector: Optional[vision.HandLandmarker] = None
        self._last_action_time = 0.0
        self._cooldown = 1.4  # seconds between gesture triggers
        self._prev_wrist_x: Optional[float] = None
        self._last_gesture = ""

    def _init_detector(self) -> bool:
        if self._detector is not None:
            return True

        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "models", "hand_landmarker.task"
        )
        if not os.path.exists(model_path):
            print(f"[GESTURE ENGINE ERROR] Model not found at: {model_path}")
            return False

        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=1,
                min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6,
                min_tracking_confidence=0.6
            )
            self._detector = vision.HandLandmarker.create_from_options(options)
            return True
        except Exception as e:
            print(f"[GESTURE ENGINE INIT ERROR] {e}")
            return False

    def is_active(self) -> bool:
        return self._running

    def start(self) -> Tuple[bool, str]:
        """Starts real-time background webcam gesture tracking."""
        if self._running:
            return True, "Hand gesture recognition is already active, Harsha."

        if not self._init_detector():
            return False, "Failed to initialize hand gesture model."

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="GestureEngineLoop")
        self._thread.start()
        print("[GESTURE ENGINE] Real-time hand tracking active on laptop camera.")
        return True, "Hand gesture control is now active on your laptop camera, Harsha. Use open palm to pause, thumbs up to confirm, or a fist to show desktop."

    def stop(self) -> Tuple[bool, str]:
        """Stops background webcam tracking and frees the camera."""
        if not self._running:
            return True, "Hand gesture control is already offline."

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        print("[GESTURE ENGINE] Hand tracking deactivated.")
        return True, "Hand gesture control has been deactivated."

    def _loop(self) -> None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(1)
            if not cap.isOpened():
                print("[GESTURE ENGINE] Could not open webcam for gesture tracking.")
                self._running = False
                return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while self._running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Mirror frame for intuitive left/right controls
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            try:
                result = self._detector.detect(mp_img)
                if result.hand_landmarks:
                    landmarks = result.hand_landmarks[0]
                    self._classify_and_execute(landmarks)
            except Exception as e:
                pass

            time.sleep(0.04)  # ~25 FPS loop — ultra light on CPU

        cap.release()

    def _classify_and_execute(self, lm: list) -> None:
        now = time.time()
        if now - self._last_action_time < self._cooldown:
            return

        # Landmark indices
        wrist = lm[0]
        thumb_tip = lm[4]
        index_tip = lm[8]
        index_pip = lm[6]
        middle_tip = lm[12]
        middle_pip = lm[10]
        ring_tip = lm[16]
        ring_pip = lm[14]
        pinky_tip = lm[20]
        pinky_pip = lm[18]

        # Finger extended flags (Y is inverted: smaller Y means higher on screen)
        index_up  = index_tip.y < index_pip.y
        middle_up = middle_tip.y < middle_pip.y
        ring_up   = ring_tip.y < ring_pip.y
        pinky_up  = pinky_tip.y < pinky_pip.y
        thumb_up  = thumb_tip.y < lm[3].y

        # Distance between thumb and index tip
        pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)

        # 1. 🤏 Pinch Gesture (Click)
        if pinch_dist < 0.048 and not (middle_up and ring_up and pinky_up):
            self._last_action_time = now
            self._last_gesture = "Pinch (Click)"
            print("[GESTURE] >>> Detected PINCH -> Left Click")
            human_controller.click()
            return

        # 2. 👍 Thumbs Up (Confirm / Enter)
        if thumb_up and not (index_up or middle_up or ring_up or pinky_up):
            self._last_action_time = now
            self._last_gesture = "Thumbs Up (Enter)"
            print("[GESTURE] >>> Detected THUMBS UP -> Press Enter")
            human_controller.press_key("enter")
            return

        # 3. ✌️ Peace Sign (Switch Window / Alt+Tab)
        if index_up and middle_up and not (ring_up or pinky_up):
            self._last_action_time = now
            self._last_gesture = "Peace Sign (Switch App)"
            print("[GESTURE] >>> Detected PEACE SIGN -> Switch Window")
            human_controller.press_shortcut("switch app")
            return

        # 4. ✊ Fist (Show Desktop)
        if not (index_up or middle_up or ring_up or pinky_up or thumb_up):
            self._last_action_time = now
            self._last_gesture = "Fist (Show Desktop)"
            print("[GESTURE] >>> Detected FIST -> Show Desktop")
            human_controller.press_shortcut("show desktop")
            return

        # 5. 🖐️ Open Palm (Pause / Mute)
        if index_up and middle_up and ring_up and pinky_up:
            self._last_action_time = now
            self._last_gesture = "Open Palm (Mute/Pause)"
            print("[GESTURE] >>> Detected OPEN PALM -> Toggle Mute/Pause")
            human_controller.press_key("space")
            return


# Global singleton
gesture_engine = GestureEngine()
