import subprocess
import webbrowser
import urllib.parse
import yt_dlp


# -----------------------------
# Open YouTube Video
# -----------------------------
def play_youtube(search):

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch10"
    }


    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(search, download=False)
            videos = info["entries"]

            best_video = None
            best_score = -1

            for video in videos:

                score = 0

                title = video.get("title", "").lower()
                uploader = video.get("uploader", "").lower()

                for word in search.lower().split():
                    if word in title:
                        score += 5

                if "official" in title:
                    score += 10

                if "trailer" in title:
                    score += 10

                if "official" in uploader:
                    score += 5

                if "t-series" in uploader:
                    score += 5

                if score > best_score:
                    best_score = score
                    best_video = video

            if best_video:
                print("▶ Playing:", best_video["title"])
                webbrowser.open(best_video["webpage_url"])
            else:
                webbrowser.open("https://youtube.com")

    except Exception as e:
        print("YouTube Error:", e)


# -----------------------------
# Google Search
# -----------------------------
def google_search(command):

    search = command

    for word in [
        "search",
        "google",
        "for",
        "open"
    ]:
        search = search.replace(word, "")

    search = search.strip()

    if search:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(search)
    else:
        url = "https://google.com"

    webbrowser.open(url)


# -----------------------------
# Execute Commands
# -----------------------------
def execute(command):

    command = command.lower().strip()

    # Exit
    if "exit ultron" in command:
        return False

    # Universal App & System Execution Dictionary
    _APP_COMMANDS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "command prompt": "cmd.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "paint": "mspaint.exe",
        "settings": "ms-settings:",
        "clock": "ms-clock:",
        "camera": "microsoft.windows.camera:",
        "explorer": "explorer.exe",
        "my computer": "explorer.exe",
    }

    for app_name, app_cmd in _APP_COMMANDS.items():
        if app_name in command:
            try:
                if app_cmd.endswith(".exe"):
                    subprocess.Popen(app_cmd)
                else:
                    subprocess.Popen(f'start "" "{app_cmd}"', shell=True)
                return True
            except Exception:
                pass

    # Universal Web / Search / Action Execution
    if command.startswith(("open ", "launch ", "start ", "go to ", "visit ")):
        target = re.sub(r"^(open|launch|start|go to|visit)\s+", "", command).strip()
        target_clean = re.sub(r"[^\w\s\.-]", "", target)

        if target_clean:
            # Common web shortcuts
            if "." not in target_clean and not target_clean.endswith(".com"):
                url = f"https://www.{target_clean.replace(' ', '')}.com"
            else:
                url = target_clean if target_clean.startswith("http") else f"https://{target_clean}"

            try:
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return True
            except Exception:
                webbrowser.open(url)
                return True

    # Google fallback
    if "google" in command or "search" in command:
        google_search(command)
        return True

    # YouTube fallback
    if "youtube" in command or "play" in command:
        search = command
        for word in [
            "play", "youtube", "on", "open", "and",
            "for me", "please", "search", "find",
            "show me", "put on", "start"
        ]:
            search = search.replace(word, "")
        search = search.strip()
        if search:
            play_youtube(search)
        else:
            webbrowser.open("https://youtube.com")
        return True

    return None