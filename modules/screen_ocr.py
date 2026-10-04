"""
modules/screen_ocr.py - ULTRON Document & Screen OCR Intelligence Engine

Captures active screen or physical document held in front of webcam, runs multimodal
OCR and visual comprehension via Gemini 3.8 Flash, and delivers clear spoken answers.
"""

from __future__ import annotations

import base64
import os
import time
from typing import Tuple

import cv2
import requests
from modules.camera_vision import _get_gemini_api_key, capture_laptop_frame
from modules.screen_vision import take_screenshot


def read_screen_content(user_question: str = "") -> Tuple[bool, str]:
    """
    Captures the primary monitor screen, extracts visible text, and explains
    the content, code, or error message concisely.
    """
    temp_img = os.path.abspath("data/screen_captures/latest_screen.png")
    os.makedirs(os.path.dirname(temp_img), exist_ok=True)

    ok, _ = take_screenshot(temp_img)
    if not ok or not os.path.exists(temp_img):
        return False, "Could not capture the current screen."

    api_key = _get_gemini_api_key()
    if not api_key:
        return False, "No Gemini API key found to analyze the screen."

    try:
        # Load and compress for fast network transfer
        img = cv2.imread(temp_img)
        if img is None:
            return False, "Failed to read captured screen image."
        # Resize if 4K to 1280 wide to save bandwidth and latency
        h, w = img.shape[:2]
        if w > 1920:
            scale = 1920 / w
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        ret, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        b64_image = base64.b64encode(buf.tobytes()).decode("utf-8")

        prompt = (
            "You are ULTRON, Harsha's personal AI assistant. "
            "Analyze this screenshot of Harsha's computer screen. "
            "Read the primary text, diagnose any visible errors, or explain what is open. "
            "Respond directly and clearly in 1 to 2 crisp, human sentences."
        )
        if user_question:
            prompt += f" Specifically answer Harsha's question: '{user_question}'."

        candidate_models = ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.5-flash"]
        last_error = ""

        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
                    ]
                }],
                "generationConfig": {"maxOutputTokens": 150, "temperature": 0.2}
            }

            try:
                t0 = time.time()
                resp = requests.post(url, json=payload, timeout=8.0)
                dt = int((time.time() - t0) * 1000)
                print(f"[TIME] Screen OCR AI ({model}): {dt} ms")

                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return True, text
                else:
                    last_error = f"status {resp.status_code}"
            except Exception as e:
                last_error = str(e)

        return False, f"Vision API temporarily unavailable: {last_error}"
    except Exception as e:
        print(f"[SCREEN OCR ERROR] {e}")
        return False, f"Unable to process screen content: {e}"


def read_physical_document(user_question: str = "") -> Tuple[bool, str]:
    """
    Uses webcam to capture and read physical paper/book/ID card held in hand.
    """
    ok, save_path, jpeg_bytes = capture_laptop_frame(0)
    if not ok:
        return False, "Could not capture document through webcam."

    api_key = _get_gemini_api_key()
    if not api_key:
        return False, "No Gemini API key configured."

    b64_image = base64.b64encode(jpeg_bytes).decode("utf-8")
    prompt = (
        "You are ULTRON. Read the physical document, book, or paper held up to the camera. "
        "Extract the main text, heading, or important notes and summarize in 1 or 2 sentences."
    )
    if user_question:
        prompt += f" Answer Harsha's request: '{user_question}'."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
            ]
        }],
        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.2}
    }

    try:
        resp = requests.post(url, json=payload, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            return True, data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return False, f"Camera OCR returned status {resp.status_code}."
    except Exception as e:
        return False, f"Failed to read document: {e}"
