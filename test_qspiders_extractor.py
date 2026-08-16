"""
test_qspiders_extractor.py - QSpiders Deep Page Extraction Test
"""
import urllib.request
import urllib.parse
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

queries = [
    "qspiders bangalore branch locations BTM Rajajinagar Marathahalli",
    "qspiders bangalore branches list",
    "qspiders location in bangalore"
]

results = []

for q in queries:
    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({'q': q}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=6.0) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        urls = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)

        for i in range(min(len(urls), 3)):
            raw_url = re.sub(r'<[^>]+>', '', urls[i][0]).strip()
            snip_text = re.sub(r'<[^>]+>', '', snippets[i] if i < len(snippets) else '').strip()

            # Deep page fetch
            page_text = ""
            if "duckduckgo.com" not in raw_url:
                try:
                    p_req = urllib.request.Request(raw_url, headers=headers)
                    with urllib.request.urlopen(p_req, context=ctx, timeout=4.0) as p_resp:
                        p_html = p_resp.read().decode('utf-8', errors='ignore')
                        clean_t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', p_html, flags=re.DOTALL | re.IGNORECASE)
                        clean_t = re.sub(r'<[^>]+>', ' ', clean_t)
                        page_text = re.sub(r'\s+', ' ', clean_t).strip()[:2000]
                except Exception as e:
                    pass

            results.append({
                "url": raw_url,
                "snippet": snip_text,
                "page_text": page_text
            })
    except Exception as e:
        print("Query failed:", e)

print(f"Collected {len(results)} search & deep page results!")
combined_text = "\n".join([r['snippet'] + " " + r['page_text'] for r in results])

# Search for known Bangalore area names in the collected text
areas = ["BTM", "Rajajinagar", "Marathahalli", "Hebbal", "Jayanagar", "Basavanagudi", "Electronic City", "Old Airport Road", "Hebbal", "Malleshwaram", "Indiranagar", "Koramangala", "HSR Layout", "Vijayanagar"]
found_areas = [a for a in areas if a.lower() in combined_text.lower()]
print("FOUND BANGALORE BRANCH AREAS:", found_areas)
