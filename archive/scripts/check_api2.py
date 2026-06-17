"""Check yazhi and daxiao overview + oneodds formats."""
import json, urllib.request, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://bifen.qiuqiushidao.com/index.php"
FID = "1279645"
H = {"User-Agent": "Mozilla/5.0", "Referer": BASE, "X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}

def fetch(url):
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

# yazhi overview
d = fetch(f"{BASE}?c=odds&a=yazhi&fid={FID}")
rows = d["data"]["rows"]
r0 = rows[0]
print(f"=== yazhi overview ({len(rows)} companies) ===")
print(f"  id={r0['id']}, name={r0['name']}")
print(f"  first: {json.dumps(r0['first'], ensure_ascii=False)}")
print(f"  end:   {json.dumps(r0['end'], ensure_ascii=False)}")
print()
time.sleep(0.5)

# daxiao overview
d = fetch(f"{BASE}?c=odds&a=daxiao&fid={FID}")
rows = d["data"]["rows"]
r0 = rows[0]
print(f"=== daxiao overview ({len(rows)} companies) ===")
print(f"  id={r0['id']}, name={r0['name']}")
print(f"  first: {json.dumps(r0['first'], ensure_ascii=False)}")
print(f"  end:   {json.dumps(r0['end'], ensure_ascii=False)}")
print()
time.sleep(0.5)

# oneodds yazhi
d = fetch(f"{BASE}?c=odds&a=oneodds&fid={FID}&cid=3&type=yazhi")
recs = d["data"]
print(f"=== oneodds yazhi Bet365 ({len(recs)} records) ===")
print(f"  keys: {list(recs[0].keys())}")
print(f"  latest: {json.dumps(recs[0], ensure_ascii=False)}")
print(f"  oldest: {json.dumps(recs[-1], ensure_ascii=False)}")
print()
time.sleep(0.5)

# oneodds daxiao
d = fetch(f"{BASE}?c=odds&a=oneodds&fid={FID}&cid=3&type=daxiao")
recs = d["data"]
print(f"=== oneodds daxiao Bet365 ({len(recs)} records) ===")
print(f"  keys: {list(recs[0].keys())}")
print(f"  latest: {json.dumps(recs[0], ensure_ascii=False)}")
