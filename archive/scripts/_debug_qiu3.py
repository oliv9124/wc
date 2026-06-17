import requests, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
url = "https://bifen.qiuqiushidao.com/index.php?c=home&a=ouzhi&fid=1279681"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers, timeout=30)
r.encoding = "utf-8"
html = r.text

# Find all script src references
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)', html):
    print(f"Script src: {m.group(1)}")

# Find all inline scripts with substantial content
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, s in enumerate(scripts):
    if len(s.strip()) > 50:
        print(f"\n=== Script {i} ({len(s)} chars) ===")
        print(s[:500])
        print("...")

# Find axios/http calls
for pat in [r'axios', r'\$http', r'this\.\$', r'created\s*\(', r'mounted\s*\(', r'methods\s*:', r'apiUrl', r'baseUrl', r'getOdds', r'getList', r'initData', r'loadOdds']:
    found = re.findall(pat, html, re.I)
    if found:
        print(f"\nPattern '{pat}': {len(found)} matches")
        for m in re.finditer(pat, html, re.I):
            ctx = html[max(0,m.start()-20):m.start()+150]
            print(f"  ...{ctx}...")
            break
