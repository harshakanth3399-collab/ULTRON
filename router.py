"""
router.py - ULTRON Command Router

Routes English transcript to the appropriate handler:
  1. Memory commands
  2. System automation
  3. Daily life (WhatsApp, phone, banking, files, etc.) -- NEW
  4. Web commands (YouTube, Google, search)
  5. AI (Ollama local model with fallback)
"""
from __future__ import annotations

import re
import time

from corrector import correct
from planner import plan
from intent import detect_intent
from commands import execute
from ai import ask_ai
from memory import remember, recall
from modules.memory.profile_manager import get_profile_manager

AWAKE = True
LAST_ACTIVITY = time.time()


def _extract(text: str, *remove_words: str) -> str:
    """Remove specified words from text and return stripped remainder."""
    result = text
    for w in remove_words:
        result = result.replace(w, "")
    return result.strip()


def process(command: str) -> tuple:
    global AWAKE, LAST_ACTIVITY

    raw = command.lower().strip()
    if not raw:
        return True, None

    LAST_ACTIVITY = time.time()

    # ── Security ────────────────────────────────────────────────────────────────
    if raw == "intruder_detected":
        return True, "Get lost! This is Harsha's laptop. You are NOT authorised."

    # ── Memory commands ─────────────────────────────────────────────────────────
    if raw.startswith("remember that"):
        note = raw.replace("remember that", "").strip()
        remember("note", note)
        return True, f"Stored in memory, bro: '{note}'"

    if "what do you remember" in raw or "show my notes" in raw:
        pm = get_profile_manager()
        notes = pm.get_notes()
        if notes:
            return True, "Here's what I remember for you, Harsha:\n- " + "\n- ".join(notes)
        return True, "Your memory is clean right now, Harsha."

    # ── System automation ───────────────────────────────────────────────────────
    if any(k in raw for k in ["volume", "battery", "cpu", "system status", "brightness"]):
        from core.system_automation import execute_system_command
        res = execute_system_command(raw)
        if res:
            return True, res

    # ── Screenshot ───────────────────────────────────────────────────────────────
    if "screenshot" in raw or "take a screen" in raw:
        from commands_daily import screenshot
        return True, screenshot()

    # ── WhatsApp ─────────────────────────────────────────────────────────────────
    if "whatsapp" in raw or "message" in raw or "text" in raw or "msg" in raw:
        from commands_daily import whatsapp_call, whatsapp_message, whatsapp_im_busy

        # "call [name] on whatsapp" / "whatsapp call [name]"
        if "call" in raw:
            name = re.sub(r"(call|on|whatsapp|via)", "", raw).strip()
            return True, whatsapp_call(name)

        # "i'm busy" / "tell [name] i'm busy"
        if "busy" in raw or "i'm busy" in raw or "im busy" in raw:
            name_match = re.search(r"(?:tell|message|text|msg)\s+(\w+)", raw)
            name = name_match.group(1) if name_match else ""
            return True, whatsapp_im_busy(name)

        # "message [name] [text]" / "send message to [name]"
        name_match = re.search(r"(?:message|text|msg|send\s+to)\s+(\w+)\s*(.*)", raw)
        if name_match:
            name = name_match.group(1)
            msg  = name_match.group(2).strip()
            return True, whatsapp_message(name, msg)

        from commands_daily import whatsapp_message
        return True, whatsapp_message("", "")

    # ── Phone calls ──────────────────────────────────────────────────────────────
    if raw.startswith("open phone link") or raw.startswith("launch phone link"):
        from commands_daily import phone_call
        return True, phone_call("")



    # ── Banking & Payments ────────────────────────────────────────────────────────
    if any(k in raw for k in ["sbi", "hdfc", "icici", "kotak", "axis", "paytm",
                                "gpay", "google pay", "phonepe", "phone pe",
                                "cred", "upi", "neft", "bhim", "amazon pay", "banking"]):
        from commands_daily import open_banking
        return True, open_banking(raw)

    # ── File / Folder opener ───────────────────────────────────────────────────
    if any(k in raw for k in ["open my", "open downloads", "open documents",
                               "open desktop", "open pictures", "open photos",
                               "open videos", "open music", "open folder",
                               "file explorer", "my files", "my folders"]):
        from commands_daily import open_folder
        return True, open_folder(raw)

    # ── Weather ────────────────────────────────────────────────────────────────
    if "weather" in raw or "temperature" in raw or "rain today" in raw or "forecast" in raw:
        from commands_daily import open_weather
        loc = re.sub(r"(weather|temperature|forecast|today|in|for)", "", raw).strip()
        return True, open_weather(loc)

    # ── Alarm / Timer ─────────────────────────────────────────────────────────
    if "set alarm" in raw or "wake me" in raw:
        from commands_daily import set_alarm
        t = re.sub(r"(set\s+alarm|wake\s+me\s+(up\s+)?at)", "", raw).strip()
        return True, set_alarm(t)

    if "set timer" in raw or "start timer" in raw or "timer for" in raw:
        from commands_daily import set_timer
        t = re.sub(r"(set|start|timer|for)", "", raw).strip()
        return True, set_timer(t)

    # ── Food / Delivery ────────────────────────────────────────────────────────
    if "swiggy" in raw:
        from commands_daily import open_swiggy
        return True, open_swiggy()

    if "zomato" in raw:
        from commands_daily import open_zomato
        return True, open_zomato()

    # ── Cab ────────────────────────────────────────────────────────────────────
    if "ola" in raw and "cab" in raw or "book ola" in raw:
        from commands_daily import open_ola
        return True, open_ola()

    if "uber" in raw:
        from commands_daily import open_uber
        return True, open_uber()

    # ── Travel ────────────────────────────────────────────────────────────────
    if "irctc" in raw or "train ticket" in raw or "book train" in raw:
        from commands_daily import open_irctc
        return True, open_irctc()

    # ── Maps ──────────────────────────────────────────────────────────────────
    if "maps" in raw or "navigate to" in raw or "directions to" in raw or "how to reach" in raw:
        from commands_daily import open_maps
        dest = re.sub(r"(maps|navigate\s+to|directions\s+to|how\s+to\s+reach|open)", "", raw).strip()
        return True, open_maps(dest)

    # ── Shopping ──────────────────────────────────────────────────────────────
    if "amazon" in raw:
        from commands_daily import open_amazon
        return True, open_amazon()

    if "flipkart" in raw:
        from commands_daily import open_flipkart
        return True, open_flipkart()

    # ── Streaming ─────────────────────────────────────────────────────────────
    if "hotstar" in raw or "disney" in raw:
        from commands_daily import open_hotstar
        return True, open_hotstar()

    if "netflix" in raw:
        from commands_daily import open_netflix
        return True, open_netflix()

    # ── Social & Instagram ───────────────────────────────────────────────────
    if any(k in raw for k in ["content preference", "content preferences", "reset preference", "reset preferences", "reset my content"]):
        from commands_daily import reset_instagram_preferences
        return True, reset_instagram_preferences()

    if "instagram" in raw and any(k in raw for k in ["reset", "preference", "content", "feed"]):
        from commands_daily import reset_instagram_preferences
        return True, reset_instagram_preferences()

    if "instagram" in raw:
        from commands_daily import open_instagram
        return True, open_instagram()



    if "twitter" in raw or "x.com" in raw:
        from commands_daily import open_twitter
        return True, open_twitter()

    if "linkedin" in raw:
        from commands_daily import open_linkedin
        return True, open_linkedin()

    if "gmail" in raw or "email" in raw or "mail" in raw:
        from commands_daily import open_email
        return True, open_email()

    # ── Training / Updates ────────────────────────────────────────────────────
    if "train model" in raw or "train ultron" in raw:
        from modules.memory.trainer import train_local_model
        success, msg = train_local_model()
        if success:
            return True, "Local model training done, Harsha! Running on custom weights now."
        return True, f"Training note: {msg}"

    if "update ultron" in raw or "check update" in raw or "upgrade yourself" in raw or "update yourself" in raw:
        from modules.updater import check_and_apply_safe_updates
        success, msg = check_and_apply_safe_updates()
        return True, msg

    # ── Phone & Wireless ADB Controls ──────────────────────────────────────────
    if any(k in raw for k in ["connect adb", "adb connect", "wireless adb", "wireless debugging"]):
        from modules.adb_bridge import adb_bridge
        ip_match = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", raw)
        phone_ip = ip_match.group(0) if ip_match else None
        success, msg = adb_bridge.connect_phone(phone_ip)
        return True, msg

    if any(k in raw for k in ["phone battery", "battery of phone", "check phone battery"]):
        from modules.adb_bridge import adb_bridge
        return True, adb_bridge.get_battery_level()

    if "phone screenshot" in raw or "screenshot of phone" in raw:
        from modules.adb_bridge import adb_bridge
        return True, adb_bridge.take_screenshot()

    if "connect phone" in raw or "mobile link" in raw or "phone link" in raw:
        return True, "Phone portal is ready, Harsha! Your connection link is displayed on screen."



    # ── Web search ──────────────────────────────────────────────────────────────────
    if raw.startswith(("search the web for", "search web for", "search for")):
        from modules.internet import search_web_live
        query = re.sub(r"^(search the web for|search web for|search for)", "", raw).strip()
        web_info = search_web_live(query)
        if web_info:
            ai_summary = ask_ai(
                f"Answer Harsha directly in 1-2 short sentences based on these "
                f"live web results for '{query}':\n{web_info}"
            )
            return True, ai_summary
        return True, f"Searched for '{query}' but found no results."

    # ── YouTube / Play ─────────────────────────────────────────────────────────────
    if "youtube" in raw or raw.startswith("play "):
        from commands import execute
        execute(raw)
        # Extract what we're playing for spoken reply
        search = re.sub(r"(play|youtube|open|on|and|for me|please)", "", raw).strip()
        if search:
            return True, f"Playing {search} on YouTube for you, bro!"
        return True, "Opening YouTube for you, Harsha!"

    # ── Standard commands: YouTube / Google / Apps / AI ───────────────────────
    corrected = correct(raw)
    tasks     = plan(corrected)
    replies   = []

    for task in tasks:
        intent = detect_intent(task)

        if intent == "EXIT":
            return False, "Always here for you, Harsha. Catch you later, bro."

        if intent in ("OPEN_APP", "GOOGLE", "YOUTUBE", "PLAY_MUSIC"):
            executed = execute(task)
            if executed:
                replies.append("On it, Harsha.")
            continue

        # AI fallback
        ai_response = ask_ai(task)
        if ai_response:
            replies.append(ai_response)

    if replies:
        return True, " ".join(replies)

    return True, "I'm right here, Harsha. Ask me anything."