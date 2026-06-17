"""Merge all CID mappings into final file."""
import json

# Load qiuqiushidao complist
with open(r"D:\Desktop\world cup\qiu_complist.json", "r", encoding="utf-8") as f:
    qiu = json.load(f)

# Load okooo full list
with open(r"D:\Desktop\world cup\okooo_cid_all.json", "r", encoding="utf-8") as f:
    okooo = json.load(f)

result = {
    "qiuqiushidao": {
        "total": len(qiu),
        "source": "complist API (c=odds&a=complist, POST tt=2&type=1)",
        "default_15": [0, 1, 2, 3, 5, 6, 9, 16, 122, 140, 280, 293, 348, 651, 1055],
        "companies": qiu
    },
    "okooo": {
        "total": len(okooo),
        "source": "odds/ajax pagination (page=0..4, 30 per page)",
        "companies": okooo
    }
}

with open(r"D:\Desktop\world cup\cid_mapping_final.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"qiuqiushidao: {len(qiu)} companies")
print(f"okooo: {len(okooo)} companies")
print("Saved to cid_mapping_final.json")
