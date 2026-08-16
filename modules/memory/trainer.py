"""
trainer.py - ULTRON Personal ChatGPT Data & Document Ingestion Engine
Ingests exported ChatGPT chat logs (conversations.json / text files) and personal data
into semantic vector memory (semantic_vector_store.json) and SQLite database (ultron.db).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any

from modules.database import get_connection
from modules.memory.profile_manager import get_profile_manager

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


def ingest_chatgpt_data(file_path: str) -> str:
    """
    Ingests exported ChatGPT JSON or TXT file into ULTRON's vector memory and SQLite database.
    """
    path = Path(file_path)
    if not path.exists():
        return f"File '{file_path}' not found."

    ingested_count = 0

    try:
        # Load existing vector store (handles both list and dict formats)
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

        if path.suffix.lower() == ".json":
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
            except Exception:
                data = None

            if isinstance(data, list):
                for conv in data:
                    if not isinstance(conv, dict):
                        continue
                    title = str(conv.get("title", "ChatGPT Conversation"))
                    mapping = conv.get("mapping", {})
                    if isinstance(mapping, dict):
                        for node_id, node in mapping.items():
                            if not isinstance(node, dict):
                                continue
                            msg = node.get("message")
                            if isinstance(msg, dict):
                                content_dict = msg.get("content", {})
                                if isinstance(content_dict, dict):
                                    parts = content_dict.get("parts", [])
                                    if isinstance(parts, list):
                                        text = " ".join(str(p) for p in parts if isinstance(p, (str, int, float))).strip()
                                        if len(text) > 20:
                                            store_list.append({
                                                "text": f"[{title}] {text[:1500]}",
                                                "category": "chatgpt_history",
                                                "metadata": {
                                                    "filename": path.name,
                                                    "title": title
                                                },
                                                "vector": _text_to_vector(text)
                                            })
                                            ingested_count += 1
            elif isinstance(data, dict):
                for k, v in data.items():
                    val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                    if len(val_str) > 20:
                        store_list.append({
                            "text": f"[{path.name} - {k}] {val_str[:1500]}",
                            "category": "user_memory",
                            "metadata": {
                                "filename": path.name,
                                "key": str(k)
                            },
                            "vector": _text_to_vector(val_str)
                        })
                        ingested_count += 1
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 20]
            for c in chunks:
                store_list.append({
                    "text": c[:1500],
                    "category": "user_document",
                    "metadata": {
                        "filename": path.name
                    },
                    "vector": _text_to_vector(c)
                })
                ingested_count += 1

        # Save back to semantic vector store
        with open(SEMANTIC_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(store_list, f, indent=2, ensure_ascii=False)

        # Log into SQLite database
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry (metric_name, metric_val) VALUES (?, ?)",
                ("personal_data_ingested", float(ingested_count))
            )
            conn.commit()

        pm = get_profile_manager()
        pref_addr = pm.get_preferred_address() or "Harsha"
        return f"Successfully ingested {ingested_count} memories from '{path.name}' into ULTRON!"

    except Exception as e:
        return f"Failed to ingest personal data: {e}"
