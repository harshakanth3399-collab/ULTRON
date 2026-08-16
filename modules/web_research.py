"""
modules/web_research.py - ULTRON Real Web Research Engine
Performs live internet searches via SearXNG meta-search API and primary web sources.
Fetches deep web page contents, extracts complete lists/addresses, and formats authoritative contexts.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

# Public SearXNG Meta-Search Instances Pool
SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://searx.prvcy.eu",
    "https://search.indie-group.org",
    "https://searx.tiekoetter.com",
    "https://searx.femboy.hu",
    "https://searx.perennialte.ch",
    "https://searx.work",
    "https://paulgo.io",
    "https://searx.ctsg.de",
    "https://search.bus-hit.me"
]

def _log_web(msg: str) -> None:
    """Prints formatted [WEB] telemetry event logs."""
    print(f"[WEB] {msg}")


def _normalize_search_query(raw_query: str) -> str:
    """Extracts essential search terms from conversational questions."""
    q = raw_query.lower().strip()
    fillers = [
        "could you please tell me", "can you please tell me", "tell me about", "can you check",
        "find out", "check in google", "search in google", "search online", "what is the current",
        "what is the latest", "what is the", "where are", "how many", "please find", "give me all"
    ]
    for f in fillers:
        q = q.replace(f, "")
    q = re.sub(r'[^\w\s]', ' ', q)
    extracted = " ".join(q.split()).strip()
    return extracted if len(extracted) >= 3 else raw_query.strip()


def fetch_web_page(url: str) -> str:
    """Fetches text content from a target Web URL."""
    if not url or "duckduckgo.com" in url or "google.com/search" in url:
        return ""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=4.5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Strip tags & scripts
            text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:2500]
    except Exception as e:
        _log_web(f"Fetch web page note for {url}: {e}")
        return ""


def _searxng_search(clean_query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Executes search across SearXNG free public instances."""
    results: List[Dict[str, str]] = []
    q_enc = urllib.parse.quote(clean_query)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for inst in SEARXNG_INSTANCES:
        try:
            url = f"{inst}/search?q={q_enc}&format=json"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=3.5) as resp:
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                items = data.get('results', [])
                for item in items[:max_results]:
                    u = item.get('url', '')
                    title = item.get('title', '')
                    snip = item.get('content', '') or item.get('snippet', '')
                    if u and snip:
                        domain = urllib.parse.urlparse(u).netloc.replace("www.", "")
                        results.append({
                            "title": title or domain,
                            "url": u,
                            "snippet": re.sub(r'<[^>]+>', '', snip).strip(),
                            "source": domain
                        })
                if results:
                    _log_web(f"SearXNG live search success from instance: {inst}")
                    break
        except Exception:
            continue

    return results


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Executes real internet search with deep page extraction for complete factual lists/addresses.
    """
    raw_query = query.strip()
    clean_query = _normalize_search_query(raw_query)

    _log_web(f"Query: '{raw_query}' (Normalized: '{clean_query}')")
    _log_web(f"Search started: Query='{clean_query}'")

    # 1. SearXNG Free Meta-Search
    results = _searxng_search(clean_query, max_results=max_results)

    # 2. DuckDuckGo / Primary Meta-Search Fallback
    if not results:
        try:
            url = "https://html.duckduckgo.com/html/"
            data = urllib.parse.urlencode({"q": clean_query}).encode("utf-8")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                url,
                data=data,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Content-Type": "application/x-www-form-urlencoded"},
                method="POST"
            )
            with urllib.request.urlopen(req, context=ctx, timeout=5.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            urls = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for i in range(min(len(urls), len(snippets), max_results)):
                raw_url = re.sub(r'<[^>]+>', '', urls[i][0]).strip()
                snip_text = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                domain = urllib.parse.urlparse(raw_url).netloc.replace("www.", "") or "web"
                if snip_text:
                    results.append({
                        "title": domain.capitalize(),
                        "url": raw_url,
                        "snippet": snip_text,
                        "source": domain
                    })
        except Exception as e:
            _log_web(f"DuckDuckGo fallback warning: {e}")

    # Prioritize Official / Primary Sources
    OFFICIAL_DOMAINS = ["qspiders.com", "jspiders.com", "wikipedia.org", "gov", "edu", "investing.com", "reuters.com", "bloomberg.com", "google.com", "apple.com", "amazon.com"]
    def _source_priority(item: Dict[str, str]) -> int:
        src = item.get("source", "").lower()
        if any(d in src for d in OFFICIAL_DOMAINS):
            return 0
        return 1

    results.sort(key=_source_priority)

    # 3. DEEP PAGE EXTRACTION: Open and fetch actual web page body text for top URLs
    _log_web("Performing deep web page content extraction for top sources...")
    for item in results[:3]:
        u = item.get("url", "")
        if u:
            p_text = fetch_web_page(u)
            if p_text:
                item["page_text"] = p_text
                _log_web(f"Extracted {len(p_text)} chars from page: {item['source']}")

    # 4. TARGETED SECONDARY SEARCH for list/location queries if initial evidence is brief
    is_list_query = any(k in raw_query.lower() for k in ["location", "branch", "address", "list", "where", "places", "area"])
    if is_list_query and len(results) < 3:
        try:
            sec_query = f"{clean_query} branch list locations addresses"
            _log_web(f"Executing secondary targeted list search: '{sec_query}'")
            sec_res = _searxng_search(sec_query, max_results=3)
            for s_item in sec_res:
                if not any(s_item["url"] == r.get("url") for r in results):
                    p_text = fetch_web_page(s_item.get("url", ""))
                    if p_text:
                        s_item["page_text"] = p_text
                    results.append(s_item)
        except Exception as e:
            _log_web(f"Secondary search note: {e}")

    sources = list(dict.fromkeys([r["source"] for r in results if r.get("source")]))
    _log_web(f"Results received: {len(results)} results from {sources if sources else 'No sources'}")
    _log_web(f"Sources: {', '.join(sources) if sources else 'None'}")

    evidence_lines = []
    for i, r in enumerate(results, 1):
        line = f"[{i}] Source: {r['source']} ({r['url']})\nSnippet: {r['snippet']}"
        if r.get("page_text"):
            line += f"\nFull Page Text: {r['page_text']}"
        evidence_lines.append(line)
    evidence_text = "\n\n".join(evidence_lines)

    _log_web(f"Evidence extracted: {len(evidence_text)} characters")

    return {
        "query": clean_query,
        "results": results,
        "sources": sources,
        "evidence_text": evidence_text,
        "success": len(results) > 0
    }


def research(query: str) -> Dict[str, Any]:
    """High-level web research entry point."""
    return web_search(query)

