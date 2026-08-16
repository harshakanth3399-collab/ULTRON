"""
train_my_data.py - ULTRON One-Click Comprehensive Memory & Document Trainer

Trains ULTRON on:
  1. All exported ChatGPT chat logs (conversations.json)
  2. All dropped documents, PDFs, TXT, JSON, code, and notes in memory/user_documents/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from modules.memory.trainer import ingest_chatgpt_data
from modules.memory.doc_trainer import auto_index_user_documents

PROJECT_DIR = Path(__file__).parent
DOCS_DIR = PROJECT_DIR / "memory" / "user_documents"

print("=" * 70)
print("             ULTRON COMPREHENSIVE DATA & DOCUMENT TRAINER")
print("=" * 70)

# 1. Train from memory/user_documents/
print("\n[STEP 1] Scanning 'memory/user_documents/' directory...")
doc_result = auto_index_user_documents()
print(f" -> {doc_result}")

# 2. Check for ChatGPT conversations.json or root files
print("\n[STEP 2] Scanning project root for ChatGPT export & text files...")
target_file = PROJECT_DIR / "conversations.json"
if not target_file.exists():
    txt_files = list(PROJECT_DIR.glob("*.txt"))
    json_files = [
        f for f in PROJECT_DIR.glob("*.json")
        if f.name not in ["package.json", "tsconfig.json", "profile.json", "contacts.json", "semantic_vector_store.json"]
    ]
    if json_files:
        target_file = json_files[0]
    elif txt_files:
        target_file = txt_files[0]
    else:
        target_file = None

if target_file and target_file.exists():
    print(f" -> Found personal export file: '{target_file.name}'")
    ingest_msg = ingest_chatgpt_data(str(target_file))
    print(f" -> {ingest_msg}")
else:
    print(" -> No additional root ChatGPT export file found.")

print("\n" + "=" * 70)
print("TRAINING COMPLETE! ULTRON has indexed your memory data successfully.")
print("=" * 70)
