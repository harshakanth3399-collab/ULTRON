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

    print(f"[ROUTER] Received: '{command}'")

    raw = command.lower().strip()
    if not raw:
        return True, "I'm listening, Harsha. Speak your command!"

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
    if raw.startswith("okay open "):
        raw = raw[10:].strip()

    from modules.short_term_memory import short_term_memory
    clean_search_query, resolved_prompt = short_term_memory.resolve_references(raw)
    raw = clean_search_query.lower().strip()

    LAST_ACTIVITY = time.time()

    # Helper function to wrap returns and record short-term memory
    def _respond(status: bool, response_text: str, search_results: Optional[List[Dict[str, str]]] = None) -> tuple:
        short_term_memory.add_turn(command, response_text, search_results=search_results)
        return status, response_text

    web_research_keywords = [
        "search", "google", "check in google", "check the internet", "look up", "find online",
        "latest", "current", "today", "where are", "how many locations", "what are the branches",
        "locations in", "branches in", "q-spiders", "qspiders", "q spider", "tell me about",
        "placement details", "current price", "nearest", "those locations", "the first one"
    ]
    is_history_query = any(k in command.lower() for k in ["what did i just ask", "what did i ask", "what was my last question", "what did you say", "what was your reply"])
    is_web_query = any(k in raw or k in command.lower() for k in web_research_keywords) and not is_history_query and not any(k in raw for k in ["open google", "open chrome", "open youtube"])


    if is_web_query:
        from modules.web_research import research
        print(f"[ROUTER] Categorized as WEB RESEARCH REQUEST: '{clean_search_query}'")
        res = research(clean_search_query)
        if res.get("success") and res.get("evidence_text"):
            evidence = res["evidence_text"]
            sources_str = ", ".join(res["sources"]) if res.get("sources") else "web sources"
            prompt = (
                f"User Question: '{command}' ({resolved_prompt})\n"
                f"Web Evidence (from {sources_str}):\n{evidence}\n\n"
                f"INSTRUCTIONS: Answer Harsha directly in 1-3 clear sentences based ONLY on the web evidence above. "
                f"Cite the source site names. NEVER invent numbers, branch counts, or addresses. "
                f"If the web evidence does not specify an exact count or detail, state clearly that it could not be verified."
            )
            ai_reply = ask_ai(prompt)
            print(f"[WEB] Final answer generated: {ai_reply}")
            return _respond(True, ai_reply, search_results=res.get("results"))
        else:
            fail_msg = f"I couldn't find reliable web sources to verify '{command}', Sir."
            print(f"[WEB] Final answer generated: {fail_msg}")
            return _respond(True, fail_msg)



    # ── High Priority WhatsApp & Messaging Intents (BEFORE multi-command split) ─────────
    if "whatsapp" in raw or "message" in raw:
        from modules.adb_bridge import adb_bridge
        m_msg = re.search(r"message\s+(.*?)\s+to\s+(.*)", raw, re.IGNORECASE) or re.search(r"message\s+(.*)", raw, re.IGNORECASE)
        contact = "contact"
        if m_msg:
            contact = m_msg.group(2).strip() if len(m_msg.groups()) > 1 else m_msg.group(1).strip()
        adb_bridge.open_app("whatsapp")
        return True, f"Opening WhatsApp to message {contact.capitalize()}, Sir."

    # ── Multi-Command Decomposition ─────────────────────────────────────────
    if any(sep in raw for sep in [" and ", " then ", " and then "]) and not ("favorite" in raw or "remember" in raw):
        tasks = plan(raw)
        if len(tasks) > 1:
            print(f"[ROUTER] Multi-command detected ({len(tasks)} tasks): {tasks}")
            responses = []
            for t in tasks:
                flag, resp = process(t)
                if resp and resp not in responses:
                    responses.append(resp)
            combined = " ".join(responses) if responses else "Executed all commands for you, Harsha!"
            return True, combined


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

    # ── Preferred Address Management ──────────────────────────────────────────
    if re.search(r"\b(call me|address me as|refer to me as)\s+(.*)", raw, re.IGNORECASE):
        pm = get_profile_manager()
        m = re.search(r"\b(call me|address me as|refer to me as)\s+(.*)", raw, re.IGNORECASE)
        raw_addr = m.group(2).strip().strip(".!").capitalize() if m else "Sir"
        new_addr = "Sir" if raw_addr.lower() in ["sir", "man", "bro", "dude"] else raw_addr
        pm.set_preference("preferred_address", new_addr)
        return True, f"Of course, {new_addr}."

    if any(k in raw for k in ["what should you call me", "what do you call me", "how should you address me", "what is my title", "what do you address me as"]):
        pm = get_profile_manager()
        curr_addr = pm.data.get("preferences", {}).get("preferred_address", "Sir")
        return True, f"{curr_addr}."

    # ── Focus Study Zone & DND Management ─────────────────────────────────────
    if any(k in raw for k in ["keep study environment", "study environment", "keep steady environment", "serious study zone", "serious study mode", "steady environment"]):
        from modules.focus_mode import set_focus_mode
        _, msg = set_focus_mode("SERIOUS_STUDY")
        return True, msg

    if any(k in raw for k in ["just study zone", "study zone", "study mode"]):
        from modules.focus_mode import set_focus_mode
        _, msg = set_focus_mode("STUDY_ZONE")
        return True, msg


    if any(k in raw for k in ["end study zone", "normal mode", "exit study zone", "stop study zone"]):
        from modules.focus_mode import set_focus_mode
        _, msg = set_focus_mode("NORMAL")
        return True, msg

    # ── Voice Reminders & Scheduler ───────────────────────────────────────────
    m_rem = re.search(r"remind me (?:to|about)\s+(.*?)\s+in\s+(\d+)\s*(minute|minutes|min|mins|hour|hours)", raw, re.IGNORECASE)
    if m_rem:
        from modules.scheduler import add_voice_reminder
        task = m_rem.group(1).strip()
        num = int(m_rem.group(2))
        unit = m_rem.group(3).lower()
        mins = num * 60 if "hour" in unit else num
        msg = add_voice_reminder(task, mins)
        return True, msg

    # ── Media Control & Shortcuts ───────────────────────────────────────────────
    if any(k in raw for k in ["pause music", "play music", "toggle music", "toggle play", "pause song"]):
        from modules.shortcuts import media_play_pause
        return True, media_play_pause()

    if any(k in raw for k in ["next song", "next track", "skip song", "skip track"]):
        from modules.shortcuts import media_next
        return True, media_next()

    if any(k in raw for k in ["previous song", "previous track"]):
        from modules.shortcuts import media_previous
        return True, media_previous()

    if "volume up" in raw or "increase volume" in raw:
        from modules.shortcuts import volume_up
        return True, volume_up()

    if "volume down" in raw or "decrease volume" in raw:
        from modules.shortcuts import volume_down
        return True, volume_down()

    if any(k in raw for k in ["set up coding workspace", "python workspace", "workspace preset"]):
        from modules.shortcuts import launch_coding_workspace
        return True, launch_coding_workspace()

    # ── Gmail & Job Selection Assistant ─────────────────────────────────────────
    if any(k in raw for k in ["check my emails", "check job applications", "check email", "check mail", "check job email"]):
        from modules.email_engine import check_job_emails
        return True, check_job_emails()

    if any(k in raw for k in ["send reply", "send email reply", "reply to email", "send the email", "send email"]):
        from modules.email_engine import send_pending_reply
        return True, send_pending_reply()

    # ── Document & File Auto-Trainer ──────────────────────────────────────────
    if any(k in raw for k in ["train from documents", "scan my documents", "train my files", "read my documents"]):
        from modules.memory.doc_trainer import auto_index_user_documents
        return True, auto_index_user_documents()

    if any(k in raw for k in ["sync phone documents", "sync documents from phone", "read phone documents", "import phone files"]):
        from modules.adb_bridge import adb_bridge
        return True, adb_bridge.sync_phone_documents()







    # ── Memory CRUD Operations (Create, Query, Update, Delete) ─────────────────
    from modules.memory.profile_manager import get_profile_manager, commit_user_memory, delete_user_memory, recall_user_memory
    pm = get_profile_manager()
    pref_addr = pm.data.get("preferences", {}).get("preferred_address", "Sir")

    # 1. MEMORY DELETE: "forget my X", "delete my X", "remove my X"
    m_del = re.search(r"\b(forget|delete|remove|clear)\s+(?:my\s+)?(favorite\s+\w+|fav\s+\w+|favourite\s+\w+|\w+)", raw, re.IGNORECASE)
    if m_del:
        raw_key = m_del.group(2).strip()
        deleted = delete_user_memory(raw_key)
        if deleted:
            return _respond(True, f"Forgotten, {pref_addr}. Your {raw_key} has been removed from memory.")
        return _respond(True, f"I didn't have your {raw_key} saved in memory, {pref_addr}.")

    # 2. MEMORY UPDATE: "change my X to Y", "update my X to Y", "set my X to Y"
    m_upd = re.search(r"\b(change|update|set|replace)\s+(?:my\s+)?(favorite\s+\w+|fav\s+\w+|favourite\s+\w+|\w+)\s+(?:to|=|is)\s+(.*)", raw, re.IGNORECASE)
    if m_upd:
        raw_key = m_upd.group(2).strip()
        new_val = m_upd.group(3).strip().strip(".!")
        commit_user_memory(raw_key, new_val)
        return _respond(True, f"Done, {pref_addr}. Your {raw_key} is now {new_val}.")

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
            return _respond(True, f"Saved, {pref_addr}. Your {key} is set to {value}.")


    if raw.startswith("remember that"):
        note = raw.replace("remember that", "").strip()
        remember("note", note)
        pm = get_profile_manager()
        pref_addr = pm.data.get("preferences", {}).get("preferred_address", "Sir")
        pm.add_note(note)
        return _respond(True, f"Stored in memory, {pref_addr}: '{note}'")


    # ── System automation & Diagnostics ────────────────────────────────────────
    if any(k in raw for k in ["volume", "battery", "cpu", "system status", "brightness", "lock screen", "lock laptop", "disk space", "storage space", "my ip", "ip address", "mute", "unmute"]):
        from core.system_automation import execute_system_command
        res = execute_system_command(raw)
        if res:
            return True, res

    # ── Follow-Up Conversation Memory ──────────────────────────────────────────
    if any(k in raw for k in ["what did i just say", "what was my last command", "what did i ask"]):
        pm = get_profile_manager()

        last = pm.get_last_turn()
        if last and last.get("user"):
            return True, f"You just said: '{last['user']}', Harsha!"
        return True, "I don't have a previous command recorded yet, Harsha."

    if any(k in raw for k in ["what was your last reply", "what did you say", "what was your last answer"]):
        pm = get_profile_manager()

        last = pm.get_last_turn()
        if last and last.get("ai"):
            return True, f"My last reply was: '{last['ai']}', Harsha!"
        return True, "I haven't said anything recently, Harsha."

    # Memory Recall & Memory Retrieval (Hardware Fallback Enforcement)
    if any(k in raw for k in [
        "remember my", "do you remember", "what is my", "what's my",
        "do you know my", "where do i live", "show my notes", "what do you remember",
        "my address", "my location", "my name", "my phone", "my city", "my state",
        "my mother", "my mom", "mother's name", "mom's name", "my favorite song", "my fav song"
    ]):
        pm = get_profile_manager()


        # Specific key queries (HARDWARE DISK LOOKUP FIRST)
        keys_to_check = [
            "mother_name", "mother's name", "mom's name", "mother", "mom",
            "favorite_song", "favorite song", "fav song", "song",
            "address", "location", "city", "state", "name", "phone", "email", "job", "college", "school", "hometown"
        ]
        for key in keys_to_check:
            if key in raw or (key == "address" and ("where do i live" in raw or "where i live" in raw or "address" in raw)):
                val = pm.recall_user_memory(key)
                display_key = "mother's name" if key in ["mother_name", "mother", "mom", "mother's name", "mom's name"] else key
                if val:
                    reply = f"Yes Harsha, your {display_key} is {val}."
                    print(f"[ROUTER] Hardware Memory hit: {reply}")
                    return True, reply
                else:
                    reply = f"I do not have your {display_key} saved yet, Harsha. Please tell me your {display_key} so I can store it."
                    print(f"[ROUTER] Memory miss: {reply}")
                    return True, reply

        # Fall back to general memory listing
        user_mem = pm.get_all_user_memory()
        notes = pm.get_notes()
        parts = []
        if user_mem:
            parts.append("Profile: " + ", ".join(f"{k}: {v}" for k, v in user_mem.items()))
        if notes:
            parts.append("Notes:\n- " + "\n- ".join(notes))
        if parts:
            reply = "Here's what I remember, Harsha:\n" + "\n".join(parts)
            return True, reply
        reply = "I do not have your memory saved yet. Please tell me your address or details so I can store it."
        return True, reply

    # ── Screenshot ───────────────────────────────────────────────────────────────
    if "screenshot" in raw or "take a screen" in raw:
        from commands_daily import screenshot
        return True, screenshot()

    # ── VS Code & GitHub ──────────────────────────────────────────────────────
    if any(k in raw for k in ["vs code", "vscode", "visual studio code", "open code"]):
        execute("code")
        return True, "Opening VS Code for you, Harsha!"

    if "github" in raw:
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
        try:
            from agent import ultron_agent
            _, agent_response = ultron_agent.process_task(task)
            if agent_response:
                replies.append(agent_response)
        except Exception as ag_err:
            print(f"[ROUTER] Agent fallback: {ag_err}")

    if replies:
        return True, " ".join(replies)

    # Universal Task Execution Engine fallback
    from modules.universal_executor import execute_universal_task
    univ_reply = execute_universal_task(command)
    return True, univ_reply