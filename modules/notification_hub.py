"""
modules/notification_hub.py - ULTRON Unified Communication & Notification Hub
Always connected to Harsha:
  1. Phone Link & Windows Notification Database (wpndatabase.db) Reader:
     - Real-time WhatsApp messages (Phone & Desktop)
     - Incoming SMS & Messages
     - Phone Calls & Battery alerts
     - App notifications (Instagram, YouTube, Mail, System)
  2. Wireless ADB Phone Notification Extraction (when Android is connected):
     - Active status bar notification dump & message parsing
  3. Comprehensive J.A.R.V.I.S. Briefing:
     - Emails, WhatsApp, Phone Status, Weather, System Health
"""
from __future__ import annotations

import datetime
import os
import re
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from modules.memory.profile_manager import get_profile_manager


def _get_wpn_db_path() -> Optional[str]:
    """Locates the Windows Push Notification SQLite database."""
    local_app_data = os.getenv("LOCALAPPDATA", "")
    if not local_app_data:
        return None
    db_path = os.path.join(local_app_data, "Microsoft", "Windows", "Notifications", "wpndatabase.db")
    return db_path if os.path.exists(db_path) else None


def _clean_text(s: str) -> str:
    """Removes non-standard unicode / high emoji characters that fail on Windows cp1252."""
    if not s:
        return ""
    # Strip emojis and unsupported symbols
    clean = re.sub(r"[\U00010000-\U0010ffff]", "", s)
    clean = clean.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return " ".join(clean.split()).strip()


def get_windows_notifications(limit: int = 40) -> List[Dict[str, Any]]:
    """
    Safely reads recent notifications from Windows Notification DB.
    Copies DB to temp directory to avoid database locking.
    """
    db_path = _get_wpn_db_path()
    if not db_path:
        return []

    temp_dir = os.getenv("TEMP", os.path.expanduser("~"))
    temp_db = os.path.join(temp_dir, "ultron_wpn_read.db")

    try:
        shutil.copy2(db_path, temp_db)
        for ext in ["-wal", "-shm"]:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                try:
                    shutil.copy2(wal_file, temp_db + ext)
                except Exception:
                    pass

        conn = sqlite3.connect(temp_db, timeout=2.0)
        cur = conn.cursor()
        query = """
        SELECT Notification.Id, Notification.ArrivalTime, Notification.Type,
               NotificationHandler.PrimaryId, Notification.Payload
        FROM Notification
        JOIN NotificationHandler ON Notification.HandlerId = NotificationHandler.RecordId
        WHERE Notification.Type IN ('toast', 'tile')
        ORDER BY Notification.ArrivalTime DESC
        LIMIT ?
        """
        cur.execute(query, (limit,))
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"[NOTIFICATION HUB NOTE] Windows DB read: {e}")
        return []

    notifications = []
    filetime_epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)

    for nid, arr_time, ntype, handler, payload in rows:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="ignore")

        # Convert Windows FileTime to UTC datetime
        try:
            notif_time = filetime_epoch + datetime.timedelta(microseconds=arr_time / 10)
        except Exception:
            notif_time = datetime.datetime.now(datetime.timezone.utc)

        texts = []
        try:
            root = ET.fromstring(payload)
            for t in root.iter("text"):
                if t.text and t.text.strip():
                    txt = _clean_text(t.text.strip())
                    if txt and txt not in texts:
                        texts.append(txt)
        except Exception:
            # Fallback simple regex extraction of text elements
            found = re.findall(r"<text[^>]*>(.*?)</text>", payload, re.DOTALL)
            texts = [_clean_text(f.strip()) for f in found if _clean_text(f.strip())]

        if not texts:
            continue

        h_lower = handler.lower()
        category = "system"
        app_name = handler

        if "whatsapp" in h_lower:
            category = "whatsapp"
            app_name = "WhatsApp"
        elif "messages" in h_lower or "sms" in h_lower:
            category = "sms"
            app_name = "Phone Messages"
        elif "calling" in h_lower or "call" in h_lower:
            category = "call"
            app_name = "Phone Call"
        elif "yourphone" in h_lower or "ms-phone" in payload:
            category = "phone"
            if "youtube" in h_lower:
                app_name = "YouTube (Phone)"
            elif "instagram" in h_lower:
                app_name = "Instagram (Phone)"
            elif "battery" in h_lower or "devicestatus" in h_lower:
                app_name = "Phone Battery"
            else:
                app_name = "Phone Alert"
        elif "mail" in h_lower or "outlook" in h_lower:
            category = "mail"
            app_name = "Mail"
        elif "defender" in h_lower or "security" in h_lower:
            category = "security"
            app_name = "Windows Security"

        notifications.append({
            "id": nid,
            "time": notif_time,
            "category": category,
            "app_name": app_name,
            "handler": handler,
            "texts": texts,
            "summary": " | ".join(texts)
        })

    return notifications


def get_adb_notifications() -> List[Dict[str, Any]]:
    """Extracts live notifications directly from connected Android smartphone via ADB."""
    try:
        from modules.adb_bridge import _get_adb_executable
        import subprocess

        adb_exe = _get_adb_executable()
        res = subprocess.run(
            [adb_exe, "shell", "dumpsys", "notification", "--noredact"],
            capture_output=True,
            text=True,
            timeout=5.0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode != 0 or not res.stdout:
            return []

        out = res.stdout
        notifs = []
        # Parse active notification records
        records = out.split("NotificationRecord(")
        for rec in records[1:15]:
            pkg_match = re.search(r"pkg=([a-zA-Z0-9._]+)", rec)
            pkg = pkg_match.group(1) if pkg_match else "Android"

            title_match = re.search(r"android\.title=String \((.*?)\)", rec)
            text_match = re.search(r"android\.text=String \((.*?)\)", rec)
            subtext_match = re.search(r"android\.subText=String \((.*?)\)", rec)

            title = title_match.group(1).strip() if title_match else ""
            body = text_match.group(1).strip() if text_match else ""
            subtext = subtext_match.group(1).strip() if subtext_match else ""

            if title or body:
                texts = [t for t in [title, body, subtext] if t]
                category = "whatsapp" if "whatsapp" in pkg.lower() else ("mail" if "gm" in pkg.lower() else "phone")
                notifs.append({
                    "pkg": pkg,
                    "app_name": "WhatsApp" if category == "whatsapp" else pkg,
                    "category": category,
                    "title": title,
                    "body": body,
                    "texts": texts,
                    "summary": f"{title}: {body}" if title and body else (title or body)
                })

        return notifs
    except Exception as e:
        print(f"[ADB NOTIFICATIONS NOTE] {e}")
        return []


def get_whatsapp_messages(limit: int = 5) -> str:
    """
    Fetches and summarizes recent WhatsApp messages from Phone Link and Desktop.
    Returns natural spoken summary for ULTRON voice.
    """
    pm = get_profile_manager()
    pref_address = pm.get_preferred_address() or "Harsha"

    # 1. Check live Windows / Phone Link notifications
    all_notifs = get_windows_notifications(limit=50)
    wa_notifs = [n for n in all_notifs if n["category"] == "whatsapp"]

    # 2. Check ADB live phone notifications if available
    adb_notifs = get_adb_notifications()
    wa_adb = [n for n in adb_notifs if n["category"] == "whatsapp"]

    messages = []
    seen = set()

    for item in wa_adb:
        s = item["summary"]
        if s and s not in seen:
            seen.add(s)
            messages.append(s)

    for item in wa_notifs:
        s = item["summary"]
        if s and s not in seen:
            seen.add(s)
            messages.append(s)

    if not messages:
        return f"You have no unread WhatsApp messages right now, {pref_address}. Everything is clear."

    items_to_read = messages[:limit]
    if len(items_to_read) == 1:
        return f"You have 1 new WhatsApp message, {pref_address}: {items_to_read[0]}."

    readout = []
    for idx, msg in enumerate(items_to_read, 1):
        readout.append(f"{idx}: {msg}")

    return f"You have {len(items_to_read)} recent WhatsApp messages, {pref_address}: " + ". ".join(readout) + "."


def get_all_notifications_summary(limit: int = 5) -> str:
    """Returns an intelligent summary of recent notifications from both phone and laptop."""
    pm = get_profile_manager()
    pref_address = pm.get_preferred_address() or "Harsha"

    notifs = get_windows_notifications(limit=40)
    if not notifs:
        return f"No active notifications on your phone or laptop right now, {pref_address}."

    # Filter out noisy background system badges
    filtered = []
    for n in notifs:
        summary_low = n["summary"].lower()
        if any(ign in summary_low for ign in ["virus removal comes with your", "mcafee monthly"]):
            continue
        filtered.append(n)

    if not filtered:
        return f"Your notification center is clear, {pref_address}."

    recent = filtered[:limit]
    readout = []
    for n in recent:
        app = n["app_name"]
        text = n["summary"]
        readout.append(f"From {app}: {text}")

    return f"Here are your latest notifications, {pref_address}: " + "; ".join(readout) + "."


def get_jarvis_briefing() -> str:
    """
    Generates a full proactive J.A.R.V.I.S. briefing:
    - Greeting with user name
    - Weather overview
    - Phone status & battery
    - Unread emails count & highlights
    - WhatsApp messages
    - Laptop system health
    """
    pm = get_profile_manager()
    pref_address = pm.get_preferred_address() or "Harsha"

    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = f"Good morning, {pref_address}!"
    elif hour < 17:
        greeting = f"Good afternoon, {pref_address}!"
    else:
        greeting = f"Good evening, {pref_address}!"

    briefing_parts = [greeting]

    # 1. Weather
    try:
        from modules.weather_service import get_live_weather
        _, w_text = get_live_weather()
        if w_text:
            briefing_parts.append(w_text)
    except Exception:
        pass

    # 2. Email status
    try:
        from modules.email_engine import get_inbox_summary
        e_summary = get_inbox_summary(max_count=3, brief_mode=True)
        if e_summary:
            briefing_parts.append(e_summary)
    except Exception:
        pass

    # 3. WhatsApp & Phone Messages
    try:
        all_notifs = get_windows_notifications(limit=25)
        wa = [n for n in all_notifs if n["category"] == "whatsapp"]
        if wa:
            briefing_parts.append(f"You have active WhatsApp alerts: {wa[0]['summary']}.")
        else:
            briefing_parts.append("Your WhatsApp messages are currently clear.")
    except Exception:
        pass

    # 4. Phone status & Battery
    try:
        from modules.adb_bridge import adb_bridge
        devs, _ = adb_bridge.get_connected_devices()
        if devs:
            bat = adb_bridge.get_battery_level()
            briefing_parts.append(f"Smartphone is connected wirelessly. {bat}")
        else:
            # Check Phone Link battery notification if available
            notifs = get_windows_notifications(limit=20)
            batt_notif = next((n for n in notifs if "battery" in n["summary"].lower() and "phone" in n["app_name"].lower()), None)
            if batt_notif:
                briefing_parts.append(f"Phone notice: {batt_notif['summary']}.")
    except Exception:
        pass

    # 5. Laptop System Telemetry
    try:
        from modules.system_control import get_battery_status, get_memory_status
        ram_pct, _, _ = get_memory_status()
        pct, plugged = get_battery_status()
        status_str = "plugged in" if plugged else "on battery"
        briefing_parts.append(f"Laptop memory is at {ram_pct}%, and battery is at {pct}% ({status_str}). All systems operational.")
    except Exception:
        briefing_parts.append("All primary systems operational.")

    return " ".join(briefing_parts)
