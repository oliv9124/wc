import requests, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for js_name in ["plouzhi.js", "commonPL.js", "common.js"]:
    url = f"https://cache.qiuqiusd.com/bifen/js/{js_name}?v=2025102702"
    r = requests.get(url, timeout=15)
    print(f"\n{'='*60}")
    print(f"{js_name} ({len(r.text)} chars)")
    print(f"{'='*60}")

    # Find API endpoints
    for m in re.finditer(r'(?:url|api|href)\s*[:=]\s*["\']([^"\']+)', r.text):
        endpoint = m.group(1)
        if 'index.php' in endpoint or 'api' in endpoint.lower() or 'c=' in endpoint:
            print(f"  Endpoint: {endpoint}")

    # Find ajax/get/post calls with URLs
    for m in re.finditer(r'\$\.(get|post|ajax)\s*\(\s*["\']([^"\']+)', r.text):
        print(f"  $.{m.group(1)}: {m.group(2)}")

    for m in re.finditer(r'axios\.(get|post)\s*\(\s*["\']([^"\']+)', r.text):
        print(f"  axios.{m.group(1)}: {m.group(2)}")

    # Also look for fetch patterns
    for m in re.finditer(r'fetch\s*\(\s*["\']([^"\']+)', r.text):
        print(f"  fetch: {m.group(1)}")

    # Look for URL construction patterns
    for m in re.finditer(r'["\']index\.php\?[^"\']+', r.text):
        print(f"  URL: {m.group()}")
