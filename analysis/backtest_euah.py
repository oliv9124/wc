"""Backtest: Euro-Asian discrepancy + Kelly anomaly + water movement signals."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

config = json.load(open(ROOT / "worldcup_fids.json", "r", encoding="utf-8"))
finished = [m for m in config["matches"] if m.get("status") == "finished"]

CN = {"win": "主胜", "draw": "平局", "lost": "客胜"}


def load_j(p):
    if not p.exists():
        return None
    return json.load(open(p, "r", encoding="utf-8"))


def parse_handi(h):
    h = str(h).strip()
    if "/" in h:
        parts = h.split("/")
        try:
            vals = [float(p) for p in parts]
            if vals[0] < 0 and vals[1] > 0:
                vals[1] = -vals[1]
            return sum(vals) / len(vals)
        except:
            return None
    try:
        return float(h)
    except:
        return None


def actual_result(score):
    h, a = score.split(":")
    h, a = int(h), int(a)
    return "win" if h > a else ("draw" if h == a else "lost")


def is_upset(actual, home_fav):
    return (home_fav and actual != "win") or (not home_fav and actual != "lost")


# ================================================================
#  策略1: 欧亚盘口不一致
# ================================================================
print("=" * 90)
print("  【策略1: 欧亚盘口不一致】")
print("  欧赔概率差→推算让球数→对比实际亚盘")
print("  偏差>0 = 让球浅于预期 = 诱上盘; 偏差<0 = 让球深于预期 = 真看好")
print("=" * 90)

print("{:<16} {:<4} {:>6} {:>6} {:>6} {:>6} {:>7} {:>6}".format(
    "比赛", "结果", "欧胜%", "欧负%", "预期盘", "实盘", "偏差", "判定"))
print("-" * 90)

s1_ok, s1_n = 0, 0

for m in finished:
    fid = m["qiu_fid"]
    score = m.get("score", "")
    label = f"{m['home']}vs{m['away']}"
    actual = actual_result(score)

    eu = load_j(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    ah = load_j(DATA / "qiu" / "overview" / f"{fid}_yazhi.json")
    if not eu or not ah:
        continue

    avg_eu = next((r for r in eu["rows"] if r["id"] == "0"), None)
    if not avg_eu:
        continue
    ed = avg_eu.get("end") or avg_eu["first"]
    w, d, l = float(ed["win"]), float(ed["draw"]), float(ed["lost"])
    p_h, p_d, p_a = 1/w, 1/d, 1/l
    tot = p_h + p_d + p_a
    p_h, p_a = p_h / tot, p_a / tot

    expected_ah = -(p_h - p_a) * 100 / 40.0

    ah_vals = []
    for r in ah.get("rows", []):
        ed_ah = r.get("end") or r["first"]
        h = parse_handi(ed_ah.get("handi", "0"))
        if h is not None:
            ah_vals.append(h)
    if not ah_vals:
        continue
    actual_ah = sum(ah_vals) / len(ah_vals)

    gap = actual_ah - expected_ah
    home_fav = p_h > p_a

    verdict = ""
    if abs(gap) > 0.25:
        s1_n += 1
        if gap > 0:
            ok = is_upset(actual, home_fav)
            verdict = "诱盘 V" if ok else "诱盘 X"
        else:
            ok = (actual == "win") if home_fav else (actual == "lost")
            verdict = "真深 V" if ok else "真深 X"
        if ok:
            s1_ok += 1
    else:
        verdict = "一致"

    print("{:<16} {:<4} {:>5.1f}% {:>5.1f}% {:>6.2f} {:>6.2f} {:>+7.2f} {:>6}".format(
        label[:16], CN[actual], p_h*100, p_a*100, expected_ah, actual_ah, gap, verdict))

print("-" * 90)
print(f"  命中: {s1_ok}/{s1_n} = {100*s1_ok/s1_n:.0f}%" if s1_n else "  无有效信号")


# ================================================================
#  策略2: 凯利指数异常 (各公司)
# ================================================================
print(f"\n{'=' * 90}")
print("  【策略2: 凯利指数异常(各公司)】")
print("  统计所有公司终盘凯利<0.85的数量, 哪个结果被压低最多→庄家保护该方向")
print("=" * 90)

print("{:<16} {:<4} {:>6} {:>6} {:>6} {:>10} {:>4}".format(
    "比赛", "结果", "胜低KL", "平低KL", "负低KL", "庄家看→", "正确"))
print("-" * 90)

s2_ok, s2_n = 0, 0

for m in finished:
    fid = m["qiu_fid"]
    score = m.get("score", "")
    label = f"{m['home']}vs{m['away']}"
    actual = actual_result(score)

    eu = load_j(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    if not eu:
        continue

    low_w, low_d, low_l = 0, 0, 0
    for r in eu["rows"]:
        if r["id"] == "0":
            continue
        ed = r.get("end") or r["first"]
        if not isinstance(ed, dict):
            continue
        try:
            wkl = float(ed.get("winkl", "1.0"))
            dkl = float(ed.get("drawkl", "1.0"))
            lkl = float(ed.get("lostkl", "1.0"))
        except (ValueError, TypeError):
            continue
        if wkl < 0.85:
            low_w += 1
        if dkl < 0.85:
            low_d += 1
        if lkl < 0.85:
            low_l += 1

    counts = {"win": low_w, "draw": low_d, "lost": low_l}
    top = max(counts, key=counts.get)
    top_v = counts[top]

    verdict = ""
    if top_v >= 3 and top_v > sorted(counts.values())[-2] + 1:
        s2_n += 1
        ok = actual == top
        verdict = "V" if ok else "X"
        if ok:
            s2_ok += 1
        signal = CN[top]
    else:
        signal = "分散"
        verdict = "-"

    print("{:<16} {:<4} {:>6} {:>6} {:>6} {:>10} {:>4}".format(
        label[:16], CN[actual], low_w, low_d, low_l, signal, verdict))

print("-" * 90)
print(f"  命中: {s2_ok}/{s2_n} = {100*s2_ok/s2_n:.0f}%" if s2_n else "  无有效信号")


# ================================================================
#  策略3: 亚盘水位变动方向
# ================================================================
print(f"\n{'=' * 90}")
print("  【策略3: 亚盘水位变动】")
print("  各公司主水平均变化: 升水→庄家想赶走上盘资金→看好上盘(主队)")
print("  降水→庄家吸引上盘资金→诱上盘→主队有风险")
print("=" * 90)

print("{:<16} {:<4} {:>8} {:>8} {:>6} {:>4} {:>10} {:>4}".format(
    "比赛", "结果", "初主水", "终主水", "变化", "盘变", "信号", "正确"))
print("-" * 90)

s3_ok, s3_n = 0, 0

for m in finished:
    fid = m["qiu_fid"]
    score = m.get("score", "")
    label = f"{m['home']}vs{m['away']}"
    actual = actual_result(score)

    ah = load_j(DATA / "qiu" / "overview" / f"{fid}_yazhi.json")
    if not ah:
        continue

    hw_deltas = []
    handi_changes = 0
    for r in ah.get("rows", []):
        fd = r["first"]
        ed = r.get("end") or fd
        try:
            hw_i = float(fd["home"])
            hw_e = float(ed["home"])
            hw_deltas.append(hw_e - hw_i)
        except:
            pass
        hi = parse_handi(fd.get("handi", "0"))
        he = parse_handi(ed.get("handi", "0"))
        if hi is not None and he is not None and abs(hi - he) >= 0.2:
            handi_changes += 1

    if not hw_deltas:
        continue

    avg_hw_init = 0
    avg_hw_end = 0
    for r in ah.get("rows", []):
        fd = r["first"]
        ed = r.get("end") or fd
        try:
            avg_hw_init += float(fd["home"])
            avg_hw_end += float(ed["home"])
        except:
            pass
    n_rows = len(hw_deltas)
    avg_hw_init /= n_rows
    avg_hw_end /= n_rows
    avg_delta = sum(hw_deltas) / len(hw_deltas)

    eu = load_j(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    home_fav = False
    if eu:
        avg_eu = next((r for r in eu["rows"] if r["id"] == "0"), None)
        if avg_eu:
            ed_eu = avg_eu.get("end") or avg_eu["first"]
            home_fav = float(ed_eu["win"]) < float(ed_eu["lost"])

    verdict = ""
    signal = ""
    if abs(avg_delta) > 0.05:
        s3_n += 1
        if avg_delta > 0.05:
            # Home water rising → bookmaker discouraging home bets → home likely good
            signal = "升水看主"
            ok = actual == "win"
        else:
            # Home water dropping → bookmaker attracting home bets → trap
            signal = "降水诱主"
            ok = actual != "win"
        verdict = "V" if ok else "X"
        if ok:
            s3_ok += 1
    else:
        signal = "水位稳"
        verdict = "-"

    print("{:<16} {:<4} {:>8.3f} {:>8.3f} {:>+6.3f} {:>4} {:>10} {:>4}".format(
        label[:16], CN[actual], avg_hw_init, avg_hw_end, avg_delta,
        handi_changes, signal, verdict))

print("-" * 90)
print(f"  命中: {s3_ok}/{s3_n} = {100*s3_ok/s3_n:.0f}%" if s3_n else "  无有效信号")


# ================================================================
#  汇总
# ================================================================
print(f"\n\n{'=' * 90}")
print("  回测汇总")
print("=" * 90)
print(f"  策略1 欧亚不一致:    {s1_ok}/{s1_n} = {100*s1_ok/s1_n:.0f}%" if s1_n else "  策略1 欧亚不一致:    无信号")
print(f"  策略2 凯利指数异常:  {s2_ok}/{s2_n} = {100*s2_ok/s2_n:.0f}%" if s2_n else "  策略2 凯利指数异常:  无信号")
print(f"  策略3 水位变动:      {s3_ok}/{s3_n} = {100*s3_ok/s3_n:.0f}%" if s3_n else "  策略3 水位变动:      无信号")
print(f"\n  对比: 现有IP漂移策略 5/6=83%(强信号) + 2/2=100%(中等信号)")
print("=" * 90)
