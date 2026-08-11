"""
ai.py - ULTRON AI Generation & Response Validation Engine
Uses local Ollama qwen2.5:3b model with dynamic profile memory context,
strict response conciseness, backend health checking, and post-processing address sanitation.
"""

from __future__ import annotations

import re
import time
import urllib.request
import subprocess
import os
import ollama
from modules.memory.profile_manager import get_profile_manager

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
DEFAULT_MODEL = "qwen2.5:3b"

FORBIDDEN_ADDRESS_PATTERNS = [
    (r"\b(yeah|yes|sure|okay|thanks)\s+(man|bro|dude|buddy|mate|boss)\b", r"\1, Sir"),
    (r",\s*(man|bro|dude|buddy|mate|boss)\b", r", Sir"),
    (r"\b(man|bro|dude|buddy|mate|boss)\b", r"Sir"),
]


def check_ai_backend_health() -> tuple[bool, str, list[str]]:
    """
    Probes local Ollama service health and returns (is_healthy, status_msg, available_models).
    """
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            import json
            data = json.loads(resp.read().decode('utf-8'))
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, f"CONNECTED ({OLLAMA_URL})", models
    except Exception as e:
        # Attempt background auto-launch if ollama command is available
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                import json
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get("name", "") for m in data.get("models", [])]
                return True, f"CONNECTED AFTER AUTO-START ({OLLAMA_URL})", models
        except Exception:
            pass
        return False, f"UNREACHABLE ({e})", []


def validate_and_correct_address(text: str, target_address: str = "Sir") -> str:
    """
    Validates and cleans generated AI text before TTS playback.
    Enforces target_address ('Sir') and purges any forbidden casual user addressing terms.
    """
    if not text:
        return ""

    cleaned = text
    for pattern, replacement in FORBIDDEN_ADDRESS_PATTERNS:
        cleaned = re.sub(pattern, replacement.replace("Sir", target_address), cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def ask_ai(prompt: str) -> str:
    """
    Invokes Ollama LLM with dynamic profile context, concise output constraint,
    backend health verification, and post-processing address sanitation.
    """
    t0 = time.time()
    pm = get_profile_manager()
    pref_address = pm.data.get("preferences", {}).get("preferred_address", "Sir")
    system_ctx = pm.get_system_context()

    # Verify backend connection
    is_ok, health_msg, avail_models = check_ai_backend_health()
    if not is_ok:
        print(f"[AI ERROR] BACKEND UNREACHABLE: {health_msg}")
        return f"AI backend is currently offline, {pref_address}. Please start Ollama."

    target_model = DEFAULT_MODEL
    if DEFAULT_MODEL not in avail_models and len(avail_models) > 0:
        target_model = avail_models[0]

    full_system_prompt = (
        f"{system_ctx}\n"
        f"STRICT FORMATTING RULE: Keep your response extremely short and concise (1 short sentence max, 15-20 words limit). "
        f"Do NOT give long explanations. ALWAYS address the user as {pref_address}."
    )

    try:
        stream = ollama.chat(
            model=target_model,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        raw_answer = ""
        for chunk in stream:
            part = chunk.get("message", {}).get("content", "")
            print(part, end="", flush=True)
            raw_answer += part

        print()
        t_ai = int((time.time() - t0) * 1000)
        print(f"[TIME] AI generation ({target_model}): {t_ai} ms")

        final_answer = validate_and_correct_address(raw_answer, target_address=pref_address)
        return final_answer

    except Exception as e:
        print(f"[AI ERROR] Connection failed during generation: {e}")
        return f"AI backend connection error, {pref_address}. Host: {OLLAMA_HOST}:{OLLAMA_PORT}"