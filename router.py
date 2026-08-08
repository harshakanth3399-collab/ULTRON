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
SLEEP_TIMEOUT = 15 * 60  # 15 minutes


def process(command: str):
    global AWAKE, LAST_ACTIVITY

    raw_command = command.lower().strip()
    if not raw_command:
        return True, None

    LAST_ACTIVITY = time.time()

    if raw_command == "intruder_detected":
        return True, "Get lost! This is Harsha's computer. You are NOT authorized to talk to me!"

    # Direct memory commands
    if raw_command.startswith("remember that"):
        note = raw_command.replace("remember that", "").strip()
        remember("note", note)
        return True, f"Got it, Harsha. I've stored that in your personal memory: '{note}'"

    if "what do you remember" in raw_command or "show my notes" in raw_command:
        pm = get_profile_manager()
        notes = pm.get_notes()
        if notes:
            notes_fmt = "\n- ".join(notes)
            return True, f"Here is what I remember for you, Harsha:\n- {notes_fmt}"
        return True, "Your personal memory is clear right now, Harsha."

    if "train model" in raw_command or "train ultron" in raw_command or "build model" in raw_command:
        from modules.memory.trainer import train_local_model
        success, msg = train_local_model()
        if success:
            return True, f"Local model training complete, Harsha! ULTRON is now running on your custom 'ultron-harsha' model weights."
        return True, f"Training note: {msg}"

    if "update ultron" in raw_command or "check update" in raw_command or "auto update" in raw_command:
        from modules.updater import check_and_apply_safe_updates
        success, msg = check_and_apply_safe_updates()
        return True, msg

    if "volume" in raw_command or "system status" in raw_command or "battery" in raw_command or "cpu" in raw_command:
        from core.system_automation import execute_system_command
        sys_res = execute_system_command(raw_command)
        if sys_res:
            return True, sys_res

    if "connect phone" in raw_command or "mobile link" in raw_command or "phone link" in raw_command:
        from web_server import get_local_ip, PORT
        ip = get_local_ip()
        return True, f"To connect your phone, Harsha: Open your phone browser and go to http://{ip}:{PORT}"

    if "check photos" in raw_command or "my photos" in raw_command:
        from modules.vision import check_new_photos
        photo_msg = check_new_photos()
        if photo_msg:
            return True, photo_msg
        return True, "No new uploaded photos in data/my_photos/ right now, Harsha."

    if raw_command.startswith("search the web for") or raw_command.startswith("search web for") or raw_command.startswith("search for"):
        from modules.internet import search_web_live
        query = raw_command.replace("search the web for", "").replace("search web for", "").replace("search for", "").strip()
        web_info = search_web_live(query)
        if web_info:
            ai_summary = ask_ai(f"Based on these live web search results for '{query}', answer Harsha directly in 1-2 short sentences:\n{web_info}")
            return True, ai_summary
        return True, f"I searched the web for '{query}', Harsha, but found no recent updates."

    corrected_cmd = correct(raw_command)
    tasks = plan(corrected_cmd)
    replies = []

    for task in tasks:
        intent = detect_intent(task)

        if intent == "EXIT":
            return False, "Always here for you, Harsha. Catch you later, brother."

        if intent in ["OPEN_APP", "GOOGLE", "YOUTUBE", "PLAY_MUSIC"]:
            executed = execute(task)
            if executed:
                replies.append("On it, Harsha.")
            continue

        ai_response = ask_ai(task)
        if ai_response:
            replies.append(ai_response)

    if replies:
        return True, "\n".join(replies)

    return True, None