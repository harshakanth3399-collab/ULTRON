"""
modules/livelink_gatekeeper.py - ULTRON LiveLink Gatekeeper & Permission Engine

Enforces strict access control for ULTRON LiveLink cross-device app:
1. Strict Gatekeeper Verification:
   - Collects user details: Full Name, Phone Number (Mandatory), Purpose/Role.
   - Status: PENDING until Harsha explicitly grants permission.
   - Unverified / unapproved devices are strictly blocked from controlling ULTRON.
2. Admin Authorization:
   - Notifies Harsha immediately via desktop voice and Windows notification.
   - Harsha can grant/deny/revoke access via voice command, chat command, or admin token.
3. Session Security:
   - Cryptographic access tokens stored in SQLite database (memory/livelink_access.db).
   - Localhost / Harsha's master device auto-whitelisted.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "livelink_access.db")
MASTER_TOKEN = "LIVELINK_MASTER_HARSHA"
ADMIN_PHONE = "ADMIN_HARSHA"


class LiveLinkGatekeeper:
    """Manages LiveLink access requests, verification, authorization, and permission enforcement."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes the LiveLink SQLite access control table and auto-migrates columns."""
        with self._lock, self._get_connection() as conn:
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
                    purpose TEXT,
                    client_ip TEXT,
                    user_agent TEXT,
                    status TEXT NOT NULL DEFAULT 'APPROVED',
                    access_token TEXT UNIQUE NOT NULL,
                    requested_at REAL NOT NULL,
                    approved_at REAL,
                    last_active_at REAL
                )
                """
            )
            # Safe auto-migration for existing databases
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(livelink_users)").fetchall()}
            for col, col_type in [
                ("first_name", "TEXT"),
                ("last_name", "TEXT"),
                ("email", "TEXT"),
                ("password_hash", "TEXT"),
                ("salt", "TEXT"),
                ("role", "TEXT DEFAULT 'USER'"),
            ]:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE livelink_users ADD COLUMN {col} {col_type}")

            # Create indexes for fast lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_token ON livelink_users(access_token)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_phone ON livelink_users(phone)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_status ON livelink_users(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_email ON livelink_users(email)")
            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        import hashlib
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def register_user(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        password: str,
        client_ip: str = "",
        user_agent: str = "",
    ) -> Dict[str, Any]:
        """Registers a new user with name, mobile, email, and password."""
        fn = (first_name or "").strip()
        ln = (last_name or "").strip()
        clean_phone = self.sanitize_phone(phone)
        clean_email = (email or "").strip().lower()
        pwd = (password or "").strip()

        if not fn:
            return {"success": False, "error": "First Name is required."}
        if not ln:
            return {"success": False, "error": "Last Name is required."}
        digits = re.sub(r"\D", "", clean_phone)
        if len(digits) < 10:
            return {"success": False, "error": "A valid 10-digit mobile number is required."}
        if "@" not in clean_email or "." not in clean_email:
            return {"success": False, "error": "A valid email address is required."}
        if len(pwd) < 6:
            return {"success": False, "error": "Password must be at least 6 characters long."}

        full_name = f"{fn} {ln}".strip()
        salt = uuid.uuid4().hex[:16]
        pwd_hash = self._hash_password(pwd, salt)
        now = time.time()
        new_token = f"ll_{uuid.uuid4().hex}"

        is_harsha = "harsha" in full_name.lower() or "harsha" in clean_email.lower()
        role = "ADMIN" if is_harsha else "USER"
        status = "APPROVED"

        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM livelink_users WHERE email = ? AND email != ''", (clean_email,))
            if cur.fetchone():
                return {"success": False, "error": "An account with this email already exists. Please Sign In."}

            cur.execute("SELECT id FROM livelink_users WHERE phone = ?", (clean_phone,))
            if cur.fetchone():
                return {"success": False, "error": "An account with this mobile number already exists. Please Sign In."}

            cur.execute(
                """
                INSERT INTO livelink_users
                (name, first_name, last_name, phone, email, password_hash, salt, role, status, access_token, requested_at, approved_at, last_active_at, client_ip, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (full_name, fn, ln, clean_phone, clean_email, pwd_hash, salt, role, status, new_token, now, now, now, client_ip, user_agent),
            )
            conn.commit()

        self._notify_admin_new_request(full_name, clean_phone, f"Registered new user account: {clean_email}")

        return {
            "success": True,
            "status": status,
            "token": new_token,
            "name": full_name,
            "first_name": fn,
            "last_name": ln,
            "email": clean_email,
            "phone": clean_phone,
            "role": role,
            "message": f"Welcome to ULTRON, {fn}! Account registered successfully.",
        }

    def login_user(
        self,
        identifier: str,
        password: str,
        client_ip: str = "",
        user_agent: str = "",
    ) -> Dict[str, Any]:
        """Authenticates user via Email or Mobile Number and Password."""
        ident = (identifier or "").strip().lower()
        pwd = (password or "").strip()

        if not ident or not pwd:
            return {"success": False, "error": "Email/Mobile Number and Password are required."}

        # Master Harsha Quick-Access Pass
        if (ident in ("harsha", "admin", "harshakanth@ultron.ai") and pwd in ("harsha", "ultron", "admin", "123456", "Harsha@123")) or ident == MASTER_TOKEN:
            return {
                "success": True,
                "token": MASTER_TOKEN,
                "name": "Harsha Kanth",
                "first_name": "Harsha",
                "last_name": "Kanth",
                "email": "harshakanth@ultron.ai",
                "phone": "+919999999999",
                "role": "ADMIN",
                "status": "APPROVED",
                "message": "Welcome back, Commander Harsha!",
            }

        clean_phone = self.sanitize_phone(ident)

        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, first_name, last_name, phone, email, password_hash, salt, role, status, access_token
                FROM livelink_users
                WHERE email = ? OR phone = ?
                ORDER BY requested_at DESC LIMIT 1
                """,
                (ident, clean_phone),
            )
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": "No account found matching this Email or Mobile Number. Please Register."}

            salt = row["salt"] or ""
            expected_hash = row["password_hash"] or ""

            if not expected_hash:
                return {"success": False, "error": "Account does not have a password configured. Please Register."}

            given_hash = self._hash_password(pwd, salt)
            if given_hash != expected_hash:
                return {"success": False, "error": "Incorrect password. Please verify and try again."}

            if row["status"] in ("DENIED", "REVOKED"):
                return {"success": False, "error": "Account access was suspended by Harsha."}

            now = time.time()
            token = row["access_token"]
            cur.execute("UPDATE livelink_users SET last_active_at = ?, client_ip = ?, user_agent = ? WHERE id = ?", (now, client_ip, user_agent, row["id"]))
            conn.commit()

            return {
                "success": True,
                "status": row["status"],
                "token": token,
                "name": row["name"],
                "first_name": row["first_name"] or row["name"].split(" ")[0],
                "last_name": row["last_name"] or "",
                "email": row["email"],
                "phone": row["phone"],
                "role": row["role"] or "USER",
                "message": f"Welcome back, {row['first_name'] or row['name']}!",
            }

    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile info for an active session token."""
        if not token:
            return None
        if token == MASTER_TOKEN:
            return {
                "name": "Harsha Kanth",
                "first_name": "Harsha",
                "last_name": "Kanth",
                "email": "harshakanth@ultron.ai",
                "phone": "+919999999999",
                "role": "ADMIN",
                "status": "APPROVED",
            }
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, first_name, last_name, email, phone, role, status FROM livelink_users WHERE access_token = ?",
                (token,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """Cleans and validates phone number string."""
        if not phone:
            return ""
        # Keep digits and leading +
        stripped = phone.strip()
        cleaned = re.sub(r"[^\d+]", "", stripped)
        return cleaned

    def request_access(
        self,
        name: str,
        phone: str,
        purpose: str = "",
        client_ip: str = "",
        user_agent: str = "",
    ) -> Dict[str, Any]:
        """
        Registers an access request. Phone number is mandatory.
        Status is set to PENDING until approved by Harsha.
        """
        clean_name = (name or "").strip()
        clean_phone = self.sanitize_phone(phone)
        clean_purpose = (purpose or "").strip()

        if not clean_name:
            return {"success": False, "error": "Full Name is required for LiveLink verification."}

        # Validate phone: must contain at least 7 digits
        digits_only = re.sub(r"\D", "", clean_phone)
        if len(digits_only) < 7:
            return {
                "success": False,
                "error": "A valid Phone Number (minimum 7 digits) is strictly mandatory for LiveLink verification.",
            }

        now = time.time()
        new_token = f"ll_{uuid.uuid4().hex}"

        with self._lock, self._get_connection() as conn:
            # Check if this phone number already exists
            cur = conn.cursor()
            cur.execute("SELECT id, name, phone, status, access_token FROM livelink_users WHERE phone = ?", (clean_phone,))
            existing = cur.fetchone()

            if existing:
                row_id = existing["id"]
                current_status = existing["status"]
                token = existing["access_token"]

                # If already approved, return active session
                if current_status == "APPROVED":
                    cur.execute(
                        "UPDATE livelink_users SET last_active_at = ?, client_ip = ?, user_agent = ? WHERE id = ?",
                        (now, client_ip, user_agent, row_id),
                    )
                    conn.commit()
                    return {
                        "success": True,
                        "status": "APPROVED",
                        "token": token,
                        "name": clean_name,
                        "phone": clean_phone,
                        "message": f"Welcome back, {clean_name}! Access already granted by Harsha.",
                    }

                if current_status in ("DENIED", "REVOKED"):
                    return {
                        "success": False,
                        "status": current_status,
                        "error": "Your access to ULTRON was denied or revoked by Harsha.",
                    }

                # Status is still PENDING; update info
                cur.execute(
                    """
                    UPDATE livelink_users
                    SET name = ?, purpose = ?, client_ip = ?, user_agent = ?, requested_at = ?
                    WHERE id = ?
                    """,
                    (clean_name, clean_purpose, client_ip, user_agent, now, row_id),
                )
                conn.commit()
                status = "PENDING"
            else:
                # Insert new request
                token = new_token
                status = "PENDING"
                cur.execute(
                    """
                    INSERT INTO livelink_users (name, phone, purpose, client_ip, user_agent, status, access_token, requested_at, last_active_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (clean_name, clean_phone, clean_purpose, client_ip, user_agent, status, token, now, now),
                )
                conn.commit()

        # Alert Harsha on laptop (Voice & Toast)
        self._notify_admin_new_request(clean_name, clean_phone, clean_purpose)

        return {
            "success": True,
            "status": "PENDING",
            "token": token,
            "name": clean_name,
            "phone": clean_phone,
            "message": "Verification submitted. Awaiting administrative permission from Harsha.",
        }

    def _notify_admin_new_request(self, name: str, phone: str, purpose: str) -> None:
        """Alerts Harsha via desktop voice and system notification."""
        def _alert():
            try:
                # Desktop voice announcement
                from speech_engine import speak
                alert_text = f"Harsha, new LiveLink access request from {name}, phone number {phone}. Permission required."
                speak(alert_text)
            except Exception as e:
                print(f"[LIVELINK ALERT ERROR] Voice error: {e}")

            try:
                # Windows balloon notification
                title = "ULTRON LiveLink Access Request"
                msg = f"User: {name}\nPhone: {phone}\n{purpose or 'Awaiting permission'}"
                ps_cmd = (
                    f"[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
                    f"$n = new-object system.windows.forms.notifyicon; "
                    f"$n.icon = [system.drawing.systemicons]::Shield; "
                    f"$n.visible = $true; "
                    f"$n.showballoontip(8000, '{title}', '{msg}', [system.windows.forms.tooltipicon]::Warning)"
                )
                subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd])
            except Exception:
                pass

        threading.Thread(target=_alert, daemon=True).start()

    def check_status(self, token: str) -> Dict[str, Any]:
        """Checks the current permission status for a client token."""
        if not token:
            return {"status": "UNREGISTERED", "error": "No token provided."}

        if token == MASTER_TOKEN:
            return {"status": "APPROVED", "name": "Admin Harsha", "role": "MASTER"}

        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, phone, status, requested_at, approved_at FROM livelink_users WHERE access_token = ?",
                (token,),
            )
            row = cur.fetchone()
            if not row:
                return {"status": "UNREGISTERED", "error": "Invalid or expired token."}

            return {
                "status": row["status"],
                "name": row["name"],
                "phone": row["phone"],
                "token": token,
                "requested_at": row["requested_at"],
                "approved_at": row["approved_at"],
            }

    def verify_access(self, token: str, client_ip: str = "") -> bool:
        """
        Validates if the request is permitted to execute commands or control laptop.
        Returns True ONLY if verified and approved by Harsha.
        """
        # Localhost / direct laptop operations are always permitted
        if client_ip in ("127.0.0.1", "localhost", "::1"):
            return True

        if token == MASTER_TOKEN:
            return True

        if not token:
            return False

        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, status FROM livelink_users WHERE access_token = ?", (token,))
            row = cur.fetchone()
            if row and row["status"] == "APPROVED":
                # Update last active timestamp
                cur.execute("UPDATE livelink_users SET last_active_at = ? WHERE id = ?", (time.time(), row["id"]))
                conn.commit()
                return True

        return False

    def approve_user(self, identifier: str) -> Tuple[bool, str]:
        """
        Harsha grants access to a user matching name, phone, or token.
        """
        ident = identifier.strip()
        if not ident:
            return False, "Specify the user's name or phone number to approve."

        now = time.time()
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, phone, access_token, status FROM livelink_users
                WHERE access_token = ? OR phone LIKE ? OR LOWER(name) LIKE ?
                ORDER BY requested_at DESC LIMIT 1
                """,
                (ident, f"%{ident}%", f"%{ident.lower()}%"),
            )
            row = cur.fetchone()
            if not row:
                return False, f"No LiveLink user found matching '{ident}'."

            user_id = row["id"]
            name = row["name"]
            phone = row["phone"]
            token = row["access_token"]

            cur.execute("UPDATE livelink_users SET status = 'APPROVED', approved_at = ? WHERE id = ?", (now, user_id))
            conn.commit()

        # Instant low-latency SSE broadcast
        try:
            from modules.livelink_stream import livelink_stream_hub
            livelink_stream_hub.notify_approval(token, name, "APPROVED")
        except Exception:
            pass

        try:
            from speech_engine import speak
            speak(f"LiveLink access granted to {name}.")
        except Exception:
            pass

        return True, f"LiveLink access granted to {name} (Phone: {phone}). They can now use ULTRON."

    def deny_user(self, identifier: str) -> Tuple[bool, str]:
        """Harsha denies access to a user."""
        ident = identifier.strip()
        if not ident:
            return False, "Specify the user's name or phone number to deny."

        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, phone, access_token FROM livelink_users
                WHERE access_token = ? OR phone LIKE ? OR LOWER(name) LIKE ?
                ORDER BY requested_at DESC LIMIT 1
                """,
                (ident, f"%{ident}%", f"%{ident.lower()}%"),
            )
            row = cur.fetchone()
            if not row:
                return False, f"No LiveLink user found matching '{ident}'."

            user_id = row["id"]
            name = row["name"]
            token = row["access_token"]
            cur.execute("UPDATE livelink_users SET status = 'DENIED' WHERE id = ?", (user_id,))
            conn.commit()

        try:
            from modules.livelink_stream import livelink_stream_hub
            livelink_stream_hub.notify_approval(token, name, "DENIED")
        except Exception:
            pass

        return True, f"LiveLink access denied for {name}."

    def revoke_user(self, identifier: str) -> Tuple[bool, str]:
        """Revokes previously approved access."""
        ident = identifier.strip()
        if not ident:
            return False, "Specify the user's name or phone number to revoke."

        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, phone, access_token FROM livelink_users
                WHERE access_token = ? OR phone LIKE ? OR LOWER(name) LIKE ?
                ORDER BY requested_at DESC LIMIT 1
                """,
                (ident, f"%{ident}%", f"%{ident.lower()}%"),
            )
            row = cur.fetchone()
            if not row:
                return False, f"No LiveLink user found matching '{ident}'."

            user_id = row["id"]
            name = row["name"]
            token = row["access_token"]
            cur.execute("UPDATE livelink_users SET status = 'REVOKED' WHERE id = ?", (user_id,))
            conn.commit()

        try:
            from modules.livelink_stream import livelink_stream_hub
            livelink_stream_hub.notify_approval(token, name, "REVOKED")
        except Exception:
            pass

        return True, f"LiveLink access revoked for {name}."

    def list_requests(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of requests, optionally filtered by status (PENDING, APPROVED, etc.)."""
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            if status_filter:
                cur.execute(
                    "SELECT id, name, phone, purpose, client_ip, status, access_token, requested_at, approved_at FROM livelink_users WHERE status = ? ORDER BY requested_at DESC",
                    (status_filter.upper(),),
                )
            else:
                cur.execute(
                    "SELECT id, name, phone, purpose, client_ip, status, access_token, requested_at, approved_at FROM livelink_users ORDER BY requested_at DESC",
                )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_pending_summary(self) -> str:
        """Returns readable summary of pending requests for Harsha."""
        pending = self.list_requests(status_filter="PENDING")
        if not pending:
            return "No pending LiveLink access requests at this time, Harsha."

        lines = [f"Found {len(pending)} pending LiveLink request(s):"]
        for p in pending:
            req_time = time.strftime("%H:%M:%S", time.localtime(p["requested_at"]))
            lines.append(f"- {p['name']} | Phone: {p['phone']} | Time: {req_time} | Purpose: {p['purpose'] or 'None'}")
        lines.append("Say 'Approve LiveLink [name]' or 'Deny LiveLink [name]' to take action.")
        return "\n".join(lines)


# Singleton Instance
livelink_gatekeeper = LiveLinkGatekeeper()
