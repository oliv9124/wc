import urllib.request, re, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://bifen.qiuqiushidao.com/index.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE,
}

# Fetch showType=2 for 6/13 and look for World Cup / team names
url = f"{BASE}?c=home&a=bifen&showType=2&date=2026-06-13"
req = urllib.request.Request(url, headers=HEADERS)
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

# Search for 世界杯
idx = html.find("世界杯")
if idx >= 0:
    print("Found 世界杯 at", idx)
    # Get surrounding context
    chunk = html[idx:idx+3000]
    clean = re.sub(r'<[^>]+>', '|', chunk)
    clean = re.sub(r'\|+', '|', clean)
    clean = re.sub(r'\s+', ' ', clean)
    print(clean[:1500])
else:
    print("世界杯 not found in HTML")
    # Try searching for team names
    for team in ["加拿大", "波黑", "美国", "巴拉圭"]:
        idx = html.find(team)
        if idx >= 0:
            chunk = html[max(0,idx-200):idx+500]
            clean = re.sub(r'<[^>]+>', '|', chunk)
            clean = re.sub(r'\|+', '|', clean)
            clean = re.sub(r'\s+', ' ', clean)
            print(f"\n{team} found:")
            print(clean[:400])
