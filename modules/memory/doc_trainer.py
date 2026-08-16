"""
doc_trainer.py - ULTRON Document & File Auto-Training Subsystem
Scans memory/user_documents/ folder and automatically trains ULTRON on any dropped
PDF, TXT, DOCX, Python, or Markdown files.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List

DOCS_DIR = Path(__file__).parent.parent.parent / "memory" / "user_documents"
SEMANTIC_STORE_PATH = Path(__file__).parent.parent.parent / "memory" / "semantic_vector_store.json"


def _text_to_vector(text: str) -> dict:
    words = [w.lower().strip() for w in re.findall(r"\w+", text) if len(w) > 2]
    if not words:
        return {}
    total = float(len(words))
    vec = {}
    for w in words:
        vec[w] = round(vec.get(w, 0.0) + (1.0 / total), 4)
    return vec


def auto_index_user_documents() -> str:
    """Scans memory/user_documents/ and indexes any new documents into vector memory."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = [f for f in DOCS_DIR.glob("*") if f.is_file()]

    if not files:
        return f"No files found in '{DOCS_DIR}'. Drop any .txt, .pdf, .md, or .py files there to train ULTRON!"

    # Load semantic store (handles both list and dict formats)
    store_list = []
    if SEMANTIC_STORE_PATH.exists():
        try:
            with open(SEMANTIC_STORE_PATH, "r", encoding="utf-8", errors="ignore") as f:
                raw_data = json.load(f)
                if isinstance(raw_data, list):
                    store_list = raw_data
                elif isinstance(raw_data, dict):
                    store_list = raw_data.get("documents", [])
        except Exception:
            store_list = []

    indexed_count = 0
    for file in files:
        try:
            content = ""
            if file.suffix.lower() in [".txt", ".md", ".py", ".json", ".js", ".html", ".csv", ".cpp", ".c", ".java"]:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            if content and len(content.strip()) > 10:
                store_list.append({
                    "text": content[:1500],
                    "category": "user_document",
                    "metadata": {
                        "filename": file.name,
                        "path": str(file)
                    },
                    "vector": _text_to_vector(content)
                })
                indexed_count += 1
        except Exception as e:
            print(f"[DOC TRAINER ERROR] {file.name}: {e}")

    with open(SEMANTIC_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store_list, f, indent=2, ensure_ascii=False)

    return f"Indexed {indexed_count} documents from your memory/user_documents folder into ULTRON's memory!"
