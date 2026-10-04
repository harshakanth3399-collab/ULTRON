"""
modules/cross_app_autopilot.py - ULTRON Microsoft UFO-style Cross-App Autopilot

Chains multi-step workflows across applications. For instance:
- Copies active window / browser content -> Generates intelligent summary -> Launches Notepad -> Types / saves the structured notes.
- Extracts screen data and compiles it to Desktop documents.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import time
from typing import Tuple

from ai import ask_ai
from modules.human_controller import human_controller
from modules.smart_clipboard import smart_clipboard


def summarize_active_app_to_notepad() -> Tuple[bool, str]:
    """
    Simulates human multi-app workflow:
    1. Selects all and copies text from active window.
    2. Uses AI to summarize the contents.
    3. Opens Notepad and pastes the structured summary.
    """
    # 1. Select all & copy
    human_controller.press_shortcut("copy")
    time.sleep(0.3)

    copied_text = smart_clipboard._get_current_clipboard_text().strip()
    if not copied_text or len(copied_text) < 15:
        return False, "Could not copy sufficient text from the active window to summarize."

    # 2. Summarize via Ask AI
    prompt = (
        "Summarize the following text extracted from the user's active window into clean, "
        "concise bullet points with key takeaways:\n\n" + copied_text[:4000]
    )
    summary = ask_ai(prompt)
    if not summary:
        summary = copied_text[:500]

    header = f"--- ULTRON AUTOPILOT SUMMARY [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] ---\n\n"
    final_note = header + summary + "\n\n--- END ---"

    # 3. Put summary in clipboard and launch Notepad
    smart_clipboard._set_clipboard_text(final_note)
    try:
        subprocess.Popen(["notepad.exe"])
        time.sleep(1.0)
        human_controller.press_shortcut("paste")
        return True, "Summarized the active page and pasted into a new Notepad document."
    except Exception as e:
        return False, f"Generated summary, but could not open Notepad: {e}"


def save_active_notes_to_desktop() -> Tuple[bool, str]:
    """
    Copies active selection or window and saves directly as a dated markdown file on Desktop.
    """
    copied_text = smart_clipboard._get_current_clipboard_text().strip()
    if not copied_text:
        human_controller.press_shortcut("copy")
        time.sleep(0.3)
        copied_text = smart_clipboard._get_current_clipboard_text().strip()

    if not copied_text:
        return False, "Please select or highlight text to save to your Desktop."

    from modules.system_paths import get_desktop_dir
    desktop_dir = str(get_desktop_dir())

    fname = f"Ultron_Notes_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    fpath = os.path.join(desktop_dir, fname)

    try:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"# ULTRON Captured Notes\nDate: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(copied_text)
            f.write("\n")
        return True, f"Saved notes directly to your Desktop as {fname}."
    except Exception as e:
        return False, f"Could not save file to Desktop: {e}"
