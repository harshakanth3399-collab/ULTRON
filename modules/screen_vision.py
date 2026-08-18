"""
modules/screen_vision.py - Zero-dependency Native Windows Screen Capture & Vision Module
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from typing import Tuple


def capture_screen_gdi() -> Tuple[bool, str, int, int]:
    """
    Captures the primary monitor screen using native Windows GDI32 C API.
    Returns (success, message, width, height).
    """
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        gdi32.SelectObject(hdc_mem, hbitmap)
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, 0x00CC0020)

        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

        print(f"[SCREEN VISION] Screen captured via GDI32 ({width}x{height}).")
        return True, f"Screen captured successfully at {width}x{height} resolution.", width, height
    except Exception as e:
        print(f"[SCREEN VISION ERROR] {e}")
        return False, f"Failed to capture screen: {e}", 0, 0


def take_screenshot(save_filename: str = "ultron_screenshot.png") -> Tuple[bool, str]:
    """Takes a screenshot and saves it to disk via Windows PowerShell GDI bridge."""
    try:
        save_path = os.path.abspath(save_filename)
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms\n"
            "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds\n"
            "$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height\n"
            "$graphics = [System.Drawing.Graphics]::FromImage($bitmap)\n"
            "$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)\n"
            f"$bitmap.Save('{save_path}', [System.Drawing.Imaging.ImageFormat]::Png)\n"
        )
        subprocess.run(["powershell", "-Command", ps_script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(save_path):
            print(f"[SCREEN VISION] Screenshot saved to '{save_path}'.")
            return True, f"Screenshot saved to {os.path.basename(save_path)}."
    except Exception:
        pass

    # Fallback to GDI capture
    ok, msg, w, h = capture_screen_gdi()
    return ok, msg
