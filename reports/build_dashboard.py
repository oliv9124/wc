"""Build a single HTML dashboard from collected odds data."""
import json, glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CONFIG = ROOT / "worldcup_fids.json"
CID_MAP = ROOT / "cid_mapping_final.json"

with open(CONFIG, "r", encoding="utf-8") as f:
    config = json.load(f)
with open(CID_MAP, "r", encoding="utf-8") as f:
    cid_map = json.load(f)

matches = config["matches"]

qiu_cid_names = cid_map["qiuqiushidao"]["companies"]

data = {"matches": matches, "qiu_cid_names": qiu_cid_names, "overview": {}, "timeseries": {}}

for f in sorted(DATA_DIR.glob("qiu/overview/*.json")):
    key = f.stem  # e.g. 1279645_ouzhi
    with open(f, "r", encoding="utf-8") as fp:
        data["overview"][key] = json.load(fp)

for f in sorted(DATA_DIR.glob("qiu/timeseries/*.json")):
    key = f.stem  # e.g. 1279645_3_ouzhi
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
        if d.get("records") and len(d["records"]) > 0:
            data["timeseries"][key] = d

data_json = json.dumps(data, ensure_ascii=False)

html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 World Cup Odds Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
<style>
:root { --bg: #0f1117; --card: #1a1d27; --border: #2a2d3a; --text: #e4e4e7; --dim: #888; --accent: #3b82f6; --green: #22c55e; --red: #ef4444; --yellow: #eab308; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); }
.header { background: linear-gradient(135deg, #1e293b, #0f172a); padding: 24px 32px; border-bottom: 1px solid var(--border); }
.header h1 { font-size: 22px; font-weight: 600; }
.header p { color: var(--dim); font-size: 13px; margin-top: 4px; }
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
.controls { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 20px; }
.controls select { background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 6px; font-size: 14px; cursor: pointer; }
.controls select:hover { border-color: var(--accent); }
.match-info { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; display: flex; justify-content: center; align-items: center; gap: 32px; }
.team { text-align: center; font-size: 20px; font-weight: 600; min-width: 120px; }
.vs { color: var(--dim); font-size: 14px; }
.score { font-size: 28px; font-weight: 700; color: var(--accent); }
.match-meta { text-align: center; color: var(--dim); font-size: 13px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.panel { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.panel h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.5px; }
.panel.full { grid-column: 1 / -1; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--border); color: var(--dim); font-weight: 500; font-size: 12px; text-transform: uppercase; position: sticky; top: 0; background: var(--card); }
td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
tr:hover td { background: rgba(59,130,246,0.06); }
tr.clickable { cursor: pointer; }
tr.selected td { background: rgba(59,130,246,0.12); }
.up { color: var(--red); }
.down { color: var(--green); }
.neutral { color: var(--dim); }
.chart-wrap { height: 420px; position: relative; }
.tabs { display: inline-flex; gap: 2px; background: var(--bg); border-radius: 8px; padding: 3px; }
.tab { padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; color: var(--dim); transition: all 0.15s; user-select: none; }
.tab.active { background: var(--accent); color: #fff; }
.tab:hover:not(.active) { color: var(--text); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-win { background: rgba(34,197,94,0.15); color: var(--green); }
.badge-draw { background: rgba(234,179,8,0.15); color: var(--yellow); }
.badge-lose { background: rgba(239,68,68,0.15); color: var(--red); }
.scroll-table { max-height: 500px; overflow-y: auto; }
.stat-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; text-align: center; }
.stat-card .value { font-size: 28px; font-weight: 700; }
.stat-card .label { font-size: 12px; color: var(--dim); margin-top: 4px; }
.chart-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
.chip { padding: 5px 12px; border-radius: 16px; font-size: 12px; cursor: pointer; border: 1px solid var(--border); background: transparent; color: var(--dim); transition: all 0.15s; user-select: none; }
.chip.on { border-color: var(--accent); color: var(--accent); background: rgba(59,130,246,0.1); }
.chip:hover { border-color: var(--accent); color: var(--text); }
.chart-hint { font-size: 12px; color: var(--dim); margin-bottom: 8px; }
</style>
</head>
<body>
<div class="header">
  <h1>2026 FIFA World Cup — Odds Dashboard</h1>
  <p>Data from 球球是道 · Group Stage Round 1</p>
</div>
<div class="container">
  <div class="controls">
    <select id="matchSel"></select>
    <div class="tabs" id="typeTabs">
      <div class="tab active" data-type="ouzhi">欧赔</div>
      <div class="tab" data-type="yazhi">亚盘</div>
      <div class="tab" data-type="daxiao">大小球</div>
    </div>
  </div>
  <div id="matchInfo" class="match-info"></div>
  <div class="stat-cards" id="statCards"></div>
  <div class="grid">
    <div class="panel full">
      <h3>赔率走势 (球球是道)</h3>
      <div class="chart-hint">点击下方公司名切换显示，可同时选多个对比</div>
      <div class="chart-controls" id="chartControls"></div>
      <div class="chart-wrap"><canvas id="tsChart"></canvas></div>
    </div>
  </div>
  <div class="grid">
    <div class="panel full">
      <h3>球球是道 · 全公司快照 <span style="font-size:11px;color:var(--dim);font-weight:400">(点击行查看走势)</span></h3>
      <div class="scroll-table" id="qiuTable"></div>
    </div>
  </div>
</div>
<script>
const DATA = """ + data_json + r""";

const CID_NAMES = DATA.qiu_cid_names;
const KEY_CIDS = [0, 1055, 3, 293, 2, 280, 9, 6, 348, 651];
const LINE_COLORS = {
  ouzhi: { win: '#22c55e', draw: '#eab308', lost: '#ef4444' },
  yazhi: { home: '#3b82f6', away: '#f97316' },
  daxiao: { big: '#a855f7', small: '#06b6d4' }
};
const LINE_LABELS = {
  ouzhi: { win: '主胜', draw: '平局', lost: '客胜' },
  yazhi: { home: '主水', away: '客水' },
  daxiao: { big: '大球', small: '小球' }
};
const COMPANY_COLORS = ['#3b82f6','#ef4444','#22c55e','#eab308','#a855f7','#f97316','#06b6d4','#ec4899','#84cc16','#6366f1'];

let currentMatch = 0;
let currentType = 'ouzhi';
let selectedCids = new Set([3]);
let tsChart = null;

const sel = document.getElementById('matchSel');
DATA.matches.forEach((m, i) => {
  const opt = document.createElement('option');
  opt.value = i;
  opt.textContent = `${m.date} ${m.time} | ${m.group}组 | ${m.home} vs ${m.away}` + (m.score ? ` (${m.score})` : '');
  sel.appendChild(opt);
});
sel.onchange = () => { currentMatch = +sel.value; render(); };

document.querySelectorAll('.tab').forEach(t => {
  t.onclick = () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    currentType = t.dataset.type;
    render();
  };
});

function arrow(curr, init) {
  const c = parseFloat(curr), i = parseFloat(init);
  if (isNaN(c) || isNaN(i) || c === i) return ['', 'neutral'];
  return c > i ? ['↑', 'up'] : ['↓', 'down'];
}

function renderMatchInfo(m) {
  document.getElementById('matchInfo').innerHTML = `
    <div class="team">${m.home}</div>
    <div style="text-align:center">
      ${m.score ? `<div class="score">${m.score}</div>` : '<div class="vs">VS</div>'}
      <div class="match-meta">${m.date} ${m.time} · ${m.group}组</div>
      <div class="match-meta">${m.status === 'finished' ? '已完赛' : '未开赛'}</div>
    </div>
    <div class="team">${m.away}</div>`;
}

function renderStats(m) {
  const div = document.getElementById('statCards');
  const ov = DATA.overview[`${m.qiu_fid}_ouzhi`];
  if (!ov || !ov.rows) { div.innerHTML = ''; return; }
  const avg = ov.rows.find(r => r.id === '0');
  if (!avg) { div.innerHTML = ''; return; }
  const e = avg.end || avg.first;
  div.innerHTML = `
    <div class="stat-card"><div class="value" style="color:var(--green)">${e.win}</div><div class="label">平均主胜</div></div>
    <div class="stat-card"><div class="value" style="color:var(--yellow)">${e.draw}</div><div class="label">平均平局</div></div>
    <div class="stat-card"><div class="value" style="color:var(--red)">${e.lost}</div><div class="label">平均客胜</div></div>
    <div class="stat-card"><div class="value">${e.pay}%</div><div class="label">返还率</div></div>
    <div class="stat-card"><div class="value badge badge-win">${parseFloat(e.winrate||e.wgl).toFixed(1)}%</div><div class="label">主胜概率</div></div>
    <div class="stat-card"><div class="value badge badge-draw">${parseFloat(e.drawrate||e.dgl).toFixed(1)}%</div><div class="label">平局概率</div></div>`;
}

function selectCid(cid) {
  if (selectedCids.has(cid)) selectedCids.delete(cid);
  else selectedCids.add(cid);
  if (selectedCids.size === 0) selectedCids.add(cid);
  renderChartControls();
  renderTimeSeries(DATA.matches[currentMatch]);
  highlightTableRows();
}

function renderChartControls() {
  const m = DATA.matches[currentMatch];
  const div = document.getElementById('chartControls');
  let html = '';
  KEY_CIDS.forEach(cid => {
    const key = `${m.qiu_fid}_${cid}_${currentType}`;
    const ts = DATA.timeseries[key];
    const has = ts && ts.records && ts.records.length > 0;
    if (!has) return;
    const name = CID_NAMES[String(cid)] || `CID${cid}`;
    const on = selectedCids.has(cid);
    const cnt = ts.records.length;
    html += `<div class="chip ${on ? 'on' : ''}" onclick="selectCid(${cid})">${name} <span style="opacity:0.5">(${cnt})</span></div>`;
  });
  div.innerHTML = html;
}

function highlightTableRows() {
  document.querySelectorAll('#qiuTable tr[data-cid]').forEach(tr => {
    tr.classList.toggle('selected', selectedCids.has(+tr.dataset.cid));
  });
}

function renderQiuTable(m) {
  const div = document.getElementById('qiuTable');
  const key = `${m.qiu_fid}_${currentType}`;
  const ov = DATA.overview[key];
  if (!ov || !ov.rows) { div.innerHTML = '<p style="color:var(--dim)">无数据</p>'; return; }

  if (currentType === 'ouzhi') {
    let html = '<table><thead><tr><th>公司</th><th>初胜</th><th>初平</th><th>初负</th><th>即时胜</th><th>即时平</th><th>即时负</th><th>返还</th></tr></thead><tbody>';
    ov.rows.forEach(r => {
      const f = r.first, e = r.end || f;
      const [aw,cw] = arrow(e.win, f.win), [ad,cd] = arrow(e.draw, f.draw), [al,cl] = arrow(e.lost, f.lost);
      const hasTsKey = `${m.qiu_fid}_${r.id}_${currentType}`;
      const hasTs = !!DATA.timeseries[hasTsKey];
      const sel = selectedCids.has(+r.id) ? 'selected' : '';
      html += `<tr class="${hasTs ? 'clickable' : ''} ${sel}" data-cid="${r.id}" ${hasTs ? `onclick="selectCid(${r.id})"` : ''}><td><b>${r.name}</b></td><td>${f.win}</td><td>${f.draw}</td><td>${f.lost}</td><td class="${cw}">${e.win} ${aw}</td><td class="${cd}">${e.draw} ${ad}</td><td class="${cl}">${e.lost} ${al}</td><td>${e.pay}%</td></tr>`;
    });
    div.innerHTML = html + '</tbody></table>';
  } else if (currentType === 'yazhi') {
    let html = '<table><thead><tr><th>公司</th><th>初主水</th><th>初盘口</th><th>初客水</th><th>即时主水</th><th>即时盘口</th><th>即时客水</th></tr></thead><tbody>';
    ov.rows.forEach(r => {
      const f = r.first, e = r.end || f;
      const hasTsKey = `${m.qiu_fid}_${r.id}_${currentType}`;
      const hasTs = !!DATA.timeseries[hasTsKey];
      const sel = selectedCids.has(+r.id) ? 'selected' : '';
      html += `<tr class="${hasTs ? 'clickable' : ''} ${sel}" data-cid="${r.id}" ${hasTs ? `onclick="selectCid(${r.id})"` : ''}><td><b>${r.name}</b></td><td>${f.home}</td><td>${f.handline}</td><td>${f.away}</td><td>${e.home}</td><td>${e.handline}</td><td>${e.away}</td></tr>`;
    });
    div.innerHTML = html + '</tbody></table>';
  } else {
    let html = '<table><thead><tr><th>公司</th><th>初大球</th><th>初盘口</th><th>初小球</th><th>即时大球</th><th>即时盘口</th><th>即时小球</th></tr></thead><tbody>';
    ov.rows.forEach(r => {
      const f = r.first, e = r.end || f;
      const hasTsKey = `${m.qiu_fid}_${r.id}_${currentType}`;
      const hasTs = !!DATA.timeseries[hasTsKey];
      const sel = selectedCids.has(+r.id) ? 'selected' : '';
      html += `<tr class="${hasTs ? 'clickable' : ''} ${sel}" data-cid="${r.id}" ${hasTs ? `onclick="selectCid(${r.id})"` : ''}><td><b>${r.name}</b></td><td>${f.big}</td><td>${f.handi}</td><td>${f.small}</td><td>${e.big}</td><td>${e.handi}</td><td>${e.small}</td></tr>`;
    });
    div.innerHTML = html + '</tbody></table>';
  }
}

function renderTimeSeries(m) {
  const ctx = document.getElementById('tsChart');
  if (tsChart) tsChart.destroy();

  const fields = Object.keys(LINE_COLORS[currentType]);
  const labels = LINE_LABELS[currentType];
  const colors = LINE_COLORS[currentType];
  const datasets = [];

  const cids = [...selectedCids];
  const multi = cids.length > 1;

  // collect all timestamps across selected companies for the X axis labels
  let allTimestamps = [];

  cids.forEach((cid, ci) => {
    const key = `${m.qiu_fid}_${cid}_${currentType}`;
    const ts = DATA.timeseries[key];
    if (!ts || !ts.records || ts.records.length === 0) return;
    const name = CID_NAMES[String(cid)] || `CID${cid}`;
    const compColor = COMPANY_COLORS[ci % COMPANY_COLORS.length];
    const records = ts.records;

    records.forEach(r => allTimestamps.push(r.time));

    fields.forEach((field, fi) => {
      const dashes = multi ? [] : (fi === 1 ? [6, 3] : (fi === 2 ? [2, 2] : []));
      const color = multi ? compColor : colors[field];
      // index-based: x = record index, store time for tooltip
      const pts = [];
      records.forEach((r, idx) => {
        const v = parseFloat(r[field]);
        if (!isNaN(v)) pts.push({ x: idx, y: v, _time: r.time });
      });
      datasets.push({
        label: multi ? `${name} ${labels[field]}` : labels[field],
        data: pts,
        borderColor: color,
        backgroundColor: color + '15',
        borderWidth: 2.5,
        borderDash: dashes,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: color,
        tension: 0.2,
        fill: !multi && fi === 0,
        _times: records.map(r => r.time),
      });
    });
  });

  // for multi-company: find the longest record set for tick labels
  let maxLen = 0;
  let refTimes = [];
  cids.forEach(cid => {
    const key = `${m.qiu_fid}_${cid}_${currentType}`;
    const ts = DATA.timeseries[key];
    if (ts && ts.records && ts.records.length > maxLen) {
      maxLen = ts.records.length;
      refTimes = ts.records.map(r => r.time);
    }
  });

  // pick ~10 evenly spaced tick positions for X axis labels
  const tickIndices = [];
  const tickLabels = {};
  if (maxLen > 0) {
    const step = Math.max(1, Math.floor(maxLen / 10));
    for (let i = 0; i < maxLen; i += step) tickIndices.push(i);
    if (tickIndices[tickIndices.length - 1] !== maxLen - 1) tickIndices.push(maxLen - 1);
    tickIndices.forEach(i => {
      const t = refTimes[i];
      if (t) {
        const d = new Date(t);
        tickLabels[i] = `${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
      }
    });
  }

  tsChart = new Chart(ctx, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
      scales: {
        x: {
          type: 'linear',
          min: 0,
          max: maxLen - 1,
          grid: { color: '#2a2d3a33' },
          ticks: {
            color: '#888',
            font: { size: 11 },
            callback: (val) => tickLabels[val] || '',
            autoSkip: false,
            maxRotation: 35,
            includeBounds: true,
          },
          afterBuildTicks: (axis) => {
            axis.ticks = tickIndices.map(v => ({ value: v }));
          },
          title: { display: true, text: '← 早期（压缩）              临近开赛（展开） →', color: '#555', font: { size: 11 } }
        },
        y: {
          grid: { color: '#2a2d3a55' },
          ticks: { color: '#888', font: { size: 11 } }
        }
      },
      plugins: {
        legend: {
          labels: { color: '#ccc', boxWidth: 20, padding: 16, font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: '#1a1d27ee',
          borderColor: '#3b82f6',
          borderWidth: 1,
          titleFont: { size: 12 },
          bodyFont: { size: 12 },
          padding: 10,
          callbacks: {
            title: (items) => {
              if (!items.length) return '';
              const pt = items[0].raw;
              return pt._time || '';
            },
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}`
          }
        }
      }
    }
  });
}

function render() {
  const m = DATA.matches[currentMatch];
  renderMatchInfo(m);
  renderStats(m);
  renderChartControls();
  renderQiuTable(m);
  renderTimeSeries(m);
}

render();
</script>
</body>
</html>"""

out = ROOT / "output" / "dashboard.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dashboard written to {out}")
print(f"Data size: {len(data_json)//1024} KB")
print(f"  Overview files: {len(data.get('overview', {}))}")
print(f"  Timeseries files: {len(data.get('timeseries', {}))}")
