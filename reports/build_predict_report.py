"""Build a comprehensive HTML report for all matches using the core prediction logic."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent
CONFIG = ROOT / "worldcup_fids.json"

# Import from our refactored predict logic
sys.path.insert(0, str(ROOT))
from predict import analyze_match_core, load_match, load_qiu, RESULT_CN

def build_report():
    with open(CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    matches = config.get("matches", [])
    analysis_data = []
    
    stats = {
        "total": 0, "finished": 0, "hits": 0,
        "kelly_trigger": 0, "kelly_hits": 0,
        "fake_trigger": 0, "fake_hits": 0,
        "squeeze_trigger": 0, "squeeze_hits": 0
    }
    
    print("Analyzing matches...")
    for m in matches:
        mid = m.get("w500_mid")
        fid = m.get("qiu_fid")
        if not mid: continue
        
        data = load_match(mid)
        if not data: continue
        qiu_eu = load_qiu(fid, "ouzhi") if fid else None
        qiu_yazhi = load_qiu(fid, "yazhi") if fid else None
        qiu_daxiao = load_qiu(fid, "daxiao") if fid else None
        
        res = analyze_match_core(m, data, qiu_eu, qiu_yazhi, qiu_daxiao)
        stats["total"] += 1
        
        is_finished = m.get("status") == "finished" and bool(m.get("score"))
        if is_finished and res.get("final_pred"):
            stats["finished"] += 1
            if res.get("is_hit"): stats["hits"] += 1
            
            strats = res.get("strategies", [])
            if "kelly_shield" in strats:
                stats["kelly_trigger"] += 1
                if res.get("is_hit"): stats["kelly_hits"] += 1
            if "fake_upgrade" in strats:
                stats["fake_trigger"] += 1
                if res.get("is_hit"): stats["fake_hits"] += 1
            if "squeeze_retreat_strong" in strats:
                stats["squeeze_trigger"] += 1
                if res.get("is_hit"): stats["squeeze_hits"] += 1
                
        if res.get("recommendation"):
            res["recommendation"] = list(res["recommendation"])
            
        analysis_data.append(res)
        
    # Reverse analysis data to show latest first
    analysis_data.reverse()

    analysis_json = json.dumps(analysis_data, ensure_ascii=False)
    
    overall_hr = round(stats["hits"] / stats["finished"] * 100) if stats["finished"] > 0 else 0
    kelly_hr = round(stats["kelly_hits"] / stats["kelly_trigger"] * 100) if stats["kelly_trigger"] > 0 else 0
    fake_hr = round(stats["fake_hits"] / stats["fake_trigger"] * 100) if stats["fake_trigger"] > 0 else 0
    sq_hr = round(stats["squeeze_hits"] / stats["squeeze_trigger"] * 100) if stats["squeeze_trigger"] > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup AI Prediction Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{
    --bg-color: #0f172a;
    --card-bg: rgba(30, 41, 59, 0.6);
    --border-color: rgba(255, 255, 255, 0.08);
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --accent: #3b82f6;
    --hit-color: #22c55e;
    --hit-bg: rgba(34, 197, 94, 0.15);
    --miss-color: #ef4444;
    --miss-bg: rgba(239, 68, 68, 0.15);
    --pending-color: #f59e0b;
    --pending-bg: rgba(245, 158, 11, 0.15);
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }}
body {{ background: linear-gradient(135deg, #020617 0%, #0f172a 100%); color: var(--text-primary); min-height: 100vh; line-height: 1.6; padding-bottom: 60px; }}

.navbar {{
    background: rgba(15, 23, 42, 0.8);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-color);
    padding: 20px 40px;
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.navbar h1 {{ font-size: 24px; font-weight: 800; background: linear-gradient(to right, #60a5fa, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.navbar .sub {{ color: var(--text-secondary); font-size: 14px; font-weight: 500; }}

.container {{ max-width: 1200px; margin: 40px auto; padding: 0 20px; }}

.stats-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 24px; margin-bottom: 40px;
}}
.stat-card {{
    background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 16px; padding: 24px;
    backdrop-filter: blur(12px); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}}
.stat-card:hover {{ transform: translateY(-4px); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); border-color: rgba(255,255,255,0.15); }}
.stat-value {{ font-size: 36px; font-weight: 800; margin-bottom: 8px; }}
.stat-label {{ font-size: 13px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }}

.match-list {{ display: flex; flex-direction: column; gap: 20px; }}

.match-card {{
    background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 16px;
    backdrop-filter: blur(12px); overflow: hidden; transition: all 0.3s ease;
}}
.match-card:hover {{ border-color: rgba(255,255,255,0.15); }}

.mc-header {{
    padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; cursor: pointer;
}}
.mc-header:hover {{ background: rgba(255,255,255,0.02); }}

.mc-info {{ display: flex; align-items: center; gap: 24px; flex: 1; }}
.mc-time {{ font-size: 14px; color: var(--text-secondary); font-weight: 500; width: 140px; }}
.mc-teams {{ font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 16px; flex: 1; }}
.mc-score {{ font-size: 20px; color: var(--accent); background: rgba(59,130,246,0.1); padding: 4px 12px; border-radius: 8px; letter-spacing: 2px; }}

.mc-result-badge {{
    padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}}
.badge-hit {{ background: var(--hit-bg); color: var(--hit-color); border: 1px solid rgba(34,197,94,0.3); }}
.badge-miss {{ background: var(--miss-bg); color: var(--miss-color); border: 1px solid rgba(239,68,68,0.3); }}
.badge-pending {{ background: var(--pending-bg); color: var(--pending-color); border: 1px solid rgba(245,158,11,0.3); }}

.mc-body {{
    display: none; padding: 0 24px 24px 24px; border-top: 1px solid var(--border-color);
    animation: fadeIn 0.3s ease;
}}
.mc-body.open {{ display: block; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-5px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.logic-banner {{
    background: rgba(15, 23, 42, 0.6); border-radius: 12px; padding: 16px 20px; margin-top: 20px;
    border-left: 4px solid var(--accent);
}}
.logic-title {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }}
.logic-text {{ font-size: 15px; font-weight: 600; color: #e2e8f0; }}

.signals-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;
}}
@media (max-width: 768px) {{ .signals-grid {{ grid-template-columns: 1fr; }} .mc-info {{ flex-direction: column; align-items: flex-start; gap: 8px; }} }}

.signal-box {{
    background: rgba(0,0,0,0.2); border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.05);
}}
.signal-box h4 {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; }}
.signal-list {{ list-style: none; }}
.signal-list li {{ font-size: 13px; margin-bottom: 8px; display: flex; align-items: flex-start; gap: 8px; }}
.sig-lv-HIGH {{ color: #ef4444; }}
.sig-lv-MED {{ color: #f59e0b; }}
.sig-lv-LOW {{ color: #22c55e; }}

.strats-tags {{ display: flex; gap: 8px; margin-top: 12px; }}
.strat-tag {{ font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(59,130,246,0.2); color: #60a5fa; font-weight: 600; }}

</style>
</head>
<body>

<div class="navbar">
    <h1>Antigravity Predictor</h1>
    <div class="sub">World Cup 2026 AI Report</div>
</div>

<div class="container">
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value" style="color: #60a5fa;">{overall_hr}%</div>
            <div class="stat-label">Overall Hit Rate ({stats['hits']}/{stats['finished']})</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #c084fc;">{kelly_hr}%</div>
            <div class="stat-label">Kelly Shield Hits ({stats['kelly_hits']}/{stats['kelly_trigger']})</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #f472b6;">{fake_hr}%</div>
            <div class="stat-label">Fake Upgrade Hits ({stats['fake_hits']}/{stats['fake_trigger']})</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #34d399;">{sq_hr}%</div>
            <div class="stat-label">Squeeze+Retreat Hits ({stats['squeeze_hits']}/{stats['squeeze_trigger']})</div>
        </div>
    </div>

    <div class="match-list" id="matchList"></div>
</div>

<script>
const DATA = {analysis_json};

function getResultCN(en) {{
    const map = {{"win": "主胜", "draw": "平局", "lose": "客胜"}};
    return map[en] || en;
}}

function renderMatches() {{
    const container = document.getElementById('matchList');
    let html = '';

    DATA.forEach(d => {{
        const m = d.match;
        const isFinished = !!d.score;
        let badgeClass = 'badge-pending';
        let badgeText = '等待开赛';
        
        if (isFinished) {{
            if (d.is_hit) {{ badgeClass = 'badge-hit'; badgeText = '✓ 命中'; }}
            else {{ badgeClass = 'badge-miss'; badgeText = '✗ 未命中'; }}
        }}

        let stratsHtml = '';
        if (d.strategies && d.strategies.length > 0) {{
            stratsHtml = '<div class="strats-tags">' + d.strategies.map(s => `<span class="strat-tag">${{s}}</span>`).join('') + '</div>';
        }}

        let signalsHtml = '';
        if (d.signals && d.signals.length > 0) {{
            signalsHtml = '<ul class="signal-list">' + d.signals.map(s => `
                <li><span class="sig-lv-${{s.lv}}">●</span> <span><b>[${{s.tag}}]</b> ${{s.msg}}</span></li>
            `).join('') + '</ul>';
        }}

        let driftHtml = '<p style="font-size:13px;color:var(--text-secondary)">无数据</p>';
        if (d.eu && d.eu.all) {{
            const a = d.eu.all.avg;
            driftHtml = `<p style="font-size:13px;color:#e2e8f0;margin-bottom:8px">W: <span style="color:${{a[0]>0?'#ef4444':'#22c55e'}}">${{a[0]>0?'+':''}}${{a[0].toFixed(2)}}%</span> | D: <span style="color:${{a[1]>0?'#ef4444':'#22c55e'}}">${{a[1]>0?'+':''}}${{a[1].toFixed(2)}}%</span> | L: <span style="color:${{a[2]>0?'#ef4444':'#22c55e'}}">${{a[2]>0?'+':''}}${{a[2].toFixed(2)}}%</span></p>`;
        }}

        html += `
            <div class="match-card">
                <div class="mc-header" onclick="this.nextElementSibling.classList.toggle('open')">
                    <div class="mc-info">
                        <div class="mc-time">${{m.date.substring(5)}} ${{m.time}} | ${{m.group}}组</div>
                        <div class="mc-teams">
                            ${{m.home}} 
                            ${{d.score ? `<span class="mc-score">${{d.score}}</span>` : '<span style="color:var(--text-secondary);font-weight:400;font-size:14px">vs</span>'}}
                            ${{m.away}}
                        </div>
                    </div>
                    <div class="mc-result-badge ${{badgeClass}}">${{badgeText}}</div>
                </div>
                <div class="mc-body">
                    <div class="logic-banner">
                        <div class="logic-title">预测结果: ${{d.final_pred ? getResultCN(d.final_pred) : '无'}}</div>
                        <div class="logic-text">${{d.primary_logic || '系统无明确信号，按热门方向推荐'}}</div>
                        ${{stratsHtml}}
                    </div>
                    
                    <div class="signals-grid">
                        <div class="signal-box">
                            <h4>触发信号池</h4>
                            ${{signalsHtml}}
                        </div>
                        <div class="signal-box">
                            <h4>核心数据支撑 (平均 IP 漂移)</h4>
                            ${{driftHtml}}
                            <h4 style="margin-top:16px">赛果对比</h4>
                            <p style="font-size:13px;color:#e2e8f0">
                                预测: <b>${{d.final_pred ? getResultCN(d.final_pred) : '未得出'}}</b><br>
                                实际: <b>${{d.result_actual ? getResultCN(d.result_actual) : '未完赛'}}</b>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }});

    container.innerHTML = html;
}}

renderMatches();
</script>
</body>
</html>"""
    
    out_path = ROOT / "output" / "predict_report.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Report generated successfully: {out_path}")

if __name__ == "__main__":
    build_report()
