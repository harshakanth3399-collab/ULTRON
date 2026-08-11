"""
train_my_data.py - ULTRON One-Click Personal ChatGPT Data Ingestion Script
Run this script to train ULTRON on your 1-year ChatGPT history export (conversations.json) or text notes!
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from modules.memory.trainer import ingest_chatgpt_data

PROJECT_DIR = Path(__file__).parent
target_file = PROJECT_DIR / "conversations.json"

if not target_file.exists():
    # Look for any .txt or .json files in project folder
    txt_files = list(PROJECT_DIR.glob("*.txt"))
    json_files = [f for f in PROJECT_DIR.glob("*.json") if f.name not in ["package.json", "tsconfig.json", "profile.json", "contacts.json", "semantic_vector_store.json"]]
    
    if json_files:
        target_file = json_files[0]
    elif txt_files:
        target_file = txt_files[0]
    else:
        print("=" * 70)
        print("ULTRON CHATGPT DATA TRAINER")
        print("=" * 70)
        print("Please place your exported 'conversations.json' file from OpenAI inside your ULTRON folder:")
        print(f" -> Path: {PROJECT_DIR}\\conversations.json")
        print("\nHow to get conversations.json from ChatGPT:")
        print(" 1. Go to https://chatgpt.com")
        print(" 2. Settings -> Data controls -> Export data -> Confirm")
        print(" 3. Download the zip file from your email and extract 'conversations.json' here!")
        print("=" * 70)
        sys.exit(0)

print(f"[TRAINER] Found personal data export file: '{target_file.name}'")
print("[TRAINER] Starting vector memory & SQLite database ingestion...")

result_msg = ingest_chatgpt_data(str(target_file))

print("=" * 70)
print(f"RESULT: {result_msg}")
print("=" * 70)
