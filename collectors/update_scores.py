"""Fetch latest match scores from bifen pages and update worldcup_fids.json"""
import json, urllib.request, re, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
CONFIG = ROOT / "worldcup_fids.json"

BASE = "https://bifen.qiuqiushidao.com/index.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE,
}

with open(CONFIG, "r", encoding="utf-8") as f:
    config = json.load(f)

# Build lookup: home team -> match
match_lookup = {}
for m in config["matches"]:
    match_lookup[m["home"]] = m

dates = sorted(set(m["date"] for m in config["matches"]))
updates = 0

for date in dates:
    url = f"{BASE}?c=home&a=bifen&showType=2&date={date}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"{date}: fetch error {e}")
        continue

    # Find patterns like: 加拿大1:1波黑 or 美国2:0巴拉圭
    for m in config["matches"]:
        if m["date"] != date:
            continue
        home, away = m["home"], m["away"]
        # Pattern: home + score + away, where score is digit:digit
        pattern = re.escape(home) + r'(\d+):(\d+)' + re.escape(away)
        match = re.search(pattern, html)
        if match:
            score = f"{match.group(1)}:{match.group(2)}"
            old_score = m.get("score", "")
            old_status = m.get("status", "")
            m["score"] = score
            m["status"] = "finished"
            changed = score != old_score or old_status != "finished"
            marker = " ** NEW" if changed else ""
            print(f"  {date} {m['time']} | {home} {score} {away}{marker}")
            updates += 1
        else:
            # Check if match is still upcoming (no score in page)
            if home in html:
                print(f"  {date} {m['time']} | {home} vs {away} — in page but no score (in progress?)")
            else:
                print(f"  {date} {m['time']} | {home} vs {away} — not found in page")

    time.sleep(0.5)

with open(CONFIG, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print(f"\nDone. {updates} matches with scores. worldcup_fids.json updated.")
