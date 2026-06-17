import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

files = [
    r"G:\download1\okooo_1315851.json",
    r"G:\download1\okooo_1315852.json",
]

for fp in files:
    with open(fp, "r", encoding="utf-8") as f:
        d = json.load(f)

    print(f"{'='*60}")
    print(f"文件: {fp.split(chr(92))[-1]}")
    print(f"比赛: {d.get('label','')}  日期: {d.get('date','')}")
    print(f"时间戳: {d.get('ts','')}")
    print()

    for dtype in ["odds", "ah", "overunder"]:
        section = d.get(dtype, {})
        type_cn = {"odds": "欧赔", "ah": "亚盘", "overunder": "大小球"}[dtype]
        if not section:
            print(f"  {type_cn}: ❌ 无数据")
            continue

        total_changes = sum(len(c.get("c", [])) for c in section.values())
        names = []
        for cid, cdata in section.items():
            cnt = len(cdata.get("c", []))
            names.append(f"{cdata.get('n',cid)}({cnt})")

        print(f"  {type_cn}: {len(section)}家公司, {total_changes}条变动")
        print(f"    {', '.join(names)}")

        # Show sample data structure
        first_cid = list(section.keys())[0]
        first_data = section[first_cid]
        sample = first_data["c"][0] if first_data.get("c") else []
        print(f"    样本({first_data.get('n','')})第1条: {sample}")
        if len(first_data.get("c", [])) > 1:
            last = first_data["c"][-1]
            print(f"    样本({first_data.get('n','')})末条: {last}")
        print()
