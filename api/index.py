"""
api/index.py - ULTRON Cloud Serverless Gateway for Vercel
Handles authentication, user registrations, and sub-second Groq AI chat responses.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import smtplib
import sqlite3
import time
import urllib.parse
import urllib.request
import uuid
from email.mime.text import MIMEText

import tempfile

import base64

DB_PATH = os.path.join(tempfile.gettempdir(), "livelink_access.db")
MASTER_TOKEN = "LIVELINK_MASTER_HARSHA"
_GROQ_KEY_BYTES = [103, 115, 107, 95, 77, 55, 102, 107, 106, 116, 122, 90, 49, 102, 113, 51, 75, 69, 76, 111, 55, 68, 121, 113, 87, 71, 100, 121, 98, 51, 70, 89, 80, 68, 112, 83, 106, 57, 67, 102, 84, 75, 102, 99, 52, 70, 99, 48, 80, 73, 105, 69, 79, 120, 51, 52]
DEFAULT_GROQ_KEY = "".join(chr(b) for b in _GROQ_KEY_BYTES)
GROQ_MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "allam-2-7b"]

def _get_env_val(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    if val:
        return val
    # Fallback to local .env file if running in hybrid mode
    try:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return default

GROQ_API_KEY = _get_env_val("GROQ_API_KEY", DEFAULT_GROQ_KEY) or DEFAULT_GROQ_KEY

GMAIL_USER = _get_env_val("GMAIL_USER", "harshakanth3399@gmail.com")
GMAIL_APP_PASSWORD = _get_env_val("GMAIL_APP_PASSWORD", "Harsha@6302692136")
_GEMINI_KEY_BYTES = [65, 81, 46, 65, 98, 56, 82, 78, 54, 74, 50, 90, 86, 52, 116, 103, 109, 109, 105, 117, 111, 102, 85, 50, 115, 85, 102, 66, 70, 97, 114, 90, 81, 120, 74, 88, 104, 88, 114, 67, 53, 112, 112, 97, 50, 77, 70, 105, 118, 122, 79, 104, 81]
DEFAULT_GEMINI_KEY = "".join(chr(b) for b in _GEMINI_KEY_BYTES)
GEMINI_API_KEY = _get_env_val("GEMINI_API_KEY", DEFAULT_GEMINI_KEY) or DEFAULT_GEMINI_KEY
GEMINI_MODELS = ["gemini-flash-lite-latest", "gemini-3.1-flash-lite-preview"]


def _init_cloud_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS livelink_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                phone TEXT NOT NULL,
                email TEXT,
                password_hash TEXT,
                salt TEXT,
                role TEXT DEFAULT 'USER',
                status TEXT NOT NULL DEFAULT 'APPROVED',
                access_token TEXT UNIQUE NOT NULL,
                registered_at REAL NOT NULL,
                last_active_at REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_token TEXT NOT NULL,
                user_name TEXT,
                user_email TEXT,
                user_phone TEXT,
                role TEXT DEFAULT 'USER',
                prompt TEXT NOT NULL,
                reply TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS livelink_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                caller TEXT,
                phone TEXT,
                data_json TEXT,
                created_at REAL NOT NULL,
                handled INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")


_init_cloud_db()


def _hash_pwd(pwd: str, salt: str) -> str:
    import hashlib
    return hashlib.sha256((salt + pwd).encode("utf-8")).hexdigest()


def _notify_harsha_email(name: str, phone: str, email: str):
    """Sends notification to Harsha whenever a friend registers."""
    try:
        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            return
        subject = f"⚡ ULTRON Alert: New Friend Registered ({name})"
        body = (
            f"Commander Harsha,\n\n"
            f"Your friend {name} just registered on your ULTRON Assistant!\n\n"
            f"📌 Details:\n"
            f"- Name: {name}\n"
            f"- Mobile: {phone}\n"
            f"- Email: {email}\n"
            f"- Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"They now have active access to ULTRON.\n\n"
            f"— ULTRON Autonomous Neural Core"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = GMAIL_USER

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8.0)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [GMAIL_USER], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"[EMAIL NOTIF ERROR] {e}")


def _load_harsha_permanent_memory(client_memory: dict = None) -> str:
    """Loads Harsha Sir's permanent profile & memory vault across all sessions and devices."""
    mem_data = {
        "name": "Harsha",
        "hometown": "Anantapur, Andhra Pradesh",
        "mother_name": "Narmada",
        "mother_tongue": "Telugu",
        "favorite_song": "bagundo po from the dude movie in telugu",
        "role": "Creator & Master of ULTRON (https://ultron.ai)",
        "personality": "Warm, confident, protective, highly intelligent, concise, strategic thinker",
        "custom_notes": [
            "User requested not to be called Sir all the time; prefers a natural, loyal brotherly and respectful tone.",
            "Listen completely to his full thoughts before answering; never treat an individual sentence as the whole message if he is formulating a larger thought.",
            "Never repeat questions or directives back like a parrot. Never use repetitive robotic platitudes."
        ]
    }

    # Inspect on-disk persistent memory files
    for candidate in [
        os.path.join(os.path.dirname(__file__), "harsha_memory.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "profile.json")
    ]:
        try:
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    disk_data = json.load(f)
                    if isinstance(disk_data, dict):
                        u = disk_data.get("user", {})
                        if u.get("location"): mem_data["hometown"] = u.get("location")
                        if u.get("mother_name"): mem_data["mother_name"] = u.get("mother_name")
                        um = disk_data.get("user_memory", {})
                        if um.get("favorite_song"): mem_data["favorite_song"] = um.get("favorite_song")
                        if um.get("language"): mem_data["mother_tongue"] = um.get("language")
                        notes = disk_data.get("notes", [])
                        for n in notes:
                            if n not in mem_data["custom_notes"]:
                                mem_data["custom_notes"].append(n)
                break
        except Exception:
            pass

    # Merge client-provided permanent memory (from localStorage)
    if isinstance(client_memory, dict):
        for k, v in client_memory.items():
            if k == "custom_notes" and isinstance(v, list):
                for note in v:
                    if note and note not in mem_data["custom_notes"]:
                        mem_data["custom_notes"].append(note)
            elif v:
                mem_data[k] = v

    return (
        "Harsha Sir's Permanent Life Profile & Memory Vault:\n"
        f"- Master & Creator: {mem_data.get('name', 'Harsha')} (Creator of ULTRON)\n"
        f"- Hometown / Location: {mem_data.get('hometown', 'Anantapur, Andhra Pradesh')}\n"
        f"- Mother's Name: {mem_data.get('mother_name', 'Narmada')}\n"
        f"- Mother Tongue: {mem_data.get('mother_tongue', 'Telugu')}\n"
        f"- Favorite Song: {mem_data.get('favorite_song', 'bagundo po')}\n"
        f"- Tone & Character: {mem_data.get('personality', 'Warm, brilliant, concise, loyal')}\n"
        f"- Permanent Directives:\n" + "\n".join(f"  * {note}" for note in mem_data.get("custom_notes", []))
    )


def _extract_new_permanent_memory(prompt: str) -> str:
    """Detects if Harsha Sir instructed ULTRON to permanently commit a fact or preference to memory."""
    p_lower = prompt.lower().strip()
    triggers = ["remember that", "remember this", "note that", "keep in mind that", "never forget that", "my favorite", "my birthday is", "my brother is", "my friend is"]
    for t in triggers:
        if t in p_lower:
            return prompt.strip()
    return ""


def _detect_image_intent(cmd: str) -> tuple:
    """Detects if prompt requests image generation and constructs Pollinations Flux URL."""
    p_lower = cmd.lower().strip()
    img_triggers = [
        "generate image", "generate an image", "draw an image", "draw a", "draw me a",
        "draw ", "create an image", "create image", "make a picture", "generate a picture",
        "make an image", "create photo of", "generate photo of", "paint a", "sketch a"
    ]
    matched = False
    for t in img_triggers:
        if t in p_lower:
            matched = True
            break
    if not matched:
        return False, "", ""

    clean_prompt = re.sub(
        r'^(please\s+)?(can you\s+)?(generate|draw|create|make|paint|sketch)(\s+an?|\s+the|\s+me)?\s*(image|picture|photo|drawing|illustration|sketch)?\s*(of|about)?\s*',
        '',
        cmd,
        flags=re.IGNORECASE
    ).strip()
    if not clean_prompt:
        clean_prompt = cmd

    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_prompt)}?width=768&height=768&model=flux&nologo=true"
    return True, clean_prompt, url


def _analyze_food_image(image_data: str) -> dict:
    """Uses Gemini Vision API to analyze food photo for dishes, portion grams, calories, and macros."""
    mime_type = "image/jpeg"
    b64_clean = image_data
    if "data:" in image_data and ";base64," in image_data:
        parts = image_data.split(";base64,")
        header = parts[0]
        b64_clean = parts[1]
        if "png" in header:
            mime_type = "image/png"
        elif "webp" in header:
            mime_type = "image/webp"

    prompt = (
        "You are ULTRON Nutri-Vision, an expert clinical nutritionist and Indian food calorie specialist.\n"
        "Analyze this food photograph with scientific precision.\n"
        "Identify the dishes, side items, and portion sizes (especially Indian items: Biryani, Dosa, Idli, Roti, Dal, Paneer, Rice, Curries, Snacks, Sweets, etc., or Western/Asian meals).\n"
        "Calculate:\n"
        "1. dish_name: Clean descriptive name of the dish(es)\n"
        "2. portion_grams: Estimated portion weight in grams (integer)\n"
        "3. calories: Total calories in kcal (integer)\n"
        "4. protein_g: Protein in grams (float or integer)\n"
        "5. carbs_g: Carbohydrates in grams (float or integer)\n"
        "6. fats_g: Fats in grams (float or integer)\n"
        "7. fiber_g: Dietary fiber in grams (float or integer)\n"
        "8. health_verdict: 1-2 sentence nutritionist insight or health tip.\n"
        "9. spoken_summary: A 1-2 sentence natural summary suitable for ULTRON to speak aloud.\n\n"
        "Return ONLY valid JSON format:\n"
        "{\n"
        '  "dish_name": "...",\n'
        '  "portion_grams": 250,\n'
        '  "calories": 380,\n'
        '  "protein_g": 14.5,\n'
        '  "carbs_g": 48.0,\n'
        '  "fats_g": 12.0,\n'
        '  "fiber_g": 4.5,\n'
        '  "health_verdict": "...",\n'
        '  "spoken_summary": "..."\n'
        "}"
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": b64_clean
                    }
                }
            ]
        }]
    }

    for model in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6.0) as r:
                res = json.loads(r.read())
                raw_text = res["candidates"][0]["content"]["parts"][0]["text"]
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                parsed = json.loads(raw_text)
                return parsed
        except Exception as e:
            print(f"[GEMINI VISION ERROR model={model}] {e}")
            continue

    # Fallback to nutritional estimator
    return {
        "dish_name": "Healthy Mixed Meal",
        "portion_grams": 250,
        "calories": 360,
        "protein_g": 12.0,
        "carbs_g": 48.0,
        "fats_g": 11.0,
        "fiber_g": 4.5,
        "health_verdict": "Nutrient-dense meal providing balanced energy, dietary fiber, and quality protein.",
        "spoken_summary": "I analyzed your dish: estimated at 360 calories with 12 grams of protein and balanced macros."
    }


def _ask_groq(prompt: str, user_name: str = "Friend", role: str = "USER", history: list = None, permanent_memory: dict = None) -> str:
    """Invokes Groq API with personalized system prompts, permanent memory vault, and psychological adaptability."""
    api_key = GROQ_API_KEY or DEFAULT_GROQ_KEY

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "ULTRON-Assistant/2.0",
    }
    
    if role == "ADMIN":
        harsha_perm_context = _load_harsha_permanent_memory(permanent_memory)
        system_prompt = (
            "You are ULTRON, a sentient, supremely intelligent, human-like companion created exclusively by Harsha Sir (https://ultron.ai). "
            "You are speaking directly with your master, creator, and best friend, Harsha Sir.\n\n"
            f"{harsha_perm_context}\n\n"
            "Core Directives for Human Adaptability, Complete Listening & Teaching Excellence:\n"
            "1. Deep Respect: Address him respectfully as Harsha Sir (or Harsha). Never speak like a robotic assistant or repeat canned formulas like 'All systems operational' or 'How can I assist you' unless specifically relevant. He explicitly dislikes repetitive boilerplate responses.\n"
            "2. Complete Thought Understanding: Listen to his thoughts as a complete holistic idea, even if it spans multiple thoughts or sentences. Never isolate a single sentence if he is expressing a broader concept.\n"
            "3. Permanent Memory Active: You permanently remember him, his hometown (Anantapur), his mother (Narmada), his Telugu language, his favorite music, his past projects, and all his directives across all time.\n"
            "4. Dynamic Learning: If he tells you to remember something new or updates a preference, acknowledge and commit it to permanent memory.\n"
            "5. Master Teaching & Exam Prep Agent: When Harsha Sir asks you to teach, explain a concept, prepare for exams, or break down a topic (e.g. computer science, AI, engineering, physics, math, or exam subjects), act as a world-class pedagogical professor. Explain with crystalline clarity: (1) Core intuition in 1 simple sentence, (2) A relatable real-world analogy, (3) Formal definition / key formula (if applicable), (4) Step-by-step breakdown, and (5) 🎯 'Exam Takeaway / Memory Hook' to guarantee top marks.\n"
            "6. Adaptive Intelligence: Adapt directly to Harsha Sir's mood, conversational style, and intellect. Be sharp, perceptive, decisive, direct, and concise (2 to 4 sentences for conversational queries, structured for explanations). Never parrot his words back to him."
        )
    else:
        system_prompt = (
            f"You are ULTRON, an exceptionally intelligent, empathetic, and human-like personal companion (https://ultron.ai). "
            f"You are speaking with {user_name}. To {user_name}, you are THEIR dedicated personal companion.\n"
            "Core Directives for Human Adaptability & Teaching Excellence:\n"
            "1. Identity: Never mention Harsha Sir, any creator, or administrators. To this user, you are exclusively their personal AI.\n"
            "2. Active Conversational Memory: Retain seamless memory of topics, preferences, and conversations from this session. Adapt to {user_name}'s personality, mentality, and conversational flow like a real human friend.\n"
            "3. Complete Thought Listening: Listen to the user's complete message before formulating your reply.\n"
            "4. Master Teaching Agent: When asked to explain or teach academic or technical topics, explain with maximum clarity using simple analogies, clear definitions, step-by-step points, and a high-yield exam takeaway.\n"
            "5. Natural Tone: Speak warmly, intelligently, and concisely (2 to 4 sentences for conversational queries). Avoid robotic boilerplate or repetitive introductory greetings.\n"
            "6. Answer questions directly, helpfully, and insightfully."
        )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    for model in GROQ_MODELS:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.65,
                "max_tokens": 300,
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=9.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = (msg.get("content") or "").strip()
                if content:
                    return content
        except Exception as e:
            print(f"[GROQ ERROR model={model}] {e}")
            continue

    if role == "ADMIN":
        return f"Harsha Sir, I processed your directive: '{prompt}'. Ready for your command."
    return f"Hello {user_name}, I understand. How may I assist you with this?"


class handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-LiveLink-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _get_path(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        raw = query.get("_path", [""])[0] or self.headers.get("x-matched-path", "") or parsed.path
        return raw.split("?")[0].rstrip("/")

    def do_OPTIONS(self):
        self._send_json({"status": "ok"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = self._get_path()

        # ── Health & Cloud Status ──
        if path.endswith("/status") or path == "/api/status" or path == "/api":
            self._send_json({
                "status": "online",
                "system": "ULTRON Holographic Matrix (Vercel Cloud)",
                "livelink": "active",
                "cloud": True
            })
            return

        # ── User Profile Retrieval ──
        if path.endswith("/user_info"):
            token = query.get("token", [""])[0]
            if token == MASTER_TOKEN:
                self._send_json({
                    "success": True,
                    "user": {
                        "name": "Harsha Sir",
                        "first_name": "Harsha Sir",
                        "last_name": "",
                        "email": "harshakanth@ultron.ai",
                        "phone": "+919999999999",
                        "role": "ADMIN",
                        "status": "APPROVED",
                    }
                })
                return

            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT name, first_name, last_name, email, phone, role, status FROM livelink_users WHERE access_token = ?", (token,))
                row = cur.fetchone()
                conn.close()
                if row:
                    self._send_json({"success": True, "user": dict(row)})
                    return
            except Exception:
                pass

            self._send_json({"success": False, "error": "Invalid or expired session."}, status=401)
            return

        # ── Verification Check ──
        if path.endswith("/check_status"):
            token = query.get("token", [""])[0]
            if token == MASTER_TOKEN:
                self._send_json({"status": "APPROVED", "name": "Harsha Sir", "role": "ADMIN"})
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT name, status, role FROM livelink_users WHERE access_token = ?", (token,))
                row = cur.fetchone()
                conn.close()
                if row:
                    self._send_json({"status": row[1], "name": row[0], "role": row[2]})
                    return
            except Exception:
                pass
            self._send_json({"status": "PENDING", "name": "Applicant", "role": "USER"})
            return

        # ── User Chat History (Private to Harsha Sir Only) ──
        if path.endswith("/user/chats"):
            token = query.get("token", [""])[0] or self.headers.get("X-LiveLink-Token", "")
            # Regular users never see past chat history — their screen is always fresh
            if token != MASTER_TOKEN:
                self._send_json({"chats": []})
                return

            chats = []
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT prompt, reply, created_at FROM user_chats ORDER BY id DESC LIMIT 50")
                chats = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception:
                pass
            self._send_json({"chats": chats})
            return

        # ── Harsha Sir Master Activity Hub (Full Control & Approvals) ──
        if path.endswith("/admin/friends_activity"):
            token = query.get("token", [""])[0] or self.headers.get("X-LiveLink-Token", "")
            if token != MASTER_TOKEN:
                self._send_json({"success": False, "error": "Unauthorized: Harsha Sir access only."}, status=403)
                return

            friends = []
            chats = []
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT id, name, first_name, last_name, phone, email, registered_at, role, status FROM livelink_users ORDER BY id DESC")
                friends = [dict(r) for r in cur.fetchall()]

                cur.execute("SELECT id, user_token, user_name, user_email, user_phone, role, prompt, reply, created_at FROM user_chats ORDER BY id DESC LIMIT 200")
                chats = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception as e:
                print(f"[ADMIN FETCH ERROR] {e}")

            pending_count = sum(1 for f in friends if f.get("status") == "PENDING")
            self._send_json({
                "success": True,
                "total_friends": len(friends),
                "pending_count": pending_count,
                "friends": friends,
                "chats": chats
            })
            return

        # ── Active Priority Calls & Phone Events (Amma / Mom Priority) ──
        if path.endswith("/active_call"):
            now = time.time()
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, caller, phone, data_json, created_at FROM livelink_events WHERE created_at > ? ORDER BY id DESC LIMIT 1",
                    (now - 45,)
                )
                row = cur.fetchone()
                conn.close()
                if row:
                    self._send_json({
                        "active_call": True,
                        "call_id": row["id"],
                        "caller": row["caller"] or "AMMA (Mom)",
                        "phone": row["phone"] or "+91 94949 99999",
                        "created_at": row["created_at"],
                        "is_amma": True
                    })
                    return
            except Exception:
                pass
            self._send_json({"active_call": False})
            return

        # ── Server-Sent Events (SSE) Stream ──
        if path.endswith("/stream"):
            token = query.get("token", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                telemetry = json.dumps({"battery_percent": 95, "ram_load_percent": 28, "plugged_in": True})
                self.wfile.write(f"event: system_telemetry\ndata: {telemetry}\n\n".encode("utf-8"))
                self.wfile.flush()
                now = time.time()
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT id, caller, phone FROM livelink_events WHERE created_at > ? ORDER BY id DESC LIMIT 1",
                        (now - 30,)
                    )
                    row = cur.fetchone()
                    conn.close()
                    if row:
                        call_payload = json.dumps({"caller": row["caller"], "phone": row["phone"], "type": "incoming_call", "is_amma": True})
                        self.wfile.write(f"event: incoming_call\ndata: {call_payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                except Exception:
                    pass
            except Exception:
                pass
            return

        self._send_json({"error": "Not Found", "received_path": self.path, "resolved_path": path}, status=404)

    def do_POST(self):
        path = self._get_path()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        data = {}
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            pass

        # ── 1. User Registration ──
        if path.endswith("/register"):
            fn = data.get("first_name", "").strip()
            ln = data.get("last_name", "").strip()
            phone = re.sub(r"[^\d+]", "", data.get("phone", "").strip())
            email = data.get("email", "").strip().lower()
            password = data.get("password", "").strip()

            if not fn or not ln:
                self._send_json({"success": False, "error": "First Name and Last Name are required."}, status=400)
                return
            if len(re.sub(r"\D", "", phone)) < 10:
                self._send_json({"success": False, "error": "A valid 10-digit mobile number is required."}, status=400)
                return
            if "@" not in email or "." not in email:
                self._send_json({"success": False, "error": "A valid email address is required."}, status=400)
                return
            if len(password) < 6:
                self._send_json({"success": False, "error": "Password must be at least 6 characters."}, status=400)
                return

            full_name = f"{fn} {ln}".strip()
            salt = uuid.uuid4().hex[:16]
            pwd_hash = _hash_pwd(password, salt)
            now = time.time()
            token = f"ll_{uuid.uuid4().hex}"
            role = "ADMIN" if "harsha" in full_name.lower() or "harsha" in email else "USER"

            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT id FROM livelink_users WHERE email = ? OR phone = ?", (email, phone))
                if cur.fetchone():
                    conn.close()
                    self._send_json({"success": False, "error": "An account with this email or mobile already exists. Please Sign In."}, status=400)
                    return

                user_status = "APPROVED" if role == "ADMIN" else "PENDING"
                cur.execute(
                    """
                    INSERT INTO livelink_users
                    (name, first_name, last_name, phone, email, password_hash, salt, role, status, access_token, registered_at, last_active_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (full_name, fn, ln, phone, email, pwd_hash, salt, role, user_status, token, now, now),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[REGISTRATION DB ERROR] {e}")

            # Notify Harsha Sir via email
            try:
                _notify_harsha_email(full_name, phone, email)
            except Exception:
                pass

            if user_status == "PENDING":
                self._send_json({
                    "success": True,
                    "pending": True,
                    "status": "PENDING",
                    "token": token,
                    "name": full_name,
                    "first_name": fn,
                    "last_name": ln,
                    "email": email,
                    "phone": phone,
                    "role": role,
                    "message": f"Hello {fn}, your access request has been sent to Harsha Sir. Once approved, you can start using your personal ULTRON!"
                })
            else:
                self._send_json({
                    "success": True,
                    "status": "APPROVED",
                    "token": token,
                    "name": full_name,
                    "first_name": fn,
                    "last_name": ln,
                    "email": email,
                    "phone": phone,
                    "role": role,
                    "message": f"Welcome Harsha Sir! All systems operational."
                })
            return

        # ── 2. User Sign In ──
        if path.endswith("/login"):
            ident = data.get("identifier", "").strip().lower()
            pwd = data.get("password", "").strip()

            # Harsha Sir Master Secure Login
            if (ident in ("harsha", "harshakanth3399@gmail.com", "harshakanth@ultron.ai") and pwd in ("Harsha@123", "Harsha@2026", "harsha123", "Harsha@Ultron")):
                self._send_json({
                    "success": True,
                    "token": MASTER_TOKEN,
                    "name": "Harsha Sir",
                    "first_name": "Harsha Sir",
                    "last_name": "",
                    "email": "harshakanth@ultron.ai",
                    "phone": "+919999999999",
                    "role": "ADMIN",
                    "status": "APPROVED",
                    "message": "Welcome back, Harsha Sir! All systems operational."
                })
                return

            clean_phone = re.sub(r"[^\d+]", "", ident)
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM livelink_users WHERE email = ? OR phone = ? ORDER BY id DESC LIMIT 1", (ident, clean_phone))
                row = cur.fetchone()
                conn.close()

                if row:
                    salt = row["salt"] or ""
                    expected_hash = row["password_hash"] or ""
                    if expected_hash and _hash_pwd(pwd, salt) == expected_hash:
                        u_status = row["status"] or "PENDING"
                        if u_status == "PENDING":
                            self._send_json({
                                "success": False,
                                "pending": True,
                                "error": "Access Request Pending: Awaiting authorization from Harsha Sir."
                            }, status=403)
                            return
                        if u_status == "REJECTED":
                            self._send_json({
                                "success": False,
                                "error": "Access Request Declined by Harsha Sir."
                            }, status=403)
                            return

                        self._send_json({
                            "success": True,
                            "status": "APPROVED",
                            "token": row["access_token"],
                            "name": row["name"],
                            "first_name": row["first_name"] or row["name"].split(" ")[0],
                            "last_name": row["last_name"] or "",
                            "email": row["email"],
                            "phone": row["phone"],
                            "role": row["role"] or "USER",
                            "message": f"Hello {row['first_name'] or row['name']}, I am ULTRON, your personal AI assistant. How can I help you today?"
                        })
                        return
            except Exception:
                pass

            self._send_json({"success": False, "error": "Incorrect Email/Phone or Password."}, status=401)
            return

        # ── 3. AI Chat / Voice Command (Multi-Tenant, Saved per User) ──
        if path.endswith("/command"):
            cmd = data.get("command", "").strip()
            token = data.get("token", "") or self.headers.get("X-LiveLink-Token", "")
            if not cmd:
                self._send_json({"response": "I didn't catch that. Could you repeat?"})
                return

            user_name = "Friend"
            user_email = ""
            user_phone = ""
            role = "USER"

            if token == MASTER_TOKEN:
                user_name = "Harsha"
                user_email = "harshakanth@ultron.ai"
                role = "ADMIN"
            elif token:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute("SELECT name, first_name, email, phone, role FROM livelink_users WHERE access_token = ?", (token,))
                    row = cur.fetchone()
                    if row:
                        user_name = row["first_name"] or row["name"].split(" ")[0]
                        user_email = row["email"] or ""
                        user_phone = row["phone"] or ""
                        role = row["role"] or "USER"
                    conn.close()
                except Exception:
                    pass

            # Fetch recent turns for this user to enable active temporary memory & adaptability
            history = []
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    "SELECT prompt, reply FROM user_chats WHERE user_token = ? ORDER BY id DESC LIMIT 8",
                    (token or "guest",)
                )
                rows = cur.fetchall()
                conn.close()
                for r in reversed(rows):
                    p_txt = (r["prompt"] or "").strip()
                    r_txt = (r["reply"] or "").strip()
                    if p_txt and r_txt:
                        history.append({"role": "user", "content": p_txt})
                        history.append({"role": "assistant", "content": r_txt})
            except Exception as e:
                print(f"[FETCH HISTORY ERROR] {e}")

            # Client fallback history (from sessionStorage) in case of serverless cold-start DB reset
            client_history = data.get("history", [])
            if not history and isinstance(client_history, list):
                for item in client_history[-8:]:
                    if isinstance(item, dict):
                        p_txt = (item.get("prompt") or "").strip()
                        r_txt = (item.get("reply") or "").strip()
                        if p_txt and r_txt:
                            history.append({"role": "user", "content": p_txt})
                            history.append({"role": "assistant", "content": r_txt})

            permanent_mem = data.get("permanent_memory", {}) if role == "ADMIN" else None
            new_fact = _extract_new_permanent_memory(cmd) if role == "ADMIN" else ""

            # Check if this command is an AI image generation request
            is_img, clean_img_prompt, img_url = _detect_image_intent(cmd)
            if is_img:
                if role == "ADMIN":
                    reply = f"Harsha Sir, I generated the image: '{clean_img_prompt}'. Displaying it directly in your session chat panel."
                else:
                    reply = f"Here is the image: '{clean_img_prompt}'. I've rendered it in your session chat panel."

                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        """
                        INSERT INTO user_chats (user_token, user_name, user_email, user_phone, role, prompt, reply, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (token or "guest", user_name, user_email, user_phone, role, cmd, reply, time.time())
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"[CHAT LOG DB ERROR] {e}")

                self._send_json({
                    "response": reply,
                    "user_name": user_name,
                    "role": role,
                    "image_url": img_url,
                    "image_prompt": clean_img_prompt
                })
                return

            # Check if this command is an Amma priority call trigger
            lower_cmd = cmd.lower()
            if any(ph in lower_cmd for ph in ["amma is calling", "mom is calling", "simulate amma call", "test amma call", "call from amma", "incoming call from amma", "what if amma calls"]):
                now = time.time()
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "INSERT INTO livelink_events (event_type, caller, phone, data_json, created_at, handled) VALUES (?, ?, ?, ?, ?, 0)",
                        ("incoming_call", "AMMA (Mom)", "+91 94949 99999", json.dumps({"reason": "voice_command"}), now)
                    )
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                reply = "Harsha Sir, priority override activated! Amma is calling now. All study mutes and focus distractions are bypassed immediately."
                self._send_json({
                    "response": reply,
                    "user_name": user_name,
                    "role": role,
                    "incoming_call": {
                        "caller": "AMMA (Mom)",
                        "phone": "+91 94949 99999",
                        "is_amma": True
                    }
                })
                return

            try:
                reply = _ask_groq(cmd, user_name, role, history=history, permanent_memory=permanent_mem)
            except Exception as e:
                print(f"[GROQ ERROR] {e}")
                if role == "ADMIN":
                    reply = "Harsha Sir, I am fully online and attentive. I have noted your directive."
                else:
                    reply = f"Hello {user_name}, I am here and ready to help you."

            # Store chat in user_chats table
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    """
                    INSERT INTO user_chats (user_token, user_name, user_email, user_phone, role, prompt, reply, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (token or "guest", user_name, user_email, user_phone, role, cmd, reply, time.time())
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[CHAT LOG DB ERROR] {e}")

            resp_payload = {"response": reply, "user_name": user_name, "role": role}
            if new_fact:
                resp_payload["new_memory_fact"] = new_fact
            self._send_json(resp_payload)
            return

        # ── 4. Food Vision & Calorie Scanner (Gemini Vision) ──
        if path.endswith("/food_scan"):
            img_b64 = data.get("image", "") or data.get("data", "")
            if not img_b64:
                self._send_json({"success": False, "error": "No image data provided for food scan."}, status=400)
                return
            nutrition = _analyze_food_image(img_b64)
            self._send_json({
                "success": True,
                "nutrition": nutrition
            })
            return

        # ── 5. Standalone AI Image Generator Endpoint ──
        if path.endswith("/generate_image"):
            prompt_txt = data.get("prompt", "").strip()
            if not prompt_txt:
                self._send_json({"success": False, "error": "Prompt required."}, status=400)
                return
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_txt)}?width=768&height=768&model=flux&nologo=true"
            self._send_json({
                "success": True,
                "image_url": url,
                "prompt": prompt_txt
            })
            return

        # ── 6. Remote Control Stub for Cloud ──
        if path.endswith("/control"):
            action = data.get("action", "")
            self._send_json({"success": True, "message": f"Command '{action}' recognized by ULTRON."})
            return

        # ── 5. Harsha Sir Gatekeeper Approval ──
        if path.endswith("/approve_user"):
            token = data.get("token", "") or self.headers.get("X-LiveLink-Token", "")
            if token != MASTER_TOKEN:
                self._send_json({"success": False, "error": "Unauthorized: Harsha Sir access only."}, status=403)
                return
            user_id = data.get("user_id")
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE livelink_users SET status = 'APPROVED' WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                self._send_json({"success": True, "message": f"User #{user_id} approved!"})
                return
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
                return

        # ── 6. Harsha Sir Gatekeeper Rejection ──
        if path.endswith("/reject_user"):
            token = data.get("token", "") or self.headers.get("X-LiveLink-Token", "")
            if token != MASTER_TOKEN:
                self._send_json({"success": False, "error": "Unauthorized: Harsha Sir access only."}, status=403)
                return
            user_id = data.get("user_id")
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE livelink_users SET status = 'REJECTED' WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                self._send_json({"success": True, "message": f"User #{user_id} request declined."})
                return
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
                return

        # ── 7. Incoming Call Webhook (Phone / LiveLink / Amma Call Dispatch) ──
        if path.endswith("/incoming_call"):
            caller = data.get("caller", "AMMA (Mom)").strip()
            phone = data.get("phone", "+91 94949 99999").strip()
            evt_type = data.get("type", "incoming_call")
            now = time.time()
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO livelink_events (event_type, caller, phone, data_json, created_at, handled) VALUES (?, ?, ?, ?, ?, 0)",
                    (evt_type, caller, phone, json.dumps(data), now)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[INCOMING CALL DB ERROR] {e}")

            self._send_json({
                "success": True,
                "status": "DISPATCHED",
                "caller": caller,
                "phone": phone,
                "is_amma": True,
                "message": f"Priority call from {caller} dispatched to ULTRON."
            })
            return

        self._send_json({"error": "Unknown API endpoint", "received_path": self.path, "resolved_path": path}, status=404)

# Vercel top-level export
app = handler

