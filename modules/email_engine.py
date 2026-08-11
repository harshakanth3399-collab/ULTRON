"""
email_engine.py - ULTRON Gmail Assistant & Job Application Reply Engine
Monitors Gmail for job selection / offer emails, triggers voice announcements,
generates hyper-formal AI replies, and sends response upon user approval.
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
from typing import Dict, List, Optional, Tuple

from ai import ask_ai
from speech_engine import speak
from modules.memory.profile_manager import get_profile_manager

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

_pending_reply: Optional[Dict[str, str]] = None


def _get_credentials() -> Tuple[str, str]:
    """Retrieves Gmail address and App Password from environment or profile."""
    email_addr = os.getenv("GMAIL_USER", "").strip()
    app_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not email_addr or not app_pass:
        pm = get_profile_manager()
        email_addr = pm.data.get("profile", {}).get("email", email_addr)
        app_pass = pm.data.get("preferences", {}).get("gmail_app_password", app_pass)

    return email_addr, app_pass


def check_job_emails() -> str:
    """
    Connects to Gmail, scans unread emails for job selection/offer keywords,
    announces selection out loud, and drafts a formal AI reply.
    """
    global _pending_reply
    email_addr, app_pass = _get_credentials()

    if not email_addr or not app_pass:
        return (
            "Gmail credentials not configured yet, Sir. "
            "Please set GMAIL_USER and GMAIL_APP_PASSWORD in your .env file."
        )

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(email_addr, app_pass)
        mail.select("inbox")

        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            mail.logout()
            return "No new unread emails in your Gmail inbox, Sir."

        job_keywords = ["congratulations", "selected", "shortlisted", "job offer", "interview", "hiring", "offer letter"]
        found_job = False
        summary_lines = []

        for e_id in reversed(email_ids[-5:]):
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")

                    sender = msg.get("From", "")
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    combined_text = f"{subject} {body}".lower()

                    # Check for job selection/congratulations
                    if any(k in combined_text for k in job_keywords):
                        found_job = True

                        # Extract company name
                        company_match = re.search(r"at\s+([A-Z][a-zA-Z0-9\s]{2,20})|from\s+([A-Z][a-zA-Z0-9\s]{2,20})", subject)
                        company = company_match.group(1) or company_match.group(2) if company_match else "a top company"

                        # Voice announcement
                        announcement = f"Congratulations Harsha! You have been selected by {company}!"
                        print(f"[JOB ANNOUNCEMENT] {announcement}")
                        speak(announcement)

                        # Generate formal AI draft
                        formal_reply = generate_formal_email_reply(subject, body, sender)
                        _pending_reply = {
                            "to": sender,
                            "subject": f"Re: {subject}",
                            "body": formal_reply,
                            "company": company
                        }

                        mail.logout()
                        return f"Congratulations Harsha! You are selected by {company}! I have prepared a formal AI reply. Say 'Send reply' to email them."

        mail.logout()
        return f"Checked unread emails, Sir. {len(email_ids)} new emails, no job selection alerts."

    except Exception as e:
        print(f"[EMAIL ENGINE ERROR] {e}")
        return f"Gmail check note: {e}. Please verify GMAIL_USER and GMAIL_APP_PASSWORD in .env."


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

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(email_addr, app_pass)
            server.sendmail(email_addr, [_pending_reply["to"]], msg.as_string())

        company = _pending_reply.get("company", "the company")
        _pending_reply = None
        return f"Formal reply email successfully sent to {company}, Sir."
    except Exception as e:
        return f"Failed to send email: {e}"
