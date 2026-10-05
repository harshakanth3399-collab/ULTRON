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

DB_PATH = os.path.join(tempfile.gettempdir(), "livelink_access.db")
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


def _ask_groq(prompt: str, user_name: str = "Friend", role: str = "USER") -> str:
    """Invokes Groq API with personalized system prompts for Harsha Sir vs Users."""
    if not GROQ_API_KEY:
        if role == "ADMIN":
            return f"Harsha Sir, I received your directive: '{prompt}'. All systems operational."
        return f"Hello {user_name}, I am ULTRON, your personal AI assistant. How can I help you today?"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "ULTRON-Assistant/2.0",
    }
    
    if role == "ADMIN":
        system_prompt = (
            "You are ULTRON, a supremely intelligent, loyal, and powerful AI assistant created by Harsha Sir. "
            "You are speaking directly with your master and creator, Harsha Sir (https://ultron.ai). "
            "Address him with deep respect as Harsha Sir. Be sharp, brilliant, decisive, and concise."
        )
    else:
        system_prompt = (
            f"You are ULTRON, an intelligent and friendly personal AI assistant (https://ultron.ai). "
            f"You are speaking with {user_name}. To {user_name}, you are THEIR personal AI assistant. "
            "Never mention Harsha Sir, any other creator, or anyone else. "
            f"Always act as {user_name}'s dedicated personal AI assistant. "
            "Be warm, polite, highly knowledgeable, and concise. Answer their questions directly and helpfully."
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

    if role == "ADMIN":
        return f"Harsha Sir, I heard: '{prompt}'. Ready for your next command."
    return f"Hello {user_name}, I heard: '{prompt}'. I am your personal AI assistant. How can I help you today?"


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

            reply = _ask_groq(cmd, user_name, role)

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

            self._send_json({"response": reply, "user_name": user_name, "role": role})
            return

        # ── 4. Remote Control Stub for Cloud ──
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

        self._send_json({"error": "Unknown API endpoint", "received_path": self.path, "resolved_path": path}, status=404)

# Vercel top-level export
app = handler

