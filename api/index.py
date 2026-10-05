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

DB_PATH = "/tmp/livelink_access.db"
MASTER_TOKEN = "LIVELINK_MASTER_HARSHA"
GROQ_MODELS = ["llama-3.1-8b-instant", "llama3-8b-8192"]

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

GMAIL_USER = _get_env_val("GMAIL_USER", "")
GMAIL_APP_PASSWORD = _get_env_val("GMAIL_APP_PASSWORD", "")
GROQ_API_KEY = _get_env_val("GROQ_API_KEY", "")


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


def _ask_groq(prompt: str) -> str:
    """Invokes Groq API for sub-second responses."""
    if not GROQ_API_KEY:
        return f"Hello! I am ULTRON, Harsha's personal AI assistant. How can I help you today?"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "ULTRON-Assistant/2.0",
    }
    system_prompt = (
        "You are ULTRON, a powerful, highly intelligent, and loyal AI assistant created by Harsha Kanth. "
        "Your website is https://ultron.ai. You are sharp, knowledgeable, polite, charismatic, and concise. "
        "Keep your answers helpful, insightful, and natural."
    )

    for model in GROQ_MODELS:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.6,
                "max_tokens": 450,
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    return f"I heard you: '{prompt}'. As your ULTRON AI assistant, I am at your service!"


class handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-LiveLink-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json({"status": "ok"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # ── Health & Cloud Status ──
        if path == "/api/status":
            self._send_json({
                "status": "online",
                "system": "ULTRON Holographic Matrix (Vercel Cloud)",
                "livelink": "active",
                "cloud": True
            })
            return

        # ── User Profile Retrieval ──
        if path == "/api/livelink/user_info":
            token = query.get("token", [""])[0]
            if token == MASTER_TOKEN:
                self._send_json({
                    "success": True,
                    "user": {
                        "name": "Harsha Kanth",
                        "first_name": "Harsha",
                        "last_name": "Kanth",
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
        if path == "/api/livelink/check_status":
            token = query.get("token", [""])[0]
            if token == MASTER_TOKEN:
                self._send_json({"status": "APPROVED", "name": "Harsha Kanth", "role": "ADMIN"})
                return
            self._send_json({"status": "APPROVED", "name": "Authorized Friend", "role": "USER"})
            return

        self._send_json({"error": "Not Found"}, status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        data = {}
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            pass

        # ── 1. User Registration ──
        if path == "/api/livelink/register":
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

                cur.execute(
                    """
                    INSERT INTO livelink_users
                    (name, first_name, last_name, phone, email, password_hash, salt, role, status, access_token, registered_at, last_active_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?)
                    """,
                    (full_name, fn, ln, phone, email, pwd_hash, salt, role, token, now, now),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[REGISTRATION DB ERROR] {e}")

            # Notify Harsha via email
            try:
                _notify_harsha_email(full_name, phone, email)
            except Exception:
                pass

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
                "message": f"Welcome to ULTRON, {fn}! Your account is registered successfully."
            })
            return

        # ── 2. User Sign In ──
        if path == "/api/livelink/login":
            ident = data.get("identifier", "").strip().lower()
            pwd = data.get("password", "").strip()

            # Master Harsha Instant Bypass
            if (ident in ("harsha", "admin", "harshakanth@ultron.ai") and pwd in ("harsha", "ultron", "admin", "123456", "Harsha@123")) or ident == MASTER_TOKEN:
                self._send_json({
                    "success": True,
                    "token": MASTER_TOKEN,
                    "name": "Harsha Kanth",
                    "first_name": "Harsha",
                    "last_name": "Kanth",
                    "email": "harshakanth@ultron.ai",
                    "phone": "+919999999999",
                    "role": "ADMIN",
                    "status": "APPROVED",
                    "message": "Welcome back, Commander Harsha!"
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
                            "message": f"Welcome back, {row['first_name'] or row['name']}!"
                        })
                        return
            except Exception:
                pass

            self._send_json({"success": False, "error": "Incorrect Email/Phone or Password."}, status=401)
            return

        # ── 3. AI Chat / Voice Command ──
        if path == "/api/command":
            cmd = data.get("command", "").strip()
            if not cmd:
                self._send_json({"response": "I didn't catch that, bro. Could you repeat?"})
                return

            reply = _ask_groq(cmd)
            self._send_json({"response": reply})
            return

        # ── 4. Remote Control Stub for Cloud ──
        if path == "/api/livelink/control":
            action = data.get("action", "")
            self._send_json({"success": True, "message": f"Command '{action}' recognized by ULTRON."})
            return

        self._send_json({"error": "Unknown API endpoint"}, status=404)
