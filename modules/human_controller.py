"""
modules/human_controller.py - Zero-dependency Native Windows Screen & Human Laptop Control Engine

Enables ULTRON to act like a real human operating the computer:
  1. Screen Vision & Button Clicker: Locates buttons, text, and links on screen and clicks them.
  2. Smooth Human Mouse Movement: Fluid cursor gliding with realistic velocity curves.
  3. Hands-Free Keyboard Typing: Direct Unicode text injection into active input fields.
  4. Keyboard Shortcuts: Enter, Tab, Copy, Paste, Close Tab, New Tab, Show Desktop, Switch App.
  5. Page Navigation: Natural scrolling up and down.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from typing import Optional, Tuple

# ── Windows API Constants ──────────────────────────────────────────────────────
user32 = ctypes.windll.user32

# Mouse flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x000C
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

# Keyboard flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1

# Virtual Key Codes
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_BACK = 0x08
VK_DELETE = 0x2E
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_F11 = 0x7A


# ── ctypes Structure Definitions for SendInput ─────────────────────────────────
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
            ("hi", HARDWAREINPUT),
        ]

    _anonymous_ = ("_input",)
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


# ── Human Controller Core Engine ───────────────────────────────────────────────

class HumanController:
    """Provides complete, human-like hands-free control of the Windows desktop."""

    def __init__(self) -> None:
        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)

    # ── Mouse Control ─────────────────────────────────────────────────────────

    def get_cursor_pos(self) -> Tuple[int, int]:
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return int(pt.x), int(pt.y)

    def move_to(self, target_x: int, target_y: int, smooth: bool = True) -> None:
        """Smoothly glides cursor to (target_x, target_y) with realistic human motion."""
        target_x = max(0, min(target_x, self.screen_w - 1))
        target_y = max(0, min(target_y, self.screen_h - 1))

        if not smooth:
            user32.SetCursorPos(target_x, target_y)
            return

        start_x, start_y = self.get_cursor_pos()
        steps = 18
        dx = (target_x - start_x) / steps
        dy = (target_y - start_y) / steps

        for i in range(1, steps + 1):
            # Gentle sinusoidal easing
            progress = i / steps
            t = 0.5 - 0.5 * ctypes.c_float(progress * 3.141592).value
            cur_x = int(start_x + (target_x - start_x) * progress)
            cur_y = int(start_y + (target_y - start_y) * progress)
            user32.SetCursorPos(cur_x, cur_y)
            time.sleep(0.008)

        user32.SetCursorPos(target_x, target_y)

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Clicks at (x, y) or at current cursor position."""
        if x is not None and y is not None:
            self.move_to(x, y, smooth=True)
            time.sleep(0.06)

        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        self.click(x, y)
        time.sleep(0.08)
        self.click()

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            self.move_to(x, y, smooth=True)
            time.sleep(0.06)

        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def scroll(self, clicks: int) -> None:
        """Scrolls wheel: positive for UP, negative for DOWN."""
        wheel_delta = clicks * 120
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, wheel_delta, 0)

    # ── Keyboard Typing ───────────────────────────────────────────────────────

    def type_text(self, text: str) -> None:
        """Types Unicode text directly into the active foreground window/box."""
        if not text:
            return

        for char in text:
            code = ord(char)
            # Send character down
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki.wVk = 0
            inp_down.ki.wScan = code
            inp_down.ki.dwFlags = KEYEVENTF_UNICODE
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

            # Send character up
            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki.wVk = 0
            inp_up.ki.wScan = code
            inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

            time.sleep(0.012)

    def press_key(self, key_name: str) -> bool:
        """Presses an individual functional keyboard key."""
        k = key_name.lower().strip()
        vk_map = {
            "enter": VK_RETURN,
            "return": VK_RETURN,
            "tab": VK_TAB,
            "escape": VK_ESCAPE,
            "esc": VK_ESCAPE,
            "space": VK_SPACE,
            "backspace": VK_BACK,
            "delete": VK_DELETE,
            "up": VK_UP,
            "down": VK_DOWN,
            "left": VK_LEFT,
            "right": VK_RIGHT,
            "fullscreen": VK_F11,
            "f11": VK_F11,
        }
        vk = vk_map.get(k)
        if not vk:
            return False

        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return True

    def press_shortcut(self, shortcut_name: str) -> bool:
        """Executes common human keyboard shortcuts."""
        sc = shortcut_name.lower().strip()

        def _combo(mod: int, key_char: str):
            vk = ord(key_char.upper())
            user32.keybd_event(mod, 0, 0, 0)
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.04)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(mod, 0, KEYEVENTF_KEYUP, 0)

        if sc in ("copy", "copy that", "copy this"):
            _combo(VK_CONTROL, "C")
            return True
        elif sc in ("paste", "paste here", "paste this"):
            _combo(VK_CONTROL, "V")
            return True
        elif sc in ("select all", "select-all", "select everything"):
            _combo(VK_CONTROL, "A")
            return True
        elif sc in ("undo", "undo that"):
            _combo(VK_CONTROL, "Z")
            return True
        elif sc in ("close tab", "close this tab"):
            _combo(VK_CONTROL, "W")
            return True
        elif sc in ("new tab", "open new tab"):
            _combo(VK_CONTROL, "T")
            return True
        elif sc in ("switch app", "switch window", "next window"):
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_TAB, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            return True
        elif sc in ("show desktop", "minimize all", "desktop"):
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(ord("D"), 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(ord("D"), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            return True
        elif sc in ("lock laptop", "lock pc", "lock computer"):
            user32.LockWorkStation()
            return True

        return False

    # ── Screen Button Finder & Clicker ────────────────────────────────────────

    def find_and_click_button(self, target_label: str) -> Tuple[bool, str]:
        """
        Scans screen elements using Microsoft UIAutomation, finds the button/link/text,
        smoothly glides the mouse cursor to its center, and clicks it.
        100% Free, local, zero cloud dependencies.
        """
        clean_target = target_label.strip().strip("'\"").lower()
        if not clean_target:
            return False, "No button or element specified."

        ps_script = f"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$target = '{clean_target}'
$desktop = [System.Windows.Automation.AutomationElement]::RootElement

# Search focused window first for maximum responsiveness
$fg = [System.Windows.Automation.AutomationElement]::FocusedElement
$scope = [System.Windows.Automation.TreeScope]::Descendants
$cond = [System.Windows.Automation.Condition]::TrueCondition

$found = $null

if ($fg) {{
    $parent = [System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($fg)
    $searchRoot = if ($parent) {{ $parent }} else {{ $fg }}
    $elems = $searchRoot.FindAll($scope, $cond)
    foreach ($el in $elems) {{
        $name = $el.Current.Name
        if ($name -and $name.ToLower().Contains($target)) {{
            $r = $el.Current.BoundingRectangle
            if ($r.Width -gt 8 -and $r.Height -gt 8) {{
                $found = $r
                break
            }}
        }}
    }}
}}

# If not found in focused window, search full desktop
if (-not $found) {{
    $elems = $desktop.FindAll($scope, $cond)
    foreach ($el in $elems) {{
        $name = $el.Current.Name
        if ($name -and $name.ToLower().Contains($target)) {{
            $r = $el.Current.BoundingRectangle
            if ($r.Width -gt 8 -and $r.Height -gt 8) {{
                $found = $r
                break
            }}
        }}
    }}
}}

if ($found) {{
    $cx = [int]($found.X + $found.Width / 2)
    $cy = [int]($found.Y + $found.Height / 2)
    Write-Output "$cx,$cy"
}} else {{
    Write-Output 'NOT_FOUND'
}}
"""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            out = res.stdout.strip()
            if out and "NOT_FOUND" not in out and "," in out:
                parts = out.split("\n")[-1].strip().split(",")
                cx, cy = int(parts[0]), int(parts[1])
                print(f"[HUMAN CONTROLLER] Located '{clean_target}' at ({cx}, {cy}). Moving and clicking...")
                self.click(cx, cy)
                return True, f"Clicked '{target_label}' at coordinates ({cx}, {cy})."
            else:
                return False, f"Could not find '{target_label}' on the current screen."
        except Exception as e:
            print(f"[HUMAN CONTROLLER ERROR] {e}")
            return False, f"Screen element search failed: {e}"


# Global singleton
human_controller = HumanController()
