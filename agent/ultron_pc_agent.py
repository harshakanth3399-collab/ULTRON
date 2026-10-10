#!/usr/bin/env python3
"""
ULTRON PC Companion Agent
Connects your laptop/desktop to the ULTRON Cloud Hub (https://ultron-omega-drab.vercel.app).
Enables secure Remote Control actions (Lock PC, Volume control, Play/Pause, Screenshot)
and synchronizes files directly to your Downloads folder.

Usage:
    python ultron_pc_agent.py
"""

import sys
import os
import time
import json
import platform
import urllib.request
import urllib.parse
import subprocess
import threading

SERVER_URL = os.environ.get("ULTRON_SERVER_URL", "https://ultron-omega-drab.vercel.app").rstrip("/")
USER_TOKEN = os.environ.get("ULTRON_TOKEN", "LIVELINK_MASTER_HARSHA")
DEVICE_NAME = f"{platform.node()} ({platform.system()})"

def send_heartbeat():
    while True:
        try:
            req = urllib.request.Request(
                f"{SERVER_URL}/api/remote/heartbeat",
                data=json.dumps({
                    "token": USER_TOKEN,
                    "device_name": DEVICE_NAME
                }).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {USER_TOKEN}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                pass
        except Exception as e:
            pass
        time.sleep(10.0)

def execute_pc_action(action: str):
    print(f"\n[ACTION RECEIVED] >> {action}")
    sys_type = platform.system().lower()

    if action in ["lock_laptop", "lock", "phone_lock"]:
        print("[ACTION] Locking PC workstation...")
        if "windows" in sys_type:
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                print("[SUCCESS] Windows Workstation Locked.")
            except Exception as e:
                print(f"[FAIL] Could not lock: {e}")
        elif "darwin" in sys_type:
            subprocess.run(["pmset", "displaysleepnow"], check=False)
            print("[SUCCESS] macOS Display Locked.")
        else:
            subprocess.run(["sh", "-c", "xdg-screensaver lock || gnome-screensaver-command -l"], check=False)
            print("[SUCCESS] Linux Screen Locked.")

    elif action in ["vol_up", "phone_vol_up"]:
        print("[ACTION] Volume UP")
        if "windows" in sys_type:
            try:
                import ctypes
                VK_VOLUME_UP = 0xAF
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
            except Exception:
                pass
        elif "darwin" in sys_type:
            subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"], check=False)

    elif action in ["vol_down", "phone_vol_down"]:
        print("[ACTION] Volume DOWN")
        if "windows" in sys_type:
            try:
                import ctypes
                VK_VOLUME_DOWN = 0xAE
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
            except Exception:
                pass
        elif "darwin" in sys_type:
            subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"], check=False)

    elif action in ["mute"]:
        print("[ACTION] Toggle MUTE")
        if "windows" in sys_type:
            try:
                import ctypes
                VK_VOLUME_MUTE = 0xAD
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            except Exception:
                pass
        elif "darwin" in sys_type:
            subprocess.run(["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"], check=False)

    elif action in ["play_pause"]:
        print("[ACTION] Media Play/Pause")
        if "windows" in sys_type:
            try:
                import ctypes
                VK_MEDIA_PLAY_PAUSE = 0xB3
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
            except Exception:
                pass

    elif action in ["screenshot"]:
        print("[ACTION] Taking Screenshot...")
        try:
            from PIL import ImageGrab
            ss = ImageGrab.grab()
            dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            dest = os.path.join(dl_dir, f"ultron_screenshot_{int(time.time())}.png")
            ss.save(dest)
            print(f"[SUCCESS] Saved screenshot to {dest}")
        except Exception as e:
            print(f"[NOTE] Screenshot requires pillow (pip install pillow): {e}")

    else:
        print(f"[UNKNOWN ACTION] {action}")

def poll_actions():
    while True:
        try:
            req = urllib.request.Request(
                f"{SERVER_URL}/api/poll_remote",
                headers={
                    "Authorization": f"Bearer {USER_TOKEN}",
                    "X-LiveLink-Token": USER_TOKEN
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("has_action"):
                    action = data.get("action", "")
                    if action:
                        execute_pc_action(action)
        except Exception:
            pass
        time.sleep(1.5)

def main():
    print("=" * 60)
    print("  ULTRON PC COMPANION AGENT - CONNECTED")
    print(f"  Hub: {SERVER_URL}")
    print(f"  Device: {DEVICE_NAME}")
    print("  Standing by for remote commands from phone & web HUD...")
    print("=" * 60)

    # Start background heartbeat thread
    t_hb = threading.Thread(target=send_heartbeat, daemon=True)
    t_hb.start()

    # Run polling loop
    try:
        poll_actions()
    except KeyboardInterrupt:
        print("\nULTRON PC Companion Agent shutting down. Farewell.")

if __name__ == "__main__":
    main()
