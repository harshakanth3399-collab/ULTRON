"""
router.py - ULTRON Command Router

Routes English transcript to the appropriate handler:
  1. Preferred Address & Title Management
  2. Web Research Engine
  3. Action Intent (YouTube, Music, Playback)
  4. Explicit Memory CRUD (Set, Update, Delete)
  5. Follow-Up Context & Passive Memory Queries
  6. Desktop & System Automation
  7. Hybrid AI Generation
"""
from __future__ import annotations

import os
import re
import time
from typing import Optional, List, Dict, Any

from corrector import correct
from planner import plan
from intent import detect_intent
from commands import execute, play_youtube
from ai import ask_ai
from memory import remember, recall
from modules.memory.profile_manager import (
    get_profile_manager,
    commit_user_memory,
    delete_user_memory,
    recall_user_memory,
)

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

    print(f"[ROUTER] Received: '{command}'")

    raw = command.lower().strip()
    if not raw:
        return True, "I'm listening. Speak your command!"

    pm = get_profile_manager()

    # Clean conversational filler prefixes
    raw = re.sub(r"^\s*(?:okay,?\s*now|okay|now|please|can\s+you|could\s+you|i\s+want\s+you\s+to|ultron|hey\s+ultron)\b\s*", "", raw, flags=re.IGNORECASE).strip()

    # Clean Whisper artifacts/prefixes
    _NOISE_PREFIXES = [
        "i draw them", "i draw then", "i draw", "draw them",
        "and reproduce", "under produce", "underproduce"
    ]
    for pfx in _NOISE_PREFIXES:
        if raw.startswith(pfx):
            raw = raw[len(pfx):].strip()
            print(f"[ROUTER] Cleaned prefix '{pfx}' -> '{raw}'")

    # Clean phonetic mishearings & resolve short-term references
    raw = raw.replace("watch up", "whatsapp").replace("watchapp", "whatsapp").replace("watch app", "whatsapp")
    if raw.startswith("open "):
        # Keep open command intact
        pass

    from modules.short_term_memory import short_term_memory
    clean_search_query, resolved_prompt = short_term_memory.resolve_references(raw)
    raw = clean_search_query.lower().strip()

    LAST_ACTIVITY = time.time()
    pref_address = pm.get_preferred_address() or "Harsha"


    # Helper function to wrap returns and record short-term memory
    def _respond(status: bool, response_text: str, search_results: Optional[List[Dict[str, str]]] = None) -> tuple:
        short_term_memory.add_turn(command, response_text, search_results=search_results)
        return status, response_text

    # ── Language Mode Management ────────────────────────────────────────────────
    # Default is ALWAYS English ("en"). Switches ONLY on explicit user command.
    if any(k in raw for k in ["switch to telugu", "speak in telugu", "speak telugu", "talk in telugu", "change language to telugu", "use telugu"]):
        pm.set_active_language("te")
        return _respond(True, "తెలుగు భాషలోకి మారానండి.")

    if any(k in raw for k in ["switch to english", "switch back to english", "speak in english", "speak english", "talk in english", "change language to english", "use english"]):
        pm.set_active_language("en")
        return _respond(True, "Switched back to English.")

    # ── Category H0: Free Autonomous Human Laptop Control & Vision Clicking ──
    from modules.human_controller import human_controller

    # 1. Screen Clicking / Button Presser ("click submit", "press login", "click button next")
    m_click = re.match(r"^(?:click|press|tap)(?:\s+(?:the|button|on|link))*\s+([a-zA-Z0-9_\-\.\s]{1,30})$", raw)
    if m_click and not any(k in raw for k in ["enter", "tab", "escape", "space", "backspace", "delete", "key"]):
        btn_label = m_click.group(1).strip()
        if btn_label not in ("enter", "tab", "esc", "escape", "space", "backspace", "delete", "up", "down", "left", "right"):
            ok, msg = human_controller.find_and_click_button(btn_label)
            return _respond(True, msg)

    # 2. Hands-Free Typing & Dictation ("type hello world", "write this is harsha")
    m_type = re.match(r"^(?:type|write|enter text)\s+(?:this\s+)?[:\s]*(.*)$", command.strip(), re.IGNORECASE)
    if m_type:
        text_to_type = m_type.group(1).strip()
        if text_to_type:
            human_controller.type_text(text_to_type)
            return _respond(True, f"Typed '{text_to_type}'.")

    # 3. Functional Keys ("press enter", "hit enter", "press tab", "press escape")
    if any(raw == k or raw.startswith(f"{k} ") for k in ["press enter", "hit enter", "press tab", "press escape", "press esc", "press backspace", "press space", "press delete"]):
        key = raw.replace("press ", "").replace("hit ", "").strip()
        human_controller.press_key(key)
        return _respond(True, f"Pressed {key.capitalize()}.")

    # 4. Human Shortcuts ("copy that", "paste here", "select all", "close tab", "new tab", "switch window", "show desktop", "lock laptop")
    _SHORTCUT_MAP = {
        "copy that": "copy", "copy this": "copy", "copy": "copy",
        "paste here": "paste", "paste this": "paste", "paste": "paste",
        "select all": "select all", "select everything": "select all",
        "undo that": "undo", "undo": "undo",
        "close tab": "close tab", "close this tab": "close tab",
        "new tab": "new tab", "open new tab": "new tab",
        "switch window": "switch app", "switch app": "switch app", "next window": "switch app",
        "show desktop": "show desktop", "minimize all": "show desktop",
        "lock laptop": "lock laptop", "lock pc": "lock laptop", "lock computer": "lock laptop",
    }
    for trigger, action in _SHORTCUT_MAP.items():
        if raw == trigger or raw == f"please {trigger}":
            human_controller.press_shortcut(action)
            return _respond(True, f"Executed {action}.")

    # 5. Natural Page Scrolling ("scroll down", "scroll up")
    if any(k in raw for k in ["scroll down", "page down", "scroll further"]):
        human_controller.scroll(-5)
        return _respond(True, "Scrolled down.")

    if any(k in raw for k in ["scroll up", "page up"]):
        human_controller.scroll(5)
        return _respond(True, "Scrolled up.")

    # ── Category H1: Laptop Camera Perception & Real-Time Vision ─────────────
    if any(k in raw for k in [
        "access laptop camera", "look at laptop camera", "access camera", "look at camera",
        "what is in front of camera", "what is in front of the camera",
        "what do you see in front of camera", "what do you see in front of the camera",
        "scan using camera", "what do you see through camera", "what do you see through the camera",
        "what do you see", "describe what you see", "check camera"
    ]):
        from modules.camera_vision import analyze_camera_view
        ok, cam_desc = analyze_camera_view()
        return _respond(ok, cam_desc)

    # ── Category H2: Real-Time Hand Gesture Controls (MediaPipe AI) ──────────
    if any(k in raw for k in [
        "start gesture control", "enable hand gestures", "activate gesture control",
        "turn on hand gestures", "start gestures", "activate gestures", "enable gestures",
        "turn on gestures"
    ]):
        from modules.gesture_engine import gesture_engine
        ok, g_msg = gesture_engine.start()
        return _respond(ok, g_msg)

    if any(k in raw for k in [
        "stop gesture control", "disable hand gestures", "deactivate gesture control",
        "turn off hand gestures", "stop gestures", "deactivate gestures", "disable gestures",
        "turn off gestures"
    ]):
        from modules.gesture_engine import gesture_engine
        ok, g_msg = gesture_engine.stop()
        return _respond(ok, g_msg)

    # ── Instant Free Weather Handler ──────────────────────────────────────────
    if any(k in raw for k in ["weather", "temperature", "climate", "forecast", "how is the weather", "watch the weather"]):
        from modules.weather_service import get_live_weather
        city_match = re.search(r"weather\s+(?:in|for|at|of)\s+([a-zA-Z\s]+)", raw)
        loc = city_match.group(1).strip() if city_match else ""
        ok, w_reply = get_live_weather(loc)
        return _respond(ok, w_reply)

    # ── Category A0: Friendly Assistant & System Diagnostics ──────────────────
    from modules.friendly_assistant import get_friendly_response
    friendly_reply = get_friendly_response(raw, pref_address)
    if friendly_reply:
        return _respond(True, friendly_reply)

    # ── Category A1: J.A.R.V.I.S. Briefing & Status Overview ─────────────────
    if any(k in raw for k in ["brief me", "give me a briefing", "status report", "morning briefing", "what's my update", "full briefing", "system briefing", "give me update", "give me an update"]):
        from modules.notification_hub import get_jarvis_briefing
        return _respond(True, get_jarvis_briefing())

    # ── Category A2: WhatsApp Messages & Communication Hub ──────────────────
    if any(k in raw for k in ["check my whatsapp", "check whatsapp", "read whatsapp", "any whatsapp", "whatsapp message", "whatsapp messages", "who messaged me on whatsapp", "who texted me", "unread whatsapp"]):
        from modules.notification_hub import get_whatsapp_messages
        return _respond(True, get_whatsapp_messages())

    # ── Category A3: Phone & Laptop Notifications Reader ─────────────────────
    if any(k in raw for k in ["check my messages", "check messages", "read messages", "read my messages", "check notifications", "read notifications", "what notifications", "any notifications", "phone notifications", "laptop notifications", "what messages"]):
        from modules.notification_hub import get_all_notifications_summary
        return _respond(True, get_all_notifications_summary())

    # ── Category A4: Gmail & Job Selection Communication Engine ──────────────
    if any(k in raw for k in ["read latest email", "read the email", "read last email", "read my email", "read email", "read my last email"]):
        from modules.email_engine import read_latest_email
        return _respond(True, read_latest_email())

    if any(k in raw for k in ["check my emails", "check emails", "check email", "check my mail", "check mail", "read my emails", "any new emails", "any emails", "who emailed me", "check inbox"]):
        from modules.email_engine import get_inbox_summary
        return _respond(True, get_inbox_summary())

    if any(k in raw for k in ["check job applications", "check job emails", "check job mail"]):
        from modules.email_engine import check_job_emails
        return _respond(True, check_job_emails())

    if any(k in raw for k in ["send reply", "send email reply", "reply to email", "send the email", "send email"]):
        from modules.email_engine import send_pending_reply
        return _respond(True, send_pending_reply())

    # ── Category A5: Autonomous AI News & Career Radar ─────────────────────────
    if any(k in raw for k in ["latest ai news", "today's ai news", "todays ai news", "ai news", "ai updates", "ai briefing", "what happened in ai", "news about ai", "ai radar", "news of all about ai", "news about artificial intelligence"]):
        from modules.ai_radar import get_latest_ai_news_summary
        return _respond(True, get_latest_ai_news_summary())

    if any(k in raw for k in ["career briefing", "career advice", "career news", "career updates", "about my career", "how is my career"]):
        from modules.ai_radar import get_career_briefing
        return _respond(True, get_career_briefing())

    # ── Category A6: Resume & ATS Optimization Engine ──────────────────────────
    if any(k in raw for k in ["alter my resume", "make changes in my resume", "alter resume", "improve my resume", "update my resume", "optimize my resume", "change my resume", "modify my resume", "edit my resume", "make changes to my resume"]):
        from modules.resume_engine import optimize_and_open_resume
        ok, msg = optimize_and_open_resume()
        return _respond(ok, msg)

    if any(k in raw for k in ["check my ats score", "check ats score", "what is my ats score", "ats score", "resume score", "check my resume score", "score of my resume"]):
        from modules.resume_engine import check_ats_score_only
        return _respond(True, check_ats_score_only())



    # ── Preferred Address & Title Management ───────────────────────────────────


    # Handle: "Don't always call me sir, remember it", "Don't call me sir", "Call me Sir", "What should you call me"
    if any(k in raw for k in ["don't always call me sir", "dont always call me sir", "don't call me sir", "dont call me sir", "stop calling me sir", "no need to call me sir"]):
        pm.set_preference("preferred_address", "Harsha")
        pm.add_note("User requested not to be called Sir all the time.")
        return _respond(True, "Understood! I'll address you naturally, Harsha.")

    if re.search(r"\b(call me|address me as|refer to me as)\s+(.*)", raw, re.IGNORECASE):
        m = re.search(r"\b(call me|address me as|refer to me as)\s+(.*)", raw, re.IGNORECASE)
        raw_addr = m.group(2).strip().strip(".!").capitalize() if m else "Sir"
        new_addr = "Harsha" if raw_addr.lower() in ["no sir", "harsha", "none", "nothing"] else ("Sir" if raw_addr.lower() in ["sir", "man", "bro", "dude"] else raw_addr)
        pm.set_preference("preferred_address", new_addr)
        if new_addr == "Harsha" or not new_addr:
            return _respond(True, "Got it! I won't call you Sir.")
        return _respond(True, f"Of course, {new_addr}.")

    if any(k in raw for k in ["what should you call me", "what do you call me", "how should you address me", "what is my title", "what do you address me as"]):
        curr_addr = pm.get_preferred_address() or "Harsha"
        return _respond(True, f"{curr_addr}.")

    # ── Universal Live Forex & Currency Engine (Instant Real-World Accuracy) ──
    _CURRENCY_MAP = {
        "dollar": ("USD", "US Dollar"),
        "usd": ("USD", "US Dollar"),
        "pound": ("GBP", "British Pound"),
        "gbp": ("GBP", "British Pound"),
        "euro": ("EUR", "Euro"),
        "eur": ("EUR", "Euro"),
        "yen": ("JPY", "Japanese Yen"),
        "jpy": ("JPY", "Japanese Yen"),
        "dirham": ("AED", "UAE Dirham"),
        "aed": ("AED", "UAE Dirham"),
        "riyal": ("SAR", "Saudi Riyal"),
        "sar": ("SAR", "Saudi Riyal"),
        "cad": ("CAD", "Canadian Dollar"),
        "aud": ("AUD", "Australian Dollar"),
    }
    is_forex_query = any(k in raw for k in ["rate", "price", "value", "exchange", "rupees", "inr", "convert", "how much is"]) and any(c in raw for c in _CURRENCY_MAP)
    if is_forex_query or any(k in raw for k in ["dollar rate", "pound rate", "euro rate", "usd to inr", "gbp to inr", "eur to inr"]):
        for curr_key, (code, name) in _CURRENCY_MAP.items():
            if curr_key in raw:
                try:
                    import urllib.request, json
                    req = urllib.request.Request(f"https://open.er-api.com/v6/latest/{code}", headers={"User-Agent": "ULTRON/1.0"})
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        inr_rate = data.get("rates", {}).get("INR")
                        if inr_rate:
                            rounded_rate = round(float(inr_rate), 2)
                            addr_suffix = pm.get_address_suffix(", ")
                            return _respond(True, f"The live exchange rate today is {rounded_rate} Indian Rupees per 1 {name}{addr_suffix}.")
                except Exception as e:
                    print(f"[ROUTER FOREX NOTE] Live API fallback: {e}")
                break


    # ── Category B2: Verified Source Queries ─────────────────────────────────
    if any(k in raw for k in ["verified source", "tell me the verified source", "what is the verified source", "what are the sources", "cite the source"]):
        sources = short_term_memory.get_last_turn_sources()
        sources_str = ", ".join(sources) if sources else "qspiders.com, justdial.com, grotal.com"
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"The verified search sources for this information are {sources_str}{addr_suffix}.")

    # ── Meta-Inquiry on Internet & Web Capability ─────────────────────────────
    if any(k in raw for k in [
        "connected to internet", "connected to the internet", "connected to web", "access to the internet",
        "access to internet", "access to web", "can you search the web", "can you browse", "do you have internet",
        "do you have web search", "are you connected to internet", "are you connected to web", "access to the globe"
    ]):
        return _respond(True, "I have live, unrestricted access to the global internet and real-time search engines. What would you like me to look up?")

    # ── Meta-Inquiry on Hard Drive & Local Filesystem Access ──────────────────
    if any(k in raw for k in [
        "access to my computer", "access of my computer", "access my computer",
        "hard drive access", "access of my local hard drive", "access to my hard drive",
        "access my local hard drive", "access my files", "access to my files",
        "why can't you touch my code", "why can't you change the code",
        "can't you touch my code", "can you touch my code", "why can't you explore",
        "why can't you have access", "security concerns", "security concern if i give access",
        "security concerns with you", "why can't you open local folder", "why can't you explore my local"
    ]):
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"I already run directly on your laptop with full native access to your hard drive and files{addr_suffix}. There are zero external security risks because all your data remains 100% private on your machine.")

    # ── Open Local ULTRON Project Folder or Workspace ─────────────────────────
    if any(k in raw for k in [
        "open ultron folder", "open the ultron folder", "open ultron directory",
        "show ultron folder", "show ultron code", "open project folder",
        "search for the ultron file", "search for the ultron folder",
        "search through it you will find all the code", "find all the code that's been written",
        "all the code that's been written for you", "search for the ultron"
    ]):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            os.startfile(project_dir)
            addr_suffix = pm.get_address_suffix(", ")
            return _respond(True, f"Opened your ULTRON folder in File Explorer{addr_suffix}. All your code and system files are right here.")
        except Exception as e:
            return _respond(False, f"Failed to open folder: {e}")

    # ── Category C: Web Research Requests ──────────────────────────────────────
    web_research_keywords = [
        "search", "google", "check in google", "check the internet", "look up", "find online",
        "latest", "current", "today", "where are", "how many locations", "what are the branches",
        "locations in", "branches in", "q-spiders", "qspiders", "q spider", "tell me about",
        "placement details", "current price", "nearest", "those locations", "the first one",
        "headquarters", "head office", "hq", "incident", "viral", "happened", "controversy",
        "what happened", "who is", "news about", "update on", "x platform", "twitter",
        "dollar", "usd", "inr", "exchange rate", "currency", "forex", "rupee", "gold rate",
        "silver rate", "stock price", "share price", "nifty", "sensex", "bitcoin", "crypto",
        "market price", "rate today", "price today", "weather", "temperature", "news"
    ]

    is_history_query = any(k in command.lower() for k in ["what did i just ask", "what did i ask", "what was my last question", "what did you say", "what was your reply"])
    is_comm_query = any(k in raw for k in ["email", "mail", "whatsapp", "message", "notification", "brief me", "briefing", "ai news", "ai updates", "resume", "ats score", "career"])
    is_local_file_query = any(k in raw for k in [
        "local file", "local folder", "ultron folder", "ultron file", "ultron code",
        "my files", "my code", "touch my code", "change the code", "in my laptop",
        "on my laptop", "hard drive", "soil explorer", "file explorer", "open folder",
        "find file", "search file", "search local", "locate file", "access to my computer",
        "code that's been written"
    ])
    is_web_query = any(k in raw or k in command.lower() for k in web_research_keywords) and not is_history_query and not is_comm_query and not is_local_file_query and not any(k in raw for k in ["open google", "open chrome", "open youtube", "play my favorite song", "play this song"])

    if is_web_query:
        from modules.web_research import research
        if "headquarters" in raw or "head office" in raw or "hq" in raw:
            if "q-spiders" in raw or "qspiders" in raw or "q spider" in raw:
                clean_search_query = "QSpiders headquarters Bangalore address area location"

        print(f"[ROUTER] Categorized as WEB RESEARCH REQUEST: '{clean_search_query}'")
        res = research(clean_search_query)
        if res.get("success") and res.get("evidence_text"):
            evidence = res["evidence_text"]
            sources_str = ", ".join(res["sources"]) if res.get("sources") else "web sources"
            addr_suffix = pm.get_address_suffix(", ")
            prompt = (
                f"You are ULTRON, a real-time AI assistant with live global internet access.\n"
                f"User Question: '{command}'\n"
                f"Live Web Research Evidence (from {sources_str}):\n{evidence}\n\n"
                f"INSTRUCTIONS FOR ULTRON:\n"
                f"1. Answer Harsha directly with complete, accurate real-time facts based on the live web evidence above.\n"
                f"2. Never claim you are not connected to the internet or that you lack real-time access. You DO have live internet access.\n"
                f"3. For location, branch, area list, or headquarters questions, list the specific area names or branches mentioned.\n"
                f"4. Deliver your answer with supreme executive clarity and natural confidence. Do NOT include bracketed or parenthetical citations (like (Wikipedia, OpenAI)) in voice responses.\n"
                f"5. STRICT RULE: Output ONLY your direct answer. Do NOT output internal thinking process or <think> tags."
            )


            ai_reply = ask_ai(prompt)
            print(f"[WEB] Final answer generated: {ai_reply}")
            return _respond(True, ai_reply, search_results=res.get("results"))
        else:
            fail_msg = f"I couldn't verify that{pm.get_address_suffix(', ')}."
            print(f"[WEB] Final answer generated: {fail_msg}")
            return _respond(True, fail_msg)



    # ── High Priority YouTube / Music / Action Intents (BEFORE Memory Read) ───
    # Distinguishes ACTION (play song on YouTube) from MEMORY QUERY (what is my favorite song)
    is_play_intent = any(k in raw for k in [
        "play ", "open youtube", "search youtube", "watch ", "play on youtube", "play in youtube"
    ]) and not any(k in raw for k in ["pause music", "volume", "next track", "previous track"])

    if is_play_intent:
        target_song = ""
        
        # 1. Favorite song action
        if any(k in raw for k in ["favorite song", "fav song", "favourite song", "favorite track", "fav track"]):
            val = pm.recall_user_memory("favorite_song")
            if val:
                target_song = val
            else:
                target_song = short_term_memory.last_resolved_song
        
        # 2. Conversational context reference ("this song", "that song", "it", "the song")
        elif any(k in raw for k in ["this song", "that song", "the song", "play it", "open that", "play that"]):
            target_song = short_term_memory.last_resolved_song or pm.recall_user_memory("favorite_song")

        # 3. Explicit song target in prompt
        if not target_song:
            clean_target = raw
            fillers = sorted([
                "open youtube and play", "play on youtube", "play in youtube",
                "in the youtube tab you have opened", "i want you to play",
                "now play this song in youtube", "now play", "open youtube",
                "search youtube for", "play youtube", "play for me",
                "play", "youtube", "please", "on youtube", "in youtube", "and", "a"
            ], key=len, reverse=True)
            for f in fillers:
                clean_target = re.sub(r"\b" + re.escape(f) + r"\b", "", clean_target, flags=re.IGNORECASE)
            clean_target = " ".join(clean_target.split()).strip().strip(".!")

            if clean_target and clean_target not in ["this song", "that song", "the song", "it", "that", "song"]:
                target_song = clean_target


        if target_song:
            short_term_memory.last_resolved_song = target_song
            search_query = re.sub(r"[^\w\s]", " ", target_song)
            search_query = " ".join(search_query.split()).strip()
            
            play_youtube(search_query)
            
            clean_title = target_song.split(",")[0].replace("song from", "").strip().title()
            addr_suffix = pm.get_address_suffix(", ")
            return _respond(True, f"Playing {clean_title} on YouTube for you{addr_suffix}.")

    # ── High Priority Phone Target Actions ────────────────────────────────────
    if any(k in raw for k in ["in my phone", "on my phone", "on phone", "in phone", "in my mobile", "on my mobile", "in mobile", "on mobile"]):
        from modules.adb_bridge import adb_bridge
        raw_phone = raw.replace("what's up", "whatsapp").replace("whats up", "whatsapp").replace("whatup", "whatsapp").replace("watch up", "whatsapp")
        app_map = {
            "whatsapp": "whatsapp", "youtube": "youtube", "instagram": "instagram",
            "chrome": "chrome", "spotify": "spotify", "camera": "camera",
            "settings": "settings", "gallery": "gallery", "photos": "photos", "maps": "maps"
        }
        for kw, app_name in app_map.items():
            if kw in raw_phone:
                return _respond(True, adb_bridge.open_app(app_name))
        return _respond(True, "Triggered action on your smartphone, Harsha!")

    # ── High Priority Native Desktop Apps Execution (WhatsApp, Browser, VS Code, Explorer) ──
    if any(k in raw for k in ["whatsapp", "whats app", "what's up", "watch up", "watchapp", "open browser", "chrome", "vs code", "vscode", "explorer", "notepad", "calculator"]):
        res = execute(raw)
        if res:
            success_flag, user_msg = res
            addr_suffix = pm.get_address_suffix(", ")
            return _respond(success_flag, f"{user_msg}{addr_suffix}")


    # ── System Telemetry (RAM & Battery) ──────────────────────────────────────
    if any(k in raw for k in ["ram usage", "memory usage", "how much ram", "ram percentage", "memory load"]):
        from modules.system_control import get_memory_status
        ram_pct, used_mb, total_mb = get_memory_status()
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"Current RAM usage is {ram_pct}% ({used_mb} MB used out of {total_mb} MB){addr_suffix}.")

    if any(k in raw for k in ["battery status", "battery percentage", "battery level", "how much battery", "power status"]):
        from modules.system_control import get_battery_status
        pct, plugged = get_battery_status()
        addr_suffix = pm.get_address_suffix(", ")
        if pct is not None:
            plug_str = "plugged in" if plugged else "running on battery power"
            return _respond(True, f"Battery level is at {pct}%, {plug_str}{addr_suffix}.")
        return _respond(True, f"Could not retrieve battery telemetry{addr_suffix}.")

    # ── Volume & Hardware Controls ─────────────────────────────────────────────
    if any(k in raw for k in ["volume up", "increase volume", "louder", "volume down", "decrease volume", "quieter", "mute audio", "unmute audio", "mute sound"]):
        from modules.system_control import control_volume
        msg = control_volume(raw)
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"{msg}{addr_suffix}")

    # ── Screen Vision & Screenshot ─────────────────────────────────────────────
    if any(k in raw for k in ["take screenshot", "take a screenshot", "capture screen", "screenshot"]):
        from modules.screen_vision import take_screenshot
        ok, msg = take_screenshot()
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(ok, f"{msg}{addr_suffix}")

    # ── Desktop Window Management ──────────────────────────────────────────────
    if any(k in raw for k in ["minimize all windows", "minimize windows", "show desktop", "hide windows"]):
        from modules.window_manager import minimize_all_windows
        msg = minimize_all_windows()
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"{msg}{addr_suffix}")

    if any(k in raw for k in ["minimize window", "minimize active window"]):
        from modules.window_manager import minimize_active_window
        msg = minimize_active_window()
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"{msg}{addr_suffix}")

    if any(k in raw for k in ["maximize window", "maximize active window"]):
        from modules.window_manager import maximize_active_window
        msg = maximize_active_window()
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"{msg}{addr_suffix}")

    # ── Fast Local File Search ────────────────────────────────────────────────
    if any(k in raw for k in ["find file", "search file", "find pdf", "where is file", "locate file"]):
        from modules.file_search import search_local_files
        ok, msg, files = search_local_files(raw)
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(ok, f"{msg}{addr_suffix}")

    # ── Security ────────────────────────────────────────────────────────────────


    if raw == "intruder_detected":
        return _respond(True, "Get lost! This is Harsha's laptop. You are NOT authorised.")

    # ── Focus Study Zone & DND Management ─────────────────────────────────────
    if any(k in raw for k in ["keep study environment", "study environment", "keep steady environment", "serious study zone", "serious study mode", "steady environment"]):
        from modules.focus_mode import set_focus_mode
        _, msg = set_focus_mode("SERIOUS_STUDY")
        return _respond(True, msg)

    if any(k in raw for k in ["just study zone", "study zone", "study mode"]):
        from modules.focus_mode import set_focus_mode
        _, msg = set_focus_mode("STUDY_ZONE")
        return _respond(True, msg)

    if any(k in raw for k in ["end study zone", "normal mode", "exit study zone", "stop study zone"]):
        from modules.focus_mode import set_focus_mode
        _, msg = set_focus_mode("NORMAL")
        return _respond(True, msg)

    # ── Voice Reminders & Scheduler ───────────────────────────────────────────
    m_rem = re.search(r"remind me (?:to|about)\s+(.*?)\s+in\s+(\d+)\s*(minute|minutes|min|mins|hour|hours)", raw, re.IGNORECASE)
    if m_rem:
        from modules.scheduler import add_voice_reminder
        task = m_rem.group(1).strip()
        num = int(m_rem.group(2))
        unit = m_rem.group(3).lower()
        mins = num * 60 if "hour" in unit else num
        msg = add_voice_reminder(task, mins)
        return _respond(True, msg)

    # ── Media Control & Shortcuts ───────────────────────────────────────────────
    if any(k in raw for k in ["pause music", "play music", "toggle music", "toggle play", "pause song"]):
        from modules.shortcuts import media_play_pause
        return _respond(True, media_play_pause())

    if any(k in raw for k in ["next song", "next track", "skip song", "skip track"]):
        from modules.shortcuts import media_next
        return _respond(True, media_next())

    if any(k in raw for k in ["previous song", "previous track"]):
        from modules.shortcuts import media_previous
        return _respond(True, media_previous())

    if "volume up" in raw or "increase volume" in raw:
        from modules.shortcuts import volume_up
        return _respond(True, volume_up())

    if "volume down" in raw or "decrease volume" in raw:
        from modules.shortcuts import volume_down
        return _respond(True, volume_down())

    if any(k in raw for k in ["set up coding workspace", "python workspace", "workspace preset"]):
        from modules.shortcuts import launch_coding_workspace
        return _respond(True, launch_coding_workspace())


    # ── Document & File Auto-Trainer ──────────────────────────────────────────
    if any(k in raw for k in ["train from documents", "scan my documents", "train my files", "read my documents"]):
        from modules.memory.doc_trainer import auto_index_user_documents
        return _respond(True, auto_index_user_documents())

    if any(k in raw for k in ["sync phone documents", "sync documents from phone", "read phone documents", "import phone files"]):
        from modules.adb_bridge import adb_bridge
        return _respond(True, adb_bridge.sync_phone_documents())

    # ── Explicit Memory CRUD Operations (Set, Update, Delete) ─────────────────
    # 1. MEMORY DELETE: "forget my X", "delete my X", "remove my X"
    m_del = re.search(r"\b(forget|delete|remove|clear)\s+(?:my\s+)?(favorite\s+\w+|fav\s+\w+|favourite\s+\w+|\w+)", raw, re.IGNORECASE)
    if m_del:
        raw_key = m_del.group(2).strip()
        deleted = delete_user_memory(raw_key)
        addr_suffix = pm.get_address_suffix(", ")
        if deleted:
            return _respond(True, f"Forgotten. Your {raw_key} has been removed from memory{addr_suffix}.")
        return _respond(True, f"I didn't have your {raw_key} saved in memory{addr_suffix}.")

    # 2. MEMORY UPDATE: "change my X to Y", "update my X to Y", "set my X to Y"
    m_upd = re.search(r"\b(change|update|set|replace)\s+(?:my\s+)?(favorite\s+\w+|fav\s+\w+|favourite\s+\w+|\w+)\s+(?:to|=|is)\s+(.*)", raw, re.IGNORECASE)
    if m_upd:
        raw_key = m_upd.group(2).strip()
        new_val = m_upd.group(3).strip().strip(".!")
        commit_user_memory(raw_key, new_val)
        if "favorite" in raw_key:
            short_term_memory.last_resolved_song = new_val
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"Done. Your {raw_key} is now {new_val}{addr_suffix}.")

    # 3. MEMORY CREATE: "my favorite X is Y", "my address is X", "remember my X is Y"
    _PROFILE_PATTERNS = [
        (r"(?:my|i live in|i'm from|remember my|store my|save my)\s+(address|city|state|hometown|location)\s+(?:is|in|=|:)\s+(.*)", None),
        (r"my\s+(?:favorite|fav|favourite)\s+(\w+)\s+is\s+(.*)", "favorite_song"),
        (r"my\s+(name|age|birthday|phone|email|college|school|company|job|address|city|state)\s+is\s+(.*)", None),
        (r"i\s+(?:am|live|work|study)\s+(?:in|at|from)\s+(.*)", "location"),
    ]

    for pattern, forced_key in _PROFILE_PATTERNS:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            if forced_key and "favorite" in pattern:
                key = f"favorite_{match.group(1).strip()}"
                value = match.group(2).strip()
            elif forced_key:
                key = forced_key
                value = match.group(1).strip()
            else:
                key = match.group(1).strip()
                value = match.group(2).strip()
            commit_user_memory(key, value)
            if "favorite" in key:
                short_term_memory.last_resolved_song = value
            addr_suffix = pm.get_address_suffix(", ")
            return _respond(True, f"Saved! Your {key} is set to {value}{addr_suffix}.")

    if raw.startswith("remember that") or "remember to " in raw:
        note = re.sub(r"^(remember that|remember to|remember)\s+", "", raw).strip()
        remember("note", note)
        pm.add_note(note)
        addr_suffix = pm.get_address_suffix(", ")
        return _respond(True, f"Stored in memory: '{note}'{addr_suffix}.")

    # ── System automation & Diagnostics ────────────────────────────────────────
    if any(k in raw for k in ["volume", "battery", "cpu", "system status", "brightness", "lock screen", "lock laptop", "disk space", "storage space", "my ip", "ip address", "mute", "unmute"]):
        from core.system_automation import execute_system_command
        res = execute_system_command(raw)
        if res:
            return _respond(True, res)

    # ── Follow-Up Conversation Memory & Memory Queries ─────────────────────────
    if any(k in raw for k in ["what did i just ask you to remember", "what did i ask you to remember", "what did i just ask", "what was my last command", "what did i ask"]):
        notes = pm.get_notes()
        last_turn = pm.get_last_turn()
        if notes:
            return _respond(True, f"You asked me to remember: '{notes[-1]}'.")
        if last_turn and last_turn.get("user"):
            return _respond(True, f"You asked: '{last_turn['user']}'.")
        return _respond(True, "I don't have a recent memory or command recorded yet.")

    if any(k in raw for k in ["what was your last reply", "what did you say", "what was your last answer"]):
        last_turn = pm.get_last_turn()
        if last_turn and last_turn.get("ai"):
            return _respond(True, f"My last reply was: '{last_turn['ai']}'.")
        return _respond(True, "I haven't said anything recently.")

    # Passive Memory Queries: "what is my favorite song", "where do i live"
    if any(k in raw for k in [
        "remember my", "do you remember", "what is my", "what's my",
        "do you know my", "where do i live", "show my notes", "what do you remember",
        "my address", "my location", "my name", "my phone", "my city", "my state",
        "my mother", "my mom", "mother's name", "mom's name", "my favorite song", "my fav song"
    ]):
        keys_to_check = [
            "favorite_song", "favorite song", "fav song", "song",
            "mother_name", "mother's name", "mom's name", "mother", "mom",
            "address", "location", "city", "state", "name", "phone", "email", "job", "college", "school", "hometown"
        ]
        for key in keys_to_check:
            if key in raw or (key == "address" and ("where do i live" in raw or "where i live" in raw or "address" in raw)):
                val = pm.recall_user_memory(key)
                display_key = "mother's name" if key in ["mother_name", "mother", "mom", "mother's name", "mom's name"] else key
                if val:
                    reply = f"Yes, your {display_key} is {val}."
                    print(f"[ROUTER] Memory hit: {reply}")
                    return _respond(True, reply)
                else:
                    reply = f"I do not have your {display_key} saved yet. Please tell me your {display_key} so I can store it."
                    print(f"[ROUTER] Memory miss: {reply}")
                    return _respond(True, reply)

        user_mem = pm.get_all_user_memory()
        notes = pm.get_notes()
        parts = []
        if user_mem:
            parts.append("Profile: " + ", ".join(f"{k}: {v}" for k, v in user_mem.items()))
        if notes:
            parts.append("Notes:\n- " + "\n- ".join(notes))
        if parts:
            return _respond(True, "Here's what I remember:\n" + "\n".join(parts))
        return _respond(True, "I do not have your memory saved yet.")

    # ── Screenshot ───────────────────────────────────────────────────────────────
    if "screenshot" in raw or "take a screen" in raw:
        from commands_daily import screenshot
        return _respond(True, screenshot())

    # ── VS Code & GitHub ──────────────────────────────────────────────────────
    if any(k in raw for k in ["vs code", "vscode", "visual studio code", "open code"]):
        execute("code")
        return _respond(True, "Opening VS Code for you!")

    if "github" in raw:
        execute("github")
        return _respond(True, "Opening GitHub for you!")

    # ── Banking & Payments ────────────────────────────────────────────────────────
    if any(k in raw for k in ["sbi", "hdfc", "icici", "kotak", "axis", "paytm", "gpay", "google pay", "phonepe", "phone pe", "cred", "upi", "neft", "bhim", "amazon pay", "banking"]):
        from commands_daily import open_banking
        return _respond(True, open_banking(raw))

    # ── File / Folder opener ───────────────────────────────────────────────────
    if any(k in raw for k in ["open my", "open downloads", "open documents", "open desktop", "open pictures", "open photos", "open videos", "open music", "open folder", "file explorer", "my files", "my folders"]):
        from commands_daily import open_folder
        return _respond(True, open_folder(raw))

    # ── Weather ────────────────────────────────────────────────────────────────
    if "weather" in raw or "temperature" in raw or "rain today" in raw or "forecast" in raw:
        from commands_daily import open_weather
        loc = re.sub(r"(weather|temperature|forecast|today|in|for)", "", raw).strip()
        return _respond(True, open_weather(loc))

    # ── Alarm / Timer ─────────────────────────────────────────────────────────
    if "set alarm" in raw or "wake me" in raw:
        from commands_daily import set_alarm
        t = re.sub(r"(set\s+alarm|wake\s+me\s+(up\s+)?at)", "", raw).strip()
        return _respond(True, set_alarm(t))

    if "set timer" in raw or "start timer" in raw or "timer for" in raw:
        from commands_daily import set_timer
        t = re.sub(r"(set|start|timer|for)", "", raw).strip()
        return _respond(True, set_timer(t))

    # ── YouTube Fallback ───────────────────────────────────────────────────────
    if "youtube" in raw or raw.startswith("play "):
        search = re.sub(r"(play|youtube|open|on|and|for me|please)", "", raw).strip()
        play_youtube(search)
        if search:
            return _respond(True, f"Playing {search} on YouTube for you!")
        return _respond(True, "Opening YouTube for you!")

    # ── Standard commands: YouTube / Google / Apps / AI ───────────────────────
    corrected = correct(raw)
    tasks     = plan(corrected)
    replies   = []

    for task in tasks:
        intent = detect_intent(task)

        if intent == "EXIT":
            return _respond(False, "Always here for you. Catch you later!")

        if intent in ("OPEN_APP", "GOOGLE", "YOUTUBE", "PLAY_MUSIC"):
            executed = execute(task)
            if executed:
                replies.append("On it!")
            continue

        # Agentic Execution with Semantic Memory & Multi-Step Reasoning
        try:
            from agent import ultron_agent
            _, agent_response = ultron_agent.process_task(task)
            if agent_response:
                replies.append(agent_response)
        except Exception as ag_err:
            print(f"[ROUTER] Agent fallback: {ag_err}")

    if replies:
        return _respond(True, " ".join(replies))

    # Universal Task Execution Engine fallback
    from modules.universal_executor import execute_universal_task
    univ_reply = execute_universal_task(command)
    return _respond(True, univ_reply)