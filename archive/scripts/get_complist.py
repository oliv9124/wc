"""Fetch full company list from qiuqiushidao."""
import json, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

url = 'https://bifen.qiuqiushidao.com/index.php?c=odds&a=complist'
data = b'tt=2&type=1'
req = urllib.request.Request(url, data=data, headers={
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://bifen.qiuqiushidao.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json'
})
with urllib.request.urlopen(req, timeout=15) as resp:
    result = json.loads(resp.read())

code = result["code"]
print(f"Code: {code}")
data = result.get("data", {})
total = 0
all_companies = {}

for group_key in sorted(data.keys()):
    group_list = data[group_key]
    print(f"\nGroup: {group_key} ({len(group_list)} companies)")
    for item in group_list:
        cid = str(item.get("id", item.get("cid", "?")))
        name = item.get("companyname", item.get("name", "?"))
        chosen = item.get("ischosed", "?")
        total += 1
        all_companies[cid] = name
        marker = " *" if chosen == 1 else ""
        print(f"  CID {cid:>5} = {name}{marker}")

print(f"\nTotal: {total} companies")

with open(r"D:\Desktop\world cup\qiu_complist.json", "w", encoding="utf-8") as f:
    json.dump(all_companies, f, ensure_ascii=False, indent=2)
print(f"Saved to qiu_complist.json")
