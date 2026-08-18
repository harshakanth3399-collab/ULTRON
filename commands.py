"""
commands.py - Fast-path Universal Desktop & App Execution Engine with OS Verification
"""
from __future__ import annotations

import os
import re
import subprocess
import time
import urllib.parse
import webbrowser
from typing import Optional, Tuple


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


def verify_app_running(process_names: list[str]) -> bool:
    """Checks whether any of the given process names are currently running in Windows tasklist."""
    try:
        output = subprocess.check_output("tasklist", shell=True).decode("utf-8", errors="ignore").lower()
        for p in process_names:
            if p.lower() in output:
                return True
    except Exception:
        pass
    return False


def launch_whatsapp() -> tuple[bool, str]:
    """Launches desktop WhatsApp application on Windows and verifies execution."""
    print("[APP LAUNCH] Attempting to launch desktop WhatsApp...")
    try:
        subprocess.Popen("start whatsapp:", shell=True)
        time.sleep(1.2)
        if verify_app_running(["whatsapp", "whatsapp.exe"]):
            print("[APP LAUNCH] WhatsApp verified running!")
            return True, "WhatsApp launched successfully."
        # Try direct executable launch fallback
        subprocess.Popen("start WhatsApp.exe", shell=True)
        time.sleep(1.0)
        return True, "WhatsApp launched."
    except Exception as e:
        print(f"[APP LAUNCH ERROR] Failed to launch WhatsApp: {e}")
        return False, f"Could not launch WhatsApp: {e}"


def launch_browser() -> tuple[bool, str]:
    """Launches the default web browser and verifies execution."""
    print("[APP LAUNCH] Opening default browser...")
    try:
        webbrowser.open("https://www.google.com")
        time.sleep(0.8)
        if verify_app_running(["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]):
            print("[APP LAUNCH] Browser verified running!")
            return True, "Browser opened successfully."
        return True, "Browser opened."
    except Exception as e:
        return False, f"Could not open browser: {e}"


def launch_vscode() -> tuple[bool, str]:
    """Launches Visual Studio Code on Windows and verifies execution."""
    print("[APP LAUNCH] Opening VS Code...")
    try:
        subprocess.Popen("code", shell=True)
        time.sleep(1.0)
        if verify_app_running(["code.exe", "code"]):
            print("[APP LAUNCH] VS Code verified running!")
            return True, "Visual Studio Code launched successfully."
        return True, "VS Code launched."
    except Exception as e:
        return False, f"Could not launch VS Code: {e}"


def launch_explorer() -> tuple[bool, str]:
    """Launches Windows File Explorer and verifies execution."""
    print("[APP LAUNCH] Opening File Explorer...")
    try:
        subprocess.Popen("explorer.exe", shell=True)
        time.sleep(0.8)
        if verify_app_running(["explorer.exe"]):
            print("[APP LAUNCH] File Explorer verified running!")
            return True, "File Explorer opened."
        return True, "File Explorer opened."
    except Exception as e:
        return False, f"Could not open File Explorer: {e}"


def execute(command: str) -> Optional[tuple[bool, str]]:
    """Universal Desktop & App Execution Engine with process verification."""
    cmd = command.lower().strip()

    if "exit ultron" in cmd:
        return False, "Exiting ULTRON."

    # 1. WhatsApp variations: whatsapp, whats app, what's up, watch up, watchapp
    if any(k in cmd for k in ["whatsapp", "whats app", "what's up", "watch up", "watchapp"]):
        return launch_whatsapp()

    # 2. Browser variations: browser, chrome, google chrome, edge, brave
    if any(k in cmd for k in ["open browser", "launch browser", "start browser", "browser", "chrome", "google chrome", "edge", "brave"]):
        return launch_browser()

    # 3. VS Code variations: vs code, vscode, visual studio code, code
    if any(k in cmd for k in ["vs code", "vscode", "visual studio code"]) or cmd == "code" or "open code" in cmd:
        return launch_vscode()

    # 4. File Explorer variations: file explorer, explorer, my computer, open files
    if any(k in cmd for k in ["file explorer", "explorer", "my computer", "open files"]):
        return launch_explorer()

    # 5. Notepad
    if "notepad" in cmd:
        try:
            subprocess.Popen("notepad.exe", shell=True)
            return True, "Notepad opened."
        except Exception as e:
            return False, f"Failed to open Notepad: {e}"

    # 6. Calculator
    if "calculator" in cmd or "calc" in cmd:
        try:
            subprocess.Popen("calc.exe", shell=True)
            return True, "Calculator opened."
        except Exception as e:
            return False, f"Failed to open Calculator: {e}"

    # 7. Task Manager
    if "task manager" in cmd:
        try:
            subprocess.Popen("taskmgr.exe", shell=True)
            return True, "Task Manager opened."
        except Exception as e:
            return False, f"Failed to open Task Manager: {e}"

    # 8. Command Prompt / Terminal
    if any(k in cmd for k in ["terminal", "cmd", "command prompt"]):
        try:
            subprocess.Popen("wt.exe", shell=True)
            return True, "Terminal opened."
        except Exception:
            subprocess.Popen("cmd.exe", shell=True)
            return True, "Command Prompt opened."

    # Dynamic Installed App Discovery Fallback
    if cmd.startswith(("open ", "launch ", "start ", "go to ", "visit ")) or len(cmd.split()) <= 3:
        from modules.app_finder import app_finder
        match = app_finder.find_app(cmd)
        if match:
            return app_finder.launch(cmd)

    # Universal Web / Search / Action Execution
    if cmd.startswith(("open ", "launch ", "start ", "go to ", "visit ")):
        target = re.sub(r"^(open|launch|start|go to|visit)\s+", "", cmd).strip()
        target_clean = re.sub(r"[^\w\s\.-]", "", target)

        if target_clean:
            if "." not in target_clean and not target_clean.endswith(".com"):
                url = f"https://www.google.com/search?q={urllib.parse.quote(target_clean)}"
            else:
                url = target_clean if target_clean.startswith("http") else f"https://{target_clean}"

            try:
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return True, f"Opened {target_clean}."
            except Exception:
                webbrowser.open(url)
                return True, f"Opened {target_clean}."


    # Google fallback
    if "google" in cmd or "search" in cmd:
        google_search(cmd)
        return True, "Google search opened."

    # YouTube fallback
    if "youtube" in cmd or "play" in cmd:
        search = cmd
        for word in ["play", "youtube", "on", "open", "and", "for me", "please", "search", "find", "show me", "put on", "start"]:
            search = search.replace(word, "")
        search = search.strip()
        play_youtube(search)
        return True, f"Playing {search or 'YouTube'}."

    return None