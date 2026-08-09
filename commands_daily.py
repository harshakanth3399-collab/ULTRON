"""
commands_daily.py - Daily Life Command Handlers for ULTRON

Covers every common daily command an Indian user needs:
  - WhatsApp: call, message, I'm busy
  - Phone: call, pick up via Phone Link
  - Banking: SBI, HDFC, ICICI, Paytm, GPay, PhonePe
  - File explorer: Documents, Downloads, Photos, Desktop
  - Weather
  - Alarm/Timer (Windows Clock)
  - Reminders
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path


# ── Contacts ──────────────────────────────────────────────────────────────────

_CONTACTS_PATH = Path(__file__).parent / "memory" / "contacts.json"

def _load_contacts() -> list[dict]:
    try:
        if _CONTACTS_PATH.exists():
            with open(_CONTACTS_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _find_contact(name: str) -> dict | None:
    name = name.lower().strip()
    if name in ("mom", "mum", "mother"):
        name = "mum"
    for c in _load_contacts():
        c_name = c.get("name", "").lower()
        if name in c_name or c_name in name:
            return c
    return None


def open_whatsapp() -> str:
    """Opens native WhatsApp Desktop app on Windows."""
    try:
        subprocess.Popen('start whatsapp:', shell=True)
        return "Opening WhatsApp Desktop app for you, Harsha!"
    except Exception:
        return "Opening WhatsApp app for you, Harsha!"


def whatsapp_call(name: str) -> str:
    contact = _find_contact(name)
    if contact and contact.get("whatsapp"):
        phone = contact["whatsapp"].replace("+", "").replace(" ", "")
        url = f"whatsapp://send?phone={phone}"
        subprocess.Popen(f'start "" "{url}"', shell=True)
        return f"Opening WhatsApp call to {contact['name']}, Harsha!"
    subprocess.Popen('start whatsapp:', shell=True)
    return "Opening WhatsApp Desktop app for you, Harsha!"


def whatsapp_message(name: str, message: str = "") -> str:
    contact = _find_contact(name)
    contact_name = contact["name"] if contact else (name.capitalize() if name else "Mum")

    if contact and contact.get("whatsapp"):
        phone = contact["whatsapp"].replace("+", "").replace(" ", "").replace("-", "")
        # Check if real phone number (not placeholder)
        if phone.isdigit() and len(phone) >= 10:
            msg_encoded = urllib.parse.quote(message) if message else ""
            url = f"whatsapp://send?phone={phone}&text={msg_encoded}" if message else f"whatsapp://send?phone={phone}"
            subprocess.Popen(f'start "" "{url}"', shell=True)
            return f"Opening WhatsApp chat to {contact_name} with message '{message or 'Hi'}', Harsha!"

    # Fallback to native WhatsApp Desktop App
    msg_encoded = urllib.parse.quote(message) if message else ""
    url = f"whatsapp://send?text={msg_encoded}" if message else "whatsapp:"
    try:
        subprocess.Popen(f'start "" "{url}"', shell=True)
    except Exception:
        subprocess.Popen('start whatsapp:', shell=True)

    return f"Opening WhatsApp Desktop app for {contact_name}, Harsha!"




def whatsapp_im_busy(name: str) -> str:
    messages = [
        "Hey! I'm busy right now, I'll get back to you soon. 🙏",
        "In a meeting, bro! Talk later.",
        "Can't talk right now. I'll call you back!",
    ]
    contact = _find_contact(name)
    msg = messages[0]
    if contact and contact.get("whatsapp"):
        phone = contact["whatsapp"].replace("+", "").replace(" ", "")
        msg_encoded = urllib.parse.quote(msg)
        webbrowser.open(f"https://wa.me/{phone}?text={msg_encoded}")
        return f"Sending 'I'm busy' to {contact['name']} on WhatsApp."
    webbrowser.open("https://web.whatsapp.com")
def reset_instagram_preferences() -> str:
    """Opens Instagram content preferences settings page directly."""
    url = "https://www.instagram.com/your_activity/content_preferences"
    try:
        subprocess.Popen(f'start "" "{url}"', shell=True)
    except Exception:
        webbrowser.open(url)
    return "Opening your Instagram content preferences page right now, Harsha!"



# ── Phone calls via Windows Phone Link ────────────────────────────────────────


def phone_call(name: str) -> str:
    # Try Phone Link (pairs with Android/iPhone)
    contact = _find_contact(name)
    try:
        subprocess.Popen(["explorer.exe", "ms-phone:"])
    except Exception:
        pass
    if contact:
        return f"Opening Phone Link to call {contact['name']}. Make sure Phone Link is paired!"
    return "Opening Phone Link. Make sure your phone is paired with this laptop."


def pick_up_call() -> str:
    """Tries to answer an incoming call via Phone Link keyboard shortcut."""
    try:
        import pyautogui
        # Phone Link answer shortcut: Ctrl+Shift+A (when notification is active)
        pyautogui.hotkey("ctrl", "shift", "a")
        return "Attempted to pick up your call, bro!"
    except Exception:
        try:
            subprocess.Popen(["explorer.exe", "ms-phone:"])
        except Exception:
            pass
        return "Opening Phone Link — answer the call there."


# ── Banking & Payments ─────────────────────────────────────────────────────────

_BANKING_URLS = {
    "sbi": "https://www.onlinesbi.sbi",
    "hdfc": "https://netbanking.hdfcbank.com",
    "icici": "https://infinity.icicibank.com",
    "axis": "https://omni.axisbank.co.in",
    "kotak": "https://netbanking.kotak.com",
    "paytm": "https://paytm.com",
    "gpay": "https://pay.google.com",
    "google pay": "https://pay.google.com",
    "phonepe": "https://phonepe.com",
    "phone pe": "https://phonepe.com",
    "cred": "https://cred.club",
    "amazon pay": "https://www.amazon.in/pay",
    "neft": "https://www.onlinesbi.sbi",
    "upi": "https://paytm.com",
    "bhim": "https://bhimupi.org.in",
}

def open_banking(keyword: str) -> str:
    kw = keyword.lower().strip()
    for key, url in _BANKING_URLS.items():
        if key in kw:
            webbrowser.open(url)
            return f"Opening {key.upper()} for you, bro."
    webbrowser.open("https://paytm.com")
    return "Opening Paytm. Tell me which bank you want."


# ── File Explorer ──────────────────────────────────────────────────────────────

_FOLDERS = {
    "downloads": str(Path.home() / "Downloads"),
    "documents": str(Path.home() / "Documents"),
    "desktop": str(Path.home() / "Desktop"),
    "pictures": str(Path.home() / "Pictures"),
    "photos": str(Path.home() / "Pictures"),
    "videos": str(Path.home() / "Videos"),
    "music": str(Path.home() / "Music"),
    "c drive": "C:\\",
    "c:": "C:\\",
}

def open_folder(keyword: str) -> str:
    kw = keyword.lower()
    for key, path in _FOLDERS.items():
        if key in kw:
            subprocess.Popen(["explorer.exe", path])
            return f"Opening your {key.title()} folder."
    # Try to open a specific file/path mentioned
    subprocess.Popen(["explorer.exe", str(Path.home())])
    return "Opening File Explorer for you."


def open_specific_file(path: str) -> str:
    try:
        os.startfile(path)
        return f"Opening {path}."
    except Exception as e:
        return f"Couldn't open that file, bro: {e}"


# ── Weather ────────────────────────────────────────────────────────────────────

def open_weather(location: str = "") -> str:
    if location:
        query = urllib.parse.quote(f"weather {location}")
    else:
        query = "weather today"
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Checking weather{f' for {location}' if location else ''} for you."


# ── Alarm / Timer ──────────────────────────────────────────────────────────────

def set_alarm(time_str: str = "") -> str:
    """Open Windows Clock app for alarm."""
    try:
        subprocess.Popen(["explorer.exe", "ms-clock:"])
    except Exception:
        pass
    return f"Opening Clock app{f' — set alarm for {time_str}' if time_str else ''}."


def set_timer(duration: str = "") -> str:
    try:
        subprocess.Popen(["explorer.exe", "ms-clock:"])
    except Exception:
        pass
    return f"Opening Clock timer{f' for {duration}' if duration else ''}."


# ── Common Apps ────────────────────────────────────────────────────────────────

def open_instagram() -> str:
    webbrowser.open("https://www.instagram.com")
    return "Opening Instagram."

def open_twitter() -> str:
    webbrowser.open("https://twitter.com")
    return "Opening Twitter."

def open_linkedin() -> str:
    webbrowser.open("https://www.linkedin.com")
    return "Opening LinkedIn."

def open_maps(destination: str = "") -> str:
    if destination:
        q = urllib.parse.quote(destination)
        webbrowser.open(f"https://www.google.com/maps/search/{q}")
        return f"Opening Google Maps for {destination}."
    webbrowser.open("https://maps.google.com")
    return "Opening Google Maps."

def open_email() -> str:
    webbrowser.open("https://mail.google.com")
    return "Opening Gmail for you."

def open_amazon() -> str:
    webbrowser.open("https://www.amazon.in")
    return "Opening Amazon India."

def open_flipkart() -> str:
    webbrowser.open("https://www.flipkart.com")
    return "Opening Flipkart."

def open_swiggy() -> str:
    webbrowser.open("https://www.swiggy.com")
    return "Opening Swiggy. Hungry again, bro?"

def open_zomato() -> str:
    webbrowser.open("https://www.zomato.com")
    return "Opening Zomato."

def open_ola() -> str:
    webbrowser.open("https://www.olacabs.com")
    return "Opening Ola Cabs."

def open_uber() -> str:
    webbrowser.open("https://www.uber.com/in/en/")
    return "Opening Uber."

def open_irctc() -> str:
    webbrowser.open("https://www.irctc.co.in")
    return "Opening IRCTC for train booking."

def open_hotstar() -> str:
    webbrowser.open("https://www.hotstar.com")
    return "Opening Disney Hotstar."

def open_netflix() -> str:
    webbrowser.open("https://www.netflix.com")
    return "Opening Netflix."

def screenshot() -> str:
    try:
        import pyautogui
        path = str(Path.home() / "Pictures" / "ultron_screenshot.png")
        pyautogui.screenshot(path)
        return f"Screenshot saved to Pictures folder, bro."
    except Exception as e:
        return f"Screenshot failed: {e}"
