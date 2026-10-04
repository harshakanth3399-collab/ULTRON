"""
modules/region_snipper.py - ULTRON Selective Window Snip & Intelligent Explainer

Crops the focused application window using Win32 bounding coordinates, analyzes
the visual contents with multimodal AI, and explains visible errors or information.
"""

from __future__ import annotations

import base64
import ctypes
import os
import time
from typing import Optional, Tuple

import cv2
import requests

from modules.camera_vision import _get_gemini_api_key
from modules.screen_vision import take_screenshot

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def get_active_window_rect() -> Optional[Tuple[int, int, int, int]]:
    """Gets the (left, top, width, height) of the currently focused window."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 50 and h > 50:
            return (max(0, rect.left), max(0, rect.top), w, h)
    return None


def snip_and_explain_active_window(user_query: str = "") -> Tuple[bool, str]:
    """Captures and analyzes only the active focused window."""
    temp_full = os.path.abspath("data/screen_captures/latest_screen.png")
    os.makedirs(os.path.dirname(temp_full), exist_ok=True)

    ok, _ = take_screenshot(temp_full)
    if not ok or not os.path.exists(temp_full):
        return False, "Could not capture display."

    img = cv2.imread(temp_full)
    if img is None:
        return False, "Failed to read screen capture."

    # Crop to active window if rect available
    bounds = get_active_window_rect()
    if bounds:
        x, y, w, h = bounds
        screen_h, screen_w = img.shape[:2]
        crop_x2 = min(screen_w, x + w)
        crop_y2 = min(screen_h, y + h)
        if crop_x2 > x and crop_y2 > y:
            img = img[y:crop_y2, x:crop_x2]

    # Save cropped snip
    snip_path = os.path.abspath("data/screen_captures/active_window_snip.jpg")
    ret_enc, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ret_enc:
        return False, "Failed to encode cropped window snip."

    api_key = _get_gemini_api_key()
    if not api_key:
        return False, "No Gemini API key found to analyze window snip."

    b64_image = base64.b64encode(buf.tobytes()).decode("utf-8")
    prompt = (
        "You are ULTRON, Harsha's personal AI assistant. "
        "Analyze this focused window capture. Explain what is happening, identify any error dialog, "
        "or summarize the primary content clearly in 1 or 2 natural sentences."
    )
    if user_query:
        prompt += f" Specifically answer: '{user_query}'."

    candidate_models = ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.5-flash"]
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
                ]
            }],
            "generationConfig": {"maxOutputTokens": 120, "temperature": 0.2}
        }
        try:
            resp = requests.post(url, json=payload, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                return True, data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            continue

    return False, "I captured the window snip, but could not connect to the vision cloud, Harsha."
