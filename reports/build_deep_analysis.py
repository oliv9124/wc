"""
Deep analysis: examine every odds change from bookmaker profit perspective.
For each finished match, for each company's time series:
  - Track payout rate trajectory (bookmaker margin changes)
  - Classify each move: balancing vs conviction vs sharp
  - Track implied probability drift direction
  - Identify "profit protection" moves (payout drops)
  - Correlate with actual result
"""
import json, sys
from pathlib import Path
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

with open(ROOT / "worldcup_fids.json", "r", encoding="utf-8") as f:
    config = json.load(f)
with open(ROOT / "cid_mapping_final.json", "r", encoding="utf-8") as f:
    cid_map = json.load(f)

cid_names = cid_map["qiuqiushidao"]["companies"]
finished = [m for m in config["matches"] if m.get("status") == "finished" and m.get("score")]

KEY_CIDS = [3, 1055, 280, 6, 9, 2, 293, 348, 651]

def result_of(score):
    h, a = map(int, score.split(":"))
    if h > a: return "win"
    if h == a: return "draw"
    return "lost"

def load_json(path):
    if not path.exists(): return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def implied_prob(odds_str):
    try:
        v = float(odds_str)
        return round(100 / v, 2) if v > 0 else 0
    except: return 0

# ── Analyze each match deeply ──
all_matches = []

for m in finished:
    fid = m["qiu_fid"]
    result = result_of(m["score"])
    h_goals, a_goals = map(int, m["score"].split(":"))
    match_time = datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M")

    # Determine favorite from overview
    eu_ov = load_json(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    favorite = "home"
    is_upset = False
    if eu_ov:
        avg = next((r for r in eu_ov["rows"] if r["id"] == "0"), None)
        if avg:
            ed = avg.get("end") or avg["first"]
            if float(ed["win"]) < float(ed["lost"]):
                favorite = "home"
                is_upset = result != "win"
            else:
                favorite = "away"
                is_upset = result != "lost"

    match_data = {
        "home": m["home"], "away": m["away"], "score": m["score"],
        "date": m["date"], "time": m["time"],
        "result": result,
        "result_cn": {"win": "主胜", "draw": "平局", "lost": "客胜"}[result],
        "favorite": favorite, "is_upset": is_upset,
        "total_goals": h_goals + a_goals,
        "companies": []
    }

    for cid in KEY_CIDS:
        ts = load_json(DATA / "qiu" / "timeseries" / f"{fid}_{cid}_ouzhi.json")
        if not ts or not ts.get("records") or len(ts["records"]) < 2:
            continue

        name = cid_names.get(str(cid), f"CID{cid}")
        records = ts["records"]
        # records are newest-first in some files, ensure chronological
        try:
            t0 = datetime.strptime(records[0]["time"], "%Y-%m-%d %H:%M:%S")
            t1 = datetime.strptime(records[-1]["time"], "%Y-%m-%d %H:%M:%S")
            if t0 > t1:
                records = list(reversed(records))
        except: pass

        changes = []
        prev = None
        for rec in records:
            w = float(rec["win"])
            d = float(rec["draw"])
            l = float(rec["lost"])
            pay = float(rec.get("pay", 0))
            kw = float(rec.get("kwin", 0))
            kd = float(rec.get("kdraw", 0))
            kl = float(rec.get("klost", 0))
            try:
                t = datetime.strptime(rec["time"], "%Y-%m-%d %H:%M:%S")
            except:
                continue

            hours_before = (match_time - t).total_seconds() / 3600

            ip_w = implied_prob(rec["win"])
            ip_d = implied_prob(rec["draw"])
            ip_l = implied_prob(rec["lost"])

            change = {
                "time": rec["time"],
                "hours_before": round(hours_before, 1),
                "win": w, "draw": d, "lost": l,
                "pay": pay,
                "ip_win": ip_w, "ip_draw": ip_d, "ip_lost": ip_l,
                "kelly": [kw, kd, kl],
                "dir_w": int(rec.get("w", 0)),
                "dir_d": int(rec.get("d", 0)),
                "dir_l": int(rec.get("l", 0)),
            }

            if prev:
                change["delta_w"] = round(w - prev["win"], 3)
                change["delta_d"] = round(d - prev["draw"], 3)
                change["delta_l"] = round(l - prev["lost"], 3)
                change["delta_pay"] = round(pay - prev["pay"], 2)
                change["delta_ip_w"] = round(ip_w - prev["ip_win"], 2)
                change["delta_ip_d"] = round(ip_d - prev["ip_draw"], 2)
                change["delta_ip_l"] = round(ip_l - prev["ip_lost"], 2)

                # Classify the move
                dp = change["delta_pay"]
                abs_shifts = abs(change["delta_ip_w"]) + abs(change["delta_ip_d"]) + abs(change["delta_ip_l"])

                if dp < -0.3 and abs_shifts < 1.0:
                    change["move_type"] = "margin_up"  # payout drop, small rebalance → taking profit
                elif dp < -0.3:
                    change["move_type"] = "protect"    # payout drop + shift → protecting against one outcome
                elif abs_shifts > 2.0:
                    change["move_type"] = "conviction"  # large probability shift → new information
                elif abs_shifts > 0.5:
                    change["move_type"] = "adjust"      # moderate shift → balancing the book
                else:
                    change["move_type"] = "micro"       # tiny adjustment

                # Which outcome is the bookmaker pushing money away from?
                max_ip_delta = max(change["delta_ip_w"], change["delta_ip_d"], change["delta_ip_l"])
                if change["delta_ip_w"] == max_ip_delta:
                    change["push_toward"] = "win"
                elif change["delta_ip_d"] == max_ip_delta:
                    change["push_toward"] = "draw"
                else:
                    change["push_toward"] = "lost"
            else:
                change["move_type"] = "open"
                change["push_toward"] = ""

            changes.append(change)
            prev = change

        if not changes: continue

        # Aggregate stats for this company
        first = changes[0]
        last = changes[-1]
        total_pay_drift = round(last["pay"] - first["pay"], 2)
        total_ip_w_drift = round(last["ip_win"] - first["ip_win"], 2)
        total_ip_d_drift = round(last["ip_draw"] - first["ip_draw"], 2)
        total_ip_l_drift = round(last["ip_lost"] - first["ip_lost"], 2)

        # Count move types
        move_counts = {}
        for c in changes:
            mt = c["move_type"]
            move_counts[mt] = move_counts.get(mt, 0) + 1

        # Count how many times bookmaker pushed toward the actual result
        push_toward_result = sum(1 for c in changes if c.get("push_toward") == result)
        push_away_result = sum(1 for c in changes if c.get("push_toward") and c["push_toward"] != result)

        # Late moves (last 6h)
        late = [c for c in changes if c["hours_before"] <= 6]
        late_pay_drift = round(late[-1]["pay"] - late[0]["pay"], 2) if len(late) >= 2 else 0

        # Kelly analysis
        final_kelly = last["kelly"]
        result_kelly = final_kelly[0] if result == "win" else (final_kelly[1] if result == "draw" else final_kelly[2])

        company_data = {
            "name": name, "cid": cid,
            "total_changes": len(changes),
            "changes": changes,
            "pay_drift": total_pay_drift,
            "ip_drift": {"win": total_ip_w_drift, "draw": total_ip_d_drift, "lost": total_ip_l_drift},
            "move_counts": move_counts,
            "push_toward_result": push_toward_result,
            "push_away_result": push_away_result,
            "late_count": len(late),
            "late_pay_drift": late_pay_drift,
            "final_kelly": final_kelly,
            "result_kelly": round(result_kelly, 3),
            "first_pay": first["pay"],
            "last_pay": last["pay"],
        }
        match_data["companies"].append(company_data)

    all_matches.append(match_data)

# ── Generate HTML ──
data_json = json.dumps(all_matches, ensure_ascii=False)

html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Deep Analysis — 庄家视角</title>
<style>
:root { --bg: #0f1117; --card: #1a1d27; --border: #2a2d3a; --text: #e4e4e7; --dim: #888; --accent: #3b82f6; --green: #22c55e; --red: #ef4444; --yellow: #eab308; --orange: #f97316; --purple: #a855f7; --cyan: #06b6d4; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
.header { background: linear-gradient(135deg, #1e293b, #0f172a); padding: 24px 32px; border-bottom: 1px solid var(--border); }
.header h1 { font-size: 22px; margin-bottom: 4px; }
.header p { color: var(--dim); font-size: 13px; }
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }

.legend { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; padding: 12px 16px; background: var(--card); border-radius: 8px; border: 1px solid var(--border); font-size: 12px; }
.legend-item { display: flex; align-items: center; gap: 6px; }
.legend-dot { width: 10px; height: 10px; border-radius: 2px; }

/* match section */
.match-section { background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 28px; overflow: hidden; }
.match-section.upset { border-left: 4px solid var(--red); }
.match-header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
.match-header:hover { background: rgba(59,130,246,0.04); }
.match-header h2 { font-size: 17px; }
.match-body { padding: 0; display: none; }
.match-body.open { display: block; }

.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.tag-win { background: rgba(34,197,94,0.15); color: var(--green); }
.tag-draw { background: rgba(234,179,8,0.15); color: var(--yellow); }
.tag-lost { background: rgba(239,68,68,0.15); color: var(--red); }
.tag-upset { background: rgba(239,68,68,0.2); color: var(--red); }

/* company tabs */
.company-tabs { display: flex; border-bottom: 1px solid var(--border); padding: 0 24px; overflow-x: auto; }
.company-tab { padding: 10px 16px; font-size: 13px; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; color: var(--dim); transition: all 0.15s; }
.company-tab:hover { color: var(--text); }
.company-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.company-tab .badge { font-size: 10px; padding: 1px 5px; border-radius: 3px; margin-left: 4px; }

/* company detail panel */
.company-panel { display: none; padding: 20px 24px; }
.company-panel.active { display: block; }

.stats-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-card { background: var(--bg); border-radius: 8px; padding: 10px 16px; min-width: 120px; }
.stat-card .label { font-size: 11px; color: var(--dim); }
.stat-card .value { font-size: 18px; font-weight: 700; }

/* chart area */
.chart-container { background: var(--bg); border-radius: 8px; padding: 16px; margin-bottom: 16px; position: relative; }
.chart-container canvas { width: 100% !important; }

/* changes timeline */
.timeline { max-height: 400px; overflow-y: auto; }
.timeline-row { display: grid; grid-template-columns: 100px 60px 90px 90px 90px 70px 100px 90px auto; gap: 4px; padding: 5px 8px; font-size: 11px; border-bottom: 1px solid var(--border); align-items: center; }
.timeline-row.header { position: sticky; top: 0; background: var(--card); color: var(--dim); font-weight: 600; z-index: 1; }
.timeline-row.margin-up { background: rgba(239,68,68,0.04); }
.timeline-row.protect { background: rgba(249,115,22,0.04); }
.timeline-row.conviction { background: rgba(168,85,247,0.06); }
.timeline-row.late { border-left: 2px solid var(--orange); }

.move-tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; }
.move-margin_up { background: rgba(239,68,68,0.15); color: var(--red); }
.move-protect { background: rgba(249,115,22,0.15); color: var(--orange); }
.move-conviction { background: rgba(168,85,247,0.15); color: var(--purple); }
.move-adjust { background: rgba(59,130,246,0.12); color: var(--accent); }
.move-micro { background: rgba(136,136,136,0.1); color: var(--dim); }

.push-tag { font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 3px; }
.push-correct { background: rgba(34,197,94,0.15); color: var(--green); }
.push-wrong { background: rgba(239,68,68,0.1); color: var(--dim); }

.up { color: var(--red); }
.down { color: var(--green); }
.flat { color: var(--dim); }

/* summary section */
.match-summary { padding: 16px 24px; border-top: 1px solid var(--border); background: rgba(59,130,246,0.02); }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.summary-item { background: var(--bg); border-radius: 8px; padding: 10px 14px; }
.summary-item h4 { font-size: 11px; color: var(--accent); text-transform: uppercase; margin-bottom: 6px; }
.summary-item p { font-size: 13px; }

.insight { margin-top: 12px; padding: 12px 16px; border-radius: 8px; font-size: 13px; line-height: 1.6; }
.insight-green { background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.2); }
.insight-red { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); }
.insight-yellow { background: rgba(234,179,8,0.08); border: 1px solid rgba(234,179,8,0.2); }

.global-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }
.gs-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; }
.gs-card h3 { font-size: 13px; color: var(--accent); margin-bottom: 10px; }
.gs-card .big { font-size: 28px; font-weight: 700; }
.gs-card p { font-size: 12px; color: var(--dim); margin-top: 4px; }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
<div class="header">
  <h1>Deep Analysis — 庄家盈利视角拆解</h1>
  <p>逐条变赔分析 · 返还率轨迹 · 隐含概率漂移 · 变赔动机分类</p>
</div>
<div class="container">
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div> margin_up 提高利润(返还率↓)</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--orange)"></div> protect 利润保护+概率调整</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--purple)"></div> conviction 信息驱动(大幅调赔)</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--accent)"></div> adjust 平衡收注</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--dim)"></div> micro 微调</div>
  </div>

  <div class="global-stats" id="globalStats"></div>
  <div id="matchSections"></div>
</div>

<script>
const M = """ + data_json + r""";
const MOVE_LABELS = {margin_up:'提利润', protect:'利润保护', conviction:'信息驱动', adjust:'平衡', micro:'微调', open:'开盘'};
const RESULT_CN = {win:'主胜', draw:'平局', lost:'客胜'};

function fmt(v, prefix) {
  if (v === undefined || v === null) return '';
  const s = typeof v === 'number' ? v.toFixed(2) : v;
  const n = parseFloat(s);
  if (n > 0) return `<span class="up">${prefix||''}+${s}</span>`;
  if (n < 0) return `<span class="down">${prefix||''}${s}</span>`;
  return `<span class="flat">0</span>`;
}

// ── Global statistics ──
let totalConviction = 0, convictionCorrect = 0;
let totalProtect = 0, protectUpset = 0;
let payDropMatches = 0, payDropUpsets = 0;
let kellyLowCorrect = 0, kellyLowTotal = 0;

M.forEach(m => {
  let matchPayDrop = false;
  m.companies.forEach(co => {
    // conviction moves: did they push toward the actual result?
    co.changes.forEach(c => {
      if (c.move_type === 'conviction') {
        totalConviction++;
        if (c.push_toward === m.result) convictionCorrect++;
      }
      if (c.move_type === 'protect') {
        totalProtect++;
      }
    });
    if (co.pay_drift < -0.5) matchPayDrop = true;
    // Kelly < 0.90 for result outcome = bookmaker saw it coming?
    const rk = co.result_kelly;
    if (rk > 0 && rk < 0.90) { kellyLowTotal++; }
    if (rk > 0 && rk >= 0.95) { kellyLowCorrect++; } // kelly normal/high = bookmaker thought this outcome more likely
  });
  if (matchPayDrop) {
    payDropMatches++;
    if (m.is_upset) payDropUpsets++;
  }
});

document.getElementById('globalStats').innerHTML = `
  <div class="gs-card">
    <h3>信息驱动变赔 vs 赛果</h3>
    <div class="big">${totalConviction > 0 ? Math.round(convictionCorrect/totalConviction*100) : 0}%</div>
    <p>${convictionCorrect}/${totalConviction} 次信息驱动变赔推向了正确结果方向</p>
  </div>
  <div class="gs-card">
    <h3>返还率下降 vs 冷门</h3>
    <div class="big">${payDropMatches > 0 ? Math.round(payDropUpsets/payDropMatches*100) : 0}%</div>
    <p>${payDropUpsets}/${payDropMatches} 场返还率明显下降的比赛出了冷门</p>
  </div>
  <div class="gs-card">
    <h3>变赔动机分布</h3>
    <div class="big" style="font-size:16px">
      <span style="color:var(--purple)">信息${totalConviction}</span> ·
      <span style="color:var(--orange)">保护${totalProtect}</span>
    </div>
    <p>在所有 ${M.reduce((s,m)=>s+m.companies.reduce((s2,c)=>s2+c.total_changes,0),0)} 次变赔中</p>
  </div>
`;

// ── Match sections ──
let html = '';
const chartIds = [];

M.forEach((m, mi) => {
  const rTag = `<span class="tag tag-${m.result}">${m.result_cn}</span>`;
  const uTag = m.is_upset ? ' <span class="tag tag-upset">爆冷</span>' : '';

  html += `<div class="match-section ${m.is_upset ? 'upset' : ''}">`;
  html += `<div class="match-header" onclick="toggleMatch(${mi})">
    <h2>${m.date} ${m.time} — ${m.home} <b>${m.score}</b> ${m.away} ${rTag}${uTag}</h2>
    <span style="color:var(--dim)">${m.companies.length}家公司 · ${m.companies.reduce((s,c)=>s+c.total_changes,0)}次变赔</span>
  </div>`;

  html += `<div class="match-body" id="mbody_${mi}">`;

  // Company tabs
  html += `<div class="company-tabs" id="tabs_${mi}">`;
  m.companies.forEach((co, ci) => {
    const badge_cls = co.pay_drift < -0.5 ? 'style="background:rgba(239,68,68,0.15);color:var(--red)"' :
                      co.pay_drift > 0.3 ? 'style="background:rgba(34,197,94,0.15);color:var(--green)"' : '';
    const badge = co.pay_drift !== 0 ? `<span class="badge" ${badge_cls}>${co.pay_drift > 0 ? '+' : ''}${co.pay_drift.toFixed(1)}%</span>` : '';
    html += `<div class="company-tab ${ci===0?'active':''}" onclick="switchTab(${mi},${ci})">${co.name}${badge}</div>`;
  });
  html += '</div>';

  // Company panels
  m.companies.forEach((co, ci) => {
    html += `<div class="company-panel ${ci===0?'active':''}" id="panel_${mi}_${ci}">`;

    // Stats row
    const pushRate = co.total_changes > 1 ? Math.round(co.push_toward_result / (co.total_changes - 1) * 100) : 0;
    html += `<div class="stats-row">
      <div class="stat-card"><div class="label">总变赔</div><div class="value">${co.total_changes}次</div></div>
      <div class="stat-card"><div class="label">返还率漂移</div><div class="value" style="color:${co.pay_drift<-0.3?'var(--red)':co.pay_drift>0.3?'var(--green)':'var(--text)'}">${co.pay_drift>0?'+':''}${co.pay_drift.toFixed(2)}%</div></div>
      <div class="stat-card"><div class="label">推向赛果占比</div><div class="value" style="color:${pushRate>60?'var(--green)':pushRate<40?'var(--red)':'var(--text)'}">${pushRate}%</div></div>
      <div class="stat-card"><div class="label">赛果凯利</div><div class="value" style="color:${co.result_kelly<0.9?'var(--red)':co.result_kelly>1.05?'var(--green)':'var(--text)'}">${co.result_kelly.toFixed(3)}</div></div>
      <div class="stat-card"><div class="label">赛前6h</div><div class="value">${co.late_count}次 ${co.late_pay_drift!==0?'(返还'+fmt(co.late_pay_drift)+')':''}</div></div>
    </div>`;

    // Chart
    const chartId = `chart_${mi}_${ci}`;
    chartIds.push({id: chartId, co: co, result: m.result, mi: mi, ci: ci});
    html += `<div class="chart-container"><canvas id="${chartId}" height="200"></canvas></div>`;

    // Timeline table
    html += `<div class="timeline">
      <div class="timeline-row header">
        <div>时间</div><div>赛前h</div>
        <div>胜赔</div><div>平赔</div><div>负赔</div>
        <div>返还率</div><div>动机</div><div>推向</div><div>概率变化</div>
      </div>`;

    co.changes.forEach(c => {
      const isLate = c.hours_before <= 6;
      const rowCls = [c.move_type, isLate ? 'late' : ''].filter(Boolean).join(' ');
      const moveTag = c.move_type !== 'open' ? `<span class="move-tag move-${c.move_type}">${MOVE_LABELS[c.move_type]||c.move_type}</span>` : '<span class="flat">开盘</span>';
      const pushTag = c.push_toward ? `<span class="push-tag ${c.push_toward===m.result?'push-correct':'push-wrong'}">${RESULT_CN[c.push_toward]||c.push_toward}${c.push_toward===m.result?' ✓':''}</span>` : '';

      const dpay = c.delta_pay !== undefined ? fmt(c.delta_pay) : '';
      const dipw = c.delta_ip_w !== undefined ? `胜${fmt(c.delta_ip_w)}` : '';
      const dipd = c.delta_ip_d !== undefined ? ` 平${fmt(c.delta_ip_d)}` : '';
      const dipl = c.delta_ip_l !== undefined ? ` 负${fmt(c.delta_ip_l)}` : '';

      html += `<div class="timeline-row ${rowCls}">
        <div>${c.time.slice(5,16)}</div>
        <div>${c.hours_before}h</div>
        <div>${c.win.toFixed(2)}</div>
        <div>${c.draw.toFixed(2)}</div>
        <div>${c.lost.toFixed(2)}</div>
        <div>${c.pay.toFixed(2)}% ${dpay}</div>
        <div>${moveTag}</div>
        <div>${pushTag}</div>
        <div style="font-size:10px">${dipw}${dipd}${dipl}</div>
      </div>`;
    });

    html += '</div>'; // timeline
    html += '</div>'; // company-panel
  });

  // Match summary
  html += '<div class="match-summary"><div class="summary-grid">';

  // Aggregate insights
  const coWithPayDrop = m.companies.filter(c => c.pay_drift < -0.3);
  const coWithPayUp = m.companies.filter(c => c.pay_drift > 0.3);
  const avgPushRate = m.companies.length > 0 ? Math.round(m.companies.reduce((s,c) => s + c.push_toward_result / Math.max(c.total_changes-1, 1), 0) / m.companies.length * 100) : 0;
  const convictions = m.companies.reduce((s,c) => s + (c.move_counts.conviction || 0), 0);
  const protects = m.companies.reduce((s,c) => s + (c.move_counts.protect || 0), 0);
  const avgResultKelly = m.companies.length > 0 ? (m.companies.reduce((s,c) => s + c.result_kelly, 0) / m.companies.length).toFixed(3) : '?';

  html += `<div class="summary-item"><h4>返还率趋势</h4><p>${coWithPayDrop.length}家下降 / ${coWithPayUp.length}家上升</p></div>`;
  html += `<div class="summary-item"><h4>变赔推向赛果</h4><p>平均 ${avgPushRate}%</p></div>`;
  html += `<div class="summary-item"><h4>信息驱动 / 保护</h4><p>${convictions} / ${protects} 次</p></div>`;
  html += `<div class="summary-item"><h4>赛果凯利均值</h4><p>${avgResultKelly}</p></div>`;

  html += '</div>'; // summary-grid

  // Insight
  let insightCls, insightText;
  if (avgPushRate > 55 && !m.is_upset) {
    insightCls = 'insight-green';
    insightText = `庄家多数变赔方向与赛果一致 (${avgPushRate}%)。变赔逻辑可读性强 — 跟随庄家方向即可。`;
  } else if (avgPushRate > 55 && m.is_upset) {
    insightCls = 'insight-yellow';
    insightText = `虽然爆冷，但庄家变赔中 ${avgPushRate}% 推向了正确方向。说明庄家预见到了冷门可能，只是初始赔率设定偏差。`;
  } else if (avgPushRate <= 55 && m.is_upset) {
    insightCls = 'insight-red';
    insightText = `爆冷且庄家变赔方向未能指向赛果 (${avgPushRate}%)。这是真正的「意外」— 庄家也被打了个措手不及。`;
  } else {
    insightCls = 'insight-yellow';
    insightText = `变赔方向与赛果吻合度一般 (${avgPushRate}%)。庄家在这场比赛中态度模糊，信号可读性低。`;
  }
  if (coWithPayDrop.length >= 3) {
    insightText += ` 另外注意：${coWithPayDrop.length}家公司返还率下降，说明庄家整体在加大利润保护。`;
  }

  html += `<div class="insight ${insightCls}">${insightText}</div>`;
  html += '</div>'; // match-summary
  html += '</div>'; // match-body
  html += '</div>'; // match-section
});

document.getElementById('matchSections').innerHTML = html;

// ── Draw charts ──
function drawChart(info) {
  const el = document.getElementById(info.id);
  if (!el) return;
  const co = info.co;

  const labels = co.changes.map(c => c.time.slice(5, 16));
  const payData = co.changes.map(c => c.pay);
  const ipW = co.changes.map(c => c.ip_win);
  const ipD = co.changes.map(c => c.ip_draw);
  const ipL = co.changes.map(c => c.ip_lost);
  const kW = co.changes.map(c => c.kelly[0]);
  const kD = co.changes.map(c => c.kelly[1]);
  const kL = co.changes.map(c => c.kelly[2]);

  // Highlight actual result line
  const resultColor = info.result === 'win' ? '#22c55e' : info.result === 'draw' ? '#eab308' : '#ef4444';

  new Chart(el, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        { label: '返还率%', data: payData, borderColor: '#fff', borderWidth: 2, pointRadius: 0, yAxisID: 'y1', tension: 0.2 },
        { label: '隐含概率-胜', data: ipW, borderColor: info.result==='win'?'#22c55e':'rgba(34,197,94,0.3)', borderWidth: info.result==='win'?2.5:1, pointRadius: 0, borderDash: info.result==='win'?[]:[4,4], yAxisID: 'y' },
        { label: '隐含概率-平', data: ipD, borderColor: info.result==='draw'?'#eab308':'rgba(234,179,8,0.3)', borderWidth: info.result==='draw'?2.5:1, pointRadius: 0, borderDash: info.result==='draw'?[]:[4,4], yAxisID: 'y' },
        { label: '隐含概率-负', data: ipL, borderColor: info.result==='lost'?'#ef4444':'rgba(239,68,68,0.3)', borderWidth: info.result==='lost'?2.5:1, pointRadius: 0, borderDash: info.result==='lost'?[]:[4,4], yAxisID: 'y' },
      ]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#888', font: { size: 11 } } },
        tooltip: {
          callbacks: {
            afterBody: function(items) {
              const idx = items[0].dataIndex;
              const c = co.changes[idx];
              let lines = [`赔率: ${c.win}/${c.draw}/${c.lost}`];
              lines.push(`Kelly: ${c.kelly.map(k=>k.toFixed(3)).join('/')}`);
              if (c.move_type && c.move_type !== 'open') lines.push(`动机: ${MOVE_LABELS[c.move_type]}`);
              if (c.push_toward) lines.push(`推向: ${RESULT_CN[c.push_toward]}`);
              return lines;
            }
          }
        }
      },
      scales: {
        x: { display: true, ticks: { color: '#666', font: { size: 9 }, maxTicksLimit: 12, maxRotation: 45 }, grid: { color: 'rgba(255,255,255,0.03)' } },
        y: { position: 'left', title: { display: true, text: '隐含概率%', color: '#666' }, ticks: { color: '#666' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y1: { position: 'right', title: { display: true, text: '返还率%', color: '#666' }, ticks: { color: '#aaa' }, grid: { display: false }, min: 88, max: 100 }
      }
    }
  });
}

// Draw visible charts on toggle
const drawnCharts = new Set();
function drawChartsForMatch(mi) {
  chartIds.filter(c => c.mi === mi).forEach(info => {
    if (!drawnCharts.has(info.id)) {
      drawChart(info);
      drawnCharts.add(info.id);
    }
  });
}

function toggleMatch(mi) {
  const body = document.getElementById('mbody_' + mi);
  body.classList.toggle('open');
  if (body.classList.contains('open')) {
    setTimeout(() => drawChartsForMatch(mi), 50);
  }
}

function switchTab(mi, ci) {
  document.querySelectorAll(`#tabs_${mi} .company-tab`).forEach((t,i) => t.classList.toggle('active', i===ci));
  document.querySelectorAll(`#panel_${mi}_${ci}`).forEach(p => p.classList.remove('active'));
  // hide all panels for this match, show selected
  const panels = document.querySelectorAll(`[id^="panel_${mi}_"]`);
  panels.forEach(p => p.classList.remove('active'));
  const target = document.getElementById(`panel_${mi}_${ci}`);
  if (target) {
    target.classList.add('active');
    // draw chart if not yet drawn
    const info = chartIds.find(c => c.mi === mi && c.ci === ci);
    if (info && !drawnCharts.has(info.id)) {
      setTimeout(() => { drawChart(info); drawnCharts.add(info.id); }, 50);
    }
  }
}
</script>
</body>
</html>""";

out = ROOT / "output" / "deep_analysis.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

# Print summary
print(f"Output: {out}")
print(f"Matches: {len(all_matches)}")
total_changes = sum(sum(c["total_changes"] for c in m["companies"]) for m in all_matches)
print(f"Total changes analyzed: {total_changes}")

# Quick stats
conviction_total = 0
conviction_correct = 0
for m in all_matches:
    for co in m["companies"]:
        for c in co["changes"]:
            if c.get("move_type") == "conviction":
                conviction_total += 1
                if c.get("push_toward") == m["result"]:
                    conviction_correct += 1

print(f"\nConviction moves: {conviction_total}, correct direction: {conviction_correct} ({round(conviction_correct/max(conviction_total,1)*100)}%)")

# Pay drift vs upset
for m in all_matches:
    avg_pay_drift = sum(c["pay_drift"] for c in m["companies"]) / max(len(m["companies"]), 1)
    avg_push = sum(c["push_toward_result"] / max(c["total_changes"]-1, 1) for c in m["companies"]) / max(len(m["companies"]), 1)
    upset = "UPSET" if m["is_upset"] else "     "
    print(f"  {upset} {m['home']:6} {m['score']:5} {m['away']:8} | 返还漂移{avg_pay_drift:+.2f}% | 推向赛果{avg_push*100:.0f}%")
