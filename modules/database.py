"""
database.py - ULTRON SQLite Storage & Telemetry Engine
Manages embedded SQLite database (memory/ultron.db) for structured chat logging,
reminders, and performance metrics.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_FILE = Path(__file__).parent.parent / "memory" / "ultron.db"


def get_connection() -> sqlite3.Connection:
    """Returns a thread-safe connection to memory/ultron.db."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes SQLite database schemas for chats, reminders, and telemetry."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Chat History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_prompt TEXT NOT NULL,
                ultron_response TEXT NOT NULL,
                model_used TEXT NOT NULL,
                latency_ms INTEGER DEFAULT 0
            )
        """)

        # 2. Reminders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                task TEXT NOT NULL,
                due_time TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)

        # 3. Telemetry Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT NOT NULL,
                metric_val REAL NOT NULL
            )
        """)

        conn.commit()
    print(f"[SQLITE] Database initialized cleanly at '{DB_FILE}'")


def log_chat(user_prompt: str, ultron_response: str, model_used: str = "ollama", latency_ms: int = 0) -> None:
    """Logs conversation interaction into SQLite database."""
    if not user_prompt or not ultron_response:
        return
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chats (user_prompt, ultron_response, model_used, latency_ms) VALUES (?, ?, ?, ?)",
                (user_prompt.strip(), ultron_response.strip(), model_used, latency_ms)
            )
            conn.commit()
    except Exception as e:
        print(f"[SQLITE ERROR] Failed to log chat: {e}")


def search_chat_history(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches past chat logs by keyword."""
    results = []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM chats WHERE user_prompt LIKE ? OR ultron_response LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{keyword}%", f"%{keyword}%", limit)
            )
            rows = cursor.fetchall()
            for r in rows:
                results.append(dict(r))
    except Exception as e:
        print(f"[SQLITE ERROR] Failed to search chat history: {e}")
    return results


def get_chat_stats() -> Dict[str, Any]:
    """Returns database statistics."""
    stats = {"total_chats": 0, "db_size_kb": 0}
    try:
        if DB_FILE.exists():
            stats["db_size_kb"] = round(DB_FILE.stat().st_size / 1024, 2)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chats")
            stats["total_chats"] = cursor.fetchone()[0]
    except Exception:
        pass
    return stats


# Auto-initialize database on import
init_db()
