"""
modules/voice_messenger.py - ULTRON Hands-Free WhatsApp & Email Voice Dispatcher

Enables natural voice-driven messaging. Automatically structures text, formats
URLs/protocols, and dispatches messages to WhatsApp (Desktop/Web) and Email.
"""

from __future__ import annotations

import os
import re
import urllib.parse
import webbrowser
from typing import Optional, Tuple


def send_whatsapp_message(target: str, message: str) -> Tuple[bool, str]:
    """
    Dispatches a WhatsApp message via WhatsApp Desktop protocol or WhatsApp Web.
    """
    if not message:
        return False, "Please state the message you would like to send on WhatsApp."

    clean_target = target.strip() if target else ""
    encoded_text = urllib.parse.quote(message)

    # If target is a phone number (digits)
    phone_digits = re.sub(r"[^\d+]", "", clean_target)

    if phone_digits and len(phone_digits) >= 10:
        url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={encoded_text}"
        app_proto = f"whatsapp://send?phone={phone_digits}&text={encoded_text}"
    else:
        # Generic message or recipient name to search
        url = f"https://web.whatsapp.com/send?text={encoded_text}"
        app_proto = f"whatsapp://send?text={encoded_text}"

    # Try launching protocol first, fallback to browser
    try:
        os.startfile(app_proto)
        target_disp = f"to {clean_target}" if clean_target else ""
        return True, f"Opening WhatsApp {target_disp} with your message: '{message}'."
    except Exception:
        webbrowser.open(url)
        target_disp = f"to {clean_target}" if clean_target else ""
        return True, f"Opened WhatsApp Web {target_disp} with your message: '{message}'."


def draft_email(recipient: str, subject: str, body: str) -> Tuple[bool, str]:
    """
    Drafts an email using the system default mail client or mailto protocol.
    """
    if not body:
        return False, "Please provide the content of the email."

    clean_recip = recipient.strip() if recipient else ""
    clean_subj = subject.strip() if subject else "Message from Harsha via ULTRON"

    params = {
        "subject": clean_subj,
        "body": body
    }
    query_str = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    mailto_url = f"mailto:{clean_recip}?{query_str}"

    try:
        webbrowser.open(mailto_url)
        to_disp = f"to {clean_recip}" if clean_recip else ""
        return True, f"Drafted email {to_disp} with subject '{clean_subj}'."
    except Exception as e:
        return False, f"Could not create email draft: {e}"


def parse_and_dispatch_messenger(command: str) -> Tuple[bool, str]:
    """
    Parses natural language messenger commands:
    'send whatsapp message to mom saying i will be late'
    'send whatsapp to 9876543210 saying hello'
    'draft email to john saying please find the attachment'
    """
    raw = command.strip()

    # WhatsApp patterns
    m_wa = re.search(r"send\s+(?:a\s+)?whatsapp(?:\s+message)?(?:\s+to\s+([a-zA-Z0-9_\+\s]+?))?\s+(?:saying|that|with text)\s+(.*)$", raw, re.IGNORECASE)
    if m_wa:
        target = m_wa.group(1) or ""
        msg = m_wa.group(2).strip()
        return send_whatsapp_message(target, msg)

    m_wa_quick = re.search(r"send\s+whatsapp\s+to\s+([a-zA-Z0-9_\+\s]+?)\s*:\s*(.*)$", raw, re.IGNORECASE)
    if m_wa_quick:
        target = m_wa_quick.group(1).strip()
        msg = m_wa_quick.group(2).strip()
        return send_whatsapp_message(target, msg)

    # Email patterns
    m_email = re.search(r"(?:draft|send)\s+(?:an?\s+)?email(?:\s+to\s+([a-zA-Z0-9_\.\@\s]+?))?\s+(?:saying|about|with text)\s+(.*)$", raw, re.IGNORECASE)
    if m_email:
        recip = m_email.group(1) or ""
        body = m_email.group(2).strip()
        return draft_email(recip, "Voice Message from Harsha", body)

    return False, "Could not identify messenger parameters."
