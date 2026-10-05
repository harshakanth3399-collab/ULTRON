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
        """Initializes the LiveLink SQLite access control table."""
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS livelink_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    purpose TEXT,
                    client_ip TEXT,
                    user_agent TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    access_token TEXT UNIQUE NOT NULL,
                    requested_at REAL NOT NULL,
                    approved_at REAL,
                    last_active_at REAL
                )
                """
            )
            # Create indexes for fast lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_token ON livelink_users(access_token)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_phone ON livelink_users(phone)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ll_status ON livelink_users(status)")
            conn.commit()

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
            # Match exact token, exact phone, or case-insensitive name match
            cur.execute(
                """
                SELECT id, name, phone, status FROM livelink_users
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

            cur.execute("UPDATE livelink_users SET status = 'APPROVED', approved_at = ? WHERE id = ?", (now, user_id))
            conn.commit()

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
                SELECT id, name, phone FROM livelink_users
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
            cur.execute("UPDATE livelink_users SET status = 'DENIED' WHERE id = ?", (user_id,))
            conn.commit()

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
                SELECT id, name, phone FROM livelink_users
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
            cur.execute("UPDATE livelink_users SET status = 'REVOKED' WHERE id = ?", (user_id,))
            conn.commit()

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
