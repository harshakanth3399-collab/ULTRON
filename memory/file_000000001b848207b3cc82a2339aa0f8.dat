def detect_intent(command):

    command = command.lower()

    # Exit
    if "exit ultron" in command:
        return "EXIT"

    # Music
    if "spotify" in command or "play" in command:
        return "PLAY_MUSIC"

    # YouTube
    if "youtube" in command:
        return "YOUTUBE"

    # Google
    if "google" in command or "search" in command:
        return "GOOGLE"

    # Windows Apps
    if any(app in command for app in [
        "calculator",
        "calc",
        "notepad",
        "chrome",
        "paint",
        "cmd",
        "terminal"
    ]):
        return "OPEN_APP"

    # Default
    return "AI_CHAT"