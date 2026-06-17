"""Analyze finished matches: odds vs results, find patterns."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent

with open(ROOT / "worldcup_fids.json", "r", encoding="utf-8") as f:
    config = json.load(f)
with open(ROOT / "cid_mapping_final.json", "r", encoding="utf-8") as f:
    cid_map = json.load(f)

cid_names = cid_map["qiuqiushidao"]["companies"]
DATA = ROOT / "data"

finished = [m for m in config["matches"] if m.get("status") == "finished" and m.get("score")]

def result_from_score(score):
    h, a = map(int, score.split(":"))
    if h > a: return "win"
    if h == a: return "draw"
    return "lost"

print(f"=== {len(finished)} finished matches ===\n")

# ============================================================
# 1. Overview analysis: init vs end odds, probability vs result
# ============================================================
print("=" * 80)
print("1. EUROPEAN ODDS OVERVIEW — Init vs End vs Result")
print("=" * 80)

KEY_CIDS = ["0", "3", "1055", "280", "6", "9"]  # 百家欧赔, Bet365, Pinnacle, 皇冠, 伟德, 易胜博

for m in finished:
    fid = m["qiu_fid"]
    result = result_from_score(m["score"])
    result_cn = {"win": "主胜", "draw": "平局", "lost": "客胜"}[result]

    ov_file = DATA / "qiu" / "overview" / f"{fid}_ouzhi.json"
    if not ov_file.exists():
        continue
    with open(ov_file, "r", encoding="utf-8") as f:
        ov = json.load(f)

    print(f"\n--- {m['date']} {m['time']} {m['home']} {m['score']} {m['away']} [{result_cn}] ---")
    print(f"{'公司':<12} {'初胜':>6} {'初平':>6} {'初负':>6}  →  {'终胜':>6} {'终平':>6} {'终负':>6} {'胜率Δ':>7} {'返还':>6}")

    for r in ov.get("rows", []):
        if r["id"] not in KEY_CIDS:
            continue
        f_data = r["first"]
        e_data = r.get("end") or f_data

        f_wr = float(f_data.get("winrate") or f_data.get("wgl") or 0)
        e_wr = float(e_data.get("winrate") or e_data.get("wgl") or 0)
        wr_delta = e_wr - f_wr

        print(f"{r['name']:<12} {f_data['win']:>6} {f_data['draw']:>6} {f_data['lost']:>6}  →  {e_data['win']:>6} {e_data['draw']:>6} {e_data['lost']:>6} {wr_delta:>+7.1f}% {e_data['pay']:>5}%")

# ============================================================
# 2. Asian handicap analysis
# ============================================================
print("\n" + "=" * 80)
print("2. ASIAN HANDICAP — Line movement vs Result")
print("=" * 80)

ah_results = []
for m in finished:
    fid = m["qiu_fid"]
    result = result_from_score(m["score"])
    h, a = map(int, m["score"].split(":"))
    goal_diff = h - a

    ov_file = DATA / "qiu" / "overview" / f"{fid}_yazhi.json"
    if not ov_file.exists():
        continue
    with open(ov_file, "r", encoding="utf-8") as f:
        ov = json.load(f)

    print(f"\n--- {m['home']} {m['score']} {m['away']} (净胜={goal_diff:+d}) ---")

    for r in ov.get("rows", []):
        f_data = r["first"]
        e_data = r.get("end") or f_data

        init_handi = f_data.get("handi", "?")
        end_handi = e_data.get("handi", "?")
        init_home = f_data.get("home", "?")
        end_home = e_data.get("home", "?")
        init_away = f_data.get("away", "?")
        end_away = e_data.get("away", "?")

        line_moved = init_handi != end_handi
        marker = " *** LINE MOVED" if line_moved else ""

        print(f"  {r['name']:<10} 初:{init_home}/{init_handi}/{init_away} → 终:{end_home}/{end_handi}/{end_away}{marker}")

        ah_results.append({
            "match": f"{m['home']}vs{m['away']}",
            "company": r["name"],
            "init_handi": init_handi,
            "end_handi": end_handi,
            "init_home": float(init_home) if init_home != "?" else 0,
            "end_home": float(end_home) if end_home != "?" else 0,
            "goal_diff": goal_diff,
            "line_moved": line_moved,
        })

# ============================================================
# 3. Over/Under analysis
# ============================================================
print("\n" + "=" * 80)
print("3. OVER/UNDER — Line vs Actual Goals")
print("=" * 80)

for m in finished:
    fid = m["qiu_fid"]
    h, a = map(int, m["score"].split(":"))
    total_goals = h + a

    ov_file = DATA / "qiu" / "overview" / f"{fid}_daxiao.json"
    if not ov_file.exists():
        continue
    with open(ov_file, "r", encoding="utf-8") as f:
        ov = json.load(f)

    print(f"\n--- {m['home']} {m['score']} {m['away']} (总进球={total_goals}) ---")

    for r in ov.get("rows", [])[:4]:
        f_data = r["first"]
        e_data = r.get("end") or f_data

        init_line = f_data.get("handi", "?")
        end_line = e_data.get("handi", "?")

        try:
            end_line_val = eval(end_line.replace("/", "+").replace("+", "+")) / (2 if "/" in end_line else 1) if "/" in end_line else float(end_line)
        except:
            end_line_val = 0

        over_under = "OVER" if total_goals > end_line_val else ("PUSH" if total_goals == end_line_val else "UNDER")

        print(f"  {r['name']:<10} 初盘:{init_line} → 终盘:{end_line}  实际:{total_goals}球 [{over_under}]")

# ============================================================
# 4. Time series: late movement analysis (last 6h before match)
# ============================================================
print("\n" + "=" * 80)
print("4. LATE MOVEMENT — Odds changes in final hours before kickoff")
print("=" * 80)

from datetime import datetime, timedelta

for m in finished:
    fid = m["qiu_fid"]
    result = result_from_score(m["score"])
    match_time = datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M")

    print(f"\n--- {m['home']} {m['score']} {m['away']} [{result}] ---")

    for cid in [3, 1055, 280]:  # Bet365, Pinnacle, 皇冠
        ts_file = DATA / "qiu" / "timeseries" / f"{fid}_{cid}_ouzhi.json"
        if not ts_file.exists():
            continue
        with open(ts_file, "r", encoding="utf-8") as f:
            ts = json.load(f)

        records = ts.get("records", [])
        if not records:
            continue

        # Find records in last 6 hours
        late_records = []
        for r in records:
            try:
                t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                if match_time - timedelta(hours=6) <= t <= match_time:
                    late_records.append(r)
            except:
                pass

        name = cid_names.get(str(cid), f"CID{cid}")
        if len(late_records) >= 2:
            first_r = late_records[0]
            last_r = late_records[-1]
            w_change = float(last_r["win"]) - float(first_r["win"])
            d_change = float(last_r["draw"]) - float(first_r["draw"])
            l_change = float(last_r["lost"]) - float(first_r["lost"])
            print(f"  {name:<10} 赛前6h变化({len(late_records)}次): 主胜{w_change:+.2f} 平局{d_change:+.2f} 客胜{l_change:+.2f}  | 终赔: {last_r['win']}/{last_r['draw']}/{last_r['lost']}")
        elif len(late_records) == 1:
            r = late_records[0]
            print(f"  {name:<10} 赛前6h仅1次变化  | 终赔: {r['win']}/{r['draw']}/{r['lost']}")
        else:
            if records:
                r = records[-1]
                print(f"  {name:<10} 赛前6h无变化  | 最后赔率: {r['win']}/{r['draw']}/{r['lost']}")

# ============================================================
# 5. "Cold game" detection: where favorites lost
# ============================================================
print("\n" + "=" * 80)
print("5. UPSET DETECTION — Favorites that didn't win")
print("=" * 80)

for m in finished:
    fid = m["qiu_fid"]
    result = result_from_score(m["score"])

    ov_file = DATA / "qiu" / "overview" / f"{fid}_ouzhi.json"
    if not ov_file.exists():
        continue
    with open(ov_file, "r", encoding="utf-8") as f:
        ov = json.load(f)

    # Use 百家欧赔 (CID 0) as reference
    avg = next((r for r in ov["rows"] if r["id"] == "0"), None)
    if not avg:
        continue

    e = avg.get("end") or avg["first"]
    win_odds = float(e["win"])
    draw_odds = float(e["draw"])
    lost_odds = float(e["lost"])
    win_prob = float(e.get("winrate") or e.get("wgl") or 0)

    # Determine favorite
    if win_odds < lost_odds:
        fav = "home"
        fav_odds = win_odds
        fav_prob = win_prob
    else:
        fav = "away"
        fav_odds = lost_odds
        fav_prob = 100 - win_prob - float(e.get("drawrate") or e.get("dgl") or 0)

    is_upset = (fav == "home" and result != "win") or (fav == "away" and result != "lost")

    result_cn = {"win": "主胜", "draw": "平局", "lost": "客胜"}[result]
    fav_team = m["home"] if fav == "home" else m["away"]

    if is_upset:
        print(f"\n  ⚠ UPSET: {m['home']} {m['score']} {m['away']}")
        print(f"    热门: {fav_team} (赔率{fav_odds:.2f}, 胜率{fav_prob:.1f}%)")
        print(f"    结果: {result_cn}")
        print(f"    终赔: {e['win']}/{e['draw']}/{e['lost']}")

        # Check if Asian handicap warned about this
        ah_file = DATA / "qiu" / "overview" / f"{fid}_yazhi.json"
        if ah_file.exists():
            with open(ah_file, "r", encoding="utf-8") as f:
                ah = json.load(f)
            for r in ah.get("rows", [])[:3]:
                ed = r.get("end") or r["first"]
                fd = r["first"]
                init_h = fd.get("handi", "?")
                end_h = ed.get("handi", "?")
                if init_h != end_h:
                    print(f"    亚盘信号 {r['name']}: {init_h} → {end_h} (盘口缩水!)")
    else:
        print(f"  ✓ Expected: {m['home']} {m['score']} {m['away']} — {fav_team}获胜 (赔率{fav_odds:.2f})")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
