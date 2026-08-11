"""
doc_trainer.py - ULTRON Document & File Auto-Training Subsystem
Scans memory/user_documents/ folder and automatically trains ULTRON on any dropped
PDF, TXT, DOCX, Python, or Markdown files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

DOCS_DIR = Path(__file__).parent.parent.parent / "memory" / "user_documents"
SEMANTIC_STORE_PATH = Path(__file__).parent.parent.parent / "memory" / "semantic_vector_store.json"


def auto_index_user_documents() -> str:
    """Scans memory/user_documents/ and indexes any new documents into vector memory."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = [f for f in DOCS_DIR.glob("*") if f.is_file()]

    if not files:
        return f"No files found in '{DOCS_DIR}'. Drop any .txt, .pdf, .md, or .py files there to train ULTRON!"

    # Load semantic store
    store_data = {}
    if SEMANTIC_STORE_PATH.exists():
        try:
            with open(SEMANTIC_STORE_PATH, "r", encoding="utf-8") as f:
                store_data = json.load(f)
        except Exception:
            store_data = {}

    if "documents" not in store_data:
        store_data["documents"] = []

    indexed_count = 0
    for file in files:
        try:
            content = ""
            if file.suffix.lower() in [".txt", ".md", ".py", ".json", ".js", ".html"]:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            if content and len(content.strip()) > 10:
                store_data["documents"].append({
                    "title": file.name,
                    "content": content[:1500],
                    "source": "user_documents"
                })
                indexed_count += 1
        except Exception as e:
            print(f"[DOC TRAINER ERROR] {file.name}: {e}")

    with open(SEMANTIC_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store_data, f, indent=2, ensure_ascii=False)

    return f"Indexed {indexed_count} documents from your memory/user_documents folder into ULTRON's memory!"
