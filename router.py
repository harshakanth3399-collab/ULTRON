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