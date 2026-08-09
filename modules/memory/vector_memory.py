"""
vector_memory.py - ULTRON Long-Term Semantic Memory Engine

Provides semantic recall of past conversations, project documents, notes,
and user preferences using persistent vector embeddings and cosine similarity.
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any


_MEMORY_FILE = Path(__file__).parent.parent.parent / "memory" / "semantic_vector_store.json"


class VectorMemory:
    def __init__(self, memory_file: Path = _MEMORY_FILE):
        self.memory_file = memory_file
        self.entries: list[dict[str, Any]] = []
        self._load()

    def _load(self):
        try:
            if self.memory_file.exists():
                raw = self.memory_file.read_text(encoding="utf-8")
                if raw.strip():
                    self.entries = json.loads(raw)
                    return
        except (json.JSONDecodeError, Exception) as e:
            print(f"[VECTOR MEMORY] Corrupted store detected, starting fresh: {e}")
            try:
                self.memory_file.unlink(missing_ok=True)
            except Exception:
                pass
        self.entries = []

    def _save(self):
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.memory_file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, indent=2)
            os.replace(str(tmp_path), str(self.memory_file))
        except Exception as e:
            print(f"[VECTOR MEMORY ERROR] Save failed: {e}")

    @staticmethod
    def _vectorize(text: str) -> dict[str, float]:
        """Convert text into word n-gram term frequency vector."""
        words = re.findall(r"\w+", text.lower())
        if not words:
            return {}
        counts: dict[str, int] = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
        total = float(len(words))
        return {w: c / total for w, c in counts.items()}

    @staticmethod
    def _cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
        if not v1 or not v2:
            return 0.0
        dot = sum(val * v2.get(k, 0.0) for k, val in v1.items())
        norm1 = math.sqrt(sum(val ** 2 for val in v1.values()))
        norm2 = math.sqrt(sum(val ** 2 for val in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def remember(self, text: str, category: str = "conversation", metadata: dict | None = None):
        """Store a new text entry into long-term semantic memory."""
        text_clean = text.strip()
        if not text_clean:
            return

        # Avoid exact duplicates
        for entry in self.entries:
            if entry.get("text", "").lower() == text_clean.lower():
                return

        vector = self._vectorize(text_clean)
        entry = {
            "text": text_clean,
            "category": category,
            "metadata": metadata or {},
            "vector": vector
        }
        self.entries.append(entry)
        self._save()

    def query(self, query_text: str, top_k: int = 3, category: str | None = None) -> list[dict[str, Any]]:
        """Retrieve top_k most relevant memories for a given query."""
        q_vec = self._vectorize(query_text)
        if not q_vec or not self.entries:
            return []

        results = []
        for entry in self.entries:
            if category and entry.get("category") != category:
                continue
            sim = self._cosine_similarity(q_vec, entry.get("vector", {}))
            if sim > 0.05:  # Relevance threshold
                results.append((sim, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:top_k]]

    def index_workspace(self, workspace_path: str | Path):
        """Index local text files and scripts into semantic memory."""
        ws_path = Path(workspace_path)
        if not ws_path.exists():
            return

        for ext in ["*.txt", "*.md", "*.py", "*.json"]:
            for file_path in ws_path.rglob(ext):
                if ".git" in str(file_path) or "__pycache__" in str(file_path) or "semantic_vector_store" in str(file_path):
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if content.strip():
                        # Chunk content by paragraphs
                        chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 30]
                        for chunk in chunks[:10]:  # Up to 10 key chunks per file
                            self.remember(
                                text=chunk,
                                category="project_file",
                                metadata={"filename": file_path.name, "path": str(file_path)}
                            )
                except Exception:
                    pass


# Singleton instance
vector_memory = VectorMemory()
