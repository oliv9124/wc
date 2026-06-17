"""Build backtest HTML: every finished match analyzed across all dimensions."""
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

KEY_EU = ["0", "3", "1055", "280", "6", "9"]
KEY_TS = [3, 1055, 280, 6, 9]

def result_of(score):
    h, a = map(int, score.split(":"))
    if h > a: return "win"
    if h == a: return "draw"
    return "lost"

def parse_handi(h):
    h = str(h).strip()
    if "/" in h:
        parts = h.split("/")
        try: return sum(float(p) for p in parts) / len(parts)
        except: return None
    try: return float(h)
    except: return None

def load_json(path):
    if not path.exists(): return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Build analysis data for each match ──
analysis = []

for m in finished:
    fid = m["qiu_fid"]
    result = result_of(m["score"])
    h_goals, a_goals = map(int, m["score"].split(":"))
    total_goals = h_goals + a_goals
    goal_diff = h_goals - a_goals

    entry = {
        "match": m,
        "result": result,
        "result_cn": {"win": "主胜", "draw": "平局", "lost": "客胜"}[result],
        "total_goals": total_goals,
        "goal_diff": goal_diff,
        "dims": {}
    }

    # ── D1: European odds ──
    eu = load_json(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    if eu:
        d1 = {"companies": [], "is_upset": False, "favorite": "", "fav_odds": 0, "fav_prob": 0}
        for r in eu.get("rows", []):
            if r["id"] not in KEY_EU: continue
            fd, ed = r["first"], r.get("end") or r["first"]
            f_wr = float(fd.get("winrate") or fd.get("wgl") or 0)
            e_wr = float(ed.get("winrate") or ed.get("wgl") or 0)
            d1["companies"].append({
                "name": r["name"], "id": r["id"],
                "init": [fd["win"], fd["draw"], fd["lost"]],
                "end": [ed["win"], ed["draw"], ed["lost"]],
                "pay": ed["pay"],
                "wr_delta": round(e_wr - f_wr, 1),
            })
        avg = next((r for r in eu["rows"] if r["id"] == "0"), None)
        if avg:
            ed = avg.get("end") or avg["first"]
            w, d_o, l = float(ed["win"]), float(ed["draw"]), float(ed["lost"])
            wp = float(ed.get("winrate") or ed.get("wgl") or 0)
            dp = float(ed.get("drawrate") or ed.get("dgl") or 0)
            if w < l:
                d1["favorite"] = m["home"]
                d1["fav_odds"] = w
                d1["fav_prob"] = wp
                d1["is_upset"] = result != "win"
            else:
                d1["favorite"] = m["away"]
                d1["fav_odds"] = l
                d1["fav_prob"] = round(100 - wp - dp, 1)
                d1["is_upset"] = result != "lost"
            d1["avg_end"] = [ed["win"], ed["draw"], ed["lost"]]
            d1["big_move_count"] = sum(1 for c in d1["companies"] if abs(c["wr_delta"]) > 5)
            d1["big_move_dir"] = "up" if sum(c["wr_delta"] for c in d1["companies"]) > 0 else "down"
        entry["dims"]["eu"] = d1

    # ── D2: Asian handicap ──
    ah = load_json(DATA / "qiu" / "overview" / f"{fid}_yazhi.json")
    if ah:
        d2 = {"companies": [], "shrink_count": 0, "water_reversal": False}
        for r in ah.get("rows", []):
            fd, ed = r["first"], r.get("end") or r["first"]
            init_h = parse_handi(fd.get("handi", "0"))
            end_h = parse_handi(ed.get("handi", "0"))
            init_hw = float(fd.get("home", "0"))
            end_hw = float(ed.get("home", "0"))
            init_aw = float(fd.get("away", "0"))
            end_aw = float(ed.get("away", "0"))
            line_moved = init_h is not None and end_h is not None and abs(init_h - end_h) >= 0.2
            if line_moved: d2["shrink_count"] += 1
            water_flip = (init_hw < 0.88 and end_hw > 1.0) or (init_hw > 1.0 and end_hw < 0.88)
            if water_flip: d2["water_reversal"] = True
            d2["companies"].append({
                "name": r["name"],
                "init_h": str(fd.get("handi", "?")), "end_h": str(ed.get("handi", "?")),
                "init_hw": init_hw, "end_hw": end_hw,
                "init_aw": init_aw, "end_aw": end_aw,
                "line_moved": line_moved,
                "hw_delta": round(end_hw - init_hw, 2),
            })
        entry["dims"]["ah"] = d2

    # ── D3: Over/Under ──
    ou = load_json(DATA / "qiu" / "overview" / f"{fid}_daxiao.json")
    if ou:
        d3 = {"companies": [], "result": ""}
        for r in ou.get("rows", [])[:4]:
            fd, ed = r["first"], r.get("end") or r["first"]
            init_line = str(fd.get("handi", "?"))
            end_line = str(ed.get("handi", "?"))
            end_val = parse_handi(end_line) or 2.5
            ou_result = "OVER" if total_goals > end_val else ("PUSH" if total_goals == end_val else "UNDER")
            d3["companies"].append({
                "name": r["name"],
                "init_line": init_line, "end_line": end_line,
                "end_val": end_val,
                "big": ed.get("big", "?"), "small": ed.get("small", "?"),
                "ou_result": ou_result,
            })
        if d3["companies"]:
            d3["result"] = d3["companies"][0]["ou_result"]
            d3["end_line"] = d3["companies"][0]["end_line"]
        entry["dims"]["ou"] = d3

    # ── D4: Late movement (last 6h) ──
    match_time = datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M")
    d4 = {"companies": []}
    for cid in KEY_TS:
        ts = load_json(DATA / "qiu" / "timeseries" / f"{fid}_{cid}_ouzhi.json")
        if not ts or not ts.get("records"): continue
        records = ts["records"]
        total_changes = len(records)
        late = []
        for r in records:
            try:
                t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                if match_time - timedelta(hours=6) <= t <= match_time:
                    late.append(r)
            except: pass
        name = cid_names.get(str(cid), f"CID{cid}")
        info = {"name": name, "total_changes": total_changes, "late_count": len(late)}
        if len(late) >= 2:
            info["late_w_delta"] = round(float(late[-1]["win"]) - float(late[0]["win"]), 3)
            info["late_d_delta"] = round(float(late[-1]["draw"]) - float(late[0]["draw"]), 3)
            info["late_l_delta"] = round(float(late[-1]["lost"]) - float(late[0]["lost"]), 3)
        d4["companies"].append(info)
    entry["dims"]["ts"] = d4

    # ── D5: Company consensus ──
    d5 = {"eu_same_dir": 0, "ah_same_dir": 0}
    if "eu" in entry["dims"]:
        ups = sum(1 for c in entry["dims"]["eu"]["companies"] if c["wr_delta"] > 1)
        downs = sum(1 for c in entry["dims"]["eu"]["companies"] if c["wr_delta"] < -1)
        d5["eu_same_dir"] = max(ups, downs)
        d5["eu_dir"] = "home_up" if ups > downs else "home_down"
    if "ah" in entry["dims"]:
        d5["ah_same_dir"] = entry["dims"]["ah"]["shrink_count"]
    entry["dims"]["consensus"] = d5

    analysis.append(entry)

# ── Generate HTML ──
analysis_json = json.dumps(analysis, ensure_ascii=False)

html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Backtest — Odds vs Results</title>
<style>
:root { --bg: #0f1117; --card: #1a1d27; --border: #2a2d3a; --text: #e4e4e7; --dim: #888; --accent: #3b82f6; --green: #22c55e; --red: #ef4444; --yellow: #eab308; --orange: #f97316; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }
.header { background: linear-gradient(135deg, #1e293b, #0f172a); padding: 20px 32px; border-bottom: 1px solid var(--border); }
.header h1 { font-size: 20px; }
.header p { color: var(--dim); font-size: 13px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

/* summary table */
.summary { width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 13px; }
.summary th { background: var(--card); padding: 10px 8px; text-align: center; border: 1px solid var(--border); color: var(--dim); font-size: 11px; font-weight: 500; text-transform: uppercase; }
.summary td { padding: 8px; text-align: center; border: 1px solid var(--border); }
.summary tr:hover td { background: rgba(59,130,246,0.06); }
.summary .match-col { text-align: left; white-space: nowrap; }
.hit { color: var(--green); font-weight: 600; }
.miss { color: var(--red); font-weight: 600; }
.neutral { color: var(--dim); }
.upset-row td { background: rgba(239,68,68,0.05); }
.tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.tag-win { background: rgba(34,197,94,0.15); color: var(--green); }
.tag-draw { background: rgba(234,179,8,0.15); color: var(--yellow); }
.tag-lost { background: rgba(239,68,68,0.15); color: var(--red); }
.tag-upset { background: rgba(239,68,68,0.2); color: var(--red); margin-left: 4px; }
.tag-over { background: rgba(168,85,247,0.15); color: #a855f7; }
.tag-under { background: rgba(6,182,212,0.15); color: #06b6d4; }

/* match detail cards */
.match-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 24px; overflow: hidden; }
.match-card.upset { border-left: 3px solid var(--red); }
.card-header { padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); cursor: pointer; }
.card-header:hover { background: rgba(59,130,246,0.04); }
.card-header h3 { font-size: 16px; }
.card-body { padding: 16px 20px; display: none; }
.card-body.open { display: block; }
.dim-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 800px) { .dim-grid { grid-template-columns: 1fr; } }
.dim-box { background: var(--bg); border-radius: 8px; padding: 12px; }
.dim-box h4 { font-size: 12px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.dim-table { width: 100%; font-size: 12px; border-collapse: collapse; }
.dim-table td, .dim-table th { padding: 4px 6px; border-bottom: 1px solid var(--border); }
.dim-table th { color: var(--dim); font-weight: 500; text-align: left; }
.signal { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin: 2px; }
.signal-red { background: rgba(239,68,68,0.15); color: var(--red); }
.signal-yellow { background: rgba(234,179,8,0.15); color: var(--yellow); }
.signal-green { background: rgba(34,197,94,0.15); color: var(--green); }
.arrow-up { color: var(--red); }
.arrow-down { color: var(--green); }

.verdict { margin-top: 12px; padding: 10px 16px; border-radius: 6px; font-size: 13px; }
.verdict-correct { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); }
.verdict-wrong { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); }

.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px 20px; text-align: center; }
.stat-item .val { font-size: 24px; font-weight: 700; }
.stat-item .lbl { font-size: 11px; color: var(--dim); }
</style>
</head>
<body>
<div class="header">
  <h1>Backtest — 多维度信号 vs 赛果</h1>
  <p>12场已完赛比赛 · 7个分析维度</p>
</div>
<div class="container">
  <div class="stats-bar" id="statsBar"></div>
  <table class="summary" id="summaryTable"></table>
  <div id="matchCards"></div>
</div>
<script>
const A = """ + analysis_json + r""";

function arrow(v) { return v > 0 ? '<span class="arrow-up">+' + v + '</span>' : v < 0 ? '<span class="arrow-down">' + v + '</span>' : '<span class="neutral">0</span>'; }
function tag(cls, text) { return `<span class="tag tag-${cls}">${text}</span>`; }
function signal(cls, text) { return `<span class="signal signal-${cls}">${text}</span>`; }

// ── Stats bar ──
const upsets = A.filter(a => a.dims.eu && a.dims.eu.is_upset).length;
const ahHits = A.filter(a => {
  if (!a.dims.ah || !a.dims.eu) return false;
  return a.dims.ah.shrink_count >= 3 && a.dims.eu.is_upset;
}).length;
const ahSignals = A.filter(a => a.dims.ah && a.dims.ah.shrink_count >= 3).length;
const underCount = A.filter(a => a.dims.ou && a.dims.ou.result === 'UNDER').length;

document.getElementById('statsBar').innerHTML = `
  <div class="stat-item"><div class="val">${A.length}</div><div class="lbl">总场次</div></div>
  <div class="stat-item"><div class="val" style="color:var(--red)">${upsets}</div><div class="lbl">爆冷场次</div></div>
  <div class="stat-item"><div class="val" style="color:var(--green)">${ahSignals > 0 ? Math.round(ahHits/ahSignals*100) : 0}%</div><div class="lbl">亚盘缩水≥3家→冷门命中率</div></div>
  <div class="stat-item"><div class="val">${underCount}/${A.length}</div><div class="lbl">小球比例</div></div>
`;

// ── Summary table ──
let thtml = `<thead><tr>
  <th>比赛</th><th>比分</th><th>赛果</th>
  <th>D1 欧赔<br>胜率Δ</th>
  <th>D2 亚盘<br>缩水数</th>
  <th>D3 大小球<br>结果</th>
  <th>D4 赛前6h<br>变化次数</th>
  <th>D5 公司<br>一致性</th>
  <th>信号<br>命中</th>
</tr></thead><tbody>`;

A.forEach(a => {
  const m = a.match;
  const isUpset = a.dims.eu && a.dims.eu.is_upset;
  const rowCls = isUpset ? ' class="upset-row"' : '';

  // D1: avg wr delta
  let d1 = '-';
  if (a.dims.eu) {
    const avg = a.dims.eu.companies.find(c => c.id === '0');
    if (avg) d1 = arrow(avg.wr_delta + '%');
  }

  // D2: shrink count
  let d2 = '-';
  let d2signal = '';
  if (a.dims.ah) {
    const sc = a.dims.ah.shrink_count;
    d2 = sc > 0 ? signal(sc >= 3 ? 'red' : 'yellow', sc + '家缩水') : signal('green', '稳定');
  }

  // D3: over/under
  let d3 = '-';
  if (a.dims.ou) {
    const r = a.dims.ou.result;
    d3 = `${tag(r === 'OVER' ? 'over' : 'under', r)} ${a.total_goals}球`;
  }

  // D4: late changes
  let d4 = '-';
  if (a.dims.ts) {
    const total = a.dims.ts.companies.reduce((s, c) => s + c.late_count, 0);
    d4 = total > 10 ? signal('yellow', total + '次') : (total > 0 ? total + '次' : signal('green', '无'));
  }

  // D5: consensus
  let d5 = '-';
  if (a.dims.consensus) {
    const eu_n = a.dims.consensus.eu_same_dir;
    const ah_n = a.dims.consensus.ah_same_dir;
    d5 = `欧${eu_n} 亚${ah_n}`;
  }

  // Signal hit analysis
  let hitHtml = '';
  if (a.dims.ah && a.dims.ah.shrink_count >= 3) {
    if (isUpset) hitHtml += signal('green', '亚盘✓');
    else hitHtml += signal('red', '亚盘✗');
  }
  if (a.dims.eu && a.dims.eu.big_move_count >= 3) {
    // big move = should reverse
    if (isUpset) hitHtml += signal('green', '欧赔✓');
    else hitHtml += signal('red', '欧赔✗');
  }
  if (!hitHtml) hitHtml = '<span class="neutral">—</span>';

  const resultTag = tag(a.result === 'win' ? 'win' : a.result === 'draw' ? 'draw' : 'lost', a.result_cn);
  const upsetTag = isUpset ? tag('upset', '冷') : '';

  thtml += `<tr${rowCls}>
    <td class="match-col">${m.home} vs ${m.away}</td>
    <td><b>${m.score}</b></td>
    <td>${resultTag}${upsetTag}</td>
    <td>${d1}</td><td>${d2}</td><td>${d3}</td><td>${d4}</td><td>${d5}</td>
    <td>${hitHtml}</td>
  </tr>`;
});
thtml += '</tbody>';
document.getElementById('summaryTable').innerHTML = thtml;

// ── Detail cards ──
let cards = '';
A.forEach((a, idx) => {
  const m = a.match;
  const isUpset = a.dims.eu && a.dims.eu.is_upset;

  let header = `<div class="card-header" onclick="this.nextElementSibling.classList.toggle('open')">
    <h3>${m.date} ${m.time} — ${m.home} <b>${m.score}</b> ${m.away} ${tag(a.result === 'win' ? 'win' : a.result === 'draw' ? 'draw' : 'lost', a.result_cn)} ${isUpset ? tag('upset', '爆冷') : ''}</h3>
    <span style="color:var(--dim)">点击展开</span>
  </div>`;

  let body = '<div class="card-body"><div class="dim-grid">';

  // D1: EU detail
  if (a.dims.eu) {
    const eu = a.dims.eu;
    body += `<div class="dim-box"><h4>D1 欧赔变化</h4>
      <p style="margin-bottom:6px">热门: <b>${eu.favorite}</b> (${eu.fav_odds}, ${eu.fav_prob}%) ${isUpset ? signal('red', '未命中') : signal('green', '命中')}</p>
      <table class="dim-table"><tr><th>公司</th><th>初盘 胜/平/负</th><th>终盘 胜/平/负</th><th>胜率Δ</th></tr>`;
    eu.companies.forEach(c => {
      const cls = Math.abs(c.wr_delta) > 5 ? ' style="font-weight:600"' : '';
      body += `<tr><td>${c.name}</td><td>${c.init.join('/')}</td><td>${c.end.join('/')}</td><td${cls}>${arrow(c.wr_delta + '%')}</td></tr>`;
    });
    body += '</table></div>';
  }

  // D2: AH detail
  if (a.dims.ah) {
    const ah = a.dims.ah;
    body += `<div class="dim-box"><h4>D2 亚盘变化 ${ah.shrink_count >= 3 ? signal('red', ah.shrink_count + '家缩水') : ah.shrink_count > 0 ? signal('yellow', ah.shrink_count + '家缩水') : signal('green', '稳定')}</h4>
      <table class="dim-table"><tr><th>公司</th><th>初盘 水/盘/水</th><th>终盘 水/盘/水</th><th>主水Δ</th></tr>`;
    ah.companies.forEach(c => {
      const moved = c.line_moved ? ' style="background:rgba(239,68,68,0.06)"' : '';
      body += `<tr${moved}><td>${c.name}${c.line_moved ? ' ⚠' : ''}</td><td>${c.init_hw}/${c.init_h}/${c.init_aw}</td><td>${c.end_hw}/${c.end_h}/${c.end_aw}</td><td>${arrow(c.hw_delta)}</td></tr>`;
    });
    body += '</table></div>';
  }

  // D3: OU detail
  if (a.dims.ou) {
    const ou = a.dims.ou;
    body += `<div class="dim-box"><h4>D3 大小球 — 实际${a.total_goals}球 ${tag(ou.result === 'OVER' ? 'over' : 'under', ou.result)}</h4>
      <table class="dim-table"><tr><th>公司</th><th>初盘</th><th>终盘</th><th>大/小赔率</th></tr>`;
    ou.companies.forEach(c => {
      const moved = c.init_line !== c.end_line ? ' ⚠' : '';
      body += `<tr><td>${c.name}${moved}</td><td>${c.init_line}</td><td>${c.end_line}</td><td>${c.big}/${c.small}</td></tr>`;
    });
    body += '</table></div>';
  }

  // D4: Time series
  if (a.dims.ts && a.dims.ts.companies.length) {
    body += `<div class="dim-box"><h4>D4 赔率时序 (赛前6h)</h4>
      <table class="dim-table"><tr><th>公司</th><th>总变化</th><th>最后6h</th><th>6h方向 胜/平/负</th></tr>`;
    a.dims.ts.companies.forEach(c => {
      let dir = '-';
      if (c.late_w_delta !== undefined) {
        dir = `${arrow(c.late_w_delta)} / ${arrow(c.late_d_delta)} / ${arrow(c.late_l_delta)}`;
      }
      body += `<tr><td>${c.name}</td><td>${c.total_changes}</td><td>${c.late_count > 0 ? signal(c.late_count > 5 ? 'yellow' : 'green', c.late_count + '次') : '无'}</td><td>${dir}</td></tr>`;
    });
    body += '</table></div>';
  }

  body += '</div>'; // dim-grid

  // verdict
  const ahShrink = a.dims.ah ? a.dims.ah.shrink_count >= 3 : false;
  const euBig = a.dims.eu ? a.dims.eu.big_move_count >= 3 : false;
  let verdictText = '';
  if (ahShrink && isUpset) verdictText = '亚盘缩水≥3家 → 预测冷门 → 实际爆冷 ✓';
  else if (ahShrink && !isUpset) verdictText = '亚盘缩水≥3家 → 预测冷门 → 实际未冷 ✗';
  else if (!ahShrink && isUpset) verdictText = '亚盘无明显信号 → 未预测冷门 → 但实际爆冷 (漏报)';
  else verdictText = '亚盘无信号 → 正常赛事 → 热门获胜 ✓';

  const verdictCls = (ahShrink === isUpset) ? 'verdict-correct' : 'verdict-wrong';
  body += `<div class="verdict ${verdictCls}">${verdictText}</div>`;

  body += '</div>'; // card-body

  cards += `<div class="match-card ${isUpset ? 'upset' : ''}">${header}${body}</div>`;
});
document.getElementById('matchCards').innerHTML = cards;
</script>
</body>
</html>""";

out = ROOT / "output" / "backtest.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Backtest page: {out}")
print(f"Matches analyzed: {len(analysis)}")
