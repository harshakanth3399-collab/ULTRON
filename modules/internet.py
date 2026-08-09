"""Real-time Web Search & Internet Intelligence Module for ULTRON."""

from __future__ import annotations

import urllib.parse
import urllib.request
import json
import re


def search_web_live(query: str, max_results: int = 4) -> str:
    """Searches the live web for real-time information using DuckDuckGo Lite."""
    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        with urllib.request.urlopen(req, timeout=6) as response:
            html = response.read().decode("utf-8", errors="ignore")

        snippets = re.findall(r'result-snippet[^>]*>(.*?)</td>', html, re.DOTALL)
        clean_snippets = []
        for snip in snippets[:max_results]:
            text = re.sub(r'<[^>]+>', '', snip).strip()
            if text:
                clean_snippets.append(text)

        if clean_snippets:
            return "\n".join(clean_snippets)
    except Exception as e:
        print("[WEB SEARCH ERROR]", e)

    return ""

