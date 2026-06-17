"""Analyze okooo change history data quality and signals."""
import json, sys, re
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent

# Load the big file (first batch - EU odds only)
big_file = ROOT / "data" / "okooo" / "okooo_odds_changes.json"
data = json.load(open(big_file, "r", encoding="utf-8"))

# Load match config for actual results
config = json.load(open(ROOT / "worldcup_fids.json", "r", encoding="utf-8"))
mid_to_match = {m["ok_mid"]: m for m in config["matches"]}

# Also check if per-match v3 files exist
v3_dir = Path(r"G:\download1")

def parse_odds(s):
    """Strip arrows and parse float."""
    if not s: return None
    clean = re.sub(r'[↑↓]', '', s).strip()
    try: return float(clean)
    except: return None

def calc_ip(w, d, l):
    """Calculate implied probabilities from odds."""
    if not all([w, d, l]) or w <= 0 or d <= 0 or l <= 0:
        return None, None, None
    total = 1/w + 1/d + 1/l
    return 1/w/total*100, 1/d/total*100, 1/l/total*100

print("=" * 70)
print("澳客欧赔变动历史数据 · 质量分析报告")
print("=" * 70)

# ── 1. Coverage analysis ──
print("\n【1. 数据覆盖度】")
print(f"{'比赛':<20} {'公司数':>6} {'变动条数':>8} {'有初盘':>6} {'有终盘':>6} {'覆盖评级'}")
print("-" * 70)

match_stats = {}
for mid, mdata in data.get("matches", {}).items():
    label = mdata.get("label", mid)
    companies = mdata.get("companies", {})

    total_changes = 0
    has_init = 0
    has_final = 0
    company_details = {}

    for cid, cdata in companies.items():
        changes = cdata.get("c", [])
        total_changes += len(changes)

        init_found = any("初" in r[0] for r in changes if r)
        final_found = any("终" in r[0] for r in changes if r)
        if init_found: has_init += 1
        if final_found: has_final += 1

        company_details[cid] = {
            "name": cdata.get("n", ""),
            "changes": len(changes),
            "has_init": init_found,
            "has_final": final_found
        }

    rating = "满" if len(companies) >= 14 else "良" if len(companies) >= 8 else "中" if len(companies) >= 4 else "低"
    print(f"{label:<20} {len(companies):>6} {total_changes:>8} {has_init:>6} {has_final:>6} {rating:>6}")

    match_stats[mid] = {
        "label": label,
        "companies": len(companies),
        "changes": total_changes,
        "details": company_details,
        "rating": rating
    }

# ── 2. Company coverage across matches ──
print(f"\n{'='*70}")
print("【2. 各公司跨比赛覆盖率】")
print(f"{'公司':<16} {'覆盖场数':>8} {'覆盖率':>8} {'平均变动':>8} {'最多':>6} {'最少':>6}")
print("-" * 60)

company_coverage = defaultdict(list)
for mid, mdata in data["matches"].items():
    for cid, cdata in mdata.get("companies", {}).items():
        company_coverage[cid].append({
            "mid": mid,
            "name": cdata.get("n", ""),
            "changes": len(cdata.get("c", []))
        })

total_matches = len(data["matches"])
for cid in sorted(company_coverage.keys(), key=lambda c: len(company_coverage[c]), reverse=True):
    entries = company_coverage[cid]
    name = entries[0]["name"]
    counts = [e["changes"] for e in entries]
    cov = len(entries)
    print(f"{name:<16} {cov:>8} {cov/total_matches*100:>7.0f}% {sum(counts)/len(counts):>8.0f} {max(counts):>6} {min(counts):>6}")

# ── 3. Signal analysis on finished matches ──
print(f"\n{'='*70}")
print("【3. 信号验证 · IP Drift vs 实际结果】")
print(f"{'比赛':<20} {'初盘IP':>18} {'终盘IP':>18} {'漂移方向':>10} {'结果':>6} {'信号':>6}")
print("-" * 80)

KEY_EU = ["14", "82", "27", "25", "84", "49", "157"]  # EU big bookmakers
KEY_ASIA = ["65", "116"]  # Asian big
BETFAIR = "879"

results_map = {"主胜": "H", "平局": "D", "客胜": "A"}

correct = 0
total_tested = 0

for mid, mdata in data["matches"].items():
    match = mid_to_match.get(mid)
    if not match or match.get("status") != "finished":
        continue

    label = mdata.get("label", mid)
    score = match.get("score", "")
    if not score or ":" not in score:
        continue

    h_goals, a_goals = map(int, score.split(":"))
    actual = "H" if h_goals > a_goals else "D" if h_goals == a_goals else "A"
    actual_cn = {"H": "主胜", "D": "平局", "A": "客胜"}[actual]

    companies = mdata.get("companies", {})
    if not companies:
        continue

    # Calculate average IP drift across available companies
    init_ips = []
    final_ips = []

    for cid, cdata in companies.items():
        changes = cdata.get("c", [])
        if len(changes) < 2:
            continue

        # First row = final, last row = init
        final_row = changes[0]
        init_row = changes[-1]

        fw, fd, fl = parse_odds(final_row[1]), parse_odds(final_row[2]), parse_odds(final_row[3])
        iw, id_, il = parse_odds(init_row[1]), parse_odds(init_row[2]), parse_odds(init_row[3])

        f_ip = calc_ip(fw, fd, fl)
        i_ip = calc_ip(iw, id_, il)

        if all(f_ip) and all(i_ip):
            init_ips.append(i_ip)
            final_ips.append(f_ip)

    if not init_ips:
        continue

    # Average IPs
    avg_init = tuple(sum(x)/len(x) for x in zip(*init_ips))
    avg_final = tuple(sum(x)/len(x) for x in zip(*final_ips))

    # Drift
    drift_w = avg_final[0] - avg_init[0]
    drift_d = avg_final[1] - avg_init[1]
    drift_l = avg_final[2] - avg_init[2]

    # Determine signal direction (biggest absolute drift)
    drifts = {"H": drift_w, "D": drift_d, "A": drift_l}
    max_drift_dir = max(drifts, key=lambda k: abs(drifts[k]))
    max_drift_val = drifts[max_drift_dir]

    # Signal: if drift > 0, bookmaker is pushing probability UP = follow
    if abs(max_drift_val) < 1.0:
        signal = "弱"
        signal_dir = "-"
    else:
        signal_dir = max_drift_dir if max_drift_val > 0 else {"H":"A","A":"H","D":"D"}.get(max_drift_dir, "-")
        signal = "✓" if signal_dir == actual else "✗"

    if signal in ["✓", "✗"]:
        total_tested += 1
        if signal == "✓":
            correct += 1

    init_str = f"{avg_init[0]:.1f}/{avg_init[1]:.1f}/{avg_init[2]:.1f}"
    final_str = f"{avg_final[0]:.1f}/{avg_final[1]:.1f}/{avg_final[2]:.1f}"
    drift_str = f"{'主' if max_drift_dir=='H' else '平' if max_drift_dir=='D' else '客'}{max_drift_val:+.1f}%"

    print(f"{label:<20} {init_str:>18} {final_str:>18} {drift_str:>10} {actual_cn:>6} {signal:>6}")

if total_tested > 0:
    print(f"\nIP Drift信号准确率: {correct}/{total_tested} ({correct/total_tested*100:.0f}%)")

# ── 4. EU vs Asia split check ──
print(f"\n{'='*70}")
print("【4. 欧亚分歧检测】")

for mid, mdata in data["matches"].items():
    match = mid_to_match.get(mid)
    if not match or match.get("status") != "finished":
        continue

    label = mdata.get("label", mid)
    companies = mdata.get("companies", {})

    eu_drifts = []
    asia_drifts = []

    for cid in KEY_EU:
        if cid in companies:
            changes = companies[cid].get("c", [])
            if len(changes) >= 2:
                fw = parse_odds(changes[0][1])
                iw = parse_odds(changes[-1][1])
                if fw and iw:
                    eu_drifts.append(1/fw*100 - 1/iw*100)

    for cid in KEY_ASIA:
        if cid in companies:
            changes = companies[cid].get("c", [])
            if len(changes) >= 2:
                fw = parse_odds(changes[0][1])
                iw = parse_odds(changes[-1][1])
                if fw and iw:
                    asia_drifts.append(1/fw*100 - 1/iw*100)

    if eu_drifts and asia_drifts:
        eu_avg = sum(eu_drifts) / len(eu_drifts)
        asia_avg = sum(asia_drifts) / len(asia_drifts)
        if (eu_avg > 0 and asia_avg < 0) or (eu_avg < 0 and asia_avg > 0):
            score = match.get("score", "")
            h, a = map(int, score.split(":")) if score else (0, 0)
            actual = "主胜" if h > a else "平局" if h == a else "客胜"
            print(f"  ⚡ {label}: EU={eu_avg:+.2f}% vs Asia={asia_avg:+.2f}% → 分歧! 结果={actual} ({score})")

# ── 5. Betfair Exchange signal ──
print(f"\n{'='*70}")
print("【5. 必发交易所方向】")

for mid, mdata in data["matches"].items():
    match = mid_to_match.get(mid)
    if not match or match.get("status") != "finished":
        continue

    if BETFAIR not in mdata.get("companies", {}):
        continue

    label = mdata.get("label", mid)
    changes = mdata["companies"][BETFAIR].get("c", [])
    if len(changes) < 2:
        continue

    fw, fd, fl = parse_odds(changes[0][1]), parse_odds(changes[0][2]), parse_odds(changes[0][3])
    iw, id_, il = parse_odds(changes[-1][1]), parse_odds(changes[-1][2]), parse_odds(changes[-1][3])

    if all([fw, fd, fl, iw, id_, il]):
        f_ip = calc_ip(fw, fd, fl)
        i_ip = calc_ip(iw, id_, il)
        drift_w = f_ip[0] - i_ip[0]
        drift_d = f_ip[1] - i_ip[1]
        drift_l = f_ip[2] - i_ip[2]

        score = match.get("score", "")
        h, a = map(int, score.split(":")) if score else (0, 0)
        actual = "主" if h > a else "平" if h == a else "客"

        print(f"  {label}: 主{drift_w:+.2f}% 平{drift_d:+.2f}% 客{drift_l:+.2f}% → 结果={actual}({score})")

# ── 6. Late movement intensity ──
print(f"\n{'='*70}")
print("【6. 赛前最后变动密度 (临场信号)】")

for mid, mdata in data["matches"].items():
    match = mid_to_match.get(mid)
    if not match or match.get("status") != "finished":
        continue

    label = mdata.get("label", mid)
    companies = mdata.get("companies", {})

    # Count changes in last 24h and last 2h
    last_24h = 0
    last_2h = 0
    total = 0

    for cid, cdata in companies.items():
        for row in cdata.get("c", []):
            total += 1
            t = row[0] if row else ""
            m = re.search(r'赛前(\d+)小时', t)
            if not m:
                if "终" in t:
                    last_2h += 1
                    last_24h += 1
                continue
            hours = int(m.group(1))
            if hours <= 24:
                last_24h += 1
            if hours <= 2:
                last_2h += 1

    if total > 0:
        score = match.get("score", "")
        pct_24h = last_24h / total * 100 if total else 0
        print(f"  {label}: 总{total}条, 最后24h={last_24h}({pct_24h:.0f}%), 最后2h={last_2h} [{score}]")

# ── 7. Data sufficiency summary ──
print(f"\n{'='*70}")
print("【7. 数据充分性总结】")
good = sum(1 for s in match_stats.values() if s["rating"] in ["满", "良"])
medium = sum(1 for s in match_stats.values() if s["rating"] == "中")
low = sum(1 for s in match_stats.values() if s["rating"] == "低")
print(f"  满/良覆盖: {good}/24 场")
print(f"  中等覆盖:  {medium}/24 场")
print(f"  低覆盖:    {low}/24 场")
print(f"  总变动记录: {sum(s['changes'] for s in match_stats.values()):,}")

# Check if v3 files exist
v3_count = 0
for f in v3_dir.glob("okooo_*.json"):
    v3_count += 1
if v3_count > 0:
    print(f"\n  v3单场文件已下载: {v3_count} 个")
