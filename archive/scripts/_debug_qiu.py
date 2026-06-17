import requests, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
url = "https://bifen.qiuqiushidao.com/index.php?c=home&a=ouzhi&fid=1279681"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers, timeout=30)
r.encoding = "utf-8"
html = r.text
print(f"Status: {r.status_code}, Length: {len(html)}")
for m in re.finditer(r'var\s+(\w+)\s*=\s*[\{\[\"]', html):
    name = m.group(1)
    pos = m.start()
    print(f"\nvar {name} at {pos}:")
    print(html[pos:pos+200])
    print("---")
# check for script tags with data
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\n{len(scripts)} script blocks found")
for i, s in enumerate(scripts):
    if len(s.strip()) > 20:
        print(f"\nScript {i} ({len(s)} chars):")
        print(s[:300])
        print("---")
