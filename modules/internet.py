"""Real-time Web Search & Internet Intelligence Module for ULTRON."""

from __future__ import annotations

from modules.web_research import web_search, research, fetch_web_page


def search_web_live(query: str, max_results: int = 4) -> str:
    """Searches the live web using the unified web research engine."""
    res = web_search(query, max_results=max_results)
    return res.get("evidence_text", "")


