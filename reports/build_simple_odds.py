import json, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG = ROOT / "worldcup_fids.json"
W500_DIR = ROOT / "data" / "w500"
QIU_DIR = ROOT / "data" / "qiu" / "overview"
QIU_TS_DIR = ROOT / "data" / "qiu" / "timeseries"

def extract_qiu(fid, kind):
    # kind can be "ouzhi", "yazhi", "daxiao"
    companies = []
    p = QIU_DIR / f"{fid}_{kind}.json"
    if not p.exists(): return companies
    
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
        for row in d.get("rows", []):
            first = row.get("first") or {}
            end = row.get("end") or first
            cid = row.get("id")
            
            # Map keys based on kind
            if kind == "ouzhi":
                if "win" not in first: continue
                init_vals = [first.get("win",""), first.get("draw",""), first.get("lost","")]
                final_vals = [end.get("win",""), end.get("draw",""), end.get("lost","")]
                kelly_vals = [end.get("winkl",""), end.get("drawkl",""), end.get("lostkl","")]
            elif kind == "yazhi":
                if "home" not in first: continue
                init_vals = [first.get("home",""), first.get("handline", first.get("handi", "")), first.get("away","")]
                final_vals = [end.get("home",""), end.get("handline", end.get("handi", "")), end.get("away","")]
                kelly_vals = []
            elif kind == "daxiao":
                if "big" not in first: continue
                init_vals = [first.get("big",""), first.get("handi",""), first.get("small","")]
                final_vals = [end.get("big",""), end.get("handi",""), end.get("small","")]
                kelly_vals = []

            history = []
            ts_path = QIU_TS_DIR / f"{fid}_{cid}_{kind}.json"
            if ts_path.exists():
                with open(ts_path, "r", encoding="utf-8") as f_ts:
                    ts_data = json.load(f_ts)
                    for rec in ts_data.get("records", []):
                        if kind == "ouzhi":
                            history.append({"val1": rec.get("win"), "val2": rec.get("draw"), "val3": rec.get("lost"), "time": rec.get("time")})
                        elif kind == "yazhi":
                            history.append({"val1": rec.get("home"), "val2": rec.get("handi"), "val3": rec.get("away"), "time": rec.get("time")})
                        elif kind == "daxiao":
                            history.append({"val1": rec.get("big"), "val2": rec.get("handi"), "val3": rec.get("small"), "time": rec.get("time")})

            companies.append({
                "name": row.get("name", ""),
                "init": init_vals,
                "final": final_vals,
                "kelly": kelly_vals,
                "history": history
            })
    return companies

def build():
    with open(CONFIG, "r", encoding="utf-8") as f:
        matches = json.load(f)["matches"]

    all_data = []

    for m in matches:
        mid = m.get("w500_mid")
        fid = m.get("qiu_fid")
        
        match_info = {
            "title": f"{m['home']} vs {m['away']}",
            "date": m["date"],
            "time": m["time"],
            "group": m.get("group", ""),
            "score": m.get("score", "")
        }

        w500_data = {"eu": [], "ah": [], "ou": [], "rq": []}
        if mid and (W500_DIR / f"{mid}.json").exists():
            with open(W500_DIR / f"{mid}.json", "r", encoding="utf-8") as f:
                d = json.load(f)
                for cid, cdata in d.get("companies", {}).items():
                    name = cdata.get("name", cid)
                    if "eu" in cdata and len(cdata["eu"]) > 0:
                        eu = cdata["eu"]
                        w500_data["eu"].append({
                            "name": name,
                            "init": [eu[-1][0], eu[-1][1], eu[-1][2]],
                            "final": [eu[0][0], eu[0][1], eu[0][2]],
                            "history": [{"val1": x[0], "val2": x[1], "val3": x[2], "time": x[4]} for x in eu]
                        })
                    if "ah" in cdata and len(cdata["ah"]) > 0:
                        ah = cdata["ah"]
                        w500_data["ah"].append({
                            "name": name,
                            "init": [ah[-1][0], ah[-1][1], ah[-1][2]],
                            "final": [ah[0][0], ah[0][1], ah[0][2]],
                            "history": [{"val1": x[0], "val2": x[1], "val3": x[2], "time": x[3]} for x in ah]
                        })
                    if "ou" in cdata and len(cdata["ou"]) > 0:
                        ou = cdata["ou"]
                        w500_data["ou"].append({
                            "name": name,
                            "init": [ou[-1][0], ou[-1][1], ou[-1][2]],
                            "final": [ou[0][0], ou[0][1], ou[0][2]],
                            "history": [{"val1": x[0], "val2": x[1], "val3": x[2], "time": x[3]} for x in ou]
                        })
                    if "rq" in cdata and len(cdata["rq"]) > 0:
                        rq = cdata["rq"]
                        line = rq[-1][3] if len(rq[-1]) > 3 else ""
                        w500_data["rq"].append({
                            "name": name + f" (让{line})",
                            "init": [rq[-1][0], rq[-1][1], rq[-1][2]],
                            "final": [rq[0][0], rq[0][1], rq[0][2]],
                            "history": [{"val1": x[0], "val2": x[1], "val3": x[2], "time": x[4]} for x in rq]
                        })

        qiu_data = {
            "eu": extract_qiu(fid, "ouzhi"),
            "ah": extract_qiu(fid, "yazhi"),
            "ou": extract_qiu(fid, "daxiao")
        }

        all_data.append({
            "info": match_info,
            "w500": w500_data,
            "qiu": qiu_data
        })

    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simple Odds Explorer</title>
<style>
:root { --bg: #f0f4f8; --card: #ffffff; --border: #e2e8f0; --text: #1e293b; --dim: #64748b; --accent: #2563eb; --green: #16a34a; --red: #dc2626; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }

.sidebar { width: 300px; background: var(--card); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
.sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); font-weight: bold; font-size: 18px; color: var(--accent); }
.match-list { flex: 1; overflow-y: auto; padding: 10px; }
.match-item { padding: 12px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; transition: background 0.2s; border: 1px solid transparent; }
.match-item:hover { background: #e0e7ff; border-color: #c7d2fe; }
.match-item.active { background: var(--accent); color: white; border-color: var(--accent); box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2); }
.match-item .time { font-size: 12px; color: var(--dim); margin-bottom: 4px; }
.match-item.active .time { color: rgba(255,255,255,0.8); }

.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.main-header { padding: 20px 30px; background: var(--card); border-bottom: 1px solid var(--border); display: flex; gap: 20px; align-items: center; justify-content: space-between; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); z-index: 10; }
.main-header h1 { font-size: 24px; margin-right: 20px; color: var(--text); }
.tabs-container { display: flex; flex-direction: column; gap: 10px; }
.tabs { display: flex; gap: 10px; }
.subtabs { display: flex; gap: 8px; }
.tab { padding: 8px 16px; background: #f1f5f9; border: 1px solid var(--border); color: var(--dim); border-radius: 20px; cursor: pointer; font-weight: 500; transition: all 0.2s; }
.tab:hover { background: #e2e8f0; color: var(--text); }
.tab.active { background: var(--accent); border-color: var(--accent); color: white; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2); }
.subtab { padding: 4px 12px; background: transparent; border: none; color: var(--dim); cursor: pointer; border-bottom: 2px solid transparent; font-size: 14px; font-weight: 500; transition: color 0.2s; }
.subtab:hover { color: var(--accent); }
.subtab.active { color: var(--accent); border-bottom-color: var(--accent); }

.content { flex: 1; overflow-y: auto; padding: 30px; background: var(--bg); }
.table-wrapper { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
table { width: 100%; border-collapse: collapse; text-align: left; }
th, td { padding: 14px 16px; border-bottom: 1px solid var(--border); font-size: 14px; }
th { color: var(--dim); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; background: #f8fafc; }
tr:last-child td { border-bottom: none; }
tr:hover { background: #f8fafc; }

.up { color: var(--red); font-weight: bold; }
.down { color: var(--green); font-weight: bold; }

.btn-history { background: white; border: 1px solid var(--border); color: var(--accent); padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; transition: all 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.btn-history:hover { border-color: var(--accent); background: #eff6ff; }

.history-row { display: none; background: #f8fafc; border-top: 1px solid var(--border); }
.history-row.open { display: table-row; }
.history-content { padding: 16px 24px; }
.history-item { display: flex; gap: 20px; font-size: 13px; color: var(--dim); margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #e2e8f0; }
.history-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.history-item span { min-width: 60px; color: var(--text); }
.history-item span:first-child { color: var(--dim); min-width: 140px; }

.empty-state { padding: 60px; text-align: center; color: var(--dim); font-size: 16px; background: var(--card); border-radius: 12px; border: 1px dashed var(--border); }
</style>
</head>
<body>

<div class="sidebar">
    <div class="sidebar-header">Matches</div>
    <div class="match-list" id="matchList"></div>
</div>

<div class="main">
    <div class="main-header">
        <h1 id="matchTitle">Select a match</h1>
        <div class="tabs-container" id="tabsContainer" style="display:none;">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('w500')">500.com (主流)</button>
                <button class="tab" onclick="switchTab('qiu')">球球是道 (国内)</button>
            </div>
            <div class="subtabs">
                <button class="subtab active" onclick="switchSubTab('eu')">欧赔 (胜/平/负)</button>
                <button class="subtab" onclick="switchSubTab('rq')">让球胜平负 (RQ)</button>
                <button class="subtab" onclick="switchSubTab('ah')">亚盘 (主/让/客)</button>
                <button class="subtab" onclick="switchSubTab('ou')">大小球 (大/盘/小)</button>
            </div>
        </div>
    </div>
    <div class="content" id="contentArea">
        <div class="empty-state">Please select a match from the sidebar.</div>
    </div>
</div>

<script>
const DATA = """ + json.dumps(all_data, ensure_ascii=False) + """;
let currentMatchIdx = -1;
let currentTab = 'w500';
let currentSubTab = 'eu';

function renderMatches() {
    const list = document.getElementById('matchList');
    list.innerHTML = '';
    DATA.forEach((m, idx) => {
        const div = document.createElement('div');
        div.className = `match-item ${idx === currentMatchIdx ? 'active' : ''}`;
        div.innerHTML = `
            <div class="time">${m.info.date} ${m.info.time} | ${m.info.group}</div>
            <div>${m.info.title} ${m.info.score ? '('+m.info.score+')' : ''}</div>
        `;
        div.onclick = () => selectMatch(idx);
        list.appendChild(div);
    });
}

function selectMatch(idx) {
    currentMatchIdx = idx;
    renderMatches();
    document.getElementById('matchTitle').textContent = DATA[idx].info.title;
    document.getElementById('tabsContainer').style.display = 'flex';
    renderContent();
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    renderContent();
}

function switchSubTab(subtab) {
    currentSubTab = subtab;
    document.querySelectorAll('.subtab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    renderContent();
}

function renderContent() {
    const area = document.getElementById('contentArea');
    if (currentMatchIdx === -1) return;
    const match = DATA[currentMatchIdx];
    const dataList = match[currentTab][currentSubTab];

    if (!dataList || dataList.length === 0) {
        area.innerHTML = `<div class="empty-state">No data available for this category.</div>`;
        return;
    }

    let headers = ['公司', '初盘', '终盘'];
    if (currentTab === 'qiu' && currentSubTab === 'eu') {
        headers.push('终盘凯利');
    }
    headers.push('操作');

    let html = `
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>
                </thead>
                <tbody>
    `;

    dataList.forEach((co, idx) => {
        const i = co.init;
        const f = co.final;
        
        const getTrend = (init, final) => {
            if (init === '' || final === '' || isNaN(parseFloat(init)) || isNaN(parseFloat(final))) return '';
            const di = parseFloat(init), df = parseFloat(final);
            if (df > di) return ' <span class="up">↑</span>';
            if (df < di) return ' <span class="down">↓</span>';
            return '';
        };

        const initStr = `${i[0]} / ${i[1]} / ${i[2]}`;
        const finalStr = `${f[0]}${getTrend(i[0],f[0])} / ${f[1]}${getTrend(i[1],f[1])} / ${f[2]}${getTrend(i[2],f[2])}`;
        const kellyStr = (currentTab === 'qiu' && currentSubTab === 'eu') ? `<td>${co.kelly[0]} / ${co.kelly[1]} / ${co.kelly[2]}</td>` : '';
        
        const hasHistory = co.history && co.history.length > 0;
        const historyBtn = hasHistory ? `<button class="btn-history" onclick="toggleHistory(${idx})">查看变动</button>` : `<span style="color:#888;font-size:12px;">无历史</span>`;

        html += `
            <tr>
                <td><strong>${co.name}</strong></td>
                <td>${initStr}</td>
                <td>${finalStr}</td>
                ${kellyStr}
                <td>${historyBtn}</td>
            </tr>
        `;

        if (hasHistory) {
            html += `
                <tr class="history-row" id="hist-${idx}">
                    <td colspan="${headers.length}">
                        <div class="history-content">
                            ${co.history.map(h => `
                                <div class="history-item">
                                    <span style="width:140px">${h.time}</span>
                                    <span>${h.val1}</span>
                                    <span>${h.val2}</span>
                                    <span>${h.val3}</span>
                                </div>
                            `).join('')}
                        </div>
                    </td>
                </tr>
            `;
        }
    });

    html += `</tbody></table></div>`;
    area.innerHTML = html;
}

function toggleHistory(idx) {
    const el = document.getElementById(`hist-${idx}`);
    el.classList.toggle('open');
}

renderMatches();
</script>
</body>
</html>
"""
    
    with open(ROOT / "output" / "simple_odds.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Generated simple_odds.html")

if __name__ == "__main__":
    build()
