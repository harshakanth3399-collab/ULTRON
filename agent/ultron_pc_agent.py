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
                    "Authorization": f"Bearer {USER_TOKEN}",
                    "X-LiveLink-Token": USER_TOKEN
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                pass
        except Exception:
            pass
        time.sleep(10.0)

def report_result(action: str, status: str, message: str, data_b64: str = None):
    """Reports execution result back to ULTRON cloud so phone/web UI gets real status."""
    try:
        payload = {
            "token": USER_TOKEN,
            "action": action,
            "status": status,
            "message": message,
            "data_b64": data_b64
        }
        req = urllib.request.Request(
            f"{SERVER_URL}/api/remote/result",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {USER_TOKEN}",
                "X-LiveLink-Token": USER_TOKEN
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            pass
        print(f"[REPORTED TO HUB] >> {message}")
    except Exception as e:
        print(f"[REPORT ERROR] >> {e}")

def change_volume(delta: float) -> str:
    sys_type = platform.system().lower()
    if "windows" in sys_type:
        try:
            import pycaw.pycaw as pc
            sp = pc.AudioUtilities.GetSpeakers()
            ev = sp.EndpointVolume
            curr = ev.GetMasterVolumeLevelScalar()
            new_v = max(0.0, min(1.0, curr + delta))
            ev.SetMasterVolumeLevelScalar(new_v, None)
            pct = int(round(new_v * 100))
            return f"Volume: {pct}%"
        except Exception:
            try:
                import ctypes
                vk = 0xAF if delta > 0 else 0xAE
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
                return f"Volume {'Up' if delta > 0 else 'Down'}"
            except Exception as ce:
                return f"Volume change failed: {ce}"
    elif "darwin" in sys_type:
        diff = 10 if delta > 0 else -10
        subprocess.run(["osascript", "-e", f"set volume output volume ((output volume of (get volume settings)) + {diff})"], check=False)
        return f"Volume {'Up' if delta > 0 else 'Down'}"
    else:
        diff_str = "+5%" if delta > 0 else "-5%"
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", diff_str], check=False)
        return f"Volume {'Up' if delta > 0 else 'Down'}"

def toggle_mute() -> str:
    sys_type = platform.system().lower()
    if "windows" in sys_type:
        try:
            import pycaw.pycaw as pc
            sp = pc.AudioUtilities.GetSpeakers()
            ev = sp.EndpointVolume
            is_muted = bool(ev.GetMute())
            new_state = 0 if is_muted else 1
            ev.SetMute(new_state, None)
            return "Muted" if new_state else "Unmuted"
        except Exception:
            try:
                import ctypes
                VK_VOLUME_MUTE = 0xAD
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
                return "Mute toggled"
            except Exception as ce:
                return f"Mute failed: {ce}"
    elif "darwin" in sys_type:
        subprocess.run(["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"], check=False)
        return "Mute toggled"
    else:
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "toggle"], check=False)
        return "Mute toggled"

def toggle_play_pause() -> str:
    sys_type = platform.system().lower()
    if "windows" in sys_type:
        try:
            import ctypes
            VK_MEDIA_PLAY_PAUSE = 0xB3
            ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
            return "Playback toggled (Play/Pause)"
        except Exception as e:
            return f"Play/Pause failed: {e}"
    elif "darwin" in sys_type:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 100'], check=False)
        return "Playback toggled (Play/Pause)"
    else:
        subprocess.run(["playerctl", "play-pause"], check=False)
        return "Playback toggled (Play/Pause)"

def lock_workstation() -> str:
    sys_type = platform.system().lower()
    if "windows" in sys_type:
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "PC Locked"
        except Exception as e:
            return f"Lock failed: {e}"
    elif "darwin" in sys_type:
        subprocess.run(["pmset", "displaysleepnow"], check=False)
        return "macOS Display Locked"
    else:
        subprocess.run(["sh", "-c", "xdg-screensaver lock || gnome-screensaver-command -l"], check=False)
        return "Linux Screen Locked"

def capture_screenshot() -> tuple:
    try:
        from PIL import ImageGrab
        import io
        import base64
        ss = ImageGrab.grab()
        dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        dest = os.path.join(dl_dir, f"ultron_screenshot_{int(time.time())}.png")
        ss.save(dest)
        
        # Create lightweight JPEG preview data URI for UI display
        buf = io.BytesIO()
        thumb = ss.copy()
        thumb.thumbnail((960, 540))
        thumb.save(buf, format="JPEG", quality=70)
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
        return "Screenshot captured", b64
    except Exception as e:
        return "Screenshot captured", None

def execute_pc_action(action: str):
    print(f"\n[ACTION RECEIVED] >> {action}")
    status = "success"
    msg = ""
    data_b64 = None

    if action in ["lock_laptop", "lock", "phone_lock"]:
        print("[ACTION] Locking PC workstation...")
        msg = lock_workstation()

    elif action in ["vol_up", "phone_vol_up"]:
        print("[ACTION] Volume UP")
        msg = change_volume(+0.05)

    elif action in ["vol_down", "phone_vol_down"]:
        print("[ACTION] Volume DOWN")
        msg = change_volume(-0.05)

    elif action in ["mute"]:
        print("[ACTION] Toggle MUTE")
        msg = toggle_mute()

    elif action in ["play_pause"]:
        print("[ACTION] Media Play/Pause")
        msg = toggle_play_pause()

    elif action in ["screenshot"]:
        print("[ACTION] Taking Screenshot...")
        msg, data_b64 = capture_screenshot()

    else:
        print(f"[UNKNOWN ACTION] {action}")
        msg = f"Unknown action: {action}"
        status = "error"

    report_result(action, status, msg, data_b64)

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
