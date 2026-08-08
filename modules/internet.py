"""Real-time Web Search & Internet Intelligence Module for ULTRON."""

from __future__ import annotations

import urllib.parse
import urllib.request
import json
import re


def search_web_live(query: str, max_results: int = 3) -> str:
    """Searches the live web for real-time information using DuckDuckGo API."""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Extract search result snippets
        snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
        clean_snippets = []
        for snip in snippets[:max_results]:
            text = re.sub(r'<[^>]+>', '', snip).strip()
            if text:
                clean_snippets.append(text)

        if clean_snippets:
            return "\n".join(clean_snippets)
    except Exception as e:
        print("Web Search Error:", e)

    return ""
