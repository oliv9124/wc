"""Deep analysis of 4 problem matches using okooo change history (25 companies)."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent
DATA = ROOT / "data"

PROBLEM_MATCHES = [
    {"ok_mid": "1315867", "label": "美国vs巴拉圭", "score": "4:1", "actual": "主胜", "qiu_signal": "IP+2.3%跟庄→平局 ❌"},
    {"ok_mid": "1315868", "label": "澳大利亚vs土耳其", "score": "2:0", "actual": "主胜", "qiu_signal": "弱信号→按热门土耳其 ❌"},
    {"ok_mid": "1315875", "label": "荷兰vs日本", "score": "2:2", "actual": "平局", "qiu_signal": "弱信号→按热门荷兰+水位升 ❌"},
    {"ok_mid": "1315869", "label": "巴西vs摩洛哥", "score": "1:1", "actual": "平局", "qiu_signal": "弱IP+降水诱主 (辅助对)"},
]

CID_NAMES = {
    "24": "99家平均", "2": "竞彩官方", "14": "威廉希尔", "82": "立博",
    "27": "Bet365", "43": "Interwetten", "25": "SNAI", "94": "bwin",
    "131": "香港马会", "65": "伟德", "35": "易胜博", "180": "Unibet",
    "19": "必发Betfair", "84": "澳门", "116": "Coral", "49": "PaddyPower",
    "307": "Mansion88", "250": "皇冠", "220": "沙巴", "280": "利记",
    "322": "金宝博", "202": "10Bet", "406": "12bet", "744": "1xbet", "157": "Skybet",
}

BIG_EU = ["14", "82", "27", "94", "116", "49", "157"]  # 欧洲大庄
BIG_ASIA = ["250", "220", "65", "35", "280", "322", "307"]  # 亚洲大庄
EXCHANGE = ["19"]  # 交易所 (Betfair)


def load_j(p):
    if not p.exists():
        return None
    return json.load(open(p, "r", encoding="utf-8"))


def analyze_match(m):
    mid = m["ok_mid"]
    print(f"\n{'='*90}")
    print(f"  {m['label']}  {m['score']} ({m['actual']})")
    print(f"  球球信号: {m['qiu_signal']}")
    print(f"{'='*90}")

    all_drifts = []  # (cid, name, drift_w, drift_d, drift_l, n_changes, last_change_dir)

    for cid in CID_NAMES:
        f = DATA / "okooo" / "changes" / f"{mid}_{cid}_odds.json"
        d = load_j(f)
        if not d or not d.get("records"):
            continue

        recs = d["records"]
        init_rec = next((r for r in recs if r.get("tag") == "init"), recs[-1])
        final_rec = next((r for r in recs if r.get("tag") == "final"), recs[0])

        try:
            iw, id_, il = float(init_rec["win"]), float(init_rec["draw"]), float(init_rec["lost"])
            fw, fd, fl = float(final_rec["win"]), float(final_rec["draw"]), float(final_rec["lost"])
        except (ValueError, KeyError):
            continue

        ip_i = [1/iw, 1/id_, 1/il]
        ip_f = [1/fw, 1/fd, 1/fl]
        ti, tf = sum(ip_i), sum(ip_f)
        ip_i = [x/ti*100 for x in ip_i]
        ip_f = [x/tf*100 for x in ip_f]

        drift = [ip_f[i] - ip_i[i] for i in range(3)]
        n_changes = len(recs)

        # Last change direction (within 24h of match)
        last_dir = None
        if len(recs) >= 2:
            r0, r1 = recs[0], recs[1]  # recs[0] is most recent
            try:
                lw = 1/float(r0["win"]) - 1/float(r1["win"])
                last_dir = "主" if lw > 0 else ("客" if lw < -0.001 else "平")
            except:
                pass

        # Kelly drift
        kelly_drift = None
        try:
            ik = [float(init_rec["kelly_w"]), float(init_rec["kelly_d"]), float(init_rec["kelly_l"])]
            fk = [float(final_rec["kelly_w"]), float(final_rec["kelly_d"]), float(final_rec["kelly_l"])]
            kelly_drift = [fk[i] - ik[i] for i in range(3)]
        except:
            pass

        all_drifts.append({
            "cid": cid, "name": CID_NAMES[cid],
            "drift": drift, "n_changes": n_changes, "last_dir": last_dir,
            "kelly_drift": kelly_drift,
            "init_odds": [iw, id_, il], "final_odds": [fw, fd, fl],
            "init_pay": init_rec.get("pay", ""), "final_pay": final_rec.get("pay", ""),
        })

    if not all_drifts:
        print("  无数据")
        return

    # --- 1. Overall drift consensus ---
    labels = ["主胜", "平局", "客胜"]
    avg_drift = [0, 0, 0]
    for d in all_drifts:
        if d["cid"] == "24":
            continue  # skip average
        for i in range(3):
            avg_drift[i] += d["drift"][i]
    n = len([d for d in all_drifts if d["cid"] != "24"])
    avg_drift = [x/n for x in avg_drift]

    print(f"\n  【25家公司平均概率漂移】(初→终)")
    for i, lb in enumerate(labels):
        print(f"    {lb}: {avg_drift[i]:+.2f}%")
    dom_idx = max(range(3), key=lambda i: avg_drift[i])
    print(f"    → 整体漂移方向: {labels[dom_idx]} ({avg_drift[dom_idx]:+.2f}%)")

    # --- 2. Count how many companies drift each way ---
    count_up = [0, 0, 0]  # companies whose prob increased >1% for each outcome
    count_down = [0, 0, 0]
    for d in all_drifts:
        if d["cid"] == "24":
            continue
        for i in range(3):
            if d["drift"][i] > 1.0:
                count_up[i] += 1
            elif d["drift"][i] < -1.0:
                count_down[i] += 1

    print(f"\n  【概率上升>1%的公司数量】")
    for i, lb in enumerate(labels):
        print(f"    {lb}: {count_up[i]}家升 / {count_down[i]}家降")

    # --- 3. Big European vs Asian split ---
    eu_drift = [0, 0, 0]
    eu_n = 0
    asia_drift = [0, 0, 0]
    asia_n = 0
    for d in all_drifts:
        if d["cid"] in BIG_EU:
            for i in range(3):
                eu_drift[i] += d["drift"][i]
            eu_n += 1
        elif d["cid"] in BIG_ASIA:
            for i in range(3):
                asia_drift[i] += d["drift"][i]
            asia_n += 1

    if eu_n > 0:
        eu_drift = [x/eu_n for x in eu_drift]
    if asia_n > 0:
        asia_drift = [x/asia_n for x in asia_drift]

    print(f"\n  【欧洲大庄 vs 亚洲大庄】")
    for i, lb in enumerate(labels):
        print(f"    {lb}: 欧庄{eu_drift[i]:+.2f}%  亚庄{asia_drift[i]:+.2f}%")

    eu_dom = max(range(3), key=lambda i: eu_drift[i])
    asia_dom = max(range(3), key=lambda i: asia_drift[i])
    split = "分歧" if eu_dom != asia_dom else "一致"
    print(f"    欧庄→{labels[eu_dom]}  亚庄→{labels[asia_dom]}  ({split})")

    # --- 4. Betfair (exchange = real money flow) ---
    bf = next((d for d in all_drifts if d["cid"] == "19"), None)
    if bf:
        print(f"\n  【必发Betfair交易所】(真实资金流向)")
        for i, lb in enumerate(labels):
            print(f"    {lb}: {bf['drift'][i]:+.2f}%  (赔率 {bf['init_odds'][i]:.2f}→{bf['final_odds'][i]:.2f})")
        bf_dom = max(range(3), key=lambda i: bf["drift"][i])
        print(f"    → 资金流向: {labels[bf_dom]}")

    # --- 5. Kelly anomaly (from okooo data) ---
    kelly_drop_w, kelly_drop_d, kelly_drop_l = 0, 0, 0
    for d in all_drifts:
        if d["cid"] == "24" or not d.get("kelly_drift"):
            continue
        kd = d["kelly_drift"]
        if kd[0] < -0.05:
            kelly_drop_w += 1
        if kd[1] < -0.05:
            kelly_drop_d += 1
        if kd[2] < -0.05:
            kelly_drop_l += 1

    print(f"\n  【凯利指数下降>0.05的公司数】")
    print(f"    主胜: {kelly_drop_w}家  平局: {kelly_drop_d}家  客胜: {kelly_drop_l}家")
    kmax = max(kelly_drop_w, kelly_drop_d, kelly_drop_l)
    if kmax >= 5:
        klabel = "主胜" if kelly_drop_w == kmax else ("平局" if kelly_drop_d == kmax else "客胜")
        print(f"    → 凯利信号: 庄家集体压低{klabel}凯利 (利润空间在{klabel})")

    # --- 6. Payout rate change ---
    pay_changes = []
    for d in all_drifts:
        if d["cid"] == "24":
            continue
        try:
            ip = float(d["init_pay"].rstrip("%"))
            fp = float(d["final_pay"].rstrip("%"))
            pay_changes.append(fp - ip)
        except:
            pass
    if pay_changes:
        avg_pay = sum(pay_changes) / len(pay_changes)
        print(f"\n  【返还率变化】平均 {avg_pay:+.2f}%")
        if avg_pay < -0.5:
            print(f"    → 庄家终盘收紧返还率，增加抽水 → 该场有风险")

    # --- 7. Late movers (companies with many changes = nervous) ---
    nervous = sorted([d for d in all_drifts if d["cid"] != "24"], key=lambda x: -x["n_changes"])[:5]
    print(f"\n  【变盘次数最多的公司】(频繁调整=庄家紧张)")
    for d in nervous:
        dom = max(range(3), key=lambda i: d["drift"][i])
        print(f"    {d['name']:12} {d['n_changes']}次变盘  漂移→{labels[dom]} ({d['drift'][dom]:+.1f}%)")

    # --- 8. Key company detail ---
    key_cids = ["14", "27", "82", "19", "250", "65", "35"]  # WH, B365, Lad, BF, Crown, Victor, Easy
    print(f"\n  【关键公司终盘赔率】")
    print(f"    {'公司':12} {'初主':>6} {'初平':>6} {'初客':>6}  →  {'终主':>6} {'终平':>6} {'终客':>6}  {'变盘':>4}")
    for d in all_drifts:
        if d["cid"] in key_cids:
            io = d["init_odds"]
            fo = d["final_odds"]
            print(f"    {d['name']:12} {io[0]:6.2f} {io[1]:6.2f} {io[2]:6.2f}  →  {fo[0]:6.2f} {fo[1]:6.2f} {fo[2]:6.2f}  {d['n_changes']:>4}")

    # --- Summary ---
    print(f"\n  {'─'*60}")
    print(f"  ★ 澳客补充诊断:")

    # Determine if okooo signals would have helped
    actual_map = {"主胜": 0, "平局": 1, "客胜": 2}
    actual_idx = actual_map[m["actual"]]

    signals = []
    if avg_drift[actual_idx] > 1.0:
        signals.append(f"25家平均漂移→{m['actual']} ({avg_drift[actual_idx]:+.1f}%)")
    if bf and bf["drift"][actual_idx] == max(bf["drift"]):
        signals.append(f"必发资金流→{m['actual']}")
    if eu_dom == actual_idx:
        signals.append(f"欧洲大庄→{m['actual']}")
    if asia_dom == actual_idx:
        signals.append(f"亚洲大庄→{m['actual']}")
    if eu_dom != asia_dom:
        signals.append("欧亚庄分歧")

    if signals:
        print(f"    能补救: {'; '.join(signals)}")
    else:
        print(f"    不能补救: 澳客数据也没有指向{m['actual']}")


for m in PROBLEM_MATCHES:
    analyze_match(m)

print(f"\n\n{'='*90}")
print("  总结: 澳客数据对4场失败case的补救能力")
print(f"{'='*90}")
