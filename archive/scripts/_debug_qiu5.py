import requests, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for js_name in ["plouzhi.js", "commonPL.js"]:
    url = f"https://cache.qiuqiusd.com/bifen/js/{js_name}?v=2025102702"
    r = requests.get(url, timeout=15)
    print(f"\n{'='*60}")
    print(f"{js_name}")
    print(f"{'='*60}")
    print(r.text)
