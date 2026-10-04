"""
modules/folder_organizer.py - ULTRON Voice-Driven Desktop & Downloads Folder Organizer

Categorizes and declutters messy folders into neat subfolders:
  - Documents (PDFs, Word docs, spreadsheets)
  - Images (Photos, screenshots, icons)
  - Installers (Executables, MSI packages)
  - Archives (ZIP, RAR, 7z)
  - Media (Videos, audio)
  - Code (Scripts, notebooks)
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Tuple

EXTENSION_CATEGORIES = {
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".rtf"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"],
    "Installers": [".exe", ".msi", ".iso", ".bat", ".cmd"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Media": [".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav", ".flac", ".m4a"],
    "Code": [".py", ".ipynb", ".js", ".html", ".css", ".json", ".sql", ".sh", ".cpp", ".java"],
}


def organize_folder(folder_path: str | Path | None = None) -> Tuple[bool, str]:
    """Organizes loose files in the specified folder into clean subfolders."""
    if folder_path is None:
        folder_path = Path.home() / "Downloads"

    target_dir = Path(folder_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        return False, f"Folder '{target_dir}' does not exist."

    moved_count = 0
    category_counts = {}

    for item in target_dir.iterdir():
        # Skip folders, shortcuts, temporary files, and system files
        if not item.is_file() or item.name.startswith((".", "~$")) or item.suffix.lower() == ".lnk":
            continue

        ext = item.suffix.lower()
        destination_cat = "Miscellaneous"

        for cat, ext_list in EXTENSION_CATEGORIES.items():
            if ext in ext_list:
                destination_cat = cat
                break

        dest_folder = target_dir / destination_cat
        dest_folder.mkdir(exist_ok=True)

        target_file = dest_folder / item.name
        # Avoid overwriting existing files with identical names
        if target_file.exists():
            base = item.stem
            target_file = dest_folder / f"{base}_{int(item.stat().st_mtime)}{ext}"

        try:
            shutil.move(str(item), str(target_file))
            moved_count += 1
            category_counts[destination_cat] = category_counts.get(destination_cat, 0) + 1
        except Exception:
            pass

    if moved_count == 0:
        return True, f"Your {target_dir.name} folder is already clean and organized, Harsha."

    details = ", ".join(f"{cnt} {cat.lower()}" for cat, cnt in category_counts.items())
    return True, f"Organized {moved_count} files in your {target_dir.name} folder into {details}."


def clean_desktop() -> Tuple[bool, str]:
    from modules.system_paths import get_desktop_dir
    desktop_dir = get_desktop_dir()
    return organize_folder(desktop_dir)


def clean_downloads() -> Tuple[bool, str]:
    from modules.system_paths import get_downloads_dir
    downloads_dir = get_downloads_dir()
    return organize_folder(downloads_dir)
