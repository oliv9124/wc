"""Quick backtest: compare okooo vs qiu drift signals on finished matches."""
import json, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATA = Path(__file__).parent / "data"

config = json.load(open(Path(__file__).parent / "worldcup_fids.json", "r", encoding="utf-8"))
finished = [m for m in config["matches"] if m.get("status") == "finished"]

OKOOO_CIDS = {
    24: "99家平均", 2: "竞彩官方", 14: "威廉希尔", 82: "立博", 27: "Bet365",
    43: "Interwetten", 25: "SNAI", 94: "bwin", 131: "香港马会", 65: "伟德国际",
    35: "易胜博", 180: "Unibet", 19: "必发", 84: "澳门彩票", 116: "Coral",
    49: "Paddy Power", 307: "Mansion88", 250: "皇冠", 220: "沙巴", 280: "利记",
    322: "金宝博", 202: "10Bet", 406: "12bet", 744: "1xbet", 157: "Skybet",
}

CN = {"win": "主胜", "draw": "平局", "lost": "客胜"}


def load_j(p):
    if not p.exists():
        return None
    return json.load(open(p, "r", encoding="utf-8"))


EXCHANGE_CIDS = {19}


def get_ok_drift(mid):
    dw, dd, dl, n = 0, 0, 0, 0
    for cid in OKOOO_CIDS:
        if cid == 24 or cid in EXCHANGE_CIDS:
            continue
        d = load_j(DATA / "okooo" / "changes" / f"{mid}_{cid}_odds.json")
        if not d or not d.get("records") or len(d["records"]) < 2:
            continue
        r = d["records"]
        try:
            pw_f = float(r[0]["prob_w"])
            pd_f = float(r[0]["prob_d"])
            pl_f = float(r[0]["prob_l"])
            pw_i = float(r[-1]["prob_w"])
            pd_i = float(r[-1]["prob_d"])
            pl_i = float(r[-1]["prob_l"])
        except (ValueError, KeyError):
            continue
        dw += pw_f - pw_i
        dd += pd_f - pd_i
        dl += pl_f - pl_i
        n += 1
    if n == 0:
        return None
    return {"win": dw / n, "draw": dd / n, "lost": dl / n, "count": n}


def implied(o):
    try:
        return 100 / float(o)
    except (ValueError, ZeroDivisionError):
        return 0


def get_qiu_drift(fid, cids):
    dw, dd, dl, n = 0, 0, 0, 0
    for cid in cids:
        ts = load_j(DATA / "qiu" / "timeseries" / f"{fid}_{cid}_ouzhi.json")
        if not ts or not ts.get("records") or len(ts["records"]) < 2:
            continue
        recs = ts["records"]
        try:
            t0 = datetime.strptime(recs[0]["time"], "%Y-%m-%d %H:%M:%S")
            t1 = datetime.strptime(recs[-1]["time"], "%Y-%m-%d %H:%M:%S")
            if t0 > t1:
                recs = list(reversed(recs))
        except ValueError:
            pass
        f, l = recs[0], recs[-1]
        dw += implied(l["win"]) - implied(f["win"])
        dd += implied(l["draw"]) - implied(f["draw"])
        dl += implied(l["lost"]) - implied(f["lost"])
        n += 1
    if n == 0:
        return None
    return {"win": dw / n, "draw": dd / n, "lost": dl / n, "count": n}


ALL_CIDS = [3, 1055, 280, 6, 9]


def actual_result(score):
    h, a = score.split(":")
    h, a = int(h), int(a)
    if h > a:
        return "win"
    elif h == a:
        return "draw"
    else:
        return "lost"


def dominant(drift):
    d = {"win": drift["win"], "draw": drift["draw"], "lost": drift["lost"]}
    dom = max(d, key=d.get)
    return dom, d[dom]


print("=" * 100)
print("  回测: 澳客变赔 vs 球球时序 — 12场已完赛比赛")
print("=" * 100)

header = "{:<18} {:<5} {:>6} {:>8} {:>6} {:>8} {:>8} {:>6}".format(
    "比赛", "结果", "澳客向", "澳客幅度", "球球向", "球球幅度", "推荐", "正确"
)
print(header)
print("-" * 100)

ok_signal_correct = 0
ok_signal_total = 0
qiu_signal_correct = 0
qiu_signal_total = 0
combined_correct = 0
combined_total = 0

for m in finished:
    fid = m["qiu_fid"]
    mid = m.get("ok_mid", "")
    score = m.get("score", "")
    label = "{}vs{}".format(m["home"], m["away"])
    actual = actual_result(score) if score else "?"

    ok = get_ok_drift(mid)
    qiu = get_qiu_drift(fid, ALL_CIDS)

    ok_dir_s = ok_mag_s = qiu_dir_s = qiu_mag_s = ""
    rec_str = ""
    correct = ""

    if ok:
        ok_dom, ok_val = dominant(ok)
        ok_dir_s = CN[ok_dom]
        ok_mag_s = "{:+.1f}%".format(ok_val)

        ok_mag_abs = abs(ok_val)
        if ok_mag_abs > 3:
            ok_signal_total += 1
            if actual != ok_dom:
                ok_signal_correct += 1
        elif ok_mag_abs > 2:
            ok_signal_total += 1
            if actual == ok_dom:
                ok_signal_correct += 1

    if qiu:
        qiu_dom, qiu_val = dominant(qiu)
        qiu_dir_s = CN[qiu_dom]
        qiu_mag_s = "{:+.1f}%".format(qiu_val)

        qiu_mag_abs = abs(qiu_val)
        if qiu_mag_abs > 3:
            qiu_signal_total += 1
            if actual != qiu_dom:
                qiu_signal_correct += 1
        elif qiu_mag_abs > 2:
            qiu_signal_total += 1
            if actual == qiu_dom:
                qiu_signal_correct += 1

    # Combined: qiu primary, okooo cross-validation; disagree → downgrade
    sources_disagree = False
    if ok and qiu:
        ok_d, _ = dominant(ok)
        qiu_d, _ = dominant(qiu)
        sources_disagree = ok_d != qiu_d

    drift = qiu or ok
    if drift:
        dom, val = dominant(drift)
        mag = abs(val)
        effective_mag = mag * 0.5 if sources_disagree else mag
        if effective_mag > 3:
            rec_str = "反向"
            is_correct = actual != dom
            correct = "V" if is_correct else "X"
            combined_total += 1
            if is_correct:
                combined_correct += 1
        elif effective_mag > 2:
            rec_str = "跟" + CN[dom]
            is_correct = actual == dom
            correct = "V" if is_correct else "X"
            combined_total += 1
            if is_correct:
                combined_correct += 1
        else:
            rec_str = "弱/无"
            correct = "-"
            if sources_disagree:
                rec_str = "分歧"

    row = "{:<18} {:<5} {:>6} {:>8} {:>6} {:>8} {:>8} {:>6}".format(
        label[:18], CN.get(actual, "?"), ok_dir_s, ok_mag_s, qiu_dir_s, qiu_mag_s, rec_str, correct
    )
    print(row)

print("-" * 100)
print("\n  信号命中率:")
if ok_signal_total > 0:
    print("    澳客(有信号场次): {}/{} = {:.0f}%".format(ok_signal_correct, ok_signal_total, 100 * ok_signal_correct / ok_signal_total))
else:
    print("    澳客: 暂无足够数据")
if qiu_signal_total > 0:
    print("    球球(有信号场次): {}/{} = {:.0f}%".format(qiu_signal_correct, qiu_signal_total, 100 * qiu_signal_correct / qiu_signal_total))
if combined_total > 0:
    print("    综合(澳客优先):  {}/{} = {:.0f}%".format(combined_correct, combined_total, 100 * combined_correct / combined_total))
