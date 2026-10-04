"""
modules/camera_vision.py - ULTRON Laptop Webcam Perception & Vision AI Engine

Accesses the laptop camera, captures a high-resolution frame, and analyzes it
using the Google Gemini 3.8 Flash multimodal vision model in real time.
"""

from __future__ import annotations

import base64
import os
import time
from typing import Tuple

import cv2
import requests


def _get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    return api_key


def capture_laptop_frame(device_idx: int = 0) -> Tuple[bool, str, bytes]:
    """Captures a single frame from the laptop webcam."""
    cap = cv2.VideoCapture(device_idx)
    if not cap.isOpened():
        # Try device index 1
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            return False, "Could not open laptop webcam.", b""

    # Let the camera auto-expose for 2 frames
    for _ in range(2):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return False, "Failed to capture image from camera.", b""

    # Save to disk for history
    save_dir = os.path.join("data", "camera_captures")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "latest_view.jpg")
    cv2.imwrite(save_path, frame)

    # Encode to JPEG bytes
    ret_enc, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret_enc:
        return False, "Failed to encode camera frame.", b""

    return True, save_path, buffer.tobytes()


def analyze_camera_view(user_prompt: str = "") -> Tuple[bool, str]:
    """
    Accesses the laptop camera and analyzes what it sees using Gemini 3.8 Flash.
    Returns (success, description_text).
    """
    print("[CAMERA VISION] Activating laptop camera...")
    ok, save_path, jpeg_bytes = capture_laptop_frame(0)
    if not ok:
        return False, "I was unable to access your laptop camera. Please verify camera permissions, Harsha."

    api_key = _get_gemini_api_key()
    if not api_key:
        return False, "Camera captured the view, but no vision API key is configured."

    b64_image = base64.b64encode(jpeg_bytes).decode("utf-8")

    prompt = (
        "You are ULTRON, a personal AI partner. "
        "Analyze this live snapshot from my laptop webcam. "
        "Describe what you see in front of the camera clearly, directly, and concisely in 1 to 2 natural sentences. "
        "Address me as Harsha."
    )
    if user_prompt:
        prompt += f" Specifically answer this question: {user_prompt}"

    candidate_models = ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.5-flash"]
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
            ]
        }],
        "generationConfig": {
            "maxOutputTokens": 100,
            "temperature": 0.2
        }
    }

    try:
        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                t0 = time.time()
                resp = requests.post(url, json=payload, timeout=7.0)
                dt = int((time.time() - t0) * 1000)
                print(f"[TIME] Camera Vision AI ({model}): {dt} ms")

                if resp.status_code == 200:
                    data = resp.json()
                    description = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    print(f"[CAMERA VISION] Result: '{description}'")
                    return True, description
            except Exception:
                continue

        return False, "I captured the camera frame, but cannot reach the vision service right now. Please verify your internet connection, Harsha."
    except Exception as e:
        print(f"[CAMERA VISION ERROR] {e}")
        return False, "I captured the camera frame, but cannot reach the vision service right now. Please verify your internet connection, Harsha."
