import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open(r"G:\download1\okooo_odds_changes_2026-06-16.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Type: {data.get('type')}")
print(f"Timestamp: {data.get('ts')}")
print(f"Matches: {len(data.get('matches', {}))}")
print()

total_changes = 0
for mid, mdata in data.get("matches", {}).items():
    label = mdata.get("label", mid)
    companies = mdata.get("companies", {})
    mc = sum(len(c.get("c", [])) for c in companies.values())
    total_changes += mc
    names = [f"{c.get('n','')}({len(c.get('c',[]))})" for c in companies.values()]
    print(f"{label}: {len(companies)}家公司, {mc}条变动")
    if len(companies) == 0:
        print(f"  ⚠ 无数据!")

print(f"\n总计: {total_changes} 条变动记录")

# Check sample data structure
for mid, mdata in list(data["matches"].items())[:1]:
    for cid, cdata in list(mdata["companies"].items())[:1]:
        print(f"\n样本数据 ({cdata['n']}, cid={cid}):")
        for row in cdata["c"][:3]:
            print(f"  {row}")
        print(f"  ... (共{len(cdata['c'])}条)")
        if cdata["c"]:
            print(f"  最后: {cdata['c'][-1]}")
