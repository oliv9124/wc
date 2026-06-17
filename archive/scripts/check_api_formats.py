"""Check qiuqiushidao API formats for all 3 odds types + oneodds detail."""
import json, urllib.request, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://bifen.qiuqiushidao.com/index.php"
FID = "1279645"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": BASE,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

# Check overview endpoints
for atype in ["ouzhi", "yapan", "daxiao"]:
    data = fetch_json(f"{BASE}?c=odds&a={atype}&fid={FID}")
    rows = data.get("data", {}).get("rows", [])
    first = rows[0] if rows else {}
    cid = first.get("id", "?")
    name = first.get("name", "?")
    first_sub = first.get("first", {})
    end_sub = first.get("end", {})
    print(f"=== {atype} overview ===")
    print(f"  companies: {len(rows)}, first: id={cid} name={name}")
    print(f"  first.first keys: {list(first_sub.keys())}")
    print(f"  first.end keys: {list(end_sub.keys())}")
    print()
    time.sleep(0.5)

# Check oneodds detail for yapan and daxiao
for otype in ["yazhi", "daxiao"]:
    data = fetch_json(f"{BASE}?c=odds&a=oneodds&fid={FID}&cid=3&type={otype}")
    records = data.get("data", [])
    first = records[0] if records else {}
    print(f"=== oneodds type={otype} (Bet365) ===")
    print(f"  records: {len(records)}")
    print(f"  keys: {list(first.keys())}")
    print(f"  sample: {json.dumps(first, ensure_ascii=False)[:200]}")
    print()
    time.sleep(0.5)
