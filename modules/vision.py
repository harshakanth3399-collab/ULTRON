"""Personal Photo & Image Analysis Module for ULTRON."""

from __future__ import annotations

import os
import glob


PHOTO_DIR = os.path.join("data", "my_photos")


def check_new_photos() -> str | None:
    """Scans for user uploaded photos in data/my_photos/ and generates a friendly prompt."""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    valid_exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    photos = []
    for ext in valid_exts:
        photos.extend(glob.glob(os.path.join(PHOTO_DIR, ext)))

    if photos:
        latest = max(photos, key=os.path.getmtime)
        filename = os.path.basename(latest)
        return f"Hey Harsha, I noticed you uploaded a new photo: '{filename}'. Want me to store or analyze it for you, bro?"

    return None
