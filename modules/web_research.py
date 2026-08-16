"""
modules/web_research.py - ULTRON Real Web Research Engine
Performs live internet searches, extracts evidence from web pages, logs [WEB] telemetry,
and formats authoritative search contexts for AI generation without hallucinating facts.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

# Supported API environment variable names
ENV_WEB_KEY = os.getenv("WEB_SEARCH_API_KEY", "") or os.getenv("TAVILY_API_KEY", "") or os.getenv("SERPER_API_KEY", "")


def _log_web(msg: str) -> None:
    """Prints formatted [WEB] telemetry event logs."""
    print(f"[WEB] {msg}")


def _normalize_search_query(raw_query: str) -> str:
    """Extracts essential search terms from conversational questions."""
    q = raw_query.lower().strip()
    fillers = [
        "could you please tell me", "can you please tell me", "tell me about", "can you check",
        "find out", "check in google", "search in google", "search online", "what is the current",
        "what is the latest", "what is the", "where are", "how many", "please find"
    ]
    for f in fillers:
        q = q.replace(f, "")
    q = re.sub(r'[^\w\s]', ' ', q)
    extracted = " ".join(q.split()).strip()
    return extracted if len(extracted) >= 3 else raw_query.strip()


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Executes a real internet search using API key if available,
    otherwise falling back to DuckDuckGo HTML/JSON and open web endpoints.
    """
    raw_query = query.strip()
    clean_query = _normalize_search_query(raw_query)

    _log_web(f"Query: '{raw_query}' (Normalized: '{clean_query}')")
    _log_web(f"Search started: Query='{clean_query}'")


    results: List[Dict[str, str]] = []


    # 1. Try Tavily / Serper API if key is present
    api_key = os.getenv("WEB_SEARCH_API_KEY", "") or os.getenv("TAVILY_API_KEY", "") or os.getenv("SERPER_API_KEY", "")
    if api_key:
        try:
            if "tavily" in api_key.lower() or os.getenv("TAVILY_API_KEY"):
                url = "https://api.tavily.com/search"
                payload = json.dumps({"query": clean_query, "search_depth": "basic", "max_results": max_results}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "api-key": api_key}, method="POST")
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    for item in res_json.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                            "source": urllib.parse.urlparse(item.get("url", "")).netloc.replace("www.", "")
                        })
        except Exception as e:
            _log_web(f"API key search warning: {e}. Falling back to DuckDuckGo engine.")

    # 2. DuckDuckGo HTML & JSON Endpoint Fallback
    if not results:
        try:
            # Method A: DuckDuckGo HTML Lite / HTML Search
            url = "https://html.duckduckgo.com/html/"
            data = urllib.parse.urlencode({"q": clean_query}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract result blocks (class="result__body" or "result-snippet")
            matches = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            if not matches:
                # Alternative regex for result snippets
                snippets = re.findall(r'<a class="result__snippet"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
                urls = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
                for i in range(min(len(urls), len(snippets), max_results)):
                    raw_url = re.sub(r'<[^>]+>', '', urls[i][0]).strip()
                    snip_text = re.sub(r'<[^>]+>', '', snippets[i][1]).strip()
                    domain = urllib.parse.urlparse(raw_url).netloc.replace("www.", "") or "web"
                    results.append({
                        "title": domain.capitalize(),
                        "url": raw_url,
                        "snippet": snip_text,
                        "source": domain
                    })
            else:
                for raw_url, title_html, snip_html in matches[:max_results]:
                    clean_url = re.sub(r'<[^>]+>', '', raw_url).strip()
                    clean_title = re.sub(r'<[^>]+>', '', title_html).strip()
                    clean_snip = re.sub(r'<[^>]+>', '', snip_html).strip()
                    domain = urllib.parse.urlparse(clean_url).netloc.replace("www.", "") or "web"
                    if clean_snip:
                        results.append({
                            "title": clean_title or domain,
                            "url": clean_url,
                            "snippet": clean_snip,
                            "source": domain
                        })
        except Exception as e:
            _log_web(f"DuckDuckGo HTML query warning: {e}")

    # Method A2: DuckDuckGo Lite GET Fallback
    if not results:
        try:
            url_lite = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(clean_query)}"
            req_lite = urllib.request.Request(
                url_lite,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req_lite, timeout=6.0) as resp:
                html_lite = resp.read().decode("utf-8", errors="ignore")
            snippets_lite = re.findall(r'result-snippet[^>]*>(.*?)</td>', html_lite, re.DOTALL)
            for snip in snippets_lite[:max_results]:
                text = re.sub(r'<[^>]+>', '', snip).strip()
                if text:
                    results.append({
                        "title": "DuckDuckGo Web Result",
                        "url": "https://duckduckgo.com",
                        "snippet": text,
                        "source": "duckduckgo.com"
                    })
        except Exception as e:
            _log_web(f"DuckDuckGo Lite GET warning: {e}")


    # 3. Method B Fallback: DuckDuckGo Instant Answer API & Wikipedia Search
    if not results:
        try:
            ddg_api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_query)}&format=json"
            req = urllib.request.Request(ddg_api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "").strip()
                source_name = data.get("AbstractSource", "DuckDuckGo").strip()
                source_url = data.get("AbstractURL", "")
                if abstract:
                    results.append({
                        "title": source_name,
                        "url": source_url,
                        "snippet": abstract,
                        "source": urllib.parse.urlparse(source_url).netloc.replace("www.", "") if source_url else source_name
                    })

                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "").split(" - ")[0],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                            "source": urllib.parse.urlparse(topic.get("FirstURL", "")).netloc.replace("www.", "") or "duckduckgo.com"
                        })
        except Exception as e:
            _log_web(f"DuckDuckGo API query warning: {e}")

    # Deduplicate & format sources
    sources = list(dict.fromkeys([r["source"] for r in results if r.get("source")]))
    _log_web(f"Results received: {len(results)} results from {sources if sources else 'No sources'}")
    _log_web(f"Sources: {', '.join(sources) if sources else 'None'}")

    evidence_text = ""
    if results:
        evidence_lines = []
        for i, r in enumerate(results, 1):
            evidence_lines.append(f"[{i}] Source: {r['source']} ({r['url']})\nSnippet: {r['snippet']}")
        evidence_text = "\n\n".join(evidence_lines)

    _log_web(f"Evidence extracted: {len(evidence_text)} characters")

    return {
        "query": clean_query,
        "results": results,
        "sources": sources,
        "evidence_text": evidence_text,
        "success": len(results) > 0
    }


def fetch_web_page(url: str) -> str:
    """Fetches text content from a target Web URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Strip tags & scripts
            text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]
    except Exception as e:
        _log_web(f"Fetch web page failed for {url}: {e}")
        return ""


def research(query: str) -> Dict[str, Any]:
    """High-level web research entry point."""
    return web_search(query)
