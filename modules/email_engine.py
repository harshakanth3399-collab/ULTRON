"""
email_engine.py - ULTRON Advanced Gmail Assistant & Communication Engine
Features:
  1. Full Inbox Summaries (Sender, Subject, Unread Count).
  2. Read Latest Email with clean body text extraction.
  3. Job Selection / Interview Detection with instant voice alerts and AI drafts.
  4. Automatic AI reply generation and one-click voice sending.
  5. Windows Mail & Notification fallback when IMAP requires App Password.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
import smtplib
import time
from email.header import decode_header
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from ai import ask_ai
from speech_engine import speak
from modules.memory.profile_manager import get_profile_manager

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

_pending_reply: Optional[Dict[str, str]] = None
_last_fetched_email: Optional[Dict[str, str]] = None


def _load_env_file() -> None:
    """Safely loads .env file if environment variables are not yet populated."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() not in os.environ:
                            os.environ[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass


_load_env_file()


def _get_credentials() -> Tuple[str, str]:
    """Retrieves Gmail address and App Password from environment or profile."""
    _load_env_file()
    email_addr = os.getenv("GMAIL_USER", "").strip()
    app_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not email_addr or not app_pass:
        pm = get_profile_manager()
        email_addr = pm.data.get("profile", {}).get("email", email_addr)
        app_pass = pm.data.get("preferences", {}).get("gmail_app_password", app_pass)

    return email_addr, app_pass


def _decode_mime_words(raw_val: Any) -> str:
    """Decodes MIME encoded subject or header strings into clean UTF-8."""
    if not raw_val:
        return ""
    try:
        decoded_parts = decode_header(raw_val)
        out = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                out.append(part.decode(encoding or "utf-8", errors="ignore"))
            else:
                out.append(str(part))
        return " ".join(out).strip()
    except Exception:
        return str(raw_val)


def _clean_sender_name(sender: str) -> str:
    """Extracts human-friendly sender name from header string."""
    decoded = _decode_mime_words(sender)
    m = re.match(r"^\"?([^\"<]+)\"?\s*<.*>$", decoded)
    if m:
        name = m.group(1).strip()
        if name:
            return name
    # Fallback to email username
    if "@" in decoded:
        return decoded.split("@")[0].replace("<", "").strip()
    return decoded


def _extract_email_body(msg: Any) -> str:
    """Extracts plain text content from email message, stripping HTML tags."""
    body = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")
                        break
                elif ctype == "text/html" and not body and "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_text = payload.decode(errors="ignore")
                        # Strip basic html
                        body = re.sub(r"<[^>]+>", " ", html_text)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="ignore")
    except Exception:
        pass

    # Normalize whitespace
    return " ".join(body.split()).strip()


def get_inbox_summary(max_count: int = 5, brief_mode: bool = False) -> str:
    """
    Connects to Gmail, counts unread messages, summarizes top senders and subjects.
    Provides fallback to Windows Mail notifications if IMAP requires App Password.
    """
    global _last_fetched_email, _pending_reply
    pm = get_profile_manager()
    pref_address = pm.get_preferred_address() or "Harsha"

    email_addr, app_pass = _get_credentials()
    if not email_addr or not app_pass:
        return f"Gmail credentials are not configured yet, {pref_address}. Please set GMAIL_USER in .env."

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=7.0)
        mail.login(email_addr, app_pass)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            # Check total recent emails if no unread
            if brief_mode:
                mail.logout()
                return "Your Gmail inbox has no unread emails."
            mail.logout()
            return f"You have no unread emails in your Gmail inbox right now, {pref_address}. All messages are read."

        total_unread = len(email_ids)
        items_to_fetch = email_ids[-max_count:]
        summaries = []

        for e_id in reversed(items_to_fetch):
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = _decode_mime_words(msg.get("Subject", "(No Subject)"))
                    sender_raw = msg.get("From", "Unknown")
                    sender_clean = _clean_sender_name(sender_raw)
                    body_text = _extract_email_body(msg)

                    _last_fetched_email = {
                        "from": sender_clean,
                        "from_raw": sender_raw,
                        "subject": subject,
                        "body": body_text,
                        "date": msg.get("Date", "")
                    }

                    # Check for job selection
                    job_keywords = ["congratulations", "selected", "shortlisted", "job offer", "interview", "hiring", "offer letter"]
                    combined = f"{subject} {body_text}".lower()
                    if any(k in combined for k in job_keywords):
                        company_match = re.search(r"at\s+([A-Z][a-zA-Z0-9\s]{2,20})|from\s+([A-Z][a-zA-Z0-9\s]{2,20})", subject)
                        company = company_match.group(1) or company_match.group(2) if company_match else sender_clean
                        formal_reply = generate_formal_email_reply(subject, body_text, sender_raw)
                        _pending_reply = {
                            "to": sender_raw,
                            "subject": f"Re: {subject}",
                            "body": formal_reply,
                            "company": company
                        }
                        summaries.append(f"[JOB ALERT] from {company} regarding '{subject}'")
                    else:
                        summaries.append(f"from {sender_clean} regarding '{subject}'")

        mail.logout()

        if brief_mode:
            return f"You have {total_unread} unread emails. Latest is {summaries[0]}."

        if len(summaries) == 1:
            return f"You have 1 unread email, {pref_address}: {summaries[0]}. Say 'Read email' to hear it."

        bullet_points = ". ".join([f"{i+1}: {s}" for i, s in enumerate(summaries)])
        return f"You have {total_unread} unread emails, {pref_address}. The latest are: {bullet_points}. Say 'Read email' to hear the full message."

    except imaplib.IMAP4.error as e:
        err_msg = str(e)
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            # Fallback: check Windows Mail notifications
            from modules.notification_hub import get_windows_notifications
            notifs = get_windows_notifications(limit=20)
            mail_notifs = [n for n in notifs if n["category"] == "mail"]
            if mail_notifs:
                preview = mail_notifs[0]["summary"]
                return (
                    f"Notice for Gmail, {pref_address}: Google requires a 16-letter App Password for direct IMAP. "
                    f"However, your latest desktop email notification shows: {preview}."
                )
            return (
                f"Harsha, Gmail requires a 16-character Google App Password for direct IMAP access. "
                f"You can generate it under Google Account -> Security -> 2-Step Verification -> App Passwords. "
                f"I am actively monitoring all incoming email notifications from your Windows desktop in the meantime."
            )
        return f"Gmail access notice: {err_msg}"
    except Exception as e:
        print(f"[EMAIL ENGINE ERROR] {e}")
        return f"Could not sync Gmail inbox at this moment: {e}"


def read_latest_email() -> str:
    """Reads aloud the body and details of the most recent email."""
    global _last_fetched_email
    pm = get_profile_manager()
    pref_address = pm.get_preferred_address() or "Harsha"

    # If already cached from recent scan
    if _last_fetched_email and _last_fetched_email.get("body"):
        sender = _last_fetched_email["from"]
        subj = _last_fetched_email["subject"]
        body = _last_fetched_email["body"][:400]
        return f"Latest email from {sender}. Subject: {subj}. Content: {body}."

    # Otherwise fetch live
    email_addr, app_pass = _get_credentials()
    if not email_addr or not app_pass:
        return f"Gmail credentials not configured, {pref_address}."

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=7.0)
        mail.login(email_addr, app_pass)
        mail.select("inbox")

        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        if not email_ids:
            mail.logout()
            return f"Your inbox is empty, {pref_address}."

        latest_id = email_ids[-1]
        res, msg_data = mail.fetch(latest_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subj = _decode_mime_words(msg.get("Subject", "(No Subject)"))
                sender_clean = _clean_sender_name(msg.get("From", "Unknown"))
                body = _extract_email_body(msg)
                mail.logout()
                body_clean = body[:350] if body else "No text body found."
                return f"Latest email from {sender_clean}. Subject: {subj}. Content: {body_clean}."

        mail.logout()
    except imaplib.IMAP4.error as e:
        err_msg = str(e)
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            from modules.notification_hub import get_windows_notifications
            notifs = get_windows_notifications(limit=20)
            mail_notifs = [n for n in notifs if n["category"] == "mail"]
            if mail_notifs:
                preview = mail_notifs[0]["summary"]
                return f"Latest email from desktop notification: {preview}."
            return (
                f"Harsha, please generate a 16-letter Google App Password under Google Account Security settings "
                f"so I can read your full email bodies directly."
            )
        return f"Gmail access notice: {err_msg}"
    except Exception as e:
        return f"Could not read latest email: {e}"


def check_job_emails() -> str:
    """Monitors Gmail for job selection / offer emails, triggers voice announcements, and drafts AI replies."""
    return get_inbox_summary(max_count=5, brief_mode=False)


def generate_formal_email_reply(subject: str, email_body: str, sender: str) -> str:
    """Invokes LLM to generate a hyper-formal, polite professional reply."""
    prompt = (
        f"Generate a hyper-formal, highly professional, polite email response from Harsha "
        f"replying to a job selection/interview email. "
        f"Original Subject: {subject}\n"
        f"Sender: {sender}\n"
        f"Original Email Content:\n{email_body[:500]}\n\n"
        f"Keep the tone extremely formal, professional, grateful, and polite. Signed as 'Harsha'."
    )
    return ask_ai(prompt)


def send_pending_reply() -> str:
    """Sends the drafted formal reply email upon user voice approval."""
    global _pending_reply
    if not _pending_reply:
        return "No pending email draft to send, Sir."

    email_addr, app_pass = _get_credentials()
    if not email_addr or not app_pass:
        return "Gmail credentials missing, Sir."

    try:
        msg = MIMEText(_pending_reply["body"])
        msg["Subject"] = _pending_reply["subject"]
        msg["From"] = email_addr
        msg["To"] = _pending_reply["to"]

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10.0) as server:
            server.starttls()
            server.login(email_addr, app_pass)
            server.sendmail(email_addr, [_pending_reply["to"]], msg.as_string())

        company = _pending_reply.get("company", "the company")
        _pending_reply = None
        return f"Formal reply email successfully sent to {company}, Sir."
    except Exception as e:
        return f"Failed to send email: {e}"


def send_custom_email(to_addr: str, subject: str, message: str) -> str:
    """Sends a custom email to any recipient."""
    email_addr, app_pass = _get_credentials()
    if not email_addr or not app_pass:
        return "Gmail credentials missing in .env."

    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = email_addr
        msg["To"] = to_addr

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10.0) as server:
            server.starttls()
            server.login(email_addr, app_pass)
            server.sendmail(email_addr, [to_addr], msg.as_string())

        return f"Email successfully dispatched to {to_addr}."
    except Exception as e:
        return f"Failed to dispatch email: {e}"
