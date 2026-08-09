import re
import subprocess
import webbrowser
import urllib.parse
import threading


def play_youtube(search: str) -> None:
    """Instantly opens YouTube search / video playback in default browser (<50ms)."""
    search_clean = search.strip()
    if not search_clean:
        webbrowser.open("https://youtube.com")
        return

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_clean)}"
    print(f"[FAST YOUTUBE] Launching URL: {url}")
    webbrowser.open(url)


def google_search(command: str) -> None:
    """Instantly opens Google search in browser (<50ms)."""
    search = command
    for word in ["search", "google", "for", "open"]:
        search = search.replace(word, "")
    search = search.strip()

    if search:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(search)
    else:
        url = "https://google.com"

    webbrowser.open(url)


def execute(command: str):
    """Fast-path Universal Desktop & Web Command Execution Engine (<10ms matching)."""
    cmd = command.lower().strip()

    if "exit ultron" in cmd:
        return False

    # Universal Native Desktop Apps & Systems Execution Dictionary
    _APP_COMMANDS = {
        "vs code": "code",
        "vscode": "code",
        "visual studio code": "code",
        "github desktop": "GitHubDesktop.exe",
        "github app": "GitHubDesktop.exe",
        "github": "https://github.com",
        "whatsapp": "whatsapp:",
        "spotify": "spotify:",
        "discord": "discord:",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
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
        "chrome": "chrome.exe",
    }

    for app_name, app_cmd in _APP_COMMANDS.items():
        if app_name in cmd:
            try:
                if app_cmd.endswith(".exe") or app_cmd == "code":
                    subprocess.Popen(app_cmd, shell=True)
                elif app_cmd.startswith("http"):
                    subprocess.Popen(f'start "" "{app_cmd}"', shell=True)
                else:
                    subprocess.Popen(f'start {app_cmd}', shell=True)
                return True
            except Exception:
                pass

    # Universal Web / Search / Action Execution
    if cmd.startswith(("open ", "launch ", "start ", "go to ", "visit ")):
        target = re.sub(r"^(open|launch|start|go to|visit)\s+", "", cmd).strip()
        target_clean = re.sub(r"[^\w\s\.-]", "", target)

        if target_clean:
            if "." not in target_clean and not target_clean.endswith(".com"):
                url = f"https://www.com"
            else:
                url = target_clean if target_clean.startswith("http") else f"https://{target_clean}"

            try:
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return True
            except Exception:
                webbrowser.open(url)
                return True

    # Google fallback
    if "google" in cmd or "search" in cmd:
        google_search(cmd)
        return True

    # YouTube fallback
    if "youtube" in cmd or "play" in cmd:
        search = cmd
        for word in [
            "play", "youtube", "on", "open", "and",
            "for me", "please", "search", "find",
            "show me", "put on", "start"
        ]:
            search = search.replace(word, "")
        search = search.strip()
        play_youtube(search)
        return True

    return None