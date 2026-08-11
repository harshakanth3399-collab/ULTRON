"""
ai.py - ULTRON Hybrid AI Generation & SQLite Logging Engine
Hybrid architecture:
  1. Groq API (llama-3.3-70b-versatile) for 0.3s sub-second responses when online.
  2. Ollama Local (qwen2.5:3b/7b) automatic fallback when offline.
  3. SQLite Database (memory/ultron.db) logging for structured chat history.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
import ollama

from modules.memory.profile_manager import get_profile_manager

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
DEFAULT_LOCAL_MODEL = "qwen2.5:3b"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _load_env_file() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass

_load_env_file()


FORBIDDEN_ADDRESS_PATTERNS = [
    (r"\b(yeah|yes|sure|okay|thanks)\s+(man|bro|dude|buddy|mate|boss)\b", r"\1, Sir"),
    (r",\s*(man|bro|dude|buddy|mate|boss)\b", r", Sir"),
    (r"\b(man|bro|dude|buddy|mate|boss)\b", r"Sir"),
]


def check_ai_backend_health() -> tuple[bool, str, list[str]]:
    """Probes local Ollama service health."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, f"CONNECTED ({OLLAMA_URL})", models
    except Exception as e:
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.2)
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get("name", "") for m in data.get("models", [])]
                return True, f"CONNECTED AFTER AUTO-START ({OLLAMA_URL})", models
        except Exception:
            pass
        return False, f"UNREACHABLE ({e})", []


def validate_and_correct_address(text: str, target_address: str = "Sir") -> str:
    """Sanitizes generated text before TTS playback."""
    if not text:
        return ""

    cleaned = text
    for pattern, replacement in FORBIDDEN_ADDRESS_PATTERNS:
        cleaned = re.sub(pattern, replacement.replace("Sir", target_address), cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _ask_groq(prompt: str, system_prompt: str, api_key: str) -> Optional[str]:
    """Invokes Groq API for sub-second responses."""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.5
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            answer = data["choices"][0]["message"]["content"].strip()
            return answer
    except Exception as e:
        print(f"[GROQ API NOTE] Groq API offline or unavailable ({e}). Falling back to Ollama Local.")
        return None


def ask_ai(prompt: str) -> str:
    """
    Invokes Hybrid AI Engine (Groq Online -> Ollama Offline fallback),
    sanitizes addressing ('Sir'), and logs to SQLite database (memory/ultron.db).
    """
    t0 = time.time()
    pm = get_profile_manager()
    pref_address = pm.data.get("preferences", {}).get("preferred_address", "Sir")
    system_ctx = pm.get_system_context()

    full_system_prompt = (
        f"{system_ctx}\n"
        f"STRICT FORMATTING RULE: Keep your response extremely short and concise (1 short sentence max, 15-20 words limit). "
        f"Do NOT give long explanations. ALWAYS address the user as {pref_address}."
    )

    raw_answer = None
    model_used = "groq-llama3.3"

    # 1. Try Groq API if GROQ_API_KEY environment variable is configured
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        raw_answer = _ask_groq(prompt, full_system_prompt, groq_key)

    # 2. Fallback to Local Ollama if Groq is unavailable or offline
    if not raw_answer:
        model_used = DEFAULT_LOCAL_MODEL
        is_ok, health_msg, avail_models = check_ai_backend_health()
        if not is_ok:
            print(f"[AI ERROR] BACKEND UNREACHABLE: {health_msg}")
            return f"AI backend is currently offline, {pref_address}. Please start Ollama."

        if DEFAULT_LOCAL_MODEL not in avail_models and len(avail_models) > 0:
            model_used = avail_models[0]

        try:
            stream = ollama.chat(
                model=model_used,
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
        except Exception as e:
            print(f"[AI ERROR] Ollama generation error: {e}")
            return f"AI generation error, {pref_address}."

    t_ai = int((time.time() - t0) * 1000)
    print(f"[TIME] AI generation ({model_used}): {t_ai} ms")

    # Sanitize address
    final_answer = validate_and_correct_address(raw_answer, target_address=pref_address)

    # 3. Log interaction to SQLite Database (memory/ultron.db)
    try:
        from modules.database import log_chat
        log_chat(user_prompt=prompt, ultron_response=final_answer, model_used=model_used, latency_ms=t_ai)
    except Exception as db_err:
        print(f"[SQLITE LOG NOTE] {db_err}")

    return final_answer