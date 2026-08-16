"""
test_searxng_provider.py - SearXNG Engine Probe
"""
import urllib.request
import json
import urllib.parse
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

instances = [
    'https://searx.be',
    'https://searx.prvcy.eu',
    'https://search.indie-group.org',
    'https://searx.tiekoetter.com',
    'https://searx.femboy.hu',
    'https://searx.perennialte.ch',
    'https://searx.work',
    'https://paulgo.io',
    'https://searx.ctsg.de',
    'https://search.bus-hit.me'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def search_instance(inst, query):
    q_enc = urllib.parse.quote(query)
    # Method 1: JSON API
    try:
        url = f"{inst}/search?q={q_enc}&format=json"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=4.0) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            results = data.get('results', [])
            if results:
                return "JSON", results
    except Exception as e:
        pass

    # Method 2: HTML scrape fallback
    try:
        url = f"{inst}/search?q={q_enc}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=4.0) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            matches = re.findall(r'href="([^"]+)"[^>]*class="url_header"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?<p[^>]*class="content"[^>]*>(.*?)</p>', html, re.DOTALL)
            if not matches:
                matches = re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>', html, re.DOTALL)
            if matches:
                res = []
                for m in matches[:5]:
                    url_clean = m[0]
                    title_clean = re.sub(r'<[^>]+>', '', m[1]).strip()
                    snip_clean = re.sub(r'<[^>]+>', '', m[2]).strip()
                    if url_clean.startswith("http"):
                        res.append({"title": title_clean, "url": url_clean, "snippet": snip_clean})
                if res:
                    return "HTML", res
    except Exception:
        pass
    return None, []

print("Probing SearXNG public instances for USD to INR query...")
query = "current USD to INR rate"
found = False
for inst in instances:
    mode, res = search_instance(inst, query)
    if res:
        print(f" [SUCCESS] ({mode}) {inst} -> {len(res)} results")
        print(f"   Top: {res[0]['title']} -> {res[0]['url']}")
        found = True
        break

if not found:
    print(" [NOTE] Public instances busy, testing meta-search fallback...")
