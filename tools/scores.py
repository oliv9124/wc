import json, re, urllib.request, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://bifen.qiuqiushidao.com"}

url = "https://bifen.qiuqiushidao.com/index.php?c=home&a=bifen&showType=3&date=2026-06-16"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode("utf-8", errors="replace")

our_fids = ["1279676","1279669","1279675","1279670"]
config = json.load(open(ROOT / "worldcup_fids.json", "r", encoding="utf-8"))
fid_to_match = {m["qiu_fid"]: m for m in config["matches"]}

# Find score data in HTML - look for fid references
for fid in our_fids:
    m = fid_to_match.get(fid, {})
    label = f"{m.get('home','?')}vs{m.get('away','?')}"
    # Search around fid in HTML
    idx = html.find(fid)
    if idx >= 0:
        context = html[max(0,idx-500):idx+500]
        # Look for score patterns like >2< or data attributes
        scores = re.findall(r'class="[^"]*score[^"]*"[^>]*>(\d+)', context)
        goals = re.findall(r'>(\d+)</(?:span|td|div)', context)
        print(f"{label} (fid={fid}): scores={scores} goals={goals}")
        # Also print raw context for debugging
        clean = re.sub(r'<[^>]+>', ' ', context)
        clean = re.sub(r'\s+', ' ', clean).strip()
        print(f"  context: {clean[:200]}")
    else:
        print(f"{label} (fid={fid}): NOT FOUND in HTML")
    print()
