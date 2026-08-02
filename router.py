import time

from corrector import correct
from planner import plan
from intent import detect_intent
from commands import execute
from ai import ask_ai
from memory import remember, recall

# Wake Mode
AWAKE = False
LAST_ACTIVITY = 0
SLEEP_TIMEOUT = 15 * 60  # 15 minutes


def process(command):

    global AWAKE, LAST_ACTIVITY

    command = command.lower().strip()

    # Sleep after 15 minutes
    if AWAKE and (time.time() - LAST_ACTIVITY > SLEEP_TIMEOUT):
        AWAKE = False

    # Wake word
    if not AWAKE:

        if "hey ultron" not in command:
            return True, None

        AWAKE = True
        LAST_ACTIVITY = time.time()

        command = command.replace("hey ultron", "").strip()

        if command == "":
            return True, "Yes, Harsha?"

    LAST_ACTIVITY = time.time()

    command = correct(command)

    print(f"\nCorrected: {command}")

    tasks = plan(command)

    replies = []

    for task in tasks:

        intent = detect_intent(task)

        print(f"[Intent] {intent}")

        if intent == "EXIT":
            return False, "Goodbye Harsha."

        if task.startswith("remember that"):

            remember(
                "note",
                task.replace("remember that", "").strip()
            )

            replies.append("I'll remember that.")
            continue

        if "what do you remember" in task:

            note = recall("note")

            if note:
                replies.append(f"You asked me to remember: {note}")
            else:
                replies.append("I don't remember anything yet.")

            continue

        if intent in [
            "OPEN_APP",
            "GOOGLE",
            "YOUTUBE",
            "PLAY_MUSIC"
        ]:

            execute(task)
            continue

        replies.append(
            ask_ai(task)
        )

    if replies:
        return True, "\n".join(replies)

    return True, None