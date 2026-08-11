"""
trainer.py - ULTRON Personal ChatGPT Data & Document Ingestion Engine
Ingests exported ChatGPT chat logs (conversations.json / text files) and personal data
into semantic vector memory (semantic_vector_store.json) and SQLite database (ultron.db).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Any

from modules.database import get_connection
from modules.memory.profile_manager import get_profile_manager

SEMANTIC_STORE_PATH = Path(__file__).parent.parent.parent / "memory" / "semantic_vector_store.json"


def ingest_chatgpt_data(file_path: str) -> str:
    """
    Ingests exported ChatGPT JSON or TXT file into ULTRON's vector memory and SQLite database.
    """
    path = Path(file_path)
    if not path.exists():
        return f"File '{file_path}' not found, Sir."

    ingested_count = 0

    try:
        # Load existing vector store
        store_data = {}
        if SEMANTIC_STORE_PATH.exists():
            try:
                with open(SEMANTIC_STORE_PATH, "r", encoding="utf-8") as f:
                    store_data = json.load(f)
            except Exception:
                store_data = {}

        if "documents" not in store_data:
            store_data["documents"] = []

        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for conv in data:
                    title = conv.get("title", "ChatGPT Conversation")
                    mapping = conv.get("mapping", {})
                    for node_id, node in mapping.items():
                        msg = node.get("message")
                        if msg and msg.get("content", {}).get("parts"):
                            text = " ".join(str(p) for p in msg["content"]["parts"] if isinstance(p, str)).strip()
                            if len(text) > 20:
                                store_data["documents"].append({
                                    "title": title,
                                    "content": text[:1000],
                                    "source": "ChatGPT_Export"
                                })
                                ingested_count += 1
        else:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 30]
            for c in chunks:
                store_data["documents"].append({
                    "title": path.name,
                    "content": c[:1000],
                    "source": "Personal_Data"
                })
                ingested_count += 1

        # Save back to semantic vector store
        with open(SEMANTIC_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(store_data, f, indent=2, ensure_ascii=False)

        # Log into SQLite database
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry (metric_name, metric_val) VALUES (?, ?)",
                ("personal_data_ingested", float(ingested_count))
            )
            conn.commit()

        pm = get_profile_manager()
        pref_addr = pm.data.get("preferences", {}).get("preferred_address", "Sir")
        return f"Successfully ingested {ingested_count} personal data memories into ULTRON, {pref_addr}!"

    except Exception as e:
        return f"Failed to ingest personal data: {e}"
