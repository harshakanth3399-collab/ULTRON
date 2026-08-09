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

    # ── High Priority Phone Target Actions ────────────────────────────────────
    if any(k in raw for k in ["in my phone", "on my phone", "on phone", "in phone", "in my mobile", "on my mobile", "in mobile", "on mobile"]):
        from modules.adb_bridge import adb_bridge

        raw_phone = raw.replace("what's up", "whatsapp").replace("whats up", "whatsapp").replace("whatup", "whatsapp")

        app_map = {
            "whatsapp": "whatsapp",
            "youtube": "youtube",
            "instagram": "instagram",
            "chrome": "chrome",
            "spotify": "spotify",
            "camera": "camera",
            "settings": "settings",
            "gallery": "gallery",
            "photos": "photos",
            "maps": "maps",
        }
        for kw, app_name in app_map.items():
            if kw in raw_phone:
                return True, adb_bridge.open_app(app_name)
        return True, "Triggered action on your smartphone, Harsha!"

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

    # ── VS Code & GitHub ──────────────────────────────────────────────────────
    if any(k in raw for k in ["vs code", "vscode", "visual studio code", "open code"]):
        from commands import execute
        execute("code")
        return True, "Opening VS Code for you, Harsha!"

    if "github" in raw:
        from commands import execute
        execute("github")
        return True, "Opening GitHub for you, Harsha!"

    # ── WhatsApp (Desktop App & Messaging) ────────────────────────────────────

    raw_wa = raw.replace("what's up", "whatsapp").replace("whats up", "whatsapp").replace("whatup", "whatsapp")

    if "whatsapp" in raw_wa or "message" in raw_wa or "text" in raw_wa or "msg" in raw_wa:
        from commands_daily import whatsapp_call, whatsapp_message, whatsapp_im_busy, open_whatsapp

        if any(k in raw_wa for k in ["mom", "mum", "mother", "dad", "father", "bro", "hi", "high", "hello", "send"]):
            contact_target = "mum"
            for c in ["mom", "mum", "mother", "dad", "father", "bro"]:
                if c in raw_wa:
                    contact_target = c
                    break

            msg = "Hi" if any(k in raw_wa for k in ["hi", "high", "hey", "hello"]) else ""
            return True, whatsapp_message(contact_target, msg)

        return True, open_whatsapp()



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
    # Normalize phonetic Whisper mishearings of ADB ("a, d, b", "a-d-b", "a, b, b", "a, d, d", "a d b") -> "adb"
    raw_adb_norm = re.sub(r"a[\s,\.-]*[db][\s,\.-]*[db]", "adb", raw, flags=re.IGNORECASE)


    if "adb" in raw_adb_norm or "wireless debugging" in raw_adb_norm:
        from modules.adb_bridge import adb_bridge
        ip_match = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", raw)
        phone_ip = ip_match.group(0) if ip_match else None
        success, msg = adb_bridge.connect_phone(phone_ip)
        return True, msg


    if any(k in raw for k in ["phone connected", "is my phone", "is phone connected", "check phone status", "phone status"]):
        from modules.adb_bridge import adb_bridge
        devs, is_unauth = adb_bridge.get_connected_devices()
        if adb_bridge.connected_ip or devs:
            dev = adb_bridge.connected_ip or devs[0]
            return True, f"Yes Harsha! Your smartphone ({dev}) is actively connected to ULTRON!"
        return True, "Your phone is currently disconnected. Say 'connect ADB' to connect your phone."

    if any(k in raw for k in ["in my phone", "on my phone", "on phone", "in phone", "on my mobile", "in my mobile"]):
        from modules.adb_bridge import adb_bridge
        for app in ["youtube", "instagram", "whatsapp", "chrome", "spotify", "camera", "settings"]:
            if app in raw:
                return True, adb_bridge.open_app(app)
        return True, "Triggered action on your phone, Harsha!"

    if "connect phone" in raw or "mobile link" in raw or "phone link" in raw:
        return True, "Phone portal is ready, Harsha! Your connection link is displayed on screen."




    # ── Live Web Search ─────────────────────────────────────────────────────────────
    if any(k in raw for k in ["search", "google", "check in google", "locations of", "where are", "where is", "find in google"]) and not any(k in raw for k in ["open google", "open chrome"]):
        from modules.internet import search_web_live
        query = re.sub(r"(search|the|web|for|google|check|in|tell|me|give|information|area|names|where|are|located)", " ", raw)
        clean_q = " ".join(query.split()).strip()
        search_target = f"QSpiders locations {clean_q}" if "spider" in raw else (clean_q or raw)

        web_info = search_web_live(search_target)
        if web_info:
            ai_summary = ask_ai(
                f"Answer Harsha directly in 1-2 short sentences giving the exact real location area names based on these "
                f"live search results:\n{web_info}"
            )
            if ai_summary:
                return True, ai_summary
        return True, f"Searched live for '{search_target}' but found no results."

    # ── YouTube / Play ─────────────────────────────────────────────────────────────
    if "youtube" in raw or raw.startswith("play "):
        execute(raw)
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

        # Agentic Execution with Semantic Memory & Multi-Step Reasoning
        from agent import ultron_agent
        _, agent_response = ultron_agent.process_task(task)
        if agent_response:
            replies.append(agent_response)


    if replies:
        return True, " ".join(replies)

    return True, "I'm right here, Harsha. Ask me anything."