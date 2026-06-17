import requests, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
url = "https://bifen.qiuqiushidao.com/index.php?c=home&a=ouzhi&fid=1279681"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers, timeout=30)
r.encoding = "utf-8"
html = r.text

# Check for ajax/fetch patterns
for pattern in [r'\.ajax\(', r'fetch\(', r'\.get\(', r'\.post\(', r'XMLHttpRequest', r'url\s*:', r'api', r'loadData', r'getData']:
    matches = [(m.start(), html[max(0,m.start()-30):m.start()+100]) for m in re.finditer(pattern, html, re.I)]
    if matches:
        print(f"Pattern '{pattern}': {len(matches)} matches")
        for pos, ctx in matches[:3]:
            print(f"  @{pos}: ...{ctx}...")
        print()

# Check for table structures
tables = re.findall(r'<table[^>]*>', html)
print(f"\n{len(tables)} tables found")

# Check for data in table cells - first few rows
trs = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
print(f"{len(trs)} table rows found")
for i, tr in enumerate(trs[:5]):
    cells = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
    clean_cells = [re.sub(r'<[^>]*>', '', c).strip()[:30] for c in cells]
    if clean_cells:
        print(f"  Row {i}: {clean_cells}")

# Look for iframe
iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)', html)
print(f"\n{len(iframes)} iframes: {iframes}")

# Check for any JSON-like data attributes
data_attrs = re.findall(r'data-[\w-]+=["\']([^"\']{20,100})', html)
print(f"\n{len(data_attrs)} long data attrs")
for d in data_attrs[:5]:
    print(f"  {d}")
