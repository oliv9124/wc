"""Predict upcoming World Cup matches using 500.com + qiu odds data.

Signals (priority order):
  1. 挤平+退盘共振 — draw-squeeze + AH-retreat together → strong draw
  2. IP Drift — implied-probability shift from initial→final EU odds
     - >3% → contrarian (bet opposite)
     - 2-3% → follow direction
     - <2% → weak
  3. Pinnacle divergence — sharp vs public bookmaker split
  4. 百家欧赔/凯利 — qiu consensus + kelly anomaly
  5. OU trend — over/under line movement direction

Data: data/w500/{w500_mid}.json + data/qiu/overview/{qiu_fid}_*.json

Usage: python predict.py [date]   (default: first upcoming date)
"""
import json, sys, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent
CONFIG = ROOT / "worldcup_fids.json"
W500_DIR = ROOT / "data" / "w500"
QIU_DIR = ROOT / "data" / "qiu" / "overview"

SHARP = ["1055"]
PUBLIC = ["293", "3", "2", "280", "9", "6"]
ALL_KEY = SHARP + PUBLIC + ["5"]

CID_NAMES = {
    "293": "威廉希尔", "1055": "Pinnacle", "3": "Bet365", "2": "立博",
    "280": "皇冠", "9": "易胜博", "6": "伟德", "348": "金宝博",
    "651": "利记", "5": "澳门", "11": "Bwin", "4": "Interwetten",
    "8": "SNAI", "14": "Coral",
}

RESULT_CN = {"win": "主胜", "draw": "平局", "lose": "客胜"}
LABELS = ["win", "draw", "lose"]

HANDICAP_MAP = {
    "平手": 0, "平手/半球": 0.25, "半球": 0.5, "半球/一球": 0.75,
    "一球": 1.0, "一球/球半": 1.25, "球半": 1.5, "球半/两球": 1.75,
    "两球": 2.0, "两球/两球半": 2.25, "两球半": 2.5, "两球半/三球": 2.75,
    "三球": 3.0, "三球/三球半": 3.25, "三球半": 3.5, "四球": 4.0,
}

# ── Utilities ──

def parse_handicap(text):
    text = re.sub(r"\s*[升降]$", "", text.strip())
    neg = text.startswith("受")
    if neg:
        text = text[1:]
    val = HANDICAP_MAP.get(text)
    if val is None:
        try:
            val = float(text)
        except ValueError:
            return None
    return -val if neg else val

def ip3(w, d, l):
    raw = [100 / w, 100 / d, 100 / l]
    t = sum(raw)
    return [x / t * 100 for x in raw]

def dominant(vals):
    idx = max(range(3), key=lambda i: vals[i])
    return LABELS[idx], vals[idx]

def load_match(mid):
    p = W500_DIR / f"{mid}.json"
    if not p.exists(): return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Signals Detectors ──

def detect_squeeze_draw(companies, cids):
    squeeze = 0
    total = 0
    draw_ip_deltas = []
    details = []
    for cid in cids:
        c = companies.get(cid)
        if not c or not c.get("eu") or len(c["eu"]) < 2: continue
        eu = c["eu"]
        total += 1
        init_d = float(eu[-1][1])
        final_d = float(eu[0][1])
        try:
            ip_i = ip3(float(eu[-1][0]), float(eu[-1][1]), float(eu[-1][2]))
            ip_f = ip3(float(eu[0][0]), float(eu[0][1]), float(eu[0][2]))
            draw_ip_deltas.append(ip_f[1] - ip_i[1])
        except: continue
        if final_d < init_d - 0.1:
            squeeze += 1
            name = CID_NAMES.get(cid, cid)
            details.append(f"{name} {init_d:.2f}→{final_d:.2f}")
    avg_draw_ip = sum(draw_ip_deltas) / len(draw_ip_deltas) if draw_ip_deltas else 0
    return {"count": squeeze, "total": total, "avg_draw_ip": avg_draw_ip, "details": details}

def detect_ah_retreat(companies, cids):
    retreat = 0
    total = 0
    details = []
    for cid in cids:
        c = companies.get(cid)
        if not c or not c.get("ah") or len(c["ah"]) < 2: continue
        total += 1
        init_h = parse_handicap(c["ah"][-1][1])
        final_h = parse_handicap(c["ah"][0][1])
        if init_h is None or final_h is None: continue
        if abs(final_h) < abs(init_h) - 0.2:
            retreat += 1
            name = CID_NAMES.get(cid, cid)
            details.append(f"{name} {c['ah'][-1][1]}→{c['ah'][0][1]}")
    return {"count": retreat, "total": total, "details": details}

def detect_ah_upgrade(companies, cids):
    upgrade = 0
    total = 0
    details = []
    for cid in cids:
        c = companies.get(cid)
        if not c or not c.get("ah") or len(c["ah"]) < 2: continue
        total += 1
        init_h = parse_handicap(c["ah"][-1][1])
        final_h = parse_handicap(c["ah"][0][1])
        if init_h is None or final_h is None: continue
        if abs(final_h) > abs(init_h) + 0.2:
            upgrade += 1
            name = CID_NAMES.get(cid, cid)
            details.append(f"{name} {c['ah'][-1][1]}→{c['ah'][0][1]}")
    return {"count": upgrade, "total": total, "details": details}

def compute_ip_drift(companies, cids):
    drifts_per_co = []
    for cid in cids:
        c = companies.get(cid)
        if not c or not c.get("eu") or len(c["eu"]) < 2: continue
        eu = c["eu"]
        try:
            ip_i = ip3(float(eu[-1][0]), float(eu[-1][1]), float(eu[-1][2]))
            ip_f = ip3(float(eu[0][0]), float(eu[0][1]), float(eu[0][2]))
        except: continue
        drifts_per_co.append({
            "cid": cid, "drift": [ip_f[j] - ip_i[j] for j in range(3)],
            "init": [float(eu[-1][0]), float(eu[-1][1]), float(eu[-1][2])],
            "final": [float(eu[0][0]), float(eu[0][1]), float(eu[0][2])],
            "n": len(eu)
        })
    if not drifts_per_co: return None
    n = len(drifts_per_co)
    avg = [sum(d["drift"][j] for d in drifts_per_co) / n for j in range(3)]
    return {"avg": avg, "per_co": drifts_per_co, "count": n}

def analyze_ou(companies, cids):
    moves = []
    for cid in cids:
        c = companies.get(cid)
        if not c or not c.get("ou") or len(c["ou"]) < 2: continue
        try:
            moves.append({
                "name": CID_NAMES.get(cid, cid),
                "init_line": float(c["ou"][-1][1]), "final_line": float(c["ou"][0][1]),
                "init_bw": float(c["ou"][-1][0]), "final_bw": float(c["ou"][0][0]),
            })
        except: continue
    return moves

def load_qiu(fid, kind):
    p = QIU_DIR / f"{fid}_{kind}.json"
    if not p.exists(): return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_qiu_eu(qiu_eu):
    if not qiu_eu or "rows" not in qiu_eu: return None
    rows = qiu_eu["rows"]
    avg = next((r for r in rows if r["id"] == "0"), None)
    jc = next((r for r in rows if r["id"] == "1"), None)
    result = {}
    if avg:
        f, e = avg["first"], avg.get("end") or avg["first"]
        try:
            ip_i = ip3(float(f["win"]), float(f["draw"]), float(f["lost"]))
            ip_e = ip3(float(e["win"]), float(e["draw"]), float(e["lost"]))
            result["avg100"] = {
                "init": [float(f["win"]), float(f["draw"]), float(f["lost"])],
                "final": [float(e["win"]), float(e["draw"]), float(e["lost"])],
                "drift": [ip_e[i] - ip_i[i] for i in range(3)],
                "winrate": float(e.get("winrate") or e.get("wgl") or 0),
                "drawrate": float(e.get("drawrate") or e.get("dgl") or 0),
            }
            result["avg100"]["loserate"] = round(100 - result["avg100"]["winrate"] - result["avg100"]["drawrate"], 1)
        except: pass
    
    kelly_prot = {"win": 0, "draw": 0, "lose": 0}
    kelly_total = 0
    for r in rows:
        if r["id"] == "0": continue
        e = r.get("end") or r.get("first")
        if not isinstance(e, dict): continue
        try:
            if float(e.get("winkl", 1)) < 0.90: kelly_prot["win"] += 1
            if float(e.get("drawkl", 1)) < 0.90: kelly_prot["draw"] += 1
            if float(e.get("lostkl", 1)) < 0.90: kelly_prot["lose"] += 1
            kelly_total += 1
        except: continue
    result["kelly_prot"] = kelly_prot
    result["kelly_total"] = kelly_total

    if jc and isinstance(jc.get("first"), dict) and jc["first"]:
        f, e = jc["first"], jc.get("end") or jc["first"]
        if not isinstance(e, dict): e = f
        try:
            ip_i = ip3(float(f["win"]), float(f["draw"]), float(f["lost"]))
            ip_e = ip3(float(e["win"]), float(e["draw"]), float(e["lost"]))
            result["jc"] = {
                "init": [float(f["win"]), float(f["draw"]), float(f["lost"])],
                "final": [float(e["win"]), float(e["draw"]), float(e["lost"])],
                "drift": [ip_e[i] - ip_i[i] for i in range(3)],
            }
        except: pass
    return result

def ah_overview(companies, cids):
    rows = []
    for cid in cids:
        c = companies.get(cid)
        if not c or not c.get("ah") or len(c["ah"]) < 2: continue
        ah = c["ah"]
        rows.append({
            "name": CID_NAMES.get(cid, cid),
            "init": f"{ah[-1][0]}/{ah[-1][1]}/{ah[-1][2]}",
            "final": f"{ah[0][0]}/{ah[0][1]}/{ah[0][2]}",
            "n": len(ah)
        })
    return rows

# ── Core Analysis Engine ──

def analyze_match_core(m, data, qiu_eu):
    """Analyze a single match and return a structured dictionary of signals and predictions."""
    companies = data.get("companies", {})
    score = m.get("score", "")
    
    result_actual = None
    if score:
        hs, as_ = score.split(":")
        if hs == as_: result_actual = "draw"
        elif int(hs) > int(as_): result_actual = "win"
        else: result_actual = "lose"
        
    res = {
        "match": m,
        "score": score,
        "result_actual": result_actual,
        "signals": [],
        "strategies": [],
        "recommendation": None,
        "final_pred": None,
        "favorite": None,
        "is_hit": False
    }

    drift_all = compute_ip_drift(companies, ALL_KEY)
    drift_sharp = compute_ip_drift(companies, SHARP)
    drift_pub = compute_ip_drift(companies, PUBLIC)
    res["eu"] = {"all": drift_all, "sharp": drift_sharp, "pub": drift_pub}

    # Extract initial odds for filter logic
    init_w, init_d, init_l = 0, 0, 0
    if qiu_eu and "rows" in qiu_eu:
        avg_row = next((r for r in qiu_eu["rows"] if r["id"] == "0"), None)
        if avg_row:
            init_w = float(avg_row["first"]["win"])
            init_d = float(avg_row["first"]["draw"])
            init_l = float(avg_row["first"]["lost"])
    if init_w == 0 and drift_all:
        init_w, init_d, init_l = drift_all["per_co"][0]["init"]
        
    favorite_odds = min(init_w, init_l) if init_w > 0 else 0
    res["favorite"] = "win" if init_w < init_l else "lose"

    sq = detect_squeeze_draw(companies, ALL_KEY)
    ar = detect_ah_retreat(companies, ALL_KEY)
    au = detect_ah_upgrade(companies, ALL_KEY)
    res["ah_moves"] = {"sq": sq, "ar": ar, "au": au}

    sq_count = sq["count"]
    draw_drift = drift_all["avg"][1] if drift_all else 0
    
    if sq_count >= 8:
        res["signals"].append({"tag": "A+", "msg": f"超级挤平({sq_count}家) → 强制覆盖推荐平局", "lv": "HIGH"})
        res["strategies"].append("super_squeeze")
    elif sq_count >= 7 and draw_drift > 1.0:
        res["signals"].append({"tag": "A+", "msg": f"中度挤平({sq_count}家) + 资金流入平局 → 高级平局信号", "lv": "HIGH"})
        res["strategies"].append("medium_squeeze_upgrade")
    elif sq_count >= 2 and ar["count"] >= 2:
        res["signals"].append({"tag": "A", "msg": f"挤平+退盘共振(挤{sq_count}退{ar['count']}) → 强平局信号", "lv": "HIGH"})
        res["strategies"].append("squeeze_retreat_strong")
    elif sq_count >= 3 and ar["count"] >= 1:
        res["signals"].append({"tag": "A", "msg": f"挤平{sq_count}家+退盘{ar['count']}家 → 平局信号", "lv": "HIGH"})
        res["strategies"].append("squeeze_retreat_strong")
    elif ar["count"] >= 3:
        res["signals"].append({"tag": "A", "msg": f"退盘{ar['count']}/{ar['total']}家 → 平局信号", "lv": "HIGH"})
        res["strategies"].append("squeeze_retreat_strong")
    elif sq_count >= 3 or sq["avg_draw_ip"] > 1.5:
        res["signals"].append({"tag": "A", "msg": f"挤平明显({sq_count}家) → 防平", "lv": "MED"})
    elif ar["count"] >= 2:
        res["signals"].append({"tag": "A", "msg": f"退盘{ar['count']}家 → 热门信心不足", "lv": "MED"})
    elif sq_count >= 1 or ar["count"] >= 1:
        res["signals"].append({"tag": "A", "msg": "轻微挤平/退盘 → 关注", "lv": "LOW"})
    else:
        res["signals"].append({"tag": "A", "msg": "无挤平退盘", "lv": "LOW"})

    res["ou"] = analyze_ou(companies, ALL_KEY)
    if res["ou"]:
        line_drops = sum(1 for om in res["ou"] if om["final_line"] - om["init_line"] < -0.2)
        line_rises = sum(1 for om in res["ou"] if om["final_line"] - om["init_line"] > 0.2)
        if line_drops >= 2: res["signals"].append({"tag": "C", "msg": f"大小球降盘{line_drops}家 → 看小球", "lv": "MED"})
        elif line_rises >= 2: res["signals"].append({"tag": "C", "msg": f"大小球升盘{line_rises}家 → 看大球", "lv": "MED"})

    qiu_sig = analyze_qiu_eu(qiu_eu)
    res["qiu"] = qiu_sig
    
    kelly_shield = False
    kelly_shield_target = None
    
    if qiu_sig:
        if "kelly_prot" in qiu_sig:
            kp = qiu_sig["kelly_prot"]
            kt = qiu_sig.get("kelly_total", 0)
            top_k = max(kp, key=kp.get)
            if kt > 0 and kp[top_k] >= max(7, int(kt * 0.50)):
                if favorite_odds > 0 and favorite_odds < 1.05:
                    res["signals"].append({"tag": "D", "msg": f"极端悬殊盘(<1.05)禁用防爆罩", "lv": "LOW"})
                else:
                    res["signals"].append({"tag": "D", "msg": f"防爆罩: {kp[top_k]}/{kt}家死守{RESULT_CN[top_k]}", "lv": "HIGH"})
                    kelly_shield = True
                    kelly_shield_target = top_k
                    res["strategies"].append("kelly_shield")
            elif kp[top_k] >= 6 and kp[top_k] > sorted(kp.values())[-2] + 2:
                res["signals"].append({"tag": "D", "msg": f"凯利: {kp[top_k]}/{kt}家保护{RESULT_CN[top_k]}", "lv": "MED"})
        
        if "jc" in qiu_sig and drift_all:
            jc_dom, jc_val = dominant(qiu_sig["jc"]["drift"])
            w500_dom, _ = dominant(drift_all["avg"])
            if jc_dom != w500_dom and abs(jc_val) > 1.0:
                res["signals"].append({"tag": "D+", "msg": f"竞彩分歧 → 信市场: {RESULT_CN[w500_dom]}(回测4/5)", "lv": "MED"})

    is_fake_upgrade = False
    fake_upgrade_anti = None
    if drift_all:
        avg = drift_all["avg"]
        dom_label, dom_val = dominant(avg)
        mag = abs(dom_val)
        
        if drift_sharp and drift_pub:
            s_dom, _ = dominant(drift_sharp["avg"])
            p_dom, _ = dominant(drift_pub["avg"])
            if s_dom != p_dom:
                res["signals"].append({"tag": "B+", "msg": f"PIN分歧 → PIN看{RESULT_CN[s_dom]}(分歧时PIN更准)", "lv": "MED"})

        if au["count"] >= 4 and not kelly_shield and dom_val > 1.0:
            is_fake_upgrade = True
            fake_upgrade_anti = [l for l in LABELS if l != dom_label]
            res["strategies"].append("fake_upgrade")
            res["signals"].append({"tag": "A+", "msg": f"深盘诱多陷阱 → 坚决反向", "lv": "HIGH"})

        if mag > 3:
            s_init_w = drift_sharp["per_co"][0]["init"][0] if drift_sharp else 0
            if s_init_w > 0 and init_w > 0 and abs(s_init_w - init_w) > 0.10:
                res["signals"].append({"tag": "B", "msg": f"Pinnacle初盘纠错({s_init_w} vs 均值{init_w}) → 忽略异常漂移", "lv": "LOW"})
            else:
                anti = [RESULT_CN[LABELS[i]] for i in range(3) if LABELS[i] != dom_label]
                res["signals"].append({"tag": "B", "msg": f"IP漂移{dom_val:+.1f}%→{RESULT_CN[dom_label]} 强信号 → 反向: {'/'.join(anti)}", "lv": "HIGH"})
                res["recommendation"] = ("contrarian", dom_label, mag)
        elif mag > 2:
            res["signals"].append({"tag": "B", "msg": f"IP漂移{dom_val:+.1f}% → 跟庄: {RESULT_CN[dom_label]}", "lv": "MED"})
            res["recommendation"] = ("follow", dom_label, mag)
        else:
            res["signals"].append({"tag": "B", "msg": f"IP漂移{dom_val:+.1f}% 弱信号", "lv": "LOW"})
            
    has_squeeze_retreat = "squeeze_retreat_strong" in res["strategies"]
    
    if "super_squeeze" in res["strategies"]:
        res["final_pred"] = "draw"
        res["primary_logic"] = f"🔥 超级挤平({sq['count']}家) → 强制看平 (最高优先级)"
    elif kelly_shield:
        if favorite_odds > 0 and favorite_odds < 1.30 and kelly_shield_target != "draw" and kelly_shield_target != res["favorite"]:
            res["final_pred"] = "draw"
            res["primary_logic"] = f"🛡️ 深盘防爆罩转移 → 强队初赔{favorite_odds}防爆罩指向弱队，修正为防平局"
        else:
            res["final_pred"] = kelly_shield_target
            res["primary_logic"] = f"🛡️ 极端悬殊凯利防爆罩 → 防超级大冷: {RESULT_CN[kelly_shield_target]}"
    elif has_squeeze_retreat or "medium_squeeze_upgrade" in res["strategies"]:
        res["final_pred"] = "draw"
        res["primary_logic"] = "⚡ 挤平+退盘共振/中度挤平升格 → 平局 (优先级极高)"
    elif is_fake_upgrade:
        res["final_pred"] = "draw"
        res["primary_logic"] = f"🪤 深盘诱多陷阱 — 亚盘升盘({au['count']}家) + 资金流入 + 无凯利保护"
    elif res["recommendation"]:
        rtype, rdir, rmag = res["recommendation"]
        if rtype == "contrarian":
            non_dom = [(LABELS[i], drift_all["avg"][i]) for i in range(3) if LABELS[i] != rdir]
            non_dom.sort(key=lambda x: x[1], reverse=True)
            res["final_pred"] = "draw" if (sq["count"] >= 1 or ar["count"] >= 1) else non_dom[0][0]
            res["primary_logic"] = f"⚡ IP漂移反向 — 资金涌入{RESULT_CN[rdir]}({rmag:.1f}%), 反向"
        else:
            res["final_pred"] = rdir
            res["primary_logic"] = f"📈 跟庄 → {RESULT_CN[rdir]} (漂移{rmag:.1f}%)"
    else:
        res["final_pred"] = res["favorite"]
        res["primary_logic"] = f"✅ 无强信号 → 热门方向"
        
    if result_actual and res["final_pred"] == result_actual:
        res["is_hit"] = True

    res["ah_overview"] = ah_overview(companies, ALL_KEY)
    
    return res

# ── CLI Display ──

def display_match(res):
    m = res["match"]
    print(f"{'─' * 70}")
    print(f"  {m['time']}  {m['home']} vs {m['away']}  ({m.get('group','')}组)")
    if res["score"]:
        print(f"  赛果: {res['score']} ({RESULT_CN[res['result_actual']]})")
    print(f"{'─' * 70}")

    if res["eu"]["all"]:
        print("\n  【欧赔变动】")
        for d in res["eu"]["all"]["per_co"]:
            name = CID_NAMES.get(d["cid"], d["cid"])
            dr = d["drift"]
            init_s = "/".join(f"{v:.2f}" for v in d["init"])
            final_s = "/".join(f"{v:.2f}" for v in d["final"])
            print(f"    {name:<8} {init_s} → {final_s}  IP: W{dr[0]:+.1f} D{dr[1]:+.1f} L{dr[2]:+.1f} [{d['n']}变]")

    sq, ar, au = res["ah_moves"]["sq"], res["ah_moves"]["ar"], res["ah_moves"]["au"]
    print(f"\n  【信号A: 挤平+退盘/升盘】")
    print(f"    挤平: {sq['count']}/{sq['total']}家平赔下降 (平局IP均漂{sq['avg_draw_ip']:+.2f}%)")
    for d in sq["details"]: print(f"      {d}")
    if ar["count"] > 0:
        print(f"    退盘: {ar['count']}/{ar['total']}家盘口回退")
        for d in ar["details"]: print(f"      {d}")
    if au["count"] > 0:
        print(f"    升盘: {au['count']}/{au['total']}家盘口升级")
        for d in au["details"]: print(f"      {d}")

    print(f"\n  【信号B: IP漂移】")
    if res["eu"]["all"]:
        avg = res["eu"]["all"]["avg"]
        dom_label, _ = dominant(avg)
        print(f"    综合: W{avg[0]:+.2f}% D{avg[1]:+.2f}% L{avg[2]:+.2f}% → 资金方向: {RESULT_CN[dom_label]}")
        if res["eu"]["sharp"]:
            sa = res["eu"]["sharp"]["avg"]
            s_dom, _ = dominant(sa)
            print(f"    Pinnacle: W{sa[0]:+.2f}% D{sa[1]:+.2f}% L{sa[2]:+.2f}% → {RESULT_CN[s_dom]}")
        if res["eu"]["pub"]:
            pa = res["eu"]["pub"]["avg"]
            p_dom, _ = dominant(pa)
            print(f"    大众: W{pa[0]:+.2f}% D{pa[1]:+.2f}% L{pa[2]:+.2f}% → {RESULT_CN[p_dom]}")

    if res["ah_overview"]:
        print(f"\n  【亚盘总览】")
        for r in res["ah_overview"]:
            print(f"    {r['name']:<8} {r['init']} → {r['final']}  [{r['n']}变]")

    if res["ou"]:
        print(f"\n  【大小球】")
        for om in res["ou"]:
            delta = om["final_line"] - om["init_line"]
            arrow = "↓" if delta < 0 else ("↑" if delta > 0 else "→")
            bw_chg = om["final_bw"] - om["init_bw"]
            print(f"    {om['name']:<8} {om['init_line']}{arrow}{om['final_line']}  大球水{om['init_bw']:.2f}→{om['final_bw']:.2f}({bw_chg:+.2f})")

    q = res["qiu"]
    if q:
        print(f"\n  【球球: 百家欧赔+凯利】")
        if "avg100" in q:
            a = q["avg100"]
            init_s = "/".join(f"{v:.2f}" for v in a["init"])
            final_s = "/".join(f"{v:.2f}" for v in a["final"])
            dr = a["drift"]
            print(f"    百家欧赔: {init_s} → {final_s} | IP漂移: W{dr[0]:+.2f}% D{dr[1]:+.2f}% L{dr[2]:+.2f}%")
        if "kelly_prot" in q:
            kp = q["kelly_prot"]
            kt = q.get("kelly_total", 0)
            print(f"    凯利保护(<0.90): 主胜{kp['win']}/{kt} 平局{kp['draw']}/{kt} 客胜{kp['lose']}/{kt}")

    print(f"\n  {'━' * 50}")
    print(f"  信号汇总:")
    icon_map = {"HIGH": "🔴", "MED": "🟡", "LOW": "🟢"}
    for s in res["signals"]:
        print(f"    {icon_map[s['lv']]} [{s['tag']}] {s['msg']}")

    print(f"\n  📊 综合推荐:")
    print(f"     {res['primary_logic']}")
    if res["score"] and res["final_pred"]:
        mark = "✓ 命中" if res["is_hit"] else "✗ 未中"
        print(f"\n  🎯 预测: {RESULT_CN.get(res['final_pred'], '?')} | 赛果: {RESULT_CN[res['result_actual']]} | {mark}")
    print()


def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)

    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    if not target_date:
        upcoming = [m["date"] for m in config["matches"] if m.get("status") != "finished"]
        target_date = min(upcoming) if upcoming else max(m["date"] for m in config["matches"])

    matches = [m for m in config["matches"] if m["date"] == target_date]
    if not matches:
        print(f"No matches on {target_date}")
        sys.exit(1)

    mode = "review" if matches[0].get("status") == "finished" else "predict"
    print(f"{'=' * 70}\n  {'复盘' if mode == 'review' else '预测'}: {target_date} ({len(matches)} matches)\n{'=' * 70}\n")

    hits = 0
    total_pred = 0

    for m in matches:
        mid = m.get("w500_mid")
        if not mid: continue
        data = load_match(mid)
        if not data: continue
        
        fid = m.get("qiu_fid")
        qiu_eu = load_qiu(fid, "ouzhi") if fid else None
        
        res = analyze_match_core(m, data, qiu_eu)
        display_match(res)
        
        if res["score"] and res["final_pred"]:
            total_pred += 1
            if res["is_hit"]: hits += 1

    if mode == "review" and total_pred > 0:
        print(f"{'=' * 70}\n  命中率: {hits}/{total_pred} ({hits/total_pred*100:.0f}%)\n{'=' * 70}")

if __name__ == "__main__":
    main()
